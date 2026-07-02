const axios = require('axios');
const path = require('path');
const { spawn } = require('child_process');

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions';
const OPENROUTER_MODELS = [
    'openrouter/free',
    'google/gemma-4-26b-a4b-it:free',
    'meta-llama/llama-3.3-70b-instruct:free',
    'qwen/qwen3-next-80b-a3b-instruct:free'
];
const TTS_SCRIPT = path.join(__dirname, 'gttslistners.py');

async function sendToAI(text) {
    if (!OPENROUTER_API_KEY) {
        console.error("AI error: set OPENROUTER_API_KEY before running Silia.");
        return;
    }

    const prompt = `Respond simply and concisely to this: "${text}"
    dont respond more than 4-6 sentences.
    Known information: You are a background assistant for older people to understand whats going on on there laptop. you are in production and you will soon get the ability to know whats going on on there screen. You care begin run on a macbook.`;

    for (const model of OPENROUTER_MODELS) {
        try {
            console.log(`[AI] Trying model: ${model}`);
            const response = await axios.post(
                OPENROUTER_API_URL,
                {
                    model,
                    messages: [{ role: "user", content: prompt }],
                },
                {
                    headers: {
                        "Authorization": `Bearer ${OPENROUTER_API_KEY}`,
                        "Content-Type": "application/json"
                    }
                }
            );

            const aiText = response.data.choices[0].message.content.trim();
            console.log("[AI Reply]:", aiText);
            speakWithGoogleTTS(aiText);

            return aiText;
        } catch (err) {
            logAIError(model, err);
        }
    }

    console.error("AI error: all OpenRouter models failed.");
}

function logAIError(model, err) {
    if (err.response) {
        console.error(`[AI] ${model} failed:`, err.response.status, err.response.data);
        return;
    }

    console.error(`[AI] ${model} failed:`, err.message);
}

function speakWithGoogleTTS(text) {
    if (!text) return;

    const pythonProcess = spawn('python3', [TTS_SCRIPT, text]);

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[TTS] ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[TTS ERR] ${data}`);
    });

    pythonProcess.on('error', (err) => {
        console.error("Failed to start Google TTS:", err.message);
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Google TTS exited with code ${code}`);
        }
    });
}

module.exports = { sendToAI };
