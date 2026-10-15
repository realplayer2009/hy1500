#!/usr/bin/env python3
"""485 探头工具台（macOS 独立应用，PyInstaller 打包）。

面向现场多根温湿度探头（出厂 ID 均为 1）的配置与调试：
  1. ID 配置   —— 连接后自动探测当前 ID，一键改写并强制验证
  2. 实时监视  —— 大数字 + 温湿度趋势曲线
  3. 寄存器读写—— 按文档寄存器表读取 / 写入任意保持寄存器
  4. 串口调试  —— SSCOM 式原始收发（HEX，自动 CRC），内置常用帧

寄存器约定（docs/温湿度探头地址切换/湿度探头_Modbus_ID配置记录.md）：
    0x0000 相对湿度（原始值 ÷ 10，%RH）
    0x0001 温度（有符号原始值 ÷ 10，℃）
    0x0100 设备 ID（1~247）
    0x0101 波特率代码（4 = 9600）

重要工程约束（实测结论，勿破坏）：
  * 禁止 `import serial.tools.list_ports`：它在 macOS 上经 ctypes 加载 IOKit，
    与本机 Python 3.9 + Tk 8.5 组合冲突，会导致 Tk 窗口静默不显示
    （进程正常运行、串口可开，但没有任何窗口）。端口发现一律用 glob。
  * 改 ID 后第一次读新 ID 可能超时（探头切换 ID 需要一点时间），
    验证读取必须重试；串口访问需要互斥锁避免轮询线程与主线程争抢。
"""

from __future__ import annotations

import glob
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import serial

# ---------------------------------------------------------------- 常量

APP_TITLE = "485 探头工具台"
WINDOW_SIZE = "960x680"

BAUDRATES = (9600, 19200, 38400, 57600, 115200, 4800, 2400)
DEFAULT_BAUD = 9600

REG_HUMIDITY = 0x0000
REG_TEMPERATURE = 0x0001
REG_DEVICE_ID = 0x0100
REG_BAUD_CODE = 0x0101

ID_MIN, ID_MAX = 1, 247
POLL_INTERVAL = 1.0          # 轮询读数间隔（秒）
MONITOR_WINDOW_SEC = 300     # 趋势曲线保留时长（秒）

# 深色主题配色
C_BG = "#1e1f24"             # 窗口/框架背景
C_PANEL = "#26272e"          # 面板背景
C_FIELD = "#31333c"          # 输入框背景
C_TEXT = "#e6e7eb"           # 主文字
C_TEXT_DIM = "#9aa0ad"       # 次要文字
C_ACCENT = "#3d8bfd"         # 强调色（按钮/选中）
C_OK = "#37b26f"             # 正常绿
C_WARN = "#e8a33d"           # 警告黄
C_ERR = "#e5534b"            # 错误红
C_GRID = "#3a3d46"           # 图表网格


# ---------------------------------------------------------------- Modbus 基础

def crc16(data: bytes) -> int:
    """Modbus CRC16（多项式 0xA001，初值 0xFFFF）。"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


class ModbusError(Exception):
    """设备返回异常响应或 CRC 校验失败。"""


class ModbusTimeout(Exception):
    """等待响应超时（总线上无该 ID 的设备）。"""


class ProbeClient:
    """最小 Modbus RTU 客户端：0x03 读 / 0x06 写 / 原始收发。

    串口访问经 _io_lock 互斥：轮询线程与界面操作共用同一串口，
    不互斥会导致请求/响应交错，表现为 CRC 错误或超时。
    """

    def __init__(self, port: str, baud: int, timeout: float = 0.4):
        self._ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            write_timeout=1.0,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._io_lock = threading.Lock()

    @property
    def port(self) -> str:
        return self._ser.port

    @property
    def baud(self) -> int:
        return self._ser.baudrate

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass

    # ---- 帧收发 ----

    def transact(self, pdu: bytes, expect_len: int) -> bytes:
        """发送 PDU（不含 CRC），读取并校验响应，返回响应帧（含 CRC）。"""
        with self._io_lock:
            frame = pdu + crc16(pdu).to_bytes(2, "little")
            self._ser.write(frame)
            self._ser.flush()
            response = self._ser.read(expect_len)
        if len(response) < 5:
            raise ModbusTimeout(f"等待响应超时（收到 {len(response)} 字节）")
        if crc16(response[:-2]) != int.from_bytes(response[-2:], "little"):
            raise ModbusError("响应 CRC 校验失败")
        if response[1] & 0x80:
            raise ModbusError(f"设备返回异常码 0x{response[2]:02X}")
        return response

    def send_raw(self, data: bytes) -> None:
        """串口调试用：原样发送（调用方自备 CRC）。"""
        with self._io_lock:
            self._ser.write(data)
            self._ser.flush()

    def read_available(self, wait: float = 0.25) -> bytes:
        """串口调试用：等待并读回当前可用字节。"""
        with self._io_lock:
            time.sleep(wait)
            return self._ser.read(self._ser.in_waiting or 1)

    # ---- 功能码 ----

    def read_holding(self, slave: int, start: int, count: int) -> list:
        """0x03 读保持寄存器，返回 int 列表。"""
        pdu = bytes([slave, 0x03]) + start.to_bytes(2, "big") + count.to_bytes(2, "big")
        response = self.transact(pdu, 5 + 2 * count)
        if response[2] != 2 * count:
            raise ModbusError(f"响应字节数不符：期望 {2 * count}，实际 {response[2]}")
        body = response[3 : 3 + 2 * count]
        return [int.from_bytes(body[i : i + 2], "big") for i in range(0, len(body), 2)]

    def write_register(self, slave: int, addr: int, value: int) -> None:
        """0x06 写单个保持寄存器。"""
        pdu = bytes([slave, 0x06]) + addr.to_bytes(2, "big") + value.to_bytes(2, "big")
        self.transact(pdu, 8)

    # ---- 业务封装 ----

    def read_measurements(self, slave: int) -> tuple:
        """返回 (湿度 %RH, 温度 ℃)。温度按有符号解析。"""
        humidity_raw, temperature_raw = self.read_holding(slave, REG_HUMIDITY, 2)
        if temperature_raw >= 0x8000:
            temperature_raw -= 0x10000
        return humidity_raw / 10.0, temperature_raw / 10.0

    def read_device_id(self, slave: int) -> int:
        return self.read_holding(slave, REG_DEVICE_ID, 1)[0]


def find_serial_ports() -> list:
    """发现可用 USB 串口。

    刻意不使用 pyserial 的 list_ports（其 macOS 实现经 ctypes 加载 IOKit，
    会与本机 Tk 冲突导致窗口不显示），改用 /dev glob。
    """
    patterns = (
        "/dev/cu.usbserial-*",
        "/dev/cu.wchusbserial-*",
        "/dev/cu.SLAB_USBtoUART*",
        "/dev/cu.usbmodem*",
    )
    ports: list = []
    for pattern in patterns:
        ports.extend(sorted(glob.glob(pattern)))
    return ports


def pick_default_port(ports: list) -> str | None:
    if not ports:
        return None
    for port in ports:
        if "usbserial" in port or "wchusbserial" in port:
            return port
    return ports[0]


# ---------------------------------------------------------------- 深色主题

def apply_dark_theme(root: tk.Tk) -> None:
    """手工深色 ttk 主题：不引第三方主题包，保证打包可靠性。"""
    style = ttk.Style(root)
    try:
        style.theme_create("probe_dark", parent="default", settings={
            ".": {
                "configure": {
                    "background": C_BG,
                    "foreground": C_TEXT,
                    "troughcolor": C_PANEL,
                    "focuscolor": C_PANEL,
                    "selectbackground": C_ACCENT,
                    "selectforeground": "#ffffff",
                    "bordercolor": C_GRID,
                    "insertbackground": C_TEXT,
                    "font": ("Helvetica", 12),
                }
            },
            "TFrame": {"configure": {"background": C_BG}},
            "TLabel": {"configure": {"background": C_BG, "foreground": C_TEXT}},
            "TLabelframe": {
                "configure": {"background": C_BG, "foreground": C_TEXT_DIM, "bordercolor": C_GRID}
            },
            "TLabelframe.Label": {
                "configure": {"background": C_BG, "foreground": C_TEXT_DIM}
            },
            "TButton": {
                "configure": {
                    "background": C_PANEL, "foreground": C_TEXT,
                    "bordercolor": C_GRID, "focuscolor": C_BG,
                },
                "map": {
                    "background": [("active", C_ACCENT), ("disabled", C_PANEL)],
                    "foreground": [("disabled", C_TEXT_DIM)],
                },
            },
            "Accent.TButton": {
                "configure": {"background": C_ACCENT, "foreground": "#ffffff"},
                "map": {"background": [("active", "#5b9dff"), ("disabled", C_PANEL)]},
            },
            "Danger.TButton": {
                "configure": {"background": C_ERR, "foreground": "#ffffff"},
                "map": {"background": [("active", "#ef7a72"), ("disabled", C_PANEL)]},
            },
            "TEntry": {
                "configure": {"fieldbackground": C_FIELD, "foreground": C_TEXT,
                              "bordercolor": C_GRID, "insertbackground": C_TEXT}
            },
            "TCombobox": {
                "configure": {"fieldbackground": C_FIELD, "foreground": C_TEXT,
                              "background": C_PANEL, "bordercolor": C_GRID,
                              "arrowcolor": C_TEXT},
                "map": {
                    "background": [("readonly", C_PANEL)],
                    "fieldbackground": [("readonly", C_FIELD)],
                    "foreground": [("readonly", C_TEXT)],
                },
            },
            "TNotebook": {"configure": {"background": C_BG, "bordercolor": C_GRID}},
            "TNotebook.Tab": {
                "configure": {"background": C_PANEL, "foreground": C_TEXT_DIM, "padding": [14, 6]},
                "map": {"background": [("selected", C_BG)], "foreground": [("selected", C_TEXT)]},
            },
            "Treeview": {
                "configure": {"background": C_FIELD, "foreground": C_TEXT,
                              "fieldbackground": C_FIELD, "bordercolor": C_GRID},
                "map": {"background": [("selected", C_ACCENT)]},
            },
            "Treeview.Heading": {
                "configure": {"background": C_PANEL, "foreground": C_TEXT, "bordercolor": C_GRID}
            },
            "TCheckbutton": {
                "configure": {"background": C_BG, "foreground": C_TEXT, "focuscolor": C_BG},
                "map": {"indicatorcolor": [("selected", C_ACCENT)]},
            },
            "TProgressbar": {"configure": {"background": C_ACCENT, "troughcolor": C_PANEL}},
        })
        style.theme_use("probe_dark")
    except tk.TclError:
        pass  # 主题创建失败则退回默认，不影响功能
    root.configure(bg=C_BG)


# ---------------------------------------------------------------- 主应用

class ProbeToolkitApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(APP_TITLE)
        root.geometry(WINDOW_SIZE)
        root.minsize(880, 640)

        self._client: ProbeClient | None = None
        self._current_id: int | None = None
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._queue: queue.Queue = queue.Queue()
        self._samples: list = []  # (时间戳, 湿度, 温度)

        self._build_ui()
        self.root.after(80, self._drain_queue)
        self.root.after(300, self._redraw_chart)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._raise_to_front()

    # ---- 窗口置前（打包版经 LaunchServices 启动时默认不激活）----

    def _raise_to_front(self) -> None:
        self.root.update_idletasks()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(400, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    # ---- 界面骨架 ----

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        header = ttk.Frame(self.root, padding=(12, 8))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Helvetica", 16, "bold")).pack(side="left")
        self.status_var = tk.StringVar(value="未连接")
        self.status_dot = tk.Label(
            header, textvariable=self.status_var, bg=C_PANEL, fg=C_TEXT_DIM,
            font=("Helvetica", 11), padx=12, pady=3,
        )
        self.status_dot.pack(side="right")

        conn_bar = ttk.LabelFrame(self.root, text="连接")
        conn_bar.pack(fill="x", **pad)
        ttk.Label(conn_bar, text="串口:").pack(side="left")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_bar, textvariable=self.port_var, width=24)
        self.port_combo.pack(side="left", **pad)
        ttk.Button(conn_bar, text="刷新", command=self._refresh_ports, width=6).pack(side="left")
        ttk.Label(conn_bar, text="波特率:").pack(side="left", padx=(16, 0))
        self.baud_var = tk.StringVar(value=str(DEFAULT_BAUD))
        ttk.Combobox(
            conn_bar, textvariable=self.baud_var, width=9, state="readonly",
            values=[str(b) for b in BAUDRATES],
        ).pack(side="left", **pad)
        self.connect_btn = ttk.Button(
            conn_bar, text="连接", command=self._on_connect, width=8, style="Accent.TButton"
        )
        self.connect_btn.pack(side="left", **pad)
        ttk.Button(conn_bar, text="断开", command=self._on_disconnect, width=8).pack(side="left")
        self._refresh_ports()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, **pad)
        self._build_id_tab(notebook)
        self._build_monitor_tab(notebook)
        self._build_register_tab(notebook)
        self._build_debug_tab(notebook)

        self._set_connected_ui(False)

    # ---- 标签页 1：ID 配置 ----

    def _build_id_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="  ID 配置  ")

        info = ttk.LabelFrame(tab, text="当前探头（总线上每次只接一根）")
        info.pack(fill="x")
        self.id_port_var = tk.StringVar(value="—")
        self.id_current_var = tk.StringVar(value="—")
        self.id_humidity_var = tk.StringVar(value="—")
        self.id_temperature_var = tk.StringVar(value="—")
        for row, (label, var) in enumerate((
            ("串口:", self.id_port_var),
            ("当前设备 ID:", self.id_current_var),
            ("湿度:", self.id_humidity_var),
            ("温度:", self.id_temperature_var),
        )):
            ttk.Label(info, text=label, width=12, anchor="e").grid(
                row=row, column=0, sticky="e", padx=8, pady=3
            )
            ttk.Label(info, textvariable=var, width=26, anchor="w").grid(
                row=row, column=1, sticky="w"
            )

        change = ttk.LabelFrame(tab, text="修改设备 ID")
        change.pack(fill="x", pady=(10, 0))
        ttk.Label(change, text=f"新 ID（{ID_MIN}~{ID_MAX}）:").pack(side="left", padx=8)
        self.new_id_var = tk.StringVar()
        entry = ttk.Entry(change, textvariable=self.new_id_var, width=8)
        entry.pack(side="left")
        entry.bind("<Return>", lambda _e: self._on_change_id())
        ttk.Button(
            change, text="写入并验证", command=self._on_change_id, width=12, style="Accent.TButton"
        ).pack(side="left", padx=10)
        ttk.Label(
            change, text="写入后自动验证：旧 ID 不再响应、新 ID 正常且读数不变",
            foreground=C_TEXT_DIM,
        ).pack(side="left")

        log_frame = ttk.LabelFrame(tab, text="操作日志")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.log_text = tk.Text(
            log_frame, height=8, state="disabled", bg=C_FIELD, fg=C_TEXT,
            insertbackground=C_TEXT, font=("Menlo", 11), relief="flat",
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

    # ---- 标签页 2：实时监视 ----

    def _build_monitor_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="  实时监视  ")

        big = ttk.Frame(tab)
        big.pack(fill="x")
        self.mon_humidity_var = tk.StringVar(value="--.-")
        self.mon_temperature_var = tk.StringVar(value="--.-")
        for column, (name, var, unit) in enumerate((
            ("湿度", self.mon_humidity_var, "%RH"),
            ("温度", self.mon_temperature_var, "℃"),
        )):
            card = ttk.LabelFrame(big, text=name)
            card.grid(row=0, column=column, sticky="nsew", padx=6)
            big.columnconfigure(column, weight=1)
            tk.Label(
                card, textvariable=var, bg=C_PANEL, fg=C_TEXT,
                font=("Helvetica", 40, "bold"),
            ).pack(padx=24, pady=(10, 0))
            tk.Label(card, text=unit, bg=C_PANEL, fg=C_TEXT_DIM, font=("Helvetica", 12)).pack(
                padx=24, pady=(0, 10)
            )
        ttk.Label(
            big, textvariable=self.id_current_var, foreground=C_TEXT_DIM
        ).grid(row=0, column=2, padx=16, sticky="s")

        chart_frame = ttk.LabelFrame(
            tab, text=f"趋势（最近 {MONITOR_WINDOW_SEC // 60} 分钟，绿=湿度 橙=温度）"
        )
        chart_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.chart = tk.Canvas(chart_frame, bg=C_PANEL, highlightthickness=0)
        self.chart.pack(fill="both", expand=True, padx=4, pady=4)
        self.chart.bind("<Configure>", lambda _e: self._redraw_chart())

    # ---- 标签页 3：寄存器读写 ----

    def _build_register_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="  寄存器读写  ")

        quick = ttk.LabelFrame(tab, text="快捷读取（按文档寄存器表）")
        quick.pack(fill="x")
        ttk.Button(quick, text="读温湿度 0x0000×2",
                   command=lambda: self._quick_read(0x0000, 2)).pack(side="left", padx=6, pady=6)
        ttk.Button(quick, text="读 ID/波特率代码 0x0100×2",
                   command=lambda: self._quick_read(0x0100, 2)).pack(side="left", padx=6, pady=6)
        ttk.Label(quick, text="文档寄存器：0x0000 湿度÷10 / 0x0001 温度÷10 / 0x0100 设备ID / 0x0101 波特率代码",
                  foreground=C_TEXT_DIM).pack(side="left", padx=10)

        read_bar = ttk.LabelFrame(tab, text="读取保持寄存器（0x03）")
        read_bar.pack(fill="x", pady=(10, 0))
        ttk.Label(read_bar, text="起始地址:").pack(side="left", padx=8)
        self.read_addr_var = tk.StringVar(value="0x0000")
        ttk.Entry(read_bar, textvariable=self.read_addr_var, width=10).pack(side="left")
        ttk.Label(read_bar, text="数量:").pack(side="left", padx=(12, 0))
        self.read_count_var = tk.StringVar(value="4")
        ttk.Entry(read_bar, textvariable=self.read_count_var, width=6).pack(side="left")
        ttk.Button(read_bar, text="读取", command=self._on_read_registers, width=8,
                   style="Accent.TButton").pack(side="left", padx=10)

        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill="both", expand=True, pady=(8, 0))
        columns = ("address", "decimal", "hex")
        self.reg_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        for col, text, width in (
            ("address", "地址", 120), ("decimal", "十进制", 120), ("hex", "十六进制", 120)
        ):
            self.reg_tree.heading(col, text=text)
            self.reg_tree.column(col, width=width, anchor="center")
        self.reg_tree.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(tree_frame, command=self.reg_tree.yview).pack(side="right", fill="y")

        write_bar = ttk.LabelFrame(tab, text="写保持寄存器（0x06，仅用于探头配置寄存器）")
        write_bar.pack(fill="x", pady=(10, 0))
        ttk.Label(write_bar, text="地址:").pack(side="left", padx=8)
        self.write_addr_var = tk.StringVar(value="0x0100")
        ttk.Entry(write_bar, textvariable=self.write_addr_var, width=10).pack(side="left")
        ttk.Label(write_bar, text="值:").pack(side="left", padx=(12, 0))
        self.write_value_var = tk.StringVar()
        ttk.Entry(write_bar, textvariable=self.write_value_var, width=10).pack(side="left")
        ttk.Button(write_bar, text="写入", command=self._on_write_register, width=8,
                   style="Danger.TButton").pack(side="left", padx=10)
        ttk.Label(write_bar, text="误写可能改变探头通信参数；改 ID 请用「ID 配置」页（带验证）",
                  foreground=C_TEXT_DIM).pack(side="left", padx=6)

    # ---- 标签页 4：串口调试 ----

    def _build_debug_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="  串口调试  ")

        quick = ttk.LabelFrame(tab, text="快捷帧")
        quick.pack(fill="x")
        ttk.Button(quick, text="读温湿度(ID1)",
                   command=lambda: self._send_frame("01 03 00 00 00 02")).pack(side="left", padx=6, pady=6)
        ttk.Button(quick, text="读ID寄存器(ID1)",
                   command=lambda: self._send_frame("01 03 01 00 00 01")).pack(side="left", padx=6, pady=6)
        ttk.Button(quick, text="读ID寄存器(ID3)",
                   command=lambda: self._send_frame("03 03 01 00 00 01")).pack(side="left", padx=6, pady=6)

        send_bar = ttk.LabelFrame(tab, text="发送（HEX，空格分隔；默认自动追加 CRC）")
        send_bar.pack(fill="x", pady=(10, 0))
        self.tx_var = tk.StringVar(value="01 03 00 00 00 02")
        entry = ttk.Entry(send_bar, textvariable=self.tx_var)
        entry.pack(side="left", fill="x", expand=True, padx=8)
        entry.bind("<Return>", lambda _e: self._on_send())
        self.append_crc_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(send_bar, text="自动CRC", variable=self.append_crc_var).pack(side="left", padx=6)
        ttk.Button(send_bar, text="发送", command=self._on_send, width=8,
                   style="Accent.TButton").pack(side="left", padx=6)

        log_frame = ttk.LabelFrame(tab, text="收发记录")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.rx_text = tk.Text(
            log_frame, state="disabled", bg=C_FIELD, fg=C_TEXT,
            insertbackground=C_TEXT, font=("Menlo", 11), relief="flat",
        )
        scroll = ttk.Scrollbar(log_frame, command=self.rx_text.yview)
        self.rx_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.rx_text.pack(fill="both", expand=True)
        self.rx_text.tag_configure("tx", foreground=C_ACCENT)
        self.rx_text.tag_configure("rx", foreground=C_OK)
        self.rx_text.tag_configure("err", foreground=C_ERR)

    # ---- 连接管理 ----

    def _refresh_ports(self) -> None:
        ports = find_serial_ports()
        self.port_combo.configure(values=ports)
        default = pick_default_port(ports)
        if default:
            self.port_var.set(default)
        elif not self.port_var.get():
            self.port_var.set("未发现串口")
        if not ports:
            self._log("未发现 USB 串口，请检查 USB-RS485 转换器", "err")

    def _set_connected_ui(self, connected: bool) -> None:
        self.connect_btn.state(["disabled"] if connected else ["!disabled"])

    def _on_connect(self) -> None:
        port = self.port_var.get()
        if not port or not port.startswith("/dev/"):
            messagebox.showerror("连接失败", "请先选择有效的串口设备（如 /dev/cu.usbserial-110）")
            return
        try:
            baud = int(self.baud_var.get())
            client = ProbeClient(port, baud)
        except (serial.SerialException, ValueError) as exc:
            messagebox.showerror(
                "连接失败",
                f"无法打开 {port}：{exc}\n\n请检查：\n"
                "1. 转换器是否插好\n2. 是否被其他程序占用（minicom/上位机）\n3. 拔插重试",
            )
            return

        self._client = client
        self._current_id = None
        self._samples.clear()
        self._stop_event.clear()
        self._set_status("已连接，正在读取设备 ID…", C_WARN)
        self._set_connected_ui(True)
        self._queue.put(("port", port))
        self._log(f"已连接 {port} @ {baud} 8N1")
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _on_disconnect(self) -> None:
        self._stop_event.set()
        if self._client is not None:
            self._client.close()
            self._client = None
        self._current_id = None
        self._set_connected_ui(False)
        self._set_status("未连接", C_TEXT_DIM)
        for var in (self.id_port_var, self.id_current_var, self.id_humidity_var,
                    self.id_temperature_var):
            var.set("—")
        self.mon_humidity_var.set("--.-")
        self.mon_temperature_var.set("--.-")
        self._samples.clear()
        self._redraw_chart()
        self._log("已断开连接")

    def _set_status(self, text: str, color: str) -> None:
        self._queue.put(("status", (text, color)))

    def _worker_loop(self) -> None:
        client = self._client
        # 改 ID 成功后 _current_id 已是新 ID，重启的轮询先用它，
        # 避免新 ID 超出探测范围被误判为“未找到探头”。
        slave = self._current_id
        first_cycle = True
        while not self._stop_event.is_set() and client is self._client:
            if slave is None:
                slave = self._detect_current_id(client)
                if slave is None:
                    self._set_status("未找到探头：请检查供电/接线/波特率", C_ERR)
                    self._log("错误：未找到探头（ID 1~50 均无响应）", "err")
                    return
                self._current_id = slave
                self._queue.put(("id", slave))
                self._set_status(f"已连接，当前 ID = {slave}", C_OK)
                self._log(f"检测到探头，当前设备 ID = {slave}")
            try:
                humidity, temperature = client.read_measurements(slave)
                self._queue.put(("reading", (humidity, temperature)))
                if first_cycle:
                    self._set_status(f"正常通信中，ID = {slave}", C_OK)
                    first_cycle = False
            except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
                self._set_status(f"通信中断：{exc}", C_ERR)
                self._log(f"通信中断：{exc}", "err")
                return
            self._stop_event.wait(POLL_INTERVAL)

    def _detect_current_id(self, client: ProbeClient) -> int | None:
        """探测当前设备 ID：先试 1（出厂默认），再试 2~50。"""
        for candidate in range(1, 51):
            try:
                client.read_device_id(candidate)
                return candidate
            except (ModbusTimeout, ModbusError, serial.SerialException):
                continue
        return None

    # ---- 改 ID ----

    def _on_change_id(self) -> None:
        if self._client is None or self._current_id is None:
            messagebox.showwarning("提示", "请先连接探头")
            return
        raw = self.new_id_var.get().strip()
        if not raw.isdigit() or not (ID_MIN <= int(raw) <= ID_MAX):
            messagebox.showerror("输入错误", f"新 ID 必须是 {ID_MIN}~{ID_MAX} 的整数")
            return
        new_id = int(raw)
        if new_id == self._current_id:
            messagebox.showinfo("无需修改", f"探头当前已经是 ID {new_id}")
            return
        if not messagebox.askyesno(
            "确认修改",
            f"将把探头 ID 从 {self._current_id} 修改为 {new_id}。\n\n"
            "请确认总线上只连接了这一根探头，否则可能误改其他设备。\n\n是否继续？",
        ):
            return

        client = self._client
        old_id = self._current_id
        # 先可靠停掉轮询线程，避免它和改 ID 的主线程抢串口
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=3.0)
        self._worker = None

        try:
            self._run_id_change(client, old_id, new_id)
        except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
            self._log(f"修改失败：{exc}", "err")
            messagebox.showerror("修改失败", f"{exc}\n\n请重新连接后重试。")
        finally:
            if self._client is not None and (
                self._worker is None or not self._worker.is_alive()
            ):
                self._stop_event.clear()
                self._worker = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker.start()

    def _run_id_change(self, client: ProbeClient, old_id: int, new_id: int) -> None:
        self._log(f"开始修改 ID：{old_id} → {new_id}")
        self._set_status(f"正在写入新 ID {new_id} …", C_WARN)

        before = client.read_measurements(old_id)
        self._log(f"修改前读数（ID {old_id}）：湿度 {before[0]:.1f} %RH，温度 {before[1]:.1f} ℃")

        client.write_register(old_id, REG_DEVICE_ID, new_id)
        self._log(f"已发送写寄存器命令：0x0100 = {new_id}")

        # 探头切换 ID 后可能需要一点时间才在新 ID 上应答，重试几次再判失败
        after = None
        last_error: Exception | None = None
        for attempt in range(5):
            time.sleep(0.4)
            try:
                after = client.read_measurements(new_id)
                break
            except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
                last_error = exc
                self._log(f"新 ID {new_id} 第 {attempt + 1} 次验证读取失败：{exc}")
        if after is None:
            actual = self._detect_current_id(client)
            if actual is not None and actual != old_id:
                self._current_id = actual
                self._queue.put(("id", actual))
                self._set_status(f"探头当前在 ID {actual}，请确认", C_WARN)
                raise ModbusError(
                    f"新 ID {new_id} 写入后持续无响应，但探测到探头当前在 ID {actual}。"
                    "请确认探头实际 ID 后再操作。"
                )
            raise last_error if last_error else ModbusError("新 ID 验证读取失败")

        self._log(f"修改后读数（ID {new_id}）：湿度 {after[0]:.1f} %RH，温度 {after[1]:.1f} ℃")
        if abs(after[0] - before[0]) > 5.0 or abs(after[1] - before[1]) > 2.0:
            raise ModbusError("新 ID 读数与修改前差异过大，请人工确认是否为同一根探头")

        try:
            client.read_device_id(old_id)
            self._log(f"警告：旧 ID {old_id} 仍有响应，总线上可能还有同 ID 设备", "err")
            messagebox.showwarning(
                "需要确认",
                f"新 ID {new_id} 已可正常通信，但旧 ID {old_id} 也仍有响应。\n"
                "总线上可能连接了第二根探头，请只留一根后重新验证。",
            )
        except ModbusTimeout:
            self._log(f"旧 ID {old_id} 已停止响应，验证通过")

        self._current_id = new_id
        self._queue.put(("id", new_id))
        self._set_status(f"修改成功，当前 ID = {new_id}", C_OK)
        self._log(f"ID 修改完成：{old_id} → {new_id}")
        messagebox.showinfo(
            "修改成功",
            f"探头 ID 已从 {old_id} 修改为 {new_id}，并验证通过。\n\n"
            f"后续读取帧：{new_id:02X} 03 00 00 00 02 …",
        )

    # ---- 寄存器读写 ----

    @staticmethod
    def _parse_int(text: str) -> int:
        text = text.strip()
        if not text:
            raise ValueError("请输入数值")
        return int(text, 16) if text.lower().startswith("0x") else int(text, 10)

    def _require_client(self) -> ProbeClient | None:
        if self._client is None or self._current_id is None:
            messagebox.showwarning("提示", "请先连接探头")
            return None
        return self._client

    def _quick_read(self, start: int, count: int) -> None:
        client = self._require_client()
        if client is None:
            return
        self.read_addr_var.set(f"0x{start:04X}")
        self.read_count_var.set(str(count))
        self._do_read(client, start, count)

    def _on_read_registers(self) -> None:
        client = self._require_client()
        if client is None:
            return
        try:
            start = self._parse_int(self.read_addr_var.get())
            count = self._parse_int(self.read_count_var.get())
        except ValueError as exc:
            messagebox.showerror("输入错误", f"地址/数量无效：{exc}")
            return
        if not (0 <= start <= 0xFFFF and 1 <= count <= 125):
            messagebox.showerror("输入错误", "地址 0~0xFFFF，数量 1~125")
            return
        self._do_read(client, start, count)

    def _do_read(self, client: ProbeClient, start: int, count: int) -> None:
        slave = self._current_id
        try:
            values = client.read_holding(slave, start, count)
        except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
            messagebox.showerror("读取失败", str(exc))
            return
        for item in self.reg_tree.get_children():
            self.reg_tree.delete(item)
        for offset, value in enumerate(values):
            self.reg_tree.insert(
                "", "end",
                values=(f"0x{start + offset:04X}", str(value), f"0x{value:04X}"),
            )
        self._log(f"读取 0x{start:04X}×{count}（ID {slave}）：" +
                  ", ".join(f"0x{v:04X}" for v in values))

    def _on_write_register(self) -> None:
        client = self._require_client()
        if client is None:
            return
        try:
            addr = self._parse_int(self.write_addr_var.get())
            value = self._parse_int(self.write_value_var.get())
        except ValueError as exc:
            messagebox.showerror("输入错误", f"地址/值无效：{exc}")
            return
        if not (0 <= addr <= 0xFFFF and 0 <= value <= 0xFFFF):
            messagebox.showerror("输入错误", "地址 0~0xFFFF，值 0~0xFFFF")
            return
        slave = self._current_id
        if not messagebox.askyesno(
            "确认写入",
            f"将向 ID {slave} 的寄存器 0x{addr:04X} 写入 {value}（0x{value:04X}）。\n\n"
            "误写可能改变探头通信参数（如 ID、波特率）。是否继续？",
        ):
            return
        try:
            client.write_register(slave, addr, value)
        except (ModbusTimeout, ModbusError, serial.SerialException) as exc:
            messagebox.showerror("写入失败", str(exc))
            return
        self._log(f"写入成功：ID {slave} 0x{addr:04X} = {value}（0x{value:04X}）")
        messagebox.showinfo("写入成功", f"已写入 0x{addr:04X} = {value}")

    # ---- 串口调试 ----

    def _send_frame(self, hex_text: str) -> None:
        self.tx_var.set(hex_text)
        self._on_send()

    def _on_send(self) -> None:
        client = self._require_client()
        if client is None:
            return
        text = self.tx_var.get().strip()
        try:
            payload = bytes.fromhex(text.replace(" ", ""))
        except ValueError:
            messagebox.showerror(
                "输入错误",
                "HEX 格式无效，请用空格分隔的两位十六进制，如：01 03 00 00 00 02",
            )
            return
        if not payload:
            messagebox.showerror("输入错误", "发送内容为空")
            return
        frame = payload
        if self.append_crc_var.get():
            frame = payload + crc16(payload).to_bytes(2, "little")
        try:
            client.send_raw(frame)
            response = client.read_available(0.3)
        except serial.SerialException as exc:
            self._rx_log(f"串口错误：{exc}", "err")
            return
        self._rx_log(f"TX → {frame.hex(' ').upper()}", "tx")
        if response:
            self._rx_log(f"RX ← {response.hex(' ').upper()}", "rx")
            if len(response) >= 3 and response[1] & 0x80:
                self._rx_log(f"设备返回异常码 0x{response[2]:02X}", "err")
        else:
            self._rx_log("RX ← （无响应，超时）", "err")

    def _rx_log(self, text: str, tag: str) -> None:
        self._queue.put(("rx", (text, tag)))

    # ---- 曲线 ----

    def _redraw_chart(self) -> None:
        chart = self.chart
        chart.delete("all")
        width = chart.winfo_width()
        height = chart.winfo_height()
        if width < 50 or height < 50:
            return
        padding_left, padding_bottom, padding_top = 46, 26, 12
        plot_w = width - padding_left - 12
        plot_h = height - padding_bottom - padding_top
        if plot_w <= 0 or plot_h <= 0:
            return

        now = time.time()
        window = MONITOR_WINDOW_SEC
        samples = [s for s in self._samples if now - s[0] <= window]
        if not samples:
            chart.create_text(
                width / 2, height / 2, text="连接后自动显示温湿度趋势",
                fill=C_TEXT_DIM, font=("Helvetica", 12),
            )
            return

        # 固定量纲：湿度 0~100 %RH，温度 0~50 ℃，曲线不随数据跳动
        def x_of(t):
            return padding_left + plot_w * (1 - (now - t) / window)

        def y_humidity(v):
            return padding_top + plot_h * (1 - min(max(v, 0), 100) / 100)

        def y_temperature(v):
            return padding_top + plot_h * (1 - min(max(v, 0), 50) / 50)

        for percent in (0, 25, 50, 75, 100):
            y = padding_top + plot_h * percent / 100
            chart.create_line(padding_left, y, padding_left + plot_w, y, fill=C_GRID)
        chart.create_text(padding_left - 30, padding_top + 4, text="100", fill=C_TEXT_DIM,
                          font=("Helvetica", 9), anchor="e")
        chart.create_text(padding_left - 30, padding_top + plot_h, text="0", fill=C_TEXT_DIM,
                          font=("Helvetica", 9), anchor="e")
        minutes = window // 60
        chart.create_text(padding_left, height - 8, text=f"-{minutes}分钟", fill=C_TEXT_DIM,
                          font=("Helvetica", 9))
        chart.create_text(padding_left + plot_w, height - 8, text="现在", fill=C_TEXT_DIM,
                          font=("Helvetica", 9), anchor="e")

        for series, y_of, color in (
            ([s[1] for s in samples], y_humidity, C_OK),
            ([s[2] for s in samples], y_temperature, C_WARN),
        ):
            points = [(x_of(samples[i][0]), y_of(series[i])) for i in range(len(samples))]
            if len(points) >= 2:
                chart.create_line(points, fill=color, width=2, smooth=True)

    # ---- 队列消费 ----

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "status":
                    text, color = payload
                    self.status_var.set(text)
                    self.status_dot.configure(fg=color)
                elif kind == "id":
                    self._current_id = payload
                    self.id_current_var.set(str(payload))
                elif kind == "port":
                    self.id_port_var.set(payload)
                elif kind == "reading":
                    humidity, temperature = payload
                    self.id_humidity_var.set(f"{humidity:.1f} %RH")
                    self.id_temperature_var.set(f"{temperature:.1f} ℃")
                    self.mon_humidity_var.set(f"{humidity:.1f}")
                    self.mon_temperature_var.set(f"{temperature:.1f}")
                    self._samples.append((time.time(), humidity, temperature))
                    if len(self._samples) > 3600:
                        self._samples.pop(0)
                elif kind == "rx":
                    text, tag = payload
                    timestamp = time.strftime("%H:%M:%S")
                    self.rx_text.configure(state="normal")
                    self.rx_text.insert("end", f"[{timestamp}] {text}\n", tag)
                    self.rx_text.see("end")
                    self.rx_text.configure(state="disabled")
                elif kind == "log":
                    self._append_log(payload[0], payload[1] if len(payload) > 1 else None)
        except queue.Empty:
            pass
        self.root.after(80, self._drain_queue)

    def _log(self, message: str, tag: str | None = None) -> None:
        self._queue.put(("log", (message, tag)))

    def _append_log(self, message: str, tag: str | None = None) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n", tag or "normal")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ---- 退出 ----

    def _on_close(self) -> None:
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=3.0)
        if self._client is not None:
            self._client.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    apply_dark_theme(root)
    ProbeToolkitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
