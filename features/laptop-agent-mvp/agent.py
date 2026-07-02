from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from browser_tools import BrowserSession, save_output_file
from safety import action_has_risk


MAX_STEPS = 20
PAGE_TEXT_LIMIT = 6000
HISTORY_LIMIT = 12

SUPPORTED_ACTIONS = {
    "open_url",
    "search_web",
    "get_page_text",
    "click_text",
    "type_text",
    "press_key",
    "save_file",
    "ask_user",
    "done",
}

SYSTEM_PROMPT = """
You are a local browser agent.
You can browse, read pages, compare information, draft content, and save files.
You must respond with JSON only.
Choose exactly one action at a time.
Do not spend money.
Do not submit forms.
Do not send emails or messages.
Do not delete files.
Do not install software.
Do not access password managers.
Ask for explicit user confirmation before irreversible or risky actions.
Prefer safe research, drafting, and file creation.
When saving research, use clean Markdown with title, table, short notes, and source URLs if available.

Supported actions:
{"action":"open_url","url":"https://example.com"}
{"action":"search_web","query":"beginner robotics kits Ireland"}
{"action":"get_page_text"}
{"action":"click_text","text":"visible link or button text"}
{"action":"type_text","selector":"input[name='q']","text":"hello"}
{"action":"press_key","key":"Enter"}
{"action":"save_file","filename":"result.md","content":"markdown content here"}
{"action":"ask_user","question":"Should I continue?"}
{"action":"done","summary":"What was completed"}

Return one JSON object only. Do not wrap it in Markdown.
""".strip()


class BrowserAgent:
    def __init__(self, outputs_dir: Path, console: Console | None = None) -> None:
        self.outputs_dir = outputs_dir
        self.console = console or Console()
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("OPENAI_MODEL", os.getenv("ASSISTANT_MODEL", "gpt-5.4-nano"))
        self.history: list[dict[str, Any]] = []

    def run(self, task: str) -> None:
        self.history.append({"type": "task", "content": task})
        self.console.print(Panel.fit(task, title="Task", border_style="cyan"))

        with BrowserSession() as browser:
            for step in range(1, MAX_STEPS + 1):
                page_text = self._safe_page_text(browser)
                action = self._choose_action(task, page_text)

                self.console.rule(f"[bold]Step {step}[/bold]")
                self._print_action(action)

                if not self._confirm_if_risky(action):
                    self.history.append({"type": "blocked_action", "action": action})
                    self.console.print("[yellow]Blocked by user. Continuing.[/yellow]")
                    continue

                try:
                    result = self._execute_action(browser, action, page_text)
                except Exception as exc:
                    result = f"Action failed: {exc}"
                    self.history.append(
                        {"type": "error", "action": action, "error": str(exc)}
                    )
                    self.console.print(f"[red]{result}[/red]")
                    continue

                if action.get("action") == "done":
                    self.console.print(Panel.fit(result, title="Done", border_style="green"))
                    return

                self.console.print(f"[green]{result}[/green]")

        summary = f"Step limit reached after {MAX_STEPS} steps."
        self.history.append({"type": "summary", "content": summary})
        self.console.print(Panel.fit(summary, title="Stopped", border_style="yellow"))

    def _choose_action(self, task: str, page_text: str) -> dict[str, Any]:
        messages = self._messages(task, page_text)
        raw = self._call_model(messages)
        try:
            return self._parse_action(raw)
        except ValueError:
            self.console.print("[red]Invalid JSON from model:[/red]")
            self.console.print(raw)
            retry_messages = messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": "That was invalid. Respond again with exactly one valid JSON object.",
                },
            ]
            raw = self._call_model(retry_messages)
            return self._parse_action(raw)

    def _messages(self, task: str, page_text: str) -> list[dict[str, str]]:
        visible_context = {
            "task": task,
            "current_page_text": page_text[:PAGE_TEXT_LIMIT],
            "recent_history": self.history[-HISTORY_LIMIT:],
        }
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(visible_context, ensure_ascii=False),
            },
        ]

    def _call_model(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _parse_action(self, raw: str) -> dict[str, Any]:
        action = json.loads(raw)
        if not isinstance(action, dict):
            raise ValueError("Model response must be a JSON object.")
        name = action.get("action")
        if name not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported action: {name}")
        return action

    def _print_action(self, action: dict[str, Any]) -> None:
        rendered = json.dumps(action, indent=2, ensure_ascii=False)
        syntax = Syntax(rendered, "json", theme="monokai", word_wrap=True)
        self.console.print(Panel(syntax, title="Chosen action", border_style="blue"))

    def _confirm_if_risky(self, action: dict[str, Any]) -> bool:
        if not action_has_risk(action):
            return True
        answer = input("Risky action detected. Allow? y/n > ").strip().lower()
        return answer == "y"

    def _safe_page_text(self, browser: BrowserSession) -> str:
        try:
            return browser.get_page_text(limit=PAGE_TEXT_LIMIT)
        except Exception:
            return ""

    def _execute_action(
        self, browser: BrowserSession, action: dict[str, Any], page_text: str
    ) -> str:
        name = action["action"]

        if name == "open_url":
            result = browser.open_url(str(action["url"]))
        elif name == "search_web":
            result = browser.search_web(str(action["query"]))
        elif name == "get_page_text":
            snippet = browser.get_page_text(limit=PAGE_TEXT_LIMIT)
            self.history.append({"type": "page_text", "content": snippet})
            result = f"Read {len(snippet)} characters from the page."
        elif name == "click_text":
            result = browser.click_text(str(action["text"]))
        elif name == "type_text":
            result = browser.type_text(str(action["selector"]), str(action["text"]))
        elif name == "press_key":
            result = browser.press_key(str(action["key"]))
        elif name == "save_file":
            path = save_output_file(
                self.outputs_dir,
                str(action.get("filename") or "output.md"),
                str(action.get("content") or ""),
            )
            self.history.append({"type": "saved_file", "path": str(path)})
            result = f"Saved {path}"
        elif name == "ask_user":
            answer = input(f"{action['question']} > ")
            self.history.append(
                {
                    "type": "user_answer",
                    "question": action["question"],
                    "answer": answer,
                }
            )
            result = "User answered."
        elif name == "done":
            summary = str(action.get("summary", "Finished."))
            self.history.append({"type": "done", "summary": summary})
            return summary
        else:
            raise ValueError(f"Unsupported action: {name}")

        self.history.append({"type": "action", "action": action, "result": result})
        if page_text:
            self.history.append({"type": "page_text_snippet", "content": page_text[:1000]})
        return result
