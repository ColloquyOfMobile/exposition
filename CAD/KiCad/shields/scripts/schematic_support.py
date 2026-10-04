"""Native KiCad schematic serialization helpers, adapted from the v2 project.

Run with Python 3.11+. Pin geometry is supplied by build_design.py; this module does not alter the circuit.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROJECT = "thomas-or-teensy"
NS = uuid.UUID("b6b6f382-9b20-4e6e-8a02-048be67203bb")
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
            prop("Datasheet", p.get("datasheet", ""), hidden=True),
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
               prop("Datasheet", p.get("datasheet", ""), x, y, hidden=True),
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
          (title_block (title {q(self.title)}) (date "2026-10-01") (rev "A-review")
            (company "Colloquy of Mobiles") (comment 1 "Prototype: verify harness polarity and sensor values before connection"))
          (lib_symbols {syms})
          {chr(10).join(self.objects)}
          (embedded_fonts no))'''
        (HERE / f"{self.name}.kicad_sch").write_text(content, encoding="utf-8")


