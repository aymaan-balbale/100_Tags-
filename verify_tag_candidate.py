"""
verify_tag_candidate.py
========================
Tests ONE specific, already-located candidate region: the 100-byte block
immediately following the literal sequence "BLOCK" + uint32(100) at file
offset 0x02A4A0 in GTASAsf9.b.

This script is READ-ONLY. It does not modify, patch, or recalculate
anything in the save file.

It does the following, and nothing more:
  1. Re-validates the candidate exists at the expected offset (does NOT
     blindly trust a hardcoded number -- if the bytes there don't match
     what was previously observed, it aborts loudly instead of silently
     proceeding on a stale assumption).
  2. Prints index : byte value for all 100 bytes.
  3. Prints which indices hold 0xFF.
  4. Attempts a comparison against "official" Los Santos tag numbering --
     see the WARNING printed in that section. This comparison is
     explicitly flagged as UNVERIFIED, because nothing in the binary
     tells us whether array index N corresponds to "tag #N" in any
     walkthrough/wiki numbering. That correspondence has not been
     established from evidence and is not asserted as fact here.
  5. Compares the observed 0xFF count against a player-supplied
     "Statistics screen" count, if given via --ingame-count. Without
     that input, this script cannot determine a match -- it will say so
     rather than guess.
  6. Prints a generated report summarizing what is and isn't established.
"""

import struct
import sys
import argparse


CANDIDATE_OFFSET = 0x02A4A0  # discovered, not assumed -- re-validated below
HEADER_LEN = 9               # "BLOCK" (5) + uint32 (4)
REGION_LEN = 100


def hex_row(b: bytes) -> str:
    return " ".join(f"{x:02x}" for x in b)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="/mnt/user-data/uploads/GTASAsf9.b")
    parser.add_argument("--ingame-count", type=int, default=None,
                         help="The tag count currently shown on the player's "
                              "in-game Statistics screen, for cross-checking "
                              "against the observed 0xFF count.")
    args = parser.parse_args()

    with open(args.path, "rb") as f:
        data = f.read()

    print(f"File: {args.path}  ({len(data)} bytes)\n")

    # --- Step 0: re-validate the candidate, don't trust the hardcoded offset blindly ---
    tag_bytes = data[CANDIDATE_OFFSET:CANDIDATE_OFFSET + 5]
    if tag_bytes != b"BLOCK":
        print(f"ABORT: Expected b'BLOCK' at 0x{CANDIDATE_OFFSET:06X}, found {tag_bytes!r}.")
        print("The candidate offset no longer matches what was previously "
              "observed in GTASAsf9.b. This script will not proceed on a "
              "stale assumption. If you're running this against a "
              "DIFFERENT save file, this offset is not expected to be valid "
              "for it -- re-run the broader scan (verify_block20.py) first.")
        sys.exit(1)

    declared_len = struct.unpack_from("<I", data, CANDIDATE_OFFSET + 5)[0]
    if declared_len != 100:
        print(f"ABORT: Expected declared length 100 at 0x{CANDIDATE_OFFSET+5:06X}, "
              f"found {declared_len}.")
        sys.exit(1)

    region_start = CANDIDATE_OFFSET + HEADER_LEN
    region_end = region_start + REGION_LEN
    region = data[region_start:region_end]

    # Structural corroboration: does the next BLOCK tag begin EXACTLY where
    # this region ends, with zero slack? (Observed previously -- re-checked
    # here, not assumed.)
    next_tag = data[region_end:region_end + 5]
    aligned = (next_tag == b"BLOCK")

    print(f"Candidate header validated at 0x{CANDIDATE_OFFSET:06X}: "
          f"b'BLOCK' + uint32(100)  -> region 0x{region_start:06X}-0x{region_end-1:06X}")
    print(f"Next 5 bytes after region end (0x{region_end:06X}): {next_tag!r}  "
          f"{'(matches BLOCK -- zero slack, exact boundary)' if aligned else '(does NOT match BLOCK -- unexpected slack)'}\n")

    # --- Step 1 & 2: index : value for all 100 bytes ---
    print("=== Index : Byte value (all 100 bytes) ===")
    for i, b in enumerate(region):
        print(f"  [{i:>3}] 0x{b:02X}")
    print()

    # --- Step 3: indices holding 0xFF ---
    ff_indices = [i for i, b in enumerate(region) if b == 0xFF]
    other_values = sorted(set(region) - {0x00, 0xFF})

    print("=== Indices with value 0xFF ===")
    print(f"  {ff_indices}")
    print(f"  Count: {len(ff_indices)}")
    if other_values:
        print(f"  NOTE: values other than 0x00/0xFF are also present: "
              f"{[hex(v) for v in other_values]} -- this region is not a "
              f"clean binary 0x00/0xFF array, which matters for "
              f"interpretation below.")
    print()

    # --- Step 4: comparison against "official" tag numbering ---
    print("=== Comparison against 'official' Los Santos tag numbering ===")
    print("  WARNING: This comparison cannot be performed with confidence.")
    print("  The binary tells us WHICH array indices (0-99) are set to 0xFF.")
    print("  It does NOT tell us whether array index N corresponds to")
    print("  'Tag #N' as numbered in any community walkthrough or wiki.")
    print("  That correspondence would require either:")
    print("    (a) decompiled/leaked script source showing how the game")
    print("        assigns array slots to physical tag objects, or")
    print("    (b) a save-to-save diff where a SPECIFIC, known, named tag")
    print("        (e.g. the one outside Cluckin' Bell in Ganton) was")
    print("        collected, anchoring index 0 (or whichever index flips)")
    print("        to a real-world location.")
    print("  Neither is available yet. The indices below are reported as")
    print("  raw array positions ONLY -- no real-world tag identity is")
    print("  claimed for any of them.")
    print(f"  Raw flagged indices (positional, NOT confirmed to be real tag IDs): {ff_indices}")
    print()

    # --- Step 5: compare count against in-game Statistics screen ---
    print("=== Comparison against in-game Statistics screen ===")
    if args.ingame_count is None:
        print("  No --ingame-count supplied. Cannot determine a match.")
        print(f"  Observed 0xFF count in this region: {len(ff_indices)}")
        print("  Re-run with e.g. --ingame-count 6 after checking the ")
        print("  Statistics screen in-game for 'Tags Sprayed' / equivalent.")
    else:
        print(f"  In-game count supplied: {args.ingame_count}")
        print(f"  Observed 0xFF count:    {len(ff_indices)}")
        if args.ingame_count == len(ff_indices):
            print("  MATCH. This is consistent with (but does not, by itself, "
                  "prove) this region being the tag table.")
        else:
            print("  MISMATCH. This is evidence AGAINST this region being the "
                  "tag table, unless the in-game count was checked at a "
                  "different point than when this save was written.")
    print()

    # --- Step 6: generated report ---
    print("=" * 70)
    print("REPORT")
    print("=" * 70)
    print(f"""
Candidate region: 0x{region_start:06X} - 0x{region_end-1:06X} (100 bytes),
preceded by the literal sequence BLOCK + uint32(100) at 0x{CANDIDATE_OFFSET:06X}.

EVIDENCE FOR this being a genuine, deliberately-sized data block:
  - This is the ONLY location in the entire file where the uint32
    immediately after a BLOCK tag equals exactly 100.
  - The declared length (100) accounts for the region with zero slack:
    the next BLOCK tag begins at exactly region_end, byte for byte.
    {"Confirmed in this run." if aligned else "NOT confirmed in this run -- see warning above."}
  - The region is sparse and binary-ish (mostly 0x00 with a minority of
    0xFF), which is the right SHAPE for a "100 collectibles, mostly not
    yet collected" flag array.

EVIDENCE AGAINST treating this as confirmed:
  - The sentinel value is 0xFF, not 0x01 -- this contradicts the layout
    patch_tags.py was originally written against (0x00/0x01 + trailing
    count). If this IS the tag array, that script's logic was wrong
    about the encoding, not just the offset.
  - The "100" preceding the array is positioned as a LEADING length
    field for this block, not a trailing "tags collected" counter.
    Nothing in this 100-byte region tracks a running total separately
    from the flags themselves, as far as has been observed.
  - No index-to-physical-tag mapping has been established (see Step 4).
  - No save-to-save diff has confirmed that any of these specific bytes
    change when a tag is collected. Everything above is consistent with
    the hypothesis, but consistency is not proof.
  - {"An in-game count was supplied and matched." if (args.ingame_count is not None and args.ingame_count == len(ff_indices)) else "No confirmed in-game count match has been established yet."}

VERDICT: {"PLAUSIBLE AND PARTIALLY CORROBORATED" if (args.ingame_count is not None and args.ingame_count == len(ff_indices)) else "PLAUSIBLE BUT NOT YET CONFIRMED"}.
This is the strongest single candidate found in the file, and the
structural self-consistency (zero-slack boundary, unique uint32==100)
is real, reproducible evidence -- not a guess. But "best candidate"
is not the same as "verified." The most direct way to actually confirm
or refute this is empirical: patch this region, load the save in-game,
and see whether the Statistics screen reads 100/100 Tags Sprayed with
no other side effects.
""")


if __name__ == "__main__":
    main()
