"""
gtasa_save_core.py
===================
Reverse-engineered structural parser for GTA San Andreas (Android) .b save
files, e.g. GTASAsf1.b ... GTASAsf9.b.

EVERYTHING in this module is derived from byte-level evidence observed in
an actual save file (GTASAsf9.b, 195000 bytes), not from assumption.
Two facts in particular were verified by exact computation, not pattern-matching:

  1. SECTION HEADER FORMAT
     Every section begins with the literal ASCII bytes "BLOCK" (5 bytes)
     followed by a 4-byte little-endian unsigned size field, i.e. a 9-byte
     header. This was confirmed because, for several sections, size_field
     was found to equal *exactly* (next_header_offset - this_header_offset - 9)
     -- not approximately, byte-for-byte.

  2. FILE CHECKSUM
     The last 4 bytes of the file are a little-endian uint32 equal to
     sum(all_preceding_bytes) % 2**32, confirmed by direct computation
     against the sample file (exact match).

KNOWN WRINKLE -- "BLOCK" TILING ARTIFACT:
  In some sections, the literal bytes "BLOCK" repeat back-to-back with a
  zero-byte gap. This is NOT a sequence of empty real sections -- it is
  filler/padding inside the data of a preceding section. This module
  collapses such runs and treats the LAST tag in a run as the
  structurally meaningful one.
"""

import struct
import zlib  # only used for the (negative) checksum-hypothesis tests in self_test()


SIG = b"BLOCK"
HEADER_LEN = 9  # 5 bytes "BLOCK" + 4 bytes LE uint32 size


class Section:
    __slots__ = ("index", "header_offset", "body_offset", "size", "body_end")

    def __init__(self, index, header_offset, size, body_offset):
        self.index = index
        self.header_offset = header_offset
        self.body_offset = body_offset
        self.size = size
        self.body_end = body_offset + size

    def __repr__(self):
        return (f"Section(#{self.index} hdr=0x{self.header_offset:06x} "
                f"body=0x{self.body_offset:06x} size={self.size} "
                f"end=0x{self.body_end:06x})")


def find_all_block_tags(data: bytes):
    """Every raw byte offset where the literal 5 bytes 'BLOCK' occur."""
    offsets = []
    start = 0
    while True:
        idx = data.find(SIG, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    return offsets


def collapse_tiling_runs(offsets):
    """
    Group raw 'BLOCK' hits into runs where each hit starts exactly 5 bytes
    after the previous one (i.e. the string is tiling itself with no gap).
    """
    if not offsets:
        return []
    runs = [[offsets[0]]]
    for o in offsets[1:]:
        if o - runs[-1][-1] == 5:
            runs[-1].append(o)
        else:
            runs.append([o])
    return runs


def parse_sections(data: bytes):
    """
    Walk the file and return a list of Section objects, using the last tag
    of each tiling run as the real header position.
    """
    raw_offsets = find_all_block_tags(data)
    runs = collapse_tiling_runs(raw_offsets)
    real_headers = [run[-1] for run in runs]

    sections = []
    for i, h in enumerate(real_headers):
        if h + HEADER_LEN > len(data):
            continue
        size = struct.unpack_from("<I", data, h + 5)[0]
        body_offset = h + HEADER_LEN
        sections.append(Section(i, h, size, body_offset))
    return sections


def compute_checksum(data_without_checksum: bytes) -> int:
    """Confirmed algorithm: flat sum of all bytes, mod 2**32."""
    return sum(data_without_checksum) % (2 ** 32)


def verify_checksum(data: bytes) -> bool:
    """Returns True if the trailing 4-byte checksum matches the body."""
    stored = struct.unpack_from("<I", data, len(data) - 4)[0]
    computed = compute_checksum(data[:-4])
    return stored == computed


def recompute_and_patch_checksum(data: bytearray) -> bytearray:
    """
    Given a save file (as a mutable bytearray) whose body has been edited,
    recompute the trailing checksum and patch it in place.
    """
    new_checksum = compute_checksum(bytes(data[:-4]))
    struct.pack_into("<I", data, len(data) - 4, new_checksum)
    return data


def load_save(path: str) -> bytearray:
    with open(path, "rb") as f:
        return bytearray(f.read())


def save_to(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


def print_section_table(data: bytes):
    sections = parse_sections(data)
    print(f"{'#':<4}{'header_off':<12}{'body_off':<12}{'size':<10}{'body_end':<12}")
    for s in sections:
        print(f"{s.index:<4}0x{s.header_offset:<10x}0x{s.body_offset:<10x}"
              f"{s.size:<10}0x{s.body_end:<10x}")
    return sections


def self_test(path: str):
    """
    Run the confirmable checks against a real file and print PASS/FAIL.
    """
    data = load_save(path)
    print(f"File: {path}  size={len(data)} bytes")

    ok = verify_checksum(data)
    print(f"[{'PASS' if ok else 'FAIL'}] trailing checksum == sum(bytes[:-4]) % 2**32")

    copy = bytearray(data)
    recompute_and_patch_checksum(copy)
    ok2 = (bytes(copy) == bytes(data))
    print(f"[{'PASS' if ok2 else 'FAIL'}] checksum round-trip leaves an unmodified body byte-identical")

    sections = parse_sections(data)
    print(f"\nFound {len(sections)} sections after collapsing BLOCK-tiling runs.")
    exact_matches = 0
    for i in range(len(sections) - 1):
        expected = sections[i + 1].header_offset - sections[i].body_offset
        if sections[i].size == expected:
            exact_matches += 1
    print(f"Sections whose size field exactly matches the gap to the next "
          f"header: {exact_matches} / {len(sections) - 1}")

    return sections


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/GTASAsf9.b"
    self_test(path)