# RS485Control 环境控制上位机

溪洛渡工程现场的环境控制上位机：通过两条 RS485 总线（Modbus RTU，19200/N/8/1）
轮询最多 2×16 块子板，完成温湿度/PT100 数据采集、按子站独立的自动温控、
手动输出控制、高压安全联锁与 CSV 数据记录。目标平台为 RK3568（ARM64）触屏
一体机，开发调试环境为 Ubuntu x86 + Qt 5.15。

## 功能概览

- **子板总览**：全部已发现子板的状态卡片，强调显示每块子板的运行模式
  （● 自动温控 / ● 手动）；平均温度、平均湿度和 PT100 均温分栏显示，
  A/B/C 加热器档位及灯/报警状态对齐排列，离线读数显示占位符。单板卡片铺满宽度，
  多板两列浏览，点击进入控制页。
- **子板控制**：按子站独立启停自动温控；三个加热器 A/B/C 各有独立的目标温度，
   各自由两路继电器驱动（1档/2档/3档/关闭循环），屏幕按键与实体按键
   （外扩输入上升沿）同效。操作界面按实际用途显示加热回路、运行绿灯、手动黄灯、
   报警红灯、高压报警蜂鸣器、加热器工作灯及操作提示蜂鸣器，名称随映射变化。
   中间区域显示测量值、运行状态、状态灯、现场输入和只读扩展设备；右侧保留操作
   按钮、备用扩展输出和操作提示。状态灯、工作灯及提示/报警蜂鸣器均只读，
   不提供手动切换；扩展闪烁灯/扩展蜂鸣器
   尚未接入自动联动，仅显示回读状态。备用回路可配置联动，备用扩展输出保留手动控制。
- **三种温控模式**：阈值三档、PID 三档、防凝露（露点余量）三档，档位顺序、
   输出点与回差均可在参数页调整；目标温度可跟随子板内部 PT100 平均值或固定值，
   固定值时三个加热器各自独立设定目标。
- **安全联锁**：高压检测支持数字量（0x0001）与模拟量（0x0003，电压阈值）两种
  来源，触发后切断全部加热回路并声光报警；备用输入 0x0002 可配置联锁；
  温湿度自检只对固定极端量程（-40~85 ℃ / 0~100 %RH）报警，不阻塞控制。
- **数据记录与浏览**：轮询周期（默认 0.1 秒）与记录周期（默认 1 秒）独立可配，
  按记录周期写按日期分文件的 CSV；历史页支持日期/子板筛选、曲线与明细联动、
  秒级聚合与跨主题配色。
- **运维**：存储容量统计、按截止日期预览+二次确认清理、日志容量上限；
   屏幕亮度滑条与无人值守自动降亮（空闲降亮/熄屏，触摸恢复）；
   标准/低光/强光/石墨灰/鸿蒙五套现场主题，默认石墨灰深色，
   安全语义颜色不随主题变化。
- **页面结构**：域控子板总览 / 子板手动控制 / 加热参数设置 / 数据浏览 /
   高级设置 / 关于本机。高级设置按功能分为“接口配置”（外扩输入、加热器输出、
   备用接口）、“安全保护”（高压联锁、继电器保护）、“数据存储”（采集周期、
   存储容量与清理）、“显示与声音”（主题、亮度、自动降亮、提示音）。
   加热参数设置保留温控参数和计算说明。两类设置页有未保存修改时，切换导航页面
   会询问保存、不保存或取消；不保存撤销当前页临时修改并恢复亮度预览，
   高级设置分组切换不弹提示。主题选择即时保存。

## 目录结构

```
src/                      上位机源码 (C++11 / Qt Widgets)
  rs485device.*           串口与 Modbus RTU 协议层 (SerialPortWorker)
  applogic.*              DeviceManager / PollScheduler / DataLogger /
                          HistoryQuery / StorageRotator / AppConfig
  controlalgorithm.*      温控算法（阈值/PID/防凝露/露点计算/传感器自检）
  appui.*                 全部界面（总览、控制、参数、历史、主题）
  main.cpp                入口
tests/
  controlalgorithm_test.* 温控算法 QtTest 单元测试
  simulator/
    pty_modbus_sim.py     无硬件下位机模拟器（PTY 模拟两条 RS485 总线,
                          默认自动拉起上位机）
    test_pty_modbus_sim.py  模拟器协议与物理模型单元测试
docs/                     设计文档（见下）
config/app.ini            配置文件示例
rs485_modbus_debug.py     独立的 RS485/Modbus 调试脚本（用法见《使用说明.txt》）
RS485Control.pro          qmake 工程文件
上位机软件需求 20260827.md   需求文档
```

## 编译与运行

依赖（Ubuntu 22.04）：`build-essential qtbase5-dev libqt5serialport5-dev`
中文字体与 RK3568 交叉部署细节见 [docs/BUILD_LINUX.md](docs/BUILD_LINUX.md)。

```bash
qmake RS485Control.pro
make -j4
```

运行时从**当前工作目录**加载 `app.ini`（串口、轮询周期、数据路径等），
未配置时使用默认串口并在界面提示。子板不依赖配置文件，启动后自动扫描
Modbus ID 1~247。

## 无硬件联调（推荐）

模拟器用 Linux PTY 模拟两条 RS485 总线和物理温升模型，一条命令拉起
模拟器 + 上位机：

```bash
python3 tests/simulator/pty_modbus_sim.py
```

退出模拟器时自动关闭上位机。常用参数：`--no-launch-app` 只跑模拟器、
`--no-interactive` 自动化后台模式、`--cli` 命令行交互、
`--real /dev/ttyUSB0 /dev/ttyUSB1` 接真实串口。交互控制台支持增减子站、
高压注入、温度调整和 `normal/highvoltage/temperature/crowded` 一键场景。

外扩板联调：`z/x/c` 模拟加热器 A/B/C 实体按键，默认闭合 600 ms 后释放；
`F1~F5` 保持或释放对应 IN，`e` 切换备用输入。下方显示当前子站的接线映射、
三路加热器档位、IN1~IN5 和 OUT1~OUT7 回读（工作灯、备用输出、提示蜂鸣器、
扩展灯/蜂鸣器）。输入功能和加热器输出对随上位机“高级设置”保存自动更新，
温升模型只计算分配给三路加热器的回路。

命令行等效操作：`press 0:1 A`、`press 0:1 IN3 2000`、`set 0:1 in2 1`
（释放用 `set 0:1 in2 0`）。实体按键靠上位机检测上升沿，先等待初始读数，
保持闭合不会反复切档；多板或慢轮询时可延长脉冲，或保持闭合至界面读到后再释放。
手自动/高压闭锁输入映射当前仅监视，蜂鸣器与灯的联动由上位机驱动。
启动只扫描每口第一块子板，多板场景请在上位机点击“重新扫描子板”。

界面保存的模拟参数跨重启保留，新增配置项从项目 `config/app.ini` 补齐；
串口和数据目录仍由模拟器隔离设置。需要恢复项目配置时运行：

```bash
python3 tests/simulator/pty_modbus_sim.py --reset-config
```

## 测试

```bash
# 温控算法单元测试 (QtTest)
qmake -o Makefile.controlalgorithm_test tests/controlalgorithm_test.pro
make -f Makefile.controlalgorithm_test && ./controlalgorithm_test

# 模拟器协议与物理模型测试 (纯标准库)
python3 tests/simulator/test_pty_modbus_sim.py
```

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [docs/BUILD_LINUX.md](docs/BUILD_LINUX.md) | 依赖安装、命令行编译、RK3568 部署 |
| [docs/DEVICE_PANEL_PA0715N.md](docs/DEVICE_PANEL_PA0715N.md) | 现场屏（PA0715-N）硬件规格与程序相关要点 |
| [docs/CONTROL_AND_SAFETY_DESIGN.md](docs/CONTROL_AND_SAFETY_DESIGN.md) | 自检、温控、联锁与备用引脚设计 |
| [docs/DATA_BROWSER_DESIGN.md](docs/DATA_BROWSER_DESIGN.md) | 数据浏览交互与聚合规则 |
| [使用说明.txt](使用说明.txt) | `rs485_modbus_debug.py` 调试脚本用法 |
| [AGENTS.md](AGENTS.md) | 工程取舍与参数决策记录（面向后续维护） |

> 注意：高压模拟量阈值等安全参数默认值仅供开发，正式使用前需按现场
> 传感器标定。
