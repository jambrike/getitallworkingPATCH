const fs = require('fs');
const os = require('os');
const path = require('path');
const vosk = require('vosk');
const mic = require('mic');
const { spawn } = require('child_process');
const { sendToAI, isAssistantSpeaking } = require('./airesponse');

const MODEL_PATH = path.join(__dirname, 'model'); // Vosk model folder
const ROOT_ENV = path.join(__dirname, '..', '.env');

loadEnvFile(ROOT_ENV);

const WAKE_WORD = 'grandson';
const MIN_PROMPT_WORDS = 2;
const SAMPLE_RATE = 16000;
const BYTES_PER_SAMPLE = 2;
const CHANNELS = 1;
const TRANSCRIBE_MODE = process.env.VOICE_STT_MODE || 'hybrid';
const TRANSCRIBE_LOOKBACK_MS = Number(process.env.VOICE_TRANSCRIBE_LOOKBACK_MS || 8000);
const TRANSCRIBE_TIMEOUT_MS = Number(process.env.VOICE_TRANSCRIBE_TIMEOUT_MS || 12000);
const MAX_BUFFER_BYTES = Math.ceil(SAMPLE_RATE * BYTES_PER_SAMPLE * CHANNELS * (TRANSCRIBE_LOOKBACK_MS / 1000));
const TRANSCRIBE_SCRIPT = path.join(__dirname, 'transcribe_audio.py');

// ---- Check model exists ----
if (!fs.existsSync(MODEL_PATH)) {
    console.error("Model folder not found! Please put Vosk model in 'model/'");
    process.exit(1);
}

// ---- Initialize Vosk ----
const model = new vosk.Model(MODEL_PATH);
const rec = new vosk.Recognizer({ model: model, sampleRate: 16000 });

// ---- Setup mic ----
const micInstance = mic({
    rate: '16000',
    channels: '1',
    debug: false,
    device: 'default',
    encoding: 'signed-integer'
});

const micInputStream = micInstance.getAudioStream();
const recentAudio = [];
let recentAudioBytes = 0;
let isTranscribing = false;

micInputStream.on('data', (data) => {
    rememberAudio(data);
    if (rec.acceptWaveform(data)) {
        const result = rec.result();
        handleTranscript(result.text);
    }
});

micInputStream.on('error', (err) => {
    console.error("Mic error:", err);
});

micInstance.start();
console.log(`Silia is listening for "${WAKE_WORD}" plus your question...`);

// ---- Wake word + AI handler ----
function handleTranscript(text) {
    text = String(text || '').toLowerCase().trim();
    if (!text) return;

    if (isAssistantSpeaking()) {
        console.log("Ignored assistant speech:", text);
        return;
    }

    console.log("Heard:", text);

    // --- Wake word detection ---
    const prompt = getPromptAfterWakeWord(text);
    if (prompt !== null) {
        handleWakeTranscript(prompt);
        return;
    }
}

async function handleWakeTranscript(voskPrompt) {
    if (isTranscribing) {
        console.log("Wake word detected, but transcription is already running.");
        return;
    }

    if (TRANSCRIBE_MODE === 'hybrid' || TRANSCRIBE_MODE === 'openai') {
        isTranscribing = true;
        try {
            const cleanText = await transcribeRecentAudio();
            const cleanPrompt = getPromptAfterWakeWord(cleanText);
            const chosenPrompt = choosePrompt(cleanPrompt, cleanText, voskPrompt);

            if (isUsablePrompt(chosenPrompt)) {
                console.log("Wake word detected. OpenAI transcript:", cleanText || "(empty)");
                console.log("Sending cleaned prompt to AI...");
                sendToAI(chosenPrompt);
                return;
            }

            console.log(`Wake word detected. Say "${WAKE_WORD}" plus your question in one sentence.`);
            return;
        } catch (error) {
            console.error("OpenAI transcription failed:", error.message || error);
            if (isUsablePrompt(voskPrompt)) {
                console.log("Falling back to Vosk prompt.");
                sendToAI(voskPrompt);
            }
            return;
        } finally {
            isTranscribing = false;
        }
    }

    if (isUsablePrompt(voskPrompt)) {
        console.log("Wake word detected. Sending prompt to AI...");
        sendToAI(voskPrompt);
        return;
    }

    console.log(`Wake word detected. Say "${WAKE_WORD}" plus your question in one sentence.`);
}

function choosePrompt(cleanPrompt, cleanText, voskPrompt) {
    if (isUsablePrompt(cleanPrompt || '')) {
        return cleanPrompt;
    }

    if (isUsablePrompt(cleanText || '') && !isOnlyWakeWord(cleanText)) {
        return cleanText;
    }

    return voskPrompt;
}

function getPromptAfterWakeWord(text) {
    text = String(text || '').toLowerCase().trim();
    const filler = String.raw`(?:hey|okay|ok|yo|um|uh|please)?`;
    const wakeVariants = [
        String.raw`grandson`,
        String.raw`grand son`,
        String.raw`grandsons`,
        String.raw`grand sun`,
        String.raw`granson`
    ];
    const wakeWordRegex = new RegExp(`^${filler}\\s*\\b(?:${wakeVariants.join('|')})\\b\\s*(.*)$`);
    const match = text.match(wakeWordRegex);
    return match ? match[1].trim() : null;
}

function isUsablePrompt(prompt) {
    if (!prompt) return false;

    const words = prompt.split(/\s+/).filter(Boolean);
    if (words.length < MIN_PROMPT_WORDS) {
        console.log("Ignored short prompt after wake word:", prompt);
        return false;
    }

    return true;
}

function isOnlyWakeWord(text) {
    return getPromptAfterWakeWord(text) === '';
}

function rememberAudio(data) {
    const chunk = Buffer.from(data);
    recentAudio.push(chunk);
    recentAudioBytes += chunk.length;

    while (recentAudioBytes > MAX_BUFFER_BYTES && recentAudio.length > 1) {
        const removed = recentAudio.shift();
        recentAudioBytes -= removed.length;
    }
}

async function transcribeRecentAudio() {
    const rawAudio = Buffer.concat(recentAudio, recentAudioBytes);
    if (!rawAudio.length) return '';

    const wavPath = path.join(os.tmpdir(), `grandson-voice-${process.pid}-${Date.now()}.wav`);
    fs.writeFileSync(wavPath, pcmToWav(rawAudio));

    try {
        return await runTranscriber(wavPath);
    } finally {
        fs.rmSync(wavPath, { force: true });
    }
}

function runTranscriber(wavPath) {
    return new Promise((resolve, reject) => {
        let settled = false;
        const child = spawn(process.env.PYTHON || 'python3', [TRANSCRIBE_SCRIPT, wavPath], {
            cwd: __dirname,
            env: process.env,
            stdio: ['ignore', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';
        const timeout = setTimeout(() => {
            if (settled) return;
            settled = true;
            child.kill('SIGTERM');
            reject(new Error('OpenAI transcription timed out.'));
        }, TRANSCRIBE_TIMEOUT_MS);

        child.stdout.on('data', (data) => {
            stdout += data.toString();
        });
        child.stderr.on('data', (data) => {
            stderr += data.toString();
        });
        child.on('error', (error) => {
            if (settled) return;
            settled = true;
            clearTimeout(timeout);
            reject(error);
        });
        child.on('close', (code) => {
            if (settled) return;
            settled = true;
            clearTimeout(timeout);
            if (code !== 0) {
                reject(new Error(stderr.trim() || `Transcriber exited with code ${code}`));
                return;
            }
            resolve(stdout.trim().toLowerCase());
        });
    });
}

function pcmToWav(pcmBuffer) {
    const header = Buffer.alloc(44);
    const byteRate = SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE;
    const blockAlign = CHANNELS * BYTES_PER_SAMPLE;

    header.write('RIFF', 0);
    header.writeUInt32LE(36 + pcmBuffer.length, 4);
    header.write('WAVE', 8);
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16);
    header.writeUInt16LE(1, 20);
    header.writeUInt16LE(CHANNELS, 22);
    header.writeUInt32LE(SAMPLE_RATE, 24);
    header.writeUInt32LE(byteRate, 28);
    header.writeUInt16LE(blockAlign, 32);
    header.writeUInt16LE(BYTES_PER_SAMPLE * 8, 34);
    header.write('data', 36);
    header.writeUInt32LE(pcmBuffer.length, 40);

    return Buffer.concat([header, pcmBuffer]);
}

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
