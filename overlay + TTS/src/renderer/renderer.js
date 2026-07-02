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

  window.overlayControls.printInput(text);
  helperText.value = '';
  localStorage.setItem(NOTE_STORAGE_KEY, '');
}

function showReply(text) {
  const cleanedText = String(text || '').trim();
  assistantReply.textContent = cleanedText;
  shell.classList.toggle('has-reply', Boolean(cleanedText));
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
