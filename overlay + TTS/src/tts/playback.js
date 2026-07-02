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
        '-STA',
        '-Command',
        createWindowsPlaybackScript(filePath)
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
    let stderr = '';

    const child = spawn(command, args, {
      stdio: ['ignore', 'ignore', 'pipe'],
      windowsHide: true
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', (error) => {
      reject(new Error(`Audio playback failed: ${error.message}`));
    });

    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      const details = stderr.trim();
      reject(new Error(`Audio playback failed with exit code ${code}.${details ? ` ${details}` : ''}`));
    });
  });
}

function createWindowsPlaybackScript(filePath) {
  const escapedPath = escapePowerShellPath(filePath);

  return [
    'Add-Type -AssemblyName PresentationCore;',
    '$ErrorActionPreference = "Stop";',
    `$path = '${escapedPath}';`,
    '$player = New-Object System.Windows.Media.MediaPlayer;',
    '$done = $false;',
    '$failed = $null;',
    '$player.add_MediaEnded({ $script:done = $true });',
    '$player.add_MediaFailed({ param($sender, $eventArgs) $script:failed = $eventArgs.ErrorException.Message; $script:done = $true });',
    '$player.Open([Uri]::new((Resolve-Path -LiteralPath $path).Path));',
    '$player.Play();',
    'while (-not $done) { Start-Sleep -Milliseconds 100; }',
    '$player.Close();',
    'if ($failed) { Write-Error $failed; exit 1; }'
  ].join(' ');
}

function escapePowerShellPath(filePath) {
  return filePath.replace(/'/g, "''");
}

module.exports = {
  playAudioFile,
  getPlaybackCommand
};
