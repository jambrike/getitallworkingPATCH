param(
  [switch]$StartVoice
)

$ErrorActionPreference = 'Stop'
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:COMPANION_URL = if ($env:COMPANION_URL) { $env:COMPANION_URL } else { 'http://127.0.0.1:8765' }

function Load-EnvFile {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }

  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) {
      return
    }

    $separator = $line.IndexOf('=')
    if ($separator -lt 1) {
      return
    }

    $name = $line.Substring(0, $separator).Trim()
    $value = $line.Substring($separator + 1).Trim().Trim('"').Trim("'")
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
  }
}

function Get-PythonCommand {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return @{ File = 'py'; Prefix = @('-3') }
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    return @{ File = 'python'; Prefix = @() }
  }

  throw 'Python was not found. Install Python 3 and make sure py.exe or python.exe is on PATH.'
}

function Stop-ChildProcess {
  param($Process)

  if ($Process -and -not $Process.HasExited) {
    Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
  }
}

Load-EnvFile (Join-Path $RootDir '.env')

if (-not $env:OPENAI_API_KEY) {
  throw 'Missing OPENAI_API_KEY. Copy .env.example to .env and add your key.'
}

$python = Get-PythonCommand
$hostName = if ($env:COMPANION_HOST) { $env:COMPANION_HOST } else { '127.0.0.1' }
$port = if ($env:COMPANION_PORT) { $env:COMPANION_PORT } else { '8765' }
$serviceArgs = $python.Prefix + @('-m', 'uvicorn', 'agent.companion_service:app', '--host', $hostName, '--port', $port)

Write-Host "Starting companion service on http://$hostName`:$port ..."
$service = Start-Process -FilePath $python.File -ArgumentList $serviceArgs -WorkingDirectory $RootDir -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2

Write-Host 'Starting overlay...'
$overlay = Start-Process -FilePath 'npm.cmd' -ArgumentList @('start') -WorkingDirectory (Join-Path $RootDir 'overlay + TTS') -WindowStyle Hidden -PassThru

$voice = $null
if ($StartVoice -or $env:START_VOICE -eq '1') {
  Write-Host 'Starting voice listener...'
  $voice = Start-Process -FilePath 'npm.cmd' -ArgumentList @('start') -WorkingDirectory (Join-Path $RootDir 'voice') -WindowStyle Hidden -PassThru
}

Write-Host 'Companion is running. Press Ctrl+C in this window to stop background processes.'

try {
  while ($true) {
    Start-Sleep -Seconds 1
    if ($service.HasExited) {
      throw 'Companion service stopped unexpectedly.'
    }
  }
} finally {
  Stop-ChildProcess $voice
  Stop-ChildProcess $overlay
  Stop-ChildProcess $service
}
