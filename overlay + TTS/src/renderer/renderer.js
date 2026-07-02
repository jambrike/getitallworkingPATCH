const helperText = document.querySelector('#helperText');
const assistantReply = document.querySelector('#assistantReply');
const closeButton = document.querySelector('#closeButton');
const minimizeButton = document.querySelector('#minimizeButton');
const expandButton = document.querySelector('#expandButton');
const speakButton = document.querySelector('#speakButton');
const sendButton = document.querySelector('#sendButton');
const shell = document.querySelector('.overlay-shell');
const statusDot = document.querySelector('#statusDot');
const statusText = document.querySelector('#statusText');

const NOTE_STORAGE_KEY = 'helper-overlay-note';
const TYPEWRITER_WORD_DELAY_MS = 55;
const VOICE_RECORDING_MS = 6500;

let typewriterTimer;
let isRecordingVoice = false;

helperText.value = localStorage.getItem(NOTE_STORAGE_KEY) || '';

helperText.addEventListener('input', () => {
  localStorage.setItem(NOTE_STORAGE_KEY, helperText.value);
});

helperText.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey) return;

  event.preventDefault();
  sendPrompt();
});

sendButton.addEventListener('click', () => {
  sendPrompt();
});

speakButton.addEventListener('click', () => {
  recordVoicePrompt();
});

closeButton.addEventListener('click', () => {
  window.overlayControls.close();
});

minimizeButton.addEventListener('click', () => {
  shell.classList.add('is-compact');
  expandButton.classList.add('is-visible');
  window.overlayControls.shrink();
});

expandButton.addEventListener('click', () => {
  shell.classList.remove('is-compact');
  expandButton.classList.remove('is-visible');
  window.overlayControls.expand();
  helperText.focus();
});

window.overlayControls.onStatus((status) => {
  setStatus(status);
});

window.overlayControls.onReply((text) => {
  showReply(text);
});

function sendPrompt() {
  const text = helperText.value.trim();
  if (!text) return;

  showPendingReply();
  window.overlayControls.printInput(text);
  helperText.value = '';
  localStorage.setItem(NOTE_STORAGE_KEY, '');
}

function showReply(text) {
  const cleanedText = String(text || '').trim();
  shell.classList.toggle('has-reply', Boolean(cleanedText));
  shell.classList.remove('is-awake');
  typeReply(cleanedText);
}

function showPendingReply() {
  clearTypewriter();
  assistantReply.textContent = 'Thinking...';
  shell.classList.remove('is-awake');
  shell.classList.add('is-opening', 'has-reply');
}

async function recordVoicePrompt() {
  if (isRecordingVoice) return;

  isRecordingVoice = true;
  speakButton.disabled = true;
  speakButton.textContent = 'Listening';
  setStatus('awake');
  showAwakeReply();

  try {
    const audioPayload = await recordAudioClip(VOICE_RECORDING_MS);
    setStatus('thinking');
    assistantReply.textContent = 'Thinking...';
    await window.overlayControls.sendVoiceAudio(audioPayload);
  } catch (error) {
    console.error(error);
    showReply('I could not use the microphone. Check microphone permission and try again.');
    setStatus('error');
  } finally {
    isRecordingVoice = false;
    speakButton.disabled = false;
    speakButton.textContent = 'Speak';
  }
}

async function recordAudioClip(durationMs) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error('Microphone recording is not available.');
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    }
  });

  const mimeType = preferredAudioMimeType();
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks = [];

  return new Promise((resolve, reject) => {
    const stopTimer = window.setTimeout(() => {
      if (recorder.state !== 'inactive') {
        recorder.stop();
      }
    }, durationMs);

    recorder.addEventListener('dataavailable', (event) => {
      if (event.data && event.data.size > 0) {
        chunks.push(event.data);
      }
    });

    recorder.addEventListener('error', (event) => {
      window.clearTimeout(stopTimer);
      stopStream(stream);
      reject(event.error || new Error('Microphone recording failed.'));
    });

    recorder.addEventListener('stop', async () => {
      window.clearTimeout(stopTimer);
      stopStream(stream);

      const blob = new Blob(chunks, { type: recorder.mimeType || mimeType || 'audio/webm' });
      const audio = await blob.arrayBuffer();
      resolve({ audio, mimeType: blob.type || 'audio/webm' });
    });

    recorder.start();
  });
}

function preferredAudioMimeType() {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus'
  ];

  return types.find((type) => MediaRecorder.isTypeSupported(type)) || '';
}

function stopStream(stream) {
  stream.getTracks().forEach((track) => track.stop());
}

function showAwakeReply() {
  clearTypewriter();
  assistantReply.textContent = 'Listening...';
  shell.classList.add('is-opening', 'has-reply', 'is-awake');
}

function typeReply(text) {
  clearTypewriter();

  if (!text) {
    assistantReply.textContent = '';
    shell.classList.remove('is-opening');
    shell.classList.remove('is-awake');
    return;
  }

  const words = text.split(/\s+/).filter(Boolean);
  const renderedWords = [];
  assistantReply.textContent = '';
  shell.classList.remove('is-opening');
  shell.classList.remove('is-awake');

  typewriterTimer = window.setInterval(() => {
    const nextWord = words.shift();

    if (!nextWord) {
      clearTypewriter();
      return;
    }

    renderedWords.push(nextWord);
    assistantReply.textContent = renderedWords.join(' ');
  }, TYPEWRITER_WORD_DELAY_MS);
}

function clearTypewriter() {
  if (!typewriterTimer) return;
  window.clearInterval(typewriterTimer);
  typewriterTimer = undefined;
}

function setStatus(status) {
  const labels = {
    awake: 'Awake',
    listening: 'Listening',
    thinking: 'Thinking',
    speaking: 'Speaking',
    error: 'Error'
  };

  const normalizedStatus = labels[status] ? status : 'listening';
  statusText.textContent = labels[normalizedStatus];
  statusDot.title = labels[normalizedStatus];
  shell.dataset.status = normalizedStatus;
}
