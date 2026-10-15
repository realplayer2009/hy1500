# 脚本工程取舍

> 后续修改本组件的 agents 请继续维护本文档：有实际参数或工程权衡时记录，没有则不强行添加。记录格式为“问题 + 解决方案选择 + 解释”。

- 问题：开机动画描述将帧数写到段类型位置，ZIP 默认压缩；目标 Android 13 播放器要求合法的 `p/c` 段和未压缩帧，原脚本产物不能可靠播放。
- 解决方案选择：使用 `c 1 0 part0` 完整播放一次宣传视频，随后用 `p 0 0 part1` 循环最后一帧等系统启动完成；ZIP 使用 store 模式（`zip -0`）。
- 解释：`c` 段即使系统提前启动完成也会播完，因此最快启动时需要等待宣传视频结束；最后一帧段可在系统完成时立即退出，避免慢启动期间黑屏或反复重播视频。PNG 自身已经压缩，ZIP store 满足播放器直接映射读取帧的要求。

- 问题：现场多根温湿度探头出厂 ID 都是 1，需要逐根改成 2/3/4；用命令行写寄存器容易误操作（改错设备、写后不验证），现场人员也不方便；脚本版还要求仓库环境和 Python 依赖，不能单独分发。
- 解决方案选择：用 PyInstaller 打成独立 macOS 应用（`--windowed --onedir`，约 10 MB，捆绑 Python 3.9 + pyserial + tkinter），交付到桌面 `探头ID配置工具.app`，双击即用、可随意搬移；仓库内不再保留脚本，源码备份在仓库外 `~/probe_id_config_source/probe_id_config.py` 供重新打包。功能上连接后自动探测当前 ID（按 1~10 顺序试读 `0x0100`，现场默认 ID 1、探测成本低），实时显示湿度/温度；写入走 `0x06` 写 `0x0100`，完成后强制验证三项：旧 ID 停止响应、新 ID 正常响应、读数与修改前一致（湿度差 >5 %RH 或温度差 >2 ℃ 判失败），旧 ID 仍有响应时警告总线上可能接了第二根探头。写操作前弹确认框提示“总线上只接一根”。
- 解释：该探头的配置寄存器是 `0x0100`（不是同类探头常见的 `0x07D0`，见 `docs/温湿度探头地址切换/湿度探头_Modbus_ID配置记录.md`），且 `0x06` 的回显不能证明配置生效，必须以新旧 ID 的响应变化为准；把“同一根探头”的判定交给读数比对，避免总线上多根同 ID 设备时改错对象。打包验证方式：直接运行 `Contents/MacOS/` 内二进制抓启动错误，另打一个启动即自动连接的测试版用 `lsof` 确认冻结后的程序能真实打开 `/dev/cu.usbserial-*`。注意 macOS 系统 Python 3.9 需要 `from __future__ import annotations` 才支持 `X | None` 标注；`screencapture` 在无屏幕录制权限的 shell 里不可用，GUI 验证要靠无头驱动逻辑或 `lsof`。

- 问题：单功能 ID 配置工具在现场不够用——改 ID 之外还要看实时曲线、读/写任意寄存器、按 SSCOM 习惯抓帧排查总线，且用户反馈旧版“是个空架子、功能用不了、界面太朴素”。
- 解决方案选择：重写为四页签综合工具 `485探头工具台`（ID 配置 / 实时监视 5 分钟趋势曲线 / 寄存器读写含快捷读取与 0x06 写入 / SSCOM 式串口调试 HEX 收发自动 CRC），深色主题用手写 ttk Style（不引 sv-ttk/customtkinter，避免 PyInstaller 数据文件打包风险），仍为 `--windowed --onedir` 独立交付；端口发现不用 `serial.tools.list_ports`（其 macOS 实现经 ctypes 加载 IOKit，与本机 Tk 组合下冻结应用窗口不映射），改用 `/dev/cu.usbserial-*` 等 glob，串口本身仍用 pyserial。改 ID 流程保留“先停轮询线程再写、写后重试 5×0.4s 验证、旧 ID 复核、读数比对”的加固逻辑，ID 探测范围从 1~10 放宽到 1~50（现场改过多根后不再是 1）。
- 解释：把配置、监视、读写、调试合到一个独立应用，现场一个人一根探头即可完成全部操作，不必在多个工具间切换；深色主题+大数字+曲线让无人值守监视时可读。**验证方法论教训**：用 `CGWindowListCopyWindowInfo(OnScreenOnly)` 判断“窗口是否创建”不可靠——agent 的 bash 会话经 `open`/LaunchServices 启动的 GUI 应用会落到其他 Space，窗口实际已健康创建（`CGWindowListCopyWindowInfo(全部)` + 解析 `kCGWindowBounds` 可见 960×712、坐标正常），会误判成“窗口未显示”并追错方向（本次曾误疑 list_ports/ctypes）；GUI 创建验证必须查全部窗口并解析边界。另：当天下午起探头在任何波特率/ID/RTS 组合下均无响应（串口可开、无回显），判定为物理层故障（供电或 A/B 接线），与软件无关，已在交付说明中要求用户先排查接线；软件逻辑用 PTY 模拟探头（含“改 ID 后首读超时”怪癖）做无头回归，连接/探测/改 ID/恢复/寄存器/调试全链路通过。

- 问题：tkinter 版探头工具被评价"空架子"（启动/连接/改 ID 有问题、界面朴素），用户要求按 FusionB 项目技术栈重建。解决方案选择：Electron 28 + React 18 + Vite + TypeScript 外壳 + Python 串口桥子进程（stdio JSON 行协议），设计语言完整照搬 FusionB 的 index.css token（#1a1a1c 根背景/#0a84ff 强调色/SF Mono 等）。解释：串口层复用现场实测过的 pyserial Modbus 实现（ProbeClient/crc16/改 ID 重试与验证逻辑原样保留），避免 serialport npm 原生模块按 Electron ABI 重编译的风险；界面四页签（ID 配置/实时监视曲线/寄存器读写/串口调试）合并为单一综合工具。桥与界面通过 list_ports/connect/change_id/read_registers/write_register/send_raw 命令和 log/id/reading/error 事件解耦，PTY 模拟器（probe_sim.py）可无头回归全链路。

- 问题：Electron 启动报 `Cannot read properties of undefined (reading 'whenReady')`，main.js 里 require('electron') 返回的是二进制路径字符串。解决方案选择：确认本会话 bash 环境设有 `ELECTRON_RUN_AS_NODE=1`（Electron 退化成纯 Node 运行主脚本），启动时用 `env -u ELECTRON_RUN_AS_NODE` 剥掉该变量，package.json 的 dev 脚本同样处理。解释：该变量是 harness 会话环境产物，不是代码缺陷；不剥掉时 Electron 不起 GUI、不注入 app 模块，误判方向会指向构建配置或版本兼容（实际 Electron 28.3.3 在 macOS 26.6.2 上工作正常）。

- 问题：CDP 驱动 E2E 时偶发"应用自己连接了真实端口""快捷帧点击无效"。解决方案选择：猴子补丁 window.bridge.send 记录全部命令实证——无自动连接、端口值不被覆盖；两处异常均为测试脚本自身问题（heredoc 变量展开、点击了写死的"ID 1"快捷帧标签）。顺带修复真实 UX 缺陷：串口调试页快捷帧与默认输入框改为跟随当前探头 ID 动态生成（改完 ID 后依然可用），保留一条"ID 1 排障"帧。解释：先用 Instrumentation 区分"应用 bug"与"测试脚本 bug"，避免按假象改产品代码；动态快捷帧源自真实使用路径（逐根改 ID 时默认帧必须指向新 ID）。

- 问题：stdio JSON 行协议里桥推的事件对象也带 `id` 字段（值为探头设备 ID 1~247），与主进程"请求-响应"匹配用的 `id` 同名；数值相等时事件被当成响应吃掉。症状极具误导性——桥日志显示"检测到探头，当前设备 ID = 1"、读数事件每秒正常到达，但状态 pill 永远卡在"已连接，正在识别探头…"，ID 卡片显示"—"。曾误判为 React 状态更新丢失、asar 未打包修复、旧实例残留等多方向，实证手段是订阅全部事件只收到 reading、对比同批日志事件能到达。解决方案选择：主进程匹配器改为 `!('event' in obj) && typeof obj.id === 'number' && pending.has(obj.id)`，响应永远不含 event 字段、事件永远含，两类对象结构上互斥。解释：协议里"事件"与"响应"共用一个字段名是设计缺陷，靠数值范围（请求 id 自增、探头 id 1~247）避开碰撞不可靠——探头 id 242 与第 242 个请求必然相撞；用结构差异（有无 event 字段）判别才与取值无关。

- 问题：改完 ID 断开重连后，识别要等约 19 秒才出结果（探头在 ID 42，检测从 1 顺序扫到 50，每个 0.4 秒超时）。测试脚本只等 4.5 秒，误报"状态不更新"，一度怀疑修复未生效。解决方案选择：Bridge 增加 `_last_known_id`（跨连接记忆，三处赋值：检测完成、改 ID 验证后、worker 识别后同步），`_detect_current_id` 先试该 ID 再全扫；`_teardown` 只清 `_current_id` 不清 `_last_known_id`。实测重连识别从 19.4 秒降到 0.0 秒。解释：逐根改 ID 是核心工作流（改完→重连→验证），全扫让每次重连都付出与 ID 成正比的等待；记忆值只在桥进程存活期内有效，重启后回退全扫，不引入持久化状态。

- 问题：electron-builder 的 `files` 配 `dist/**/*`，而 `directories.output` 默认也是 `dist/`，产物（.app/.dmg）被当作输入又打进 asar，191MB 包里套包；同时误用 `asar extract-file ... > file` 验证 asar 内容得到空输出，差点误判"修复没进包"。解决方案选择：`build.directories.output` 设为 `release/`（dist/ 只放 Vite 渲染层产物）；验证 asar 内容用 `grep -c <特征串> app.asar`（asar 是原样拼接，二进制 grep 可靠），不要用 extract-file 的重定向。解释：构建工具的输出目录与输入 glob 重叠是隐蔽的递归打包陷阱，体积翻倍只是表象，还会让 asar 内含 LICENSE/mac-arm64 等无关文件；产物目录必须与源目录分离。
