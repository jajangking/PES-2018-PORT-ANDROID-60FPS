#!/usr/bin/env python3
"""Align an APK's uncompressed entries without zipalign (4-byte, 4096-byte for .so)."""
import struct
import sys
import zipfile

src, dst = sys.argv[1], sys.argv[2]

with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        name_bytes = info.filename.encode("utf-8")
        native = info.filename.startswith("lib/") and info.filename.endswith(".so")
        align = 4096 if native and info.compress_type == zipfile.ZIP_STORED else (
            4 if info.compress_type == zipfile.ZIP_STORED else 1
        )

        base_extra = info.extra or b""
        pad = 0
        if align > 1:
            base = zout.fp.tell() + 30 + len(name_bytes) + len(base_extra)
            pad = (-base) % align
            if 0 < pad < 4:
                pad += align
        extra = base_extra
        if pad:
            # ID 0xd935 is the marker zipalign uses for alignment padding.
            extra += struct.pack("<HH", 0xD935, pad - 4) + b"\x00" * (pad - 4)

        new = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        new.compress_type = info.compress_type
        new.comment = info.comment
        new.extra = extra
        new.create_system = info.create_system
        new.create_version = info.create_version
        new.extract_version = info.extract_version
        new.flag_bits = info.flag_bits
        new.internal_attr = info.internal_attr
        new.external_attr = info.external_attr
        new.volume = info.volume
        with zout.open(new, "w", force_zip64=False) as fh:
            fh.write(data)

print("aligned:", dst)
