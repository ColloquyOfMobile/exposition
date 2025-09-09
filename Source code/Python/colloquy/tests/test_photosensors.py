from colloquy.thread_element import ThreadElement

class TestPhotosensors(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="test photosensors")
        self._is_started = False
        self._is_open = False
        # self.speaker_on = None

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def is_open(self):
        return self._is_open

    def open(self, **kwargs):
        if self._is_open:
            return
        self.colloquy.connect()
        self.owner.opened = self
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        self.colloquy.close()
        self._is_open = False
        self.owner.opened = None

    def _setup(self, **kwargs):
        self.colloquy.turn_to_origin_position(elements=self.colloquy.moving_elements)
        self.colloquy.male1.body_neopixel.ring.on()
        self.colloquy.female1.emulate_light_sensor = False

    def _loop(self, **kwargs):
        self.colloquy.female1.sensor.read()
        print(f"{self.colloquy.female1.sensor.read()=}")
    
    def stop(self, **kwarg):
        self.colloquy.male1.body_neopixel.ring.off()
        self.colloquy.female1.emulate_light_sensor = None
                
        if self._is_started:
            self._is_started = False
            self.stop_event.set()
            return
            
        for element in self.elements:
            element.stop()

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return

        self._add_html_title()
        
        if self._is_started:
            self._write_html_action(value="colloquy/tests/photosensors/stop", label="stop", func=self.stop)
            return
        
            
        self._write_html_action(value="colloquy/tests/photosensors/close", label="close", func=self.close)
        
        self._write_html_action(value="colloquy/tests/photosensors/start", label="start", func=self.start)
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="colloquy/tests/speaker/open", label=self.name, func=self.open)


    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(self.name.title())
        with tag("div"):
            text("Enable testing photosensors one by one.")