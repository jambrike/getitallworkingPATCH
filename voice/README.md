# SILIA

Voice assistant prototype using Vosk speech recognition, OpenRouter for AI responses, and Google Text-to-Speech playback.

## Setup

Install the Node dependencies:

```bash
npm install vosk mic axios
```

Install the Python TTS dependencies:

```bash
python3 -m pip install gtts pygame
```

Download the Vosk English model:

```bash
bash scripts/install-vosk-model.sh
```

Set your OpenRouter key:

```bash
export OPENROUTER_API_KEY="your_key_here"
```

Run Silia:

```bash
node index.js
```

Say `click`, then ask your question. You can also say the question in one go, like `click what is two plus two`.
