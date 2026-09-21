#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/android_dev_setup.log"
echo "=== Android dev setup start: $(date) ===" | tee "$LOG"

# 1. Homebrew
if ! command -v brew >/dev/null 2>&1; then
  echo "[1/6] Installing Homebrew..." | tee -a "$LOG"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" | tee -a "$LOG"
else
  echo "[1/6] Homebrew already installed" | tee -a "$LOG"
fi

# 2. adb + platform-tools
echo "[2/6] Installing adb..." | tee -a "$LOG"
brew install --cask android-platform-tools | tee -a "$LOG"

# 3. JDK 17
echo "[3/6] Installing JDK 17..." | tee -a "$LOG"
brew install openjdk@17 | tee -a "$LOG"

# 4. Android cmdline-tools
ANDROID_SDK_ROOT="${HOME}/Library/Android/sdk"
mkdir -p "${ANDROID_SDK_ROOT}/cmdline-tools"
CMDLINE_ZIP="/tmp/cmdline-tools.zip"
echo "[4/6] Downloading Android cmdline-tools..." | tee -a "$LOG"
curl -fsSL -o "$CMDLINE_ZIP" "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip" | tee -a "$LOG"
unzip -q -o "$CMDLINE_ZIP" -d "${ANDROID_SDK_ROOT}/cmdline-tools" | tee -a "$LOG"
mv "${ANDROID_SDK_ROOT}/cmdline-tools/cmdline-tools" "${ANDROID_SDK_ROOT}/cmdline-tools/latest" 2>/dev/null || true
rm -f "$CMDLINE_ZIP"

# 5. Android packages
echo "[5/6] Installing Android platform-33 and build-tools 34..." | tee -a "$LOG"
yes | "${ANDROID_SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager" --sdk_root="${ANDROID_SDK_ROOT}" "platform-tools" "platforms;android-33" "build-tools;34.0.0" | tee -a "$LOG"

# 6. PowerShell (pwsh)
echo "[6/6] Installing PowerShell (pwsh)..." | tee -a "$LOG"
brew install --cask powershell | tee -a "$LOG"

cat <<'EOF' | tee -a "$LOG"

=== Setup complete. Add the following to ~/.zprofile or ~/.bash_profile: ===

export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export PATH="$PATH:$ANDROID_SDK_ROOT/platform-tools"
export PATH="$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin"
export PATH="/usr/local/opt/openjdk@17/bin:$PATH"

Then run: source ~/.zprofile

Verify with:
  adb --version
  java -version
  sdkmanager --list | grep -E "platforms;android-33|build-tools;34.0.0"
  pwsh --version

EOF
