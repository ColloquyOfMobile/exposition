from pathlib import Path

from .base import Base
        
class CLI(Base):
    
    def __init__(self, owner):
        super().__init__(owner=owner)
        
        self._request = None
        self._args = None 
        
        self["server"] = self.owner.server.cli
    
    def __call__(self, *args):
        if self.is_simulated:
            print(f"Warning: The hardware is simulated.")
        if args:
            path, *args = args
            request = Path(path)
        else:
            request = Path()

        self._request = request
        self._args = args
        
        if not request.parts:
            return self._call_root()

        key, *leftover = request.parts
        
        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{self=}, {key=}, {leftover=}")
    
    @property
    def name(self, ):
        return "cli"

    def run(self, ):
        return self.server()
    
    def restart(self):        
        python = sys.executable
        args = ["main.py", "server/restart"]
        # args.append()
        os.execl(python, python, *args)
        
    def _call_root(self):
        print("Available command:")
        for name in self.owner:
            print(f"- {name}")
        # raise NotImplementedError(f"{self=}")