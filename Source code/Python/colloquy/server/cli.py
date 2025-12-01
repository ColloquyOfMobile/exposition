from pathlib import Path

from colloquy.base import Base
        
class CLI(Base):
    
    def __init__(self, owner):
        super().__init__(owner=owner)
        
        self._request = None
        self["start"] = self.owner.start.cli
        self["restarted"] = self.owner.restarted.cli
        
    
    def __call__(self, request):
        request = Path(request)

        self._request = request
        
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

    # def pprint(self, ):
        # return self.server()
    
    # def restart(self):        
        # python = sys.executable
        # args = ["main.py", "server/restart"]
        # # args.append()
        # os.execl(python, python, *args)
        
    def _call_root(self):
        print(f"Available command for {self.owner.path.as_posix()}:")
        for name in self:
            print(f"- {name}")
        # raise NotImplementedError(f"{self=}")