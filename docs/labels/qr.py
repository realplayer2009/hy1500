#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小 QR 码编码器（ISO/IEC 18004, Model 2）
==========================================

用途
    给标贴生成二维码（海康风格标签需要"二维码 + 编号 + 型号"）。
    本机无 qrcode/segno 等库，故自行实现。

范围
    版本 1~6、字节/字母数字模式、四级纠错。标贴只需版本 1
    （19 位字母数字，ECC-M 容量 20），但保留到 6 以备数据变长。

正确性保障
    同文件附 qr_decode()，可把生成的矩阵解回原文，用于往返自检。
    make_labels.py 的 verify.py 会对每一张标贴的二维码做解码比对。
"""
from __future__ import annotations

# ---------------- GF(256) ----------------
# 本原多项式 x^8+x^4+x^3+x^2+1 = 0x11D
GF_EXP = [0] * 512
GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    GF_EXP[_i] = _x
    GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    GF_EXP[_i] = GF_EXP[_i - 255]


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]


def gf_gen_poly(degree: int) -> list[int]:
    """RS 生成多项式，**最高次项在前**，长度 degree+1。

    g(x) = Π_{i=0}^{degree-1}(x - α^i)；GF(2^8) 中减法即加法，故为 (x + α^i)。
    累加过程天然得到「最低次项在前」，末尾反转成「最高次项在前」——
    rs_remainder 的合成除法按 gen[0] 对齐被消项，要求 gen[0] 是最高次项系数。
    曾因漏了这次反转，阶数 ≥2 的纠错码全是废值：自己的解码器不校验 RS，
    往返测试照样全过，但真实扫码器解不出来。
    """
    g = [1]
    for i in range(degree):
        ng = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            ng[j + 1] ^= c                      # c * x
            ng[j] ^= gf_mul(c, GF_EXP[i])       # c * α^i
        g = ng
    return g[::-1]


def rs_remainder(data: list[int], ecc_len: int) -> list[int]:
    gen = gf_gen_poly(ecc_len)
    res = list(data) + [0] * ecc_len
    for i in range(len(data)):
        coef = res[i]
        if coef:
            for j in range(ecc_len + 1):
                res[i + j] ^= gf_mul(gen[j], coef)
    return res[len(data):]


# ---------------- 版本/纠错参数表（v1~v6）----------------
# (每块纠错码字数, 块数1组数, 每组数据码字数, 总数据码字数)
ECC_TABLE = {
    "L": {1: (7, 1, 19), 2: (10, 1, 34), 3: (15, 1, 55),
          4: (20, 1, 80), 5: (26, 1, 108), 6: (18, 2, 68)},
    "M": {1: (10, 1, 16), 2: (16, 1, 28), 3: (26, 1, 44),
          4: (18, 2, 64), 5: (24, 2, 86), 6: (16, 4, 108)},
    "Q": {1: (13, 1, 13), 2: (22, 1, 22), 3: (18, 2, 36),
          4: (26, 2, 52), 5: (18, 2, 72), 6: (24, 4, 92)},
    "H": {1: (17, 1, 9), 2: (28, 1, 16), 3: (22, 2, 28),
          4: (18, 2, 44), 5: (22, 4, 64), 6: (28, 4, 84)},
}
ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def data_codewords(version: int, ecc: str) -> int:
    return ECC_TABLE[ecc][version][2]


def _put(bits: list[int], val: int, n: int) -> None:
    for i in range(n - 1, -1, -1):
        bits.append((val >> i) & 1)


def encode_data(text: str, version: int, ecc: str) -> list[int]:
    """文本 → 数据码字（已补终止符/填充位/填充字节）。"""
    if any(c not in ALNUM for c in text):
        raise ValueError("含非字母数字字符，需改用字节模式: {!r}".format(text))
    cap = data_codewords(version, ecc)
    bits: list[int] = []
    _put(bits, 0b0010, 4)                 # 字母数字模式
    _put(bits, len(text), 9)              # v1~9 字符数 9 位
    i = 0
    while i + 1 < len(text):
        _put(bits, ALNUM.index(text[i]) * 45 + ALNUM.index(text[i + 1]), 11)
        i += 2
    if i < len(text):
        _put(bits, ALNUM.index(text[i]), 6)
    cap_bits = cap * 8
    _put(bits, 0, min(4, cap_bits - len(bits)))     # 终止符
    while len(bits) % 8:
        bits.append(0)                              # 补到字节边界
    k = 0
    while len(bits) < cap_bits:                     # 交替填充字节
        _put(bits, 0xEC if k % 2 == 0 else 0x11, 8)
        k += 1
    out = []
    for j in range(0, len(bits), 8):
        v = 0
        for b in bits[j:j + 8]:
            v = (v << 1) | b
        out.append(v)
    if len(out) != cap:
        raise RuntimeError("数据码字数 {} != 容量 {}".format(len(out), cap))
    return out


def build_codewords(data: list[int], version: int, ecc: str) -> list[int]:
    """数据码字 + RS 纠错码字，按标准块交织（v1~v6 单组时无需交织）。"""
    ecc_len, nblocks, dbytes = ECC_TABLE[ecc][version]
    if len(data) != dbytes:
        raise RuntimeError("数据码字数 {} != 表定 {}".format(len(data), dbytes))
    blocks = []
    per = dbytes // nblocks
    extra = dbytes % nblocks
    pos = 0
    for b in range(nblocks):
        n = per + (1 if b >= nblocks - extra else 0)
        blk = data[pos:pos + n]
        pos += n
        blocks.append(blk + rs_remainder(blk, ecc_len))

    out: list[int] = []
    max_d = max(len(b) - ecc_len for b in blocks)
    for i in range(max_d):                      # 交织数据
        for b in blocks:
            if i < len(b) - ecc_len:
                out.append(b[i])
    for i in range(ecc_len):                    # 交织纠错
        for b in blocks:
            out.append(b[len(b) - ecc_len + i])
    return out


# ---------------- 掩码 ----------------
MASKS = [
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i * j) % 3 + (i + j) % 2) % 2 == 0,
]


def _runs(line: list[bool]) -> int:
    p, run = 0, 1
    for k in range(1, len(line)):
        if line[k] == line[k - 1]:
            run += 1
        else:
            if run >= 5:
                p += 3 + (run - 5)
            run = 1
    if run >= 5:
        p += 3 + (run - 5)
    return p


def penalty(m: list[list[bool]]) -> int:
    size = len(m)
    p = 0
    for row in m:
        p += _runs(row)
    for j in range(size):
        p += _runs([m[i][j] for i in range(size)])
    for i in range(size - 1):                       # 规则2：2x2 同色块
        for j in range(size - 1):
            if m[i][j] == m[i][j + 1] == m[i + 1][j] == m[i + 1][j + 1]:
                p += 3
    p1 = [True, False, True, True, True, False, True,
          False, False, False, False]
    p2 = p1[::-1]
    for line in ([r for r in m] + [[m[i][j] for i in range(size)]
                                    for j in range(size)]):
        for k in range(size - 10):
            if line[k:k + 11] in (p1, p2):          # 规则3：类探测图形
                p += 40
    dark = sum(1 for r in m for v in r if v)        # 规则4：明暗比
    p += 10 * int(abs(100.0 * dark / (size * size) - 50) // 5)
    return p


def format_bits(ecc: str, mask: int) -> int:
    val = {"L": 1, "M": 0, "Q": 3, "H": 2}[ecc] << 3 | mask
    v = val << 10
    for i in range(14, 9, -1):
        if v & (1 << i):
            v ^= 0b10100110111 << (i - 10)
    return ((val << 10) | v) ^ 0x5412


# ---------------- 矩阵构建 ----------------
def _function_patterns(m: list[list[bool]], size: int, version: int) -> None:
    # 探测图形 + 分隔符
    for fx, fy in ((0, 0), (size - 7, 0), (0, size - 7)):
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                x, y = fx + dx, fy + dy
                if 0 <= x < size and 0 <= y < size:
                    if 0 <= dx <= 6 and 0 <= dy <= 6:
                        m[y][x] = (dx in (0, 6) or dy in (0, 6)
                                   or (2 <= dx <= 4 and 2 <= dy <= 4))
                    else:
                        m[y][x] = False               # 分隔符
    # 定位图形
    for i in range(size):
        if m[6][i] is None:
            m[6][i] = (i % 2 == 0)
        if m[i][6] is None:
            m[i][6] = (i % 2 == 0)
    # 黑模块
    m[size - 8][8] = True
    # 校正图形（v2~v6 单中心，位于 size-7）
    if version >= 2:
        c = size - 7
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                m[c + dy][c + dx] = (
                    max(abs(dx), abs(dy)) != 1)


def _format_positions(size: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """两份格式信息的 15 个位置（row, col）。

    第 1 份绕左上探测图形：第 8 行取 8 格（跳过第 6 列定位）+ 第 8 列取 7 格。
    第 2 份：第 8 列取 7 格 + 第 8 行取 8 格（右下方向）。
    注意 (size-8, 8) 是黑模块，不属于格式信息，不能算进来。
    """
    pos1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    pos2 = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
            (size - 5, 8), (size - 6, 8), (size - 7, 8),
            (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5),
            (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]
    return pos1, pos2


def _place_format(m: list[list[bool]], fb: int) -> None:
    size = len(m)
    pos1, pos2 = _format_positions(size)
    for k, (r, c) in enumerate(pos1):
        m[r][c] = bool((fb >> (14 - k)) & 1)
    for k, (r, c) in enumerate(pos2):
        m[r][c] = bool((fb >> (14 - k)) & 1)


def _data_positions(size: int) -> list[tuple[int, int]]:
    """标准 Z 字形扫描顺序（自右下向左上，遇第 6 列跳过）。

    注意：返回的是**全部** Z 字形坐标，含功能图形格。填位/读位前必须
    先用 _reserved() 过滤，否则会覆盖探测图形或抢格式信息的位。
    """
    pos = []
    direction = -1
    row = size - 1
    col = size - 1
    while col > 0:
        if col == 6:
            col -= 1
        while 0 <= row < size:
            for c in (col, col - 1):
                pos.append((row, c))
            row += direction
        row -= direction
        direction = -direction
        col -= 2
    return pos


def _reserved(size: int, version: int) -> set[tuple[int, int]]:
    """所有非数据格：功能图形（探测/定位/校正/黑模块）+ 格式信息位。"""
    m: list[list[bool]] = [[None] * size for _ in range(size)]
    _function_patterns(m, size, version)
    for p in _format_positions(size)[0] + _format_positions(size)[1]:
        m[p[0]][p[1]] = False
    return {(r, c) for r in range(size) for c in range(size)
            if m[r][c] is not None}


def qr_matrix(text: str, ecc: str = "M") -> tuple[list[list[bool]], int, int]:
    """返回 (矩阵, version, mask)。矩阵 True = 黑模块。"""
    for version in range(1, 7):
        try:
            data = encode_data(text, version, ecc)
            break
        except Exception:
            continue
    else:
        raise ValueError("数据过长，超出版本 6 容量")
    cw = build_codewords(data, version, ecc)
    bits: list[int] = []
    for b in cw:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    # v1 无余位；v2~v6 补 7 个余位
    rem = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7}[version]
    bits += [0] * rem

    size = version * 4 + 17
    base: list[list[bool]] = [[None] * size for _ in range(size)]
    _function_patterns(base, size, version)
    # 只往非功能格填数据；_reserved 额外扣除格式信息的 30 个格，
    # 否则这些位会被数据抢占，掩码/格式信息读到的是垃圾。
    reserved = _reserved(size, version)
    positions = [p for p in _data_positions(size) if p not in reserved]
    if len(positions) < len(bits):
        raise RuntimeError("矩阵容量不足：{} < {}".format(len(positions), len(bits)))

    best, best_pen = None, None
    for mask in range(8):
        m = [row[:] for row in base]
        f = MASKS[mask]
        for k, (r, c) in enumerate(positions[:len(bits)]):
            m[r][c] = bool(bits[k]) != f(r, c)
        _place_format(m, format_bits(ecc, mask))
        p = penalty(m)
        if best_pen is None or p < best_pen:
            best, best_pen = m, p
    return best, version, mask_of(best, ecc)


def mask_of(m: list[list[bool]], ecc: str) -> int:
    """从矩阵反读出所用掩码（供解码器使用）。

    掩码在 5 个数据位的低 3 位，位于最终 15 位值的 bit 12..10
    （val = ECC级<<3 | 掩码，整体再 <<10），故须右移 10 位再取。
    """
    pos1 = _format_positions(len(m))[0]
    fb = 0
    for k, (r, c) in enumerate(pos1):
        fb = (fb << 1) | (1 if m[r][c] else 0)
    fb ^= 0x5412
    return (fb >> 10) & 0b111


# ---------------- 解码器（仅用于自检）----------------
def qr_decode(m: list[list[bool]], ecc: str = "M") -> str:
    size = len(m)
    version = (size - 17) // 4
    mask = mask_of(m, ecc)
    f = MASKS[mask]
    base: list[list[bool]] = [[None] * size for _ in range(size)]
    _function_patterns(base, size, version)
    # 与编码端一致：只读非功能格（含格式信息位）
    reserved = _reserved(size, version)
    positions = [p for p in _data_positions(size) if p not in reserved]

    bits: list[int] = []
    for (r, c) in positions:
        bits.append(1 if (bool(m[r][c]) != f(r, c)) else 0)
    cw: list[int] = []
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for b in bits[i:i + 8]:
            v = (v << 1) | b
        cw.append(v)
    dbytes = data_codewords(version, ecc)
    data = cw[:dbytes]

    # 解位流。必须按"还剩几个字符"决定读 11 位（配对）还是 6 位（末位单字符），
    # 否则奇数长度时会把 6 位有效值 + 5 位填充零拼成 11 位，解出错误的字符。
    bs = "".join(format(b, "08b") for b in data)
    mode = int(bs[0:4], 2)
    if mode != 0b0010:
        raise ValueError("非字母数字模式: {}".format(mode))
    n = int(bs[4:13], 2)
    out, p = [], 13
    while len(out) < n:
        if n - len(out) >= 2:
            v = int(bs[p:p + 11], 2)
            out.append(ALNUM[v // 45])
            out.append(ALNUM[v % 45])
            p += 11
        else:
            out.append(ALNUM[int(bs[p:p + 6], 2)])
            p += 6
    return "".join(out)


# ---------------- PIL 渲染 ----------------
def qr_image(text: str, module_px: int = 8, border: int = 2,
             ecc: str = "M") -> "Image.Image":
    from PIL import Image
    m, ver, mask = qr_matrix(text, ecc)
    size = len(m)
    dim = (size + 2 * border) * module_px
    im = Image.new("1", (dim, dim), 1)
    px = im.load()
    for r in range(size):
        for c in range(size):
            if m[r][c]:
                for dy in range(module_px):
                    for dx in range(module_px):
                        px[(c + border) * module_px + dx,
                           (r + border) * module_px + dy] = 0
    return im
