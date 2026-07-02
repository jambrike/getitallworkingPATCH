# Background Screen Context Agent

`screen_context_agent.py` keeps a small rolling memory of recent screenshots while it runs. In the integrated companion app, `agent/companion_service.py` imports the same buffer and capture loop.

## How It Works

1. A background thread captures screenshots every few seconds.
2. Only the latest few screenshots are kept in memory.
3. Screenshots are sent to OpenAI only after the user asks a question through overlay or voice.
4. The newest screenshot is treated as the main view. Earlier screenshots help explain what changed.

## Settings

```bash
OPENAI_API_KEY=your_openai_api_key_here
VISION_MODEL=gpt-5.4-nano
VISION_MAX_TOKENS=300
SCREEN_AGENT_INTERVAL=5
SCREEN_AGENT_BUFFER_SIZE=3
```

## Privacy Notes

The prototype watches the screen only while the companion service is running. It does not save screenshots by default. Closing the service clears the in-memory buffer.

For an elderly-assistance product, keep a visible on/off state, a pause button, and clear consent around screen watching.
