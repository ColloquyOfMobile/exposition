"""Compare KiCad's exported netlist with the circuit contract, pad by pad.

Usage: python scripts/verify_schematic.py path/to/exported.net
The exporter must be run on colloquy-control-v2.kicad_sch, not a child sheet.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_schematic import HERE, children, one, parse


def verify(netlist: Path, board: Path | None = None) -> dict:
    circuit = json.loads((HERE / "circuit.json").read_text(encoding="utf-8"))
    native = parse(netlist.read_text(encoding="utf-8"))
    expected = {(c["ref"], str(pin)): net
                for c in circuit["components"] for pin, net in c["pins"].items() if net}
    intended_nc = {(c["ref"], str(pin))
                   for c in circuit["components"] for pin, net in c["pins"].items() if net is None}
    actual = {}
    connected_nets = set()
    for net in children(children(native, "nets")[0], "net"):
        name = one(net, "name").replace("{slash}", "/")
        for node in children(net, "node"):
            key = one(node, "ref"), one(node, "pin")
            if key[0].startswith("#"):
                continue
            if key in intended_nc and name.startswith("unconnected-"):
                continue
            if key in actual:
                raise AssertionError(f"Pad {key} appears in multiple nets")
            actual[key] = name
            connected_nets.add(name)
    refs = {one(c, "ref") for c in children(children(native, "components")[0], "comp")}
    target_refs = {c["ref"] for c in circuit["components"]}
    problems = []
    for key in sorted(set(expected) | set(actual)):
        if expected.get(key) != actual.get(key):
            problems.append({"pad": list(key), "expected": expected.get(key), "actual": actual.get(key)})
    if refs != target_refs:
        problems.append({"missing_components": sorted(target_refs-refs), "extra_components": sorted(refs-target_refs)})
    result = dict(passed=not problems, components=len(refs), connected_pads=len(actual),
                  connected_nets=len(connected_nets), intentional_nc_pads=len(intended_nc),
                  problems=problems)
    if board:
        pcb = parse(board.read_text(encoding="utf-8"))
        copper = {}
        board_refs = set()
        for fp in children(pcb, "footprint"):
            props = {p[1]: p[2] for p in children(fp, "property")}
            ref = props.get("Reference")
            if ref not in target_refs:
                continue  # Additional padless mounting holes are mechanical.
            board_refs.add(ref)
            for pad in children(fp, "pad"):
                pin = pad[1]
                if not pin:
                    continue
                item = children(pad, "net")
                name = item[0][2].replace("{slash}", "/") if item else ""
                if not name:
                    continue
                key = ref, pin
                if key in intended_nc and name.startswith("unconnected-"):
                    continue
                if key in copper and copper[key] != name:
                    problems.append({"duplicate_pad_net_mismatch": list(key), "nets": [copper[key], name]})
                copper[key] = name
        for key in sorted(set(actual) | set(copper)):
            if actual.get(key) != copper.get(key):
                problems.append({"board_pad": list(key), "schematic": actual.get(key), "board": copper.get(key)})
        if board_refs != target_refs:
            problems.append({"missing_board_components": sorted(target_refs-board_refs)})
        result["board_components_checked"] = len(board_refs)
        result["board_connected_pads"] = len(copper)
        result["passed"] = not problems
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netlist", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pcb", type=Path, help="Also compare physical board pad assignments")
    args = parser.parse_args()
    result = verify(args.netlist, args.pcb)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["passed"] else 1)
