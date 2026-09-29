# Android 本机构建

## 工具链隔离

本机可将 Android 工具链安装在仓库根目录的 `.android-toolchain/`，不会写入系统 SDK、Java、Qt，
也不会修改 shell profile。其他机器可通过 `QT_ANDROID_ROOT`、`ANDROID_SDK_ROOT`、
`ANDROID_NDK_ROOT`、`JAVA_HOME` 指向已有安装；对应的项目本地目录存在时优先使用本地版本。
CI 使用环境变量提供的安装路径，不依赖本机目录。
当前按 Qt 5.15.2 Android、NDK r21e、JDK 11、Android API 33
和 Build Tools 34 配置。Qt 生成的 AGP 3.6.0 工程还会使用 Build Tools 28.0.3，因此两个
Build Tools 版本都保留在项目本地 SDK 中。该目录已加入 `.gitignore`，不进版本库。

项目位于外接 NTFS 盘，因为项目所在 exFAT 盘不支持 Qt 和 JDK 安装包所需的符号链接。
外接盘卸载时，工具链和项目都不可用。

## 构建 APK

从项目任意目录运行：

```bash
./android/build_apk.sh
```

脚本只在当前构建进程中设置工具链路径；默认 Gradle 缓存和 Android 用户缓存放在
`.android-toolchain/`，也可用 `GRADLE_USER_HOME`、`ANDROID_USER_HOME` 覆盖。
生成文件为 `android/dist/RS485Control-arm64-v8a-debug.apk`。构建主机需要 Linux 和
Qt 5.15.2 Android 的 arm64-v8a 工具链。

当前 APK 包含 RS485Control Qt 界面和全屏 Activity。设备安装、Termux/X11 启动以及真实
串口权限仍需按 `docs/ANDROID_DEPLOYMENT.md` 和 `docs/DEBUGGING_GUIDE.md` 配置。
