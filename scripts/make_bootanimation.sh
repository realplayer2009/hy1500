#!/usr/bin/env bash
# 从 MP4 视频制作 Android 系统开机动画 bootanimation.zip
# 用法: scripts/make_bootanimation.sh <视频.mp4> [输出目录]
# 默认输出 /tmp/bootanim/bootanimation.zip。Android 13 userdebug 设备部署前
# 使用 adb root、重新连接、adb remount（按输出要求重启），保留原厂动画备份。
# 具体推送与恢复命令见 docs/ANDROID_DEPLOYMENT.md。
set -euo pipefail

VIDEO="${1:?用法: $0 <视频.mp4> [输出目录]}"
OUT_DIR="${2:-/tmp/bootanim}"
WIDTH=1024      # rk3562_t 面板物理分辨率
HEIGHT=600
FPS=30

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/part0" "$OUT_DIR/part1"

ffmpeg -y -loglevel error -i "$VIDEO" \
    -vf "scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=decrease,pad=${WIDTH}:${HEIGHT}:(ow-iw)/2:(oh-ih)/2" \
    -r "$FPS" -pix_fmt rgb24 "$OUT_DIR/part0/frame_%04d.png"

frames=("$OUT_DIR"/part0/frame_*.png)
FRAMES=${#frames[@]}
cp "${frames[-1]}" "$OUT_DIR/part1/frame_0001.png"
# Complete the promo once, then hold its last frame until Android finishes booting.
printf '%s %s %s\nc 1 0 part0\np 0 0 part1\n' "$WIDTH" "$HEIGHT" "$FPS" \
    > "$OUT_DIR/desc.txt"

cd "$OUT_DIR"
rm -f bootanimation.zip
zip -0 -q -r bootanimation.zip desc.txt part0 part1
echo "已生成: $OUT_DIR/bootanimation.zip ($FRAMES 帧, $(du -h bootanimation.zip | cut -f1))"
