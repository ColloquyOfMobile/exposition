# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library

from colloquy.base import Base
from .html import HTML
from time import time, sleep
from colloquy.input import Input
from colloquy.hardware.value_setter import ValueSetter

class DXLOrigin(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self["get"] = self.get
        self._setter = ValueSetter(owner=self, limit=101)
        
        # if not self.is_readonly():
        self._input = Input(owner=self)
        self[self.input.name] = self.input

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
    def input(self):
        return self._input

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.colloquy.params

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "dxl origin"
    
    @property
    def female(self):
        return self.owner
    
    @property
    def setter(self):
        return self._setter
    
    @property
    def dxl_origin(self):
        return self
    
    def is_readonly(self):
        return False
        
    def commit(self, value):
        value = int(value)
        return self.set(value=value)
        
    def get(self, request=None):
        return self.params[self.owner.name][self.name]
    
    def set(self, value):
        self.params[self.owner.name][self.name] = value
    
    def snapshot(self, path):
        _path = path + (self.name, )        
        states = super().snapshot(path=path)
        
        states.update({
            "value": self.get(),
            self.setter.name: self.setter.snapshot(_path),
        })
        return states 



# # ChatGPT, I would a more generale implementation that would work with any limit.
# class Setter(Base):
    
    # def __init__(self, owner, limit):
        # super().__init__(owner=owner)
        # self._setters = list()
        
        # for i in range(5):      
            
            # value = i*1000
            # if value > limit:
                # return

            # self._setters.append(Setter0(owner=self, thousands=i, limit=limit))
    
    # @property
    # def name(self):
        # return "set"
    
    # @property
    # def dxl_origin(self):
        # return self.owner.dxl_origin
    
    # def snapshot(self, path):
        # states = super().snapshot(path=path)
        # _path = path + (self.name, )
        # for setter in self._setters:
            # states[setter.name] = setter.snapshot(_path)
        
        # return states
        
        
# class Setter0(Base):
    
    # def __init__(self, owner, thousands, limit):
        # self._thousands = thousands
        # super().__init__(owner=owner)
        
        # self._setters = list()
        
        # for i in range(10):
            # value = thousands*1000 + i*100
            # if value >= limit:
                # return
            # self._setters.append(Setter1(owner=self, thousands=thousands, hundreds=i, limit=limit))
    
    # @property
    # def name(self):
        # return f"{self._thousands}***"
    
    # @property
    # def dxl_origin(self):
        # return self.owner.dxl_origin
    
    # def snapshot(self, path):
        # states = super().snapshot(path=path)
        # _path = path + (self.name, )
        # for setter in self._setters:
            # states[setter.name] = setter.snapshot(_path)
        # return states
        
        
# class Setter1(Base):
    
    # def __init__(self, owner, thousands, hundreds, limit):
        # self._thousands = thousands
        # self._hundreds = hundreds
        # super().__init__(owner=owner)
        
        # self._setters = list()
        
        # for i in range(10):
            # value = thousands*1000 + hundreds*100 + i*10
            # if value >= limit:
                # return
            # self._setters.append(Setter2(owner=self, thousands=thousands, hundreds=hundreds, tens=i, limit=limit))
    
    # @property
    # def name(self):
        # return f"{self._thousands}{self._hundreds}**"
    
    # @property
    # def dxl_origin(self):
        # return self.owner.dxl_origin
    
    # def snapshot(self, path):
        # states = super().snapshot(path=path)
        # _path = path + (self.name, )
        # for setter in self._setters:
            # states[setter.name] = setter.snapshot(_path)
        # return states
        
        
# class Setter2(Base):
    
    # def __init__(self, owner, thousands, hundreds, tens, limit):
        # self._thousands = thousands
        # self._hundreds = hundreds
        # self._tens = tens
        
        # super().__init__(owner=owner)
        
        # self._setters = list()
        
        # for i in range(10):
            # value = thousands*1000 + hundreds*100 + i*10
            # if value >= limit:
                # return
            # self._setters.append(self.set(value))
    
    # @property
    # def name(self):
        # return f"{self._thousands}{self._hundreds}{self._tens}*"
    
    # @property
    # def dxl_origin(self):
        # return self.owner.dxl_origin
    
    # def set(self, value):
        # def wrap():
            # self.dxl_origin.set(value)
        # return wrap
    
    # def snapshot(self, path):
        # states = super().snapshot(path=path)
        # _path = path + (self.name, )
        # for i, setter in enumerate(self._setters):
            # states[f"{self._thousands}{self._hundreds}{self._tens}{i}"] = setter
        # return states