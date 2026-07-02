const fs = require('fs');
const path = require('path');
const vosk = require('vosk');
const mic = require('mic');
const { sendToAI } = require('./airesponse'); // separate AI module

const MODEL_PATH = path.join(__dirname, 'model'); // Vosk model folder
const WAKE_WORD = 'click';

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
console.log(`Silia is listening for "${WAKE_WORD}"...`);

let waitingForPrompt = false;

// ---- Wake word + AI handler ----
function handleTranscript(text) {
    text = text.toLowerCase();
    if (!text) return;

    console.log("Heard:", text);

    // --- Wake word detection ---
    if (text.includes(WAKE_WORD)) {
        const prompt = getPromptAfterWakeWord(text);

        if (prompt) {
            console.log("Wake word detected. Sending prompt to AI...");
            sendToAI(prompt);
            waitingForPrompt = false;
            return;
        }

        waitingForPrompt = true;
        console.log("Wake word detected. Say your prompt now.");
        return;
    }

    if (waitingForPrompt) {
        console.log("Sending prompt to AI...");
        sendToAI(text);
        waitingForPrompt = false;
    }
}

function getPromptAfterWakeWord(text) {
    const wakeWordRegex = new RegExp(`\\b${WAKE_WORD}\\b\\s*(.*)$`);
    const match = text.match(wakeWordRegex);
    return match ? match[1].trim() : '';
}
