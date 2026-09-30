# Android 部署与设备预装指南

## 两种运行方式

| 路线 | 应用包名 | 构建入口 | 安装或更新入口 |
|---|---|---|---|
| 原生 Qt APK | `com.rs485.control` | `android/build_apk.sh` | `android/provision_apk.ps1` |
| Termux + Termux:X11 | `com.termux`、`com.termux.x11`，另有现场启动器 `com.rs485.launcher` | `android/build_device.sh`（在设备 Termux 内） | `android/provision.ps1`（已有启动器）、`android/deploy_device.sh`（业务程序更新） |

两条路线共用控制程序源码，但安装包、依赖环境与启动入口独立。可以同时安装，
运行时只启动一套控制程序，避免两个进程同时访问同一串口。

## 原生 Qt APK

### 前提

- 构建机使用 Qt 5.15.2 Android、NDK r21e、JDK 11、Android API 33；工具链位置见 [`android/README.md`](../android/README.md)。目标设备无需安装 NDK、Termux 或 Termux:X11。
- 构建机可通过 ADB 连接目标设备。现场 PA0715-N 使用厂商设置中的网络 ADB 调试入口，见 [`docs/DEVICE_PANEL_PA0715N.md`](DEVICE_PANEL_PA0715N.md)。
- 目标设备提供应用可访问的串口；APK 构建成功不代表串口权限已配置完成。

### 构建与安装

在仓库根目录构建：

```bash
./android/build_apk.sh
```

产物为 `android/dist/RS485Control-arm64-v8a-debug.apk`，包名为 `com.rs485.control`。
Windows 上可从任意工作目录调用安装脚本，APK 默认路径按脚本所在目录解析：

```powershell
powershell -File android/provision_apk.ps1 -DeviceAddr <设备IP>:<端口>
```

也可以直接使用 ADB：

```bash
adb connect <设备IP>:<端口>
adb -s <设备IP>:<端口> install -r android/dist/RS485Control-arm64-v8a-debug.apk
adb -s <设备IP>:<端口> shell am start -W -n com.rs485.control/.MainActivity
```

该入口只安装并启动原生应用，不配置 Termux、启动器桌面或 X11。
独立包名使它不会替换现场的 `com.rs485.launcher`；此前装过同包名测试版的设备，
需要在新应用中重新核对配置，旧应用数据不会自动迁移。

### GitHub Actions

推送或手动运行 `Native Android APK Build`，下载产物 `RS485Control-native-arm64-v8a`。
其中只有原生控制 APK，不包含 Termux 启动器或设备运行环境。

## Termux + Termux:X11

### 前提与首次部署边界

目标设备需要 Termux、Termux:X11、Termux 内的 Qt5/串口库，以及控制程序、配置和
启动脚本。业务程序目录为 `/data/data/com.termux/files/home/rs485/`。
先配置运行环境并放入完整源码，再在设备 Termux 中执行：

```bash
cd ~/rs485
bash android/build_device.sh
```

已有的 `start_rs485.sh` 负责启动显示服务和 `RS485Control`；开机启动、唤醒锁、
触控与日志检查见 [`docs/DEBUGGING_GUIDE.md`](DEBUGGING_GUIDE.md)。

当前仓库未提供完整的现场 `start_rs485.sh` 与 RUN_COMMAND/HOME 启动器源码。
`android/src/com/rs485/launcher/MainActivity.java` 仅为旧 QtActivity 全屏示例，不能
替代现场启动器。新设备需另行准备这些组件，不能把原生 APK 当作 Termux 启动器。

### 安装已有 Termux 启动器

在设备运行环境已配置完成后，安装由现场维护方提供、包名为 `com.rs485.launcher`
的启动器 APK：

```powershell
powershell -File android/provision.ps1 -DeviceAddr <设备IP>:<端口> -LauncherApk <已有启动器.apk>
```

省略 `-LauncherApk` 时默认读取 `android/dist/RS485Launcher-debug.apk`。
脚本检查 Termux 与 Termux:X11 是否已安装，再安装并打开启动器；它不安装原生控制
APK，也不自动配置桌面或常亮。通过启动器正常链路申请唤醒锁后，用以下命令核对：

```bash
adb -s <设备IP>:<端口> shell dumpsys power
```

输出中应有 `termux:service-wakelock`。直接从 ADB 调用 `termux-wake-lock` 的返回码
不能证明锁已生效；原理及恢复方法见调试手册。

### 更新已有 Termux 设备

`android/deploy_device.sh` 保留原有推送源码、设备端编译和重启流程。在仓库根目录执行：

```bash
adb connect <设备IP>:<端口>
ADB_DEVICE=<设备IP>:<端口> bash android/deploy_device.sh
```

该脚本用于已有环境的增量更新，不是首次部署。首次应放入完整源码，尤其是
`src/controlalgorithm.cpp`、`src/controlalgorithm.h`；增量脚本未推送这两个文件，
修改它们后须另行同步。更新会使用执行目录中的源码，部署前确认它是要发布的版本。

## 串口与显示核对

- 用 `adb -s <设备IP>:<端口> shell ls -l /dev/ttyS4 /dev/ttyS2` 检查节点与权限；现场串口以实测为准，不能按外壳编号猜测。
- Termux:X11 黑屏时先核对显示服务和控制进程，再打开 `com.termux.x11/.MainActivity`，见调试手册。原生 APK 不使用这条排障路径。
- 两条路线的空闲降亮仍使用当前共用实现；本次部署隔离不代表安卓原生亮度或 root 背光控制已经实现。
