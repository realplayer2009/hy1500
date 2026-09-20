# linaro-alip 设备配置记录

> 最后实机核对时间：2026-08-31
>
> 2026-09-01 整理本文档时设备未连接。下列内容来自最后一次 SSH 登录、编译和运行验证。
>
> **敏感信息提醒：本文档按要求明文记录了设备登录密码，不宜上传到公开仓库或发送给无关人员。**

## 1. 设备概况

| 项目 | 配置 |
| --- | --- |
| 主机名 | `linaro-alip` |
| 板卡型号 | Rockchip RK3562 ZYSJ 2362K V10 Board |
| CPU 架构 | ARM64 / AArch64 |
| 操作系统 | Debian GNU/Linux 11（bullseye） |
| 内核 | Linux `5.10.198`，构建号 `#11195 #9` |
| 内核构建时间 | 2025-06-30 09:29:54 CST |
| 登录用户 | `root` |
| 已有普通用户 | `linaro` |
| 图形桌面 | LightDM + Xorg `:0` + XFCE |
| 系统时区显示 | HKT（UTC+8） |

工程文档中曾写 RK3568/Ubuntu 22.04，但实际设备检测结果为 **RK3562/Debian 11**，部署和依赖选择应以实机为准。

### 1.1 登录凭据

| 项目 | 配置 |
| --- | --- |
| SSH 用户名 | `root` |
| root 密码 | `1` |

该密码已于 2026-08-31 通过 SSH 实际登录验证。

## 2. 资源情况

最后一次检查结果：

| 项目 | 数值 |
| --- | --- |
| 内存总量 | 约 1.9 GiB |
| 当时可用内存 | 约 1.5 GiB |
| Swap | 未配置 |
| 根文件系统 | `/dev/root`，约 28 GiB |
| 当时已用空间 | 约 3.6 GiB（14%） |
| 当时可用空间 | 约 23 GiB |
| systemd 失败服务 | 0 个 |

该资源量足够在板上使用 `make -j2` 原生编译当前 Qt 工程。选择 `-j2` 是为了兼顾编译速度和 2 GiB 内存限制。

## 3. 网络配置

### 3.1 开发板端

| 项目 | 配置 |
| --- | --- |
| 有线接口 | `eth0` |
| MAC 地址 | `92:e9:0e:81:92:54` |
| IPv6 链路本地地址 | `fe80::4d44:6ae8:aa2a:e68c/64` |
| 临时 IPv4 地址 | `10.42.0.1/24` |
| 临时默认网关 | `10.42.0.2` |

临时 IPv4 是在设备上手动执行以下命令设置的：

```bash
ip link set eth0 up
ip addr replace 10.42.0.1/24 dev eth0
ip route replace default via 10.42.0.2 dev eth0
```

这些 `ip` 命令只修改运行时状态，**设备重启后会丢失**。此前曾出现网口灯亮但系统无 IP、IPv6 也不响应的情况；网口灯亮只表示物理载波存在。

无 IPv4 时可尝试通过链路本地 IPv6 登录，接口作用域 `%enp1s0` 不能省略：

```bash
ssh -6 root@'fe80::4d44:6ae8:aa2a:e68c%enp1s0'
```

有临时 IPv4 时使用：

```bash
ssh root@10.42.0.1
```

### 3.2 上位电脑端

| 项目 | 配置 |
| --- | --- |
| 有线接口 | `enp1s0` |
| 有线地址 | `10.42.0.2/24` |
| NetworkManager 连接 | `netplan-enp1s0` |
| IPv4 模式 | `shared`（共享电脑的上游网络） |

为让开发板访问 Debian 软件源，电脑端的 `netplan-enp1s0` 已切换为 NetworkManager 的共享模式。该模式负责 IPv4 转发、NAT 和 DNS 转发。

## 4. SSH 与对外服务

SSH 服务版本：

```text
OpenSSH 8.4p1 Debian 5+deb11u5
```

最后核对的 SSH 有效配置：

```text
permitrootlogin yes
passwordauthentication yes
pubkeyauthentication yes
```

监听端口：

| 端口 | 服务 |
| --- | --- |
| TCP 22 | SSH |
| TCP 5555 | ADB |
| UDP 500、4500 | IPsec/strongSwan `charon` |
| UDP 1701 | L2TP `xl2tpd` |
| UDP 123 | NTP |

当前允许 root 密码登录，且 ADB 监听所有地址。设备接入非隔离网络前应改用强密码或 SSH 密钥，并按需限制 5555 端口。

## 5. 显示环境

| 项目 | 配置 |
| --- | --- |
| X11 Display | `:0` |
| X Server | `/usr/lib/xorg/Xorg` |
| 登录管理器 | LightDM |
| 桌面 | XFCE |
| 帧缓冲 | `/dev/fb0` |
| DRM 显卡 | `/dev/dri/card0` |
| DRM Render 节点 | `/dev/dri/renderD128` |

Rockchip OpenGL 驱动启动时曾出现 DRI 加载警告，因此桌面启动器使用：

```bash
QT_XCB_GL_INTEGRATION=none
```

程序可以在 X11 桌面正常显示，不是只能命令行运行。

## 6. 串口配置

系统检测到以下板载串口：

```text
/dev/ttyS1
/dev/ttyS2
/dev/ttyS4
/dev/ttyS5
/dev/ttyS6
/dev/ttyS7
/dev/ttyS8
```

部署程序使用：

| 项目 | 配置 |
| --- | --- |
| 设备节点 | `/dev/ttyS5` |
| 波特率 | 19200 |
| 数据位 | 8 |
| 校验 | N（无校验） |
| 停止位 | 1 |
| 帧间隔 | 5 ms |

选择 `/dev/ttyS5` 的依据是板上已有的 CuteCom 配置 `/root/.config/CuteCom/CuteCom5.conf` 曾实际选择该端口，而不是仅根据设备节点编号猜测。程序运行时已通过 `/proc/<PID>/fd` 验证成功打开 `/dev/ttyS5`。

## 7. Qt 编译环境

板上原有 `g++`、`make` 和 `pkg-config`，后来安装了：

```text
qtbase5-dev
qt5-qmake
qtchooser
libqt5serialport5-dev
```

版本情况：

| 项目 | 版本 |
| --- | --- |
| GCC/G++ | 10.2.1 |
| qmake | 3.1 |
| Qt | 5.15.2，AArch64 |

软件源使用中科大 Debian 镜像。`bullseye`、`bullseye-security` 和 `bullseye-updates` 可用；`bullseye-backports` 当时返回 404，后续执行 `apt update` 时仍可能报该源无 Release 文件。

## 8. RS485Control 部署

| 项目 | 配置 |
| --- | --- |
| 工程目录 | `/root/RS485Control` |
| 可执行文件 | `/root/RS485Control/RS485Control` |
| 架构 | ELF 64-bit ARM AArch64 |
| 配置文件 | `/root/RS485Control/config/app.ini` |
| 运行数据目录 | `/root/RS485Control/data/logs` |
| 运行日志（曾用于后台测试） | `/var/log/RS485Control.log` |

板上编译命令：

```bash
cd /root/RS485Control
make distclean
qmake RS485Control.pro
make -j2
file RS485Control
```

目标板上的 `config/app.ini` 与电脑端源码目录中的默认文件有一处部署差异：

```ini
[Port0]
enabled=true
device=/dev/ttyS5
baudRate=19200
dataBits=8
parity=N
stopBits=1
frameDelayMs=5
```

通用参数：

```ini
[General]
dataPath=data/logs
retentionDays=30
maxStorageMB=512
pollIntervalMs=1000
modbusTimeoutMs=500
interSlaveDelayMs=50
recordIntervalSec=60
```

已启用的逻辑设备：

| 名称 | 物理端口 | Modbus 从站地址 |
| --- | --- | --- |
| `PcbBoard-1` | Port0 | 1 |
| `PcbBoard-2` | Port0 | 2 |

## 9. 桌面启动器

桌面已创建：

```text
/root/Desktop/RS485Control.desktop
```

启动器内容：

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=RS485控制程序
Comment=启动RS485 Modbus控制界面
Exec=env QT_XCB_GL_INTEGRATION=none /root/RS485Control/RS485Control
Path=/root/RS485Control
Icon=utilities-terminal
Terminal=false
StartupNotify=true
Categories=Utility;
```

它已设置为可执行和可信，可在桌面双击运行。`Path` 必须指向工程目录，否则程序可能找不到相对路径下的 `config/app.ini` 和 `data/logs`。

桌面启动器不是开机自启动项。设备重启后仍需人工双击，除非以后另外配置 XFCE Autostart 或永久 systemd 服务。

## 10. 重启后需要注意的项目

1. `10.42.0.1/24` 和默认路由是临时设置，重启后可能消失。
2. `RS485Control` 当前没有配置开机自启动。
3. 桌面启动器、编译产物、Qt 软件包和 `/root/RS485Control` 会保留。
4. 如果再次出现网口灯亮但无法连接，先在板端本地终端检查：

```bash
ip -brief link show eth0
ip -brief addr show eth0
ethtool eth0 | grep -E 'Speed|Duplex|Link detected'
```

然后按需恢复临时直连地址：

```bash
ip link set eth0 up
ip addr replace 10.42.0.1/24 dev eth0
ip route replace default via 10.42.0.2 dev eth0
```
