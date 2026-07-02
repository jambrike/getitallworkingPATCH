# Screen Description Workflow

This workflow turns a plain question such as `what is happening?` into a calm, plain-language explanation of the current screen for an older adult. It can also answer task questions such as `how do I log into my bank account?` or `how can I send my grandson a picture?`, and clarification questions such as `is it this icon I should press?`.

## Files

- `screen_describer.py`: captures the screen and asks a vision-capable model to explain it in elderly-friendly language.
- `screen_context_agent.py`: keeps a small rolling screenshot buffer and answers typed questions using recent screen context.
- `background_agent.md`: explains how to use the background context prototype.
- `usage.md`: gives step-by-step instructions for running the script.
- `workflow.md`: explains the operating flow.
- `ruleset.md`: defines behavior and safety rules for the script and model prompt.
- `approach.txt`: explains the design approach in plain language.

Only documentation files live in `docs/`. Runnable scripts live one level above this folder.

For command-by-command setup and usage instructions, read `usage.md`.

For the background context prototype, read `background_agent.md`.

## Setup

From `image_processing_demo`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
export GEMINI_API_KEY="your_gemini_api_key_here"
export GEMINI_MODEL="gemini-3.1-flash-lite"
```

Optional:

```bash
export GEMINI_MAX_TOKENS="700"
```

The script defaults to `gemini-3.1-flash-lite`. To use a different vision-capable Gemini model, set `GEMINI_MODEL` or pass `--model`. You can browse models at `https://ai.google.dev/gemini-api/docs/models`.

## Running It

One-shot mode:

```bash
python screen_describer.py "what is happening?"
```

Background context mode:

```bash
python screen_context_agent.py
```

If Gemini says you requested too many tokens, lower the response cap:

```bash
python screen_describer.py "what is happening?" --max-tokens 200
```

Optional debug/audit screenshot:

```bash
python screen_describer.py "what is happening?" --save
```

Saved screenshots go to `screenshots/`.

## Step-by-Step Flow

One-shot flow:

1. A person types a question, usually `what is happening?`.
2. The script captures the current primary screen as a PNG image.
3. The image is encoded as inline base64 PNG data.
4. The question and image are sent to the Gemini Interactions API using a vision-capable model.
5. The model returns a concise text description of visible screen activity, capped by `--max-tokens`.
6. The script prints only that description to standard output.

Background context flow:

1. The agent starts and captures screenshots every few seconds.
2. It keeps only a small rolling buffer of recent screenshots in memory.
3. A person types a question into the terminal.
4. The recent screenshots are sent to Gemini, oldest to newest.
5. The model uses the newest screenshot as the main view and earlier screenshots only to understand what changed.
6. The model is instructed to ignore the terminal running the helper unless the user asks about it.
7. The answer is printed in brief, elderly-friendly language.

## Expected Output

The output should explain the screen briefly and include a safe next step:

```text
This looks like a sign-in page, which is where a website checks that it is really you. If this is a website you trust and meant to use, you can continue carefully. If you did not expect this page, do not enter your password yet.
```

For task questions, the output should coach the user through the next few steps:

```text
You are on your browser start page, so you are not on your bank website yet. Type your bank's official website address into the address bar. Do not use a link from an email or text message. After the bank page opens, ask again before entering any private details.
```

## Response Style

The model is instructed to:

- Use short, respectful, plain-language sentences.
- Avoid technical words when simpler wording works.
- Answer in a brief, conversational way by default.
- Explain basic technology terms clearly, without assuming the user already knows them.
- Describe only the visible detail needed for the next step.
- For task questions, give the next one to three steps from the visible screen.
- For clarification questions, identify what the user probably means before recommending an action.
- Be extra careful around passwords, banking, payments, urgent warnings, remote access, and suspicious popups.

## macOS Permission Note

On macOS, the terminal app may need Screen Recording permission before screenshots work:

`System Settings -> Privacy & Security -> Screen & System Audio Recording`

After granting permission, restart the terminal and run the script again.
