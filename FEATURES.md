# Companion Feature List

## Working Features

- Floating Electron overlay for typed prompts.
- Overlay reply bubble that shows the latest assistant answer above the input.
- Overlay Send and Speak buttons, with Enter as a send shortcut.
- Spoken replies using OpenAI TTS.
- Local Vosk voice listener with the `grandson + question` wake phrase.
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
  - open common sites like YouTube directly from commands such as "open YouTube"
  - read visible page text
  - click visible text
  - type into a selector
  - press a key
  - save a file
- Safety approval gate for risky actions involving passwords, payments, banking, sending, deleting, uploads, downloads, purchases, and similar irreversible steps.
- Root launcher:

```bash
START_VOICE=1 ./run-companion.sh
```

## Current Limitations

- Desktop-wide control is not enabled; actions are limited to the Playwright browser and safe file saves.
- Voice recognition uses local Vosk and may mishear noisy rooms.
- Voice only responds when the wake word and question are in the same phrase, such as `grandson what am I looking at`.
- macOS Screen Recording and Microphone permissions must be granted manually.
- The overlay and voice clients both speak through local audio, so headphones or low speaker volume will improve voice accuracy.

## Next Planned Improvements

- Pause or duck microphone input at the system level while TTS is playing.
- Add a visible microphone on/off toggle in the overlay.
- Add desktop action support only after a stronger approval and safety design.
- Add a small local settings screen for model choice, voice, screenshot interval, and wake word.
- Add lightweight automated tests around `/prompt`, memory controls, and voice wake-word parsing.
