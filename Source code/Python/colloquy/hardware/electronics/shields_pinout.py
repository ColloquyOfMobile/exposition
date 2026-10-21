"""Matching functional pinouts, read from the shield PCBs and adapter manifest.

Run export_shields_pinout.py from the repository root; no hardware is opened.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from . import harness
except ImportError:
    import harness

ROOT = harness.KICAD / 'proposed-solutions/shields'
STATIC = Path(__file__).resolve().parents[2] / 'server2/static/hardware'
BODIES = ('female1', 'female2', 'female3', 'male1', 'male2')
COLOURS = {'mic': '#b34478', 'photo': '#976410', 'tone': '#2864a2',
           'pixel': '#287653', 'control': '#6556a0'}


def board_pins(name):
    board = harness.parse((ROOT / name / (name + '.kicad_pcb')).read_text(encoding='utf-8'))
    result = {}
    for fp in harness.children(board, 'footprint'):
        ref = harness._property(fp, 'Reference')
        pins = {}
        for pad in harness.children(fp, 'pad'):
            net = harness.children(pad, 'net')
            pins[pad[1]] = net[0][2].replace('{slash}', '/').lstrip('/') if net else None
        result[ref] = pins
    return result


def connections():
    """Follow adapter input dividers and translator channels to the socket pins.

    The adapter manifest supplies socket GPIO labels; every connected pad/net
    is checked against the PCB before any picture is written.
    """
    mega = board_pins('backplane')['A1']
    native = board_pins('teensy-adapter')
    parts = {c['ref']: c for c in json.loads((ROOT / 'teensy-adapter/circuit.json').read_text())['components']}
    for ref, part in parts.items():
        for pin, net in part['pins'].items():
            if net:
                assert native[ref][pin] == net, (ref, pin, net)
    for pin, net in parts['JM1']['pins'].items():
        if net:
            assert mega[pin] == net, (pin, net)

    def mega_pin(net):
        found = [pin for pin, value in mega.items() if value == net]
        assert len(found) == 1, (net, found)
        return found[0]

    def teensy_pin(net):
        found = [part['pin_names'][pin] for ref, part in parts.items() if ref in ('JT1', 'JT2')
                 for pin, value in part['pins'].items() if value == net]
        assert len(found) == 1, (net, found)
        pin = int(found[0])
        analogue = pin - 14 if 14 <= pin <= 27 else pin - 24 if pin in (38, 39) else None
        return f'{pin} / A{analogue}' if analogue is not None else str(pin)

    inputs = []
    outputs = []
    for body in BODIES:
        inputs.append(dict(signal=body + '/microphone', kind='mic',
                           mega=mega_pin(body + '/analyser out'),
                           teensy=teensy_pin(body + '/mic direct'),
                           mega_path='DFRobot MSGEQ7 → analyser out',
                           teensy_path='4.7K series · 1M to AGND · 1nF to GND'))
    photos = [body + '/photosensor' + suffix for body in BODIES
              for suffix in (('',) if body.startswith('female') else ('/A', '/B', '/C', '/D'))]
    for net in photos:
        dividers = [c for ref, c in parts.items() if ref.startswith('RA') and c['pins']['1'] == net]
        assert len(dividers) == 1, net
        inputs.append(dict(signal=net, kind='photo', mega=mega_pin(net),
                           teensy=teensy_pin(dividers[0]['pins']['2']),
                           mega_path='backplane · 10K load',
                           teensy_path='100K / 150K divider · 10nF at pin'))
    nets = [(body + '/tone', 'tone') for body in BODIES]
    nets += [(body + '/neopixel/driven', 'pixel') for body in BODIES]
    nets += [(body + '/bar neopixel/driven', 'pixel') for body in BODIES[3:]]
    nets += [(body + '/aux driven', 'control') for body in BODIES[3:]]
    nets += [('amp shutdown', 'control')]
    for net, kind in nets:
        channels = [c['pins'][a] for ref, c in parts.items() if ref in ('U1', 'U2', 'U3', 'U4')
                    for a, y in (('2', '3'), ('5', '6'), ('9', '8'), ('12', '11')) if c['pins'].get(y) == net]
        assert len(channels) == 1, net
        path = 'RC voice card → body line out' if kind == 'tone' else '330R series' if net != 'amp shutdown' else 'reserved · 10K pull-up to USB 5V'
        signal = net.replace('/driven', '').replace('/aux driven', '/aux')
        outputs.append(dict(signal=signal, kind=kind, mega=mega_pin(net),
                            teensy=teensy_pin(channels[0]), mega_path=path,
                            teensy_path='3.3V → 5V translator · ' + path))
    for net in ('analyser/reset', 'analyser/strobe'):
        outputs.append(dict(signal=net, kind='control', mega=mega_pin(net), teensy='—',
                            mega_path='MSGEQ7 carrier · shared by five modules',
                            teensy_path='analyser slot empty · no connection'))
    return inputs, outputs


def render(processor, inputs, outputs):
    """A shared signal rectangle with the processor's pins in its centre."""
    title = 'Arduino Mega 2560' if processor == 'mega' else 'Teensy 4.1'
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1160" viewBox="0 0 1800 1160" role="img" aria-labelledby="title desc">',
           f'<title id="title">{title}: shield signal pinout</title>',
           '<desc id="desc">Signal origins on the left, processor pins in the middle, signal destinations on the right. Matching rows compare the Mega and Teensy configurations.</desc>',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 Z" fill="context-stroke"/></marker></defs>',
           '<rect width="1800" height="1160" fill="#fff"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#243343}.signal{font-family:Consolas,monospace;font-size:17px}.path{font-size:14px}.pin{font-family:Consolas,monospace;font-size:21px;font-weight:bold}</style>']

    def text(x, y, value, size=17, anchor='start', cls='', colour=None):
        colour = f' style="fill:{colour}"' if colour else ''
        svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" class="{cls}"{colour}>{escape(value)}</text>')

    text(35, 48, title + ' · signal connections', 32)
    text(35, 79, 'SHIELDS configuration · matching signal order in both diagrams · functional pinout', 18)
    svg += ['<rect x="20" y="105" width="1760" height="860" rx="10" fill="#f8fafc" stroke="#93a4b5" stroke-width="2"/>',
            '<rect x="760" y="205" width="280" height="725" rx="9" fill="#eaf0f6" stroke="#354e68" stroke-width="2"/>']
    text(35, 145, 'INPUTS · origin', 20)
    text(900, 145, title, 23, 'middle')
    text(1765, 145, 'OUTPUTS · destination', 20, 'end')
    text(565, 185, 'signal path into processor', 16, 'middle')
    text(900, 185, 'PROCESSOR PINS', 16, 'middle')
    text(1225, 185, 'signal path out of processor', 16, 'middle')

    for side, rows in (('in', inputs), ('out', outputs)):
        for i, row in enumerate(rows):
            y = 250 + i * 40
            colour = COLOURS[row['kind']] if row[processor] != '—' else '#7f8c99'
            if side == 'in':
                text(35, y + 6, row['signal'], cls='signal', colour=colour)
                start, end = 340, 760
                text(781, y + 7, row[processor], cls='pin')
            else:
                text(1440, y + 6, row['signal'], cls='signal', colour=colour)
                start, end = 1040, 1420
                text(1019, y + 7, row[processor], anchor='end', cls='pin')
            dashed = ' stroke-dasharray="5 5"' if row[processor] == '—' else ''
            svg.append(f'<path d="M{start},{y} H{end}" fill="none" stroke="{colour}" stroke-width="2" marker-end="url(#arrow)"{dashed}/>')
            svg.append(f'<circle cx="{760 if side == "in" else 1040}" cy="{y}" r="4" fill="{colour}"/>')
            text((start + end) / 2, y - 9, row[processor + '_path'], cls='path', anchor='middle', colour=colour)
    text(35, 1004, 'Microphones', 18)
    if processor == 'mega':
        text(200, 1004, 'A0–A4 read the MSGEQ7 band outputs. Direct microphone taps also reach D26–D30, unused by firmware 4.', 17)
        power = 'USB supplies MEGA_5V. Analogue reference: 5V. The Mega itself is the computing shield.'
    else:
        text(200, 1004, 'Pins 14–18 / A0–A4 read raw microphone signals. MSGEQ7 band outputs and reset/strobe have no adapter connection.', 17)
        power = 'USB supplies VIN; Teensy logic/ADC: 3.3V. MEGA_5V reaches the backplane through the adapter Schottky diode.'
    text(35, 1044, 'Power / return', 18)
    text(200, 1044, power, 17)
    text(35, 1084, 'Shared wiring', 18)
    text(200, 1084, 'Backplane GND/AGND bond; five RC voice cards; the same harness signals. Dynamixel communication uses the separate U2D2.', 17)
    text(35, 1124, 'Pin numbers are processor labels. Signal lines show conditioning along the route; connector positions are in the PCB drawings.', 16)
    svg.append('</svg>')
    return '\n'.join(svg) + '\n'


def write():
    inputs, outputs = connections()
    STATIC.mkdir(parents=True, exist_ok=True)
    paths = []
    for processor in ('mega', 'teensy'):
        path = STATIC / f'shields-{processor}-pinout.svg'
        path.write_text(render(processor, inputs, outputs), encoding='utf-8')
        paths.append(path)
    return paths
