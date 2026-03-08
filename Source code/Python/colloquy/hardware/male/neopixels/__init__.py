from colloquy.base import Base

from pathlib import Path
from .html import HTML

from .o_drive_level import ODriveLevel
from .p_drive_level import PDriveLevel
from .ring import Ring



class Neopixels(Base):
    
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._arduino = owner.arduino
        
        self._ring = Ring(owner=self)
        self._o_drive_level= ODriveLevel(owner=self)
        self._p_drive_level = PDriveLevel(owner=self)

        self[self.html.name] = self.html.handle_request
        self[self.ring.name] = self.ring
        self[self.o_drive_level.name] = self.o_drive_level
        self[self.p_drive_level.name] = self.p_drive_level
    
    def __iter__(self):
        yield self.ring
        yield self.o_drive_level
        yield self.p_drive_level
        
    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return "neopixels"

    @property
    def ring(self):
        return self._ring

    @property
    def o_drive_level(self):
        return self._o_drive_level

    @property
    def p_drive_level(self):
        return self._p_drive_level

