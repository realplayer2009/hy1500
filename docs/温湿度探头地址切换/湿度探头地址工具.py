#!/usr/bin/env python3
"""检测并修改 RS485 温湿度探头的 Modbus 地址。

依据《湿度探头_Modbus_ID配置记录.md》和郎汉德 LH-TH 系列手册：
- 串口固定为 9600 bps、8N1；不会改写波特率寄存器。
- 温湿度寄存器为 0x0000、0x0001，地址配置寄存器为 0x0100。
- 地址变更使用功能码 0x06，写完后通过新旧地址分别验证。

依赖：python3 -m pip install pyserial

用法：
    python3 湿度探头地址工具.py scan
    python3 湿度探头地址工具.py read 1
    python3 湿度探头地址工具.py change 1 3
"""

from __future__ import annotations

import argparse
import sys
import time

try:
    import serial
except ImportError as exc:
    raise SystemExit("缺少 pyserial，请先执行：python3 -m pip install pyserial") from exc


DEFAULT_PORT = "/dev/ttyUSB1"
BAUDRATE = 9600
ADDRESS_REGISTER = 0x0100


class ModbusError(Exception):
    """串口通信或 Modbus 响应错误。"""


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def frame_with_crc(data: bytes) -> bytes:
    crc = crc16(data)
    return data + bytes((crc & 0xFF, crc >> 8))


def show_frame(prefix: str, data: bytes) -> None:
    print(f"{prefix}: {' '.join(f'{byte:02X}' for byte in data)}")


class Probe:
    def __init__(self, port_name: str, timeout: float, verbose: bool) -> None:
        self.port_name = port_name
        self.timeout = timeout
        self.verbose = verbose
        try:
            self.port = serial.Serial(
                port=port_name,
                baudrate=BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.03,
                write_timeout=1,
            )
        except serial.SerialException as exc:
            raise ModbusError(f"无法打开串口 {port_name}: {exc}") from exc

    def close(self) -> None:
        self.port.close()

    def exchange(self, request: bytes, function: int) -> bytes:
        self.port.reset_input_buffer()
        if self.verbose:
            show_frame("发送", request)
        self.port.write(request)
        self.port.flush()

        received = bytearray()
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            chunk = self.port.read(1)
            if chunk:
                received.extend(chunk)
            elif received:
                break
        if not received:
            raise TimeoutError("等待设备响应超时")

        response = bytes(received)
        # 某些 USB-RS485 转换器会回显发送帧。读寄存器时剥掉回显；
        # 0x06 正常响应本身与请求完全相同，因此单帧回显也可作为写确认。
        if function == 0x03 and response.startswith(request):
            response = response[len(request) :]
            if not response:
                raise TimeoutError("只收到本地发送回显，没有收到设备响应")
        elif function == 0x06 and len(response) == 16 and response.startswith(request):
            response = response[8:]

        if self.verbose:
            show_frame("接收", response)
        if len(response) < 5:
            raise ModbusError(f"响应帧过短：{response.hex(' ').upper()}")
        expected_crc = int.from_bytes(response[-2:], "little")
        if crc16(response[:-2]) != expected_crc:
            raise ModbusError(f"响应 CRC 错误：{response.hex(' ').upper()}")
        if response[0] != request[0]:
            raise ModbusError(f"响应地址为 {response[0]}，预期 {request[0]}")
        if response[1] == (function | 0x80):
            raise ModbusError(f"设备返回 Modbus 异常码 0x{response[2]:02X}")
        if response[1] != function:
            raise ModbusError(f"响应功能码为 0x{response[1]:02X}，预期 0x{function:02X}")
        return response

    def read_registers(self, address: int, start: int, count: int) -> list[int]:
        if not 1 <= address <= 247:
            raise ValueError("设备地址必须为 1～247")
        request = frame_with_crc(
            bytes((address, 0x03))
            + start.to_bytes(2, "big")
            + count.to_bytes(2, "big")
        )
        response = self.exchange(request, 0x03)
        if len(response) != 5 + count * 2 or response[2] != count * 2:
            raise ModbusError(f"寄存器响应长度不符：{response.hex(' ').upper()}")
        return [
            int.from_bytes(response[index : index + 2], "big")
            for index in range(3, 3 + count * 2, 2)
        ]

    def write_address(self, current_address: int, new_address: int) -> None:
        request = frame_with_crc(
            bytes((current_address, 0x06))
            + ADDRESS_REGISTER.to_bytes(2, "big")
            + new_address.to_bytes(2, "big")
        )
        response = self.exchange(request, 0x06)
        if response != request:
            raise ModbusError("写地址响应与请求不一致")


def print_measurements(probe: Probe, address: int) -> list[int]:
    humidity_raw, temperature_raw = probe.read_registers(address, 0x0000, 2)
    temperature = (
        temperature_raw if temperature_raw < 0x8000 else temperature_raw - 0x10000
    )
    print(
        f"地址 {address}: 湿度 {humidity_raw / 10:.1f}%RH，"
        f"温度 {temperature / 10:.1f}℃"
    )
    return [humidity_raw, temperature_raw]


def scan(probe: Probe) -> int:
    print(f"扫描 Modbus 地址 1～247（{BAUDRATE} bps、8N1）…")
    found = 0
    for address in range(1, 248):
        try:
            print_measurements(probe, address)
            found += 1
        except TimeoutError:
            continue
        except ModbusError as exc:
            print(f"地址 {address} 响应异常：{exc}")
    if not found:
        print("没有探测到有效响应。请检查供电、A/B 接线、串口号及 9600 bps 通信参数。")
        return 1
    print(f"扫描完成，发现 {found} 个响应地址。")
    return 0


def change_address(probe: Probe, old_address: int, new_address: int) -> int:
    if not 1 <= old_address <= 247 or not 1 <= new_address <= 247:
        raise ValueError("新旧地址都必须在 1～247 范围内")
    if old_address == new_address:
        raise ValueError("新旧地址相同，无需修改")

    print("先读取当前配置和温湿度，确认旧地址可用…")
    settings = probe.read_registers(old_address, ADDRESS_REGISTER, 2)
    if settings[0] != old_address:
        raise ModbusError(
            f"地址 {old_address} 的设备报告自身地址为 {settings[0]}，为避免误写已停止"
        )
    print(f"当前地址寄存器：0x0100={settings[0]}，波特率代码 0x0101={settings[1]}")
    print_measurements(probe, old_address)

    try:
        print_measurements(probe, new_address)
    except TimeoutError:
        pass
    else:
        raise ModbusError(
            f"新地址 {new_address} 已有设备响应。请选未占用地址，避免总线地址冲突。"
        )

    print(f"将地址 {old_address} 改为 {new_address}；通信波特率保持 {BAUDRATE} bps。")
    try:
        probe.write_address(old_address, new_address)
    except (TimeoutError, ModbusError) as exc:
        print(f"写入确认帧异常（{exc}），继续通过新旧地址读回判断是否生效。")

    time.sleep(0.15)
    try:
        settings = probe.read_registers(new_address, ADDRESS_REGISTER, 2)
        if settings[0] != new_address:
            raise ModbusError(
                f"新地址有响应，但地址寄存器读回 {settings[0]}，预期 {new_address}"
            )
        print(f"新地址 {new_address} 读回成功；波特率代码仍为 {settings[1]}。")
        print_measurements(probe, new_address)
    except (TimeoutError, ModbusError) as exc:
        raise ModbusError(f"新地址验证失败：{exc}") from exc

    try:
        print_measurements(probe, old_address)
    except TimeoutError:
        print(f"旧地址 {old_address} 无响应，地址切换验证通过。")
        return 0
    raise ModbusError(
        f"旧地址 {old_address} 仍有响应；可能有重复地址设备，或地址切换未完成。"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="检测 RS485 温湿度探头，并通过 0x0100 寄存器修改 Modbus 地址。"
    )
    parser.add_argument(
        "--port", default=DEFAULT_PORT, help=f"串口设备（默认 {DEFAULT_PORT}）"
    )
    parser.add_argument(
        "--timeout", type=float, default=0.15, help="单次响应超时秒数（默认 0.15）"
    )
    parser.add_argument("--verbose", action="store_true", help="显示 Modbus 请求和响应帧")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scan", help="扫描地址 1～247 并显示响应探头的温湿度")
    read_command = commands.add_parser("read", help="读取指定地址的温湿度")
    read_command.add_argument("address", type=int, help="探头地址 1～247")
    change_command = commands.add_parser("change", help="修改地址并验证新旧地址")
    change_command.add_argument("old_address", type=int, help="当前探头地址")
    change_command.add_argument("new_address", type=int, help="要设置的新地址")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")

    try:
        probe = Probe(args.port, args.timeout, args.verbose)
        try:
            if args.command == "scan":
                return scan(probe)
            if args.command == "read":
                print_measurements(probe, args.address)
                return 0
            return change_address(probe, args.old_address, args.new_address)
        finally:
            probe.close()
    except (ModbusError, serial.SerialException, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
