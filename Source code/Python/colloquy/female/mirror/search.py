from colloquy.thread_element import ThreadElement
from time import time, sleep

class Search(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"search")

    def __enter__(self):
        self.stop_event.clear()
        raise NotImplementedError

    def _loop(self):
        if not self.owner.is_moving:
            if self.owner.listen_for_confirmation():
                self.owner.memorise_drive()
                raise NotImplementedError()
            self.owner.toggle_position()