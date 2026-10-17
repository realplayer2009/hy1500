# Android 组件工程取舍

> 后续修改本组件的 agents 请继续维护本文档；记录格式为“问题 + 解决方案选择 + 解释”。

- 问题：原生 APK 拖动亮度时同步执行系统 settings 命令，会卡住 Qt 事件处理且可能因缺少系统设置权限失败。解决方案选择：由 RS485_NATIVE_ANDROID 构建路径通过 QtAndroid::runOnAndroidThread 设置当前 Activity 的 WindowManager.LayoutParams.screenBrightness。解释：窗口亮度由应用自身控制，异步更新不等待外部进程；只影响本应用前台窗口，Termux 和 Linux 仍使用原有后端。

- 问题：原生 Qt APK 与 Termux 启动器共用 `com.rs485.launcher` 包名，安装时可能覆盖启动器或遇到签名冲突；预装脚本又混用两条启动链路。
- 解决方案选择：原生 APK 改用 `com.rs485.control`，由 `provision_apk.ps1` 安装；`provision.ps1` 保留 Termux 启动器入口，接收现场已有启动器 APK，Termux 编译和更新脚本保持独立；构建复用目录时移除旧包名的生成 Activity，并在 aux-mode 前用源清单覆盖生成清单，输出前核对成品包名。
- 解释：两种应用可独立安装升级，原生 CI 产物不能替代 Termux 启动器；Qt aux-mode 读取已有生成清单，仅改源清单仍会产出旧包名，删除生成清单又会导致打包失败，因此必须先刷新它再校验成品。旧 QtActivity 示例不具备现场 RUN_COMMAND/HOME 链路，不能声明本仓库能构建完整的 Termux 启动器。唤醒锁由正常启动链路申请，去掉 ADB 直接调用的假成功路径。

- 问题：只从 `.android-toolchain/` 查找工具链会使 CI 即使通过 setup-java/setup-qt 安装完成也在依赖检查时失败。
- 解决方案选择：APK 脚本使用 `QT_ANDROID_ROOT`、`ANDROID_SDK_ROOT`、`ANDROID_NDK_ROOT`、`JAVA_HOME` 覆盖默认的项目本地路径；CI 显式传入其安装路径。
- 解释：本机仍可使用被 Git 忽略的隔离工具链，编译机可使用自己的安装位置，脚本中的版本检查保证两者使用同一目标 API 和 NDK 版本。

- 问题：在含中文的本机项目路径下，以绝对路径调用 Qt 5.15.2 的 qmake 或传入绝对 mkspec 路径会报 `Could not find feature thread`；同一工具链从构建目录以相对路径调用可正常解析。
- 解决方案选择：构建时从输出目录计算到 Qt 安装的相对路径，用于 qmake 和 `android-clang` mkspec。
- 解释：Qt 安装位置仍由本机目录或环境变量决定；相对调用只修正旧 qmake 对当前路径的特征文件查找，不固定编译机的目录结构。

- 问题：Qt 5.15.2 生成的 Android 工程使用 Gradle 5.6.4 和 Android Gradle Plugin 3.6.0，Gradle 5.6.4 不支持在 JDK 17 上运行，而仓库原 CI 和文档指定了 JDK 17。
- 解决方案选择：Android 本机构建与 CI 统一使用 JDK 11，保持 Qt 5.15.2 默认生成的 Gradle/AGP 版本，不升级旧 Android 构建模板。
- 解释：JDK 11 可运行 Gradle 5.6.4，避免升级 AGP 对 Qt 5.15.2 旧模板和打包流程造成的额外兼容改动；JDK 安装在项目 `.android-toolchain/` 中，不覆盖系统 Java。

- 问题：工程位于含中文目录名的 NTFS 挂载路径，Gradle 5.6 按 Java properties 规则读取 `gradle.properties` 时会把 Qt 源码路径中的 UTF-8 字节解码成乱码，导致 QtActivity 源码无法参与编译。
- 解决方案选择：`androiddeployqt --aux-mode` 生成 Gradle 工程后，构建脚本把 properties 中非 ASCII 字符转换为 `\uXXXX`，再用项目本地 Gradle 执行 `assembleDebug`。
- 解释：Java properties 的 Unicode 转义会在读取时还原成原路径；这样保留项目在外接 NTFS 盘上的目录结构，也无需改系统环境或移动源码。

- 问题：Android 12（API 31）及以上要求带有 intent-filter 的 Activity 显式声明 `android:exported`，否则系统拒绝解析 APK。
- 解决方案选择：给作为桌面启动入口且声明 MAIN/LAUNCHER intent-filter 的 `MainActivity` 设置 `android:exported="true"`。
- 解释：系统启动器需要能够从应用外启动该 Activity；显式声明满足 Android 12+ 安装要求并保留应用图标启动能力。

- 问题：PA0715-N 一台设备通过 ADB 流式覆盖安装后，APK 内正常的 `libc++_shared.so` 在应用目录中被提取成全零内容，启动时因 ELF magic 为 `00000000` 闪退；同一 APK 改用非流式覆盖安装后库文件恢复正常并可启动。
- 解决方案选择：原生 APK 的安装入口统一使用 `adb install --no-streaming -r`。
- 解释：牺牲流式安装的少量传输便利，确保这类设备完整落盘 native 库；保留 `-r` 以继续升级应用并保留现场配置和历史数据。

- 问题：PA0715-N 一台已有设备所有者的屏覆盖安装后，设备所有者记录仍存在，但 `KioskAdminReceiver` 未出现在活动管理员列表；Activity 恢复时调用 `setLockTaskPackages` 因 UID 不匹配而抛出 `SecurityException` 并闪退。
- 解决方案选择：Kiosk 安装流程在确认或设置设备所有者后，显式执行 `dpm set-active-admin --user 0 com.rs485.control/.KioskAdminReceiver`。
- 解释：重新激活同一管理组件即可恢复导航锁调用，不删除设备所有者、不清除现场应用数据。

- 问题：Android 默认 HOME 和 PA0715-N 厂商开机自启/守护由两套机制控制，只设置其中一处会出现按 Home 或开机启动行为不完整。
- 解决方案选择：Kiosk 安装统一将 `com.rs485.control/.MainActivity` 设为 Android HOME，并通过厂商工程设置将 `xzjh_auto_boot_package_name`、`xzjh_daemon_package_name` 都设为 `com.rs485.control`。
- 解释：Android HOME 负责桌面选择，厂商工程项负责开机拉起和守护；两者同时设置，重启和按 Home 都进入控制软件。

- 问题：原生 APK 未携带现场配置，启动工作目录也不保证可写，空白屏安装后界面可显示但串口列表为空。
- 解决方案选择：打包共享 `config/app.ini` 与提示音，原生 Android 启动时在应用私有 files 目录中仅首次复制，后续配置和日志都使用该可写工作目录；仅 APK 工程定义 `RS485_NATIVE_ANDROID` 开启该路径。
- 解释：APK assets 只读，不能作为保存路径；升级保留现场已有配置，桌面 Linux 与 Termux 的配置查找规则不变。Termux 同样运行于 Android，不能只用 `Q_OS_ANDROID` 区分两条部署路线。私有数据在卸载/清除应用数据时会删除，升级用 `install -r`。

- 问题：原生 Qt Activity 在 `onBackPressed()` 之前将返回键转发给 Qt，单独覆盖该方法仍会触发主窗口退出提示。
- 解决方案选择：在 `dispatchKeyEvent()` 中消费返回键的按下和释放，HOME 仍交给系统选择已配置的默认桌面。
- 解释：控制程序作为专用桌面时，返回键不能关闭控制窗口；需要维护时通过 ADB 恢复默认桌面或显式打开设置。

- 问题：Qt `androiddeployqt --aux-mode` 未将新增样式复制到复用构建目录，清单引用 `RS485Theme` 时资源链接失败。
- 解决方案选择：aux-mode 后显式复制本项目 `package/res`，与已有 Activity 和共享 assets 一起刷新。
- 解释：保留原 aux-mode 构建流程，同时保证新增及更新资源进入最终 APK。

- 问题：沉浸式全屏只隐藏系统栏，底部上滑仍能调出导航按钮，默认 HOME 和消费返回键也无法禁止最近任务。解决方案选择：安装脚本在 Kiosk 模式下将本应用注册为设备所有者，Activity 恢复前台时配置仅允许本包的锁定任务模式，关闭全部可选系统导航功能；ADB 通过受 DUMP 权限保护的维护广播移除锁定白名单并暂停自动锁定，维护完成后显式恢复。解释：由 Android 系统约束导航，避免依赖反复隐藏或厂商“隐藏系统栏”配置；未授权设备所有者时不调用 startLockTask，避免进入可手动退出且弹确认框的屏幕固定模式。

- 问题：本机 `am task lock stop` 解锁后 Activity 立即恢复前台，onResume 又会重新锁定，无法稳定打开维护设置。解决方案选择：维护广播先持久保存暂停锁定状态，再移除锁定白名单；完成后以 enabled=false 恢复并启动应用，接收器要求 android.permission.DUMP。解释：暂停状态先落盘保证重启或焦点变化不意外重新锁定，普通应用不能发送此维护指令；现场必须显式结束维护。

- 问题：`build-apk.yml` 引用的 `actions/setup-qt@v4` 在 GitHub 上不存在（404），runner 在 "Prepare all required actions" 阶段即报 `Unable to resolve action actions/setup-qt, repository not found` 并失败，该工作流自建立以来从未产出过 APK，且失败点与代码无关、难以从运行摘要看出。解决方案选择：改用社区维护的 `jurplel/install-qt-action@v4`，参数名同步由 `qt-version` 改为 `version`；`target: android`、`arch: android` 保持不变。解释：Qt 官方并未提供 `actions/setup-*` 体系的 setup-qt，install-qt-action 是唯一在维护的通用方案；参数名差异是该 action 的既有约定，改工作流即可，不需要动构建脚本。

- 问题：同一工作流里 `modules: qtandroidextras qtserialport` 让 aqt 报 `The packages [...] were not found while parsing XML of package information!`。原因是 Qt 5.15.2 的 android 只有 `qt.qt5.5152.android` 一个基础包，其压缩包名为 `qtbase-Linux-RHEL_7_6-Clang-Android-Android_ANY-Multi.7z` 形式，qtbase/qtserialport/qtandroidextras 都是该包**内部的 archive**，而不是 PackageUpdate 级别的独立 module/package；aqt 的 `--modules` 只匹配后者，因此永远找不到。解决方案选择：去掉 `modules` 输入，安装整个基础包（`aqt list-qt linux android --archives 5.15.2 android` 可核实其已含 core/gui/widgets/serialport/androidextras）；不要改用 `archives` 输入，因为 aqt 对基础包同样按 archive 名过滤，少写 qtbase 会被判定为 `nopatch` 而不装基础包。解释：5.15 的 android 包是 Android_ANY-Multi 单包（含全部 ABI），arm64 由 `build_apk.sh` 的 `ANDROID_ABIS=arm64-v8a` 选出；若 ABI 装错，该脚本复制 `libRS485Control_arm64-v8a.so` 会直接失败，不会静默产出坏包。

- 问题：`build_apk.sh` 用 `androiddeployqt --aux-mode` 在干净检出上构建时退出 12，报 `Cannot find .../deployment//res/values/libs.xml in prepared packaged. This file is required.`，后续 `./gradlew` 也没有 `build.gradle`/`gradlew` 可用。原因是 aux 分支只调 `updateAndroidFiles()`，不调 `copyAndroidTemplate()`（`main.cpp`：`if (options.build && !options.auxMode) { cleanAndroidFiles(); copyAndroidTemplate(); }`，aux 分支在其后直接 `return 0`），`--no-build` 同样不复制模板；而 `updateLibsXml()` 只更新已存在的 `res/values/libs.xml`，不存在就报错退出。此前能构建只是因为复用了被 gitignore 的暖构建目录。解决方案选择：在 aux-mode 前按 `copyAndroidTemplate()` 的做法（纯递归拷贝）把 Qt 自带的 `$QT_ROOT/src/3rdparty/gradle` 与 `$QT_ROOT/src/android/templates` 铺到输出目录，再用我们自己的 `AndroidManifest.xml` 覆盖模板那份；`updateAndroidManifest` 只做占位符替换、不改写已有的 `package="com.rs485.control"`，包名仍然正确。解释：保留 aux-mode 刻意设计（刷新生成清单才能产出新包名，删除生成清单又会导致打包失败），只补上它假定已存在的模板文件。

- 问题：铺好模板后 Gradle 5.6.4 能启动却在配置阶段失败，报 `Could not get unknown property 'androidCompileSdkVersion' for object of type ...BaseAppModuleExtension`（build.gradle 第 37 行）。原因是 `buildAndroidProject()` 才会写这些属性（`buildDir`/`qt5AndroidDir`/`androidCompileSdkVersion`/`qtMinSdkVersion`/`qtTargetSdkVersion`/`androidNdkVersion`/`androidBuildToolsVersion`/`qtTargetAbiList`，以及 `local.properties` 的 `sdk.dir`，并给 `gradlew` 加可执行位），而 aux 分支在它之前就 `return 0`，模板自带的 `gradle.properties` 不含它们。解决方案选择：在 aux-mode 前按 `buildAndroidProject` 的做法补齐——值取自 qmake 生成的 deployment settings 与 NDK 的 `source.properties`（`Pkg.Revision`），合并时保留文件原有行与注释（`mergeGradleProperties` 语义）；`androidCompileSdkVersion` 按 build.gradle 是否含 `.toInteger()` 决定给 `android-33` 还是 `33`；`androidBuildToolsVersion` 沿用“仅缺失时补”，因为模板自带的 `28.0.3` 与 AGP 3.6.0 配套。解释：值与源码逻辑一致，不硬编码 SDK 版本；顺带补上 `sdk.dir` 和 `gradlew` 可执行位，避免依赖环境变量。

- 问题：补齐属性后 Gradle 跑完 25 个任务，最后挂在 `:stripDebugDebugSymbols`，报 `A problem occurred starting process '.../sdk/ndk/30.0.16248370/toolchains/llvm/prebuilt/linux-x86_64/bin/aar...'` 与 `Ignoring invalid ABI 'riscv64' found in ABI metadata file '.../ndk/30.0.16248370/meta/abis.json'`。原因是 qtbase **v5.15.2 标签**的模板（注意与 5.15 分支 tip 不同：分支已升到 AGP 7.0.2 且写了 `ndkVersion`）声明 AGP 3.6.0、`buildToolsVersion '28.0.3'` 硬编码、**没有 `ndkVersion` 行**，AGP 3.6.0 只能回退到 `ANDROID_NDK_HOME` 或“SDK 里最新的 NDK”；runner 镜像预装了 NDK 30 等，于是用了 NDK 30。本机 `.android-toolchain/sdk` 通常只有 21.4.7075529 一个 NDK，所以本地从未触发。解决方案选择：在 CI 里把多余的 NDK 移到 `/tmp/ndk-stash`（同一文件系统，瞬间完成且可恢复），只保留 `21.4.7075529`，让“最新 NDK”回退落到正确版本。解释：不改旧 Android 构建模板（与“保持 AGP 3.6.0”的既定取舍一致），也不删本机数据；CI runner 是一次性环境。

- 问题：CI 首次成功产出 APK 后推到面板报 `INSTALL_FAILED_UPDATE_INCOMPATIBLE: Existing package com.rs485.control signatures do not match newer version`。根因是 AGP 用 `$ANDROID_USER_HOME/.android/debug.keystore` 签 debug 包，而该目录固定指向被 gitignore 的 `.android-toolchain`，干净环境（尤其 CI 的全新检出）里文件不存在，AGP 会**现场生成一个新的 debug 密钥**——于是每轮产物签名都不同，面板永远无法覆盖升级；且原密钥已丢失（本机全盘无 `debug.keystore`，`android/rs485.keystore` 只是占位符）。解决方案选择：生成真实的 `android/rs485.keystore`（别名 `androiddebugkey`、口令 `android`，即 Android debug 密钥的惯例值，也正是 AGP 自己假定的默认值），提交进版本库；`build_apk.sh` 在 `./gradlew` 前先校验可读并把它播种到 `$ANDROID_USER_HOME/.android/debug.keystore`，同时打印 SHA-256 指纹便于核对。解释：不需要改 `build.gradle` 的 `signingConfigs`，复用 AGP 既有的 debug 签名机制；任何机器、任何一轮构建的签名一致，面板可持续升级。代价是公开仓库可见该密钥（项目原先就打算把真密钥放这个位置，占位符的说明写反了——它其实被追踪且未被 gitignore），防的是误装与恶作剧，不防有针对性攻击。

- 问题：CI 产出的 APK 装到面板后启动即崩，报 `UnsatisfiedLinkError: dlopen failed: library "libc++_shared.so" not found`（`Qt JAVA : Can't find '.../lib/arm64/libc++_shared.so'`）。根因是 `copyStdCpp()`（把 NDK 的 `libc++_shared.so` 放进 `libs/<abi>/`）只在非 aux 模式调用，而 `cleanTopFolders` 只操作目录且跳过 `libs`，因此 aux 模式复用的暖构建目录里一直残留着这个库，从未暴露；干净检出（含 CI）产出的 APK 里完全没有该文件。解决方案选择：`build_apk.sh` 显式从 NDK 复制它到 `libs/arm64-v8a/`，并同时兼容两种 NDK 布局（NDK 21 及更早的 `sources/cxx-stl/llvm-libc++/libs/<abi>/`，NDK 22 起改为 `toolchains/llvm/prebuilt/*/sysroot/usr/lib/aarch64-linux-android/`）；构建后再用 `aapt list` 核对成品里确有 `lib/arm64-v8a/libc++_shared.so`，缺了就拒绝发布。解释：这个错误安装阶段完全正常（`Success`），要到装到面板上才崩，且与签名、包名无关，必须在构建侧拦住而不是靠现场试出来。

- 问题：卸载重装后恢复备份数据，应用仍启动即退，报 `Cannot initialize Android app file: "config/app.ini"`。根因是恢复数据时按旧 uid（`u0_a90`）`chown`，而 Android 在重装后分配了新 uid（`u0_a91`），应用读不到自己的私有目录。解决方案选择：恢复数据后用 `stat -c %U/%G /data/data/<pkg>` 取当前属主再 `chown -R`，不要沿用备份里的 uid。解释：uid 随卸载重装递增，任何按旧 uid 修复属主的恢复流程都会静默失败；取当前值才与本次安装匹配。

- 问题：自动温控下三个加热器不独立——现场反馈"第一路 A 达到温度之后，会自动切断其他路的加热器"，而设计要求 A/B/C 各自独立（A 的传感器管理 A 的加热器，B 的传感器管理 B 的加热器，C 的传感器管理 C 的加热器）。根因是 `applyAutomaticControl` 把三路外部温湿度温度**取平均后当成同一个被控量**传给三个加热器的控制算法（`const double temperature = temperatureSum / temperatureCount`），只有目标温度是按路分开的。模拟器实测对照：固定 th1=30（A 的目标）、th2=20、th3=20 后，旧逻辑因平均值 23.3 ℃ 而输出 `加热A/B/C=[3,1,3]`——A 的传感器已到达目标却仍满档加热（B/C 的冷探头把平均拉低所致），B/C 自己远未到目标却因 A 的热读数把平均抬高而降压；三路互相干扰，与"独立"的要求相反。解决方案选择：改为每个加热器跟随自己的传感器（加热器 A↔th1、B↔th2、C↔th3），该路传感器缺失或越界时回退到三路有效平均（保持旧行为），三路全无效才不控制；`heaterAPair/heaterBPair/heaterCPair` 与目标温度的既有语义不变。解释：耦合来自共用一个被控量，而不是输出对或写入路径（OT 写入本就是 0x0031 位掩码 RMW，`addConfiguredSpareOutputs` 也跳过加热器占用的 OT，这两处已核实无误）；改成按路取被控量后，模拟器同一场景输出 `加热A/B/C=[0,3,3]`，A 到位即停、B/C 继续按各自传感器满档加热，符合现场预期。防凝露模式的 `worstDewPoint` 仍取三路最大值，因为三路加热器共用同一室外空气条件是既定假设；PT100 跟随模式下目标仍共用 PT100 平均，未改动。
