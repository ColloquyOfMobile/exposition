"""Generate the project-local 'TJ' symbol and footprint libraries (KiCad 7 format)."""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIR = os.path.join(HERE, '..', 'tj_library')

# ----------------------------------------------------------------- Teensy 4.1
# Physical pin order (top view, USB at top), DIP-style numbering 1..48.
TEENSY_LEFT = ['GND', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '3V3',
               '24', '25', '26', '27', '28', '29', '30', '31', '32']
TEENSY_RIGHT_TOP_DOWN = ['VIN', 'GND', '3V3', '23', '22', '21', '20', '19', '18', '17', '16', '15', '14',
                         '13', 'GND', '41', '40', '39', '38', '37', '36', '35', '34', '33']
ALT = {
    '0': 'RX1', '1': 'TX1', '7': 'RX2', '8': 'TX2', '10': 'MQSR', '11': 'MOSI', '12': 'MQSL',
    '13': 'SCK/LED', '14': 'A0/TX3', '15': 'A1/RX3', '16': 'A2/RX4', '17': 'A3/TX4', '18': 'A4/SDA',
    '19': 'A5/SCL', '20': 'A6/TX5', '21': 'A7/RX5', '22': 'A8', '23': 'A9', '24': 'A10/TX6',
    '25': 'A11/RX6', '26': 'A12', '27': 'A13', '28': 'RX7', '29': 'TX7', '34': 'RX8', '35': 'TX8',
    '38': 'A14', '39': 'A15', '40': 'A16', '41': 'A17',
}


def teensy_pins():
    """Return list of (number, name, side, index) ; number = DIP position."""
    out = []
    for i, n in enumerate(TEENSY_LEFT):
        out.append((i + 1, n, 'L', i))
    for i, n in enumerate(TEENSY_RIGHT_TOP_DOWN):
        out.append((48 - i, n, 'R', i))
    return out


def pin_label(n):
    if n in ('GND', 'VIN', '3V3'):
        return n
    return 'D' + n + ('/' + ALT[n] if n in ALT else '')


def pin_type(n):
    return {'GND': 'power_in', 'VIN': 'power_in', '3V3': 'power_out'}.get(n, 'bidirectional')


def sym_pin(ptype, x, y, ang, name, number, length=2.54, hide=False):
    return ('      (pin %s line (at %g %g %d) (length %g)%s\n'
            '        (name "%s" (effects (font (size 1.27 1.27))))\n'
            '        (number "%s" (effects (font (size 1.27 1.27))))\n'
            '      )\n') % (ptype, x, y, ang, length, ' hide' if hide else '', name, number)


def prop(name, val, x, y, hide=False, justify=None):
    j = ' (justify %s)' % justify if justify else ''
    return ('    (property "%s" "%s" (at %g %g 0)\n      (effects (font (size 1.27 1.27))%s%s)\n    )\n'
            % (name, val, x, y, j, ' hide' if hide else ''))


def teensy_symbol():
    w = 12.7  # half width of body
    top = 31.75
    s = '  (symbol "Teensy4.1" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n'
    s += prop('Reference', 'U', -w, top + 2.54, justify='left')
    s += prop('Value', 'Teensy4.1', w, top + 2.54, justify='right')
    s += prop('Footprint', 'TJ:Teensy41_Socket', 0, 0, True)
    s += prop('Datasheet', 'https://www.pjrc.com/store/teensy41.html', 0, 0, True)
    s += prop('ki_description', 'PJRC Teensy 4.1 module (outer 2x24 pins, plugged into female headers)', 0, 0, True)
    s += '    (symbol "Teensy4.1_0_1"\n'
    s += ('      (rectangle (start %g %g) (end %g %g) (stroke (width 0.254) (type default)) '
          '(fill (type background)))\n') % (-w, top, w, -top)
    s += ('      (text "USB" (at 0 %g 0) (effects (font (size 1.27 1.27))))\n') % (top - 2.0)
    s += '    )\n    (symbol "Teensy4.1_1_1"\n'
    for num, n, side, idx in teensy_pins():
        y = top - 3.81 - idx * 2.54
        if side == 'L':
            s += sym_pin(pin_type(n), -w - 5.08, y, 0, pin_label(n), num, 5.08)
        else:
            s += sym_pin(pin_type(n), w + 5.08, y, 180, pin_label(n), num, 5.08)
    s += '    )\n  )\n'
    return s


AMP_PINS = [(1, 'OUT+', 'output'), (2, 'OUT-', 'output'), (3, 'PWR-', 'power_in'), (4, 'PWR+', 'power_in'),
            (5, 'SD(set)', 'input'), (6, 'IN+', 'input'), (7, 'IN-', 'input'), (8, 'VOL-', 'passive'),
            (9, 'VOL_SET', 'passive'), (10, 'VOL+', 'passive')]


def amp_symbol():
    s = '  (symbol "SparkFun_TPA2005D1_Breakout" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)\n'
    s += prop('Reference', 'U', -7.62, 10.16, justify='left')
    s += prop('Value', 'SparkFun BOB-11044 (TPA2005D1)', -7.62, -10.16, justify='left')
    s += prop('Footprint', 'TJ:SparkFun_TPA2005D1_Breakout', 0, 0, True)
    s += prop('Datasheet', 'https://www.sparkfun.com/products/11044', 0, 0, True)
    s += prop('ki_description', 'SparkFun mono class-D audio amplifier breakout (TPA2005D1), plugged on 0.1in headers', 0, 0, True)
    s += '    (symbol "SparkFun_TPA2005D1_Breakout_0_1"\n'
    s += '      (rectangle (start -7.62 8.89) (end 7.62 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))\n'
    s += '    )\n    (symbol "SparkFun_TPA2005D1_Breakout_1_1"\n'
    left = [6, 7, 5, 4, 3]
    right = [1, 2, 10, 9, 8]
    names = {p[0]: p for p in AMP_PINS}
    for i, n in enumerate(left):
        s += sym_pin(names[n][2], -12.7, 5.08 - i * 2.54, 0, names[n][1], n, 5.08)
    for i, n in enumerate(right):
        s += sym_pin(names[n][2], 12.7, 5.08 - i * 2.54, 180, names[n][1], n, 5.08)
    s += '    )\n  )\n'
    return s


def write_symbols():
    os.makedirs(LIBDIR, exist_ok=True)
    txt = '(kicad_symbol_lib (version 20220914) (generator tj_brain_generator)\n'
    txt += teensy_symbol() + amp_symbol() + ')\n'
    open(os.path.join(LIBDIR, 'TJ.kicad_sym'), 'w').write(txt)


# ----------------------------------------------------------------- footprints
def tid():
    return str(uuid.uuid4())


def fp_line(x1, y1, x2, y2, layer, w):
    return '  (fp_line (start %g %g) (end %g %g) (stroke (width %g) (type solid)) (layer "%s") (tstamp %s))\n' % (
        x1, y1, x2, y2, w, layer, tid())


def fp_rect(x1, y1, x2, y2, layer, w):
    return (fp_line(x1, y1, x2, y1, layer, w) + fp_line(x2, y1, x2, y2, layer, w) +
            fp_line(x2, y2, x1, y2, layer, w) + fp_line(x1, y2, x1, y1, layer, w))


def fp_text(kind, text, x, y, layer, size=1.0, hide=False):
    return ('  (fp_text %s "%s" (at %g %g) (layer "%s")%s\n    (effects (font (size %g %g) (thickness %g)))\n'
            '    (tstamp %s)\n  )\n') % (kind, text, x, y, layer, ' hide' if hide else '', size, size, size * 0.15, tid())


def thpad(num, x, y, shape='circle', size=1.7, drill=1.0):
    return ('  (pad "%s" thru_hole %s (at %g %g) (size %g %g) (drill %g) (layers "*.Cu" "*.Mask") (tstamp %s))\n'
            % (num, shape, x, y, size, size, drill, tid()))


def teensy_fp():
    s = '(footprint "Teensy41_Socket" (version 20221018) (generator tj_brain_generator)\n  (layer "F.Cu")\n'
    s += '  (descr "PJRC Teensy 4.1 on two 1x24 female headers (0.6in row spacing). Pad 1 = GND next to USB.")\n'
    s += '  (tags "Teensy 4.1 PJRC")\n  (attr through_hole)\n'
    s += fp_text('reference', 'REF**', 7.62, -4.2, 'F.SilkS')
    s += fp_text('value', 'Teensy4.1', 7.62, 30, 'F.Fab')
    # board outline 17.78 x 60.96, pins rows at x=0 and 15.24, first pin 1.27 from top edge
    x1, x2, y1, y2 = -1.27, 16.51, -1.27, 59.69
    s += fp_rect(x1, y1, x2, y2, 'F.Fab', 0.1)
    s += fp_rect(x1 - 0.15, y1 - 0.15, x2 + 0.15, y2 + 0.15, 'F.SilkS', 0.15)
    # micro USB overhang
    s += fp_rect(4.12, -2.5, 11.12, 3.0, 'F.Fab', 0.1)
    s += fp_rect(x1 - 0.5, -3.0, x2 + 0.5, y2 + 0.5, 'F.CrtYd', 0.05)
    s += fp_text('user', 'USB', 7.62, 1.0, 'F.SilkS', 1.0)
    s += fp_text('user', 'TEENSY 4.1', 7.62, 29.0, 'F.SilkS', 1.5)
    s += fp_line(-1.27 - 0.6, -0.6, -1.27 - 0.6, 0.6, 'F.SilkS', 0.3)
    from make_lib import teensy_pins
    for num, n, side, idx in teensy_pins():
        x = 0 if side == 'L' else 15.24
        y = idx * 2.54
        s += thpad(num, x, y, 'rect' if num == 1 else 'circle')
    s += ')\n'
    return s


def amp_fp():
    s = '(footprint "SparkFun_TPA2005D1_Breakout" (version 20221018) (generator tj_brain_generator)\n  (layer "F.Cu")\n'
    s += '  (descr "SparkFun Mono Audio Amp Breakout BOB-11044 (TPA2005D1), same geometry as ZKM electronic box custom1 footprint")\n'
    s += '  (tags "TPA2005D1 SparkFun amplifier breakout")\n  (attr through_hole)\n'
    s += fp_text('reference', 'REF**', 8.89, -20.6, 'F.SilkS')
    s += fp_text('value', 'TPA2005D1_breakout', 8.89, 2.8, 'F.Fab')
    s += fp_rect(-1, -19, 19, 1, 'F.SilkS', 0.15)
    s += fp_rect(-1, -19, 19, 1, 'F.Fab', 0.1)
    s += fp_rect(-2, -20, 20, 2, 'F.CrtYd', 0.05)
    labels = {1: 'OUT+', 2: 'OUT-', 3: 'GND', 4: '5V', 5: 'SD', 6: 'IN+', 7: 'IN-', 8: 'V-', 9: 'VW', 10: 'V+'}
    lp = [(1, 0, -15.24), (2, 0, -12.7), (3, 0, -5.08), (4, 0, -2.54), (5, 0, 0),
          (6, 17.78, -15.24), (7, 17.78, -12.7), (8, 17.78, -5.08), (9, 17.78, -2.54), (10, 17.78, 0)]
    for n, x, y in lp:
        s += thpad(n, x, y, 'rect' if n == 1 else 'circle')
        s += fp_text('user', labels[n], x + (2.6 if x == 0 else -2.6), y, 'F.Fab', 0.6)
    for x, y in [(0, -17.78), (0, -10.16), (0, -7.62), (17.78, -17.78), (17.78, -10.16), (17.78, -7.62)]:
        s += thpad('', x, y)
    s += fp_text('user', 'AMP', 8.89, -9, 'F.SilkS', 1.5)
    s += ')\n'
    return s


def write_footprints():
    d = os.path.join(LIBDIR, 'TJ.pretty')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'Teensy41_Socket.kicad_mod'), 'w').write(teensy_fp())
    open(os.path.join(d, 'SparkFun_TPA2005D1_Breakout.kicad_mod'), 'w').write(amp_fp())


if __name__ == '__main__':
    write_symbols()
    write_footprints()
    print('library written to', os.path.abspath(LIBDIR))
