# MVP Screen Assistant Decision Layer

This folder contains a tiny AI decision layer for your assistant.

It takes three text inputs:

- what the user said
- what another AI described as happening on screen
- context that has built up about what happened recently

It returns:

- what to say out loud
- whether to run background work
- one or more allowed browser/file actions

It also now contains `companion_service.py`, the FastAPI service that connects overlay input, Vosk voice input, screenshot context, the decision layer, browser/file actions, and OpenAI TTS clients.

## Run The Integrated Service

From the workspace root:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
python3 -m pip install -r agent/requirements.txt
python3 -m uvicorn agent.companion_service:app --host 127.0.0.1 --port 8765
```

The full app launcher is:

```bash
./run-companion.sh
```

## Files

- `agent_prompt.md`: the system prompt and behavior rules
- `simple_agent.py`: a small Python wrapper that calls a model and prints JSON

## Run

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
python simple_agent.py
```

For the standalone decision script, by default it reads:

- `user.txt`
- `screen.txt`
- `context.txt`

Example:

```bash
printf "What is this asking me to do?\\n" > user.txt
printf "A Safari window is showing a sign-in page with a password box.\\n" > screen.txt
printf "The user was trying to check email.\\n" > context.txt
python simple_agent.py
```

You can also pass values directly:

```bash
python simple_agent.py \
  --user-prompt "What is this asking me to do?" \
  --screen-description "A Safari window is showing a sign-in page with a password box." \
  --context "The user was trying to check email."
```

## Terminal Output

```text
SAY_OUTLOUD:
It is asking you to type your password to sign in. Only do this if you trust this page and meant to open your email.

RUN_IN_BACKGROUND:
no

ACTIONS:
[]
```

## JSON Output

Use this if another program needs to parse it:

```bash
python simple_agent.py --format json
```

The assistant uses a warm, simple style intended for older laptop users. Think clear family tech support, not a formal chatbot.
