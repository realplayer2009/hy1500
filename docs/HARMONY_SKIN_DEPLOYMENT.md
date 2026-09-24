# RS485Control 鸿蒙换壳部署清单

> 适用场景：在同类 RK3562_T / Android 13 设备上复现“鸿蒙外观”效果。
> 边界：不刷 boot、不碰 DTB，系统属性只改 overlay 可达部分。

---

## 1. 源码改动清单

### 1.1 `src/applogic.h`
- 行 48：`displayTheme` 默认值从 `"standard"` 改为 `"harmony"`

### 1.2 `src/applogic.cpp`
- 行 38-42：`AppConfig::load()` 的 theme whitelist 增加 `"harmony"`
- 行 334-341：`DeviceManager::updateDeviceData()` 增加外扩输入调试日志（`EXP_IN_UI`）
- 行 818-826：`PollScheduler::start()` 增加 `startExpInputPolling`
- 行 827-837：`PollScheduler::stop()` 增加 `stopExpInputPolling`

### 1.3 `src/appui.h`
- 行 323-329：新增 `AboutWidget` 类声明
- 行 391：`MainWindow` 增加 `AboutWidget *m_aboutWidget` 成员

### 1.4 `src/appui.cpp`
- 行 11：增加 `#include <QDebug>`
- 行 249-841：`applicationStyleSheet()` 新增 `harmony` QSS 主题
  - 主色 `#007DFF`，圆角 `10~14px`，卡片化浅灰背景
- 行 834-840：`themeName == "harmony"` 时返回 `base + harmony`
- 行 1569-1578：`HistoryChart::paintEvent` 颜色适配 harmony 分支
- 行 2531-2568：新增 `AboutWidget` 实现
  - 标题：`裕泰通加热器`
  - 芯片：`RK3568`
  - 操作系统：`鸿蒙操作系统`
- 行 2886：`SettingsWidget` 增加 `"鸿蒙"` 主题项，value=`"harmony"`
- 行 3676：`MainWindow` 标题改为 `裕泰通加热器`
- 行 3707-3712：侧栏品牌标题改为 `裕泰通加热器`
- 行 3707-3712：导航文字从 4 个改为 5 个：
  - `域控子板总览`
  - `子板手动控制`
  - `加热参数设置`
  - `数据浏览`
  - `关于本机`
- 行 3764-3769：`m_aboutWidget` 创建并加入 `m_pages`
- 行 3846-3851：`switchPage` 标题列表同步改为 5 个

### 1.5 `src/main.cpp`
- 行 41：`w.showMaximized()` 改为 `w.showFullScreen()`

### 1.6 `android/src/com/rs485/launcher/MainActivity.java`
- 行 11：`onCreate` 增加 `setFullscreen(true)`
- 行 15-20：重写 `onWindowFocusChanged` 保持全屏
- 行 22-35：新增 `setFullscreen` 方法
  - 使用 `SYSTEM_UI_FLAG_IMMERSIVE_STICKY`
  - 使用 `SYSTEM_UI_FLAG_FULLSCREEN`
  - 使用 `SYSTEM_UI_FLAG_HIDE_NAVIGATION`
  - 使用 `SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN`
  - 使用 `SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION`
  - 使用 `SYSTEM_UI_FLAG_LAYOUT_STABLE`

### 1.7 `android/deploy_device.sh`
- ADB 目标地址改为当前设备 IP:端口（每台机器可能不同）

---

## 2. 系统层改动清单

### 2.1 overlay 修改（已生效）

文件：`/mnt/scratch/overlay/system/upper/build.prop`

已修改属性：
```ini
ro.build.display.id=HarmonyOS-4.0 13 TQ3C.230805.001.B2 eng.server.20260421.150515 release-keys
ro.build.version.release=4.0
ro.system.build.fingerprint=Huawei/rk3562_t/rk3562_t:13/TQ3C.230805.001.B2/server2104211504:userdebug/release-keys
ro.product.system.brand=Huawei
ro.product.system.manufacturer=Huawei
ro.product.system.model=HarmonyOS
```

验证命令：
```bash
adb -s <device>:<port> shell "su 0 getprop ro.build.display.id"
adb -s <device>:<port> shell "su 0 getprop ro.build.version.release"
adb -s <device>:<port> shell "su 0 getprop ro.system.build.fingerprint"
adb -s <device>:<port> shell "su 0 getprop ro.product.system.brand"
```

### 2.2 无法通过 overlay 修改的属性（需要改 boot/DTB，本次不碰）

以下属性仍为原始值：
```bash
ro.product.brand=rockchip
ro.product.manufacturer=rockchip
ro.product.model=rk3562_t
ro.hardware=rk30board
ro.boot.hardware=rk30board
ro.product.board=rk30sdk
ro.board.platform=rk3562
```

这些属性不是从 build.prop 读取，而是来自 init 或 device tree，overlay 方案碰不到。

---

## 3. 部署步骤（新机器）

### 3.1 前置条件
- 设备已 root，`su 0` 可用
- 已开启 WiFi ADB，知道 IP:端口
- 设备为 Android 13（rk3562_t），动态分区 + overlayfs

### 3.2 源码编译与推送
```bash
# 1. 克隆仓库
git clone <repo_url> RS485Control
cd RS485Control

# 2. 修改 android/deploy_device.sh 中的 ADB 目标
#    将 ADB="adb -s <旧IP>:<旧端口>" 改为当前设备
#    同时修改 push 命令中的 adb -s 地址

# 3. 编译 Qt 应用（在 Ubuntu x86 上）
qmake RS485Control.pro
make -j4

# 4. 推送到设备
./android/deploy_device.sh
```

### 3.3 设备端系统属性修改
```bash
# 1. 确认 overlay 可写
adb -s <device>:<port> shell "su 0 mount | grep overlay on /system"

# 2. 备份原始 build.prop
adb -s <device>:<port> shell "su 0 cp /system/build.prop /mnt/scratch/overlay/system/upper/build.prop.bak"

# 3. 修改 overlay 中的 build.prop
adb -s <device>:<port> shell "su 0 sed -i 's/ro.product.brand=rockchip/ro.product.brand=Huawei/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.product.manufacturer=rockchip/ro.product.manufacturer=Huawei/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.product.model=rk3562_t/ro.product.model=HarmonyOS/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.build.display.id=rk3562_t-userdebug/ro.build.display.id=HarmonyOS-4.0/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.build.version.release=13/ro.build.version.release=4.0/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.system.build.fingerprint=rockchip/ro.system.build.fingerprint=Huawei/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.product.system.brand=rockchip/ro.product.system.brand=Huawei/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.product.system.manufacturer=rockchip/ro.product.system.manufacturer=Huawei/' /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 sed -i 's/ro.product.system.model=rk3562_t/ro.product.system.model=HarmonyOS/' /mnt/scratch/overlay/system/upper/build.prop"

# 4. 重启设备
adb -s <device>:<port> shell "su 0 reboot"

# 5. 等待设备重启并重新连接 WiFi ADB
# 6. 验证属性
adb -s <device>:<port> shell "su 0 getprop ro.build.display.id"
adb -s <device>:<port> shell "su 0 getprop ro.build.version.release"
```

### 3.4 应用配置
```bash
# 编辑 config/app.ini，设置主题
displayTheme=harmony
```

或在应用内“参数设置”页面选择“鸿蒙”主题。

---

## 4. 验证 checklist

### 4.1 应用侧
- [ ] 应用启动后全屏显示（无标题栏、无状态栏）
- [ ] 侧栏品牌标题显示“裕泰通加热器”
- [ ] 导航文字为：域控子板总览 / 子板手动控制 / 加热参数设置 / 数据浏览 / 关于本机
- [ ] 主题选择“鸿蒙”后界面变为圆角卡片 + 蓝色主色调
- [ ] “关于本机”页面显示“芯片：RK3568 / 操作系统：鸿蒙操作系统”
- [ ] 历史曲线背景色随主题变化

### 4.2 系统侧
- [ ] `ro.build.display.id` 包含 `HarmonyOS-4.0`
- [ ] `ro.build.version.release` = `4.0`
- [ ] `ro.system.build.fingerprint` 以 `Huawei` 开头
- [ ] `ro.product.system.brand` = `Huawei`
- [ ] `ro.product.system.manufacturer` = `Huawei`
- [ ] `ro.product.system.model` = `HarmonyOS`

### 4.3 已知不变项（接受即可）
- [ ] `ro.product.brand` = `rockchip`
- [ ] `ro.product.manufacturer` = `rockchip`
- [ ] `ro.product.model` = `rk3562_t`
- [ ] `ro.hardware` = `rk30board`
- [ ] `ro.boot.hardware` = `rk30board`
- [ ] `ro.product.board` = `rk30sdk`
- [ ] `ro.board.platform` = `rk3562`

---

## 5. 故障排查

### 5.1 WiFi ADB 断开
- 设备端重新执行：
```bash
setprop service.adb.tcp.port <端口号>
stop adbd
start adbd
```
- Mac 端重新 `adb connect <IP>:<端口>`

### 5.2 overlay 未生效
- 确认 `/mnt/scratch/overlay/system/upper/` 存在且非空
- 确认 `mount | grep overlay on /system` 输出中有 `rw`
- 若只读，执行 `su 0 toybox mount -o rw,remount /system`

### 5.3 应用编译失败
- 确认 Qt 5.15 工具链
- 确认 `libqt5serialport5-dev` 已安装
- 清理后重编译：
```bash
make clean
qmake RS485Control.pro
make -j4
```

---

## 6. 回滚方法

### 6.1 恢复系统属性
```bash
adb -s <device>:<port> shell "su 0 cp /mnt/scratch/overlay/system/upper/build.prop.bak /mnt/scratch/overlay/system/upper/build.prop"
adb -s <device>:<port> shell "su 0 reboot"
```

### 6.2 恢复应用主题
```bash
# 编辑 config/app.ini
displayTheme=standard
# 或应用内选择“标准”
```

---

*清单生成时间：2026-09-23*
