"""
verify_block20.py
==================
Single-purpose verification script. Tests exactly ONE hypothesis:

    "Is there a 'BLOCK' header somewhere in GTASAsf9.b whose immediately
     following uint32 equals 100, and if so, what does the data right
     after it look like?"

This script does NOT:
  - parse scripts, vehicles, peds, or any other entity pool
  - assume a block index ("block 20" or otherwise)
  - use any reverse-engineered size formula
  - collapse/resync "BLOCK" tiling runs -- every raw occurrence is reported,
    tiling artifacts included, so a human can see them and judge for
    themselves
  - write/patch/modify anything

It only reads the file and prints what's there. Conclusions are left to
the human reading the output.

Usage:
    python3 verify_block20.py [path_to_save]

Defaults to /mnt/user-data/uploads/GTASAsf9.b if no path is given.
"""

import struct
import sys


SIG = b"BLOCK"


def find_all_block_occurrences(data: bytes):
    """Every raw byte offset where the literal 5 bytes 'BLOCK' occur.
    No filtering, no resyncing, no collapsing of adjacent hits."""
    offsets = []
    start = 0
    while True:
        idx = data.find(SIG, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    return offsets


def hex_preview(b: bytes) -> str:
    return " ".join(f"{x:02x}" for x in b)


def ascii_preview(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/GTASAsf9.b"

    with open(path, "rb") as f:
        data = f.read()

    file_len = len(data)
    print(f"File: {path}")
    print(f"Size: {file_len} bytes\n")

    offsets = find_all_block_occurrences(data)
    print(f"=== Found {len(offsets)} raw occurrences of 'BLOCK' ===\n")

    candidates = []

    for i, off in enumerate(offsets):
        # Need at least 5 (tag) + 4 (uint32) + 32 (body preview) bytes available
        if off + 5 + 4 > file_len:
            print(f"[{i:>2}] offset=0x{off:06X}  (truncated near EOF, skipping)")
            continue

        uint32_val = struct.unpack_from("<I", data, off + 5)[0]

        body_start = off + 9
        body_preview_len = min(32, file_len - body_start)
        body32 = data[body_start: body_start + body_preview_len]

        print(f"[{i:>2}] offset=0x{off:06X}  uint32_after_BLOCK={uint32_val}")
        print(f"     body[0:32]  hex: {hex_preview(body32)}")
        print(f"     body[0:32] ascii: {ascii_preview(body32)}")

        if uint32_val == 100:
            print(f"     *** uint32 == 100 -- CANDIDATE, inspecting next 100 bytes ***")

            if body_start + 100 > file_len:
                print(f"     [!] Not enough bytes remaining in file to read 100 "
                      f"bytes from 0x{body_start:06X}. Skipping byte-value count.")
            else:
                window = data[body_start: body_start + 100]
                count_00 = sum(1 for b in window if b == 0x00)
                count_01 = sum(1 for b in window if b == 0x01)
                count_ff = sum(1 for b in window if b == 0xFF)
                count_other = len(window) - count_00 - count_01 - count_ff

                print(f"     next 100 bytes hex:")
                for row in range(0, 100, 16):
                    chunk = window[row:row + 16]
                    print(f"       0x{body_start + row:06X}: {hex_preview(chunk)}")

                print(f"     byte-value breakdown over next 100 bytes:")
                print(f"       0x00 : {count_00}")
                print(f"       0x01 : {count_01}")
                print(f"       0xFF : {count_ff}")
                print(f"       other: {count_other}")

                # What immediately follows the 100-byte window (next 8 bytes),
                # for visibility only -- no interpretation/assumption applied.
                tail_start = body_start + 100
                tail = data[tail_start: tail_start + 8]
                print(f"     next 8 bytes after the 100-byte window "
                      f"(offset 0x{tail_start:06X}): {hex_preview(tail)}")

                candidates.append({
                    "index": i,
                    "offset": off,
                    "count_00": count_00,
                    "count_01": count_01,
                    "count_ff": count_ff,
                    "count_other": count_other,
                })

        print()

    print("=== Summary: occurrences where uint32_after_BLOCK == 100 ===")
    if not candidates:
        print("  None found.")
    else:
        for c in candidates:
            print(f"  [{c['index']}] offset=0x{c['offset']:06X}  "
                  f"00s={c['count_00']} 01s={c['count_01']} FFs={c['count_ff']} "
                  f"other={c['count_other']}")
        print()
        print("  A plausible 'all-100-tags-collected' state would show "
              "count_01 == 100 (or count_ff == 100, depending on the "
              "true sentinel value, which is unconfirmed). A plausible "
              "'partially collected' state would show a mix. A region "
              "that's mostly 0x00 with no variation is weaker evidence -- "
              "it could just as easily be unrelated padding or a "
              "different all-default array that happens to also be "
              "preceded by the integer 100.")
        print()
        print("  This script makes no claim about which (if any) candidate "
              "above is the real tag block. That requires either (a) "
              "matching the count against a known in-game tag count at "
              "the time this save was made, or (b) a differential "
              "comparison against a second save where exactly one more "
              "tag was collected.")


if __name__ == "__main__":
    main()