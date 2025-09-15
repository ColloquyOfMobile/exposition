from colloquy.thread_element import ThreadElement

class TestPhotosensors(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="test photosensors")
        self._is_started = False
        self._is_open = False
        self._last_sensor_value = None  # stores the previous sensor state
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

    def _toggle_beam(self, **kwargs):
        self.colloquy.male1.body_neopixel.ring.toggle()
        # raise NotImplementedError()

    def _setup(self, **kwargs):
        self.colloquy.turn_to_origin_position(elements=self.colloquy.moving_elements)
        self.colloquy.male1.body_neopixel.ring.configure(
            red = 0,
            green = 0,
            blue = 0,
            white = 255,
            brightness = 255,)
        self.colloquy.male1.body_neopixel.ring.on()
        self.colloquy.female1.emulate_light_sensor = False

    def _loop(self, **kwargs):
        raise NotImplementedError("Update this funtion to detect the pattern of light.")
        value = self.colloquy.female1.sensor.read()
        print(f"{value=}")
        
        # threshold to decide between "light detected" and "no light"
        threshold = 300  # adjust depending on your sensor
        
        # convert to boolean (False = low, True = high)
        current_state = value > threshold
        
        if self._last_sensor_value is None:
            # first read, just initialize
            self._last_sensor_value = current_state
            return
        
        # rising edge detected (low -> high)
        if not self._last_sensor_value and current_state:
            print("Rising edge detected!")
        
        # falling edge detected (high -> low)
        elif self._last_sensor_value and not current_state:
            print("Falling edge detected!")
        
        # update last value for the next loop
        self._last_sensor_value = current_state
    
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
            
            self._write_html_action(value="colloquy/tests/photosensors/toggle_beam", label="toggle beam", func=self._toggle_beam)
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

class DetectPattern(ThreadElement):
    def __init__(self, owner):
        super().__init__(owner=owner, name="detect_pattern")
        self._last_sensor_value = None
        self._edges = []  # store timestamps of edges
        self._threshold = 300  # adjust to your sensor
        self._debounce = 0.05  # seconds to avoid false triggers
        self._last_edge_time = 0

    def _loop(self, **kwargs):
        value = self.colloquy.female1.sensor.read()

        # convert to boolean (False = low, True = high)
        current_state = value > self._threshold

        if self._last_sensor_value is None:
            self._last_sensor_value = current_state
            return

        now = time()

        # rising edge detected (0 -> 1)
        if not self._last_sensor_value and current_state:
            if now - self._last_edge_time > self._debounce:
                print("Rising edge detected")
                self._edges.append(("rise", now))
                self._last_edge_time = now

        # falling edge detected (1 -> 0)
        elif self._last_sensor_value and not current_state:
            if now - self._last_edge_time > self._debounce:
                print("Falling edge detected")
                self._edges.append(("fall", now))
                self._last_edge_time = now

        self._last_sensor_value = current_state

        # Optional: after collecting enough edges, analyze timing vs LIGHT_PATTERNS
