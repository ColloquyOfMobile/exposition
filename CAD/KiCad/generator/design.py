"""Minimal design-description DSL shared by schematic and PCB generators."""
import collections
import uuid as _uuid

FP = {
    'R': 'Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder',
    'R1206': 'Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder',
    'C': 'Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder',
    'C1206': 'Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder',
    'CP10': 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',
    'LED': 'LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder',
    'SOD323': 'Diode_SMD:D_SOD-323_HandSoldering',
    'SOD123': 'Diode_SMD:D_SOD-123',
    'SMB': 'Diode_SMD:D_SMB',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'SOT23-5': 'Package_TO_SOT_SMD:SOT-23-5_HandSoldering',
    'SOIC14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    'DIP8S': 'Package_DIP:DIP-8_W7.62mm_Socket',
    'TRIM': 'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical',
    'JST_EH3': 'Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical',
    'JST_XH3': 'Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical',
    'JST_XH2': 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical',
    'MSTB2': 'Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal',
    'MSTB3': 'Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_3-G-5,08_1x03_P5.08mm_Horizontal',
    'MINIFIT4': 'Connector_Molex:Molex_Mini-Fit_Jr_5566-04A_2x02_P4.20mm_Vertical',
    'MINIFIT4H': 'Connector_Molex:Molex_Mini-Fit_Jr_5569-04A1_2x02_P4.20mm_Horizontal',
    'HDR1x1': 'Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical',
    'HDR1x4': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    'HDR2x5': 'Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical',
    'SJ2': 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm',
    'SJ3': 'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm',
    'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'TPLOOP': 'TestPoint:TestPoint_Keystone_5005-5009_Compact',
    'MH': 'MountingHole:MountingHole_3.2mm_M3_Pad_Via',
    'DSUB15': 'Connector_Dsub:DSUB-15_Male_Horizontal_P2.77x2.84mm_EdgePinOffset4.94mm_Housed_MountingHolesOffset7.48mm',
    'DIPSW4': 'Button_Switch_THT:SW_DIP_SPSTx04_Slide_9.78x12.34mm_W7.62mm_P2.54mm',
    'PTC300': 'Fuse:Fuse_Bourns_MF-RHT300',
    'PTC400': 'Fuse:Fuse_Bourns_MF-RHT400',
}

POWER_NETS = {'GND': 'power:GND', '+5V': 'power:+5V', '+12V': 'power:+12V', '+3V3': 'power:+3V3'}


class Part:
    def __init__(self, ref, lib_id, value, footprint, pins, sheet, group, **kw):
        self.ref = ref
        self.lib_id = lib_id
        self.value = value
        self.footprint = FP.get(footprint, footprint)
        self.pins = dict(pins)          # pin number(str) -> net name or None (no connect)
        self.sheet = sheet
        self.group = group
        self.uuid = str(_uuid.uuid4())
        self.fields = kw.get('fields', {})
        self.silk = kw.get('silk')       # extra silkscreen label on PCB
        self.rot = kw.get('rot', None)   # schematic rotation override
        self.dnp = kw.get('dnp', False)
        self.mpn = kw.get('mpn', '')
        self.desc = kw.get('desc', '')


class Design:
    def __init__(self, name, title):
        self.name = name
        self.title = title
        self.parts = []
        self.sheets = collections.OrderedDict()   # key -> (title, description)
        self._count = collections.Counter()
        self._group = None
        self._sheet = None

    def sheet(self, key, title, description=''):
        self.sheets[key] = (title, description)
        self._sheet = key

    def group(self, name):
        self._group = name

    def next_ref(self, prefix):
        used = {p.ref for p in self.parts}
        while True:
            self._count[prefix] += 1
            ref = '%s%d' % (prefix, self._count[prefix])
            if ref not in used:
                return ref

    def add(self, ref, lib_id, value, footprint, pins, **kw):
        if ref.endswith('?'):
            ref = self.next_ref(ref[:-1])
        pins = {str(k): v for k, v in pins.items()}
        p = Part(ref, lib_id, value, footprint, pins, self._sheet, self._group, **kw)
        assert ref not in [q.ref for q in self.parts], ref
        self.parts.append(p)
        return p

    # convenience helpers -------------------------------------------------
    def R(self, value, a, b, fp='R', **kw):
        return self.add('R?', 'Device:R', value, fp, {1: a, 2: b}, **kw)

    def C(self, value, a, b, fp='C', **kw):
        return self.add('C?', 'Device:C', value, fp, {1: a, 2: b}, **kw)

    def CP(self, value, plus, minus, fp='CP10', **kw):
        return self.add('C?', 'Device:C_Polarized', value, fp, {1: plus, 2: minus}, **kw)

    def LED(self, color, anode, cathode, **kw):
        return self.add('D?', 'Device:LED', color, 'LED', {1: cathode, 2: anode}, **kw)

    def led_to_gnd(self, src, rvalue, color, label, mid=None):
        """src -> R -> LED -> GND ; returns (R, LED)."""
        mid = mid or 'LED_%s_A' % label.replace(' ', '_').replace('+', 'P').replace('.', '')
        r = self.R(rvalue, src, mid)
        d = self.LED(color, mid, 'GND', silk=label)
        return r, d

    def nets(self):
        n = collections.defaultdict(list)
        for p in self.parts:
            for pin, net in p.pins.items():
                if net:
                    n[net].append((p.ref, pin))
        return n

    def check(self):
        bad = []
        for net, nodes in self.nets().items():
            if len(nodes) < 2:
                bad.append((net, nodes))
        return bad
