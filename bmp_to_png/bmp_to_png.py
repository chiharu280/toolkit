#!/usr/bin/env python3
"""Convert BMP screenshots written by SDL_SaveBMP into PNG.

Uses only the Python standard library so regenerating screenshots needs no
Imaging library. Each argument may be a .bmp file or a directory whose *.bmp
files are all converted. Output is written next to the input as .png.
"""
import struct
import sys
import zlib
from pathlib import Path


def read_bmp(path):
    """Return (width, height, rows) with rows as top-down RGB bytes."""
    data = Path(path).read_bytes()
    if data[:2] != b"BM":
        raise SystemExit(f"{path}: not a BMP file")
    (offset,) = struct.unpack_from("<I", data, 10)
    width, height = struct.unpack_from("<ii", data, 18)
    (bits,) = struct.unpack_from("<H", data, 28)
    (compression,) = struct.unpack_from("<I", data, 30)
    if bits not in (24, 32) or compression not in (0, 3) or width <= 0:
        raise SystemExit(
            f"{path}: unsupported BMP ({bits} bpp, compression {compression})"
        )
    top_down = height < 0
    height = abs(height)
    step = bits // 8
    stride = (width * step + 3) & ~3
    if offset + stride * height > len(data):
        raise SystemExit(f"{path}: truncated pixel data")

    rows = []
    for y in range(height):
        base = offset + (y if top_down else height - 1 - y) * stride
        pixels = data[base:base + width * step]
        row = bytearray(width * 3)
        row[0::3] = pixels[2::step]          # BMP stores BGR(A); PNG wants RGB
        row[1::3] = pixels[1::step]
        row[2::3] = pixels[0::step]
        rows.append(bytes(row))
    return width, height, rows


def write_png(path, width, height, rows):
    def chunk(tag, payload):
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row for row in rows)  # filter 0 per scanline
    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def convert(path):
    width, height, rows = read_bmp(path)
    target = Path(path).with_suffix(".png")
    write_png(target, width, height, rows)
    print(target)


def main(arguments):
    if not arguments:
        raise SystemExit("usage: bmp_to_png.py <file.bmp|directory> ...")
    sources = []
    for argument in arguments:
        path = Path(argument)
        if path.is_dir():
            sources.extend(sorted(path.glob("*.bmp")))
        else:
            sources.append(path)
    if not sources:
        raise SystemExit("no .bmp files found")
    for source in sources:
        convert(source)


if __name__ == "__main__":
    main(sys.argv[1:])
