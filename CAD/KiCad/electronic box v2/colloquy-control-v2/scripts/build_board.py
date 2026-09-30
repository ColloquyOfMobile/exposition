"""Build the placed board from circuit.json using the KiCad 9 Python interpreter.

This is a deliberate regeneration operation: the routed PCB is only replaced
when --replace is passed. Ordinary runs write a separate staging board.
"""
from pathlib import Path
import argparse
import json

import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
NAME = "colloquy-control-v2"
ORIGINAL = ROOT.parents[1] / "electronic box" / "electronic box.kicad_pcb"
LIB = Path(p.__file__).resolve().parents[3] / "share/kicad/footprints"
if not LIB.exists():
    LIB = Path(r"C:\Program Files\KiCad\9.0\share\kicad\footprints")
LOCAL = ROOT / "Colloquy.pretty"
mm = p.FromMM


def xy(x, y):
    return p.VECTOR2I(mm(x), mm(y))


def text(board, content, x, y, size=1.2, layer=p.F_SilkS, angle=0):
    item = p.PCB_TEXT(board)
    item.SetText(content)
    item.SetPosition(xy(x, y))
    item.SetTextSize(xy(size, size))
    item.SetTextThickness(mm(0.16 if size >= 1.2 else 0.12))
    item.SetLayer(layer)
    item.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
    board.Add(item)
    return item


def local_footprint(comp, old):
    identifier = comp["footprint"]
    lib, name = identifier.split(":", 1)
    saved = name.replace(" ", "_")
    if lib in ("custom1", "PCM_arduino-library"):
        ref = {"A1": "A1", "M1": "U1", "J2": "J2", "J6": "J6"}[comp["ref"]]
        fp = old[ref].Duplicate()
        fp.SetOrientationDegrees(0)
        fp.SetPosition(xy(0, 0))
        # U2D2 mounting apertures are drillable round holes, not milling contours.
        if comp["ref"] in ("M1", "J2"):
            for graphic in list(fp.GraphicalItems()):
                if graphic.GetLayer() == p.Edge_Cuts:
                    pad = p.PAD(fp)
                    pad.SetNumber("")
                    pad.SetAttribute(p.PAD_ATTRIB_NPTH)
                    pad.SetShape(p.PAD_SHAPE_CIRCLE)
                    diameter = 4.5 if comp["ref"] == "M1" else 1.6
                    pad.SetSize(xy(diameter, diameter))
                    pad.SetDrillSize(xy(diameter, diameter))
                    layers = p.LSET.AllCuMask()
                    layers.AddLayer(p.F_Mask)
                    layers.AddLayer(p.B_Mask)
                    pad.SetLayerSet(layers)
                    pad.SetPosition(graphic.GetCenter())
                    fp.Add(pad)
                    fp.Remove(graphic)
    else:
        fp = p.FootprintLoad(str(LIB / (lib + ".pretty")), name)
        if fp is None:
            raise ValueError(f"Missing footprint {identifier}")
    for pad in fp.Pads():
        pad.SetNetCode(0)
    # Original absolute custom STEP references cannot travel with this project.
    # Standard KiCad 3D references use KICAD9_3DMODEL_DIR and remain portable.
    if lib in ("custom1", "PCM_arduino-library"):
        fp.Models().clear()
    if comp["ref"] == "J2":
        for pad in fp.Pads():
            if pad.GetAttribute() == p.PAD_ATTRIB_PTH and not pad.GetNumber():
                pad.SetSize(xy(1.2, 2.4))
    if comp["ref"] == "A1":
        for graphic in fp.GraphicalItems():
            if hasattr(graphic, "SetMirrored") and graphic.GetLayer() in (p.B_SilkS, p.B_Fab):
                graphic.SetMirrored(True)
    fp.SetReference("REF**")
    fp.SetValue(saved)
    fp.SetFPID(p.LIB_ID("Colloquy", saved))
    p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LOCAL), fp)
    return fp, saved


def placements():
    pos = {
        "A1": (141.16, 53.32, -90), "M1": (49, 56.66, 0),
        "J2": (251.7, 61.17, -90), "J6": (228.68, 93.98, -90),
        "J7": (70.04, 124.44, 180),
        "J5": (239.16, 322.66, 90), "J1": (58, 303.27, -90),
        "A-J3": (97.305, 334.96, 0), "B-J4": (179.655, 334.96, 0),
        "Extra1": (71, 285, 0), "Extra2": (228, 294, 0),
        "Extra3": (212, 324, 0), "C1": (225, 65, 180),
        "C2": (223, 79, 0), "JP1": (127, 96.5, 0),
        "RS1": (209, 110, 0), "TP30": (224, 110, 0),
        "TP20": (203, 105, 0), "TP21": (203, 100, 0),
        "TP31": (231, 79, 0), "TP32": (132, 91, 0),
        "TP33": (232, 86, 0), "TP34": (127, 103, 0),
        "RA1": (188, 160, 0), "RA2": (188, 165, 0),
    }
    for n in range(1, 8):
        pos[f"RN{n}"] = (203, 123 + (n - 1) * 6, 0)
    for n in range(1, 12):
        pos[f"RP{n}"] = (124, 117 + (n - 1) * 4, 0)
    # Five spacious strips, ordered by increasing frequency.
    for n in range(1, 6):
        x = 78 + (n - 1) * 32
        pos.update({
            f"R{n}01": (x, 185, 0), f"C{n}01": (x+14, 191, 0),
            f"R{n}02": (x, 201, 0), f"C{n}02": (x+14, 207, 0),
            f"R{n}03": (x, 217, 0), f"TP{n}": (x+14, 217, 0),
            f"JP{n+1}": (x, 229, 0),
            f"U{n}": (x+4, 250, 0),
            f"R{n}11": (x, 279, 0), f"R{n}16": (x+14, 273, 90),
            f"C{n}12": (x+14, 281, 0),
            f"R{n}13": (x+12, 238, 0), f"C{n}14": (x+12, 245, 0),
            f"C{n}15": (x, 243, 0), f"C{n}16": (x+15, 258, 0),
            f"JS{n}": (x+4, 273, 0), f"TP{n+10}": (x, 264, 0),
        })
    return pos


def project_file():
    original = json.loads(ORIGINAL.with_suffix(".kicad_pro").read_text())
    original["meta"] = {"filename": NAME + ".kicad_pro", "version": 1}
    original["text_variables"] = {"REVISION": "A-prototype"}
    settings = original["board"]["design_settings"]
    settings["drc_exclusions"] = []
    settings["rules"].update(min_clearance=0.25, min_track_width=0.25,
                             min_copper_edge_clearance=0.5,
                             min_via_diameter=0.8, min_through_hole_diameter=0.4,
                             min_via_annular_width=0.15, min_hole_clearance=0.25)
    original["net_settings"] = {
        "classes": [], "meta": {"version": 4}, "net_colors": None,
        "netclass_assignments": None, "netclass_patterns": []}
    for name, width, via, drill in [("Default", .3, .8, .4), ("Power", 2, 1.2, .6),
                                   ("Analog", .5, .8, .4)]:
        original["net_settings"]["classes"].append({
            "name": name, "clearance": .25, "track_width": width,
            "via_diameter": via, "via_drill": drill,
            "microvia_diameter": .3, "microvia_drill": .1,
            "diff_pair_gap": .25, "diff_pair_width": .3, "diff_pair_via_gap": .25,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "wire_width": 6, "bus_width": 12, "line_style": 0})
    for net in ("+5V", "+12V", "GND"):
        original["net_settings"]["netclass_patterns"].append({"netclass": "Power", "pattern": net})
    for net in ("MEGA_5V", "AGND"):
        original["net_settings"]["netclass_patterns"].append({"netclass": "Analog", "pattern": net})
    original["pcbnew"]["last_paths"] = {} if "pcbnew" in original else {}
    (ROOT / (NAME + ".kicad_pro")).write_text(json.dumps(original, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    LOCAL.mkdir(exist_ok=True)
    data = json.loads((ROOT / "circuit.json").read_text())
    board = p.BOARD()
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(mm(1.6))
    board.GetDesignSettings().m_MinClearance = mm(.25)
    original = p.LoadBoard(str(ORIGINAL))
    old = {fp.GetReference(): fp for fp in original.GetFootprints()}
    for shape in original.GetDrawings():
        if shape.GetLayer() == p.Edge_Cuts:
            board.Add(shape.Duplicate())
    net_names = sorted({net for c in data["components"] for net in c["pins"].values() if net})
    nets = {}
    for code, name in enumerate(net_names, 1):
        net = p.NETINFO_ITEM(board, name, code)
        board.Add(net)
        nets[name] = net
    pos = placements()
    footprint_map = {}
    for comp in data["components"]:
        ref = comp["ref"]
        if not comp.get("footprint"):
            continue
        if ref not in pos:
            raise ValueError(f"No placement for {ref}: {comp}")
        fp, name = local_footprint(comp, old)
        fp.SetReference(ref)
        fp.SetValue(comp["value"])
        board.Add(fp)
        if comp.get("sheet_path") and comp.get("uuid"):
            path = p.KIID_PATH()
            for uid in (comp["sheet_path"].strip("/") + "/" + comp["uuid"]).split("/"):
                path.push_back(p.KIID(uid))
            fp.SetPath(path)
        x, y, angle = pos[ref]
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(xy(x, y))
        for pad in fp.Pads():
            name_net = comp["pins"].get(pad.GetNumber())
            if name_net:
                pad.SetNet(nets[name_net])
        fp.Reference().SetVisible(True)
        fp.Reference().SetLayer(p.F_SilkS)
        fp.Reference().SetMirrored(False)
        fp.Reference().SetTextSize(xy(1, 1))
        fp.Reference().SetTextThickness(mm(.12))
        fp.Reference().SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
        fp.Reference().SetPosition(xy(x+3, y-2.4))
        if ref.startswith("RP"):
            fp.Reference().SetPosition(xy(x-3.5, y))
        elif ref.startswith("C") and ref != "C1":
            fp.Reference().SetPosition(xy(x+2.5, y-4.5))
        elif ref.startswith("R") and angle == 90:
            fp.Reference().SetPosition(xy(x+3.5, y-5))
        overrides = {"J2": (235,65), "J5": (232,320), "J1": (65,306),
                     "A-J3": (100,329), "B-J4": (180,329), "C1": (220,55),
                     "J7": (70,118), "TP30": (227,112.5)}
        if ref in overrides:
            fp.Reference().SetPosition(xy(*overrides[ref]))
        fp.Value().SetVisible(False)
        footprint_map[ref] = "Colloquy:" + name
    for n, (x, y) in enumerate([(52, 114), (244, 82), (52, 341), (244, 341)], 1):
        fp = p.FootprintLoad(str(LIB / "MountingHole.pretty"), "MountingHole_3.2mm_M3")
        fp.SetReference(f"H{n}")
        fp.SetValue("M3 3.2mm NPTH")
        fp.SetPosition(xy(x, y))
        fp.SetAttributes(p.FP_BOARD_ONLY | p.FP_EXCLUDE_FROM_BOM | p.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp)
        # An 8 mm pad-sized copper keepout enforces the washer envelope.
        zone = p.ZONE(board)
        zone.SetIsRuleArea(True)
        zone.SetLayerSet(p.LSET.AllCuMask(2))
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowCopperPour(True)
        outline = zone.Outline()
        outline.NewOutline()
        for px, py in [(x-4,y-4),(x+4,y-4),(x+4,y+4),(x-4,y+4)]:
            outline.Append(mm(px), mm(py))
        board.Add(zone)
    text(board, "COLLOQUY / CONTROL V2", 151, 301, 3)
    text(board, "REV A - PROTOTYPE / 2026-09-29", 151, 307, 1.6)
    text(board, "LINE LEVEL OUTPUTS - AMPLIFIERS AT BODIES", 151, 312, 1.2)
    text(board, "FEMALE 1", 235, 294, 1.5, angle=90)
    text(board, "FEMALE 2", 65, 275, 1.5, angle=90)
    text(board, "A-J3 / FEMALE 3 + MALE 1", 104, 325, 1.5)
    text(board, "B-J4 / MALES / NO POWER", 184, 320, 1.5)
    text(board, "5V INPUT / CENTER +", 232, 57, 1.1)
    text(board, "BOARD +5V", 231, 75, 1)
    text(board, "MEGA 5V", 130, 87, 1)
    text(board, "AGND STAR", 122, 100, 1)
    text(board, "D2 / D3 / D4 AUDIO CONTROL", 220, 115, 1)
    text(board, "DXL: GND / 12V / DATA", 75, 130, 1.2)
    labels = [("male1",160,"D11",3),("male2",400,"D5",4),
              ("female1",1000,"D6",0),("female2",2500,"D46",1),("female3",6250,"D10",2)]
    for n,(body,hz,pin,adc) in enumerate(labels):
        x=78+n*32
        text(board, body.upper(), x+8, 174, 1.6)
        text(board, f"{hz} Hz / {pin}", x+8, 179, 1.15)
        text(board, f"EAR {adc} / A{adc}", x+8, 234, 1.2)
        text(board, "MIC ATTEN BYPASS", x+8, 289, .8)
    board.SetFileName(str(ROOT / (NAME + ".kicad_pcb")))
    target = ROOT / (NAME + ("" if args.replace else "-placed") + ".kicad_pcb")
    p.SaveBoard(str(target), board)
    target.write_text(target.read_text(encoding="utf-8").replace('(paper "A4")', '(paper "A3" portrait)'), encoding="utf-8")
    (ROOT / "footprint-map.json").write_text(json.dumps(footprint_map, indent=2)+"\n")
    (ROOT / "fp-lib-table").write_text('(fp_lib_table\n (version 7)\n (lib (name "Colloquy")(type "KiCad")(uri "${KIPRJMOD}/Colloquy.pretty")(options "")(descr "Vendored control PCB footprints"))\n)\n')
    project_file()
    print(f"Placed {len(list(board.GetFootprints()))} footprints; {len(nets)} nets: {target}")


if __name__ == "__main__":
    main()
