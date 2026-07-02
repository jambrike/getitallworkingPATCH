# Local Companion App

This workspace now runs the five prototypes as one background companion:

- `overlay + TTS` collects typed prompts and speaks replies with OpenAI TTS.
- `voice` keeps Vosk wake-word speech recognition local.
- `screenshot` keeps a small in-memory screen buffer and describes it with OpenAI vision.
- `agent` runs the local FastAPI companion service and decision layer.
- `features/laptop-agent-mvp` provides safe browser/file actions.

See `FEATURES.md` for the full feature list, limitations, and next planned improvements.

## Setup

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Install the Python dependencies:

```bash
python3 -m pip install -r agent/requirements.txt
python3 -m pip install -r features/laptop-agent-mvp/requirements.txt
python3 -m playwright install chromium
```

Install the Node dependencies:

```bash
(cd "overlay + TTS" && npm install)
(cd voice && nvm use 16 && npm install)
```

Install the Vosk model if you want voice input:

```bash
(cd voice && bash scripts/install-vosk-model.sh)
```

## Run

Start the companion service and overlay:

```bash
./run-companion.sh
```

Start voice input too:

```bash
START_VOICE=1 ./run-companion.sh
```

The service listens on `http://127.0.0.1:8765`. The overlay and voice listener both send prompts there. Screenshots are kept in memory and the newest screenshot is resized before being sent to OpenAI only when a prompt is received.

For voice, say the wake word and question in the same phrase:

```text
grandson what am I looking at
```

Saying only `grandson` no longer opens a free-listening mode. This prevents random room audio or the assistant's own speech from becoming the next prompt.

## Safety

The first version only automates the Playwright browser and safe file saves. It does not control arbitrary Mac apps. Risky actions involving passwords, payments, banking, messages, uploads, downloads, or other irreversible steps require explicit approval before they run.
