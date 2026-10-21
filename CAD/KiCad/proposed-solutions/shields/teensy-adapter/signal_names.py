"""Reading names shared by the wired drawing and PCB's back silkscreen.

These captions do not rename electrical nets. The current circuit manifest is
the authority for routing a functional signal to its Teensy socket contact.
"""


def short_signal(net):
    return (net.replace('female', 'f').replace('male', 'm')
            .replace('/neopixel/driven', '/neopixel')
            .replace('/bar neopixel/driven', '/bar/neopixel')
            .replace('/mic direct', '/microphone')
            .replace('/aux driven', '/aux')
            .replace('amp shutdown', 'amp/shutdown'))


def gpio_signals(parts):
    """Map processor GPIO number to the signal across each existing interface."""
    signals = {}
    for ref in ('U1', 'U2', 'U3', 'U4'):
        for inp, out in [('2','3'), ('5','6'), ('9','8'), ('12','11')]:
            source, destination = parts[ref]['pins'][inp], parts[ref]['pins'][out]
            if source.startswith('gpio/'):
                signals[source.split('/')[1]] = short_signal(destination)
    for ref, part in parts.items():
        if ref.startswith('RA'):
            signals[part['pins']['2'].split('/')[1]] = short_signal(part['pins']['1'])
    for socket in ('JT1', 'JT2'):
        for pin, net in parts[socket]['pins'].items():
            if net and net.endswith('/mic direct'):
                signals[parts[socket]['pin_names'][pin]] = short_signal(net)
    assert len(signals) == 31
    return signals
