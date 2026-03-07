"""XDF binary format helpers."""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET  # noqa: N817

import pylsl

# XDF chunk type tags
TAG_FILE_HEADER = 1
TAG_STREAM_HEADER = 2
TAG_SAMPLES = 3
TAG_CLOCK_OFFSET = 4
TAG_STREAM_FOOTER = 6

# pylsl channel format → (XDF name, struct char, byte size)
CF_INFO: dict[int, tuple[str, str, int]] = {
    pylsl.cf_float32: ('float32', 'f', 4),
    pylsl.cf_double64: ('double64', 'd', 8),
    pylsl.cf_int8: ('int8', 'b', 1),
    pylsl.cf_int16: ('int16', 'h', 2),
    pylsl.cf_int32: ('int32', 'i', 4),
    pylsl.cf_int64: ('int64', 'q', 8),
}


def encode_vlen(n: int) -> bytes:
    """Encode an unsigned integer as a variable-length XDF integer."""
    if n <= 0xFF:  # noqa: PLR2004
        return struct.pack('<BB', 1, n)
    if n <= 0xFFFFFFFF:
        return struct.pack('<BI', 4, n)
    return struct.pack('<BQ', 8, n)


def write_chunk(f, tag: int, content: bytes) -> None:
    """Write one XDF chunk to an open binary file."""
    length = len(content) + 2  # +2 for the 2-byte tag field
    f.write(encode_vlen(length))
    f.write(struct.pack('<H', tag))
    f.write(content)


def stream_header_xml(info: pylsl.StreamInfo, stream_id: int) -> str:
    """Build the StreamHeader XML from a pylsl StreamInfo."""
    fmt_name = CF_INFO.get(info.channel_format(), ('string', '', 0))[0]
    root = ET.Element('info')
    ET.SubElement(root, 'name').text = info.name()
    ET.SubElement(root, 'type').text = info.type()
    ET.SubElement(root, 'channel_count').text = str(info.channel_count())
    ET.SubElement(root, 'nominal_srate').text = str(info.nominal_srate())
    ET.SubElement(root, 'channel_format').text = fmt_name
    ET.SubElement(root, 'source_id').text = info.source_id()
    ET.SubElement(root, 'stream_id').text = str(stream_id)
    desc = ET.fromstring(info.as_xml()) if info.as_xml() else None
    if desc is not None:
        root.append(desc)
    return ET.tostring(root, encoding='unicode')


def pack_samples(samples: list, timestamps: list, fmt: int) -> bytes:
    """Pack a batch of samples into the XDF Samples chunk payload (after stream_id)."""
    buf = bytearray()
    buf += encode_vlen(len(timestamps))

    if fmt == pylsl.cf_string:
        for sample, ts in zip(samples, timestamps):
            buf += b'\x08' + struct.pack('<d', ts)
            for val in sample:
                encoded = str(val).encode()
                buf += encode_vlen(len(encoded)) + encoded
    else:
        _, sc, _ = CF_INFO[fmt]
        fmt_str = f'<{len(samples[0])}{sc}'
        for sample, ts in zip(samples, timestamps):
            buf += b'\x08' + struct.pack('<d', ts)
            buf += struct.pack(fmt_str, *sample)

    return bytes(buf)
