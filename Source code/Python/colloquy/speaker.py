from .thread_element import ThreadElement
from pathlib import Path
from threading import Event
from time import sleep

class Speaker(ThreadElement):

    def __init__(self, owner, arduino_manager):
        ThreadElement.__init__(self, name="speaker", owner=owner)
        # self._owner = owner
        self.arduino_manager = arduino_manager
        self._on_off_state = None
        self._is_notifing = False
        self._is_encouraging = False
        self.colloquy.speakers.append(self)
        self._ui_context = None

    @property
    def is_encouraging(self):
        return self._is_encouraging

    @property
    def is_notifing(self):
        return self._is_notifing

    @property
    def is_on(self):
        return self._on_off_state

    def set(self, neopixel_on_off):
        if neopixel_on_off:
            self.on()
        else:
            self.off()

    def on(self, **kwargs):
        path = f"{self._owner.name}/speaker"
        self.arduino_manager.send(path, data="on")
        self._on_off_state = True
        
        if self._ui_context:
            self._ui_context.speaker_on = self


    def off(self, **kwargs):
        path = f"{self._owner.name}/speaker"
        self.arduino_manager.send(path, data="off")
        self._on_off_state = False
        
        if self._ui_context:
            self._ui_context.speaker_on = None

    def toggle(self):
        if self._on_off_state is None:
            self.on()
            self._on_off_state = True
            return

        if self._on_off_state:
            self.off()
            self._on_off_state = False
            return

        if not self._on_off_state:
            self.on()
            self._on_off_state = True
            return

    def notify(self):
        self._is_notifing = True
        for i in range(3):
            self.on()
            sleep(0.2)
            self.off()
            sleep(0.1)
        self._is_notifing = False

    def encourage(self):
        self._is_encouraging = True
        for i in range(3):
            self.on()
            sleep(0.2)
            self.off()
            sleep(0.1)
        self._is_encouraging = False

    def write_html(self, ui_context = None):
        doc, tag, text = self.html_doc.tagtext()
        self._ui_context = ui_context
        
        if self.is_on:
            self._write_html_action(value=f"colloquy/{self.owner.name}/speaker/off", label=f"{self.owner.name} off", func=self.off)
            return

        
        self._write_html_action(value=f"colloquy/{self.owner.name}/speaker/on", label=f"{self.owner.name} on", func=self.on)