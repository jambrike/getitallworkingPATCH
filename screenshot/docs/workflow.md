# Screen Description Workflow

The screenshot workflow turns a prompt such as `what is happening?` into a calm, plain-language description of the current screen.

## Integrated Flow

1. Overlay or Vosk sends a prompt to the companion service.
2. The service reads the recent in-memory screenshot buffer.
3. OpenAI vision describes the screen briefly.
4. The decision layer combines the user prompt, screen description, and recent memory.
5. The overlay or voice client speaks the final answer with OpenAI TTS.

## Standalone Flow

```bash
python screen_describer.py "what is happening?"
python screen_context_agent.py
```

Both modes use `OPENAI_API_KEY`, `VISION_MODEL`, and `VISION_MAX_TOKENS`.
