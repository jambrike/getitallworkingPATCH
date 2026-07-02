# Local Companion App

This workspace now runs the five prototypes as one background companion:

- `overlay + TTS` collects typed prompts and speaks replies with OpenAI TTS.
- `voice` keeps Vosk wake-word speech recognition local.
- `screenshot` keeps a small in-memory screen buffer and describes it with OpenAI vision.
- `agent` runs the local FastAPI companion service and decision layer.
- `features/laptop-agent-mvp` provides safe browser/file actions.

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


## Windows 10 Setup

Run these commands from PowerShell in the repo root:

```powershell
Copy-Item .env.example .env
notepad .env
```

Add your `OPENAI_API_KEY` in `.env`, then install dependencies:

```powershell
py -3 -m pip install -r agent/requirements.txt
py -3 -m pip install -r screenshot/requirements.txt
py -3 -m pip install -r features/laptop-agent-mvp/requirements.txt
py -3 -m playwright install chromium

Set-Location "overlay + TTS"
npm install
Set-Location ..
```

Start the companion service and overlay:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-companion.ps1
```

Start voice too:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-companion.ps1 -StartVoice
```

Screenshot notes for Windows:

- The screenshot module uses Pillow `ImageGrab` and captures all monitors by default on Windows.
- To capture only the primary screen, set `SCREENSHOT_ALL_SCREENS=0` in `.env`.
- Run it from your normal signed-in desktop session. Windows screen capture will not work correctly from a background service or a different desktop session.

Test screenshot capture by saving a screenshot locally:

```powershell
py -3 screenshot\screen_describer.py --save "what is on screen?"
```
## macOS/Linux Run

Start the companion service and overlay:

```bash
./run-companion.sh
```

Start voice input too:

```bash
START_VOICE=1 ./run-companion.sh
```

The service listens on `http://127.0.0.1:8765`. The overlay and voice listener both send prompts there. Screenshots are kept in memory and are sent to OpenAI only when a prompt is received.

## Safety

The first version only automates the Playwright browser and safe file saves. It does not control arbitrary Mac apps. Risky actions involving passwords, payments, banking, messages, uploads, downloads, or other irreversible steps require explicit approval before they run.


