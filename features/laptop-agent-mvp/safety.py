from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RISKY_WORDS = {
    "buy",
    "purchase",
    "checkout",
    "payment",
    "send",
    "email",
    "message",
    "submit",
    "delete",
    "install",
    "sudo",
    "password",
    "post",
    "upload",
    "download",
    "transfer",
    "card",
    "passcode",
    "recovery",
}


def action_has_risk(action: dict[str, Any]) -> bool:
    """Return True when any action field contains a configured risky word."""
    text = json.dumps(action, ensure_ascii=False).lower()
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in RISKY_WORDS)


def safe_output_path(outputs_dir: Path, filename: str | None) -> Path:
    """Return a path guaranteed to stay inside outputs_dir."""
    outputs_dir = outputs_dir.resolve()
    raw_name = filename or "output.md"
    cleaned = Path(raw_name).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", cleaned)
    cleaned = cleaned or "output.md"

    candidate = (outputs_dir / cleaned).resolve()
    try:
        candidate.relative_to(outputs_dir)
    except ValueError:
        candidate = outputs_dir / "output.md"
    return candidate
