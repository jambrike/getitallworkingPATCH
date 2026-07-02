#!/usr/bin/env python3
"""
Run a small terminal agent that keeps recent screenshots for context.

Usage:
    python screen_context_agent.py

Type a question, such as "what is happening?", and press Enter.
Type "quit" or "exit" to stop.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from collections import deque

from screen_describer import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    capture_screen,
    describe_screen_context,
)


DEFAULT_INTERVAL_SECONDS = 5.0
DEFAULT_BUFFER_SIZE = 3
STOP_COMMANDS = {"exit", "quit"}


class ScreenContextBuffer:
    def __init__(self, buffer_size: int) -> None:
        self._screenshots: deque[bytes] = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self.last_error: str | None = None

    def add(self, image_bytes: bytes) -> None:
        with self._lock:
            self._screenshots.append(image_bytes)
            self.last_error = None

    def snapshot(self) -> list[bytes]:
        with self._lock:
            return list(self._screenshots)

    def set_error(self, error: Exception) -> None:
        with self._lock:
            self.last_error = str(error)

    def count(self) -> int:
        with self._lock:
            return len(self._screenshots)


def capture_loop(
    buffer: ScreenContextBuffer,
    stop_event: threading.Event,
    interval_seconds: float,
) -> None:
    while not stop_event.is_set():
        try:
            buffer.add(capture_screen())
        except Exception as exc:
            buffer.set_error(exc)

        stop_event.wait(interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Keep a small rolling screenshot buffer, then answer typed questions "
            "using the recent screen context."
        )
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("SCREEN_AGENT_INTERVAL", DEFAULT_INTERVAL_SECONDS)),
        help="Seconds between background screenshots. Also configurable with SCREEN_AGENT_INTERVAL.",
    )
    parser.add_argument(
        "--buffer-size",
        type=int,
        default=int(os.environ.get("SCREEN_AGENT_BUFFER_SIZE", DEFAULT_BUFFER_SIZE)),
        help="Number of recent screenshots to keep in memory.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("VISION_MODEL", DEFAULT_MODEL),
        help="Vision-capable OpenAI model to use. Also configurable with VISION_MODEL.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.environ.get("VISION_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        help="Maximum response tokens to request. Also configurable with VISION_MAX_TOKENS.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[str, str] | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    if not args.model:
        print(
            "Missing vision model. Pass --model or set VISION_MODEL to a "
            "vision-capable model slug.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if args.max_tokens < 1:
        print("Max tokens must be at least 1.", file=sys.stderr)
        raise SystemExit(2)

    if args.interval <= 0:
        print("Interval must be greater than 0 seconds.", file=sys.stderr)
        raise SystemExit(2)

    if args.buffer_size < 1:
        print("Buffer size must be at least 1.", file=sys.stderr)
        raise SystemExit(2)

    return api_key, args.model


def wait_for_initial_screenshot(buffer: ScreenContextBuffer, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while buffer.count() == 0 and time.monotonic() < deadline:
        time.sleep(0.2)


def main() -> int:
    args = parse_args()
    credentials = validate_args(args)
    if credentials is None:
        print("Missing OPENAI_API_KEY. Set it before running this script.", file=sys.stderr)
        return 2

    api_key, model = credentials
    buffer = ScreenContextBuffer(args.buffer_size)
    stop_event = threading.Event()
    worker = threading.Thread(
        target=capture_loop,
        args=(buffer, stop_event, args.interval),
        daemon=True,
    )
    worker.start()
    wait_for_initial_screenshot(buffer)

    print("Screen context agent is running.")
    print(f"Keeping the last {args.buffer_size} screenshot(s) in memory.")
    print("Type a question and press Enter. Type 'quit' or 'exit' to stop.")

    try:
        while True:
            question = input("\nQuestion> ").strip()
            if not question:
                continue

            if question.lower() in STOP_COMMANDS:
                break

            screenshots = buffer.snapshot()
            if not screenshots:
                if buffer.last_error:
                    print(f"Could not capture the screen: {buffer.last_error}", file=sys.stderr)
                    continue
                screenshots = [capture_screen()]

            try:
                answer = describe_screen_context(
                    question,
                    screenshots,
                    model,
                    api_key,
                    args.max_tokens,
                )
                print(f"\n{answer}")
            except Exception as exc:
                print(f"Could not answer the question: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nStopping screen context agent.")
    finally:
        stop_event.set()
        worker.join(timeout=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
