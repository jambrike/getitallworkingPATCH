# How to Use the Screen Describer

The screenshot repo captures the current screen and asks an OpenAI vision-capable model for a short, older-adult-friendly explanation.

## Setup

From the workspace root, prefer the shared setup:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
python3 -m pip install -r screenshot/requirements.txt
```

Optional settings:

```bash
VISION_MODEL=gpt-5.4-nano
VISION_MAX_TOKENS=300
SCREEN_AGENT_INTERVAL=5
SCREEN_AGENT_BUFFER_SIZE=3
```

## One-Shot Mode

```bash
cd screenshot
python screen_describer.py "what is happening?"
```

Save a screenshot only when debugging:

```bash
python screen_describer.py "what is happening?" --save
```

## Background Buffer Mode

```bash
cd screenshot
python screen_context_agent.py
```

This keeps the latest few screenshots in memory and sends them to OpenAI only when you ask a question.

## macOS Permission Note

If screenshot capture fails, grant Screen Recording permission to your terminal app:

`System Settings -> Privacy & Security -> Screen & System Audio Recording`

Then restart the terminal and try again.

## Privacy Reminder

Screenshots may contain private information. They are not saved by default, and the background buffer is in memory only.
