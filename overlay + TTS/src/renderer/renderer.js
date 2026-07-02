const helperText = document.querySelector('#helperText');
const closeButton = document.querySelector('#closeButton');
const minimizeButton = document.querySelector('#minimizeButton');
const expandButton = document.querySelector('#expandButton');
const shell = document.querySelector('.overlay-shell');

const NOTE_STORAGE_KEY = 'helper-overlay-note';

helperText.value = localStorage.getItem(NOTE_STORAGE_KEY) || '';

helperText.addEventListener('input', () => {
  localStorage.setItem(NOTE_STORAGE_KEY, helperText.value);
});

helperText.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey) return;

  event.preventDefault();
  window.overlayControls.printInput(helperText.value);
  helperText.value = '';
  localStorage.setItem(NOTE_STORAGE_KEY, '');
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
