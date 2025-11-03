from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from .base import Base

class ColloquyItem(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
    
    def add(self, element):
        self[element.name] = element