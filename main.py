import sys
from pathlib import Path
cwd = Path(__file__).parent
server_code = cwd / "Server"
sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

import server


# position = [
    # 1100,
    # 2700,
    # 5000,
    # 7600,
    # 9000,
    # 11300,
    # ]

# for e in position:
    # print(e-1100)

if __name__ == "__main__":
    server.run()