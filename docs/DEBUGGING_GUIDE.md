# 环境控制系统（安卓版）调试手册

> 从零上手到独立排障：一套可复用的分层调试方法，以及八个真实踩过的坑。

## TL;DR

这套系统把一份 **Qt5/C++ 的 RS485 环境控制程序**跑在了**安卓触摸屏**上：Termux 提供 Linux 用户态运行时，Termux:X11 负责显示，启动器 APK 充当设备桌面。调试它的正确姿势不是"哪里坏了修哪里"，而是**自下而上分层验证**——系统层 → 运行时层 → 显示服务层 → 应用层 → 显示端层，每层单独确认，绝不跳层。

## 文档信息

| 项 | 内容 |
|---|---|
| 目标读者 | 接手本项目的工程师（无需 Termux / 安卓底层经验） |
| 前置知识 | 会用命令行；知道 adb 是什么；能读懂 shell 脚本 |
| 学完能做什么 | 独立定位任意环节的故障；把一台新设备装成可调试状态；现场 5 分钟内恢复 |
| 硬件环境 | 冠奕 PA0715-N（RK3562 / 2GB+16GB / Android 13） |
| 软件版本 | Termux 0.118.3、Termux:X11（nightly） |
| 预计阅读时间 | 25 分钟（含动手验证） |
| 关键前提 | 设备固件必须是 **userdebug（开发版）**；user（正式版）固件上本方案不成立 |

## 阅读约定

- 除注明"设备端"外，所有命令都在 **PC 端**执行。
- `<尖括号>` 是占位符，执行前替换成实际值，例如 `<设备IP>`、`<端口>`、`<私钥文件>`。
- `$ADB` 代表 adb 命令。把 adb 加进系统 PATH 后可直接写 `adb`；本文统一写 `$ADB`，你按自己的环境替换一次即可。
- `#` 开头是注释；行尾 `←` 后面是对预期输出的说明。

## 一、先看懂系统：五层结构与职责边界

排障效率低，九成是因为**不清楚故障属于哪一层**。先建立这张地图——它会告诉你"现在该查谁"。

| 层 | 组件 | 职责 | 出问题时的表象 | 归属 |
|---|---|---|---|---|
| L1 系统层 | Android 13 / adb / 内核串口驱动 | 提供硬件与调试通道 | 连不上设备、串口节点不存在 | 硬件厂商 |
| L2 运行时层 | Termux + 启动脚本 | 提供 Linux 环境、拉起进程 | 脚本报错、进程不在 | 我方 |
| L3 显示服务层 | termux-x11（X server） | 提供 X11 显示服务 | 显示端提示 Not connected | 我方（第三方组件） |
| L4 应用层 | RS485Control（ARM64 二进制） | 业务逻辑、串口通信 | 界面能出但无数据 / 直接退出 | 我方 |
| L5 显示端层 | Termux:X11 Activity | 把 X 画面渲染到屏幕 | 黑屏、触控无效 | 我方（第三方组件） |

### （一）上电启动链路

理解这条链路，你就理解了整个系统的"生命线"：

```
设备上电
   │
   ▼
Android 启动完成 ──自动拉起 HOME──▶ 启动器 APK（com.rs485.launcher）
                                        │
                                        │ ① startForegroundService(RUN_COMMAND)
                                        ▼
                              Termux 的 RunCommandService
                                        │
                                        │ ② 执行 ~/start_rs485.sh（幂等）
                                        ▼
                        ┌────────────────────────────────────┐
                        │ [0/3] termux-wake-lock  持有唤醒锁  │
                        │ [1/3] sshd              远程维护通道 │
                        │ [2/3] termux-x11 :0     X 显示服务   │
                        │ [3/3] ./RS485Control    业务程序     │
                        └────────────────────────────────────┘
                                        │
                                        │ ③ 打开 Termux:X11 显示 Activity
                                        ▼
                              全屏渲染环境控制系统界面
```

### （二）三个关键判定点

链路里有三处必须依次成立，排障时按顺序问自己：

1. ① 步骤有没有发出去？（启动器有没有跑起来）
2. ② 步骤有没有执行？（脚本日志里有没有 `ALL_OK`）
3. ③ 步骤有没有成功？（屏幕上有没有出现界面）

**绝大多数"看起来像程序崩溃"的问题，其实卡在前两步。**

## 二、开工前：工具、通道与设备信息

拿到设备第一件事不是查故障，而是**建立调试通道**——没有通道，任何诊断都无从下手。

### （一）你只需要三样东西

| 工具 | 用途 | 取得方式 |
|---|---|---|
| adb（platform-tools） | 底层操作、root、日志、截图 | 官方 platform-tools 压缩包，解压即用；**不需要 Android Studio** |
| SSH 客户端 | 不依赖 adb 的稳定通道 | Windows 10 及以上自带；macOS / Linux 自带 |
| 终端（bash / PowerShell） | 执行上面两个工具 | 系统自带 |

### （二）先问出三个值

| 值 | 从哪儿取 | 注意 |
|---|---|---|
| 设备 IP | 设备：设置 → 关于 → 状态 | 现场网段可能不同 |
| 无线调试端口 | 设备：设置 → 系统 → 开发者选项 → 无线调试 | **设备每次重启都会变** |
| Termux 用户名 | 设备端 Termux 里执行 `whoami` | 形如 `u0_a90`，随安装变化 |

### （三）通道一：无线 adb（首选，权限最全）

设备端操作：`设置 → 系统 → 开发者选项 → 无线调试 → 打开`，记下显示的 IP 与端口。

PC 端连接：

```bash
# $ADB 替换成你自己的 adb 路径；已加入 PATH 时直接写 adb
$ADB connect <设备IP>:<端口>
$ADB devices          ← 预期输出：<设备IP>:<端口>  device
```

⚠️ **注意**：这是 `userdebug` 固件，`adb root` 可用。但执行 `adb root` 会重启 adbd，**端口号会变**，必须重新查端口并重连。

### （四）通道二：SSH（端口固定，长期可用）

设备的 sshd 由启动脚本拉起，固定监听 8022。IP、用户名按 §2.2 查：

```bash
ssh -p 8022 -i <私钥文件> \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  <Termux用户名>@<设备IP> "echo SSH_OK"
```

预期输出：`SSH_OK`

**为什么必须备这条通道**：adb 端口每次重启都变，而 SSH 端口固定；且 SSH 直接进 Termux 用户态，排查脚本问题比 adb 更直接。

### （五）端口变了怎么办

按顺序试，前两个通常够用：

**办法 1（最快）**：在设备上打开无线调试页面，直接看显示的端口号。

**办法 2（无人值守时用）**：跑端口扫描。逻辑很简单——并发 connect 一遍候选端口段，能连上的就是。把下面这段存成 `portscan.py`，改好 IP 后运行（需要 Python 3）：

```python
import socket, concurrent.futures

HOST = "<设备IP>"          # 改成实际设备 IP

def probe(p):
    s = socket.socket()
    s.settimeout(0.4)
    try:
        s.connect((HOST, p))
        return p
    except Exception:
        return None
    finally:
        s.close()

with concurrent.futures.ThreadPoolExecutor(max_workers=900) as ex:
    open_ports = [p for p in ex.map(probe, range(30000, 61000)) if p]

print("OPEN:", sorted(open_ports))   # 预期输出：OPEN: [38xxx]
```

**办法 3**：两个都不通时，回到 SSH 通道（8022 固定端口）临时作业。

## 三、分层调试法（核心方法论）

这是本手册最核心的一节。掌握它，你就不需要记住任何具体命令——因为每一层的验证思路是一样的：**先确认这一层的组件活着，再确认它和上一层的连接正常**。

> **铁律：自下而上，逐层单点验证，不跳层、不假设。**

看到故障时，最常见的错误是"从现象倒推"，比如屏幕黑就怀疑程序崩了。正确的做法是**从最底层往上，每一层拿到确凿证据再往上走**。下面五层，每层给你验证命令、预期输出和失败特征。

### （一）L1 系统层：设备在不在、能不能调试

```bash
$ADB connect <设备IP>:<端口>
$ADB shell "id"
```

预期输出（userdebug 且已 root）：

```
uid=0(root) gid=0(root) ...
```

若输出是 `uid=2000(shell)`，说明未 root，执行 `$ADB root` 后重连。

检查串口节点是否就绪：

```bash
$ADB shell "ls -l /dev/ttyS*"
```

预期输出：`/dev/ttyS2` 到 `/dev/ttyS8` 权限为 `crw-rw-rw-`（0666，普通应用可直接访问，无需 root）。

⚠️ **陷阱**：厂商丝印编号与 Linux 节点序号**不一致**（丝印 ttyS01 实际是 `/dev/ttyS4`，丝印 ttyS02 是 `/dev/ttyS2`）。**不要靠数字猜**，以厂商书面定义为准。

### （二）L2 运行时层：Termux 与启动脚本

先确认包与家目录正常：

```bash
$ADB shell "run-as com.termux sh -c 'ls /data/data/com.termux/files/home/'"
```

预期能看到 `start_rs485.sh`、`rs485/`、`apk_launch.log`。

手工跑一次启动脚本看输出：

```bash
$ADB shell "run-as com.termux sh -c '/data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/start_rs485.sh'"
```

预期输出（关键就是最后一行）：

```
[2/3] X server ...... already running
[3/3] app ........... already running (pid 1877)

ALL_OK
```

⚠️ **重要限制**：用这种方式手工执行脚本时，**第 0 步 wakelock 不会真正生效**（详见坑 5）。手工跑只用于验证 L2/L3/L4，wakelock 的状态必须单独查。

### （三）L3 显示服务层：X server 活着吗

```bash
$ADB shell "ps -A -o PID,ARGS | grep 'termux-x11 com.termux.x11'"
```

预期输出：

```
1794 termux-x11 com.termux.x11 :0
```

进程命令行里必须有 `:0`，这表示 X server 已经绑定到 display 0。

**失败特征**：没有输出 → X server 没起来。看日志：

```bash
$ADB shell "run-as com.termux sh -c 'tail -20 /data/data/com.termux/files/home/x11.log'"
```

常见原因是上一次异常退出残留了 socket 锁文件，脚本里的 `rm -f` 会清理，但如果是权限问题就清不掉。

### （四）L4 应用层：业务程序活着吗

```bash
$ADB shell "ps -A -o PID,ARGS | grep '[R]S485Control'"
```

预期输出：`1877 ./RS485Control`

**失败特征**：没有输出。看应用日志定位：

```bash
$ADB shell "run-as com.termux sh -c 'tail -30 /data/data/com.termux/files/home/app_run.log'"
```

典型报错与对策：

- `cannot open /dev/ttyS2: Permission denied` → 回 L1 检查串口节点权限
- `error while loading shared libraries` → 二进制依赖的 Qt 库缺失，重装 `qt5-qtbase`
- 无任何报错直接退出 → 检查是否缺少图形环境变量 `DISPLAY=:0`

### （五）L5 显示端层：画面有没有真的渲染出来

这层最容易被误判，因为"进程都在"不等于"屏幕上有画面"。三个检查点：

```bash
# 1. 显示 Activity 是否在前台（oom_score_adj 越小越靠前，0 = 前台）
$ADB shell "ps -A -o PID,ARGS | grep -i 'termux-x11'"

# 2. 直接截图看（最可靠）
$ADB shell screencap -p /data/local/tmp/s.png
$ADB pull /data/local/tmp/s.png ./screen.png

# 3. 手动把显示端拉到前台
$ADB shell "monkey -p com.termux.x11 -c android.intent.category.LAUNCHER 1"
```

⚠️ **架构认知**：Termux:X11 采用 Loader 架构，**显示 Activity 与 X server 跑在同一个进程里**（进程名 `termux-x11 com.termux.x11 :0`）。所以"找不到独立的 `com.termux.x11` 进程"是正常的，不要据此判断显示端挂了——**以截图为唯一真相**。

触控无效的处理见坑 6。

## 四、八个真实的坑（现象 → 根因 → 修复 → 验证）

> 这些都是实际调试中踩过的，按"最容易再次踩到"排序。

### （一）坑 1：`run-as` 的 `~` 不是 Termux 家目录

**现象**：把文件推到 `~/xxx`，命令不报错，但脚本行为不对（比如 `allow-external-apps` 明明写了却不生效）。

**根因**：`run-as com.termux` 的 `~` 展开为**应用根目录** `/data/data/com.termux`，而 Termux 真正的家目录是 `/data/data/com.termux/files/home`。

**修复**：所有涉及路径的命令**一律用绝对路径**，禁止用 `~`。

**验证**：

```bash
$ADB shell "ls -la /data/data/com.termux/files/home/.termux/termux.properties"
```

### （二）坑 2：`force-stop` 让 Termux 进入 stopped 状态

**现象**：执行过 `am force-stop com.termux` 之后，启动器再也无法下发指令。

**根因**：被强行停止的应用进入 stopped 状态，系统禁止其他应用唤醒其服务（logcat 报 `Background start not allowed`）。

**修复**：打开一次 Termux 即可解除（点图标，或 `monkey -p com.termux -c android.intent.category.LAUNCHER 1`）。**日常排查不要 force-stop Termux。**

### （三）坑 3：RUN_COMMAND 的 extra 名不带 `.app.` 段

**现象**：指令发出去了，Termux 只在 logcat 里报 `Mandatory extra missing`。

**根因**：extra 名是 `com.termux.RUN_COMMAND_PATH`、`com.termux.RUN_COMMAND_ARGUMENTS`、`com.termux.RUN_COMMAND_WORKDIR`、`com.termux.RUN_COMMAND_BACKGROUND`，**没有** `.app.` 中间段。

**验证**：

```bash
$ADB logcat -d | grep -i "RunCommandService" | tail -20
```

### （四）坑 4：普通 `startService` 在冷启动时被静默拦截（最重要）

**现象**：设备**重启后**自动进入启动器，但停在蓝色页面报"无法向 Termux 下发启动指令"。手动打开一次 Termux 后再点图标，一切正常。

**根因**：Android 8+ 上，**目标应用进程不存在时**，跨应用 `startService` 会被判定为后台启动而静默拦截：

```
Background start not allowed: service Intent { act=com.termux.RUN_COMMAND ... }
```

重启后 Termux 进程尚未创建，因此**必现**。这与 `allow-external-apps` 设置无关——启动器早期版本的报错文案有误导性。

**修复**：改用 `startForegroundService()`（Termux 的 RunCommandService 内部本就调用 `startForeground()`，这是官方预期用法），并在 Manifest 声明 `android.permission.FOREGROUND_SERVICE`。

**验证**：真机 `adb reboot`，等设备起来后**不要做任何干预**，直接看屏幕是否显示控制界面。

### （五）坑 5：`termux-wake-lock` 会"假成功"

**现象**：脚本里明明执行了 `termux-wake-lock` 且返回码为 0，但设备熄屏几分钟后 sshd 失联、控制程序消失。

**根因**：`termux-wake-lock` 依赖向 TermuxService 发送 am 调用，而 **am 调用在后台受限**。当脚本是通过 `adb run-as` 手工执行时（不在 TermuxService 会话内），am 调用被静默拦截——**返回码依然是 0**。

**修复**：确保脚本经由**正常链路**执行（启动器点图标 / 开机自动拉起），即 RUN_COMMAND 路径。

**验证（唯一可信标准）**：

```bash
$ADB shell "dumpsys power | grep -A6 'Wake Locks'"
```

必须看到这一行：

```
PARTIAL_WAKE_LOCK  'termux:service-wakelock' ACQ=-12s970ms (uid=10090 ...)
```

没有这一行 = 唤醒锁没挂上 = 系统随时会回收整个进程组。

### （六）坑 6：Termux:X11 默认触控模式是"触控板"

**现象**：界面看得见，但手指点击没反应。

**根因**：Termux:X11 默认 `Trackpad` 模式，把触摸当成"移动虚拟光标"，单击落到的是光标当前位置而非手指位置。

**修复**：进入 Termux:X11 偏好设置：`齿轮图标 → Preferences → Pointer → Touchscreen input mode → Direct touch`。

**批量预装时的免手工做法**（需 root）：先确认当前偏好文件里触控模式的实际键名与取值，再批量写入。

```bash
# 先看现状（确认键名与当前值）
$ADB shell "grep -i touchmode /data/data/com.termux.x11/shared_prefs/com.termux.x11_preferences.xml"
```

确认键名为 `touchMode`、目标值为 Direct touch 对应的取值后（该版本中 Direct touch = 3），再批量替换。**不同版本的 Termux:X11 键名或取值可能有差异，务必先看上一步的输出再动手。**

### （七）坑 7：`pkill -f` 会匹配到自己

**现象**：脚本执行到清理进程那一步，脚本自己反而被杀掉（退出码 143）。

**根因**：`pkill -f '[R]S485Control'` 的模式本身会出现在执行它的 shell 命令行里，导致自匹配。

**修复**：模式里用方括号打断字面量——写 `[R]S485Control` 而不是 `RS485Control`；且**整条脚本里所有匹配模式都要保持一致带括号**。

### （八）坑 8：系统熄屏后回收整个进程组

**现象**：一切正常，放置一段时间后控制系统消失，屏幕黑掉。

**根因**：Termux 退到后台成为缓存应用，Android 低内存回收时会**杀掉整个进程组**，sshd、X server、RS485Control 一起消失。

**修复**：两个措施同时上——

1. 脚本第 0 步 `termux-wake-lock`（见坑 5），让 TermuxService 成为前台服务；
2. 屏幕常亮：

```bash
$ADB shell settings put global stay_on_while_plugged_in 7
$ADB shell settings get global stay_on_while_plugged_in   # 预期输出：7
```

## 五、回归清单（每次改动后必须全过）

改完任何一层，都按这张表回归一遍——**用截图和命令输出留证，不靠"应该没问题"**。

| 序号 | 验收项 | 操作 | 通过标准 |
|---|---|---|---|
| 1 | 点图标启动 | 冷态（无组件运行）点图标 | 约 10 秒进入控制界面 |
| 2 | 幂等性 | 连续点图标两次 | 程序 PID 不变 |
| 3 | HOME 自愈 | 按 Home 键 | 自动回到控制界面 |
| 4 | 重启自愈 | `adb reboot` 后不做任何操作 | 开机自动进入控制界面 |
| 5 | 进程保活 | 熄屏放置 10 分钟后从 SSH 查进程 | sshd 与 RS485Control 均在 |
| 6 | 屏幕常亮 | 插电静置 | 屏幕不熄灭 |
| 7 | 中文与触控 | 目视 + 手指点击各控件 | 中文正常、点击响应 |

## 六、现场故障恢复手册

> 现场人员只能打电话描述现象时的应对流程。**按现象直接查对应场景**，不要从头排查。

### （一）场景 A：屏幕全黑，不确定设备是否在运行

```bash
# 第一步：确认设备在线
ping <设备IP>

# 第二步：用 SSH 查进程（最能说明问题）
ssh -p 8022 -i <私钥文件> <Termux用户名>@<设备IP> \
  "ps -ef | grep -E 'RS485Control|termux.x11' | grep -v grep"
```

- **进程都在** → 只是屏幕熄了，按一下电源键唤醒；若长期熄屏，检查 `stay_on_while_plugged_in` 是否为 7
- **X server 在、app 不在** → 执行启动脚本（走正常链路），看 `app_run.log`
- **都没有** → 走场景 C

### （二）场景 B：停在蓝色页面（启动器自检页）

看屏幕上的文案分流：

| 屏幕文案 | 含义 | 处置 |
|---|---|---|
| 无法向 Termux 下发启动指令 | 冷启动拦截或 Termux 缺失 | 确认启动器 ≥ v1.1；在设备上打开一次 Termux |
| 未检测到 Termux 运行环境 | Termux 被卸载 | 重新预装 |
| 缺少 Termux 启动授权 | 权限未授予 | 重装启动器（targetSdk=22 会自动授予） |

### （三）场景 C：完全无响应，需要重刷

按顺序尝试，多数情况到第二步就能恢复：

1. 断电重启设备（等 90 秒让它自然启动完）
2. 若仍无画面：用 adb 手工拉起一次全链路，确认是启动器问题还是系统问题
3. 若 adb 也进不去：设备可能固件损坏，联系硬件厂商

## 七、命令速查卡

把这一节单独打印出来贴在工位上，日常排查 90% 的场景够用。

```bash
# —— 连接 ——
$ADB connect <设备IP>:<端口>
$ADB devices
$ADB root

# —— 进程状态 ——
$ADB shell "ps -A -o PID,ARGS | grep -E 'RS485Control|termux.x11' | grep -v grep"

# —— 日志 ——
$ADB shell "run-as com.termux sh -c 'tail -20 /data/data/com.termux/files/home/apk_launch.log'"
$ADB shell "run-as com.termux sh -c 'tail -20 /data/data/com.termux/files/home/x11.log'"
$ADB shell "run-as com.termux sh -c 'tail -20 /data/data/com.termux/files/home/app_run.log'"

# —— 唤醒锁 ——
$ADB shell "dumpsys power | grep -A6 'Wake Locks'"

# —— 屏幕 ——
$ADB shell screencap -p /data/local/tmp/s.png && $ADB pull /data/local/tmp/s.png ./screen.png
$ADB shell input keyevent 3          # 按 Home 键

# —— 预装（在项目仓库根目录执行）——
powershell -File android\provision.ps1 -DeviceAddr <设备IP>:<端口>
```

## 八、附录：组件清单与维护边界

下表说明系统由哪些件组成、各自在哪儿、改动时要注意什么。**路径中"仓库"指本文档所在的代码仓库根目录。**

| 组件 | 位置 | 维护要点 |
|---|---|---|
| 启动器 APK | 仓库 `android/dist/RS485Launcher.apk` | 装到设备后同时注册为桌面（HOME），是"上电即用"的关键 |
| 启动器源码 | 仓库 `android/src/com/rs485/launcher/MainActivity.java` | 单 Activity，逻辑很短，改前先读懂上面那条启动链路 |
| APK 构建脚本 | 仓库 `android/build_apk.sh` | 免 Android Studio，一条命令出包 |
| 预装脚本 | 仓库 `android/provision.ps1` | 新设备一键预装（装 APK、设桌面、设屏幕常亮） |
| 签名密钥 | 仓库 `android/rs485.keystore` | **丢失后无法对已装机做覆盖升级**；口令由项目负责人保管，不记录在本文档 |
| 设备端启动脚本 | 设备 `/data/data/com.termux/files/home/start_rs485.sh` | 幂等，可重复执行；改动后必须重跑回归清单 |
| 设备端程序目录 | 设备 `/data/data/com.termux/files/home/rs485/` | RS485Control 二进制所在 |
| 设备端日志 | 设备 `~/apk_launch.log`、`~/x11.log`、`~/app_run.log` | 排障第一现场，出问题先看这三个 |
| 构建工具链 | 开发机自行准备 | Android build-tools 34、platform-33、JDK 17；版本需一致 |

> **一句话记住整套方法**：先分层定位，再单点验证；报错文案是线索不是结论，系统日志才是证据；改完必须过回归清单。
