# SILIA

Voice assistant prototype using local Vosk speech recognition. AI responses now come from the local companion service, and speech playback uses the shared OpenAI TTS module in `overlay + TTS`.

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

Say `grandson`, then ask your question. You can also say the question in one go, like `grandson what is two plus two`.
