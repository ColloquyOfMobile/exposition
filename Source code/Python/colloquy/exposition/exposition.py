from colloquy.thread_element import ThreadElement
from datetime import datetime
from time import sleep, time


class Exposition(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="exposition")
        self._is_open = False
        self._print_origin = None

    @property
    def near_origin_threashold(self):
        return self.owner.near_origin_threashold 

    @property
    def agenda(self):
        return self.owner.agenda 

    @property
    def hardware(self):
        return self.owner.hardware

    @property
    def is_open(self):
        return self._is_open

    
    def get_near_origin_threashold(self, **kwargs):
        return self._near_origin_threashold

    
    def set_near_origin_threashold(self, **kwargs):
        value = kwargs["value"][0]
        self.hardware.near_origin_threashold = int(value)

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return
            
        self._add_html_thread_count()
        
        with tag("h2"):
            text(self.name.title())
        
        with tag("div"):
            doc.stag("hr")
            path =f"hardware/near origin threashold"
            with tag("form", method="post"):
                min_value = 0
                max_value = 400
                with tag("label"):
                    text(f"Near origin threashold [{min_value}-{max_value}]: ")
                doc.stag("input", type="number", name="value", value=self.near_origin_threashold, min=min_value, max=max_value, increment=1)
                with tag("button", name="action", value=path):
                    text("set")
            self.actions[path] = self.set_near_origin_threashold
            doc.stag("hr")
        
        self.agenda.add_html()
            
        with tag("div"):
            doc.stag("hr")
            if not self.is_started:
                self._add_html_start()
            else:
                self._add_html_stop()
            doc.stag("hr")

    

    def stop(self, **kwargs):        
        self.stop_event.set()
        self.hardware.stop()
        self.hardware.join()
        ThreadElement.stop(self, **kwargs)     
        self.stop_event.clear()

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
    
    def _setup(self):
        pass
    
    def _loop(self):
        if self._print_origin is None:
            self._print_origin = time()
        
        now = datetime.now()
        today = now.strftime("%A").lower()
        
        day = self.agenda.week[today]
        
        
        
        if day.state:
            start, end = day.start, day.end
            assert start and end, "Make sure to define start and end working days!"
            current_time = now.time()
            if start <= current_time < end:  
                if not self.hardware.is_started:              
                    print(f"Hardware is started...")
                    self.hardware.start()
                    
                if time() - self._print_origin > 10:
                    self._print_origin = time()
                    print("Running...")
            else:
                if self.hardware.is_started:          
                    print(f"Hardware is stop...")
                    self.hardware.stop()
                    
                if time() - self._print_origin > 10:
                    self._print_origin = time()
                    print("Waiting next agenda slot...")
        else:
            
            if time() - self._print_origin > 10:
                self._print_origin = time()
                print("Waiting next agenda slot...")
        
        sleep(1)
   
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/exposition/open", label=self.name, func=self.open)

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="hardware/start"):
                text(f"Start.")
                self.actions["hardware/start"] = self.start
            
            
            self._write_html_action(value="hardware/exposition/close", label="close", func=self.close)

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="hardware/stop"):
                text(f"Stop.")
        self.actions["hardware/stop"] = self.stop