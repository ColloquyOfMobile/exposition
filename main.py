import sys
from pathlib import Path
cwd = Path(__file__).parent
server_code = cwd / "Server"
sys.path.append(str(server_code.resolve()))
source_code = cwd / "Source code" / "Python"
sys.path.append(str(source_code.resolve()))

import server

if __name__ == "__main__":
    server.run()