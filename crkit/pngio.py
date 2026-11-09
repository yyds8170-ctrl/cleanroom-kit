"""纯标准库 PNG 读取器（仅用 zlib/struct）。
支持 8 位、非隔行的灰度(0)/RGB(2)/RGBA(6)，以及带调色板的常见截图。
返回 (width, height, channels, pixels)，pixels 为逐行逐通道的 bytearray。
"""
import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != PNG_SIG:
        raise ValueError("不是有效的 PNG 文件")

    pos = 8
    width = height = bit_depth = color_type = None
    idat = b""
    palette = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", body)
        elif ctype == b"PLTE":
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break

    if bit_depth != 8:
        raise ValueError(f"暂仅支持 8 位深，实际 {bit_depth}")
    raw = zlib.decompress(idat)

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError(f"不支持的颜色类型 {color_type}")
    bpp = channels
    stride = width * bpp
    pixels = bytearray(width * height * channels)
    prev = bytearray(stride)
    rpos = 0

    for row in range(height):
        ftype = raw[rpos]
        rpos += 1
        line = bytearray(raw[rpos:rpos + stride])
        rpos += stride
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = prev[i]
            ul = prev[i - bpp] if i >= bpp else 0
            x = line[i]
            if ftype == 1:
                x = (x + left) & 255
            elif ftype == 2:
                x = (x + up) & 255
            elif ftype == 3:
                x = (x + ((left + up) >> 1)) & 255
            elif ftype == 4:
                x = (x + _paeth(left, up, ul)) & 255
            line[i] = x
        start = row * stride
        pixels[start:start + stride] = line
        prev = line

    # 调色板索引展开为 RGB
    if color_type == 3:
        if palette is None:
            raise ValueError("索引图缺少 PLTE")
        out = bytearray(width * height * 3)
        for i, idx in enumerate(pixels):
            out[i * 3:i * 3 + 3] = palette[idx]
        return width, height, 3, out

    return width, height, channels, pixels


def pixel_at(pixels, channels, width, x, y):
    i = (y * width + x) * channels
    return tuple(pixels[i:i + channels])
