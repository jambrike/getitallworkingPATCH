#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${APP_PATH:-/Applications/Grandson.app}"
CONTENTS_DIR="$APP_PATH/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
EXECUTABLE="$MACOS_DIR/Grandson"
PLIST="$CONTENTS_DIR/Info.plist"
ICON_SOURCE="$ROOT_DIR/assets/Grandson.icns"
ICON_DEST="$RESOURCES_DIR/Grandson.icns"

mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

if [[ -f "$ICON_SOURCE" ]]; then
  cp "$ICON_SOURCE" "$ICON_DEST"
fi

cat >"$PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>Grandson</string>
  <key>CFBundleExecutable</key>
  <string>Grandson</string>
  <key>CFBundleIconFile</key>
  <string>Grandson</string>
  <key>CFBundleIdentifier</key>
  <string>local.grandson.companion</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>Grandson</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSMicrophoneUsageDescription</key>
  <string>Grandson uses the microphone for voice prompts.</string>
  <key>NSScreenCaptureUsageDescription</key>
  <string>Grandson uses screen context to help explain and assist with what is on screen.</string>
</dict>
</plist>
PLIST

cat >"$EXECUTABLE" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$ROOT_DIR"
LOG_DIR="\$HOME/Library/Logs/Grandson"
STATE_DIR="\$HOME/Library/Application Support/Grandson"
LOG_FILE="\$LOG_DIR/companion.log"
PID_FILE="\$STATE_DIR/grandson.pid"
HEALTH_URL="http://127.0.0.1:8765/health"
APP_PATH_EXPORT="/Library/Frameworks/Python.framework/Versions/3.11/bin:/opt/homebrew/bin:/usr/local/bin:\$HOME/.nvm/versions/node/v20.20.0/bin:\$HOME/.nvm/versions/node/v16.20.2/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "\$LOG_DIR" "\$STATE_DIR"

notify() {
  /usr/bin/osascript -e "display notification \"\$1\" with title \"Grandson\"" >/dev/null 2>&1 || true
}

if /usr/bin/curl -fsS --max-time 1 "\$HEALTH_URL" >/dev/null 2>&1; then
  notify "Grandson is already running."
  exit 0
fi

if /usr/bin/pgrep -f "\$ROOT_DIR/run-companion.sh" >/dev/null 2>&1; then
  notify "Grandson is already starting."
  exit 0
fi

cd "\$ROOT_DIR"
notify "Starting Grandson..."
echo "\$\$" >"\$PID_FILE"
exec /bin/zsh -lc "export PATH=\"\$APP_PATH_EXPORT:\\\$PATH\"; cd \"\$ROOT_DIR\"; START_VOICE=1 ./run-companion.sh" >>"\$LOG_FILE" 2>&1
LAUNCHER

chmod +x "$EXECUTABLE"
/usr/bin/plutil -lint "$PLIST" >/dev/null

echo "Installed $APP_PATH"
echo "Logs will be written to ~/Library/Logs/Grandson/companion.log"
