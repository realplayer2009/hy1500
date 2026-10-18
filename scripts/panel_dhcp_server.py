#!/usr/bin/python3
# 给"直连 USB 网卡、网络上没有 DHCP"的 PA0715-N 面板当 DHCP 服务器。
#
# 场景: 现场要连续克隆 18 台屏, 屏与安装电脑的 USB 网卡直连, 段上没有 DHCP,
# 屏就只会一直广播 DHCP DISCOVER 而拿不到 IPv4, adb 连不上、程序灌不进去。
# (实测: 屏 MAC 2a:76:9b:52:1b:5e 在 en5 上持续发 0.0.0.0->255.255.255.255 请求)
#
# 用法(需要 root, 因为 DHCP 服务端口 67 是特权端口):
#   sudo python3 scripts/panel_dhcp_server.py
#
# 跑起来后屏会在几秒内拿到 192.168.0.50~60 之一的地址, 脚本会把"MAC -> IP"
# 打到屏幕上; 拿到地址后另开终端 adb connect <那个IP>:5555 即可灌程序。
# Ctrl-C 结束; 只影响这个直连段, 不动电脑其它网卡和现场网络。
#
# 实现要点:
#   - 只实现 DHCP 最核心的 DISCOVER->OFFER / REQUEST->ACK 两步, 现场足够。
#   - 出口网卡用 IP_BOUND_IF(macOS/BSD 特有)钉死在 USB 网卡上: 若不定,
#     发往 255.255.255.255 的广播会从默认路由口(本例是手机热点 en0)出去,
#     屏根本收不到, 表现就是"DHCP 服务器在跑但屏还是没 IP"。
#   - 按 MAC 记分配, 屏重启后拿回同一个地址, 方便连续克隆时对得上号。

import socket
import struct
import sys
import time

# ── 按现场改这三行 ─────────────────────────────────────────────────────
IFACE = "en5"                    # 插屏的那个 USB 网卡
SERVER_IP = "192.168.0.200"      # 电脑在该网卡上的地址
POOL = ["192.168.0.%d" % i for i in range(50, 61)]   # 可分配地址段
LEASE_SECONDS = 3600

MAGIC = b"\x63\x82\x53\x63"
BROADCAST = "255.255.255.255"


def iface_index(name):
    idx = socket.if_nametoindex(name)
    if not idx:
        sys.exit("找不到网卡 %s" % name)
    return idx


def parse_options(msg):
    """返回 {选项码: 值}; 认不出 magic cookie 或长度不足就返回 None。"""
    if len(msg) < 240 or msg[236:240] != MAGIC:
        return None
    opts = {}
    i = 240
    while i < len(msg):
        code = msg[i]
        if code == 0:                      # padding
            i += 1
            continue
        if code == 255:                    # end
            break
        if i + 1 >= len(msg):
            break
        ln = msg[i + 1]
        opts[code] = msg[i + 2:i + 2 + ln]
        i += 2 + ln
    return opts


def option(code, payload):
    return bytes([code, len(payload)]) + payload


def build_reply(req, msg_type, yiaddr):
    """按请求回一包 OFFER/ACK。xid/chaddr/flags 必须原样带回, 否则屏不认。"""
    xid = struct.unpack("!I", req[4:8])[0]
    flags = struct.unpack("!H", req[10:12])[0]
    ciaddr = req[12:16] if msg_type == 5 else b"\x00" * 4   # RENEW 才带 ciaddr
    out = struct.pack("!BBBBIHH", 2, 1, 6, 0, xid, 0, flags)
    out += ciaddr
    out += socket.inet_aton(yiaddr)          # yiaddr: 分配给屏的地址
    out += socket.inet_aton(SERVER_IP)       # siaddr
    out += b"\x00" * 4                       # giaddr
    out += req[28:34] + b"\x00" * 10         # chaddr(取前 6 字节 MAC)
    out += b"\x00" * 64 + b"\x00" * 128      # sname + file
    out += MAGIC
    out += option(53, bytes([msg_type]))                       # message type
    out += option(54, socket.inet_aton(SERVER_IP))             # server identifier
    out += option(51, struct.pack("!I", LEASE_SECONDS))        # lease time
    out += option(1, socket.inet_aton("255.255.255.0"))        # subnet mask
    out += option(3, socket.inet_aton(SERVER_IP))              # router
    out += option(6, socket.inet_aton(SERVER_IP))              # DNS
    out += b"\xff"
    return out


def handle(s, msg, assigned, ip_to_mac):
    """处理一个 DHCP 报文。拆出来单放, 方便主循环包 try 而不影响服务器存活。"""
    opts = parse_options(msg)
    if not opts or 53 not in opts:
        return
    mtype = opts[53][0]
    mac = ":".join("%02x" % b for b in msg[28:34])
    if mtype == 1:        # DISCOVER
        ip = assigned.get(mac)
        if ip is None:
            free = [p for p in POOL if p not in ip_to_mac]
            if not free:
                print("  地址池已满, 忽略 %s" % mac)
                return
            ip = free[0]
            assigned[mac] = ip
            ip_to_mac[ip] = mac
            print("  [分配] %s -> %s" % (mac, ip))
        s.sendto(build_reply(msg, 2, ip), (BROADCAST, 68))      # OFFER
    elif mtype == 3:      # REQUEST
        ip = assigned.get(mac)
        if ip is None:
            # 屏指名要的地址(选项 50), 在池里就让给它
            want = opts.get(50)
            if want:
                want_ip = socket.inet_ntoa(want)
                if want_ip in POOL and want_ip not in ip_to_mac:
                    ip = want_ip
                    assigned[mac] = ip
                    ip_to_mac[ip] = mac
                    print("  [按请求分配] %s -> %s" % (mac, ip))
        if ip is None:
            print("  %s 请求但无可用地址, 回 NAK" % mac)
            s.sendto(build_reply(msg, 6, "0.0.0.0"), (BROADCAST, 68))
            return
        s.sendto(build_reply(msg, 5, ip), (BROADCAST, 68))      # ACK
        print("  [确认] %s 已拿到 %s  <-- 用这个地址 adb connect %s:5555"
              % (mac, ip, ip))


def main():
    idx = iface_index(IFACE)
    assigned = {}          # mac -> ip
    ip_to_mac = {}

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # 关键: 把出口钉在插屏的那块网卡上, 否则广播走默认路由口
    IP_BOUND_IF = 25       # macOS/BSD 的 IP_BOUND_IF
    s.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, struct.pack("I", idx))
    try:
        # 必须绑 INADDR_ANY 而不是 SERVER_IP: 屏发的是 0.0.0.0->255.255.255.255
        # 广播, 目的地址不是 SERVER_IP, 绑到具体单播地址的内核不会把广播包
        # 送上来 —— 表现就是"服务器在跑、屏在拼命请求, 但两边都看不到对方"。
        # 收包范围由下面的 IP_BOUND_IF 收敛到插屏的那块网卡。
        s.bind(("", 67))
    except PermissionError:
        sys.exit("绑不上 67 端口 —— DHCP 服务端口是特权端口, 请用 sudo 运行")
    except OSError as e:
        sys.exit("绑定 %s:67 失败: %s (确认该网卡上配了这个地址)" % (SERVER_IP, e))

    print("DHCP 服务器已启动: 网卡 %s(index=%d) 地址 %s" % (IFACE, idx, SERVER_IP))
    print("可分配: %s ~ %s" % (POOL[0], POOL[-1]))
    print("等屏来要地址... (Ctrl-C 结束)\n")

    while True:
        try:
            msg, addr = s.recvfrom(2048)
        except KeyboardInterrupt:
            print("\n已停止")
            return
        except OSError as e:
            # 屏重启/拔线的瞬间接口状态会变, sendto 可能抛 Network is unreachable。
            # 这不是致命错误: 屏还会重发 DHCP, 所以打一行警告继续等, 不能退出。
            print("  [警告] 收包出错(%s), 继续等屏重发" % e)
            time.sleep(1)
            continue
        try:
            handle(s, msg, assigned, ip_to_mac)
        except Exception as e:
            # 单包解析或发送失败不该让整个服务器退出, 否则 18 台部署时
            # 一包异常就全停; 屏自己会重发, 下次还有机会。
            print("  [警告] 处理一包时出错(%s), 忽略该包继续" % e)
            continue


if __name__ == "__main__":
    main()
