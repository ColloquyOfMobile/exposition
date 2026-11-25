import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_board import route
SCR = os.environ.get('TJ_BUILD', os.path.join(HERE, '_build'))
os.makedirs(SCR, exist_ok=True)
from route_brain_cfg import WIDTHS, FIRST
logf = open(os.path.join(SCR, 'route_log.txt'), 'w')
def log(s):
    print(s); logf.write(s + '\n'); logf.flush()
PROTECT = ['+5V', '+12V', '+3V3', '+5V_TEENSY', '+5V_BODY', '+12V_BODY']
failed = route(os.path.join(SCR, 'tj_brain_placed.kicad_pcb'), os.path.join(SCR, 'tj_brain_repaired.kicad_pcb'),
               180.0, 136.0, WIDTHS, FIRST, log=log, routes_json=os.path.join(SCR, 'tj_brain_routes.json'),
               protect=PROTECT)
print('open nets:', failed)
