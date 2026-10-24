#!/usr/bin/env python3
"""485 探头串口桥：Electron 主进程拉起，stdio 走 JSON 行协议。

协议（每行一个 JSON 对象）：
  请求: {"id": 1, "cmd": "...", ...}
  响应: {"id": 1, "ok": true, ...}  /  {"id": 1, "ok": false, "error": "..."}
  事件: {"event": "reading", ...}   （无 id，主动推送）

Modbus 实现复用自探头ID配置工具（现场实测加固版）：
  - 串口访问 threading.Lock 互斥（轮询线程与命令处理共用串口）
  - 改 ID 后新 ID 首读超时重试 5×0.4s（探头切换 ID 需要时间）
  - 写入后强制验证：旧 ID 停止响应、新 ID 正常、读数与改前一致
  - 端口发现用 glob，不用 serial.tools.list_ports
"""

import glob
import json
import queue
import sys
import threading
import time

import serial

# ---------------------------------------------------------------- Modbus

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class ModbusError(Exception):
    pass


class ModbusTimeout(Exception):
    pass


class ProbeClient:
    def __init__(self, port: str, baud: int, timeout: float = 0.4):
        self._ser = serial.Serial(
            port=port, baudrate=baud, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=timeout, write_timeout=1.0,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._io_lock = threading.Lock()

    def close(self):
        try:
            self._ser.close()
        except Exception:
            pass

    def transact(self, pdu: bytes, expect_len: int) -> bytes:
        with self._io_lock:
            frame = pdu + crc16(pdu).to_bytes(2, "little")
            self._ser.write(frame)
            self._ser.flush()
            response = self._ser.read(expect_len)
        if len(response) < 5:
            raise ModbusTimeout(f"等待响应超时（收到 {len(response)} 字节）")
        if crc16(response[:-2]) != int.from_bytes(response[-2:], "little"):
            raise ModbusError("响应 CRC 校验失败")
        if response[0] != pdu[0]:
            raise ModbusError("响应从站地址与请求不符")
        if response[1] not in (pdu[1], pdu[1] | 0x80):
            raise ModbusError("响应功能码与请求不符")
        if response[1] & 0x80:
            raise ModbusError(f"设备返回异常码 0x{response[2]:02X}")
        if len(response) != expect_len:
            raise ModbusError("响应长度与请求不符")
        if pdu[1] == 0x06 and response[:-2] != pdu:
            raise ModbusError("写寄存器回显与请求不符")
        return response

    def read_holding(self, slave: int, start: int, count: int) -> list:
        pdu = bytes([slave, 0x03]) + start.to_bytes(2, "big") + count.to_bytes(2, "big")
        response = self.transact(pdu, 5 + 2 * count)
        if response[2] != 2 * count:
            raise ModbusError(f"响应字节数不符：期望 {2 * count}，实际 {response[2]}")
        body = response[3:3 + 2 * count]
        return [int.from_bytes(body[i:i + 2], "big") for i in range(0, len(body), 2)]

    def write_register(self, slave: int, addr: int, value: int) -> None:
        pdu = bytes([slave, 0x06]) + addr.to_bytes(2, "big") + value.to_bytes(2, "big")
        self.transact(pdu, 8)

    def read_measurements(self, slave: int) -> tuple:
        humidity_raw, temperature_raw = self.read_holding(slave, 0x0000, 2)
        if temperature_raw >= 0x8000:
            temperature_raw -= 0x10000
        return humidity_raw / 10.0, temperature_raw / 10.0

    def read_device_id(self, slave: int) -> int:
        return self.read_holding(slave, 0x0100, 1)[0]


def find_serial_ports() -> list:
    ports = []
    for pattern in ("/dev/cu.usbserial-*", "/dev/cu.wchusbserial-*",
                    "/dev/cu.SLAB_USBtoUART*", "/dev/cu.usbmodem*"):
        ports.extend(sorted(glob.glob(pattern)))
    return ports


# ---------------------------------------------------------------- 桥服务

class Bridge:
    def __init__(self):
        self._client = None
        self._current_id = None
        self._last_known_id = None  # 跨连接记忆：重连时优先探测该 ID
        self._stop = threading.Event()
        self._worker = None
        self._cmd_lock = threading.Lock()  # 命令串行化，避免同时操作串口

    # ---- 事件输出 ----

    def emit(self, obj: dict) -> None:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def log(self, message: str, level: str = "info") -> None:
        self.emit({"event": "log", "message": message, "level": level})

    # ---- 命令处理 ----

    def handle(self, req: dict) -> dict:
        cmd = req.get("cmd")
        rid = req.get("id")
        try:
            with self._cmd_lock:
                if cmd == "list_ports":
                    ports = find_serial_ports()
                    default = next((p for p in ports if "usbserial" in p), ports[0] if ports else None)
                    return {"id": rid, "ok": True, "ports": ports, "default": default}
                if cmd == "connect":
                    return self._cmd_connect(rid, req)
                if cmd == "disconnect":
                    return self._cmd_disconnect(rid)
                if cmd == "change_id":
                    return self._cmd_change_id(rid, req)
                if cmd == "read_registers":
                    return self._cmd_read_registers(rid, req)
                if cmd == "write_register":
                    return self._cmd_write_register(rid, req)
                if cmd == "send_raw":
                    return self._cmd_send_raw(rid, req)
                return {"id": rid, "ok": False, "error": f"未知命令 {cmd}"}
        except Exception as exc:  # 兜底：任何异常都不让桥进程退出
            return {"id": rid, "ok": False, "error": str(exc)}

    def _cmd_connect(self, rid, req):
        if self._client is not None:
            self._teardown()
        port, baud = req.get("port"), int(req.get("baud", 9600))
        try:
            self._client = ProbeClient(port, baud)
        except serial.SerialException as exc:
            self._client = None
            return {"id": rid, "ok": False,
                    "error": f"无法打开 {port}：{exc}\n请检查转换器是否插好、是否被其他程序占用"}
        self._current_id = None
        self._stop.clear()
        self.log(f"已连接 {port} @ {baud} 8N1")
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        return {"id": rid, "ok": True}

    def _cmd_disconnect(self, rid):
        self._teardown()
        self.log("已断开连接")
        return {"id": rid, "ok": True}

    def _cmd_change_id(self, rid, req):
        new_id = int(req.get("new_id"))
        if not (1 <= new_id <= 247):
            return {"id": rid, "ok": False, "error": "新 ID 必须是 1~247 的整数"}
        client, old_id = self._client, self._current_id
        if client is None or old_id is None:
            return {"id": rid, "ok": False, "error": "请先连接探头"}

        # 先停轮询线程，避免和改 ID 抢串口
        self._stop.set()
        if self._worker is not None:
            self._worker.join()
        self._worker = None
        try:
            result = self._run_id_change(client, old_id, new_id)
        finally:
            if self._client is not None:
                self._stop.clear()
                self._worker = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker.start()
        return {"id": rid, "ok": True, "result": result}

    def _cmd_read_registers(self, rid, req):
        client, slave = self._client, self._current_id
        if client is None or slave is None:
            return {"id": rid, "ok": False, "error": "请先连接探头"}
        start, count = int(req.get("start")), int(req.get("count"))
        if not (0 <= start <= 0xFFFF and 1 <= count <= 125):
            return {"id": rid, "ok": False, "error": "地址 0~0xFFFF，数量 1~125"}
        values = client.read_holding(slave, start, count)
        return {"id": rid, "ok": True,
                "registers": [{"address": start + i, "value": v} for i, v in enumerate(values)]}

    def _cmd_write_register(self, rid, req):
        client, slave = self._client, self._current_id
        if client is None or slave is None:
            return {"id": rid, "ok": False, "error": "请先连接探头"}
        addr, value = int(req.get("addr")), int(req.get("value"))
        if not (0 <= addr <= 0xFFFF and 0 <= value <= 0xFFFF):
            return {"id": rid, "ok": False, "error": "地址 0~0xFFFF，值 0~0xFFFF"}
        client.write_register(slave, addr, value)
        return {"id": rid, "ok": True}

    def _cmd_send_raw(self, rid, req):
        client = self._client
        if client is None:
            return {"id": rid, "ok": False, "error": "请先连接探头"}
        payload = bytes.fromhex(req.get("hex", "").replace(" ", ""))
        if req.get("append_crc", True):
            payload += crc16(payload).to_bytes(2, "little")
        # 请求和响应共用一次加锁，防止轮询线程取走调试响应。
        with client._io_lock:
            client._ser.write(payload)
            client._ser.flush()
            time.sleep(0.3)
            response = client._ser.read(client._ser.in_waiting or 1)
        return {"id": rid, "ok": True,
                "tx": payload.hex(" ").upper(),
                "rx": response.hex(" ").upper() if response else ""}

    # ---- 改 ID 全流程（现场加固逻辑）----

    def _run_id_change(self, client: ProbeClient, old_id: int, new_id: int) -> dict:
        self.log(f"开始修改 ID：{old_id} → {new_id}")
        before = client.read_measurements(old_id)
        self.log(f"修改前读数（ID {old_id}）：湿度 {before[0]:.1f} %RH，温度 {before[1]:.1f} ℃")
        client.write_register(old_id, 0x0100, new_id)
        self.log(f"已发送写寄存器命令：0x0100 = {new_id}")

        after, last_error = None, None
        for attempt in range(5):
            time.sleep(0.4)
            try:
                after = client.read_measurements(new_id)
                break
            except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
                last_error = exc
                self.log(f"新 ID {new_id} 第 {attempt + 1} 次验证读取失败：{exc}", "warn")
        if after is None:
            actual = self._detect_current_id(client)
            if actual is not None and actual != old_id:
                self._current_id = actual
                self._last_known_id = actual
                self.emit({"event": "id", "id": actual})
                raise ModbusError(
                    f"新 ID {new_id} 写入后持续无响应，但探测到探头当前在 ID {actual}。请确认后再操作。")
            raise last_error or ModbusError("新 ID 验证读取失败")

        self.log(f"修改后读数（ID {new_id}）：湿度 {after[0]:.1f} %RH，温度 {after[1]:.1f} ℃")
        if abs(after[0] - before[0]) > 5.0 or abs(after[1] - before[1]) > 2.0:
            raise ModbusError("新 ID 读数与修改前差异过大，请人工确认是否为同一根探头")

        old_alive = False
        try:
            client.read_device_id(old_id)
            old_alive = True
        except (ModbusTimeout, ModbusError, serial.SerialException):
            pass
        if old_alive:
            self.log(f"警告：旧 ID {old_id} 仍有响应，总线上可能还有同 ID 设备", "warn")

        self._current_id = new_id
        self._last_known_id = new_id
        self.emit({"event": "id", "id": new_id})
        self.log(f"ID 修改完成：{old_id} → {new_id}（验证通过）")
        return {"old_id": old_id, "new_id": new_id,
                "before": {"humidity": before[0], "temperature": before[1]},
                "after": {"humidity": after[0], "temperature": after[1]},
                "old_id_still_alive": old_alive}

    # ---- 轮询 ----

    def _worker_loop(self):
        client = self._client
        slave = self._current_id  # 改 ID 后的重启轮询先用新 ID
        while not self._stop.is_set() and client is self._client:
            if slave is None:
                slave = self._detect_current_id(client, self._stop)
                if self._stop.is_set():
                    return
                if slave is None:
                    self.emit({"event": "error", "stage": "detect",
                               "message": "未找到探头：请检查供电/接线/波特率（已扫描 ID 1~247）"})
                    self.log("错误：未找到探头（ID 1~247 均无响应）", "error")
                    return
                self._current_id = slave
                self._last_known_id = slave
                self.emit({"event": "id", "id": slave})
                self.log(f"检测到探头，当前设备 ID = {slave}")
            try:
                humidity, temperature = client.read_measurements(slave)
                if self._stop.is_set():
                    return
                self.emit({"event": "reading", "id": slave,
                           "humidity": humidity, "temperature": temperature})
            except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
                if self._stop.is_set():
                    return
                self.emit({"event": "error", "stage": "poll", "message": f"通信中断：{exc}"})
                self.log(f"通信中断：{exc}", "error")
                return
            self._stop.wait(1.0)

    def _detect_current_id(self, client: ProbeClient, stop_event=None):
        # 先试上次已知 ID：改完 ID 重连时秒级识别，不必从 1 开始全扫
        last = self._last_known_id
        if stop_event is not None and stop_event.is_set():
            return None
        if last is not None:
            try:
                client.read_device_id(last)
                return last
            except (ModbusTimeout, ModbusError, serial.SerialException):
                pass
        for candidate in range(1, 248):
            if stop_event is not None and stop_event.is_set():
                return None
            try:
                client.read_device_id(candidate)
                return candidate
            except (ModbusTimeout, ModbusError, serial.SerialException):
                continue
        return None

    def _teardown(self):
        self._stop.set()
        if self._worker is not None:
            self._worker.join()
        self._worker = None
        if self._client is not None:
            self._client.close()
        self._client = None
        self._current_id = None


def main():
    bridge = Bridge()
    bridge.log("串口桥已启动")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            bridge.emit({"id": None, "ok": False, "error": "JSON 解析失败"})
            continue
        if req.get("cmd") == "exit":
            bridge._teardown()
            break
        response = bridge.handle(req)
        bridge.emit(response)


if __name__ == "__main__":
    main()
