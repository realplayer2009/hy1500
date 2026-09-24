#!/usr/bin/env bash
# 从 MP4 视频制作 Android 系统开机动画 bootanimation.zip
# 用法: scripts/make_bootanimation.sh <视频.mp4> [输出目录]
# 默认输出 /tmp/bootanim/bootanimation.zip, 用 adb 推送到设备:
#   adb push /tmp/bootanim/bootanimation.zip /data/local/tmp/
#   adb shell "su 0 sh -c 'mount -o rw,remount /system \
#     && cp /system/media/bootanimation.zip /system/media/bootanimation.zip.bak \
#     && cp /data/local/tmp/bootanimation.zip /system/media/bootanimation.zip \
#     && chmod 644 /system/media/bootanimation.zip'"
set -euo pipefail

VIDEO="${1:?用法: $0 <视频.mp4> [输出目录]}"
OUT_DIR="${2:-/tmp/bootanim}"
WIDTH=1024      # rk3562_t 面板物理分辨率
HEIGHT=600
FPS=30

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/part0"

ffmpeg -y -loglevel error -i "$VIDEO" \
    -vf "scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=decrease,pad=${WIDTH}:${HEIGHT}:(ow-iw)/2:(oh-ih)/2" \
    -r "$FPS" -pix_fmt rgb24 "$OUT_DIR/part0/frame_%04d.png"

FRAMES=$(ls "$OUT_DIR/part0" | wc -l)
printf '%s %s %s\n%s 0 0\n' "$WIDTH" "$HEIGHT" "$FPS" "$FRAMES" \
    > "$OUT_DIR/desc.txt"

cd "$OUT_DIR"
rm -f bootanimation.zip
zip -q -r bootanimation.zip desc.txt part0
echo "已生成: $OUT_DIR/bootanimation.zip ($FRAMES 帧, $(du -h bootanimation.zip | cut -f1))"
