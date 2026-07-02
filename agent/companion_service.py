#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import threading
import time
import base64
import io
import re
from collections import deque
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = ROOT_DIR / "screenshot"
FEATURES_DIR = ROOT_DIR / "features" / "laptop-agent-mvp"

for import_path in (str(AGENT_DIR), str(SCREENSHOT_DIR), str(FEATURES_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from screen_context_agent import ScreenContextBuffer, capture_loop, wait_for_initial_screenshot
from screen_describer import DEFAULT_MODEL, capture_screen

from simple_agent import CAPABILITIES, validate_actions

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
DEFAULT_DECISION_MAX_TOKENS = 360
DEFAULT_SCREEN_MAX_WIDTH = 1024
CONTROL_COMMANDS = {
    "reset context": "reset",
    "forget that": "forget",
    "cancel": "cancel",
}
KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "you tube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
}
DECISION_SCHEMA: dict[str, Any] = {
    "name": "companion_decision",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["say", "run_in_background", "actions", "memory_note", "needs_action", "status"],
        "properties": {
            "say": {"type": "string"},
            "run_in_background": {"type": "boolean"},
            "needs_action": {"type": "boolean"},
            "status": {"type": "string"},
            "memory_note": {"type": "string"},
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "required": ["action"],
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "open_url",
                                "search_web",
                                "get_page_text",
                                "click_text",
                                "type_text",
                                "press_key",
                                "save_file",
                                "ask_user",
                                "done",
                            ],
                        }
                    },
                },
            },
        },
    },
    "strict": False,
}
DECISION_SYSTEM_PROMPT = """
You are Grandson, a fast practical computer helper for older Mac users.

The user may type in an overlay or speak through a wake word. You receive their
prompt, compact recent memory, available browser/file actions, and usually one
current screenshot.

Priorities:
1. Help the user do the next useful thing. Start with the practical answer.
2. Describe the screen only when asked, when safety needs it, or when it helps
   explain the next step.
3. Keep spoken replies very short: one or two short sentences unless safety
   needs more. Aim for about 25 words.
4. If the user asks for a task, guide or choose one safe action instead of
   narrating the whole screen.
5. Be careful with passwords, banking, payments, identity, remote access,
   urgent warnings, messages, downloads, uploads, deletion, and purchases.
6. Never repeat private details from the screen. Refer to them generally.
7. Use only the actions listed in the input.
8. Prefer a single useful next action. Do not create long speculative plans.
9. If the user asks to open a known website, use open_url with a full https URL.

Return JSON only.

Response fields:
- say: what to speak out loud, concise and direct.
- run_in_background: true only if an action should run.
- actions: zero or one action unless a save_file after research is clearly ready.
- memory_note: one compact note for future context, or empty string.
- needs_action: true if the user wants something done or guided.
- status: short machine-readable status such as ok, acted, needs_clarification,
  approval_required, screen_unavailable, or done.
""".strip()
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

    def remember(self, note: str, source: str, status: str, action_result: str = "") -> None:
        note = compact_text(note)
        if not note and not action_result:
            return

        self.memory.append(
            {
                "source": source,
                "note": note,
                "status": status,
                "action_result": compact_text(action_result, limit=220),
                "time": int(time.time()),
            }
        )

    def reset_memory(self) -> None:
        self.memory.clear()
        self.pending_action = None
        self.pending_screen_description = ""

    def forget_last(self) -> None:
        if self.memory:
            self.memory.pop()


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
        control_response = handle_control_command(text)
        if control_response is not None:
            return control_response

        if state.pending_action and is_approval(text):
            return execute_pending_action(text)

        direct_decision = direct_site_open_decision(text)
        if direct_decision is not None:
            return execute_decision(request.source, text, direct_decision)

        try:
            decision = choose_decision(text)
        except Exception as exc:
            say = "I could not think that through because the assistant service had a problem."
            state.remember(f"Request failed: {text}", request.source, "error", str(exc))
            return PromptResponse(say=say, run_in_background=False, actions=[], status="error")

        return execute_decision(request.source, text, decision)


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

    state.remember(f"Approved action: {action.get('action')}", "approval", status, result)
    return PromptResponse(say=say, run_in_background=True, actions=[action], status=status)


def execute_decision(source: str, text: str, decision: dict[str, Any]) -> PromptResponse:
    actions = decision.get("actions", [])
    run_in_background = bool(decision.get("run_in_background"))
    say = str(decision.get("say") or "")
    status = str(decision.get("status") or "ok")
    memory_note = str(decision.get("memory_note") or "")

    action_result = ""
    if run_in_background and actions:
        action = actions[0]
        if should_require_approval(action):
            state.pending_action = action
            say = say or "That could affect something important. Please say yes if you want me to continue."
            status = "approval_required"
        else:
            action_result = execute_action(action)
            status = "acted"

    state.remember(memory_note or f"User asked: {text}", source, status, action_result)
    return PromptResponse(say=say, run_in_background=run_in_background, actions=actions[:1], status=status)


def choose_decision(user_prompt: str) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Missing dependency: install the OpenAI Python SDK.") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY.")

    screenshot = newest_screenshot_for_prompt(user_prompt)
    user_content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": json.dumps(
                {
                    "user_prompt": user_prompt,
                    "recent_memory": state.context_text(),
                    "capabilities": CAPABILITIES,
                    "screen_available": screenshot is not None,
                    "screen_error": state.screen_buffer.last_error,
                },
                ensure_ascii=False,
            ),
        }
    ]
    if screenshot:
        user_content.append({"type": "input_image", "image_url": screenshot})

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=os.getenv("ASSISTANT_MODEL", os.getenv("VISION_MODEL", DEFAULT_MODEL)),
        input=[
            {"role": "system", "content": DECISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_output_tokens=int(os.getenv("DECISION_MAX_TOKENS", DEFAULT_DECISION_MAX_TOKENS)),
        text={
            "format": {
                "type": "json_schema",
                "name": DECISION_SCHEMA["name"],
                "schema": DECISION_SCHEMA["schema"],
                "strict": DECISION_SCHEMA["strict"],
            }
        },
    )
    decision = json.loads(response.output_text)
    validate_actions(decision)
    return decision


def direct_site_open_decision(text: str) -> dict[str, Any] | None:
    normalized = " ".join(text.lower().split())
    if not re.search(r"\b(open|go to|launch|bring up|show me)\b", normalized):
        return None

    for site_name, url in KNOWN_SITES.items():
        if re.search(rf"\b{re.escape(site_name)}\b", normalized):
            return {
                "say": f"Opening {site_name.title()}.",
                "run_in_background": True,
                "actions": [{"action": "open_url", "url": url}],
                "memory_note": f"User asked to open {site_name}.",
                "needs_action": True,
                "status": "ok",
            }

    domain_match = re.search(r"\b([a-z0-9-]+\.(?:com|org|net|ie|co\.uk))\b", normalized)
    if domain_match:
        domain = domain_match.group(1)
        return {
            "say": f"Opening {domain}.",
            "run_in_background": True,
            "actions": [{"action": "open_url", "url": f"https://{domain}"}],
            "memory_note": f"User asked to open {domain}.",
            "needs_action": True,
            "status": "ok",
        }

    return None


def should_require_approval(action: dict[str, Any]) -> bool:
    if action_has_risk(action):
        return True
    combined = json.dumps(action, ensure_ascii=False).lower()
    return any(term in combined for term in HIGH_RISK_TERMS)


def is_approval(text: str) -> bool:
    normalized = " ".join(text.lower().replace(".", "").split())
    return normalized in APPROVAL_PHRASES


def handle_control_command(text: str) -> PromptResponse | None:
    normalized = " ".join(text.lower().strip().split())
    command = CONTROL_COMMANDS.get(normalized)
    if command == "reset":
        state.reset_memory()
        return PromptResponse(say="Okay, I forgot the recent context.", run_in_background=False, actions=[], status="context_reset")
    if command == "forget":
        state.forget_last()
        return PromptResponse(say="Okay, I forgot the last bit.", run_in_background=False, actions=[], status="context_forgot_last")
    if command == "cancel":
        state.pending_action = None
        state.pending_screen_description = ""
        return PromptResponse(say="Okay, cancelled.", run_in_background=False, actions=[], status="cancelled")
    return None


def execute_action(action: dict[str, Any]) -> str:
    try:
        return state.action_runner.execute_one(action)
    except Exception as exc:
        return f"Action failed: {exc}"


def newest_screenshot_for_prompt(prompt: str) -> str | None:
    screenshots = state.screen_buffer.snapshot()
    image_bytes: bytes | None = screenshots[-1] if screenshots else None

    if image_bytes is None:
        try:
            image_bytes = capture_screen()
        except Exception as exc:
            state.screen_buffer.set_error(exc)
            return None

    return image_bytes_to_data_url(image_bytes)


def image_bytes_to_data_url(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail((int(os.getenv("SCREEN_MAX_WIDTH", DEFAULT_SCREEN_MAX_WIDTH)), DEFAULT_SCREEN_MAX_WIDTH))

    buffer = io.BytesIO()
    image.convert("RGB").save(
        buffer,
        format="JPEG",
        quality=int(os.getenv("SCREEN_JPEG_QUALITY", "72")),
        optimize=True,
    )
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def compact_text(value: str, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3].rstrip()}..."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "companion_service:app",
        host=os.getenv("COMPANION_HOST", DEFAULT_SERVICE_HOST),
        port=int(os.getenv("COMPANION_PORT", DEFAULT_SERVICE_PORT)),
        reload=False,
    )
