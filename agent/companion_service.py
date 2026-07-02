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
import smtplib
from collections import deque
from email.message import EmailMessage
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
DATA_DIR = ROOT_DIR / "data"
CONTACTS_FILE = DATA_DIR / "contacts.json"

for import_path in (str(AGENT_DIR), str(SCREENSHOT_DIR), str(FEATURES_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from screen_context_agent import ScreenContextBuffer, capture_loop, wait_for_initial_screenshot
from screen_describer import DEFAULT_MODEL, capture_screen

from simple_agent import CAPABILITIES, validate_actions

try:
    from browser_tools import BrowserSession, save_output_file
except Exception:
    BrowserSession = None  # type: ignore[assignment]
    save_output_file = None  # type: ignore[assignment]


load_dotenv(ROOT_DIR / ".env")
load_dotenv(Path(__file__).with_name(".env"))

DEFAULT_SERVICE_HOST = "127.0.0.1"
DEFAULT_SERVICE_PORT = 8765
DEFAULT_MEMORY_LIMIT = 12
DEFAULT_SCREEN_INTERVAL = 5.0
DEFAULT_SCREEN_BUFFER_SIZE = 3
DEFAULT_DECISION_MAX_TOKENS = 360
DEFAULT_SCREEN_MAX_WIDTH = 1024
DEFAULT_MAX_ACTIONS_PER_PROMPT = 5
CONTROL_COMMANDS = {
    "reset context": "reset",
    "forget that": "forget",
    "cancel": "cancel",
}
OPEN_SITE_VERBS = r"(?:open up|open|go to|launch|bring up|show me)"
EMAIL_BODY_MARKERS = (
    "saying",
    "that says",
    "to say",
    "and say",
    "message",
    "telling them",
    "tell them",
    "tell him",
    "tell her",
    "that",
)
OPEN_TARGET_CLEANUPS = (
    "for me",
    "please",
    "the website",
    "website",
    "the site",
    "site",
    "the app",
    "app",
)
KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "you tube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "bbc": "https://www.bbc.com",
    "rte": "https://www.rte.ie",
    "rté": "https://www.rte.ie",
    "hse": "https://www.hse.ie",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "outlook": "https://outlook.live.com",
    "hotmail": "https://outlook.live.com",
    "yahoo": "https://www.yahoo.com",
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
                                "click_at",
                                "type_text",
                                "press_key",
                                "scroll",
                                "wait",
                                "save_file",
                                "remember_contact",
                                "lookup_contact",
                                "send_email",
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
8. Prefer one useful next action, but you may return up to five ordinary
   browser/file actions for simple tasks.
9. If the user asks to open a website, use open_url with a full https URL.
10. Use click_text for visible labels and click_at only when the screenshot
    makes the target position clear. Use scroll if the page likely needs it.
11. Use remember_contact when the user gives you a person's email address to
    save. Use lookup_contact when you need a saved email address. Use send_email
    only when recipient, subject, and body are clear.
12. Sending email is allowed, but it must pause for approval before it is sent.

Return JSON only.

Response fields:
- say: what to speak out loud, concise and direct.
- run_in_background: true only if an action should run.
- actions: zero to five actions. Keep them safe and directly useful.
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
REJECTION_PHRASES = {
    "no",
    "no thanks",
    "don't",
    "dont",
    "do not",
    "cancel",
    "stop",
    "never mind",
    "nevermind",
}
HIGH_RISK_TERMS = {
    "bank",
    "banking",
    "buy",
    "card",
    "card number",
    "checkout",
    "delete",
    "download",
    "email",
    "gift card",
    "install",
    "identity",
    "message",
    "one-time code",
    "passcode",
    "password",
    "payment",
    "post",
    "purchase",
    "recovery",
    "remote access",
    "security warning",
    "send",
    "send money",
    "social security",
    "sudo",
    "submit",
    "transfer",
    "upload",
}
SENSITIVE_TYPE_TERMS = {
    "card",
    "code",
    "cvv",
    "otp",
    "passcode",
    "password",
    "pin",
    "security answer",
    "social security",
}


class PromptRequest(BaseModel):
    source: str = Field(default="overlay")
    text: str


class PromptResponse(BaseModel):
    say: str
    run_in_background: bool
    actions: list[dict[str, Any]]
    status: str = "ok"


class VoiceStatusRequest(BaseModel):
    status: str = Field(default="awake")
    duration_ms: int = Field(default=4500)


class CompanionState:
    def __init__(self) -> None:
        self.memory: deque[dict[str, Any]] = deque(maxlen=int(os.getenv("MEMORY_LIMIT", DEFAULT_MEMORY_LIMIT)))
        self.pending_action: dict[str, Any] | None = None
        self.pending_screen_description = ""
        self.voice_awake_until = 0.0
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

    def mark_voice_awake(self, duration_ms: int) -> None:
        bounded_ms = max(500, min(int(duration_ms), 15000))
        self.voice_awake_until = time.time() + (bounded_ms / 1000)

    def is_voice_awake(self) -> bool:
        return time.time() < self.voice_awake_until


class BrowserActionRunner:
    def __init__(self) -> None:
        self.session: Any | None = None
        self.outputs_dir = FEATURES_DIR / "outputs"
        self.contacts = ContactBook(CONTACTS_FILE)

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
        if name == "save_file":
            path = save_output_file(
                self.outputs_dir,
                str(action.get("filename") or "output.md"),
                str(action.get("content") or ""),
            )
            return f"Saved {path}"
        if name == "remember_contact":
            return self.contacts.remember(str(action["name"]), str(action["email"]))
        if name == "lookup_contact":
            return self.contacts.lookup(str(action["name"]))
        if name == "send_email":
            return send_email_action(action)

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
        if name == "click_at":
            return browser.click_at(float(action["x"]), float(action["y"]))
        if name == "type_text":
            return browser.type_text(str(action["selector"]), str(action["text"]))
        if name == "press_key":
            return browser.press_key(str(action["key"]))
        if name == "scroll":
            return browser.scroll(float(action.get("delta_y", 600)))
        if name == "wait":
            return browser.wait(int(action.get("milliseconds", 1000)))
        raise ValueError(f"Unsupported action: {name}")

    def _browser(self) -> Any:
        if self.session is None:
            self.session = BrowserSession()
            self.session.__enter__()
        return self.session


class ContactBook:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()

    def remember(self, name: str, email: str) -> str:
        clean_name = normalize_contact_name(name)
        clean_email = normalize_email(email)
        if not clean_name:
            raise ValueError("Contact name cannot be empty.")
        if not clean_email:
            raise ValueError("Contact email is not valid.")

        with self.lock:
            contacts = self._load()
            contacts[clean_name] = {
                "name": name.strip(),
                "email": clean_email,
                "updated_at": int(time.time()),
            }
            self._save(contacts)

        return f"Remembered {name.strip()} as {clean_email}."

    def lookup(self, name: str) -> str:
        clean_name = normalize_contact_name(name)
        contacts = self._load()
        contact = contacts.get(clean_name)
        if not contact:
            return f"No saved contact found for {name}."
        return f"{contact['name']}: {contact['email']}"

    def summary(self) -> list[dict[str, str]]:
        contacts = self._load()
        return [
            {"name": item["name"], "email": item["email"]}
            for item in sorted(contacts.values(), key=lambda contact: contact["name"].lower())
        ]

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, contacts: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_contact_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def normalize_email(email: str) -> str:
    cleaned = str(email or "").strip()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
        return cleaned
    return ""


def send_email_action(action: dict[str, Any]) -> str:
    to_email = resolve_email_recipient(str(action.get("to") or action.get("name") or ""))
    subject = str(action.get("subject") or "").strip()
    body = str(action.get("body") or "").strip()

    if not to_email:
        raise ValueError("Email recipient is missing or not saved in contacts.")
    if not subject:
        raise ValueError("Email subject is required.")
    if not body:
        raise ValueError("Email body is required.")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM") or smtp_user
    from_name = os.getenv("SMTP_FROM_NAME", "Grandson")

    if not smtp_host or not smtp_user or not smtp_password or not from_email:
        raise RuntimeError("Email is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM.")

    message = EmailMessage()
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    return f"Sent email to {to_email}."


def resolve_email_recipient(recipient: str) -> str:
    recipient = recipient.strip()
    if normalize_email(recipient):
        return recipient

    contacts = ContactBook(CONTACTS_FILE)
    contact = contacts._load().get(normalize_contact_name(recipient))
    if contact:
        return str(contact.get("email") or "")
    return ""


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
        "voice_awake": state.is_voice_awake(),
    }


@app.post("/voice-status")
def voice_status(request: VoiceStatusRequest) -> dict[str, Any]:
    if request.status in {"awake", "listening"}:
        state.mark_voice_awake(request.duration_ms)
    return {"status": "ok", "voice_awake": state.is_voice_awake()}


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
        if state.pending_action and is_rejection(text):
            state.pending_action = None
            state.remember("User rejected pending action.", request.source, "cancelled")
            return PromptResponse(say="Okay, I will not send it.", run_in_background=False, actions=[], status="cancelled")

        direct_email = direct_email_decision(text)
        if direct_email is not None:
            return execute_decision(request.source, text, direct_email)

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
        say = "Email sent." if action.get("action") == "send_email" else "Okay, I did that."
        status = "acted"
    except Exception as exc:
        result = f"Action failed: {exc}"
        say = "I tried, but that did not work."
        status = "error"

    state.remember(f"Approved action: {action.get('action')}", "approval", status, result)
    return PromptResponse(say=say, run_in_background=True, actions=[action], status=status)


def execute_decision(source: str, text: str, decision: dict[str, Any]) -> PromptResponse:
    actions = decision.get("actions", [])
    action_limit = int(os.getenv("MAX_ACTIONS_PER_PROMPT", DEFAULT_MAX_ACTIONS_PER_PROMPT))
    requested_actions = actions[:action_limit]
    run_in_background = bool(decision.get("run_in_background"))
    say = str(decision.get("say") or "")
    status = str(decision.get("status") or "ok")
    memory_note = str(decision.get("memory_note") or "")

    action_results: list[str] = []
    completed_actions: list[dict[str, Any]] = []
    if run_in_background and requested_actions:
        for action in requested_actions:
            if should_require_approval(action):
                state.pending_action = action
                completed_actions.append(action)
                say = approval_message(action, say)
                status = "approval_required"
                break

            result = execute_action(action)
            completed_actions.append(action)
            action_results.append(result)
            status = "acted"

            if result.lower().startswith("action failed:"):
                break

    action_result = " | ".join(action_results)
    if state.pending_action is not None and not action_result:
        action_result = "Waiting for approval."
    if state.pending_action is not None:
        status = "approval_required"
        if not say:
            say = approval_message(state.pending_action)

    state.remember(memory_note or f"User asked: {text}", source, status, action_result)
    return PromptResponse(say=say, run_in_background=run_in_background, actions=completed_actions, status=status)


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
                    "saved_contacts": state.action_runner.contacts.summary(),
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
    if not re.search(rf"\b{OPEN_SITE_VERBS}\b", normalized):
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

    domain_match = re.search(r"\b([a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|ie|co\.uk|co|edu|gov|tv|io|ai|app))\b", normalized)
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

    target = extract_open_target(normalized)
    if target:
        guessed_domain = slugify_site_target(target)
        if guessed_domain:
            return {
                "say": f"Opening {target.title()}.",
                "run_in_background": True,
                "actions": [{"action": "open_url", "url": f"https://www.{guessed_domain}.com"}],
                "memory_note": f"User asked to open {target}.",
                "needs_action": True,
                "status": "ok",
            }

    return None


def direct_email_decision(text: str) -> dict[str, Any] | None:
    cleaned = " ".join(text.strip().split())
    normalized = cleaned.lower()
    if not re.search(r"\b(send|email|mail)\b", normalized):
        return None
    if not re.search(r"\b(email|mail)\b", normalized):
        return None

    recipient = extract_email_recipient(cleaned)
    body = extract_email_body(cleaned)
    subject = extract_email_subject(cleaned) or "Quick note"

    if not recipient:
        return {
            "say": "Who should I send the email to?",
            "run_in_background": False,
            "actions": [],
            "memory_note": "User wanted to send an email but recipient was unclear.",
            "needs_action": True,
            "status": "needs_clarification",
        }

    to_email = resolve_email_recipient(recipient)
    if not to_email:
        return {
            "say": f"I do not have an email address saved for {recipient}.",
            "run_in_background": False,
            "actions": [],
            "memory_note": f"Email recipient missing for {recipient}.",
            "needs_action": True,
            "status": "needs_clarification",
        }

    if not body:
        return {
            "say": f"What should I say to {recipient}?",
            "run_in_background": False,
            "actions": [],
            "memory_note": f"User wanted to email {recipient}, but body was unclear.",
            "needs_action": True,
            "status": "needs_clarification",
        }

    action = {
        "action": "send_email",
        "to": to_email,
        "subject": subject,
        "body": body,
    }
    return {
        "say": approval_message(action),
        "run_in_background": True,
        "actions": [action],
        "memory_note": f"Drafted email to {recipient}; waiting for approval.",
        "needs_action": True,
        "status": "approval_required",
    }


def extract_email_recipient(text: str) -> str:
    email_match = re.search(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b", text)
    if email_match:
        return email_match.group(0)

    contacts = state.action_runner.contacts.summary()
    normalized = text.lower()
    for contact in contacts:
        name = str(contact.get("name") or "")
        if name and re.search(rf"\b{re.escape(name.lower())}\b", normalized):
            return name

    recipient_patterns = (
        r"\b(?:send|write)\s+([a-z][a-z .'-]{0,60}?)\s+(?:an\s+)?(?:email|mail)\b",
        r"\b(?:send|write)\s+(?:an\s+)?(?:email|mail)\s+to\s+([a-z][a-z .'-]{0,60}?)(?:\s+(?:saying|that|to say|message|about)\b|$)",
        r"\b(?:email|mail)\s+([a-z][a-z .'-]{0,60}?)(?:\s+(?:saying|that|to say|message|about)\b|$)",
    )
    for pattern in recipient_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_email_fragment(match.group(1))

    return ""


def clean_email_fragment(value: str) -> str:
    cleaned = str(value or "").strip(" ,.!?")
    cleaned = re.sub(r"\b(?:an|a|the|email|mail|please|for me)\b", " ", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()).strip(" ,.!?")


def extract_email_body(text: str) -> str:
    subject_split = re.split(r"\bbody\b\s*:?", text, maxsplit=1, flags=re.IGNORECASE)
    if len(subject_split) == 2:
        return clean_email_body(subject_split[1])

    lowered = text.lower()
    best_index = -1
    best_marker = ""
    for marker in EMAIL_BODY_MARKERS:
        index = lowered.find(marker)
        if index >= 0 and (best_index == -1 or index < best_index):
            best_index = index
            best_marker = marker

    if best_index == -1:
        return ""

    return clean_email_body(text[best_index + len(best_marker):])


def clean_email_body(value: str) -> str:
    cleaned = str(value or "").strip(" :,.!?")
    cleaned = re.sub(r"^(?:to\s+)?", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_email_subject(text: str) -> str:
    match = re.search(
        r"\bsubject\b\s*(?:is|:)?\s+(.+?)(?:\s+\b(?:body|saying|that says|to say|message)\b|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return match.group(1).strip(" :,.!?")[:120]


def extract_open_target(text: str) -> str:
    match = re.search(rf"\b{OPEN_SITE_VERBS}\b\s+(.+)$", text)
    if not match:
        return ""

    target = match.group(1).strip(" ?!.,")
    changed = True
    while changed:
        changed = False
        for cleanup in OPEN_TARGET_CLEANUPS:
            if target.endswith(f" {cleanup}"):
                target = target[: -len(cleanup) - 1].strip(" ?!.,")
                changed = True
            elif target == cleanup:
                return ""

    target = re.sub(r"^(?:the|a|an)\s+", "", target)
    return target.strip(" ?!.,")


def slugify_site_target(target: str) -> str:
    words = re.findall(r"[a-z0-9]+", target.lower())
    if not words or len(words) > 4:
        return ""
    return "".join(words)


def should_require_approval(action: dict[str, Any]) -> bool:
    action_name = str(action.get("action") or "")
    if action_name in {"remember_contact", "lookup_contact"}:
        return False
    if action_name == "send_email":
        return True

    combined = json.dumps(action, ensure_ascii=False).lower()
    if action_name == "type_text" and any(
        term in combined for term in SENSITIVE_TYPE_TERMS
    ):
        return True
    return any(term in combined for term in HIGH_RISK_TERMS)


def approval_message(action: dict[str, Any], fallback: str = "") -> str:
    if action.get("action") == "send_email":
        to_email = resolve_email_recipient(str(action.get("to") or action.get("name") or ""))
        subject = str(action.get("subject") or "").strip() or "Quick note"
        body = compact_text(str(action.get("body") or "").strip(), limit=180)
        return (
            f"Draft ready. To {to_email}. Subject: {subject}. "
            f"Message: {body}. Say yes to send, or cancel."
        )

    return fallback or "That could affect something important. Please say yes if you want me to continue."


def is_approval(text: str) -> bool:
    normalized = " ".join(text.lower().replace(".", "").split())
    return normalized in APPROVAL_PHRASES


def is_rejection(text: str) -> bool:
    normalized = " ".join(text.lower().replace(".", "").split())
    return normalized in REJECTION_PHRASES


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
