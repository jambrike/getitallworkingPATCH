# Grandson Local Companion App

Grandson is a local desktop companion prototype for helping older adults use
their computer with less stress. It provides a small floating overlay, accepts
typed or spoken questions, looks at recent screen context, gives plain-language
guidance, and can perform a limited set of safer browser/file actions after
approval.

The goal is not to replace a relative, carer, or trusted helper. The goal is to
make everyday computer moments easier: understanding what is on screen, knowing
which button to press next, checking whether something looks suspicious, or
drafting a simple email.

See `FEATURES.md` for the full feature list, current limitations, and next
planned improvements.

## What This Repo Contains

This workspace runs five prototypes together as one background companion:

- `overlay + TTS` collects typed prompts in a floating Electron overlay and
  speaks replies with OpenAI TTS.
- `voice` uses local Vosk for wake detection, then OpenAI transcription to clean
  up the actual prompt.
- `screenshot` keeps a small in-memory screen buffer and describes it with
  OpenAI vision when a prompt needs screen context.
- `agent` runs the local FastAPI companion service and decision layer.
- `features/laptop-agent-mvp` provides safe browser/file actions.

The companion service listens on `http://127.0.0.1:8765`. The overlay and voice
listener both send prompts there. Screenshots are kept in memory, and the newest
screenshot is resized before being sent to OpenAI only when a prompt is
received.

## Requirements

- macOS for the current overlay/app-wrapper workflow.
- Python 3.
- Node.js for the Electron overlay and voice listener.
- Node 16 for the Vosk voice package.
- An OpenAI API key.
- macOS Screen Recording permission for screen context.
- macOS Microphone permission for voice input.

## Setup

Create a local environment file:

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

## How To Run

Start the companion service and overlay:

```bash
./run-companion.sh
```

Start the companion service, overlay, and voice input:

```bash
START_VOICE=1 ./run-companion.sh
```

Once it is running, use the floating overlay to type a question such as:

```text
what am I looking at?
what should I do next?
is this safe?
is this the right icon?
```

Click `Speak` in the overlay to record a short voice prompt directly. The
overlay lights up while it is awake/listening, transcribes the clip with OpenAI,
then sends the prompt to the same companion service.

## Voice Wake Word

For hands-free voice, say the wake word and question in the same phrase:

```text
grandson what am I looking at
```

Saying only `grandson` no longer opens a free-listening mode. This prevents
random room audio or the assistant's own speech from becoming the next prompt.

Voice defaults to `VOICE_STT_MODE=hybrid`: Vosk listens cheaply for the wake
word, then the last few seconds of microphone audio are transcribed with OpenAI
for better accuracy in noisy rooms.

Set `VOICE_STT_MODE=local` if you want Vosk-only recognition.

## Mac App Launcher

Install a clickable macOS app wrapper:

```bash
scripts/install-mac-app.sh
```

This creates `/Applications/Grandson.app`. Open it from Finder or drag it to the
Dock. It starts Grandson with voice enabled and writes logs to:

```text
~/Library/Logs/Grandson/companion.log
```

The app icon uses `assets/Grandson.icns`; rerun the installer after changing
that icon.

## What Grandson Can Do

Grandson can:

- explain what is visible on screen
- answer questions typed into the overlay
- answer short voice prompts
- speak replies aloud
- remember recent context
- search or open web pages through the Playwright browser
- read visible page text
- click visible text inside the Playwright browser
- type into browser fields
- scroll browser pages
- save files inside the feature-agent outputs folder
- remember contacts by name and email
- draft and send email through SMTP after approval

Desktop-wide control is not enabled in this version. Clicks and scrolling happen
inside the Playwright browser window, and file saves stay inside the
feature-agent outputs folder.

## Safety

The first version only automates the Playwright browser and safe file saves. It
does not control arbitrary Mac apps.

Risky actions involving passwords, payments, banking, messages, uploads,
downloads, purchases, installs, private codes, account recovery, or other
irreversible steps require explicit approval before they run.

Email sending also always asks for approval before sending.

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

Contacts are stored locally in `data/contacts.json`.

For example, `send Colm an email saying I will call tomorrow` should reply with
the draft details and wait for you to say `yes` before it sends.

## Troubleshooting

- If the overlay cannot answer, check that `./run-companion.sh` is still
  running.
- If screen descriptions are missing, check macOS Screen Recording permission.
- If voice does not work, check Microphone permission and confirm the Vosk model
  is installed.
- If wake detection is unreliable in a loud room, use the overlay `Speak` button
  or type the prompt.
- If email does not send, check the SMTP values in `.env`. Gmail users should
  use an app password.
