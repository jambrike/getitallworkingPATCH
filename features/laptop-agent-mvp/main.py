from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from agent import BrowserAgent


def main() -> None:
    load_dotenv()
    console = Console()

    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            "[red]Missing API key. Set OPENAI_API_KEY in the root .env.[/red]"
        )
        raise SystemExit(1)

    task = input("What should the agent do? > ").strip()
    if not task:
        console.print("[yellow]No task provided.[/yellow]")
        raise SystemExit(0)

    outputs_dir = Path(__file__).parent / "outputs"
    agent = BrowserAgent(outputs_dir=outputs_dir, console=console)
    agent.run(task)


if __name__ == "__main__":
    main()
