# Background Screen Context Agent

`screen_context_agent.py` is a prototype that keeps a small rolling memory of recent screenshots while it runs. When a person types a question into the terminal, the agent sends the recent screenshots to Gemini and prints an elderly-friendly answer.

This is different from `screen_describer.py`:

- `screen_describer.py` takes one screenshot only when you run the command.
- `screen_context_agent.py` keeps taking screenshots in the background while the terminal program is open.

## How It Works

1. The agent starts a background capture loop.
2. Every few seconds, it captures the current screen.
3. It keeps only the latest few screenshots in memory.
4. Older screenshots are automatically replaced.
5. When the user types a question, the recent screenshots are sent to Gemini.
6. The model answers briefly in elderly-friendly language, usually with one clear next step.

The newest screenshot is treated as the main view. Earlier screenshots are used only to understand what may have changed.

The terminal window running this agent may still appear in screenshots. The prompt tells the model to treat that terminal as invisible and not mention the command line, dark text window, `Question>` prompt, typed question, or previous helper answers. It should focus on the app, website, icon, message, desktop item, or task outside the terminal. This is not the same as removing the terminal from the screenshot; it is a model instruction.

## Setup

From `image_processing_demo`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
export GEMINI_API_KEY="your_gemini_api_key_here"
export GEMINI_MODEL="gemini-3.1-flash-lite"
```

## Run the Agent

```bash
python screen_context_agent.py
```

Then type a question:

```text
Question> what is happening?
```

Other useful questions:

```text
Question> what should I do next?
Question> does this look safe?
Question> why is this not working?
Question> what changed?
Question> how do I send my grandson a picture?
Question> is it this icon I should press?
```

To stop:

```text
Question> quit
```

You can also press `Control-C`.

## Optional Settings

Capture every 3 seconds:

```bash
python screen_context_agent.py --interval 3
```

Keep the last 5 screenshots in memory:

```bash
python screen_context_agent.py --buffer-size 5
```

Limit answer length:

```bash
python screen_context_agent.py --max-tokens 200
```

Use a different model for one run:

```bash
python screen_context_agent.py --model "your-model-slug"
```

Environment variable alternatives:

```bash
export SCREEN_AGENT_INTERVAL="5"
export SCREEN_AGENT_BUFFER_SIZE="3"
export GEMINI_MAX_TOKENS="700"
```

## Privacy Notes

This prototype watches the screen while it is running. That means it may capture private information such as emails, names, health details, messages, passwords, payment pages, or banking pages.

Current prototype privacy behavior:

- Screenshots are kept in memory only.
- Screenshots are not saved to disk by default.
- Only the recent buffer is sent when the user asks a question.
- Closing the program clears the in-memory buffer.

Important limits:

- Screenshots are still sent to Gemini when a question is answered.
- The terminal running the agent may still be visible in screenshots, even though the model is told to ignore it.
- The prototype does not yet detect or blur sensitive information.
- The prototype does not yet pause automatically on banking, payment, or password screens.
- The prototype should not run secretly or without a clear user-facing indicator.

For an elderly-assistance product, the next safer version should include a visible on/off state, a pause button, and stronger privacy controls before background watching is enabled by default.

## Common Problems

If screenshot capture fails on macOS, grant Screen Recording permission to your terminal app:

`System Settings -> Privacy & Security -> Screen & System Audio Recording`

Then restart the terminal and try again.

If Gemini says you requested too many tokens, lower the response cap:

```bash
python screen_context_agent.py --max-tokens 200
```

If the answer does not include enough recent context, try a shorter interval or larger buffer:

```bash
python screen_context_agent.py --interval 3 --buffer-size 5
```
