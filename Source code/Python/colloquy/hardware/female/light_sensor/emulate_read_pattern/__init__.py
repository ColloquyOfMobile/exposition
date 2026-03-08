# -*- coding: utf-8 -*-
# ../workspace2/Colloquy/exposition/Source code/Python/colloquy/hardware/female/light_sensor/emulate_read_pattern/__init__.py

from colloquy.base_thread import BaseThread
from time import sleep
from threading import Lock
from pathlib import Path
from .html import HTML

class EmulateReadPattern(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._lock = Lock()
        self._html = HTML(owner=self)      
        self[self.html.name] = self.html.handle_request  
    
    @property
    def light_sensor(self):
        return self.owner        

    @property
    def html(self):
        return self._html        

    @property
    def name(self):
        return "emulate read pattern"

    def loop(self):
        if not female.near_origin():
            return
            
        if not self.hardware.bar.is_nearby(female):
            return

            male = interaction.male
            if not male.near_origin():
                return

    def setup(self):
        pass

    def setdown(self):
        print(f"Set down {self=}")        
        pass
        
    
    def fyi(self):
        female = self.owner
        with self.hardware.lock:

            if not female.near_origin():
                return

            interaction = self.hardware.bar.nearby(female)
            if interaction is None:
                return

            male = interaction.male
            if not male.near_origin():
                return

            common_drives = set(female.drives.state).intersection(male.drives.state)
            if common_drives:
                interaction.target_drive = tuple(common_drives)
                interaction.start()
        