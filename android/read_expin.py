import serial
import struct
import time

PORT = "/dev/ttyS4"
BAUDRATE = 19200


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def read_regs(port, slave, start, count):
    req = struct.pack(">BBBBH", slave, 0x03, start >> 8, start & 0xFF, count)
    port.write(req + struct.pack("<H", crc16(req)))
    time.sleep(0.03)
    raw = port.read(256)
    if not raw:
        raise TimeoutError("no response")
    if raw[1] & 0x80:
        return f"exception {raw[2]}"
    byte_count = raw[2]
    return [int.from_bytes(raw[3 + i:5 + i], "big") for i in range(0, byte_count, 2)]


def main():
    port = serial.Serial(port=PORT, baudrate=BAUDRATE,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         timeout=0.5)
    try:
        port.reset_input_buffer()
        for slave in range(1, 8):
            try:
                vals = read_regs(port, slave, 0x000E, 1)
                print(f"slave {slave}: 0x000E={vals[0]:04x}")
            except Exception as e:
                print(f"slave {slave}: {type(e).__name__}: {e}")
    finally:
        port.close()


if __name__ == "__main__":
    main()
