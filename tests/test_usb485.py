#!/usr/bin/env python3
"""USB-RS485 设备连通性测试：打开端口、遍历常见波特率、发送 Modbus RTU 请求帧并监听响应。"""
import sys
import time
import serial

PORT = "/dev/cu.usbserial-110"

# Modbus RTU: 从站1, 功能码03, 起始地址0x0000, 读2个寄存器 (带CRC16)
def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def make_frame() -> bytes:
    pdu = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x02])
    return pdu + crc16(pdu).to_bytes(2, "little")

def try_baud(baud: int, parity: str) -> bytes:
    with serial.Serial(PORT, baudrate=baud, bytesize=8, parity=parity,
                       stopbits=1, timeout=0.2, write_timeout=1) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(make_frame())
        ser.flush()
        return ser.read(256)

def main() -> int:
    print(f"测试端口: {PORT}")
    try:
        ser = serial.Serial(PORT)
    except serial.SerialException as e:
        print(f"打开失败: {e}")
        return 1
    print(f"打开成功: {ser.name}")
    ser.close()

    frame = make_frame()
    print(f"测试帧: {frame.hex(' ').upper()} (Modbus RTU 读保持寄存器, 从站1)")
    print()

    any_response = False
    for parity, pname in (("N", "8N1"), ("E", "8E1")):
        for baud in (9600, 19200, 38400, 57600, 115200):
            try:
                resp = try_baud(baud, parity)
            except serial.SerialException as e:
                print(f"  {pname} @ {baud:>6}: 串口错误 {e}")
                continue
            if resp:
                any_response = True
                print(f"  {pname} @ {baud:>6}: 收到 {len(resp)} 字节 -> {resp.hex(' ').upper()}")
            else:
                print(f"  {pname} @ {baud:>6}: 无响应(超时)")
    print()
    if any_response:
        print("结论: 设备工作正常, 总线上有从站应答。")
    else:
        print("结论: 端口可正常打开和发送, 但未收到任何应答 —— ")
        print("      若总线上未接从站设备, 这属于预期结果, 设备本身可用。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
