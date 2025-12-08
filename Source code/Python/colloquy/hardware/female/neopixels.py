from colloquy.hardware.neopixel import Neopixel
# from colloquy.hardware.female.item import Item
# from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.base import Base

from pathlib import Path
from threading import Event
        
        
    

class Head(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="head")
        self._body = owner
    
    def set_test_default(self):
        self.configure(red=0, green=255, blue=0, white=0, brightness=255)
        self.on()

    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")


# class BodyFemaleNeopixel(Base):

    # def __init__(self, owner):
        # super().__init__(owner=owner, ) 
        # self._arduino = owner.arduino
        # self._o_neopixel = BodyFemaleONeopixel(owner=self)
        # self._p_neopixel = BodyFemalePNeopixel(owner=self)
        # self._neopixels = [
            # self.o_neopixel,
            # self.p_neopixel,
        # ]
        
        # self[self._o_neopixel.name] = self._o_neopixel
        # self[self._p_neopixel.name] = self._p_neopixel

    # def __call__(self, request):
        # request = Path(request)
        # if not request.parts:
            # raise NotImplementedError
            
        # key, *leftover = request.parts
        
        # if key in self:
            # self[key](request="/".join(leftover))
            # return
            
        # raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")        
        

    # @property
    # def arduino(self):
        # return self._arduino
        
    
    # @property
    # def name(self):
        # return "body"
    
    # @property
    # def neopixels(self):
        # return self._neopixels
    
    # @property
    # def o_neopixel(self):
        # return self._o_neopixel
    
    # @property
    # def p_neopixel(self):
        # return self._p_neopixel
    
    # @property
    # def arduino_manager(self):
        # return self.owner.arduino_manager
    
    # # def open(self):
        # # self.o_neopixel.open()
        # # self.p_neopixel.open()
    
    # def on(self):
        # self.o_neopixel.on()
        # self.p_neopixel.on()
    
    # def off(self):
        # self.o_neopixel.off()
        # self.p_neopixel.off()


class Feet(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="feet")  
        self._body = owner
        
    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")
    
    def set_test_default(self):
        self.configure(red=0, green=0, blue=255, white=0, brightness=255)
        self.on()


class BodyO(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="bodyO")  
        self._body = owner
        
    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")
    
    def set_test_default(self):
        self.configure(red=125, green=125, blue=0, white=0, brightness=255)
        self.on()
        
class BodyP(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="bodyP")  
        self._body = owner

    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")
    
    def set_test_default(self):
        self.configure(red=125, green=0, blue=125, white=0, brightness=255)
        self.on()