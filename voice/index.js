const fs = require('fs');
const path = require('path');
const vosk = require('vosk');
const mic = require('mic');
const { sendToAI, isAssistantSpeaking } = require('./airesponse');

const MODEL_PATH = path.join(__dirname, 'model'); // Vosk model folder
const WAKE_WORD = 'grandson';
const MIN_PROMPT_WORDS = 2;

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
micInputStream.on('data', (data) => {
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

        if (isUsablePrompt(prompt)) {
            console.log("Wake word detected. Sending prompt to AI...");
            sendToAI(prompt);
            return;
        }

        console.log(`Wake word detected. Say "${WAKE_WORD}" plus your question in one sentence.`);
        return;
    }
}

function getPromptAfterWakeWord(text) {
    const wakeWordRegex = new RegExp(`^(?:hey|okay|ok|yo|um|uh)?\\s*\\b${WAKE_WORD}\\b\\s*(.*)$`);
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
