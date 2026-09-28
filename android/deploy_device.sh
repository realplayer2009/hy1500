#!/usr/bin/env bash
set -euo pipefail

# 无线调试端口每次启用可能变化: 临时覆盖用
#   ADB_DEVICE=192.168.0.116:新端口 bash android/deploy_device.sh
ADB_DEVICE="${ADB_DEVICE:-192.168.0.116:43601}"
ADB="adb -s ${ADB_DEVICE}"
TERMUX_PKG="com.termux"
APP_USER="u0_a90"
APP_HOME="/data/data/${TERMUX_PKG}/files/home"
APP_RS485="${APP_HOME}/rs485"
START_SH="/data/local/tmp/start_rs485.sh"
# 新版安卓 /system/bin 已无 bash, run-as 下必须用 Termux 自己的 bash 绝对路径
TERMUX_BASH="/data/data/${TERMUX_PKG}/files/usr/bin/bash"

echo "=== Step 1: kill existing RS485Control ==="
$ADB shell "run-as ${TERMUX_PKG} ${TERMUX_BASH} -c 'pkill -f \"[R]S485Control\" 2>/dev/null || true'"
sleep 2
$ADB shell "ps -ef | grep -E '[R]S485Control' || echo 'process stopped'"

echo "=== Step 2: push changed source files ==="
FILES=(
  "src/rs485device.cpp"
  "src/rs485device.h"
  "src/applogic.cpp"
  "src/applogic.h"
  "src/appui.cpp"
  "src/appui.h"
  "src/main.cpp"
  "RS485Control.pro"
  "config/app.ini"
)

$ADB shell "mkdir -p /data/local/tmp/rs485_push_tmp"
for f in "${FILES[@]}"; do
  echo " pushing $f"
  $ADB push "$f" "/data/local/tmp/rs485_push_tmp/" 2>/dev/null || true
  $ADB shell "run-as ${TERMUX_PKG} cp /data/local/tmp/rs485_push_tmp/$(basename "$f") ${APP_RS485}/$f"
done

echo "=== Step 3: verify pushed files ==="
$ADB shell "run-as ${TERMUX_PKG} md5sum ${APP_RS485}/src/rs485device.cpp ${APP_RS485}/src/rs485device.h ${APP_RS485}/src/appui.cpp ${APP_RS485}/src/appui.h ${APP_RS485}/RS485Control.pro ${APP_RS485}/config/app.ini 2>/dev/null || echo 'md5 failed'"

echo "=== Step 4: rebuild on device ==="
# 构建脚本推送到设备执行, 避免内联命令的嵌套引号问题
cat > /tmp/rs485_build.sh <<'BUILD_EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -e
APP_RS485="$1"
PREFIX=/data/data/com.termux/files/usr
# run-as 环境下 PATH 不含 Termux bin, clang++ 等工具必须显式导出
export PATH="${PREFIX}/bin:${PATH}"
cd "$APP_RS485"
mkdir -p build/moc build/obj data/logs
echo "=== moc ==="
for h in rs485device appui applogic; do
    "${PREFIX}/bin/moc" "src/${h}.h" -o "build/moc/moc_${h}.cpp" -I src
done
echo "=== compile ==="
OBJS=""
for cpp in src/main.cpp src/controlalgorithm.cpp src/appui.cpp src/applogic.cpp src/rs485device.cpp build/moc/moc_rs485device.cpp build/moc/moc_appui.cpp build/moc/moc_applogic.cpp; do
    base=$(basename "$cpp" .cpp)
    obj="build/obj/${base}.o"
    echo "--- $cpp"
    clang++ -std=c++11 -O2 -fPIC -DQT_DEPRECATED_WARNINGS -DQT_NO_DEBUG -DQT_WIDGETS_LIB -DQT_GUI_LIB -DQT_CORE_LIB -I"${PREFIX}/include" -I"${PREFIX}/include/QtCore" -I"${PREFIX}/include/QtGui" -I"${PREFIX}/include/QtWidgets" -I"${PREFIX}/include/QtSerialPort" -Isrc -Ibuild/moc -c "$cpp" -o "$obj"
    OBJS="$OBJS $obj"
done
echo "=== link ==="
clang++ $OBJS -o RS485Control -L"${PREFIX}/lib" -lQt5Widgets -lQt5Gui -lQt5Core -lQt5SerialPort
echo "=== result ==="
ls -la RS485Control
echo BUILD_OK
BUILD_EOF
$ADB push /tmp/rs485_build.sh "/data/local/tmp/rs485_push_tmp/rs485_build.sh"
$ADB shell "run-as ${TERMUX_PKG} cp /data/local/tmp/rs485_push_tmp/rs485_build.sh ${APP_RS485}/rs485_build.sh"
$ADB shell "run-as ${TERMUX_PKG} ${TERMUX_BASH} ${APP_RS485}/rs485_build.sh ${APP_RS485}"

echo "=== Step 5: restart app ==="
# 启动脚本需要执行位, run-as 的 app 用户才能经 Termux bash 运行它
$ADB shell "chmod 777 ${START_SH} 2>/dev/null || true"
$ADB shell "run-as ${TERMUX_PKG} ${TERMUX_BASH} -c 'FORCE=1 ${START_SH}'"

echo "=== Step 6: verify ==="
sleep 3
$ADB shell "ps -ef | grep -E '[R]S485Control' || echo 'no process'"
$ADB shell "run-as ${TERMUX_PKG} tail -20 ${APP_HOME}/app_run.log 2>/dev/null || echo 'no log'"

echo "=== DONE ==="
