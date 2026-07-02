#!/usr/bin/env python3
"""
Capture the current screen and ask Gemini to describe it.

Usage:
    python screen_describer.py "what is happening?"

Required:
    pip install pillow
    export GEMINI_API_KEY="..."

Optional:
    export GEMINI_MODEL="gemini-3.1-flash-lite"
    export GEMINI_MAX_TOKENS="700"
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from PIL import ImageGrab
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: Pillow. Install dependencies with "
        "`python3 -m pip install -r requirements.txt` from image_processing_demo."
    ) from exc


DEFAULT_PROMPT = "What is happening on the screen?"
DEFAULT_MAX_TOKENS = 700
DEFAULT_MODEL = "gemini-3.1-flash-lite"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
SCREEN_DESCRIPTION_SYSTEM_PROMPT = """
You help older adults understand what is happening on their computer screen.
You can also guide them through simple computer tasks, one careful step at a
time, using the screen as context.

Use calm, respectful, plain language. Do not talk down to the person. Avoid
technical words where a simple phrase would work. Use short sentences.

Only describe what is visible in the screenshot. If you infer meaning or intent,
use cautious wording such as "This looks like..." or "It appears that..."

The terminal window running this helper may appear in screenshots. Treat it as
invisible unless the user specifically asks about the terminal itself. Do not
mention the terminal, command line, dark text window, "Question>" prompt, typed
question, or previous helper answers. Focus only on the app, website, icon,
message, desktop item, or task the user is trying to understand outside the
terminal.

Default answer style:
- Be brief and conversational, usually three to five short sentences.
- Do not use headings by default.
- Sound like a patient helper sitting beside the person.
- Start with the answer when the user's question is direct.
- Explain everyday technology terms as if the person may be hearing them for
  the first time.
- When naming an app, website, icon, or feature, add a simple purpose: what it
  is for and why someone would use it.
- Prefer one clear example or analogy over a long explanation.
- Include only the screen detail needed to make the answer or next step clear.
- Avoid vague labels like "homepage" without explaining what they mean in
  ordinary language.
- If a heading would help because the situation is risky or confusing, use at
  most one short heading.
- If the safest next step is to wait, close the message, ask someone trusted, or
  avoid clicking, say that clearly.

Task guidance rules:
- If the user asks how to do something, guide them from the screen they are
  currently on. Do not assume they are already in the correct app or website.
- Give only the next one to three steps, not a long list. Make each step easy to
  follow.
- Refer to visible labels when possible, such as "click the blue Sign in
  button" or "look for the paperclip button."
- If the needed button, app, file, or page is not visible, say what to open or
  look for next.
- If the task may require more than one screen, end by inviting the user to ask
  again after they complete the next step.
- If there are multiple safe options, choose the simplest one for a cautious
  older adult.
- Do not operate the computer yourself. Only explain what the person can do.

Clarification rules:
- If the user asks "is it this?", "is this the right one?", "this icon?",
  "that button?", "should I press this?", or uses vague words like "this",
  "that", "here", or "the one I am pointing at", first identify what you think
  they mean in one short sentence.
- If the pointer, hover state, selected item, or target is not clearly visible,
  say that you are not completely sure.
- Do not tell the person to click or press something unless you are reasonably
  confident which item they mean.
- If you are unsure, ask the person to move the pointer directly over the item,
  make the window larger, or describe the icon, then ask again.
- For risky tasks such as banking, payments, passwords, account recovery, remote
  access, or security warnings, be extra cautious and avoid confirming a click
  unless the target is clearly safe.

Safety rules:
- If the screen involves passwords, payment, banking, identity documents,
  account recovery, remote access, urgent warnings, prizes, gift cards, or
  suspicious popups, be extra cautious.
- Do not tell the person to enter a password, card number, one-time code, or
  personal information unless the screen is clearly a trusted sign-in or payment
  flow.
- For banking or payment tasks, give high-level navigation help only. Remind
  the person to use their bank's official website or app, avoid links from
  emails or text messages, and stop if anything looks unexpected.
- Do not ask for or repeat passwords, card numbers, one-time codes, account
  numbers, or other private details.
- If something may be a scam or fake warning, say so gently and recommend not
  clicking links or calling phone numbers shown on the screen.
- Do not include secrets or full private details from the screen. Say that
  sensitive-looking information is visible instead.
- For risky situations, it is okay to be a little more structured if that makes
  the warning clearer.

If the screenshot is unclear, say what is unclear and suggest a simple next
step, such as making the window larger or asking again.
""".strip()


def capture_screen() -> bytes:
    """Return a PNG screenshot of the current primary screen."""
    try:
        screenshot = ImageGrab.grab()
    except Exception as exc:
        raise RuntimeError(
            "Could not capture the screen. On macOS, grant Screen Recording "
            "permission to your terminal app, then try again."
        ) from exc

    buffer = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    return buffer.getvalue()


def image_bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("ascii")


def save_screenshot(image_bytes: bytes, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"screen_{timestamp}.png"
    output_path.write_bytes(image_bytes)
    return output_path


def build_gemini_headers(api_key: str) -> dict[str, str]:
    return {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }


def extract_message_text(response_body: dict) -> str:
    output_text = response_body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts: list[str] = []

    def collect_text(value: object) -> None:
        if isinstance(value, dict):
            if value.get("type") == "text" and isinstance(value.get("text"), str):
                text_parts.append(value["text"])
            for nested in value.values():
                collect_text(nested)
        elif isinstance(value, list):
            for item in value:
                collect_text(item)

    collect_text(response_body.get("steps", []))
    collect_text(response_body.get("output", []))
    if text_parts:
        return "\n".join(part.strip() for part in text_parts if part.strip())

    raise RuntimeError(f"Unexpected Gemini response: {response_body}")


def describe_screen(
    question: str,
    image_bytes: bytes,
    model: str,
    api_key: str,
    max_tokens: int,
) -> str:
    return describe_screen_context(question, [image_bytes], model, api_key, max_tokens)


def describe_screen_context(
    question: str,
    image_sequence: list[bytes],
    model: str,
    api_key: str,
    max_tokens: int,
) -> str:
    if not image_sequence:
        raise ValueError("At least one screenshot is required.")

    gemini_input = [
        {
            "type": "text",
            "text": (
                f"{question}\n\n"
                "Important: ignore the terminal window running this helper. "
                "Do not mention the terminal, command line, dark text window, "
                '"Question>" prompt, typed question, or previous helper answers. '
                "Answer only about the user's actual app, website, desktop, "
                "icon, message, or task outside the terminal.\n\n"
                "You may receive one or more screenshots in order from oldest "
                "to newest. Use the newest screenshot as the main view, and use "
                "earlier screenshots only to understand what changed."
            ),
        }
    ]

    for image_bytes in image_sequence:
        gemini_input.append(
            {
                "type": "image",
                "data": image_bytes_to_base64(image_bytes),
                "mime_type": "image/png",
            }
        )

    payload = {
        "model": model,
        "system_instruction": SCREEN_DESCRIPTION_SYSTEM_PROMPT,
        "input": gemini_input,
        "generation_config": {
            "max_output_tokens": max_tokens,
            "thinking_level": "low",
        },
    }

    request = Request(
        GEMINI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=build_gemini_headers(api_key),
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed with HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Gemini: {exc.reason}") from exc

    return extract_message_text(response_body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Take a screenshot and print a text description of the screen."
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEFAULT_PROMPT,
        help=f'Question to ask about the screen. Default: "{DEFAULT_PROMPT}"',
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        help="Vision-capable Gemini model to use. Also configurable with GEMINI_MODEL.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.environ.get("GEMINI_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        help="Maximum response tokens to request. Also configurable with GEMINI_MAX_TOKENS.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the screenshot under screenshots for debugging or audit.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "screenshots"),
        help="Directory used when --save is enabled.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Missing GEMINI_API_KEY. Set it before running this script.", file=sys.stderr)
        return 2

    if args.max_tokens < 1:
        print("Max tokens must be at least 1.", file=sys.stderr)
        return 2

    try:
        image_bytes = capture_screen()
        if args.save:
            saved_path = save_screenshot(image_bytes, Path(args.output_dir))
            print(f"Saved screenshot: {saved_path}", file=sys.stderr)

        description = describe_screen(
            args.question,
            image_bytes,
            args.model,
            api_key,
            args.max_tokens,
        )
        print(description)
        return 0
    except Exception as exc:
        print(f"Screen description failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
