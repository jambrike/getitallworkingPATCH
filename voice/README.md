# SILIA

Voice assistant prototype using local Vosk wake detection. By default it sends the recent wake-word audio clip to OpenAI transcription for a cleaner prompt, then sends that prompt to the local companion service. Speech playback uses the shared OpenAI TTS module in `overlay + TTS`.

## Setup

Install the Node dependencies:

```bash
nvm use 16
npm install
```

The Vosk npm package uses an older native binding, so this repo should run on Node 16.

Download the Vosk English model:

```bash
bash scripts/install-vosk-model.sh
```

Set your OpenAI key in the workspace root `.env`, then start the companion service:

```bash
cd ..
./run-companion.sh
```

Run Silia separately, or start it with the root launcher by setting `START_VOICE=1`:

```bash
node index.js
```

Say `grandson` and your question in one phrase:

```text
grandson what is two plus two
```

Saying only `grandson` will not make it listen to the next random sentence. This keeps room noise and the assistant's own spoken reply from becoming a prompt.

## Accuracy Modes

The default mode is:

```env
VOICE_STT_MODE=hybrid
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
VOICE_TRANSCRIBE_LOOKBACK_MS=8000
```

In hybrid mode, Vosk only has to catch the wake word. The actual question is transcribed from the recent audio buffer with OpenAI, which is usually much better in a crowd. For fully local recognition, set `VOICE_STT_MODE=local`.
