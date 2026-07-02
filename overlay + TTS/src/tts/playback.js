const { spawn } = require('child_process');

function playAudioFile(filePath, options = {}) {
  if (!filePath) {
    return Promise.reject(new Error('No audio file path provided for playback.'));
  }

  const command = getPlaybackCommand(filePath, options);

  if (!command) {
    return Promise.reject(new Error(`Audio playback is not configured for ${process.platform}.`));
  }

  return runPlaybackCommand(command);
}

function getPlaybackCommand(filePath, options = {}) {
  if (options.playerCommand) {
    return {
      command: options.playerCommand,
      args: options.playerArgs || [filePath]
    };
  }

  if (process.platform === 'win32') {
    return {
      command: 'powershell.exe',
      args: [
        '-NoProfile',
        '-Command',
        `(New-Object Media.SoundPlayer '${escapePowerShellPath(filePath)}').PlaySync();`
      ]
    };
  }

  if (process.platform === 'darwin') {
    return {
      command: 'afplay',
      args: [filePath]
    };
  }

  return {
    command: 'aplay',
    args: [filePath]
  };
}

function runPlaybackCommand({ command, args }) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'ignore',
      windowsHide: true
    });

    child.on('error', (error) => {
      reject(new Error(`Audio playback failed: ${error.message}`));
    });

    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      reject(new Error(`Audio playback failed with exit code ${code}.`));
    });
  });
}

function escapePowerShellPath(filePath) {
  return filePath.replace(/'/g, "''");
}

module.exports = {
  playAudioFile,
  getPlaybackCommand
};
