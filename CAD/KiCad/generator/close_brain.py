"""Loop: link GND pour islands -> rebuild -> finish (fill, DRC, export) until DRC has no unconnected items."""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('TJ_BUILD', os.path.join(HERE, '_build'))
for it in range(6):
    out = subprocess.run([sys.executable, os.path.join(HERE, 'finish_brain.py')], capture_output=True, text=True).stdout
    line = [l for l in out.splitlines() if l.startswith('DRC')][-1]
    print('finish', it, line)
    if "'unconnected_items'" not in line:
        break
    out = subprocess.run([sys.executable, os.path.join(HERE, 'islands_brain.py')], capture_output=True, text=True).stdout
    print('\n'.join(l for l in out.splitlines() if 'island' in l or 'open' in l))
