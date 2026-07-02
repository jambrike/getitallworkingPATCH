const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const DEFAULT_COMPANION_URL = 'http://127.0.0.1:8765';
const ROOT_ENV = path.join(__dirname, '..', '.env');
const OVERLAY_ROOT = path.join(__dirname, '..', 'overlay + TTS');
const TTS_CLI = path.join(OVERLAY_ROOT, 'src', 'cli', 'say.js');

loadEnvFile(ROOT_ENV);

async function sendToAI(text) {
  const prompt = String(text || '').trim();
  if (!prompt) return '';

  try {
    const response = await fetch(`${companionUrl()}/prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ source: 'voice', text: prompt })
    });

    if (!response.ok) {
      throw new Error(`Companion service returned HTTP ${response.status}.`);
    }

    const payload = await response.json();
    const say = String(payload.say || '').trim();
    console.log('[Companion Reply]:', say || '(nothing to say)');

    if (say) {
      speakWithOpenAITTS(say);
    }

    return say;
  } catch (error) {
    console.error('Companion error:', error.message || error);
    return '';
  }
}

function companionUrl() {
  return (process.env.COMPANION_URL || DEFAULT_COMPANION_URL).replace(/\/$/, '');
}

function speakWithOpenAITTS(text) {
  const child = spawn('node', [TTS_CLI, text], {
    cwd: OVERLAY_ROOT,
    env: process.env,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  child.stdout.on('data', (data) => {
    console.log(`[TTS] ${data}`);
  });

  child.stderr.on('data', (data) => {
    console.error(`[TTS ERR] ${data}`);
  });

  child.on('error', (err) => {
    console.error('Failed to start OpenAI TTS:', err.message);
  });

  child.on('close', (code) => {
    if (code !== 0) {
      console.error(`OpenAI TTS exited with code ${code}`);
    }
  });
}

module.exports = { sendToAI };

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;

  const contents = fs.readFileSync(filePath, 'utf8');
  for (const line of contents.split(/\r?\n/)) {
    const trimmedLine = line.trim();
    if (!trimmedLine || trimmedLine.startsWith('#')) continue;

    const separatorIndex = trimmedLine.indexOf('=');
    if (separatorIndex === -1) continue;

    const key = trimmedLine.slice(0, separatorIndex).trim();
    const value = trimmedLine.slice(separatorIndex + 1).trim().replace(/^["']|["']$/g, '');
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}
