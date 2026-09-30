"""Rebuild the native schematic and PCB connectivity contract without app imports.

Run with Python 3.11+. The upstream design-only netlist supplies the fixed harness
and firmware mapping; this script completes the previously unnumbered receiver.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LEGACY = HERE.parent / "next_pcb.net"
OLD_PCB = HERE.parent.parent / "electronic box" / "electronic box.kicad_pcb"
PROJECT = "colloquy-control-v2"
NS = uuid.UUID("44c5247c-66de-4a71-b72e-2b7a8a754529")
ROOT_UUID = str(uuid.uuid5(NS, PROJECT))


def uid(key):
    return str(uuid.uuid5(NS, key))


def q(value):
    return json.dumps(str(value), ensure_ascii=False)


def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack, root = [], None
    for token in tokens:
        if token == "(":
            item = []
            if stack:
                stack[-1].append(item)
            else:
                root = item
            stack.append(item)
        elif token == ")":
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    return root


def children(node, key):
    return [item for item in node[1:] if isinstance(item, list) and item[0] == key]


def one(node, key, default=None):
    found = children(node, key)
    return found[0][1] if found else default


def circuit():
    src = parse(LEGACY.read_text(encoding="utf-8"))
    parts = {}
    for item in children(children(src, "components")[0], "comp"):
        ref = one(item, "ref")
        parts[ref] = dict(ref=ref, value=one(item, "value"), footprint=one(item, "footprint"),
                          description=one(item, "description", ""), pins={})
    for net in children(children(src, "nets")[0], "net"):
        name = one(net, "name")
        for node in children(net, "node"):
            parts[one(node, "ref")]["pins"][one(node, "pin")] = name

    # Recover every physical shield pad, including intentionally unused pins.
    old = parse(OLD_PCB.read_text(encoding="utf-8"))
    for fp in children(old, "footprint"):
        props = {x[1]: x[2] for x in children(fp, "property")}
        ref = props.get("Reference")
        if ref == "A1":
            for pad in children(fp, "pad"):
                number = pad[1]
                if number:
                    parts["A1"]["pins"].setdefault(number, None)
    for n in range(1, 7):
        parts["A1"]["pins"][f"GND{n}"] = "GND"
    for n in range(1, 5):
        parts["A1"]["pins"][f"5V{n}"] = "MEGA_5V"
    # The old design-only netlist invented a terminal on this padless mount.
    # The electrical U2D2 TTL connection is J7, not a pad on M1.
    parts["M1"]["pins"] = {}
    parts["J6"]["pins"] = {str(n): ("GND" if n in (1, 2, 4) else "+5V") for n in range(1, 7)}
    parts["RS1"]["pins"]["2"] = "MEGA_5V"
    parts["RS1"]["description"] = "Reserved D2 pullup to logic rail; prevents external +5V back-powering Mega"

    resistor_fp = parts["R111"]["footprint"]
    bypass_fp = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
    for c in range(1, 6):
        body = {1: "male1", 2: "male2", 3: "female1", 4: "female2", 5: "female3"}[c]
        mic, atten, ac = f"{body}/microphone", f"{body}/mic attenuated", f"{body}/msgeq input"
        osc, vref = f"{body}/oscillator", f"{body}/internal reference"
        parts[f"U{c}"]["pins"] = {"1": "MEGA_5V", "2": "AGND", "3": f"{body}/analyser out",
                                      "4": "analyser/strobe", "5": ac, "6": vref,
                                      "7": "analyser/reset", "8": osc}
        parts[f"U{c}"]["description"] = f"{body} MSGEQ7P; pin6 is internal 2.5V reference, NEVER ground directly"
        parts[f"R{c}11"].update(value="47K", pins={"1": mic, "2": atten},
                                 description="Microphone attenuator series: default 0.126 gain with 6K8 shunt")
        parts[f"C{c}12"].update(value="100nF", pins={"1": atten, "2": ac}, footprint=bypass_fp,
                                 description="AC input coupling; passes 63Hz and above with internal 1Mohm bias")
        parts[f"R{c}13"].update(value="200K 1%", pins={"1": "MEGA_5V", "2": osc},
                                 description="MSGEQ7 clock resistor; keep adjacent to pin8")
        parts[f"C{c}14"].update(value="33pF C0G", pins={"1": osc, "2": "AGND"}, footprint=bypass_fp,
                                 description="MSGEQ7 clock capacitor; 33pF includes stray capacitance")
        parts[f"C{c}15"].update(value="100nF", pins={"1": "MEGA_5V", "2": "AGND"}, footprint=bypass_fp,
                                 description="Local MSGEQ7 supply bypass, close to pins1 and2")
        parts[f"C{c}16"] = dict(ref=f"C{c}16", value="100nF", footprint=bypass_fp,
                                pins={"1": vref, "2": "AGND"},
                                description="Pin6 internal reference bypass; not a connection to board ground")
        parts[f"R{c}16"] = dict(ref=f"R{c}16", value="6K8", footprint=resistor_fp,
                                pins={"1": atten, "2": "AGND"},
                                description="Microphone attenuator shunt; >=5K load even when bypass selected")
        parts[f"JS{c}"] = dict(ref=f"JS{c}", value="ATTEN BYPASS (OPEN)",
                               footprint="Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm",
                               pins={"1": mic, "2": atten},
                               description="Default OPEN. Bridge only for weak microphone output after measuring ADC headroom")

    for n in range(1, 12):
        parts[f"RP{n}"].update(value="10K provisional", description="Provisional photosensor shunt; replace with measured calibration value before deployment")
    parts["C2"]["footprint"] = bypass_fp
    parts["C1"]["value"] = "470uF 16V"
    power = {"J2", "J6", "J7", "C1", "C2", "JP1", "RS1", "TP30", "TP31", "TP32", "TP33", "TP34", "M1"}
    harness = {"J1", "J5", "A-J3", "B-J4", "Extra1", "Extra2", "Extra3"}
    for ref, part in parts.items():
        if ref == "A1":
            sheet = "controller"
        elif ref in power:
            sheet = "power"
        elif ref in harness:
            sheet = "harness"
        elif re.fullmatch(r"(?:RN|RP|RA)\d+", ref) or ref in {"TP20", "TP21"}:
            sheet = "io"
        else:
            if re.fullmatch(r"[RC][1-5]\d\d", ref):
                c = int(ref[1])
            elif ref.startswith("JP"):
                c = int(ref[2:]) - 1
            elif ref.startswith("TP"):
                c = int(ref[2:]) % 10
            elif ref.startswith("JS"):
                c = int(ref[2:])
            else:
                c = int(ref[1:])
            sheet = f"audio{c}"
        part["sheet"] = sheet
        part["uuid"] = uid(f"component/{ref}")
        part["sheet_path"] = f"/{ROOT_UUID}/{uid('sheet/'+sheet)}"
        part["pin_names"] = {pin: pin for pin in part["pins"]}
        part["pin_types"] = {pin: "passive" for pin in part["pins"]}
        if ref.startswith("U"):
            part["pin_names"] = dict(zip(map(str, range(1, 9)), ["VDD", "VSS", "OUT", "STROBE", "IN", "GND_REF", "RESET", "CKIN"]))
            part["pin_types"] = dict(zip(map(str, range(1, 9)), ["power_in", "power_in", "output", "input", "input", "power_out", "input", "input"]))
        if ref == "A1":
            for pin, net in part["pins"].items():
                if net is None:
                    continue
                if pin.startswith("GND"):
                    part["pin_types"][pin] = "power_in"
                elif pin == "5V1":
                    part["pin_types"][pin] = "power_out"
                elif pin.startswith("A"):
                    part["pin_types"][pin] = "input"
                elif pin.startswith("D"):
                    part["pin_types"][pin] = "bidirectional" if pin == "D2" else "output"
        part["assembly"] = "open" if ref.startswith("JS") else "fit"
        part["include_bom"] = not ref.startswith(("TP", "JS"))
        if ref.startswith("TP"):
            part["assembly"] = "copper only"
        if ref.startswith("RP"):
            part["assembly"] = "provisional_10k_calibrate"
    result = dict(project=PROJECT, revision="A-prototype", root_uuid=ROOT_UUID,
                  source="../next_pcb.net plus reviewed MSGEQ7 support and power corrections",
                  components=list(parts.values()),
                  nets=sorted({net for part in parts.values() for net in part["pins"].values() if net}),
                  assumptions=["RP1..RP11: 10K provisional, verify fitted old divider resistance and calibrate",
                               "JS1..JS5 default open: 47K/6K8 microphone attenuation, 0.126 gain",
                               "External +5V is separate from MEGA_5V; D2 pullup uses MEGA_5V",
                               "Four-connector fixed harness and original Mega footprint retained",
                               "Body amplifier and MAX9814 boards are off-board assemblies"],
                  datasheets=["https://mix-sig.com/images/datasheets/MSGEQ7.pdf",
                              "https://www.analog.com/media/en/technical-documentation/data-sheets/MAX9814.pdf"])
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "circuit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def fx(size=1.27, justify="", hide=False):
    return f'(effects (font (size {size} {size})) {"(justify " + justify + ")" if justify else ""} {"(hide yes)" if hide else ""})'


def prop(name, value, x=0, y=0, hidden=False, size=1.27, justify=""):
    return f'(property {q(name)} {q(value)} (at {x:.4f} {y:.4f} 0) {fx(size, justify, hide=hidden)})'


def sym_geometry(p):
    """Pin locations in KiCad symbol coordinates; tuple=(number,x,y,angle)."""
    ref, pins = p["ref"], list(p["pins"])
    if ref.startswith("#FLG"):
        return {1: ([("1", 0, 0, 90)], (1.27, 2.54), "flag")}
    if ref == "A1":
        groups = [
            [pin for pin in pins if pin.startswith("D") and p["pins"][pin]],
            [f"A{i}" for i in range(16)],
            [f"5V{i}" for i in range(1, 5)] + [f"GND{i}" for i in range(1, 7)],
            [pin for pin in pins if p["pins"][pin] is None],
        ]
        out = {}
        for u, numbers in enumerate(groups, 1):
            # Active signals on a single edge; unused pins occupy two edges.
            left, right = (numbers, []) if u != 4 else (numbers[:(len(numbers)+1)//2], numbers[(len(numbers)+1)//2:])
            pitch = 5.08 if u != 4 else 2.54
            h = max(len(left), len(right)) * pitch
            locs = [(pin, -20.32, (len(left)-1)*pitch/2-i*pitch, 0) for i, pin in enumerate(left)]
            locs += [(pin, 20.32, (len(right)-1)*pitch/2-i*pitch, 180) for i, pin in enumerate(right)]
            out[u] = (locs, (15.24, max(h/2, 7.62)), "block")
        return out
    if ref.startswith("U"):
        return {1: ([("1", 0, 25.4, 270), ("2", 0, -25.4, 90),
                     ("5", -25.4, 10.16, 0), ("7", -25.4, 0, 0), ("4", -25.4, -10.16, 0),
                     ("3", 25.4, 10.16, 180), ("8", 25.4, 0, 180), ("6", 25.4, -10.16, 180)],
                    (20.32, 20.32), "block")}
    if ref.startswith("C"):
        return {1: ([("1", 0, 5.08, 270), ("2", 0, -5.08, 90)], (2.54, 2.54), "capacitor")}
    if ref.startswith(("R", "JP", "JS")):
        return {1: ([("1", -5.08, 0, 0), ("2", 5.08, 0, 180)], (2.54, 1.016), "resistor")}
    if ref.startswith("TP") or ref == "Extra3":
        return {1: ([("1", -2.54, 0, 0)], (1.27, 1.27), "testpoint")}
    if not pins:
        return {1: ([], (20.32, 10.16), "block")}
    pins.sort(key=lambda pin: int(pin) if pin.isdigit() else 1000)
    pitch = 5.08
    return {1: ([(pin, 20.32, (len(pins)-1)*pitch/2-i*pitch, 180) for i, pin in enumerate(pins)],
                (15.24, max(len(pins)*pitch/2, 7.62)), "block")}


def lib_symbol(p, external=False):
    name = re.sub(r"[^A-Za-z0-9_]", "_", p["ref"])
    libname = name if external else "Colloquy:" + name
    in_bom = "yes" if p.get("include_bom", True) else "no"
    text = [f'(symbol {q(libname)} (pin_names (offset 1.27)) (exclude_from_sim no) (in_bom {in_bom}) (on_board yes)',
            prop("Reference", re.sub(r"\d+$", "", p["ref"])), prop("Value", p["value"]),
            prop("Footprint", p["footprint"], hidden=True),
            prop("Datasheet", "https://mix-sig.com/images/datasheets/MSGEQ7.pdf" if p["ref"].startswith("U") else "", hidden=True),
            prop("Description", p["description"], hidden=True)]
    for unit, (locs, box, style) in sym_geometry(p).items():
        w, h = box
        text.append(f'(symbol {q(name+"_"+str(unit)+"_1")}')
        if style in ("block", "resistor"):
            text.append(f'(rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width 0.254) (type default)) (fill (type {"background" if style == "block" else "none"})))')
        elif style == "capacitor":
            for y in [-0.762, 0.762]:
                text.append(f'(polyline (pts (xy -2.54 {y}) (xy 2.54 {y})) (stroke (width 0.508) (type default)) (fill (type none)))')
            if p["ref"] == "C1":
                text.append(f'(text "+" (at -3.81 2.54 0) {fx(1.27)})')
        elif style == "flag":
            text.append('(polyline (pts (xy 0 0) (xy 0 2.54) (xy -1.27 3.81) (xy 0 5.08) (xy 1.27 3.81) (xy 0 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))')
        else:
            text.append('(circle (center 0 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))')
        for pin, x, y, angle in locs:
            if style == "capacitor":
                length = 5.08 - 0.762
            elif style == "resistor":
                length = 2.54
            elif style == "testpoint":
                length = 1.524
            elif style == "flag":
                length = 0
            else:
                length = 5.08
            text.append(f'(pin {p["pin_types"][pin]} line (at {x} {y} {angle}) (length {length}) '
                        f'(name {q(p["pin_names"][pin] if style=="block" else "~")} {fx(1.016)}) '
                        f'(number {q(pin)} {fx(0.889)}))')
        text.append(')')
    text.append(')')
    return "\n".join(text)


class Sheet:
    def __init__(self, name, title, parts, number):
        self.name, self.title, self.parts, self.number = name, title, parts, number
        self.objects, self.counter = [], 0

    def key(self, prefix):
        self.counter += 1
        return uid(f"{self.name}/{prefix}/{self.counter}")

    def text(self, text, x, y, size=1.27, bold=False):
        font = f'(font (size {size} {size}) {"(bold yes)" if bold else ""})'
        self.objects.append(f'(text {q(text)} (at {x} {y} 0) (effects {font} (justify left top)) (uuid {q(self.key("text"))}))')

    def line(self, a, b):
        if a == b:
            return
        self.objects.append(f'(wire (pts (xy {a[0]:.4f} {a[1]:.4f}) (xy {b[0]:.4f} {b[1]:.4f})) (stroke (width 0) (type default)) (uuid {q(self.key("wire"))}))')

    def label(self, net, x, y, angle=0, size=0.95):
        self.objects.append(f'(global_label {q(net)} (shape bidirectional) (at {x:.4f} {y:.4f} {angle}) '
                            f'(effects (font (size {size} {size})) (justify {"left" if angle==0 else "right"})) '
                            f'(uuid {q(self.key("label"))}) '
                            f'{prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, hidden=True, size=1.016)})')

    def place(self, ref, x, y, unit=1, labels=True):
        p = self.parts[ref]
        locs, (w, h), style = sym_geometry(p)[unit]
        ident = p["uuid"] if unit == 1 else uid("component/"+ref+"/unit/"+str(unit))
        symname = "Colloquy:" + re.sub(r"[^A-Za-z0-9_]", "_", ref)
        value = p["value"]
        refx, refy = (x+5.08, y-2.54) if style == "capacitor" else (x, y-h-5.08)
        valuey = refy+2.54
        if style == "testpoint":
            refx, refy, valuey = x+5.08, y-3.81, y-1.27
        in_bom = "yes" if p.get("include_bom", True) else "no"
        obj = [f'(symbol (lib_id {q(symname)}) (at {x:.4f} {y:.4f} 0) (unit {unit}) (exclude_from_sim no) (in_bom {in_bom}) (on_board yes) (dnp no) (uuid {q(ident)})',
               prop("Reference", ref, refx, refy, size=1.016, justify="left" if style == "capacitor" else ""),
               prop("Value", value, refx, valuey, size=1.016, justify="left" if style == "capacitor" else ""),
               prop("Footprint", p["footprint"], x, y, hidden=True),
               prop("Datasheet", "https://mix-sig.com/images/datasheets/MSGEQ7.pdf" if ref.startswith("U") else "", x, y, hidden=True),
               prop("Description", p["description"], x, y, hidden=True)]
        for pin, *_ in locs:
            obj.append(f'(pin {q(pin)} (uuid {q(uid(ref+"/pin/"+pin))}))')
        obj.append(f'(instances (project {q(PROJECT)} (path {q(p["sheet_path"])} (reference {q(ref)}) (unit {unit})))))')
        self.objects.append("\n".join(obj))
        pins = {}
        for pin, px, py, angle in locs:
            pos = x+px, y-py
            pins[pin] = pos
            if not labels:
                continue
            net = p["pins"][pin]
            if net is None:
                self.objects.append(f'(no_connect (at {pos[0]:.4f} {pos[1]:.4f}) (uuid {q(self.key("nc"))}))')
            else:
                dx, dy = {0: (-2.54, 0), 180: (2.54, 0), 90: (0, 2.54), 270: (0, -2.54)}[angle]
                endpoint = pos[0]+dx, pos[1]+dy
                self.line(pos, endpoint)
                self.label(net, *endpoint, angle=180 if dx < 0 else 0)
        return pins

    def save(self):
        syms = "\n".join(lib_symbol(p) for p in self.parts.values())
        content = f'''(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
          (uuid {q(uid('sheetfile/'+self.name))}) (paper "A3")
          (title_block (title {q(self.title)}) (date "2026-09-29") (rev "A-prototype")
            (company "Colloquy of Mobiles") (comment 1 "Prototype: verify harness polarity and sensor values before connection"))
          (lib_symbols {syms})
          {chr(10).join(self.objects)}
          (embedded_fonts no))'''
        (HERE / f"{self.name}.kicad_sch").write_text(content, encoding="utf-8")


def schematic(data):
    # Board generation retains upstream identifiers; editable KiCad files use
    # project-local footprints copied by build_board.py.
    footprint_map = json.loads((HERE / "footprint-map.json").read_text()) if (HERE / "footprint-map.json").exists() else {}
    parts = {p["ref"]: {**p, "footprint": footprint_map.get(p["ref"], p["footprint"])} for p in data["components"]}
    library_parts = dict(parts)
    titles = dict(power="Power, reference bond and service points",
                  controller="Arduino Mega 2560: firmware 4 pin assignment",
                  harness="Fixed enclosure connectors and spare conductors",
                  io="Pixel damping, spare controls and photosensor dividers")
    bodies = {1: ("male1", 160, "D11", "A3"), 2: ("male2", 400, "D5", "A4"),
              3: ("female1", 1000, "D6", "A0"), 4: ("female2", 2500, "D46", "A1"),
              5: ("female3", 6250, "D10", "A2")}
    titles.update({f"audio{c}": f"{body}: {hz} Hz voice / {adc} receiver" for c, (body, hz, _, adc) in bodies.items()})
    for number, (name, title) in enumerate(titles.items(), 2):
        s = Sheet(name, title, {ref: p for ref, p in parts.items() if p["sheet"] == name}, number)
        s.text(title, 15.24, 17.78, 2.032, True)
        if name == "controller":
            s.place("A1", 121.92, 86.36, 1)
            s.place("A1", 284.48, 86.36, 2)
            s.place("A1", 121.92, 213.36, 3)
            s.place("A1", 299.72, 218.44, 4)
            s.text("USB powers the Mega. External +5V does not join MEGA_5V.\nAll physical 5V and GND shield pads are explicitly assigned.\nD0/D1, D13, D20/D21 remain unused by this PCB.", 15.24, 269.24, 1.016)
        elif name == "harness":
            for ref, x, y in [("J5", 40.64, 76.2), ("J1", 233.68, 76.2),
                              ("A-J3", 40.64, 198.12), ("B-J4", 233.68, 198.12),
                              ("Extra2", 152.4, 66.04), ("Extra1", 355.6, 66.04),
                              ("Extra3", 355.6, 139.7)]:
                s.place(ref, x, y)
            s.text("J5: female1    |    J1: female2\nSpeaker pairs are now LINE OUT + AUDIO RETURN.", 15.24, 127, 1.27)
            s.text("A-J3: female3 + shared center power + male1 sensors\nB-J4: male1/male2 signals; NO POWER on this connector.\nUse J7 for Dynamixel GND / +12V / DATA. Shells join GND.", 15.24, 254, 1.016)
        elif name == "io":
            s.text("330R series at the controller end", 15.24, 25.4, 1.27, True)
            for i, ref in enumerate([f"RN{i}" for i in range(1, 8)]+["RA1", "RA2"]):
                s.place(ref, 96.52, 45.72+i*22.86)
            s.text("10K is an assembly assumption: calibrate each sensor", 218.44, 25.4, 1.27, True)
            for i in range(1, 12):
                s.place(f"RP{i}", 304.8, 45.72+(i-1)*17.78)
            s.place("TP20", 264.16, 243.84)
            s.place("TP21", 355.6, 243.84)
        elif name == "power":
            for ref, x, y in [("J2", 40.64, 50.8), ("J6", 147.32, 60.96), ("J7", 284.48, 60.96),
                              ("C1", 55.88, 132.08), ("C2", 116.84, 132.08), ("JP1", 228.6, 132.08),
                              ("M1", 330.2, 137.16), ("RS1", 76.2, 203.2), ("TP30", 167.64, 203.2),
                              ("TP31", 55.88, 246.38), ("TP32", 147.32, 246.38), ("TP33", 238.76, 246.38), ("TP34", 330.2, 246.38)]:
                s.place(ref, x, y)
            s.text("J2: center-positive REGULATED 5V ONLY.\nJ6 is a parallel power landing; same-polarity lugs are commoned.\nJ7 pin2 supplies 12V servo distribution; it never powers the Mega.", 15.24, 91.44, 1.016)
            s.text("JP1: single AGND-to-GND bond beside Mega.\nM1 is the existing U2D2 mechanical mount; connect TTL lead via J7.\nExternal PSU must provide current limiting / branch protection.", 15.24, 157.48, 1.016)
            s.text("RS1 uses MEGA_5V: D2 is reserved; there is no five-body mute harness.", 15.24, 220.98, 1.016)
            # ERC power-source declarations are electrical assumptions, not PCB parts.
            for i, net in enumerate(["+5V", "+12V", "GND", "AGND"]):
                x, y = 60.96+i*60.96, 269.24
                flag = dict(ref=f"#FLG0{i+1}", value="PWR_FLAG", footprint="", description="External source / reference bond drives this net",
                            pins={"1": net}, pin_names={"1": "pwr"}, pin_types={"1": "power_out"},
                            uuid=uid("powerflag/"+net), sheet_path=f"/{ROOT_UUID}/{uid('sheet/power')}")
                s.parts[flag["ref"]] = flag
                library_parts[flag["ref"]] = flag
                s.place(flag["ref"], x, y)
        else:
            c = int(name[-1]); body, hz, digital, adc = bodies[c]
            s.text(f"TRANSMIT   {digital} / {hz} Hz hardware timer -> two RC stages -> line-level harness", 15.24, 27.94, 1.27, True)
            # Draw the passive ladder conventionally, including explicit branches.
            p1 = s.place(f"R{c}01", 91.44, 53.34, labels=False)
            p2 = s.place(f"R{c}02", 157.48, 53.34, labels=False)
            p3 = s.place(f"R{c}03", 223.52, 53.34, labels=False)
            c1 = s.place(f"C{c}01", 121.92, 76.2, labels=False)
            c2 = s.place(f"C{c}02", 187.96, 76.2, labels=False)
            for a, b in [(p1['2'], (121.92, 53.34)), ((121.92, 53.34), p2['1']),
                         (p2['2'], (187.96, 53.34)), ((187.96, 53.34), p3['1']),
                         ((121.92, 53.34), c1['1']), ((187.96, 53.34), c2['1']),
                         (c1['2'], (121.92, 91.44)), (c2['2'], (187.96, 91.44)),
                         ((121.92, 91.44), (187.96, 91.44))]:
                s.line(a, b)
            for net, x, y, angle in [(f"{body}/tone", *p1['1'], 180), (f"{body}/filter mid", 121.92, 53.34, 90),
                                     (f"{body}/filter out", 187.96, 53.34, 90), (f"{body}/line out", *p3['2'], 0),
                                     ("AGND", 121.92, 91.44, 180)]:
                # Vertical text kept out of the signal ladder: horizontal label offset.
                if angle == 90:
                    s.line((x, y), (x, y-12.7))
                    s.label(net, x, y-12.7)
                else:
                    s.label(net, x, y, angle)
            for x in [121.92, 187.96]:
                s.objects.append(f'(junction (at {x} 53.34) (diameter 0) (color 0 0 0 0) (uuid {q(s.key("junction"))}))')
            s.place(f"TP{c}", 335.28, 55.88)
            s.place(f"JP{c+1}", 325.12, 91.44)
            s.text(f"RECEIVE   {body} microphone -> 0.126 attenuation -> AC coupling -> MSGEQ7 -> {adc}", 15.24, 111.76, 1.27, True)
            for ref, x, y in [(f"R{c}11", 81.28, 144.78), (f"R{c}16", 81.28, 177.8), (f"JS{c}", 81.28, 208.28),
                              (f"C{c}12", 165.1, 147.32), (f"U{c}", 271.78, 172.72), (f"TP{c+10}", 375.92, 142.24),
                              (f"C{c}15", 370.84, 193.04), (f"C{c}16", 370.84, 236.22),
                              (f"R{c}13", 177.8, 228.6), (f"C{c}14", 261.62, 238.76)]:
                s.place(ref, x, y)
            s.text("JS default OPEN. Bridge only after measuring input headroom.\nR=47K/6K8: 2Vpp microphone becomes about 0.25Vpp at IN.\nPin6 is an INTERNAL 2.5V REFERENCE: bypass, never short to GND.", 15.24, 248.92, 1.016)
            s.text("Oscillator: 200K / 33pF incl. stray C.\nKeep clock and bypass parts at DIP pins.\nAudio return bonds at the local 0R link.", 198.12, 264.16, 1.016)
        s.save()

    # Navigation root: every sheet is embedded into one native KiCad project.
    root = Sheet("root", "Colloquy control v2 / system overview", {}, 1)
    root.text("COLLOQUY OF MOBILES / CONTROL PCB V2", 20.32, 17.78, 3.048, True)
    root.text("Revision A prototype   |   Fixed harness / Mega2560 / U2D2 / five complete audio channels", 20.32, 27.94, 1.524)
    for i, (name, title) in enumerate(titles.items()):
        x, y = 25.4+(i%3)*129.54, 58.42+(i//3)*55.88
        sheetid = uid("sheet/"+name)
        root.objects.append(f'''(sheet (at {x} {y}) (size 111.76 35.56) (fields_autoplaced yes)
          (stroke (width 0.254) (type default)) (fill (color 240 245 250 0.25)) (uuid {q(sheetid)})
          {prop("Sheetname", title, x+55.88, y-3.81, size=1.016)}
          {prop("Sheetfile", name+".kicad_sch", x+55.88, y+39.37, size=1.016)}
          (instances (project {q(PROJECT)} (path {q('/'+ROOT_UUID)} (page {q(i+2)})))))''')
        root.text(f"{i+2:02d}  {name.upper()}\nOpen this sheet for circuit detail", x+5.08, y+10.16, 1.27)
    root.text("PROTOTYPE ASSEMBLY ASSUMPTIONS", 20.32, 233.68, 1.524, True)
    root.text("RP1..RP11 are provisional 10K sensor dividers. Measure the old board and calibrate before deployment.\nJS1..JS5 default open; integrated MSGEQ7 sockets use the reviewed eight-pin manufacturer circuit.\nJ2 accepts regulated 5V only. MEGA_5V remains separate. B-J4 carries NO POWER.\nBody microphones/amplifiers are external. Verify chosen amplifier supply rating before harness connection.", 20.32, 241.3, 1.27)
    root_content = f'''(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
      (uuid {q(ROOT_UUID)}) (paper "A3")
      (title_block (title "Colloquy control v2: system overview") (date "2026-09-29") (rev "A-prototype") (company "Colloquy of Mobiles"))
      (lib_symbols) {chr(10).join(root.objects)} (sheet_instances (path "/" (page "1"))) (embedded_fonts no))'''
    (HERE / f"{PROJECT}.kicad_sch").write_text(root_content, encoding="utf-8")
    (HERE / "Colloquy.kicad_sym").write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+
                                             "\n".join(lib_symbol(p, external=True) for p in library_parts.values())+'\n)\n', encoding="utf-8")
    (HERE / "sym-lib-table").write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Project-local reviewed circuit symbols")))\n', encoding="utf-8")


if __name__ == "__main__":
    data = circuit()
    schematic(data)
    print(f"Wrote native schematic and circuit.json: {len(data['components'])} components, {len(data['nets'])} nets")
