# Local Companion App

This workspace now runs the five prototypes as one background companion:

- `overlay + TTS` collects typed prompts and speaks replies with OpenAI TTS.
- `voice` uses local Vosk for wake detection, then OpenAI transcription to clean up the actual prompt.
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

Click `Speak` in the overlay to record a short voice prompt directly. The overlay lights up while it is awake/listening, transcribes the clip with OpenAI, then sends the prompt to the same companion service.

For voice, say the wake word and question in the same phrase:

```text
grandson what am I looking at
```

Saying only `grandson` no longer opens a free-listening mode. This prevents random room audio or the assistant's own speech from becoming the next prompt.

Voice defaults to `VOICE_STT_MODE=hybrid`: Vosk listens cheaply for the wake word, then the last few seconds of microphone audio are transcribed with OpenAI for better accuracy in noisy rooms. Set `VOICE_STT_MODE=local` if you want Vosk-only recognition.

## Safety

The first version only automates the Playwright browser and safe file saves. It does not control arbitrary Mac apps. Risky actions involving passwords, payments, banking, messages, uploads, downloads, or other irreversible steps require explicit approval before they run.

## Email And Contacts

Grandson can remember contacts and send email through SMTP. Add these to `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
SMTP_FROM=your_email@gmail.com
SMTP_FROM_NAME=Grandson
```

Example prompts:

```text
remember Jane as jane@example.com
send Jane an email saying I will call tomorrow
```

Contacts are stored locally in `data/contacts.json`. Email sending always asks for approval before sending.
For example, `send Colm an email saying I will call tomorrow` should reply with the draft details and wait for you to say `yes` before it sends.
