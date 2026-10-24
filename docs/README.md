# docs 目录导航

按用途分目录，不再把所有文件平铺在 `docs/` 根下。

```
docs/
├── README.md            本文件
├── design/              工程设计文档（取舍、面板、部署、测试报告）
├── products/            面向客户/现场的产品资料（简介 + 使用说明书）
├── hardware/            硬件图纸与照片
├── labels/              标贴与合格证生成器及产物
├── manual/              《变压器加热系统-使用手册》构建管线
└── tools/               现场工具（温湿度探头地址切换）
```

## design/ — 工程设计文档

| 文件 | 内容 |
| --- | --- |
| [CONTROL_AND_SAFETY_DESIGN.md](design/CONTROL_AND_SAFETY_DESIGN.md) | 自检、温控、联锁与备用引脚设计 |
| [DATA_BROWSER_DESIGN.md](design/DATA_BROWSER_DESIGN.md) | 数据浏览交互与聚合规则 |
| [DEBUGGING_EXPERIENCE.md](design/DEBUGGING_EXPERIENCE.md) | 安卓端调试过程记录 |
| [DEVICE_PANEL_PA0715N.md](design/DEVICE_PANEL_PA0715N.md) | 现场屏 PA0715-N 硬件规格与程序相关要点 |
| [DEVICE_PANEL_ZYSJ.md](design/DEVICE_PANEL_ZYSJ.md) | 另一款现场屏的对应记录 |
| [HARMONY_SKIN_DEPLOYMENT.md](design/HARMONY_SKIN_DEPLOYMENT.md) | 鸿蒙主题部署 |
| [批量安装指南.md](design/批量安装指南.md) | APK 批量安装步骤 |
| [面板升级指南.md](design/面板升级指南.md) | 现场屏系统/程序升级步骤 |
| [软硬件结合测试报告.md](design/软硬件结合测试报告.md) | 软硬件联调测试结论 |

## products/ — 产品资料

| 文件 | 内容 |
| --- | --- |
| [客户使用说明书.md](products/客户使用说明书.md) / [.docx](products/客户使用说明书.docx) / [.pdf](products/客户使用说明书.pdf) | 现场操作图解：功能入口、手自动控制、联锁处理、接口设置、历史管理 |
| [产品简介.md](products/产品简介.md) / [.pdf](products/产品简介.pdf) | 盒内产品宣传册 |
| [客户使用说明书插图/](products/客户使用说明书插图) | 说明书引用的 18 张界面与接线插图 |

> 说明：说明书原先文件名带 ` (2)` 后缀（重复下载留下的），与根 `README.md`
> 及 `scripts/build_customer_manual.py` 引用的 `客户使用说明书.*` 不一致，
> 属于既有断链，本次已改回不带后缀的名字。

## hardware/ — 硬件图纸与照片

| 文件 | 内容 |
| --- | --- |
| [DXN-O高压电机启动接线图.png](hardware/DXN-O高压电机启动接线图.png) | 高压电机启动接线图 |
| [接线图.jpg](hardware/接线图.jpg) | 主板、探头、继电器与加热器接线 |
| [电路主板图.png](hardware/电路主板图.png) | 控制主板 |
| [微信图片_20261006121528_157_99.jpg](hardware/微信图片_20261006121528_157_99.jpg) | 微信转存的现场照片（原始文件名未改，内容待确认） |

## labels/ — 标贴与合格证

47×47 mm 方形标贴与合格证的生成器，A4 排版（控制器 20 张/页、加热器 60 张分 3 页）。

| 文件 | 作用 |
| --- | --- |
| [make_labels.py](labels/make_labels.py) | 主生成器：版式、文案、二维码、PDF 输出 |
| [qr.py](labels/qr.py) | 从零实现的二维码编码器/解码器（无第三方库可用） |
| [measure.py](labels/measure.py) | 版面尺寸测量脚本 |
| [verify.py](labels/verify.py) | 版面 QA + 二维码反解 + RS 纠错码自检 |
| [verify_pdf.py](labels/verify_pdf.py) | PDF 字节级校验 |
| [verify_roundtrip.py](labels/verify_roundtrip.py) | LibreOffice pdfium 渲染往返校验 |
| [out/](labels/out) | 5 个成品 PDF、序列号清单与预览图 |
| [标贴_裕泰通YTT-TC1500.png](labels/标贴_裕泰通YTT-TC1500.png) / [YTT-CR850A.png](labels/标贴_裕泰通YTT-CR850A.png) | 单张标贴参考图（1276×1276） |
| [合格证_四川裕泰通新能源科技有限公司.png](labels/合格证_四川裕泰通新能源科技有限公司.png) | 旧版合格证参考图 |

重新生成全部产物：

```bash
python3 docs/labels/make_labels.py
python3 docs/labels/verify.py
```

## manual/ — 使用手册构建管线

《变压器加热系统-使用手册.docx》的生成脚本与图片素材，`run_all.sh` 一键重制。
成品 docx 就在本目录，另拷贝一份到 `~/Documents/变压器加热系统-使用手册_v2.docx`。

## tools/ — 现场工具

[温湿度探头地址切换/](tools/温湿度探头地址切换) — 485 探头 Modbus ID 配置工具台
（Electron 版 + 旧版 tkinter + 配置记录）。

> 该目录下的 `electron/node_modules`、`electron/release`、`deliverables/*.dmg|*.app`
> 都是构建产物且已被 `.gitignore` 忽略，体积约 1.1 GB；清理后可用
> `npm install` 与 electron-builder 重新生成。

## 尚未入库的文档

以下路径在多处被引用，但仓库里**没有对应文件**（属既有情况，本次未凭空创建）：

- `docs/BUILD_LINUX.md` — 依赖安装、命令行编译、RK3568 部署（README 与 AGENTS.md 引用）
- `docs/ANDROID_DEPLOYMENT.md` — 安卓部署与串口权限（design/DEVICE_PANEL_PA0715N.md、design/批量安装指南.md、android/README.md、scripts/make_bootanimation.sh 引用）
- `docs/DEBUGGING_GUIDE.md` — 调试手册（.omo/plans/android-toolchain-setup.md 引用）
- `docs/products/产品简介截图/` — 产品简介的 4 张截图（products/产品简介.md 引用；PDF 版应已内嵌这些图）

