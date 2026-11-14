"""纯标准库 PNG 读取器（仅用 zlib/struct）。

支持 8 位深的灰度(0)/RGB(2)/索引(3)/灰度+alpha(4)/RGBA(6)，支持 Adam7
隔行（interlace=1）解包、tRNS 透明块并入 alpha 合成，并对每个 chunk 做
CRC32 校验（不一致给出中文警告，标注 crc_mismatch，不强制中断）。
返回 (width, height, channels, pixels)，pixels 为逐行逐通道的 bytearray。

许可证：PolyForm Noncommercial License 1.0.0。
Copyright (c) 2026 洋洋。
"""
import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"

# Adam7 隔行扫描的 7 个 pass：(起始列, 起始行, 列步长, 行步长)
_ADAM7_PASSES = [
    (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
    (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2),
]

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
_SUPPORTED_TYPES = "灰度 0、RGB 2、索引 3、灰度+alpha 4、RGBA 6"


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter_row(ftype, line, prev, bpp):
    for i in range(len(line)):
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
    return line


def _pass_dimensions(width, height, x0, y0, step_x, step_y):
    cols = 0
    x = x0
    while x < width:
        cols += 1
        x += step_x
    rows = 0
    y = y0
    while y < height:
        rows += 1
        y += step_y
    return cols, rows


def _decode_interlace(raw, width, height, bpp):
    """按 Adam7 七次扫描解包，返回完整分辨率像素 bytearray。"""
    pixels = bytearray(width * height * bpp)
    rpos = 0
    for x0, y0, step_x, step_y in _ADAM7_PASSES:
        cols, rows = _pass_dimensions(width, height, x0, y0, step_x, step_y)
        if cols == 0 or rows == 0:
            continue
        stride = cols * bpp
        prev = bytearray(stride)
        for j in range(rows):
            if rpos >= len(raw):
                raise ValueError("不是有效的 PNG 文件：隔行数据被截断")
            ftype = raw[rpos]
            rpos += 1
            line = bytearray(raw[rpos:rpos + stride])
            rpos += stride
            _unfilter_row(ftype, line, prev, bpp)
            for k in range(cols):
                x, y = x0 + k * step_x, y0 + j * step_y
                dst = (y * width + x) * bpp
                src = k * bpp
                pixels[dst:dst + bpp] = line[src:src + bpp]
            prev = line
    return pixels


def _decode_scanlines(raw, width, height, bpp):
    stride = width * bpp
    pixels = bytearray(width * height * bpp)
    prev = bytearray(stride)
    rpos = 0
    for row in range(height):
        ftype = raw[rpos]
        rpos += 1
        line = bytearray(raw[rpos:rpos + stride])
        rpos += stride
        _unfilter_row(ftype, line, prev, bpp)
        start = row * stride
        pixels[start:start + stride] = line
        prev = line
    return pixels


def _parse_png(data):
    """解析 PNG 块，返回元数据字典与解包后的像素。"""
    if data[:8] != PNG_SIG:
        raise ValueError("不是有效的 PNG 文件：文件头与 PNG 签名不符")

    meta = {
        "width": None, "height": None, "bit_depth": None, "color_type": None,
        "interlace": None, "palette": None, "trns": None,
        "crc_mismatch": False, "warnings": [],
    }
    idat = b""
    pos = 8
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("不是有效的 PNG 文件：块结构截断")
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        if pos + 12 + length > len(data):
            raise ValueError("不是有效的 PNG 文件：块长度超出文件范围")
        body = data[pos + 8:pos + 8 + length]
        (crc_stored,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(ctype + body) & 0xFFFFFFFF != crc_stored:
            meta["crc_mismatch"] = True
            meta["warnings"].append(f"块 {ctype.decode('latin1')} CRC32 校验不一致")
        pos += 12 + length

        if ctype == b"IHDR":
            meta["width"], meta["height"], meta["bit_depth"], meta["color_type"], \
                _, _, meta["interlace"] = struct.unpack(">IIBBBBB", body)
        elif ctype == b"PLTE":
            meta["palette"] = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif ctype == b"tRNS":
            ct = meta["color_type"]
            if ct == 3:
                meta["trns"] = list(body)
            elif ct == 0:
                meta["trns"] = body[0]  # 8 位深取高字节作为透明灰度值
            elif ct == 2:
                # tRNS 为三组 16 位大端采样；8 位深取每组高字节作为透明色
                meta["trns"] = (body[0], body[2], body[4])
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break

    if meta["bit_depth"] != 8:
        raise ValueError(f"暂仅支持 8 位深，实际位深 {meta['bit_depth']}（支持范围：8）")
    channels = _CHANNELS.get(meta["color_type"])
    if channels is None:
        raise ValueError(f"不支持的颜色类型 {meta['color_type']}（支持：{_SUPPORTED_TYPES}）")

    raw = zlib.decompress(idat)
    bpp = channels
    if meta["interlace"] == 1:
        pixels = _decode_interlace(raw, meta["width"], meta["height"], bpp)
    else:
        pixels = _decode_scanlines(raw, meta["width"], meta["height"], bpp)
    return meta, pixels


def read_png_meta(path):
    """读取 PNG 并返回 (meta, width, height, channels, pixels)。

    meta 含 crc_mismatch / warnings / palette / trns / interlace 等附加信息。
    """
    with open(path, "rb") as f:
        data = f.read()
    meta, pixels = _parse_png(data)
    channels = _CHANNELS[meta["color_type"]]
    return meta, meta["width"], meta["height"], channels, pixels


def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    meta, pixels = _parse_png(data)
    channels = _CHANNELS[meta["color_type"]]

    # 调色板索引展开为 RGB（带 tRNS 时由 read_png_rgb 做透明合成）
    if meta["color_type"] == 3:
        if meta["palette"] is None:
            raise ValueError("索引图缺少 PLTE")
        out = bytearray(meta["width"] * meta["height"] * 3)
        for i, idx in enumerate(pixels):
            out[i * 3:i * 3 + 3] = meta["palette"][idx]
        return meta["width"], meta["height"], 3, out
    return meta["width"], meta["height"], channels, pixels


def pixel_at(pixels, channels, width, x, y):
    i = (y * width + x) * channels
    return tuple(pixels[i:i + channels])


def _composite_white(r, g, b, a):
    return (
        255 - (255 - r) * a // 255,
        255 - (255 - g) * a // 255,
        255 - (255 - b) * a // 255,
    )


def read_png_rgb(path):
    """读取任意支持的 PNG 并归一化为 (width, height, rgb_bytearray)。

    灰度扩展为 RGB；RGBA/灰度+alpha 按 alpha 合成到白底；tRNS 透明色/索引
    透明同样按透明合成到白底，避免半透明误差。
    """
    meta, w, h, c, px = read_png_meta(path)
    n = w * h
    out = bytearray(n * 3)
    trns, palette, ct = meta["trns"], meta["palette"], meta["color_type"]

    if ct == 3:
        if palette is None:
            raise ValueError("索引图缺少 PLTE")
        for i, idx in enumerate(px):
            r, g, b = palette[idx]
            a = trns[idx] if trns and idx < len(trns) else 255
            out[i * 3:i * 3 + 3] = bytes(_composite_white(r, g, b, a))
        return w, h, out

    if c == 3:
        if trns is not None:
            for i in range(n):
                r, g, b = px[i * 3], px[i * 3 + 1], px[i * 3 + 2]
                a = 0 if (r, g, b) == tuple(trns) else 255
                out[i * 3:i * 3 + 3] = bytes(_composite_white(r, g, b, a))
        else:
            out[:] = px
        return w, h, out
    if c == 1:  # 灰度
        for i in range(n):
            v = px[i]
            a = 0 if trns is not None and v == trns else 255
            comp, _, _ = _composite_white(v, v, v, a)
            out[i * 3:i * 3 + 3] = bytes((comp, comp, comp))
    elif c == 2:  # 灰度 + alpha
        for i in range(n):
            v, a = px[i * 2], px[i * 2 + 1]
            comp, _, _ = _composite_white(v, v, v, a)
            out[i * 3:i * 3 + 3] = bytes((comp, comp, comp))
    elif c == 4:  # RGBA，合成到白底
        for i in range(n):
            r, g, b, a = px[i * 4], px[i * 4 + 1], px[i * 4 + 2], px[i * 4 + 3]
            out[i * 3:i * 3 + 3] = bytes(_composite_white(r, g, b, a))
    else:
        raise ValueError(f"无法归一化通道数 {c}")
    return w, h, out


def _chunk(ctype, data):
    block = ctype + data
    return struct.pack(">I", len(data)) + block + struct.pack(">I", zlib.crc32(block) & 0xFFFFFFFF)


def write_png(path, width, height, rgb_bytes, compress=9):
    """写入 8 位、非隔行 RGB（color type 2）PNG。rgb_bytes 长度需为 width*height*3。"""
    if len(rgb_bytes) != width * height * 3:
        raise ValueError("像素数据长度与宽高不匹配")
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0（None）
        raw.extend(rgb_bytes[y * stride:(y + 1) * stride])
    idat = zlib.compress(bytes(raw), compress)
    with open(path, "wb") as f:
        f.write(PNG_SIG)
        f.write(_chunk(b"IHDR", ihdr))
        f.write(_chunk(b"IDAT", idat))
        f.write(_chunk(b"IEND", b""))
    return path
