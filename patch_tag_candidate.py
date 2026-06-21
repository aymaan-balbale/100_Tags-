"""
patch_tag_candidate.py
========================
Patches ONLY the 100-byte candidate region at 0x02A4A9-0x02A50C in
GTASAsf9.b to all 0xFF (the "collected" sentinel observed in that
region), then recalculates the file's trailing checksum using the
confirmed algorithm (sum of all preceding bytes mod 2**32).

This script exists to let you EMPIRICALLY test the hypothesis: load
the output in-game and check whether the Statistics screen reads
100/100 Tags Sprayed with no other corruption. That's a stronger
confirmation than anything obtainable from static analysis alone.

SAFETY:
  - The original file is never opened in write mode and is never modified.
  - Output is always written to a NEW file: <stem>_patched.b
  - Before writing anything, this script re-validates:
      1. "BLOCK" + uint32(100) really is at the expected offset
      2. The 100-byte region really does end exactly where the next
         "BLOCK" tag begins (zero slack)
    If either check fails, it aborts without writing anything.
  - This script does NOT claim the hypothesis is proven. It patches
    the best current candidate so you can test it. Treat the result
    as an experiment, not a finished mod.

Usage:
    python3 patch_tag_candidate.py [path_to_save]

Defaults to /mnt/user-data/uploads/GTASAsf9.b.
Output: <same directory>/<stem>_patched.b  (e.g. GTASAsf9_patched.b)
"""

import struct
import sys
import os


CANDIDATE_OFFSET = 0x02A4A0
HEADER_LEN = 9
REGION_LEN = 100


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/GTASAsf9.b"

    with open(path, "rb") as f:
        original = f.read()

    print(f"Source (read-only): {path}  ({len(original)} bytes)")

    # --- Re-validate before touching anything ---
    if original[CANDIDATE_OFFSET:CANDIDATE_OFFSET + 5] != b"BLOCK":
        print(f"ABORT: 'BLOCK' not found at 0x{CANDIDATE_OFFSET:06X}. "
              f"Refusing to patch. No file written.")
        sys.exit(1)

    declared_len = struct.unpack_from("<I", original, CANDIDATE_OFFSET + 5)[0]
    if declared_len != 100:
        print(f"ABORT: declared length at 0x{CANDIDATE_OFFSET+5:06X} is "
              f"{declared_len}, expected 100. Refusing to patch.")
        sys.exit(1)

    region_start = CANDIDATE_OFFSET + HEADER_LEN
    region_end = region_start + REGION_LEN

    if original[region_end:region_end + 5] != b"BLOCK":
        print(f"ABORT: expected the next 'BLOCK' tag immediately at "
              f"0x{region_end:06X} (zero slack), but didn't find it. "
              f"Refusing to patch -- the structural assumption this "
              f"script depends on doesn't hold for this file.")
        sys.exit(1)

    print(f"[+] Validated candidate region 0x{region_start:06X}-0x{region_end-1:06X}.")

    before = original[region_start:region_end]
    print(f"[*] Current region contents: "
          f"{before.count(0x00)}x 0x00, {before.count(0xFF)}x 0xFF, "
          f"{len(before) - before.count(0x00) - before.count(0xFF)}x other")

    # --- Build the patched copy ---
    patched = bytearray(original)

    for i in range(REGION_LEN):
        patched[region_start + i] = 0xFF

    # The leading length field is already 100 -- confirm, don't blindly rewrite.
    still_100 = struct.unpack_from("<I", patched, CANDIDATE_OFFSET + 5)[0]
    assert still_100 == 100, "leading length field changed unexpectedly"

    print(f"[+] Set all {REGION_LEN} bytes in the candidate region to 0xFF.")
    print("[*] No 'trailing count' field was modified -- none was found to "
          "exist for this candidate; the only length field observed is "
          "the LEADING uint32, which was already 100 and is unchanged.")

    # --- Recalculate the one confirmed checksum: trailing 4 bytes of the whole file ---
    old_checksum = struct.unpack_from("<I", patched, len(patched) - 4)[0]
    new_checksum = sum(patched[:-4]) % (2 ** 32)
    struct.pack_into("<I", patched, len(patched) - 4, new_checksum)
    print(f"[+] Recalculated trailing file checksum: "
          f"0x{old_checksum:08X} -> 0x{new_checksum:08X}")

    # --- Write to a new file, never touch the original ---
    stem, ext = os.path.splitext(path)
    out_path = f"{stem}_patched{ext}"
    with open(out_path, "wb") as f:
        f.write(patched)

    print(f"\n[+] Wrote patched copy to: {out_path}")
    print(f"[+] Original file untouched: {path}")
    print(f"\nLength check: original={len(original)} bytes, "
          f"patched={len(patched)} bytes "
          f"({'unchanged' if len(original) == len(patched) else 'CHANGED -- unexpected!'})")
    print("\nThis is an experiment, not a confirmed fix. Load the patched "
          "file in-game and check whether the Statistics screen reads "
          "100/100 Tags Sprayed, and whether anything else looks wrong.")


if __name__ == "__main__":
    main()
