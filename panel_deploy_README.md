# 面板克隆部署包

连续克隆同款 PA0715-N 面板用的「程序 + 设定 + 工具」三件套。
本目录不进版本库（APK 有 9.4 MB），由 `scripts/clone_panel.sh` 按需引用。

## 内容

| 文件 | 说明 |
|---|---|
| `RS485Control-arm64-v8a-debug.apk` | 程序。CI 产物，对应 commit `84934fc`（手动模式告警灯长亮 + 呼吸灯 1.12s + 跨主题 pill 守门） |
| `app.ini` | 设定模板。从现网面板 `192.168.0.32` 整份拉取，含现场接线映射与温控参数 |
| `retry.txt` | 续跑用 IP 列表模板（`scripts/clone_panel.sh -f` 吃这个格式） |

## 设定模板里值得留意的项

这些是**现场接线与工况**，克隆时原样带走：

```
displayTheme=low_light          # 低光主题
expIn1Mode=manual_auto          # IN1 = 手/自动切换开关
expIn2Mode=heater_a             # IN2 = 加热器 A 实体按键
expIn3Mode=heater_b             # IN3 = 加热器 B 实体按键
expIn4Mode=heater_c             # IN4 = 加热器 C 实体按键
heaterAPair=2 / BPair=3 / CPair=4   # A/B/C 各占一对 OT
temperatureTargetSource=fixed   # 固定温度目标(不跟 PT100)
pollIntervalMs=100              # 轮询 100ms
recordIntervalMs=1000           # 记录 1s
brightnessPercent=97            # 背光
idleDimMinutes=30 / idleDimPercent=1   # 无人值守 30 分钟降到 1%
```

两台现网面板的主题并不相同（`.32` 是 `low_light`，`.34` 是 `graphite`）。
模板取 `.32` 的 `low_light`；若要统一成石墨灰，改这一行再克隆。

## 三种用法

```bash
# 单台
scripts/clone_panel.sh 192.168.0.40

# 批量(18 台): 一行一个 IP, # 注释和空行会自动剔除
scripts/clone_panel.sh -f ~/panel_deploy/retry.txt

# 只装程序不动面板现有设定
scripts/clone_panel.sh -f retry.txt --no-config

# 先只查在线状态, 不装任何东西
scripts/clone_panel.sh --dry-run -f retry.txt
```

每台的处理顺序是固定的，不能换：
连接 → 停应用 → 装 APK → 校验 native 库 → **启动一次让应用自建数据目录** → 再停
→ 备份旧配置 → 推模板配置 → **chown 回应用 uid** → 启动 → 读回校验

## 两个必须这么做的原因

**1. 为什么要"启动一次再停"**

`/data/data/com.rs485.control/files/config/` 这个目录必须由**应用自己**（以 app uid）
创建。如果脚本用 `su 0 mkdir -p` 建，属主会是 root，应用之后写不回 `app.ini`——
现场改了参数存不住，而且不报错。

**2. 为什么推完配置还要 chown**

`su 0 cp` 写进去的文件是 `root:root`，同样导致应用写不回去。
所以推完必须 `chown -R <appUid>:<appGid>` 把属主还给应用。

这两条都会在脚本里打印确认信息，属主读回不符时会给出警告。

## 保留与可恢复

- 安装走 `install -r`，**不动**面板上的 `data/logs` 历史数据
- 覆盖配置前，旧配置备份成 `app.ini.bak-<时间戳>` 留在面板上，不删

## 直连屏拿不到 IP 时

若屏与电脑 USB 网卡直连、段上没有 DHCP，屏会一直广播 DHCP DISCOVER 而拿不到
IPv4（实测面板 MAC `2a:76:9b:52:1b:5e`，每 30~60 秒一次，永远没有 ACK）。
此时需要电脑充当 DHCP 服务器：

```bash
sudo python3 scripts/panel_dhcp_server.py
```

脚本会把 `MAC -> IP` 打到屏幕上，屏拿到地址后 `adb connect <那个IP>:5555` 即可。
该脚本已按 `IP_BOUND_IF` 把出口钉死在插屏的网卡上——不定的话广播会从默认
路由口（手机热点）出去，屏根本收不到，表现就是"DHCP 服务器在跑但屏还是没 IP"。
