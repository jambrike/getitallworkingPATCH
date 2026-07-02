# How to Use the Screen Describer

This guide explains how to run `screen_describer.py` from the command line. For the background context prototype, read `background_agent.md`.

## 1. Open the Project Folder

In a terminal, go to the project folder:

```bash
cd /Users/beatricecesonyte/Desktop/old_heyclicky/image_processing_demo
```

## 2. Install the Dependency

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required package:

```bash
python3 -m pip install -r requirements.txt
```

## 3. Set Gemini Details

Set your Gemini API key:

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

Set a vision-capable Gemini model:

```bash
export GEMINI_MODEL="gemini-3.1-flash-lite"
```

If that model is too expensive or unavailable, choose another Gemini model from `https://ai.google.dev/gemini-api/docs/models` that supports image input.

## 4. Run the Script

Ask the default question:

```bash
python screen_describer.py
```

Ask a specific question:

```bash
python screen_describer.py "what is happening?"
```

Ask for a safe next step:

```bash
python screen_describer.py "what should I do next?"
```

Ask whether something looks safe:

```bash
python screen_describer.py "does this look safe?"
```

Ask for step-by-step guidance:

```bash
python screen_describer.py "how do I log into my bank account?"
```

```bash
python screen_describer.py "how can I send my grandson a picture of our dog Betty?"
```

Ask a clarification question:

```bash
python screen_describer.py "is it this icon I should press?"
```

## 5. Optional Settings

Limit the answer length:

```bash
python screen_describer.py "what is happening?" --max-tokens 200
```

Save the screenshot for debugging:

```bash
python screen_describer.py "what is happening?" --save
```

Saved screenshots go to `screenshots/`.

Use a different model for one run:

```bash
python screen_describer.py "what is happening?" --model "your-model-slug"
```

## 6. Expected Output

The script prints an answer like this:

```text
This looks like a sign-in page, which is where a website checks that it is really you. If this is a website you trust and meant to use, you can continue carefully. If you did not expect this page, do not enter your password yet.
```

For simple explanation questions, it should add just enough background:

```text
Google is a website people use to search the internet, a bit like asking a very large library where to find something. The box in the middle is where you type what you want to look for. If you want to search, click in that box and type your question.
```

For task guidance, the script should give only the next few safe steps:

```text
You are on an email page, and I can see a Compose button. Click Compose first. When the new message opens, ask me again and I can help you attach the picture.
```

For clarification questions, the script should be short and direct:

```text
Yes, that looks like the Messages icon. Click it once to open your messages. When it opens, ask me again and I can help you choose the person to message.
```

## 7. Common Problems

If you see `Missing GEMINI_API_KEY`, set the API key:

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

If you see `Missing Gemini model`, set a model:

```bash
export GEMINI_MODEL="gemini-3.1-flash-lite"
```

If you see `No module named PIL`, install the dependency:

```bash
python3 -m pip install -r requirements.txt
```

If Gemini says you requested too many tokens, use a smaller limit:

```bash
python screen_describer.py "what is happening?" --max-tokens 200
```

If screenshot capture fails on macOS, grant Screen Recording permission to your terminal app:

`System Settings -> Privacy & Security -> Screen & System Audio Recording`

Then restart the terminal and try again.

## 8. Privacy Reminder

The script sends a screenshot of the current screen to Gemini. Screenshots may contain private information such as emails, names, passwords, or banking pages.

By default, screenshots are not saved locally. Only use `--save` when you need to debug what the model saw.
