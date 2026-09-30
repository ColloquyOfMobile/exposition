"""Independently compare fixed drilling with the original enclosure board.

Run using KiCad's Python interpreter. This script only reads PCB files and
prints a JSON report; use shell redirection to retain the result if needed.
It does not replace KiCad DRC or physical enclosure fit checks.
"""

from pathlib import Path
import argparse
import hashlib
import json
import math

import pcbnew as p


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parents[1] / "electronic box" / "electronic box.kicad_pcb"


def vector_mm(vector):
    return tuple(round(value, 6) for value in p.ToMM(vector))


def drilling(footprint, attribute):
    return sorted(
        (pad.GetNumber(), vector_mm(pad.GetPosition()), vector_mm(pad.GetDrillSize()))
        for pad in footprint.Pads() if pad.GetAttribute() == attribute
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    path = args.board.resolve()
    original = p.LoadBoard(str(OLD))
    board = p.LoadBoard(str(path))
    old = {fp.GetReference(): fp for fp in original.GetFootprints()}
    new = {fp.GetReference(): fp for fp in board.GetFootprints()}
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    for ref in ("J1", "J5", "A-J3", "B-J4", "J2", "A1", "J6", "J7"):
        before = drilling(old[ref], p.PAD_ATTRIB_PTH)
        after = drilling(new[ref], p.PAD_ATTRIB_PTH)
        check(f"{ref} original connector drilling", before == after,
              "Plated pad numbers, positions, and drill sizes match the old board.")

    for ref, old_ref in (("M1", "U1"), ("J2", "J2")):
        circles = []
        for graphic in old[old_ref].GraphicalItems():
            if graphic.GetLayer() == p.Edge_Cuts and graphic.GetShape() == p.SHAPE_T_CIRCLE:
                diameter = round(2 * p.ToMM(graphic.GetRadius()), 6)
                circles.append(("", vector_mm(graphic.GetCenter()), (diameter, diameter)))
        after = drilling(new[ref], p.PAD_ATTRIB_NPTH)
        check(f"{ref} original cutout geometry", sorted(circles) == after,
              {"original_circles": sorted(circles), "replacement_drills": after})

    for ref, centre in {"H1": (52.0, 114.0), "H2": (244.0, 82.0),
                        "H3": (52.0, 341.0), "H4": (244.0, 341.0)}.items():
        holes = drilling(new[ref], p.PAD_ATTRIB_NPTH)
        expected = [("", centre, (3.2, 3.2))]
        check(f"{ref} new M3 standoff", holes == expected, holes)

    mega = {pad.GetNumber(): pad.GetNetname() for pad in new["A1"].Pads()}
    expected = {**{f"5V{n}": "MEGA_5V" for n in range(1, 5)},
                **{f"GND{n}": "GND" for n in range(1, 7)}}
    check("Mega duplicated supply pin mapping",
          all(mega.get(number) == net for number, net in expected.items()), expected)

    support_distances = []
    for n in range(1, 6):
        chip = {pad.GetNumber(): pad for pad in new[f"U{n}"].Pads()}
        for name, chip_pin, capacitor, maximum in (
            ("VDD bypass", "1", f"C{n}15", 10),
            ("CKIN capacitor", "8", f"C{n}14", 8),
            ("internal reference bypass", "6", f"C{n}16", 8),
        ):
            destination = chip[chip_pin]
            candidates = [pad for pad in new[capacitor].Pads()
                          if pad.GetNetname() == destination.GetNetname()]
            distance = min((math.dist(vector_mm(destination.GetPosition()),
                                     vector_mm(pad.GetPosition())) for pad in candidates),
                           default=float("inf"))
            detail = {"ic": f"U{n}", "function": name, "capacitor": capacitor,
                      "direct_pin_distance_mm": round(distance, 3),
                      "review_limit_mm": maximum}
            support_distances.append(detail)
            check(f"U{n} {name} placement", distance <= maximum, detail)

    report = {
        "board": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "footprints": len(new),
        "track_and_via_count": len(list(board.GetTracks())),
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
        "limitations": [
            "Support component distances are straight-line placement checks, not routed loop lengths.",
            "Actual enclosure fit, harness current ratings, and operating temperature remain unmeasured.",
            "Run KiCad DRC separately for clearances, courtyard overlap, and connectivity.",
        ],
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
