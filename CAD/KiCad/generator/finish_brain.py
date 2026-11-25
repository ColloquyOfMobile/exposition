"""Zone fill, DRC, project files and fabrication outputs for the TJ Brain."""
import os
import shutil
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export
from brain import D, REV
from route_board import finish, stitch, connect_pour_islands

SCR = os.environ.get('TJ_BUILD', os.path.join(HERE, '_build'))
OUT = os.path.join(HERE, '..', 'tj_brain')
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCR, 'tj_brain_repaired.kicad_pcb')
final = os.path.join(OUT, 'tj_brain.kicad_pcb')
shutil.copy(src, final)
print('stitching vias:', stitch(final, 180.0, 136.0))
finish(final, os.path.join(SCR, 'brain_drc_fill.rpt'))
connect_pour_islands(final, 180.0, 136.0)
finish(final, os.path.join(SCR, 'brain_drc_fill2.rpt'))
export.project_file(os.path.join(OUT, 'tj_brain.kicad_pro'), 'tj_brain', [
    ('Power', 0.8, ['+5V', '+12V']),
    ('Body', 1.2, ['+5V_BODY', '+12V_BODY']),
    ('Supply', 0.4, ['+3V3', '+5V_TEENSY']),
    ('Speaker', 0.6, ['SPK+', 'SPK-']),
    ('Outputs', 0.4, ['NP?_OUT', 'STATE?_OUT', 'STATE?_HI']),
])
export.lib_tables(OUT)
counts, unc = export.drc(final, os.path.join(SCR, 'brain_drc_final.rpt'))
if counts.get('starved_thermal'):
    # pads whose thermal relief could only get one spoke: connect them solid to the pour
    import re, pcbnew
    txt = open(os.path.join(SCR, 'brain_drc_final.rpt')).read()
    pads = set()
    blocks = txt.split('\n[')
    for blk in blocks:
        if blk.startswith('starved_thermal]') or blk.startswith('[starved_thermal]'):
            pads |= set(re.findall(r'PTH pad (\S+) \[GND\] of (\S+)', blk))
    b = pcbnew.LoadBoard(final)
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            if (pd.GetNumber(), fp.GetReference()) in pads:
                pd.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                print('solid zone connection for', fp.GetReference(), pd.GetNumber())
    pcbnew.SaveBoard(final, b)
    finish(final, os.path.join(SCR, 'brain_drc_fill3.rpt'))
    counts, unc = export.drc(final, os.path.join(SCR, 'brain_drc_final.rpt'))
print('DRC', dict(counts), unc)
export.fab(final, OUT, 'tj_brain', D)
print('exported to', os.path.abspath(OUT))
