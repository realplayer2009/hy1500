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
# --aux-mode 只"更新"输出目录里已有的工程文件, 不会复制模板:
#   main.cpp: if (options.build && !options.auxMode) { copyAndroidTemplate(...); }
# 因此干净检出时 res/values/libs.xml 不存在, updateLibsXml 直接报
# "Cannot find ... in prepared packaged. This file is required." 并退出 12,
# 后续 ./gradlew 也没有 build.gradle/gradlew 可用。这里按 copyAndroidTemplate
# 的做法(纯递归拷贝)先把 Qt 自带的 Gradle 与 Android 模板铺到输出目录,
# 让 aux-mode 与 gradlew 都能工作; 之后再用我们自己的清单覆盖模板里的那份。
for TPL in "src/3rdparty/gradle" "src/android/templates"; do
    if [[ ! -d "$QT_ROOT/$TPL" ]]; then
        printf 'Qt template directory missing: %s\n' "$QT_ROOT/$TPL" >&2
        printf 'The Qt Android package must ship src/3rdparty/gradle and src/android/templates.\n' >&2
        exit 1
    fi
    cp -R "$QT_ROOT/$TPL/." "$DEPLOY_DIR/"
done
# aux-mode expects a manifest in place; refresh it from our package source.
cp "$ANDROID_DIR/package/AndroidManifest.xml" "$DEPLOY_DIR/AndroidManifest.xml"
# aux-mode 也不走 buildAndroidProject() (main.cpp 的 aux 分支在它之前就 return 0),
# 因此不会写 gradle.properties 里 build.gradle 需要的属性。模板自带的
# gradle.properties 不含它们, 于是 build.gradle 的
#   compileSdkVersion androidCompileSdkVersion
# 报 "Could not get unknown property 'androidCompileSdkVersion'"。
# 这里按 buildAndroidProject 的做法, 从 qmake 生成的 deployment settings 与 NDK
# 的 source.properties 取值, 合并进 gradle.properties (保留原有行与注释),
# 同时写 local.properties 的 sdk.dir, 并保证 gradlew 可执行。
python3 - "$SETTINGS" "$DEPLOY_DIR" "$SDK_ROOT" "$NDK_ROOT" "$QT_ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

settings_path, deploy, sdk_root, ndk_root, qt_root = sys.argv[1:6]
settings = json.loads(Path(settings_path).read_text(encoding="utf-8"))

def setting(key, default=""):
    value = settings.get(key)
    return default if value is None else str(value)

# NDK 版本取自 NDK 的 source.properties (Pkg.Revision), 与 androiddeployqt 一致
ndk_version = ""
for line in Path(ndk_root, "source.properties").read_text(
    encoding="utf-8", errors="replace"
).splitlines():
    if line.strip().startswith("Pkg.Revision"):
        ndk_version = line.split("=", 1)[1].strip()

# 只有 build.gradle 显式 .toInteger() 时才给整数形式, 否则用 android-33 字符串
build_gradle = Path(deploy, "build.gradle").read_text(encoding="utf-8", errors="replace")
platform = setting("android-platform", "android-33")
compile_sdk = (
    platform.split("-")[-1]
    if "androidCompileSdkVersion.toInteger()" in build_gradle
    else platform
)

architectures = settings.get("architectures") or {}
props = {
    "buildDir": "build",
    "qt5AndroidDir": str(Path(qt_root, "src", "android", "java")),
    "androidCompileSdkVersion": compile_sdk,
    "qtMinSdkVersion": setting("android-min-sdk-version", "21") or "21",
    "qtTargetSdkVersion": setting("android-target-sdk-version", "31") or "31",
    "androidNdkVersion": ndk_version,
    "androidBuildToolsVersion": setting("sdkBuildToolsRevision"),
    "qtTargetAbiList": ",".join(architectures) if architectures else "arm64-v8a",
}

def merge(path, values, fill_only=()):
    path = Path(path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    out, used = [], set()
    for line in lines:
        match = re.match(r"\s*([^#=\s][^=]*?)\s*=", line)
        key = match.group(1) if match else None
        if key is not None and key in values and key not in used:
            # fill_only 的键沿用文件里已有的值 (与 buildAndroidProject 对
            # androidBuildToolsVersion 的处理一致: 仅在为空时才补)
            out.append(line if key in fill_only else f"{key}={values[key]}")
            used.add(key)
        else:
            out.append(line)
    for key, value in values.items():
        if key not in used and value != "":
            out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")

merge(Path(deploy, "gradle.properties"), props, fill_only=("androidBuildToolsVersion",))
merge(Path(deploy, "local.properties"), {"sdk.dir": sdk_root})
PY
chmod +x "$DEPLOY_DIR/gradlew"
"$QT_ROOT/bin/androiddeployqt" \
    --input "$SETTINGS" \
    --output "$DEPLOY_DIR" \
    --android-platform android-33 \
    --jdk "$JAVA_ROOT" \
    --aux-mode

# Bundle the shared defaults; the app copies them to writable storage only once.
mkdir -p "$DEPLOY_DIR/assets/config" "$DEPLOY_DIR/assets/assets"
cp "$PROJECT_DIR/config/app.ini" "$DEPLOY_DIR/assets/config/app.ini"
cp "$PROJECT_DIR/assets/click.wav" "$DEPLOY_DIR/assets/assets/click.wav"
cp -R "$ANDROID_DIR/package/res/." "$DEPLOY_DIR/res/"
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
cp "$ANDROID_DIR/package/src/com/rs485/control/"*.java \
    "$DEPLOY_DIR/src/com/rs485/control/"

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

# 显式使用项目签名，不覆盖用户的全局 debug.keystore。
KEYSTORE_SRC="$ANDROID_DIR/rs485.keystore"
if [[ ! -s "$KEYSTORE_SRC" ]]; then
    printf 'Android signing keystore missing: %s\n' "$KEYSTORE_SRC" >&2
    printf 'Generate it with keytool and commit it as the project signing key.\n' >&2
    exit 1
fi
if ! "$JAVA_ROOT/bin/keytool" -list -keystore "$KEYSTORE_SRC" -storepass android \
    >/dev/null 2>&1; then
    printf 'Android signing keystore is not readable with the expected alias/password: %s\n' \
        "$KEYSTORE_SRC" >&2
    exit 1
fi
printf 'Signing key: %s (alias androiddebugkey)\n' "$KEYSTORE_SRC"
"$JAVA_ROOT/bin/keytool" -list -v -keystore "$KEYSTORE_SRC" -storepass android 2>/dev/null \
    | grep -m1 'SHA256:' | sed 's/^[[:space:]]*/  /' || true
python3 - "$DEPLOY_DIR/build.gradle" "$KEYSTORE_SRC" <<'PY_SIGNING'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open("a", encoding="utf-8") as out:
    out.write("\nandroid { signingConfigs { debug {\n")
    out.write("    storeFile file(" + json.dumps(sys.argv[2]).replace("$", "\\$") + ")\n")
    out.write('    storePassword "android"\n    keyAlias "androiddebugkey"\n    keyPassword "android"\n')
    out.write("} } }\n")
PY_SIGNING

cd "$DEPLOY_DIR"
./gradlew assembleDebug

BUILT_APK="$DEPLOY_DIR/build/outputs/apk/debug/deployment-debug.apk"
if [[ ! -s "$BUILT_APK" ]]; then
    printf 'Gradle did not produce an APK: %s\n' "$BUILT_APK" >&2
    exit 1
fi
# 核对成品 APK 的签名证书就是仓库密钥: 面板只能接受同一密钥的覆盖升级, 签名不一致
# 时装不上(INSTALL_FAILED_UPDATE_INCOMPATIBLE), 必须在这里失败而不是静默产出。
python3 - "$BUILT_APK" "$KEYSTORE_SRC" "$JAVA_ROOT/bin/keytool" <<'PY'
import re
import subprocess
import sys

apk, keystore, keytool = sys.argv[1], sys.argv[2], sys.argv[3]

def fingerprint(args):
    out = subprocess.run(args, capture_output=True, text=True).stdout
    match = re.search(r"SHA256:\s*([0-9A-Fa-f:]+)", out)
    return match.group(1).upper() if match else None

apk_fp = fingerprint([keytool, "-printcert", "-jarfile", apk])
key_fp = fingerprint([keytool, "-list", "-v", "-keystore", keystore, "-storepass", "android"])
if not apk_fp or not key_fp:
    print("warning: cannot read certificate fingerprints to verify signing", file=sys.stderr)
    sys.exit(0)
if apk_fp != key_fp:
    print(
        "APK was signed with an unexpected certificate; it cannot be installed "
        "over an existing build on the panel.",
        file=sys.stderr,
    )
    print(f"  APK:      {apk_fp}", file=sys.stderr)
    print(f"  Keystore: {key_fp}", file=sys.stderr)
    sys.exit(1)
print(f"APK signature verified against the project keystore: {apk_fp}")
PY
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
