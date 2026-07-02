#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = ROOT_DIR / "screenshot"
FEATURES_DIR = ROOT_DIR / "features" / "laptop-agent-mvp"

for import_path in (str(AGENT_DIR), str(SCREENSHOT_DIR), str(FEATURES_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from screen_context_agent import ScreenContextBuffer, capture_loop, wait_for_initial_screenshot
from screen_describer import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, capture_screen, describe_screen_context

from simple_agent import build_input, call_openai, load_system_prompt, validate_actions

try:
    from browser_tools import BrowserSession, save_output_file
    from safety import action_has_risk
except Exception:
    BrowserSession = None  # type: ignore[assignment]
    save_output_file = None  # type: ignore[assignment]

    def action_has_risk(_action: dict[str, Any]) -> bool:
        return True


load_dotenv(ROOT_DIR / ".env")
load_dotenv(Path(__file__).with_name(".env"))

DEFAULT_SERVICE_HOST = "127.0.0.1"
DEFAULT_SERVICE_PORT = 8765
DEFAULT_MEMORY_LIMIT = 12
DEFAULT_SCREEN_INTERVAL = 5.0
DEFAULT_SCREEN_BUFFER_SIZE = 3
DEFAULT_VISION_MAX_TOKENS = 300
APPROVAL_PHRASES = {
    "yes",
    "yes do it",
    "yes, do it",
    "approve",
    "approved",
    "go ahead",
    "continue",
    "do it",
}
HIGH_RISK_TERMS = {
    "bank",
    "banking",
    "card number",
    "checkout",
    "gift card",
    "identity",
    "login",
    "one-time code",
    "passcode",
    "password",
    "payment",
    "purchase",
    "recovery",
    "remote access",
    "security warning",
    "send money",
    "social security",
    "submit",
    "transfer",
}


class PromptRequest(BaseModel):
    source: str = Field(default="overlay")
    text: str


class PromptResponse(BaseModel):
    say: str
    run_in_background: bool
    actions: list[dict[str, Any]]
    status: str = "ok"


class CompanionState:
    def __init__(self) -> None:
        self.memory: deque[dict[str, Any]] = deque(maxlen=int(os.getenv("MEMORY_LIMIT", DEFAULT_MEMORY_LIMIT)))
        self.pending_action: dict[str, Any] | None = None
        self.pending_screen_description = ""
        self.screen_buffer = ScreenContextBuffer(
            int(os.getenv("SCREEN_AGENT_BUFFER_SIZE", DEFAULT_SCREEN_BUFFER_SIZE))
        )
        self.stop_event = threading.Event()
        self.capture_thread: threading.Thread | None = None
        self.action_runner = BrowserActionRunner()
        self.lock = threading.Lock()

    def start(self) -> None:
        if self.capture_thread and self.capture_thread.is_alive():
            return

        interval = float(os.getenv("SCREEN_AGENT_INTERVAL", DEFAULT_SCREEN_INTERVAL))
        self.capture_thread = threading.Thread(
            target=capture_loop,
            args=(self.screen_buffer, self.stop_event, interval),
            daemon=True,
        )
        self.capture_thread.start()
        wait_for_initial_screenshot(self.screen_buffer, timeout_seconds=3.0)

    def stop(self) -> None:
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        self.action_runner.close()

    def context_text(self) -> str:
        if not self.memory:
            return "No previous context yet."
        return json.dumps(list(self.memory), ensure_ascii=False, indent=2)

    def remember(self, item: dict[str, Any]) -> None:
        self.memory.append(item)


class BrowserActionRunner:
    def __init__(self) -> None:
        self.session: Any | None = None
        self.outputs_dir = FEATURES_DIR / "outputs"

    def close(self) -> None:
        if self.session is not None:
            self.session.__exit__(None, None, None)
            self.session = None

    def execute_one(self, action: dict[str, Any]) -> str:
        if BrowserSession is None or save_output_file is None:
            raise RuntimeError("Browser action dependencies are not installed.")

        name = action.get("action")
        if name == "ask_user":
            return str(action.get("question") or "Please confirm what you want me to do.")
        if name == "done":
            return str(action.get("summary") or "Finished.")

        browser = self._browser()
        if name == "open_url":
            return browser.open_url(str(action["url"]))
        if name == "search_web":
            return browser.search_web(str(action["query"]))
        if name == "get_page_text":
            text = browser.get_page_text()
            return f"Read {len(text)} characters from the page."
        if name == "click_text":
            return browser.click_text(str(action["text"]))
        if name == "type_text":
            return browser.type_text(str(action["selector"]), str(action["text"]))
        if name == "press_key":
            return browser.press_key(str(action["key"]))
        if name == "save_file":
            path = save_output_file(
                self.outputs_dir,
                str(action.get("filename") or "output.md"),
                str(action.get("content") or ""),
            )
            return f"Saved {path}"
        raise ValueError(f"Unsupported action: {name}")

    def _browser(self) -> Any:
        if self.session is None:
            self.session = BrowserSession()
            self.session.__enter__()
        return self.session


state = CompanionState()
app = FastAPI(title="Local Companion Service")


@app.on_event("startup")
def startup() -> None:
    state.start()


@app.on_event("shutdown")
def shutdown() -> None:
    state.stop()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "screenshots": state.screen_buffer.count(),
        "screen_error": state.screen_buffer.last_error,
        "pending_action": state.pending_action is not None,
    }


@app.post("/prompt", response_model=PromptResponse)
def handle_prompt(request: PromptRequest) -> PromptResponse:
    text = request.text.strip()
    if not text:
        return PromptResponse(say="", run_in_background=False, actions=[], status="ignored")

    with state.lock:
        if state.pending_action and is_approval(text):
            return execute_pending_action(text)

        screen_description = describe_current_screen(text)
        try:
            decision = choose_decision(text, screen_description)
        except Exception as exc:
            say = "I could not think that through because the assistant service had a problem."
            state.remember(
                {
                    "source": request.source,
                    "user_prompt": text,
                    "screen": screen_description,
                    "say": say,
                    "actions": [],
                    "action_result": str(exc),
                    "status": "error",
                    "time": int(time.time()),
                }
            )
            return PromptResponse(say=say, run_in_background=False, actions=[], status="error")

        actions = decision.get("actions", [])
        run_in_background = bool(decision.get("run_in_background"))
        say = str(decision.get("say") or "")
        status = "ok"

        action_result = ""
        if run_in_background and actions:
            action = actions[0]
            if should_require_approval(action, screen_description):
                state.pending_action = action
                state.pending_screen_description = screen_description
                say = say or "That could affect something important. Please say yes if you want me to continue."
                status = "approval_required"
            else:
                action_result = execute_action(action)
                status = "acted"

        state.remember(
            {
                "source": request.source,
                "user_prompt": text,
                "screen": screen_description,
                "say": say,
                "actions": actions[:1],
                "action_result": action_result,
                "status": status,
                "time": int(time.time()),
            }
        )
        return PromptResponse(say=say, run_in_background=run_in_background, actions=actions[:1], status=status)


def execute_pending_action(approval_text: str) -> PromptResponse:
    action = state.pending_action
    state.pending_action = None
    if not action:
        return PromptResponse(say="There is nothing waiting for approval.", run_in_background=False, actions=[])

    try:
        result = execute_action(action)
        say = "Okay, I did that."
        status = "acted"
    except Exception as exc:
        result = f"Action failed: {exc}"
        say = "I tried, but that did not work."
        status = "error"

    state.remember(
        {
            "source": "approval",
            "user_prompt": approval_text,
            "screen": state.pending_screen_description,
            "say": say,
            "actions": [action],
            "action_result": result,
            "status": status,
            "time": int(time.time()),
        }
    )
    return PromptResponse(say=say, run_in_background=True, actions=[action], status=status)


def describe_current_screen(question: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Screen context is unavailable because OPENAI_API_KEY is not set."

    screenshots = state.screen_buffer.snapshot()
    if not screenshots:
        if state.screen_buffer.last_error:
            return f"Screen context is unavailable: {state.screen_buffer.last_error}"
        try:
            screenshots = [capture_screen()]
        except Exception as exc:
            return f"Screen context is unavailable: {exc}"

    try:
        return describe_screen_context(
            question=question,
            image_sequence=screenshots,
            model=os.getenv("VISION_MODEL", DEFAULT_MODEL),
            api_key=api_key,
            max_tokens=int(os.getenv("VISION_MAX_TOKENS", DEFAULT_VISION_MAX_TOKENS)),
        )
    except Exception as exc:
        return f"Screen context is unavailable: {exc}"


def choose_decision(user_prompt: str, screen_description: str) -> dict[str, Any]:
    model = os.getenv("ASSISTANT_MODEL", "gpt-5.4-nano")
    system_prompt = load_system_prompt()
    user_input = build_input(user_prompt, screen_description, state.context_text())
    decision = call_openai(system_prompt, user_input, model)
    validate_actions(decision)
    return decision


def should_require_approval(action: dict[str, Any], screen_description: str) -> bool:
    if action_has_risk(action):
        return True
    combined = f"{screen_description}\n{json.dumps(action, ensure_ascii=False)}".lower()
    return any(term in combined for term in HIGH_RISK_TERMS)


def is_approval(text: str) -> bool:
    normalized = " ".join(text.lower().replace(".", "").split())
    return normalized in APPROVAL_PHRASES


def execute_action(action: dict[str, Any]) -> str:
    try:
        return state.action_runner.execute_one(action)
    except Exception as exc:
        return f"Action failed: {exc}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "companion_service:app",
        host=os.getenv("COMPANION_HOST", DEFAULT_SERVICE_HOST),
        port=int(os.getenv("COMPANION_PORT", DEFAULT_SERVICE_PORT)),
        reload=False,
    )
