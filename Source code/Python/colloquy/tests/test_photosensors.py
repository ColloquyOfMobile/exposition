from colloquy.thread_element import ThreadElement
import socket
from .detect_pattern import DetectPattern

class TestPhotosensors(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="test photosensors")
        self._is_started = False
        self._is_open = False
        self._last_sensor_value = None  # stores the previous sensor state
        self._detect_pattern = DetectPattern(owner=self)
        # self.speaker_on = None

    @property
    def hardware(self):
        return self.owner.hardware

    @property
    def is_open(self):
        return self._is_open

    def open(self, **kwargs):
        if self._is_open:
            return
        self.hardware.connect()
        self.owner.opened = self
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        self.hardware.close()
        self._is_open = False
        self.owner.opened = None

    def _toggle_beam(self, **kwargs):
        self.hardware.male1.body_neopixel.ring.toggle()
        # raise NotImplementedError()

    def _setup(self, **kwargs):
        hostname = socket.gethostname()
        if hostname != "DESKTOP-MRSLS88":        
            self.hardware.female1.emulate_light_sensor = False
        
        self.hardware.turn_to_origin_position(elements=self.hardware.moving_elements)
        self._detect_pattern.start()
        # self.hardware.male1.search.blink.start()
        # self.hardware.male1.body_neopixel.ring.configure(
            # red = 0,
            # green = 0,
            # blue = 0,
            # white = 255,
            # brightness = 255,)
        # self.hardware.male1.body_neopixel.ring.on()

    def _loop(self, **kwargs):
        return
        # raise NotImplementedError("Update this funtion to detect the pattern of light.")
        # value = self.hardware.female1.sensor.read()
        # print(f"{value=}")
        
        # # threshold to decide between "light detected" and "no light"
        # threshold = 300  # adjust depending on your sensor
        
        # # convert to boolean (False = low, True = high)
        # current_state = value > threshold
        
        # if self._last_sensor_value is None:
            # # first read, just initialize
            # self._last_sensor_value = current_state
            # return
        
        # # rising edge detected (low -> high)
        # if not self._last_sensor_value and current_state:
            # print("Rising edge detected!")
        
        # # falling edge detected (high -> low)
        # elif self._last_sensor_value and not current_state:
            # print("Falling edge detected!")
        
        # # update last value for the next loop
        # self._last_sensor_value = current_state
    
    def stop(self, **kwarg):
        if self.is_started:
            self.hardware.male1.body_neopixel.ring.off()
        self.hardware.female1.emulate_light_sensor = None
                
        
        ThreadElement.stop(self)

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return

        self._add_html_title()
        
        if self._is_started:
            self._write_html_action(value="hardware/tests/photosensors/stop", label="stop", func=self.stop)
            
            
            self.hardware.male1.search.blink.add_html()
            return
        
            
        self._write_html_action(value="hardware/tests/photosensors/close", label="close", func=self.close)
        
        self._write_html_action(value="hardware/tests/photosensors/start", label="start", func=self.start)
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/tests/speaker/open", label=self.name, func=self.open)


    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(self.name.title())
        with tag("div"):
            text("Enable testing photosensors one by one.")
    


