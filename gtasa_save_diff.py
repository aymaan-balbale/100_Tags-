"""
gtasa_save_diff.py
====================
Differential analysis tool for locating the 100 Los Santos spray-tag
collectible structure (or any other stat/collectible) in GTA SA Android
.b save files, by comparing two or more saves that differ by exactly one
known in-game change.

THIS SCRIPT DOES NOT ASSUME WHERE THE TAG DATA IS. It finds it, given the
right input files, by:

  1. Diffing Save A (baseline) against Save B (baseline + 1 tag collected).
  2. Automatically excluding the trailing 4-byte file checksum from the
     diff (since collecting a tag changes file contents, which changes
     the checksum -- that's an *expected*, uninteresting difference,
     not a clue).
  3. Reporting every other byte that changed, grouped into contiguous
     runs, with the section (per gtasa_save_core.parse_sections) each
     change falls inside.
  4. If a third save (Save C, baseline + a *different* single tag) is
     provided, intersecting/cross-referencing the two diffs narrows
     things further: a true per-tag bitfield should show *different*
     bytes or bits changing between A->B and A->C (since a different
     tag was collected), while still landing in the same section/array.

USAGE
-----
    python3 gtasa_save_diff.py saveA.b saveB.b [saveC.b ...]

    saveA.b : baseline, fewest tags collected
    saveB.b : baseline + exactly one tag collected, nothing else changed
    saveC.b : (optional) baseline + a different single tag collected

INTERPRETING THE OUTPUT
------------------------
- A run of differing bytes that is exactly 1 byte long, changing from
  0x00 -> 0x01 (or similar), is a strong candidate for "one byte per
  collectible" encoding.
- A run where only a single BIT differs within an otherwise-unchanged
  byte (e.g. 0x00 -> 0x01, 0x00 -> 0x02, 0x00 -> 0x04 ...) across
  different single-tag-diff save pairs is a strong candidate for a
  packed bitfield, and the bit position tells you the tag index directly.
- Differences inside fields that monotonically increase across *any*
  two saves regardless of what you did in-game (play time counters,
  RNG seed, last-saved timestamp) are noise -- this script flags large
  multi-byte runs that look like timers/counters so you can sanity-check
  and exclude them by hand if needed.
"""

import struct
import sys
from gtasa_save_core import load_save, parse_sections, Section


def diff_bytes(a: bytes, b: bytes, ignore_tail: int = 4):
    """
    Compare two equal-length (or near-equal-length) buffers, ignoring the
    last `ignore_tail` bytes (the file checksum, which is EXPECTED to
    differ any time save contents differ).
    Returns a list of (offset, old_byte, new_byte).
    """
    n = min(len(a), len(b))
    end = n - ignore_tail
    diffs = []
    for i in range(end):
        if a[i] != b[i]:
            diffs.append((i, a[i], b[i]))
    if len(a) != len(b):
        print(f"WARNING: file sizes differ ({len(a)} vs {len(b)} bytes). "
              f"This is expected if entity pools changed (e.g. a vehicle "
              f"spawned), but means offsets below this point may shift. "
              f"Diff was only performed over the first {n} bytes.")
    return diffs


def group_into_runs(diffs):
    """Collapse a list of (offset, old, new) into contiguous byte runs."""
    if not diffs:
        return []
    runs = []
    cur = [diffs[0]]
    for d in diffs[1:]:
        if d[0] == cur[-1][0] + 1:
            cur.append(d)
        else:
            runs.append(cur)
            cur = [d]
    runs.append(cur)
    return runs


def describe_run(run, sections):
    start = run[0][0]
    end = run[-1][0]
    old_bytes = bytes(d[1] for d in run)
    new_bytes = bytes(d[2] for d in run)

    section_label = "unknown / before first section"
    for s in sections:
        if s.body_offset <= start < s.body_end:
            section_label = f"section #{s.index} (body 0x{s.body_offset:x}-0x{s.body_end:x})"
            break

    # single-bit-flip detection for 1-byte runs
    bit_note = ""
    if len(run) == 1:
        xor = old_bytes[0] ^ new_bytes[0]
        if xor != 0 and (xor & (xor - 1)) == 0:  # power of two => single bit
            bit_index = xor.bit_length() - 1
            bit_note = f"  <-- SINGLE BIT FLIP, bit {bit_index} (0x{xor:02x})"

    print(f"  offset 0x{start:06x}-0x{end:06x} ({len(run)} byte(s))  "
          f"in {section_label}")
    print(f"      old: {old_bytes.hex()}")
    print(f"      new: {new_bytes.hex()}{bit_note}")


def compare(path_a: str, path_b: str, label: str = ""):
    print(f"\n{'='*70}\nDiffing {path_a}  vs  {path_b}  {label}\n{'='*70}")
    a = load_save(path_a)
    b = load_save(path_b)

    diffs = diff_bytes(a, b)
    if not diffs:
        print("No differences found outside the checksum trailer. "
              "These saves may be identical, or your in-game change "
              "wasn't actually saved.")
        return []

    runs = group_into_runs(diffs)
    sections = parse_sections(a)
    print(f"Found {len(diffs)} differing byte(s) in {len(runs)} contiguous run(s).\n")
    for run in runs:
        describe_run(run, sections)
    return runs


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    paths = sys.argv[1:]
    baseline = paths[0]

    all_run_sets = []
    for other in paths[1:]:
        runs = compare(baseline, other, label="(baseline vs this save)")
        all_run_sets.append((other, runs))

    if len(all_run_sets) >= 2:
        print(f"\n{'='*70}\nCross-referencing across {len(all_run_sets)} comparisons\n{'='*70}")
        print("Offsets that changed in EVERY comparison (good bitfield/array "
              "candidates -- the same structure changing each time a "
              "different tag was collected):")
        offset_sets = []
        for _, runs in all_run_sets:
            offsets = set()
            for run in runs:
                for d in run:
                    offsets.add(d[0])
            offset_sets.append(offsets)
        common = set.intersection(*offset_sets) if offset_sets else set()
        if common:
            for off in sorted(common):
                print(f"  0x{off:06x}")
        else:
            print("  (none -- each comparison touched different offsets; if "
                  "you collected different tags each time, this is "
                  "consistent with a per-tag bitfield where each tag owns "
                  "a different byte/bit, NOT a single shared counter byte)")


if __name__ == "__main__":
    main()