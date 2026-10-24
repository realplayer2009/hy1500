#!/usr/bin/env python3
"""PTY Modbus RTU 从站模拟器：模拟温湿度探头的寄存器与怪癖。

寄存器（与现场探头一致）：
    0x0000 湿度（682 → 68.2 %RH）
    0x0001 温度（250 → 25.0 ℃）
    0x0100 设备 ID
    0x0101 波特率代码（4）

模拟的真实探头怪癖：
    1. 改 ID 后，第一次用新 ID 读取会超时（不响应），第二次起正常；
    2. 只有帧头从站地址等于当前 ID 时才响应；
    3. 仅支持 0x03 / 0x06，其他功能码返回异常 01。
"""
import os
import pty
import select
import sys
import time

REG_HUMIDITY, REG_TEMPERATURE, REG_ID, REG_BAUD = 0x0000, 0x0001, 0x0100, 0x0101


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def main() -> None:
    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    with open("/tmp/probe_sim_port.txt", "w") as f:
        f.write(slave_name)

    state = {REG_HUMIDITY: 682, REG_TEMPERATURE: 250, REG_ID: 1, REG_BAUD: 4}
    new_id_pending_timeout = False  # 改 ID 后首读新 ID 超时
    buffer = b""

    print(f"模拟探头就绪，PTY: {slave_name}", flush=True)
    try:
        while True:
            readable, _, _ = select.select([master], [], [], 0.5)
            if not readable:
                continue
            chunk = os.read(master, 256)
            if not chunk:
                continue
            buffer += chunk
            # 找完整帧：Modbus RTU 3.5 字符间隔，这里按最小请求长度 8 解析
            while len(buffer) >= 8:
                frame = buffer[:8]
                buffer = buffer[8:]
                if crc16(frame[:-2]) != int.from_bytes(frame[-2:], "little"):
                    continue
                slave_addr, func = frame[0], frame[1]
                if slave_addr != state[REG_ID]:
                    continue
                if func == 0x03:
                    if new_id_pending_timeout:
                        new_id_pending_timeout = False
                        print(f"[模拟] 新 ID {slave_addr} 首次读取 → 故意超时不响应", flush=True)
                        continue
                    start = int.from_bytes(frame[2:4], "big")
                    count = int.from_bytes(frame[4:6], "big")
                    values = [state.get(start + i, 0) for i in range(count)]
                    body = bytes([slave_addr, 0x03, 2 * count])
                    for v in values:
                        body += v.to_bytes(2, "big")
                    os.write(master, body + crc16(body).to_bytes(2, "little"))
                    print(f"[模拟] 0x03 读 0x{start:04X}×{count} → {values}", flush=True)
                elif func == 0x06:
                    addr = int.from_bytes(frame[2:4], "big")
                    value = int.from_bytes(frame[4:6], "big")
                    state[addr] = value
                    if addr == REG_ID:
                        new_id_pending_timeout = True
                        print(f"[模拟] 0x06 写设备 ID → {value}", flush=True)
                    else:
                        print(f"[模拟] 0x06 写 0x{addr:04X} → {value}", flush=True)
                    echo = frame[:6]
                    os.write(master, echo + crc16(echo).to_bytes(2, "little"))
                else:
                    body = bytes([slave_addr, func | 0x80, 0x01])
                    os.write(master, body + crc16(body).to_bytes(2, "little"))
                    print(f"[模拟] 功能码 0x{func:02X} → 异常 01", flush=True)
    finally:
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    main()
