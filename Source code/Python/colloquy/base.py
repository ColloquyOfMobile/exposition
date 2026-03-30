
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
import socket
from .logger import Logger

class Base:

    _all_threads = set()

    @staticmethod
    def retrieve_call_origin():
        """Used for debug."""
        stack = inspect.stack()
        if len(stack) > 2:
            caller_frame = stack[2]
            caller_filename = caller_frame.filename  # File where the call happened
            caller_lineno = caller_frame.lineno      # Line number of the call
            return f"{caller_filename}:{caller_lineno}"
        else:
            return "unknown origin"

    def __init__(self, owner):
        self._dict = {}
        self._path = None
        assert owner is not self
        self._owner = owner
        self._owners = None
        assert owner is not self.owners
        self._log = Logger()
        self._is_opened = False

    def __repr__(self):
        return f"{type(self).__name__}({self.path.as_posix()})"

    def __getitem__(self, key):
        try:
            item = self._dict[key]
        except KeyError:
            raise KeyError(f"{key} not in {self=}")

        return item

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __contains__(self, key):
        return key in self._dict

    def __iter__(self):
        yield from self._dict

    @property
    def all_threads(self):
        dead_threads = set()
        # Remove dead threads
        for thread in self._all_threads:
            if thread.is_started:
                continue
            dead_threads.add(thread)
        self._all_threads.difference_update(dead_threads)
        return self._all_threads

    @property
    def log(self):
        return self._log

    @property
    def items(self):
        return self._dict.items

    @property
    def path(self):
        if self._path is not None:
            return self._path

        if self.owner is not None:
            self._path = self.owner.path / self.name
            return self._path

        self._path = Path()
        return self._path

    @property
    def owner(self):
        return self._owner

    @property
    def owners(self):
        if self.owner is None:
            return []
        if self._owners is None:
            self._owners = [self.owner] + self.owner.owners
        return self._owners

    @property
    def events(self):
        return self.owner.events

    @property
    def is_simulated(self):
        if socket.gethostname() == 'Colloquy-Laptop':
            return False
        return True
    
    @property
    def opened(self):
        raise NotImplementedError(self)
    
    @opened.setter
    def opened(self, value):
        raise NotImplementedError(self)

    def add(self, element):
        self[element.name] = element

    def _svg_down_arrow(self):
        raise NotImplementedError("Implemented in BaseHTML class now.")


    def _svg_right_arrow(self):
        raise NotImplementedError("Implemented in BaseHTML class now.")
        
    def open(self):
        self._is_opened = True 
        
    def close(self):
        self._is_opened = False