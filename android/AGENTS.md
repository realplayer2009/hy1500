# Android 组件工程取舍

> 后续修改本组件的 agents 请继续维护本文档；记录格式为“问题 + 解决方案选择 + 解释”。

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
