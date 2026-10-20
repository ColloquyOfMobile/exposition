"""Apply the body-board parity/ERC checks to the male continuous-wire copy."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('body_verify',HERE.parent/'female base v2/scripts/verify_wired_schematic.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

if __name__=='__main__':
    # The common checker uses the source board's filename in three places.
    # Supply paths through an explicit per-board stem rather than altering files.
    v.HERE=HERE
    v.WIRED=HERE/'wired'
    v.STEM='male-static-v2'
    v.main()
