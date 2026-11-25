"""TJ Brain board: one Teensy 4.1 brain per unit (female / male / bar).

Electrical description consumed by schgen.py (schematic) and pcbgen.py (layout).
"""
from design import Design

D = Design('tj_brain', 'TJ Brain - Teensy 4.1 unit controller')
REV = 'A'

# =========================================================================== POWER
D.sheet('power', 'Power input & protection',
        'Backplane cable (Molex Mini-Fit Jr 4p): +12V / +5V / GND. TVS, bulk caps, '
        'PTC-protected body supply, rail LEDs.')
D.group('Backplane power input')
D.add('J1', 'Connector_Generic:Conn_02x02_Top_Bottom', 'PWR IN Mini-Fit Jr', 'MINIFIT4H',
      {1: '+12V', 2: '+5V', 3: 'GND', 4: 'GND'}, silk='PWR IN 12V/5V', mpn='Molex 39-30-1041 (5569-04A1, right angle)')
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: '+12V'})
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: '+5V'})
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: 'GND'})
D.group('12V rail')
D.add('D?', 'Device:D_Zener', 'SMBJ15A', 'SMB', {1: '+12V', 2: 'GND'}, desc='TVS 15V unidirectional')
D.CP('470u 25V', '+12V', 'GND')
D.C('100n', '+12V', 'GND', fp='C1206', fields={'Voltage': '25V'})
D.group('5V rail')
D.add('D?', 'Device:D_Zener', 'SMBJ5.0A', 'SMB', {1: '+5V', 2: 'GND'}, desc='TVS 5V unidirectional')
D.CP('1000u 10V', '+5V', 'GND')
D.C('100n', '+5V', 'GND')
D.group('Teensy supply (diode-OR safe with USB VBUS)')
D.add('D?', 'Device:D_Schottky', 'B5819W', 'SOD123', {1: '+5V_TEENSY', 2: '+5V'},
      desc='Schottky 1A 40V; lets the Teensy VIN/VUSB link stay uncut')
D.add('#FLG?', 'power:PWR_FLAG', 'PWR_FLAG', '', {1: '+5V_TEENSY'})
D.C('10u', '+5V_TEENSY', 'GND', fp='C1206', fields={'Voltage': '10V'})
D.group('Body (D-sub) supply, PTC protected')
D.add('F1', 'Device:Polyfuse', 'MF-RHT300 3A', 'PTC300', {1: '+12V', 2: '+12V_BODY'})
D.add('F2', 'Device:Polyfuse', 'MF-RHT400 4A', 'PTC400', {1: '+5V', 2: '+5V_BODY'})
D.group('Rail LEDs')
D.led_to_gnd('+12V', '10k', 'red', '12V')
D.led_to_gnd('+5V', '2k2', 'green', '5V')
D.led_to_gnd('+3V3', '1k', 'green', '3V3')
D.led_to_gnd('+12V_BODY', '10k', 'red', 'BODY 12V')
D.led_to_gnd('+5V_BODY', '2k2', 'green', 'BODY 5V')
D.group('Test points & mounting')
D.add('TP?', 'Connector:TestPoint', 'GND', 'TPLOOP', {1: 'GND'}, silk='GND')
D.add('TP?', 'Connector:TestPoint', 'GND', 'TPLOOP', {1: 'GND'}, silk='GND')
D.add('TP?', 'Connector:TestPoint', '+12V', 'TP', {1: '+12V'}, silk='12V')
D.add('TP?', 'Connector:TestPoint', '+5V', 'TP', {1: '+5V'}, silk='5V')
D.add('TP?', 'Connector:TestPoint', '+3V3', 'TP', {1: '+3V3'}, silk='3V3')
for i in range(4):
    D.add('H?', 'Mechanical:MountingHole_Pad', 'M3', 'MH', {1: 'GND'})

# =========================================================================== MCU
D.sheet('mcu', 'Teensy 4.1, unit ID, status LEDs, expansion',
        'Teensy plugs into 2x24 female headers. USB from the backplane hub goes straight into the '
        'Teensy micro-USB (strain relief holes next to it).')
T = {  # Teensy pin -> net
    '0': 'DXL_RX', '1': 'DXL_TX', '2': 'DXL_DIR', '3': 'STATE1_PWM', '4': 'STATE2_PWM', '5': 'AMP_EN',
    '6': 'ID0', '7': 'ID1', '8': 'NP1_3V', '9': 'EQ_STROBE', '10': 'EQ_RESET', '11': 'ID2', '12': 'AUDIO_PWM',
    '24': 'NP4_3V', '25': 'EXP_A11', '26': 'EXP_D26', '27': 'EXP_D27', '28': 'ID3', '29': 'NP2_3V',
    '30': 'LED_HB', '31': 'LED_HOST', '32': 'LED_ERR',
    '23': 'EXP_A9', '22': 'AUX_A', '21': 'EQ_OUT', '20': 'LS4_A', '19': 'SCL', '18': 'SDA', '17': 'LS3_A',
    '16': 'MIC_A', '15': 'LS2_A', '14': 'LS1_A', '13': None,
    '41': 'EXP_A17', '40': 'EXP_A16', '39': None, '38': None, '37': 'LED_USER', '36': None, '35': 'NP3_3V',
    '34': None, '33': None,
    'GND': 'GND', 'VIN': '+5V_TEENSY', '3V3': '+3V3',
}
from make_lib import teensy_pins
D.group('Teensy 4.1')
D.add('U1', 'TJ:Teensy4.1', 'Teensy 4.1', 'TJ:Teensy41_Socket',
      {num: T[n] for num, n, side, idx in teensy_pins()},
      mpn='PJRC Teensy 4.1 + 2x 1x24 female header 2.54mm', silk=None)
D.C('100n', '+3V3', 'GND')
D.group('Unit ID DIP switch (ON = 0)')
D.add('SW1', 'Switch:SW_DIP_x04', 'UNIT ID', 'DIPSW4',
      {1: 'ID0', 2: 'ID1', 3: 'ID2', 4: 'ID3', 5: 'GND', 6: 'GND', 7: 'GND', 8: 'GND'}, silk='UNIT ID')
D.group('Firmware status LEDs')
D.led_to_gnd('LED_HB', '1k', 'green', 'HEARTBEAT')
D.led_to_gnd('LED_HOST', '330', 'blue', 'HOST')
D.led_to_gnd('LED_ERR', '1k', 'red', 'ERROR')
D.led_to_gnd('LED_USER', '1k', 'yellow', 'USER')
D.group('Expansion header (I2C, analog, GPIO)')
D.add('J2', 'Connector_Generic:Conn_02x05_Odd_Even', 'EXPANSION', 'HDR2x5',
      {1: '+3V3', 2: '+5V', 3: 'SDA', 4: 'SCL', 5: 'EXP_A9', 6: 'EXP_A11', 7: 'EXP_D26', 8: 'EXP_D27',
       9: 'EXP_A16', 10: 'EXP_A17'}, silk='EXP')
D.R('2k2', 'SDA', '+3V3', dnp=True, desc='optional I2C pull-up')
D.R('2k2', 'SCL', '+3V3', dnp=True, desc='optional I2C pull-up')

# =========================================================================== DYNAMIXEL
D.sheet('dxl', 'Dynamixel TTL half-duplex bus',
        'Serial1 + DIR (Dynamixel2Arduino: Dynamixel2Arduino dxl(Serial1, 2)). '
        'TX buffer 74AHCT1G126 @5V (TTL input accepts 3.3V), RX buffer 74LVC1G125 @3.3V (5V tolerant).')
D.group('TX buffer (DIR=1 transmits)')
D.add('U2', '74xGxx:74AHCT1G126', '74AHCT1G126', 'SOT23-5',
      {1: 'DXL_DIR', 2: 'DXL_TX', 3: 'GND', 4: 'DXL_DATA', 5: '+5V'})
D.C('100n', '+5V', 'GND')
D.group('RX buffer (DIR=0 receives)')
D.add('U3', '74xGxx:74LVC1G125', '74LVC1G125', 'SOT23-5',
      {1: 'DXL_DIR', 2: 'DXL_DATA', 3: 'GND', 4: 'DXL_RX', 5: '+3V3'})
D.C('100n', '+3V3', 'GND')
D.group('Bias')
D.R('10k', 'DXL_DATA', '+5V', desc='bus pull-up (as ROBOTIS reference)')
D.R('10k', 'DXL_RX', '+3V3')
D.R('10k', 'DXL_DIR', 'GND', desc='default = receive')
D.group('Dynamixel X-series TTL ports (JST EH: GND, 12V, DATA)')
for i in (1, 2, 3):
    D.add('J?', 'Connector_Generic:Conn_01x03', 'DXL TTL %d' % i, 'JST_EH3',
          {1: 'GND', 2: '+12V', 3: 'DXL_DATA'}, silk='DXL%d' % i)
D.add('TP?', 'Connector:TestPoint', 'DXL_DATA', 'TP', {1: 'DXL_DATA'}, silk='DXL')

# =========================================================================== NEOPIXEL
D.sheet('neopixel', 'NeoPixel outputs (4 channels)',
        '3.3V -> 5V level shift with 74AHCT125. NP1 and NP2 are also on the body D-sub. '
        'Pins are WS2812Serial / OctoWS2811 capable (8, 29, 35, 24).')
D.group('Level shifter')
sh = {1: ('NP1', '1', '2', '3'), 2: ('NP2', '4', '5', '6'), 3: ('NP3', '10', '9', '8'), 4: ('NP4', '13', '12', '11')}
pins = {'14': '+5V', '7': 'GND'}
for u, (n, oe, a, y) in sh.items():
    pins[oe] = 'GND'
    pins[a] = n + '_3V'
    pins[y] = n + '_5V'
D.add('U4', '74xx:74LVC125', '74AHCT125', 'SOIC14', pins, desc='use 74AHCT125 (TTL thresholds @5V)')
D.C('100n', '+5V', 'GND')
for n in ('NP1', 'NP2', 'NP3', 'NP4'):
    D.group('%s output' % n)
    D.R('100k', n + '_3V', 'GND', desc='keeps strip quiet while Teensy boots')
    D.R('330', n + '_5V', n + '_OUT')
    D.add('J?', 'Connector_Generic:Conn_01x03', '%s 5V/DIN/GND' % n, 'MSTB3',
          {1: '+5V', 2: n + '_OUT', 3: 'GND'}, silk=n, mpn='Phoenix MSTBA 2,5/3-G-5,08 + MSTB 2,5/3-ST-5,08')

# =========================================================================== AUDIO
D.sheet('audio', 'Tone output, amplifier, microphone, MSGEQ7',
        'Tone filter after T. Erforth "Pask redesign": 2nd-order RC low-pass (R/C per unit band, see README), '
        'divider to amp level, SparkFun TPA2005D1 breakout or external amp module. '
        'Mic input clamped for the 3.3V ADC, optional MSGEQ7 analyser.')
D.group('2nd order low-pass (fit R/C for the unit band)')
D.R('1k2', 'AUDIO_PWM', 'AF1', fields={'Note': 'band table'})
D.C('150n', 'AF1', 'GND', fields={'Note': 'band table'})
D.R('1k2', 'AF1', 'AF2', fields={'Note': 'band table'})
D.C('150n', 'AF2', 'GND', fields={'Note': 'band table'})
D.group('Divider + coupling')
D.R('22k', 'AF2', 'AUDIO_LINE')
D.R('6k8', 'AUDIO_LINE', 'GND')
D.C('1u', 'AUDIO_LINE', 'AMP_IN', fp='C')
D.add('TP?', 'Connector:TestPoint', 'AUDIO', 'TP', {1: 'AMP_IN'}, silk='AUDIO')
D.group('Amplifier (SparkFun TPA2005D1 breakout)')
D.add('U5', 'TJ:SparkFun_TPA2005D1_Breakout', 'SparkFun BOB-11044', 'TJ:SparkFun_TPA2005D1_Breakout',
      {1: 'SPK+', 2: 'SPK-', 3: 'GND', 4: '+5V', 5: 'AMP_EN', 6: 'AMP_IN', 7: 'GND', 8: 'VOL_L', 9: 'VOL_W', 10: 'VOL_H'},
      silk='AMP')
D.add('RV1', 'Device:R_Potentiometer_Trim', '10k VOLUME', 'TRIM', {1: 'VOL_H', 2: 'VOL_W', 3: 'VOL_L'}, silk='VOL')
D.R('100k', 'AMP_EN', '+3V3', desc='amp enabled by default')
D.C('10u', '+5V', 'GND', fp='C1206', fields={'Voltage': '10V'})
D.group('External amp option (GF1002 near speaker)')
D.add('J?', 'Connector_Generic:Conn_01x04', 'EXT AMP', 'HDR1x4',
      {1: 'AMP_IN', 2: 'GND', 3: '+5V', 4: 'GND'}, silk='EXT AMP')
D.add('JP1', 'Jumper:SolderJumper_2_Open', 'LINE->SPK+', 'SJ2', {1: 'AMP_IN', 2: 'SPK+'},
      desc='close (and leave U5 out) to send line level on the D-sub speaker pins')
D.add('JP2', 'Jumper:SolderJumper_2_Open', 'GND->SPK-', 'SJ2', {1: 'GND', 2: 'SPK-'})
D.group('Speaker terminal')
D.add('J?', 'Connector_Generic:Conn_01x02', 'SPEAKER', 'MSTB2', {1: 'SPK+', 2: 'SPK-'}, silk='SPK')
D.group('Microphone input (MAX9814 module)')
D.add('J?', 'Connector_Generic:Conn_01x03', 'MIC VCC/GND/OUT', 'JST_XH3', {1: 'MIC_VCC', 2: 'GND', 3: 'MIC_IN'}, silk='MIC')
D.add('JP3', 'Jumper:SolderJumper_3_Bridged12', 'MIC VCC 5V|3V3', 'SJ3', {1: '+5V', 2: 'MIC_VCC', 3: '+3V3'})
D.R('1k', 'MIC_IN', 'MIC_A')
D.add('D?', 'Diode:BAT54S', 'BAT54S', 'SOT23', {1: 'GND', 2: '+3V3', 3: 'MIC_A'}, desc='clamp 0..3.3V')
D.C('1n', 'MIC_A', 'GND')
D.add('TP?', 'Connector:TestPoint', 'MIC', 'TP', {1: 'MIC_A'}, silk='MIC')
D.group('MSGEQ7 7-band analyser (optional, socketed)')
D.add('U6', 'Audio:MSGEQ7', 'MSGEQ7', 'DIP8S',
      {1: '+3V3', 2: 'GND', 3: 'EQ_OUT', 4: 'EQ_STROBE', 5: 'EQ_IN', 6: 'EQ_GREF', 7: 'EQ_RESET', 8: 'EQ_CK'})
D.C('100n', '+3V3', 'GND')
D.C('100n', 'EQ_GREF', 'GND')
D.C('10n', 'MIC_A', 'EQ_INC')
D.R('22k', 'EQ_INC', 'EQ_IN')
D.R('200k', '+3V3', 'EQ_CK')
D.C('33p', 'EQ_CK', 'GND')

# =========================================================================== SENSORS
D.sheet('sensors', 'Light sensors, comparator LEDs, AUX input',
        'Sensor modules may output 0..5V: 10k/18k divider keeps the ADC below 3.3V. '
        'LM339 lights an LED when a sensor is above its trimmer threshold (aiming aid).')
D.group('Sensor supply select')
D.add('JP4', 'Jumper:SolderJumper_3_Bridged12', 'LS VCC 5V|3V3', 'SJ3', {1: '+5V', 2: 'LS_VCC', 3: '+3V3'})
D.group('Comparator')
lm = {1: ('2', '4', '5'), 2: ('1', '6', '7'), 3: ('13', '10', '11'), 4: ('14', '8', '9')}  # out, -, +
pins = {'3': '+5V', '12': 'GND'}
for n, (o, m, p) in lm.items():
    pins[m] = 'LS%d_A' % n
    pins[p] = 'LS%d_TH' % n
    pins[o] = 'LS%d_LED' % n
D.add('U7', 'Comparator:LM339', 'LM339', 'SOIC14', pins)
D.C('100n', '+5V', 'GND')
for n in (1, 2, 3, 4):
    D.group('Light sensor %d' % n)
    D.add('J?', 'Connector_Generic:Conn_01x03', 'LS%d VCC/GND/SIG' % n, 'JST_XH3',
          {1: 'LS_VCC', 2: 'GND', 3: 'LS%d_IN' % n}, silk='LS%d' % n)
    D.R('10k', 'LS%d_IN' % n, 'LS%d_A' % n)
    D.R('18k', 'LS%d_A' % n, 'GND')
    D.C('10n', 'LS%d_A' % n, 'GND')
    D.add('RV?', 'Device:R_Potentiometer_Trim', '10k', 'TRIM', {1: '+3V3', 2: 'LS%d_TH' % n, 3: 'GND'}, silk='TH%d' % n)
    D.R('2k2', '+5V', 'LS%d_LEDA' % n)
    D.LED('white', 'LS%d_LEDA' % n, 'LS%d_LED' % n, silk='LIGHT%d' % n)
D.group('AUX analog input (D-sub pin 11)')
D.R('1k', 'AUX_IN', 'AUX_A')
D.add('D?', 'Diode:BAT54S', 'BAT54S', 'SOT23', {1: 'GND', 2: '+3V3', 3: 'AUX_A'})
D.C('10n', 'AUX_A', 'GND')
D.add('TP?', 'Connector:TestPoint', 'AUX', 'TP', {1: 'AUX_IN'}, silk='AUX')

# =========================================================================== OUTPUTS
D.sheet('outputs', 'State LED high-side drivers',
        'Same topology as the 2018 / electronic-box "state LED" (backlight KWB-R8445W): switched +5V '
        'through 150R to the LED, cathode to GND in the body. PWM capable.')
for n in (1, 2):
    D.group('State output %d' % n)
    D.R('100', 'STATE%d_PWM' % n, 'STATE%d_G' % n)
    D.R('100k', 'STATE%d_G' % n, 'GND')
    D.add('Q?', 'Transistor_FET:2N7002', '2N7002', 'SOT23', {1: 'STATE%d_G' % n, 2: 'GND', 3: 'STATE%d_PG' % n})
    D.R('10k', '+5V', 'STATE%d_PG' % n)
    D.add('Q?', 'Transistor_FET:AO3401A', 'AO3401A', 'SOT23', {1: 'STATE%d_PG' % n, 2: '+5V', 3: 'STATE%d_HI' % n})
    D.R('150', 'STATE%d_HI' % n, 'STATE%d_OUT' % n, fp='R1206', desc='LED current limit (0R for self-limited loads)')
    D.led_to_gnd('STATE%d_HI' % n, '2k2', 'yellow', 'STATE%d' % n)
    D.add('J?', 'Connector_Generic:Conn_01x02', 'STATE%d OUT/GND' % n, 'JST_XH2',
          {1: 'STATE%d_OUT' % n, 2: 'GND'}, silk='STATE%d' % n)

# =========================================================================== INDICATORS
D.sheet('indicators', 'Signal activity LEDs',
        'Each signal is tapped through 1k + Schottky into 47n || 1M (~50 ms pulse stretcher) and drives a '
        '74HC14 (3.3V) so that short NeoPixel / Dynamixel bursts are visible. PROBE = free logic probe.')
ch = [('NP1_3V', 'NP1', 'H'), ('NP2_3V', 'NP2', 'H'), ('NP3_3V', 'NP3', 'H'), ('NP4_3V', 'NP4', 'H'),
      ('DXL_DIR', 'DXL TX', 'H'), ('DXL_RX', 'DXL BUS', 'L'), ('AUDIO_PWM', 'TONE', 'H'), ('PROBE', 'PROBE', 'H')]
hc_units = [('1', '2'), ('3', '4'), ('5', '6'), ('9', '8'), ('11', '10'), ('13', '12')]  # (in, out)
u8 = {'14': '+3V3', '7': 'GND'}
u9 = {'14': '+3V3', '7': 'GND'}
for i, (sig, label, mode) in enumerate(ch):
    u = u8 if i < 6 else u9
    a, y = hc_units[i % 6]
    s = 'IND%d_S' % (i + 1)
    u[a] = s
    u[y] = 'IND%d_Y' % (i + 1)
for k in range(2, 6):          # unused gates of U9: input to GND, output NC
    a, y = hc_units[k]
    u9[a] = 'GND'
    u9[y] = None
D.group('Schmitt inverters')
D.add('U8', '74xx:74HC14', '74HC14', 'SOIC14', u8)
D.add('U9', '74xx:74HC14', '74HC14', 'SOIC14', u9)
D.C('100n', '+3V3', 'GND')
D.C('100n', '+3V3', 'GND')
D.group('Probe input')
D.add('J?', 'Connector_Generic:Conn_01x01', 'PROBE', 'HDR1x1', {1: 'PROBE'}, silk='PROBE')
D.R('100k', 'PROBE', 'GND')
for i, (sig, label, mode) in enumerate(ch):
    n = i + 1
    D.group('Indicator %s' % label)
    D.R('4k7' if sig == 'PROBE' else '1k', sig, 'IND%d_D' % n)
    if mode == 'H':
        D.add('D?', 'Device:D_Schottky', 'BAT54WS', 'SOD323', {1: 'IND%d_S' % n, 2: 'IND%d_D' % n})
        D.R('1M', 'IND%d_S' % n, 'GND')
        D.C('47n', 'IND%d_S' % n, 'GND')
        D.R('1k', '+3V3', 'IND%d_K' % n)       # LED lit when inverter output is low
        D.LED('yellow' if 'NP' in label else 'orange', 'IND%d_K' % n, 'IND%d_Y' % n, silk=label)
    else:
        D.add('D?', 'Device:D_Schottky', 'BAT54WS', 'SOD323', {1: 'IND%d_D' % n, 2: 'IND%d_S' % n})
        D.R('1M', 'IND%d_S' % n, '+3V3')
        D.C('47n', 'IND%d_S' % n, 'GND')
        D.R('1k', 'IND%d_Y' % n, 'IND%d_K' % n)  # LED lit when inverter output is high
        D.LED('orange', 'IND%d_K' % n, 'GND', silk=label)

# =========================================================================== BODY
D.sheet('body', 'Body connector (DA-15 male, female-harness compatible)',
        'Pins 4,5,6,7,8,12,13,14,15 identical to the ZKM electronic box female D-subs (J1/J5), '
        'so existing female body harnesses plug in unchanged. Pins 1,2,3,9,10,11 add the male extras.')
D.group('DA-15')
D.add('J?', 'Connector:DA15_Plug_MountingHoles', 'BODY DA-15 male', 'DSUB15',
      {0: 'GND', 1: 'LS2_IN', 2: 'LS3_IN', 3: 'LS4_IN', 4: 'SPK-', 5: 'LS1_IN', 6: 'MIC_IN', 7: '+12V_BODY',
       8: 'GND', 9: 'NP2_OUT', 10: 'STATE1_OUT', 11: 'AUX_IN', 12: 'SPK+', 13: 'NP1_OUT', 14: 'DXL_DATA',
       15: '+5V_BODY'}, silk='BODY')

if __name__ == '__main__':
    bad = D.check()
    print(len(D.parts), 'parts', len(D.nets()), 'nets')
    for b in bad:
        print('single-node net:', b)
