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
