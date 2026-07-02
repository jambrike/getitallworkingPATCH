const fs = require('fs');
const os = require('os');
const path = require('path');
const { once } = require('events');
const { pipeline } = require('stream');
const { promisify } = require('util');
const OpenAI = require('openai');
const { preprocessText } = require('./preprocessText');

const pipelineAsync = promisify(pipeline);
const DEFAULT_TTS_MODEL = 'gpt-4o-mini-tts';
const DEFAULT_TTS_VOICE = 'alloy';
const DEFAULT_AUDIO_FORMAT = 'wav';

function createTempAudioPath(format = DEFAULT_AUDIO_FORMAT) {
  const fileName = `openai-tts-${process.pid}-${Date.now()}.${format}`;
  return path.join(os.tmpdir(), fileName);
}

function getTtsConfig(options = {}) {
  return {
    model: options.model || process.env.OPENAI_TTS_MODEL || DEFAULT_TTS_MODEL,
    voice: options.voice || process.env.OPENAI_TTS_VOICE || DEFAULT_TTS_VOICE,
    responseFormat: options.responseFormat || process.env.OPENAI_TTS_FORMAT || DEFAULT_AUDIO_FORMAT
  };
}

async function streamSpeechToFile(text, outputPath, options = {}) {
  const processedText = preprocessText(text);

  if (!processedText) {
    throw new Error('Cannot create speech from empty text.');
  }

  if (!process.env.OPENAI_API_KEY) {
    throw new Error('Missing OPENAI_API_KEY. Set it before running text-to-speech.');
  }

  const config = getTtsConfig(options);
  const targetPath = outputPath || createTempAudioPath(config.responseFormat);
  const client = options.client || new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  let response;

  try {
    response = await client.audio.speech.create({
      model: config.model,
      voice: config.voice,
      input: processedText,
      response_format: config.responseFormat
    });
  } catch (error) {
    throw new Error(`OpenAI text-to-speech request failed: ${safeErrorMessage(error)}`);
  }

  try {
    await writeStreamingResponseToFile(response, targetPath);
  } catch (error) {
    throw new Error(`Could not create speech audio file: ${safeErrorMessage(error)}`);
  }

  return targetPath;
}

async function writeStreamingResponseToFile(response, outputPath) {
  if (!response || !response.body) {
    throw new Error('OpenAI response did not include a readable audio stream.');
  }

  const output = fs.createWriteStream(outputPath);

  if (typeof response.body.pipe === 'function') {
    await pipelineAsync(response.body, output);
    return;
  }

  if (typeof response.body.getReader === 'function') {
    await writeWebStreamToFile(response.body, output);
    return;
  }

  throw new Error('Unsupported audio stream type returned by OpenAI.');
}

async function writeWebStreamToFile(webStream, output) {
  const reader = webStream.getReader();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      if (!output.write(Buffer.from(value))) {
        await once(output, 'drain');
      }
    }

    await finishWritable(output);
  } catch (error) {
    output.destroy(error);
    throw error;
  } finally {
    reader.releaseLock();
  }
}

function finishWritable(output) {
  return new Promise((resolve, reject) => {
    output.end((error) => {
      if (error) {
        reject(error);
        return;
      }

      resolve();
    });
  });
}

function safeErrorMessage(error) {
  if (!error) return 'unknown error';
  return error.message || String(error);
}

module.exports = {
  streamSpeechToFile,
  createTempAudioPath,
  getTtsConfig
};
