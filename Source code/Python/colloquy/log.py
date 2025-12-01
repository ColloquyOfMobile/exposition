from time import sleep, time
from pathlib import Path
from threading import Timer
from colloquy.base import Base
from datetime import datetime

class Log(Base): 
    
    def __init__(self, owner):
        super().__init__(owner=owner)
    
    def __call__(self, msg):
        print(f"{self.owner.name}: {msg}")