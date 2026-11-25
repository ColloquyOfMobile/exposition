import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_board import repair, extract_routes
from route_brain_cfg import WIDTHS
SCR = os.environ.get('TJ_BUILD', os.path.join(HERE, '_build'))
os.makedirs(SCR, exist_ok=True)
SCR = os.environ.get('TJ_SRC', SCR)
logf = open(os.path.join(SCR, os.environ.get('TJ_LOG', 'repair_log.txt')), 'w')
def log(s):
    print(s); logf.write(s + '\n'); logf.flush()
rj = os.path.join(SCR, os.environ.get('TJ_ROUTES', 'tj_brain_routes.json'))
if not os.path.exists(rj):
    log('extracted %d items' % extract_routes(os.path.join(SCR, 'tj_brain_routed.kicad_pcb'), rj))
PROTECT = ['+5V', '+12V', '+3V3', '+5V_TEENSY', '+5V_BODY', '+12V_BODY']
print(repair(os.path.join(SCR, 'tj_brain_placed.kicad_pcb'), rj,
             os.path.join(SCR, os.environ.get('TJ_OUT', 'tj_brain_repaired.kicad_pcb')),
             180.0, 136.0, WIDTHS, log=log, protect=PROTECT if os.environ.get('TJ_PROTECT', '1') == '1' else (),
             drop=[n for n in os.environ.get('TJ_DROP', '').split(',') if n]))
