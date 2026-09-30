#!/usr/bin/env bash
set -euo pipefail

# Build the standalone Qt Android app; Termux uses build_device.sh instead.
# Prefer the project-local toolchain. CI and other machines can pass their own
# installed paths through the standard Android/Java variables and QT_ANDROID_ROOT.
ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$ANDROID_DIR/.." && pwd)"
TOOL_ROOT="$PROJECT_DIR/.android-toolchain"
if [[ -d "$TOOL_ROOT/Qt/5.15.2/android" ]]; then
    QT_ROOT="$TOOL_ROOT/Qt/5.15.2/android"
else
    QT_ROOT="${QT_ANDROID_ROOT:-}"
fi
if [[ -d "$TOOL_ROOT/sdk" ]]; then
    SDK_ROOT="$TOOL_ROOT/sdk"
    NDK_ROOT="$SDK_ROOT/ndk/21.4.7075529"
else
    SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
    NDK_ROOT="${ANDROID_NDK_ROOT:-${ANDROID_NDK_HOME:-$SDK_ROOT/ndk/21.4.7075529}}"
fi
if [[ -d "$TOOL_ROOT/jdk-11" ]]; then
    JAVA_ROOT="$TOOL_ROOT/jdk-11"
else
    JAVA_ROOT="${JAVA_HOME:-}"
fi
DEPLOY_DIR="$ANDROID_DIR/build/deployment"
APK_DIR="$ANDROID_DIR/dist"

# Keep inherited IDE/Qt library settings out of this build.
unset LD_LIBRARY_PATH QTDIR QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH
unset QMAKEPATH QMAKESPEC ANDROID_SDK_HOME
unset JAVA_TOOL_OPTIONS _JAVA_OPTIONS GRADLE_OPTS

for required in \
    "$QT_ROOT/bin/qmake" \
    "$QT_ROOT/bin/androiddeployqt" \
    "$SDK_ROOT/platforms/android-33/android.jar" \
    "$SDK_ROOT/build-tools/34.0.0/aapt" \
    "$NDK_ROOT/source.properties" \
    "$JAVA_ROOT/bin/java"; do
    if [[ ! -e "$required" ]]; then
        printf 'Android build dependency missing: %s\n' "$required" >&2
        printf 'Set QT_ANDROID_ROOT, ANDROID_SDK_ROOT, ANDROID_NDK_ROOT and JAVA_HOME, or install under %s\n' "$TOOL_ROOT" >&2
        exit 1
    fi
done

# These values are scoped to this build process and its Gradle child process.
export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_NDK_ROOT="$NDK_ROOT"
export JAVA_HOME="$JAVA_ROOT"
export PATH="$QT_ROOT/bin:$JAVA_ROOT/bin:$SDK_ROOT/build-tools/34.0.0:/usr/bin:/bin"

mkdir -p "$DEPLOY_DIR" "$APK_DIR"
cd "$DEPLOY_DIR"
QT_BUILD_ROOT="$(realpath --relative-to="$DEPLOY_DIR" "$QT_ROOT")"

"$QT_BUILD_ROOT/bin/qmake" \
    -spec "$QT_BUILD_ROOT/mkspecs/android-clang" \
    "ANDROID_ABIS=arm64-v8a" \
    "ANDROID_TARGET_SDK_VERSION=33" \
    "ANDROID_SDK_ROOT=$SDK_ROOT" \
    "ANDROID_NDK_ROOT=$NDK_ROOT" \
    "$ANDROID_DIR/src/RS485Control.pro"
make -j"$(getconf _NPROCESSORS_ONLN)"

SETTINGS="$DEPLOY_DIR/android-RS485Control-deployment-settings.json"
if [[ ! -f "$SETTINGS" ]]; then
    printf 'qmake did not generate Android deployment settings: %s\n' "$SETTINGS" >&2
    exit 1
fi

export ANDROID_HOME="$SDK_ROOT"
export ANDROID_NDK_HOME="$NDK_ROOT"
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$TOOL_ROOT/gradle-home}"
export ANDROID_USER_HOME="${ANDROID_USER_HOME:-$TOOL_ROOT/android-user-home}"
export ANDROID_PREFS_ROOT="${ANDROID_PREFS_ROOT:-$ANDROID_USER_HOME}"
export PATH="$QT_ROOT/bin:$SDK_ROOT/cmdline-tools/latest/bin:$SDK_ROOT/platform-tools:$SDK_ROOT/build-tools/34.0.0:$JAVA_ROOT/bin:/usr/bin:/bin"

mkdir -p "$DEPLOY_DIR/libs/arm64-v8a"
cp "$DEPLOY_DIR/libRS485Control_arm64-v8a.so" \
    "$DEPLOY_DIR/libs/arm64-v8a/libRS485Control_arm64-v8a.so"

OUTPUT_APK="$APK_DIR/RS485Control-arm64-v8a-debug.apk"
# aux-mode expects a manifest in place; refresh it from our package source.
cp "$ANDROID_DIR/package/AndroidManifest.xml" "$DEPLOY_DIR/AndroidManifest.xml"
"$QT_ROOT/bin/androiddeployqt" \
    --input "$SETTINGS" \
    --output "$DEPLOY_DIR" \
    --android-platform android-33 \
    --jdk "$JAVA_ROOT" \
    --aux-mode
python3 - "$DEPLOY_DIR/AndroidManifest.xml" <<'PY'
from pathlib import Path
import sys

manifest = Path(sys.argv[1])
text = manifest.read_text(encoding="utf-8")
activity = 'android:name="com.rs485.control.MainActivity"'
if activity in text and "android:exported=" not in text:
    text = text.replace(
        'android:launchMode="singleTop">',
        'android:launchMode="singleTop" android:exported="true">',
        1,
    )
manifest.write_text(text, encoding="utf-8")
PY
# Remove the old package's generated Activity when reusing a previous build.
rm -f "$DEPLOY_DIR/src/com/rs485/launcher/MainActivity.java"
mkdir -p "$DEPLOY_DIR/src/com/rs485/control"
cp "$ANDROID_DIR/package/src/com/rs485/control/MainActivity.java" \
    "$DEPLOY_DIR/src/com/rs485/control/MainActivity.java"

# Gradle 5.6 reads gradle.properties as ISO-8859-1. Escape UTF-8 project paths
# as Java properties Unicode sequences so Qt paths remain valid on non-ASCII mounts.
python3 - "$DEPLOY_DIR/gradle.properties" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
path.write_text(
    "".join(f"\\u{ord(char):04x}" if ord(char) > 0x7e else char for char in text),
    encoding="ascii",
)
PY

cd "$DEPLOY_DIR"
./gradlew assembleDebug

BUILT_APK="$DEPLOY_DIR/build/outputs/apk/debug/deployment-debug.apk"
if [[ ! -s "$BUILT_APK" ]]; then
    printf 'Gradle did not produce an APK: %s\n' "$BUILT_APK" >&2
    exit 1
fi
if ! "$SDK_ROOT/build-tools/34.0.0/aapt" dump badging "$BUILT_APK" \
    | grep -q "^package: name='com.rs485.control' "; then
    printf 'Refusing to publish an APK with an unexpected package name: %s\n' "$BUILT_APK" >&2
    exit 1
fi
cp "$BUILT_APK" "$OUTPUT_APK"
if [[ ! -s "$OUTPUT_APK" ]]; then
    printf 'androiddeployqt did not produce an APK: %s\n' "$OUTPUT_APK" >&2
    exit 1
fi
printf 'APK built: %s\n' "$OUTPUT_APK"
