from colloquy.thread_element import ThreadElement
from time import sleep

class Microphone(ThreadElement):

    def __init__(self, owner):
        name = f"microphone"
        ThreadElement.__init__(self, name=name, owner=owner)
        self.is_plugged = True # For testing

    @property
    def is_notified(self):
        # raise NotImplementedError
        if self.is_plugged:
            interaction = self.colloquy.bar.interaction
            if interaction is not None:
                if interaction.is_started:
                    if interaction.male is self.owner:
                        return interaction.female.speaker.is_notifing
            # raise NotImplementedError
        return False

    @property
    def is_encouraged(self):
        # raise NotImplementedError
        if self.is_plugged:
            interaction = self.colloquy.bar.interaction
            if interaction is not None:
                if interaction.is_started:
                   return interaction.male.speaker.is_encouraging
            # raise NotImplementedError
        return False