#!/usr/bin/env python3
"""在无 AVB footer 的 Android v2 boot 副本中替换 Rockchip 两阶段 Logo。

只生成文件，不连接设备、不刷写分区。资源格式参照 Rockchip 官方源码：
https://github.com/rockchip-linux/u-boot/blob/next-dev/tools/rockchip/resource_tool.c
"""

import argparse
import hashlib
from pathlib import Path
import struct


def boot_sha1(image):
    kernel_size, _, ramdisk_size, _, second_size, _, _, page_size = (
        struct.unpack_from("<8I", image, 8)
    )
    dtb_size = struct.unpack_from("<I", image, 1648)[0]
    digest = hashlib.sha1()
    offset = page_size
    for size in (kernel_size, ramdisk_size, second_size):
        digest.update(image[offset:offset + size])
        digest.update(struct.pack("<I", size))
        offset += (size + page_size - 1) // page_size * page_size
    # 本工具拒绝含 recovery_dtbo 的镜像，其空段长度仍参与 v2 校验。
    digest.update(struct.pack("<I", 0))
    digest.update(image[offset:offset + dtb_size])
    digest.update(struct.pack("<I", dtb_size))
    return digest.digest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("boot", type=Path, help="本屏原厂 boot 完整备份")
parser.add_argument("logo", type=Path, help="替换两阶段 Logo 的未压缩 8 位 BMP")
parser.add_argument("output", type=Path, help="新文件路径；已有文件不会覆盖")
args = parser.parse_args()
original = args.boot.read_bytes()
logo = args.logo.read_bytes()
if len(original) < 1660 or original[:8] != b"ANDROID!":
    parser.error("不是 Android boot 镜像")
kernel_size, _, ramdisk_size, _, second_size, _, _, page_size, version = (
    struct.unpack_from("<9I", original, 8)
)
recovery_size, _, header_size, dtb_size = struct.unpack_from("<IQII", original, 1632)
if version != 2 or recovery_size != 0 or header_size != 1660:
    parser.error("仅支持无 recovery_dtbo 的 Android v2 boot")
if page_size < header_size or page_size > 65536 or page_size & (page_size - 1):
    parser.error("不支持的 boot 页大小")
resource_offset = page_size
for size in (kernel_size, ramdisk_size):
    resource_offset += (size + page_size - 1) // page_size * page_size
resource_end = resource_offset + second_size
dtb_offset = resource_offset + (second_size + page_size - 1) // page_size * page_size
if second_size < 512 or dtb_offset + dtb_size > len(original):
    parser.error("boot 内容越界或缺少资源区")
if original[-64:-60] == b"AVBf":
    parser.error("带 AVB footer 的镜像不能直接替换")
if boot_sha1(original) != original[576:596]:
    parser.error("原始 boot SHA1 不匹配，停止生成")
if original[resource_offset:resource_offset + 12] != b"RSCE\0\0\0\0\1\1\1\0":
    parser.error("second 区不是支持的 Rockchip RSCE 格式")
if len(logo) < 54 or logo[:2] != b"BM":
    parser.error("Logo 不是 BMP")
width, height, planes, bits, compression = struct.unpack_from("<iiHHI", logo, 18)
if width <= 0 or height <= 0 or planes != 1 or bits != 8 or compression != 0:
    parser.error("Logo 必须是正向高度、未压缩的 8 位 BMP")
if struct.unpack_from("<I", logo, 2)[0] != len(logo):
    parser.error("BMP 声明大小不匹配")

count = struct.unpack_from("<I", original, resource_offset + 12)[0]
if count == 0 or (count + 1) * 512 > second_size:
    parser.error("资源表越界")
patched = bytearray(original)
changed = []
changed_ranges = [(576, 596)]
content_ranges = []
for i in range(count):
    entry = resource_offset + (i + 1) * 512
    if original[entry:entry + 4] != b"ENTR":
        parser.error("资源条目标记无效")
    name = original[entry + 4:entry + 224].split(b"\0")[0]
    hash_size, block, size = struct.unpack_from("<III", original, entry + 256)
    start = resource_offset + block * 512
    end = start + size
    if start < resource_offset + (count + 1) * 512 or end > resource_end:
        parser.error("资源内容越界")
    content_ranges.append((start, end))
    content = original[start:end]
    if hash_size not in (20, 32):
        parser.error("不支持的资源哈希长度")
    digest = hashlib.sha1(content) if hash_size == 20 else hashlib.sha256(content)
    if digest.digest() != original[entry + 224:entry + 224 + hash_size]:
        parser.error("原始资源哈希不匹配")
    if name not in (b"logo.bmp", b"logo_kernel.bmp"):
        continue
    if len(logo) > size or content[:2] != b"BM":
        parser.error("新 Logo 超过原图大小，或原资源不是 BMP")
    patched[start:end] = logo + bytes(size - len(logo))
    digest = hashlib.sha1(logo) if hash_size == 20 else hashlib.sha256(logo)
    patched[entry + 224:entry + 224 + hash_size] = digest.digest()
    struct.pack_into("<I", patched, entry + 264, len(logo))
    changed.append(name)
    changed_ranges.extend(((start, end), (entry + 224, entry + 224 + hash_size),
                           (entry + 264, entry + 268)))
if sorted(changed) != [b"logo.bmp", b"logo_kernel.bmp"]:
    parser.error("需要恰好一个 logo.bmp 和一个 logo_kernel.bmp")
previous_end = resource_offset + (count + 1) * 512
for start, end in sorted(content_ranges):
    if start < previous_end:
        parser.error("资源内容重叠")
    previous_end = end
patched[576:596] = boot_sha1(patched)
cursor = 0
for start, end in sorted(changed_ranges):
    if original[cursor:start] != patched[cursor:start]:
        parser.error("预期范围以外的内容发生变化")
    cursor = end
if original[cursor:] != patched[cursor:] or len(original) != len(patched):
    parser.error("镜像长度或未修改区域发生变化")
with args.output.open("xb") as output:
    output.write(patched)
print(f"已生成 {args.output}；{width}×{height}，仅替换两阶段 Logo 及校验")
print(f"SHA256 {hashlib.sha256(patched).hexdigest()}")
