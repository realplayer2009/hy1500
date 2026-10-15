# 交付物

| 文件 | 说明 |
|---|---|
| `485探头工具台.app` | 新版打包应用（Electron 28 + React 18 + Python 串口桥），macOS arm64 |
| `485探头工具台-1.0.0-arm64.dmg` | 安装包（92MB） |

> 这两个二进制**不在 git 里**：`.app` 内的 Electron 框架单文件 143MB，
> 超过 GitHub 100MB 硬限制；DMG 可由源码一键重建，没必要进版本库。

## 重新构建

```bash
cd electron
pnpm install     # 首次
pnpm dist        # 产出 release/mac-arm64/485探头工具台.app 和 release/*.dmg
```

构建要求：Node 22+、macOS arm64。electron-builder 的 Electron 下载走
npmmirror 镜像（`package.json` 的 `build.electronDownload.mirror`），
GitHub 下载源不可达时的替代方案。

## 运行

直接双击 `.app`，或：

```bash
open deliverables/485探头工具台.app
```

探头用 USB-RS485 转换器（CH340）连接，工具启动后自动发现 `/dev/cu.usbserial-*`
端口；识别探头 ID 会自动扫描 1~247（带上次已知 ID 快速路径）。
