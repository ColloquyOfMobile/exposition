from colloquy.base import Base

from pathlib import Path
from .html import HTML

from .up_ring import UpRing
from .o_drive_level import ODriveLevel
from .p_drive_level import PDriveLevel
from .ring import Ring



class Neopixels(Base):
    
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._arduino = owner.arduino
        
        self._up_ring = UpRing(owner=self)
        self._ring = Ring(owner=self)
        self._o_drive_level= ODriveLevel(owner=self)
        self._p_drive_level = PDriveLevel(owner=self)

        self[self.html.name] = self.html.handle_request
        self[self.ring.name] = self.ring
        self[self.o_drive_level.name] = self.o_drive_level
        self[self.p_drive_level.name] = self.p_drive_level
        self[self.up_ring.name] = self.up_ring
    
    def __iter__(self):
        yield self.up_ring
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
    def male(self):
        return self.owner

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
    def up_ring(self):
        return self._up_ring

    @property
    def o_drive_level(self):
        return self._o_drive_level

    @property
    def p_drive_level(self):
        return self._p_drive_level
    
    # def snapshot(self, path):
        # path = path + (self.name, )
        # states = {
            # "path": path,
            # "name": self.name,
            # "close": self.close,
            # "open": self.open,
            # "opened": self._is_opened,
            # self.up_ring.name: self.up_ring.snapshot(path=path),
            # self.ring.name: self.ring.snapshot(path=path),
            # self.o_drive_level.name: self.o_drive_level.snapshot(path=path),
            # self.p_drive_level.name: self.p_drive_level.snapshot(path=path),
        # }
        # return states
    
    @property
    def snapshot_children(self):
        children = {}
        children.update({
            self.up_ring.name: self.up_ring,
            self.ring.name: self.ring,
            self.o_drive_level.name: self.o_drive_level,
            self.p_drive_level.name: self.p_drive_level,
        })
        return children

