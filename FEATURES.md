# Companion Feature List

## Working Features

- Floating Electron overlay for typed prompts.
- Overlay reply bubble that shows the latest assistant answer above the input.
- Overlay Send and Speak buttons, with Enter as a send shortcut.
- Spoken replies using OpenAI TTS.
- Hybrid voice listener with local Vosk wake detection and optional OpenAI transcription cleanup.
- In-memory screenshot buffer for screen context.
- Local FastAPI companion service at `http://127.0.0.1:8765`.
- `GET /health` for service status.
- `POST /prompt` for overlay and voice prompts.
- One-call multimodal OpenAI decision path using prompt, screenshot, memory, and available actions.
- Compact local memory for recent intent, results, unresolved tasks, and action status.
- Context controls: `reset context`, `forget that`, and `cancel`.
- Browser/file actions through Playwright:
  - search the web
  - open a URL
  - open common sites like YouTube or Netflix directly from commands such as "open YouTube"
  - open arbitrary website names by guessing the normal `.com` address, such as "open Amazon"
  - run up to five ordinary browser/file actions from one prompt
  - read visible page text
  - click visible text
  - click a clear screen coordinate inside the Playwright browser
  - type into a selector
  - press a key
  - scroll the browser page
  - wait briefly for pages or menus to load
  - save a file
- Safety approval gate for high-risk actions involving passwords, payments, banking, sending, deleting, uploads, downloads, purchases, installs, private codes, account recovery, and similar irreversible steps.
- Root launcher:

```bash
START_VOICE=1 ./run-companion.sh
```

## Current Limitations

- Desktop-wide control is not enabled; clicks and scrolling happen inside the Playwright browser window, and file saves stay inside the feature-agent outputs folder.
- Voice wake detection still uses local Vosk, so very loud rooms can still miss the wake word.
- After the wake word is detected, the recent audio clip is transcribed with OpenAI by default for better noisy-room accuracy.
- Voice only responds when the wake word and question are in the same phrase, such as `grandson what am I looking at`.
- macOS Screen Recording and Microphone permissions must be granted manually.
- The overlay and voice clients both speak through local audio, so headphones or low speaker volume will improve voice accuracy.

## Next Planned Improvements

- Add push-to-talk recording in the overlay for very loud rooms where wake-word detection is unreliable.
- Pause or duck microphone input at the system level while TTS is playing.
- Add a visible microphone on/off toggle in the overlay.
- Add desktop action support only after a stronger approval and safety design.
- Add a small local settings screen for model choice, voice, screenshot interval, and wake word.
- Add lightweight automated tests around `/prompt`, memory controls, and voice wake-word parsing.
