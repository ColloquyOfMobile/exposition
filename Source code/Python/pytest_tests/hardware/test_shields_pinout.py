"""Protect the signal comparison's processor mapping and generated diagrams.

Load by file path so these PCB checks never initialize the application.
"""
import importlib.util
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
ELECTRONICS = ROOT / 'Source code/Python/colloquy/hardware/electronics'


def load(name):
    spec = importlib.util.spec_from_file_location(name, ELECTRONICS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load('harness')
diagram = load('shields_pinout')


def test_microphone_routes_distinguish_band_outputs_from_raw_adc_inputs():
    inputs, _ = diagram.connections()
    microphones = inputs[:5]
    assert [r['signal'] for r in microphones] == [b + '/microphone' for b in diagram.BODIES]
    assert [r['mega'] for r in microphones] == ['A0', 'A1', 'A2', 'A3', 'A4']
    assert [r['teensy'] for r in microphones] == ['14 / A0', '15 / A1', '16 / A2', '17 / A3', '18 / A4']
    assert all('MSGEQ7' in r['mega_path'] and '4.7K' in r['teensy_path'] for r in microphones)


def test_tone_and_bar_pixel_pins_do_not_follow_body_number_order():
    _, outputs = diagram.connections()
    rows = {r['signal']: r for r in outputs}
    assert (rows['female2/tone']['mega'], rows['female2/tone']['teensy']) == ('D46', '4')
    assert (rows['male2/tone']['mega'], rows['male2/tone']['teensy']) == ('D5', '28')
    assert (rows['male1/bar neopixel']['mega'], rows['male1/bar neopixel']['teensy']) == ('D16', '29')
    assert (rows['male2/bar neopixel']['mega'], rows['male2/bar neopixel']['teensy']) == ('D17', '12')
    assert rows['analyser/reset']['teensy'] == rows['analyser/strobe']['teensy'] == '—'


def test_last_sensor_channels_use_teensy_extended_analogue_pins():
    inputs, _ = diagram.connections()
    rows = {r['signal']: r for r in inputs}
    assert (rows['male2/photosensor/C']['mega'], rows['male2/photosensor/C']['teensy']) == ('A14', '38 / A14')
    assert (rows['male2/photosensor/D']['mega'], rows['male2/photosensor/D']['teensy']) == ('A15', '39 / A15')


def test_both_artifacts_are_current_and_share_every_signal_label():
    inputs, outputs = diagram.connections()
    assert len(inputs) == 16 and len(outputs) == 17
    for processor in ('mega', 'teensy'):
        expected = diagram.render(processor, inputs, outputs)
        stored = (diagram.STATIC / f'shields-{processor}-pinout.svg').read_text(encoding='utf-8')
        assert stored == expected
        root = ET.fromstring(stored)
        labels = [node.text for node in root.iter('{http://www.w3.org/2000/svg}text')]
        assert all(r['signal'] in labels for r in inputs + outputs)
