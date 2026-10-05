# Android 部署与设备预装指南

十多台同型号屏的现场安装，请先按 [`批量安装指南.md`](批量安装指南.md) 执行：使用同一份已验收 APK，连接、安装、设置自启、首次替换开机画面并重启。本页保留构建、系统画面替换和旧 Termux 路线的详细说明。

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

APK 内携带共享 `config/app.ini` 和提示音。首次启动复制到应用私有 files 目录，
配置可编辑、日志可写；之后安装升级不覆盖已有配置。现场路径为
`/data/user/0/com.rs485.control/files/config/app.ini`，日志为同目录下的 `data/logs/`。
卸载应用或清除应用数据会删除这些配置和日志。

### 上电直接进入控制界面（原生 APK）

APK 同时提供普通应用和 HOME 入口，横屏全屏、保持屏幕唤醒，并在进入 Qt 前
拦截返回键。将它设为默认 HOME 后，系统启动及 Home 键都进入控制界面。
Kiosk 安装将应用注册为设备所有者；进入应用即启用锁定任务模式，禁用系统导航。
未配置设备所有者的普通安装仍只提供沉浸式全屏。

```bash
adb -s <设备IP>:<端口> shell dpm set-device-owner --user 0 com.rs485.control/.KioskAdminReceiver  # 首次设置一次
adb -s <设备IP>:<端口> shell cmd package set-home-activity --user 0 com.rs485.control/.MainActivity
adb -s <设备IP>:<端口> shell am start -W -n com.rs485.control/.MainActivity
adb -s <设备IP>:<端口> shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME
```

Windows 安装脚本加 `-Kiosk` 可同时设置设备所有者及默认 HOME：

```powershell
powershell -File android/provision_apk.ps1 -DeviceAddr <设备IP>:<端口> -Kiosk
```

2026-10-05 的新屏实测：设备为 `rk3562_t` / Android 13 / 1024×600，ADB 地址
`10.42.0.254:5555`（仅是该次现场地址）；厂商服务提供以下 system 设置，
原值均为 `unknow`，守护检测周期原值为 60 秒。先保存原值，再指定原生包名：

```bash
adb -s <设备IP>:<端口> shell settings put system xzjh_auto_boot_package_name com.rs485.control
adb -s <设备IP>:<端口> shell settings put system xzjh_daemon_package_name com.rs485.control
```

这两项是该厂商固件的接口，其他屏需使用自己的厂商设置。不要修改硬件看门狗的
喂狗配置来代替应用守护。验证上电行为时重启设备，不通过 ADB 手工启动应用，
待系统起来后检查默认 HOME、前台 Activity、两路串口句柄及屏幕画面。

本次真机已通过系统重启验证：日志确认宣传动画播放，随后自动显示控制 Activity，
没有原厂 Launcher 的 Displayed 记录；配置校验值保持一致，`ttyS4` 与 `ttyS2`
重新打开。Home 和返回键均保持控制界面，单次结束应用进程后界面自动恢复。
早期开机链路验收没有连接子板；2026-10-05 最新 APK 更新后已读到串口 1 / ID 1 的温湿度并持续记录 CSV，三路加热器保持关闭。输出接线、负载加热和联锁触发仍须现场验收，完整更新记录见批量安装指南。

现场维护时恢复原厂桌面及原始守护配置（下列 `unknow` 为实测原值拼写）：

```bash
adb -s <设备IP>:<端口> shell am broadcast -a com.rs485.control.MAINTENANCE -n com.rs485.control/.KioskMaintenanceReceiver --ez enabled true
adb -s <设备IP>:<端口> shell settings put system xzjh_auto_boot_package_name unknow
adb -s <设备IP>:<端口> shell settings put system xzjh_daemon_package_name unknow
adb -s <设备IP>:<端口> shell cmd package set-home-activity --user 0 com.android.launcher3/.uioverrides.QuickstepLauncher
adb -s <设备IP>:<端口> shell input keyevent KEYCODE_HOME
```

维护完成恢复导航锁：`adb -s <设备IP>:<端口> shell am broadcast -a com.rs485.control.MAINTENANCE -n com.rs485.control/.KioskMaintenanceReceiver --ez enabled false`，再启动控制应用。

这里只恢复桌面入口，不卸载程序，不清除业务配置和历史数据。启动早期的厂商
Logo 和系统开机动画不由默认 HOME 控制，需要分别处理；本次设备的动画播放器
没有 `/data/local/bootanimation.zip` 覆盖路径，不能照旧版 Android 教程推送到该路径。

### 宣传开机动画（该 root 设备）

```bash
bash scripts/make_bootanimation.sh assets/boot_animation_source.mp4
adb -s <设备IP>:<端口> root
adb connect <设备IP>:<端口>
adb -s <设备IP>:<端口> remount
```

本屏直接 `mount -o rw,remount /` 会报 `Invalid argument`；`adb remount` 使用
overlayfs 提供可写的 `/system`。按其输出要求重启、重连并重新获取 root。
确认 `/system` 可写后部署（首次保留原厂备份，重复部署不覆盖备份）：

```bash
adb -s <设备IP>:<端口> push /tmp/bootanim/bootanimation.zip /data/local/tmp/rs485-bootanimation.zip
adb -s <设备IP>:<端口> shell 'set -e; if [ ! -e /system/media/bootanimation.zip.orig.bak ]; then cp -p /system/media/bootanimation.zip /system/media/bootanimation.zip.orig.bak; fi; cp /data/local/tmp/rs485-bootanimation.zip /system/media/bootanimation.zip.new; chown root:root /system/media/bootanimation.zip.new; chmod 644 /system/media/bootanimation.zip.new; chcon u:object_r:system_file:s0 /system/media/bootanimation.zip.new; mv /system/media/bootanimation.zip.new /system/media/bootanimation.zip'
adb -s <设备IP>:<端口> reboot
```

产物为 1024×600、30 fps、180 帧宣传视频加一帧等待画面，约 21 MiB。
视频完整播放一次，随后保持末帧直到系统完成启动。帧数不能写在动画描述的
段类型位置，ZIP 必须使用 store，转换脚本已处理这两点。

2026-10-05 部署时本机备份另存于
`android/dist/device-backup/bootanimation.factory.zip`，设备备份为
`/system/media/bootanimation.zip.orig.bak`，桌面及守护原值备份为
`/data/local/tmp/rs485-kiosk-before.txt`。这些本机构建输出不进版本库。
恢复动画时在 root 且 `/system` 可写的情况下执行：

```bash
adb -s <设备IP>:<端口> shell cp -p /system/media/bootanimation.zip.orig.bak /system/media/bootanimation.zip
adb -s <设备IP>:<端口> reboot
```

开机动画与最早的静态图是两个独立阶段，静态图替换方法见下一节。

### 最早静态 Logo（该厂商固件）

2026-10-05 已将 U-Boot 和内核两阶段静态图替换为“裕泰通新能源”。
源文件 [`assets/boot_logo.bmp`](../assets/boot_logo.bmp) 从宣传视频第 4 秒提取，
1024×600、8-bit 灰度调色板、未压缩 BMP，与原厂 BMP 的 8-bit 格式一致。
完整流程为：静态 Logo → 宣传视频 → 全屏控制界面。

该屏有独立的 16 MiB `/dev/block/by-name/logo` 分区。原分区全为零，因此回退
到 `boot` 内置资源。实际厂商服务 `XzjhSystemService.xzjhSetUbootAndKernelLogo`
将第一张 BMP 按 512 字节对齐，再拼接第二张 BMP 写入该分区；不修改 `boot`。
本固件 `IXzjhSystemService` 的此方法事务号经设备 framework 核对为 **117**，
其他固件需重新核对，不能直接套用事务号。

重新制作同一幅静态图：

```bash
ffmpeg -y -ss 4 -i assets/boot_animation_source.mp4 -frames:v 1 -vf 'scale=1024:600:force_original_aspect_ratio=decrease,pad=1024:600:(ow-iw)/2:(oh-ih)/2,format=gray' -pix_fmt gray assets/boot_logo.bmp
```

部署前首次备份 `logo` 分区，拉到本机保存，重复部署不要覆盖原厂备份。
本次已有本机备份 `android/dist/device-backup/logo.factory.img`，设备备份
`/data/local/tmp/rs485-logo.factory.img`；额外保留 `boot.factory.img` 作为核对基线。

```bash
adb -s <设备IP>:<端口> root
adb connect <设备IP>:<端口>
adb -s <设备IP>:<端口> push assets/boot_logo.bmp /data/local/tmp/rs485-boot-logo.bmp
adb -s <设备IP>:<端口> shell service call xzjh 117 s16 /data/local/tmp/rs485-boot-logo.bmp s16 /data/local/tmp/rs485-boot-logo.bmp
adb -s <设备IP>:<端口> shell sync
adb -s <设备IP>:<端口> reboot
```

服务返回的零不能单独证明写入成功，应读取分区并核对两张 BMP。
本次回读第一张图起始为 0，第二张为 615936 字节，均与源文件逐字节一致；
重启后 `logo` 分区 SHA256 为
`bd14ba66dc405f9d412bf77500a62c6ca8501f5d9b5ad68b04015c59498f515a`，
`boot` 的 SHA256 仍为
`5c3d9b018db6aa5fd4cc5e27c44e52a6e93c366b975b837252402db740f113b0`。
最早的画面发生在 ADB 启动前，不能用重连后的截图代替验证；本次用户已现场
目视确认自己的静态 Logo、宣传视频、控制界面依次正常出现。

恢复原厂静态图（root 下写回本次备份；原分区为空，恢复后重新使用固件内置图）：

```bash
adb -s <设备IP>:<端口> push android/dist/device-backup/logo.factory.img /data/local/tmp/rs485-logo.factory.img
adb -s <设备IP>:<端口> shell 'dd if=/data/local/tmp/rs485-logo.factory.img of=/dev/block/by-name/logo bs=1M && sync'
adb -s <设备IP>:<端口> reboot
```

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
- 原生 APK 已通过 Android 窗口 `screenBrightness` 异步设置亮度，无需系统设置写权限；Linux/Termux 使用原有后端。原生应用退到后台时窗口亮度覆盖失效。
- 同时检查 `adb -s <设备IP>:<端口> shell getenforce`：测试机为 `Permissive`。若其他固件为 `Enforcing` 且日志有 `avc: denied`，文件权限放开也可能打不开串口，应由厂商配置应用访问串口的 SELinux 策略，不把永久关闭 SELinux 当作安装步骤。
