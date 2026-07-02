#!/usr/bin/env python3
"""
Tiny decision layer for the MVP screen assistant.

Input: user prompt + screen description + context, usually from three files.
Output: what to say out loud and which allowed action(s) to run.

Usage:
  OPENAI_API_KEY=... python simple_agent.py \
    --user-file user.txt \
    --screen-file screen.txt \
    --context-file context.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_MODEL = os.environ.get("ASSISTANT_MODEL", "gpt-5.4-nano")

CAPABILITIES = [
    {"action": "open_url", "url": "https://example.com"},
    {"action": "search_web", "query": "beginner robotics kits Ireland"},
    {"action": "get_page_text"},
    {"action": "click_text", "text": "visible link or button text"},
    {"action": "type_text", "selector": "input[name='q']", "text": "hello"},
    {"action": "press_key", "key": "Enter"},
    {"action": "save_file", "filename": "result.md", "content": "markdown content here"},
    {"action": "ask_user", "question": "Should I continue?"},
    {"action": "done", "summary": "What was completed"},
]

JSON_SCHEMA: dict[str, Any] = {
    "name": "screen_assistant_decision",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["say", "run_in_background", "actions", "reasoning_summary"],
        "properties": {
            "say": {"type": "string"},
            "run_in_background": {"type": "boolean"},
            "reasoning_summary": {"type": "string"},
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


def load_system_prompt() -> str:
    return Path(__file__).with_name("agent_prompt.md").read_text(encoding="utf-8")


DEFAULT_USER_FILE = "user.txt"
DEFAULT_SCREEN_FILE = "screen.txt"
DEFAULT_CONTEXT_FILE = "context.txt"


def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def value_from_arg_or_file(
    value: str | None,
    file_path: str,
    label: str,
    value_flag: str,
    file_flag: str,
    required: bool = True,
) -> str:
    if value is not None:
        return value.strip()
    if Path(file_path).exists():
        return read_text_file(file_path)
    if required:
        raise SystemExit(
            f"Missing {label}. Provide {value_flag}, or create/pass a file with {file_flag}."
        )
    return ""


def build_input(user_prompt: str, screen_description: str, context: str) -> str:
    payload = {
        "user_prompt": user_prompt,
        "screen_description": screen_description,
        "context": context,
        "capabilities": CAPABILITIES,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def call_openai(system_prompt: str, user_input: str, model: str) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: install the OpenAI Python SDK with `pip install openai`."
        ) from exc

    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": JSON_SCHEMA["name"],
                "schema": JSON_SCHEMA["schema"],
                "strict": JSON_SCHEMA["strict"],
            }
        },
    )

    return json.loads(response.output_text)


def validate_actions(decision: dict[str, Any]) -> None:
    allowed = {item["action"] for item in CAPABILITIES}
    for action in decision.get("actions", []):
        name = action.get("action")
        if name not in allowed:
            raise ValueError(f"Model requested unsupported action: {name}")


def print_terminal(decision: dict[str, Any]) -> None:
    say = decision.get("say", "")
    actions = decision.get("actions", [])
    run_in_background = decision.get("run_in_background", False)

    print("SAY_OUTLOUD:")
    print(say if say else "(say nothing)")
    print()
    print("RUN_IN_BACKGROUND:")
    print("yes" if run_in_background else "no")
    print()
    print("ACTIONS:")
    print(json.dumps(actions, ensure_ascii=True, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-prompt")
    parser.add_argument("--screen-description")
    parser.add_argument("--context")
    parser.add_argument("--user-file", default=DEFAULT_USER_FILE)
    parser.add_argument("--screen-file", default=DEFAULT_SCREEN_FILE)
    parser.add_argument("--context-file", default=DEFAULT_CONTEXT_FILE)
    parser.add_argument("--format", choices=["terminal", "json"], default="terminal")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    user_prompt = value_from_arg_or_file(
        args.user_prompt,
        args.user_file,
        "user prompt",
        "--user-prompt",
        "--user-file",
    )
    screen_description = value_from_arg_or_file(
        args.screen_description,
        args.screen_file,
        "screen description",
        "--screen-description",
        "--screen-file",
    )
    context = value_from_arg_or_file(
        args.context,
        args.context_file,
        "context",
        "--context",
        "--context-file",
        required=False,
    )

    system_prompt = load_system_prompt()
    user_input = build_input(user_prompt, screen_description, context)
    decision = call_openai(system_prompt, user_input, args.model)
    validate_actions(decision)

    if args.format == "json":
        print(json.dumps(decision, ensure_ascii=True, indent=2))
    else:
        print_terminal(decision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
