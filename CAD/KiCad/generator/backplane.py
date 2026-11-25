"""TJ Backplane: 12V / 5V splitter for up to 7 TJ Brain boards (+ USB hub supply).

USB is split by a commercial 7-port powered USB 2.0 hub mounted next to this board
(one USB cable per brain board, straight into the Teensy micro-USB); this board powers
that hub from its own fused 5V output.
"""
from design import Design, FP

FP['MKDS2'] = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
FP['MKDS4'] = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal'
FP['PTC500'] = 'Fuse:Fuse_Bourns_MF-RHT500'

D = Design('tj_backplane', 'TJ Backplane - 12V / 5V / USB-hub power splitter')
REV = 'A'
OUTPUTS = ['F1', 'F2', 'F3', 'M1', 'M2', 'BAR', 'SPARE']

D.sheet('inputs', 'Power inputs',
        '12V PSU (Dynamixels, <=10A) and 5V PSU (NeoPixels + logic, <=25A, two terminal poles in parallel). '
        'Order the PCB with 2 oz copper. TVS + bulk capacitance on both rails.')
D.group('12V input')
D.add('J1', 'Connector_Generic:Conn_01x02', '12V IN', 'MKDS2', {1: '+12V', 2: 'GND'}, silk='12V IN')
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: '+12V'})
D.add('D?', 'Device:D_Zener', 'SMBJ15A', 'SMB', {1: '+12V', 2: 'GND'}, desc='TVS 15V unidirectional')
D.CP('470u 25V', '+12V', 'GND')
D.led_to_gnd('+12V', '10k', 'red', '12V')
D.group('5V input')
D.add('J2', 'Connector_Generic:Conn_01x04', '5V IN', 'MKDS4', {1: '+5V', 2: '+5V', 3: 'GND', 4: 'GND'}, silk='5V IN')
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: '+5V'})
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: 'GND'})
D.add('D?', 'Device:D_Zener', 'SMBJ5.0A', 'SMB', {1: '+5V', 2: 'GND'}, desc='TVS 5V unidirectional')
D.CP('1000u 10V', '+5V', 'GND')
D.led_to_gnd('+5V', '2k2', 'green', '5V')
D.group('USB hub supply (5V, 2A PTC)')
D.add('F?', 'Device:Polyfuse', 'MF-RHT300 3A', 'PTC300', {1: '+5V', 2: '+5V_HUB'})
D.add('J3', 'Connector_Generic:Conn_01x02', 'HUB 5V OUT', 'MKDS2', {1: '+5V_HUB', 2: 'GND'}, silk='HUB 5V')
D.led_to_gnd('+5V_HUB', '2k2', 'green', 'HUB')
D.group('Test points & mounting')
D.add('TP?', 'Connector:TestPoint', 'GND', 'TPLOOP', {1: 'GND'}, silk='GND')
D.add('TP?', 'Connector:TestPoint', '+12V', 'TP', {1: '+12V'}, silk='12V')
D.add('TP?', 'Connector:TestPoint', '+5V', 'TP', {1: '+5V'}, silk='5V')
for i in range(4):
    D.add('H?', 'Mechanical:MountingHole_Pad', 'M3', 'MH', {1: 'GND'})

D.sheet('outputs', 'Brain board outputs (x7)',
        'Each output: Mini-Fit Jr 4p (1 = +12V, 2 = +5V, 3/4 = GND, same as TJ Brain J1, cable wired pin-to-pin), '
        'resettable fuses 3A (12V) and 5A (5V), one LED per rail after its fuse (LED off = fuse tripped).')
for k, name in enumerate(OUTPUTS, start=1):
    D.group('Output %d (%s)' % (k, name))
    D.add('F?', 'Device:Polyfuse', 'MF-RHT300 3A', 'PTC300', {1: '+12V', 2: '+12V_%s' % name})
    D.add('F?', 'Device:Polyfuse', 'MF-RHT500 5A', 'PTC500', {1: '+5V', 2: '+5V_%s' % name})
    D.add('J?', 'Connector_Generic:Conn_02x02_Top_Bottom', 'OUT %s' % name, 'MINIFIT4',
          {1: '+12V_%s' % name, 2: '+5V_%s' % name, 3: 'GND', 4: 'GND'}, silk=name,
          mpn='Molex 39-30-1040 (5566-04A)')
    D.led_to_gnd('+12V_%s' % name, '10k', 'red', '12V %s' % name)
    D.led_to_gnd('+5V_%s' % name, '2k2', 'green', '5V %s' % name)

if __name__ == '__main__':
    print(len(D.parts), 'parts', len(D.nets()), 'nets', D.check())
