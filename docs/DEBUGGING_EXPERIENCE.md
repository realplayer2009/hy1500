# RS485Control 项目调试经验与工程记录

> 本文档记录项目当前框架、真实调试经验、工程决策和后续维护边界。
> 面向后续接手工程师，避免重复踩坑。

## 一、当前程序框架（截至 2026-09-21）

### 1.1 整体架构

```
PC 端 / 开发机
  ├─ src/                      Qt5/C++ 上位机源码
  │   ├─ rs485device.*         Modbus RTU 协议层 + SerialPortWorker
  │   ├─ applogic.*            DeviceManager / PollScheduler / DataLogger /
  │   │                         HistoryQuery / StorageRotator / AppConfig
  │   ├─ controlalgorithm.*    阈值 / PID / 防凝露 / 露点计算 / 传感器自检
  │   ├─ appui.*               MainWindow / OverviewCard / ManualPanel /
  │   │                         FleetOverviewPanel / SettingsWidget / HistoryWidget
  │   └─ main.cpp             入口
  ├─ tests/
  │   ├─ controlalgorithm_test.*  QtTest 单元测试
  │   └─ simulator/
  │       ├─ pty_modbus_sim.py    无硬件模拟器（Linux PTY）
  │       └─ test_pty_modbus_sim.py 模拟器单元测试
  └─ docs/                     设计文档

安卓设备端（RK3568 / 2GB+16GB / Android 13）
  ├─ Termux 0.118.3            Linux 用户态运行时
  ├─ Termux:X11 (nightly)      X11 显示服务 + Activity 渲染
  ├─ RS485Control ARM64 二进制  业务程序
  ├─ start_rs485.sh            设备端幂等启动脚本
  └─ 日志：apk_launch.log / x11.log / app_run.log
```

### 1.2 核心数据流

1. **启动链路**：启动器 APK（HOME）→ Termux RunCommandService → `start_rs485.sh` → RS485Control
2. **轮询链路**：PollScheduler → DeviceManager → SerialPortWorker → Modbus RTU → 子板
3. **控制链路**：ManualPanel / AutoPanel → setDeviceAutoRunning → controlalgorithm → OT3/OT4 下发
4. **数据链路**：DataLogger → CSV（按日期）→ HistoryQuery → 内存缓存 → HistoryWidget

### 1.3 设备唯一标识

- 子板唯一键：`portIndex * 256 + slaveId`
- 每口最多 16 块
- 两路 RS485 分别扫描 Modbus ID 1~247

---

## 二、已建立的调试通道（2026-09-21 实测）

### 2.1 设备信息

| 项 | 值 |
|---|---|
| 设备 IP | 192.168.0.116 |
| 无线调试端口 | 35483（每次重启会变） |
| ADB 固定序列 | `192.168.0.116:36259`（`adb root` 后端口变化） |
| SSH 端口 | 8022（固定） |
| Termux 用户 | u0_a90 |
| 固件 | userdebug（开发版） |

### 2.2 ADB 通道

```bash
# 无线连接（每次重启后端口会变，需重新查询）
adb connect 192.168.0.116:<无线调试端口>
adb devices

# 获取 root（会重启 adbd，端口会变）
adb root
adb connect 192.168.0.116:<新端口>

# 指定设备执行（多设备时必须 -s）
adb -s 192.168.0.116:36259 shell <命令>
```

**经验**：
- `adb root` 后端口会变，必须重新 `adb connect`
- 多设备共存时，旧连接会显示 `offline`，新连接显示 `device`
- zsh 下 `adb shell ls -l /dev/ttyS*` 会报 `no matches`，必须加引号：`adb shell "ls -l /dev/ttyS*"`

### 2.3 SSH 通道

```bash
# 密钥登录（已配置）
ssh -p 8022 -i ~/.ssh/id_ed25519 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  u0_a90@192.168.0.116 "echo SSH_OK"
```

**经验**：
- 设备上已有 `rs485-pc` 公钥，但 Mac 上的 `id_ed25519` 不匹配
- 通过 adb 将 Mac 公钥写入设备后，SSH 密钥登录成功
- SSH 端口 8022 固定，比 adb 无线端口稳定，适合长期排查

### 2.4 串口节点对应关系（实测）

| 丝印编号 | Linux 节点 | 权限 |
|---|---|---|
| ttyS01 | /dev/ttyS4 | crw-rw-rw- |
| ttyS02 | /dev/ttyS2 | crw-rw-rw- |
| ttyS03 | /dev/ttyS7 | crw-rw-rw- |
| ttyS04 | /dev/ttyS5 | crw-rw-rw- |
| ttyS05 | /dev/ttyS3 | crw-rw-rw- |
| ttyS06 | /dev/ttyS8 | crw-rw-rw- |

**经验**：厂商丝印编号与 Linux 节点序号不一致，不要靠数字猜，以厂商书面定义为准。

---

## 三、分层调试法（实测验证）

### 3.1 L1 系统层

```bash
adb -s 192.168.0.116:36259 shell id
# 预期：uid=0(root)

adb -s 192.168.0.116:36259 shell "ls -l /dev/ttyS*"
# 预期：/dev/ttyS2~ttyS8 权限为 crw-rw-rw-
```

### 3.2 L2 运行时层

```bash
ssh -p 8022 -i ~/.ssh/id_ed25519 u0_a90@192.168.0.116 \
  "bash /data/data/com.termux/files/home/start_rs485.sh"
# 预期：最后一行 ALL_OK
```

**注意**：手工执行脚本时，第 0 步 wakelock 不会真正生效（详见坑 5）。

### 3.3 L3 显示服务层

```bash
ssh -p 8022 -i ~/.ssh/id_ed25519 u0_a90@192.168.0.116 \
  "ps -A | grep termux-x11"
# 预期：termux-x11 com.termux.x11 :0
```

**注意**：该设备 `ps` 不支持 `-o PID,ARGS`，用 `ps -A` 即可。

### 3.4 L4 应用层

```bash
ssh -p 8022 -i ~/.ssh/id_ed25519 u0_a90@192.168.0.116 \
  "ps -A | grep -i RS485Control"
# 预期：./RS485Control
```

### 3.5 L5 显示端层

```bash
adb -s 192.168.0.116:36259 shell screencap -p /data/local/tmp/s.png
adb -s 192.168.0.116:36259 pull /data/local/tmp/s.png ./screen.png
```

**经验**：截图是判断屏幕是否有画面的唯一可靠标准。进程都在不等于屏幕有画面。

---

## 四、八个真实踩坑记录

### 坑 1：`run-as` 的 `~` 不是 Termux 家目录

- **现象**：文件推到 `~/xxx`，命令不报错，但脚本行为不对
- **根因**：`run-as com.termux` 的 `~` 是 `/data/data/com.termux`，不是 `/data/data/com.termux/files/home`
- **修复**：所有路径一律用绝对路径

### 坑 2：`force-stop` 让 Termux 进入 stopped 状态

- **现象**：`am force-stop com.termux` 后启动器无法下发指令
- **修复**：打开一次 Termux 即可解除；日常排查不要 force-stop

### 坑 3：RUN_COMMAND 的 extra 名不带 `.app.` 段

- **现象**：Termux 报 `Mandatory extra missing`
- **修复**：extra 名是 `com.termux.RUN_COMMAND_PATH` 等，没有 `.app.` 中间段

### 坑 4：普通 `startService` 在冷启动时被静默拦截

- **现象**：重启后停在蓝色页面报"无法向 Termux 下发启动指令"
- **根因**：Android 8+ 上，目标进程不存在时跨应用 `startService` 被判定为后台启动
- **修复**：改用 `startForegroundService()`，并在 Manifest 声明 `android.permission.FOREGROUND_SERVICE`

### 坑 5：`termux-wake-lock` 会"假成功"

- **现象**：脚本返回 0，但熄屏后 sshd 失联、程序消失
- **根因**：`adb run-as` 手工执行时，am 调用被静默拦截，返回码仍为 0
- **验证标准**：`dumpsys power | grep -A6 'Wake Locks'` 必须有 `PARTIAL_WAKE_LOCK 'termux:service-wakelock'`

### 坑 6：Termux:X11 默认触控模式是"触控板"

- **现象**：界面看得见，但手指点击没反应
- **修复**：Preferences → Pointer → Touchscreen input mode → Direct touch

### 坑 7：`pkill -f` 会匹配到自己

- **现象**：脚本执行到清理进程那一步，脚本自己被杀掉
- **修复**：模式里用方括号打断字面量，如 `[R]S485Control`

### 坑 8：系统熄屏后回收整个进程组

- **现象**：放置一段时间后控制系统消失，屏幕黑掉
- **修复**：
  1. 脚本第 0 步 `termux-wake-lock`
  2. 屏幕常亮：`settings put global stay_on_while_plugged_in 7`

---

## 五、Mac 开发机工具链（2026-09-21 实测）

| 工具 | 版本/路径 | 状态 |
|---|---|---|
| adb | 1.0.41 (37.0.1-15733141) | ✅ `/opt/homebrew/bin/adb` |
| Java | openjdk 26.0.2.1 (Temurin) | ✅ 已安装 |
| sdkmanager | 12.0 | ✅ `~/Library/Android/sdk/cmdline-tools/latest/bin/sdkmanager` |
| Android platform-tools | 已安装 | ✅ |
| Android platforms;android-33 | 已安装 | ✅ |
| Android build-tools;34.0.0 | 已安装 | ✅ |
| pwsh | PowerShell 7.7.0-preview.4 | ✅ `/usr/local/microsoft/powershell/7-preview/pwsh` |

**环境变量（已写入 ~/.zprofile）**：
```bash
export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export PATH="$PATH:$ANDROID_SDK_ROOT/platform-tools"
export PATH="$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin"
export PATH="/usr/local/microsoft/powershell/7-preview:$PATH"
```

---

## 六、回归清单（每次改动后必须全过）

| 序号 | 验收项 | 操作 | 通过标准 |
|---|---|---|---|
| 1 | 点图标启动 | 冷态点图标 | 约 10 秒进入控制界面 |
| 2 | 幂等性 | 连续点图标两次 | 程序 PID 不变 |
| 3 | HOME 自愈 | 按 Home 键 | 自动回到控制界面 |
| 4 | 重启自愈 | `adb reboot` 后不做任何操作 | 开机自动进入控制界面 |
| 5 | 进程保活 | 熄屏放置 10 分钟后从 SSH 查进程 | sshd 与 RS485Control 均在 |
| 6 | 屏幕常亮 | 插电静置 | 屏幕不熄灭 |
| 7 | 中文与触控 | 目视 + 手指点击各控件 | 中文正常、点击响应 |

---

## 七、后续待办

- [ ] 实现 `android/` 启动器 APK（MainActivity、build_apk.sh、provision.ps1）
- [ ] 将调试手册 `docs/DEBUGGING_GUIDE.md` 纳入项目文档索引
- [ ] 建立真机自动化回归流程（adb + SSH 脚本化）
- [ ] 完善 `rs485_modbus_debug.py` 的 Modbus 调试命令集

---

## 八、经验总结

1. **分层调试法有效**：五层模型让排障从"猜"变成"查"，每层有明确验证命令和预期输出
2. **SSH 比 adb 更稳定**：adb 无线端口每次重启都会变，SSH 8022 固定，长期排查优先 SSH
3. **截图是唯一真相**：进程都在不等于屏幕有画面，L5 必须以截图为判断标准
4. **设备端 `ps` 语法差异**：该设备 `ps` 不支持 `-o PID,ARGS`，用 `ps -A | grep` 即可
5. **zsh glob 问题**：`adb shell ls -l /dev/ttyS*` 在 zsh 下会报 `no matches`，必须加引号
6. **密钥管理**：通过 adb 写入公钥是解决 SSH 密钥不匹配的最快路径
