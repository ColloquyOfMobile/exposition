from colloquy.hardware.item import Item as _Item


class Item(_Item):
    @property
    def female(self):
        return self.owner.female
