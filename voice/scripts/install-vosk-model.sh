#!/usr/bin/env bash
set -euo pipefail

MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
MODEL_ZIP="downloads/vosk-model-en-us-0.22.zip"
MODEL_DIR="downloads/vosk-model-en-us-0.22"

mkdir -p downloads

if [ ! -f "$MODEL_ZIP" ]; then
  curl -L --fail -o "$MODEL_ZIP" "$MODEL_URL"
fi

if [ ! -d "$MODEL_DIR" ]; then
  unzip -q "$MODEL_ZIP" -d downloads
fi

if [ -d model ]; then
  mv model "model.backup-$(date +%Y%m%d-%H%M%S)"
fi

mv "$MODEL_DIR" model
echo "Installed Vosk model to ./model"
