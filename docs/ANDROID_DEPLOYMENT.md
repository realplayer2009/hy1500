# Android 部署与设备预装指南

## 目标
把 `RS485Control` 部署到 RK3568  Android 设备，并通过 `com.rs485.launcher` 拉起 Termux X11 会话运行。

## 前提
- Mac 开发机已安装：Android SDK (`platform-tools`、`platforms;android-33`、`build-tools;34.0.0`)、JDK 17、Qt 5.15 for Android `arm64-v8a`
- 设备已开启 ADB/SSH，`adb connect <IP>:<PORT>` 可达
- 设备已安装 Termux、Termux:X11、`com.rs485.launcher`

## 方案 A：APK 构建（推荐长期方案）
1. 在 Mac 上安装 Qt 5.15 Android `arm64-v8a` 工具链。
2. 运行 `android/build_apk.sh` 生成 `android/dist/RS485Launcher-debug.apk`。
3. 推送到设备：`adb -s <device> install -r android/dist/RS485Launcher-debug.apk`
4. 用 `android/provision.ps1` 配置设备自启与 X11 拉起。

## 方案 B：GitHub Actions 自动构建
1. 推送代码到 GitHub。
2. 在 Actions 中运行 `Android Build` workflow。
3. 下载产物 `RS485Launcher-arm64-v8a` APK。
4. 通过 ADB 安装到设备。

## 设备预装脚本（`android/provision.ps1`）
```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceAddr
)

$ErrorActionPreference='SilentlyContinue'
adb connect $DeviceAddr
adb -s $DeviceAddr shell 'export PREFIX=/data/data/com.termux/files/usr; export PATH=$PREFIX/bin:$PATH; termux-wake-lock'
adb -s $DeviceAddr shell am start -n com.rs485.launcher/.MainActivity
adb -s $DeviceAddr shell 'export PREFIX=/data/data/com.termux/files/usr; export PATH=$PREFIX/bin:$PATH; bash ~/start_rs485.sh'
```

## 手动重启现有进程
如果设备上已有 `RS485Control` 在运行：
```bash
adb -s <device> shell 'export PREFIX=/data/data/com.termux/files/usr; export PATH=$PREFIX/bin:$PATH; pkill -f "[R]S485Control"; bash ~/start_rs485.sh'
```

## 故障排查
- `start_rs485.sh` 报 `~/rs485` 不存在：需要把 `RS485Control` 二进制放到 Termux 家目录的 `rs485` 子目录，或修改脚本指向实际路径。
- X11 黑屏：确认 Termux:X11 已启动，必要时执行 `adb shell am start -n com.termux.x11/.MainActivity`。
- 权限不足：ADB 连接使用 root 会话（当前设备 `adb root` 已生效）。
