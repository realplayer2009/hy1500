# Android 部署与设备预装指南

## 两种运行方式

项目保留两种 Android 运行方式：Qt APK 直接运行控制界面；Termux + Termux:X11
运行 Linux 版本并提供远程维护/启动脚本。两者的启动链路和串口权限配置不同，不能把
APK 构建成功当作 Termux/X11 环境已经配置完成。

## 前提
- Qt APK 构建使用仓库根目录 `.android-toolchain/` 下的项目专用 Android SDK、NDK r21e、JDK 11 和 Qt 5.15.2；详见 [`android/README.md`](../android/README.md)。无需在目标设备安装 NDK。
- 设备已开启 ADB/SSH，`adb connect <IP>:<PORT>` 可达
- 设备已安装 Termux、Termux:X11、`com.rs485.launcher`

## Qt APK 构建

运行 `./android/build_apk.sh`，生成 `android/dist/RS485Control-arm64-v8a-debug.apk`；
再用 `adb -s <device> install -r android/dist/RS485Control-arm64-v8a-debug.apk` 安装。
APK 启动 Qt 控制界面。设备侧的串口权限需要单独验证。

## Termux + Termux:X11 方式

这条路径运行 Termux 内编译的 Linux 二进制，不依赖 Qt Android APK；启动脚本和设备
预装步骤见下文及 [`docs/DEBUGGING_GUIDE.md`](DEBUGGING_GUIDE.md)。

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
