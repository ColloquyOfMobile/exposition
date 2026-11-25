"""Link isolated GND pour islands (uses the last finished board), then re-run finish_brain.py."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_board import repair_islands, apply_routes
from route_brain_cfg import WIDTHS
SCR = os.environ.get('TJ_BUILD', os.path.join(HERE, '_build'))
PROTECT = ['+5V', '+12V', '+3V3', '+5V_TEENSY', '+5V_BODY', '+12V_BODY']
left = repair_islands(os.path.join(SCR, 'tj_brain_placed.kicad_pcb'), os.path.join(SCR, 'tj_brain_routes.json'),
                      os.path.join(HERE, '..', 'tj_brain', 'tj_brain.kicad_pcb'), 180.0, 136.0, WIDTHS, PROTECT)
print('left open:', left)
print('open after apply:', apply_routes(os.path.join(SCR, 'tj_brain_placed.kicad_pcb'), os.path.join(SCR, 'tj_brain_routes.json'),
                                         os.path.join(SCR, 'tj_brain_repaired.kicad_pcb'), 180.0, 136.0))
