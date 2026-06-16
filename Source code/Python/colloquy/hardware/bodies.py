from colloquy.base import Base


class Bodies(Base):
    
    def __init__(self, owner, males, females):
        super().__init__(owner=owner)
        self._males = males
        self._females = females
    
    def __iter__(self):
        yield from self._males
        yield from self._females
        
    @property
    def name(self):
        return "bodies"
    
    def turn_all_bodies_origin(self):
        for body in self:
            body.turn_to_origin()
        
    def snapshot(self, path):
        states = super().snapshot(path=path)
        states["turn all bodies to origin"] = self.turn_all_bodies_origin
        return states 