# laptop-agent-mvp

A small local AI-powered browser agent MVP. In the integrated companion app, this repo provides the browser/file action executor behind `agent/companion_service.py`.

This is browser-only. It does not control your desktop outside Playwright.

## Install

```bash
cd laptop-agent-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Configure

Create a `.env` file:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-nano
```

The root `.env.example` is the preferred shared setup for the full five-repo companion app.

## Run

```bash
python main.py
```

When prompted, enter a task:

```text
What should the agent do? > Find 5 beginner robotics kit suppliers and save a comparison as robotics_kits.md
```

## Example Tasks

- `Find 5 beginner robotics kit suppliers and save a comparison as robotics_kits.md`
- `Research parts for a €120 robotics kit and save a BOM`
- `Find Irish electronics suppliers and create a supplier list`

## Supported Actions

The model must respond with one JSON action at a time:

- Open a URL
- Search the web
- Read visible page text
- Click visible text
- Type text into a selector
- Press a keyboard key
- Save a file under `outputs/`
- Ask the user a question
- Finish with a summary

## Safety Limitations

Before executing an action, the agent checks for risky words such as `buy`, `purchase`, `checkout`, `payment`, `send`, `email`, `message`, `submit`, `delete`, `install`, `sudo`, `password`, `login`, `post`, `upload`, and `download`.

If a risky word appears, the agent prints the action and asks:

```text
Risky action detected. Allow? y/n >
```

Only `y` allows the action. Anything else blocks it and records the blocked action in history.

The system prompt also tells the model not to spend money, submit forms, send messages, delete files, install software, access password managers, or perform irreversible actions without explicit confirmation.

This is still an MVP. Watch the visible browser, avoid sensitive accounts, and do not rely on it for high-risk workflows.

## Next-Step Ideas

- Add screenshot-based desktop control
- Add an approval queue
- Add local memory
- Add Gmail and Calendar integrations later
