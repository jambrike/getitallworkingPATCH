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

let typewriterTimer;

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
  const text = helperText.value.trim();
  if (!text) return;

  window.overlayControls.speakText(text);
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
  typeReply(cleanedText);
}

function showPendingReply() {
  clearTypewriter();
  assistantReply.textContent = 'Thinking...';
  shell.classList.add('is-opening', 'has-reply');
}

function typeReply(text) {
  clearTypewriter();

  if (!text) {
    assistantReply.textContent = '';
    shell.classList.remove('is-opening');
    return;
  }

  const words = text.split(/\s+/).filter(Boolean);
  const renderedWords = [];
  assistantReply.textContent = '';
  shell.classList.remove('is-opening');

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
