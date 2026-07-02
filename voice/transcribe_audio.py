#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: transcribe_audio.py audio.wav", file=sys.stderr)
        return 2

    load_env_file(ROOT_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY.", file=sys.stderr)
        return 2

    audio_path = Path(sys.argv[1])
    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}", file=sys.stderr)
        return 2

    try:
        from openai import OpenAI
    except ImportError:
        print("Missing Python dependency: openai. Run python3 -m pip install -r agent/requirements.txt", file=sys.stderr)
        return 2

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

    with audio_path.open("rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            language=os.getenv("VOICE_LANGUAGE", "en"),
        )

    print(getattr(transcript, "text", "") or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
