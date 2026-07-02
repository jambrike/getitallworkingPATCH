# Old People Helper Overlay

A tiny Electron overlay app that floats above other apps on macOS. It shows a small mascot and a simple text box for reminders, notes, or helper prompts.

## Run With The Companion Service

From the workspace root, copy `.env.example` to `.env`, set `OPENAI_API_KEY`, install dependencies, then run:

```bash
./run-companion.sh
```

The overlay sends typed prompts to `http://127.0.0.1:8765/prompt`, speaks only the assistant's returned `say` text, and shows listening/thinking/speaking/error status.

## Run Overlay Only

```bash
npm install
npm start
```

## Terminal Text-to-Speech

The project also includes a standalone OpenAI text-to-speech CLI. It is separate from the Electron UI for now, so it can later be reused from the app without mixing UI and API code.

Install dependencies:

```bash
npm install
```

Set your API key:

```bash
# macOS/Linux
export OPENAI_API_KEY="your_api_key"

# Windows PowerShell
$env:OPENAI_API_KEY="your_api_key"
```

You can also put local environment values in a `.env` file at the project root. `.env` is ignored by git:

```bash
OPENAI_API_KEY=your_api_key
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
```

Speak text from the terminal:

```bash
node src/cli/say.js "Hello, this is a test."
```

Or use the package script:

```bash
npm run say -- "Hello, this is a test."
```

If no text argument is provided, the CLI asks for interactive input.

Optional configuration:

```bash
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
```

The TTS module streams the OpenAI audio response to a temporary WAV file, plays it with an OS-native player, then removes the file. On Windows it uses PowerShell `Media.SoundPlayer`; on macOS it uses `afplay`. This keeps playback isolated in `src/tts/playback.js` and leaves the structure ready for direct stream playback later.

Reusable functions are exported from `src/tts`:

```js
const { speak, streamSpeechToFile, preprocessText, playAudioFile } = require('./src/tts');
```

The Electron overlay now calls the local companion service from the main process when text is submitted with Enter. The renderer still does not call OpenAI directly.

## macOS Notes

- The overlay is frameless, transparent, and always on top.
- Drag it by the mascot or the top handle area.
- Use `Cmd+Q` to quit.
- It is configured to appear on all workspaces and sit above fullscreen apps where macOS allows it.
