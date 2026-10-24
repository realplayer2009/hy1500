# 485 探头工具台（Electron 版）

温湿度探头的综合工具：**ID 配置 + 实时监视 + 寄存器读写 + 串口调试**四合一。
技术栈对齐 FusionB 项目：Electron 28 + React 18 + Vite + TypeScript + Python 后端子进程。

## 架构

```
electron/            Electron 外壳（主进程 + 渲染进程）
  main.ts            窗口、拉起 Python 桥、IPC 中转
  preload.ts         contextBridge 暴露 serial API（contextIsolation）
  src/               React 界面（FusionB 深色设计语言）
    App.tsx          外壳：连接栏 + 页签 + 全局状态
    panels/          IdPanel / MonitorPanel / RegisterPanel / DebugPanel
backend/
  serial_bridge.py   串口桥：stdio JSON 行协议，复用现场验证过的 Modbus 实现
```

**为什么 Python 桥而不是 serialport npm**：pyserial 已在本机验证可用；
serialport 是原生模块，需按 Electron ABI 重编译，风险高。与 FusionB
"Python 干脏活 + Electron 干界面"的模式一致。

## 串口桥协议（stdio，每行一个 JSON）

- 请求：`{"id": 1, "cmd": "connect", "port": "...", "baud": 9600}`
- 响应：`{"id": 1, "ok": true, ...}` / `{"id": 1, "ok": false, "error": "..."}`
- 事件（无 id，主动推送）：`{"event": "log"|"id"|"reading"|"error", ...}`

命令：`list_ports` / `connect` / `disconnect` / `change_id` /
`read_registers` / `write_register` / `send_raw` / `exit`

## 探头寄存器（现场实测）

| 地址 | 含义 | 备注 |
|------|------|------|
| 0x0000 | 湿度 | ÷10，%RH |
| 0x0001 | 温度 | ÷10，有符号，℃ |
| 0x0100 | 设备 ID | 1~247 |
| 0x0101 | 波特率代码 | 4 = 9600 |

- 只支持 FC 0x06 写单寄存器（0x10 对探头无效）
- 改 ID 后第一次读新 ID 会超时，需重试（桥内自动 5×0.4s）
- 0x06 回显不能证明生效，必须验证：旧 ID 停止响应 + 新 ID 正常 + 读数不变

## 开发

```bash
cd electron
npm install
npm run dev        # Vite dev server + Electron（PROBE_DEV=1）
npm run build      # tsc + vite build
npm run dist       # electron-builder 打 dmg
```

## 已知坑

- **本会话环境有 `ELECTRON_RUN_AS_NODE=1`**，会让 Electron 退化成纯 Node
  （`require('electron')` 返回路径字符串，`app` 为 undefined）。启动需
  `env -u ELECTRON_RUN_AS_NODE`。
- **事件与响应的 `id` 字段冲突**：桥推的事件也带 `id`（探头设备 ID 1~247），
  与请求-响应协议的 `id` 同名，数值相等时事件会被主进程匹配器当成响应吃掉
  （症状：识别成功但状态 pill 卡在"正在识别探头"）。主进程匹配器必须排除
  含 `event` 字段的对象。
- **"0 字节"不等于硬件坏**：Modbus 从机只应答自己的地址，探头若被改到
  其他 ID（实测被旧版改到过 3），只查 ID 1 会全程静默。识别必须扫全范围
  1~247（桥已实现，带 last_known_id 快速路径）。另：CH340 转换器可能反复
  掉线（`Device not configured` / `readiness to read but returned no data`），
  掉线期间所有查询必然失败，需先排除转换器稳定性再判断探头。
- **改完 ID 后重连识别慢**：检测从 ID 1 顺序扫到 50，探头在 ID 42 时要
  ~19 秒才识别。桥内记忆 `_last_known_id`，重连时优先探测该 ID（0 秒识别）。
- **electron-builder 会递归打包自己的输出目录**：`files` 含 `dist/**/*`
  而输出目录也是 `dist/mac-arm64` 时，产物会把 .app/.dmg 又塞进 asar
  （191MB → 97MB 的差距）。`directories.output` 必须设在 `dist/` 之外。
- macOS 多 Space：从终端启动的 GUI 应用窗口可能落在其他 Space，
  验证窗口要用 `CGWindowListCopyWindowInfo(0)`（全部窗口），
  OnScreenOnly 会假阴性。窗口在不可见 Space 时 Chromium 停止渲染新帧，
  截图会拿到旧帧（DOM 已是新状态），颜色/布局类断言要用 CDP 读
  `getComputedStyle`，不要只信截图。
- 端口发现用 glob `/dev/cu.usbserial-*` 等，不用 `serial.tools.list_ports`
  （打包后 ctypes 依赖不稳）。串口设备名随重插变化，工具必须自动发现。

## 无硬件回归测试

`tools/probe_sim.py` 用 PTY 模拟探头（含"改 ID 后
首读超时"怪癖），可无头验证全链路。改 ID 命令要等识别完成
（`currentId` 非 null）再发，否则桥会正确拒绝（`请先连接探头`）。
