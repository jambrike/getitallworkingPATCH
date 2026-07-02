#!/usr/bin/env node

const readline = require('readline');
const { loadEnvFile } = require('../config/loadEnv');
const { speak, preprocessText } = require('../tts');

loadEnvFile();

function readInteractiveInput() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question('Text to speak: ', (answer) => {
      rl.close();
      resolve(answer);
    });
  });
}

async function main() {
  const argumentText = process.argv.slice(2).join(' ');
  const rawText = argumentText || await readInteractiveInput();
  const text = preprocessText(rawText);

  if (!text) {
    console.error('Please provide some text to speak.');
    process.exitCode = 1;
    return;
  }

  try {
    await speak(text);
  } catch (error) {
    console.error(error.message || 'Text-to-speech failed.');
    process.exitCode = 1;
  }
}

main();
