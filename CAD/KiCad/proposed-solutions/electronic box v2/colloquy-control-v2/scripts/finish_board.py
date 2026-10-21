"""Apply this revision's ground pours, documentation, and drill-mask details.

Run after routing, before DRC and fabrication export. This creates the named
ground zones once, reuses their geometry on later runs, and rejects foreign zones.
"""
from pathlib import Path
import argparse
import json
import re
import pcbnew as p
from build_schematic import children, one, parse

ROOT = Path(__file__).resolve().parents[1]
mm = p.FromMM


def xy(x, y):
    return p.VECTOR2I(mm(x), mm(y))


def zone(board, name, net, layer, points, priority):
    for existing in board.Zones():
        if existing.GetZoneName() == name:
            existing.SetNeedRefill(True)
            return
    item = p.ZONE(board)
    item.SetZoneName(name)
    item.SetNet(board.FindNet(net))
    item.SetLayer(layer)
    item.SetAssignedPriority(priority)
    item.SetLocalClearance(mm(.3))
    item.SetMinThickness(mm(.25))
    item.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
    item.SetThermalReliefGap(mm(.3))
    item.SetThermalReliefSpokeWidth(mm(.5))
    item.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
    item.SetMinIslandArea(10 * mm(1) ** 2)
    outline = item.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(mm(x), mm(y))
    board.Add(item)


ANNOTATIONS = [
    ("LINE 12 / RTN 4", 242, 277, 90),
    ("LINE 12 / RTN 4", 61, 265, 90),
    ("F3 LINE 12 / RTN 5", 102, 321, 0),
    ("M1 LINE 9 RTN 2 / M2 LINE 6 RTN 14", 183, 324, 0),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    args = parser.parse_args()
    project = args.board.with_suffix(".kicad_pro")
    project_content = project.read_bytes() if project.exists() else None
    # KiCad internally escapes literal slashes in global labels. Preserve the
    # copper net codes while matching the schematic's native identifiers.
    source = args.board.read_text(encoding="utf-8")
    names = set(re.findall(r'\(net\s+\d+\s+"([^"\n]+)"\)', source))
    for name in names:
        if "/" in name:
            source = source.replace(json.dumps(name), json.dumps(name.replace("/", "{slash}")))
    args.board.write_text(source, encoding="utf-8")
    board = p.LoadBoard(str(args.board.resolve()))
    circuit = json.loads((ROOT / "circuit.json").read_text(encoding="utf-8"))
    nc = {(c["ref"], pin) for c in circuit["components"] for pin, net in c["pins"].items() if net is None}
    netlist = parse((ROOT / "reports/schematic.net").read_text(encoding="utf-8"))
    pads = {(fp.GetReference(), pad.GetNumber()): pad for fp in board.GetFootprints() for pad in fp.Pads()}
    code = max(net.GetNetCode() for net in board.GetNetInfo().NetsByNetcode().values()) + 1
    for net in children(children(netlist, "nets")[0], "net"):
        name = one(net, "name")
        for node in children(net, "node"):
            key = (one(node, "ref"), one(node, "pin"))
            if key in nc and name.startswith("unconnected-"):
                target = board.FindNet(name)
                if not target:
                    target = p.NETINFO_ITEM(board, name, code)
                    code += 1
                    board.Add(target)
                pads[key].SetNet(target)
    for item in list(board.Zones()):
        if item.GetIsRuleArea():
            continue
        if not item.GetZoneName().startswith("V2_"):
            raise ValueError("Refusing to overwrite a manually added copper zone")
    # Keep analogue return currents off the body power-return distribution.
    # The north tongue includes the sensor loads and JP1's analogue terminal.
    analog = [(118,90),(139,90),(139,171),(231,171),(231,292),
              (72,292),(72,171),(118,171)]
    perimeter = [(44.75,52.91),(253.25,52.91),(253.25,348.41),(44.75,348.41)]
    for layer, side in [(p.F_Cu, "F"), (p.B_Cu, "B")]:
        zone(board, "V2_AGND_"+side, "AGND", layer, analog, 2)
        zone(board, "V2_GND_"+side, "GND", layer, perimeter, 0)
    local = ROOT / "Colloquy.pretty"
    io = p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    for fp in board.GetFootprints():
        # The sensor ground pads sit in narrow filled-copper corridors. Solid
        # joins keep those ground connections robust instead of narrow thermals.
        solid_pads = {("A-J3", "0"), ("C301", "2")}
        solid_pads.update((f"RP{n}", "2") for n in range(1, 12))
        for pad in fp.Pads():
            if (fp.GetReference(), pad.GetNumber()) in solid_pads:
                pad.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
        if fp.GetReference() in ("M1", "J2"):
            for pad in fp.Pads():
                if pad.GetAttribute() == p.PAD_ATTRIB_NPTH:
                    layers = pad.GetLayerSet()
                    layers.AddLayer(p.F_Mask)
                    layers.AddLayer(p.B_Mask)
                    pad.SetLayerSet(layers)
            name = fp.GetFPID().GetLibItemName()
            master = p.FootprintLoad(str(local), str(name))
            for pad in master.Pads():
                if pad.GetAttribute() == p.PAD_ATTRIB_NPTH:
                    layers = pad.GetLayerSet()
                    layers.AddLayer(p.F_Mask)
                    layers.AddLayer(p.B_Mask)
                    pad.SetLayerSet(layers)
            io.FootprintSave(str(local), master)
        if fp.GetReference() in ("H1", "H2", "H3", "H4"):
            fp.SetAttributes(p.FP_BOARD_ONLY | p.FP_EXCLUDE_FROM_BOM | p.FP_EXCLUDE_FROM_POS_FILES)
            fp.SetFPID(p.LIB_ID("Colloquy", "MountingHole_3.2mm_M3"))
            copy = fp.Duplicate()
            copy.SetPosition(xy(0,0))
            copy.SetReference("REF**")
            io.FootprintSave(str(local), copy)
    texts = {item.GetText(): item for item in board.GetDrawings() if hasattr(item, "GetText")}
    for value, x, y, angle in ANNOTATIONS:
        item = texts.get(value)
        new_item = item is None
        if new_item:
            item = p.PCB_TEXT(board)
        item.SetText(value)
        item.SetPosition(xy(x,y))
        item.SetLayer(p.F_SilkS)
        item.SetTextSize(xy(1,1))
        item.SetTextThickness(mm(.12))
        item.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
        if new_item:
            board.Add(item)
    board.BuildConnectivity()
    p.ZONE_FILLER(board).Fill(board.Zones())
    try:
        p.SaveBoard(str(args.board.resolve()), board)
    finally:
        # SaveBoard may also rewrite project settings, including on failure.
        if project_content is not None:
            project.write_bytes(project_content)
    content = args.board.read_text(encoding="utf-8")
    content = content.replace('(paper "A4")', '(paper "A3" portrait)')
    if "(stackup" not in content:
        stack = '''
        (stackup
            (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
            (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01) (color "Green"))
            (layer "F.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 1" (type "core") (thickness 1.51)
                (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "B.Cu" (type "copper") (thickness 0.035))
            (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01) (color "Green"))
            (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
            (copper_finish "HASL lead-free")
            (dielectric_constraints no)
        )'''
        content = content.replace("(setup", "(setup" + stack, 1)
    args.board.write_text(content, encoding="utf-8")
    print("Filled separate AGND and perimeter GND zones; verify DRC before export.")


if __name__ == "__main__":
    main()
