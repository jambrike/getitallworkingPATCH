const DEFAULT_COMPANION_URL = 'http://127.0.0.1:8765';

async function sendPrompt(text, source = 'overlay', options = {}) {
  const baseUrl = options.baseUrl || process.env.COMPANION_URL || DEFAULT_COMPANION_URL;
  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/prompt`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ source, text })
  });

  if (!response.ok) {
    throw new Error(`Companion service returned HTTP ${response.status}.`);
  }

  return response.json();
}

module.exports = {
  sendPrompt,
  DEFAULT_COMPANION_URL
};
