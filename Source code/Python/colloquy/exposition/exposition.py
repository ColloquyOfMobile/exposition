from colloquy.thread_element import ThreadElement
from datetime import datetime
from time import sleep


class Exposition(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="exposition")
        self._is_open = False

    @property
    def near_origin_threashold(self):
        return self.owner.near_origin_threashold 

    @property
    def agenda(self):
        return self.owner.agenda 

    @property
    def colloquy(self):
        return self.owner

    @property
    def is_open(self):
        return self._is_open

    
    def get_near_origin_threashold(self, **kwargs):
        return self._near_origin_threashold

    
    def set_near_origin_threashold(self, **kwargs):
        value = kwargs["value"][0]
        self.colloquy.near_origin_threashold = int(value)
        # raise NotImplementedError(f"{value=} save into parameters")

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return
        
        with tag("h2"):
            text(self.name.title())
        
        with tag("div"):
            path =f"colloquy/near origin threashold"
            with tag("form", method="post"):
                min_value = 0
                max_value = 400
                with tag("label"):
                    text(f"Near origin threashold [{min_value}-{max_value}]: ")
                doc.stag("input", type="number", name="value", value=self.near_origin_threashold, min=min_value, max=max_value, increment=1)
                with tag("button", name="action", value=path):
                    text("set")
            self.actions[path] = self.set_near_origin_threashold
        
        self.agenda.add_html()
            
        with tag("div"):
            doc.stag("hr")
            if not self.colloquy.is_started:
                self._add_html_start()
            else:
                self._add_html_timer()
                self._add_html_stop()
            doc.stag("hr")

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
    
    def _setup(self):
        pass
    
    def _loop(self):
        
        now = datetime.now()
        today = now.strftime("%A").lower()
        
        day = self.agenda.week[today]
        
        print(f"{today=}")
        
        if day.state:
            start, end = day.start, day.end
            assert start and end, "Make sure to start and end working days!"
            current_time = now.time()
            print(f"{current_time=}")            
            print(f"{start=}")
            print(f"{end=}")
            print(f"{start <= current_time < end=}")
            if start <= current_time < end:  
                print(f"{self.colloquy.is_started=}")
                if not self.colloquy.is_started:              
                    print(f"Colloquy is started...")
                    self.colloquy.start()
                # delta = datetime.combine(now.date(), end) - now
            else:
                if self.colloquy.is_started:          
                    print(f"Colloquy is stop...")
                    self.colloquy.stop()
        
        sleep(1)
                    
                # if current_time < start:
                    # delta = datetime.combine(now.date(), start) - now
                # else:
                    # tomorrow = now.date() + timedelta(days=1)
                    # next_day = datetime.combine(tomorrow, time(hour=0, minute=0))
                    # delta = next_day - now
        # else:
            
            # tomorrow = now.date() + timedelta(days=1)
            # next_day = datetime.combine(tomorrow, time(hour=0, minute=0))
            # delta = next_day - now
                    
                    
        # if now is in the agenda range:            
            # self.colloquy.start()
            # sleep(the time until when it needs to stop)
        # else:
            # if self.colloquy.is_started:
                # self.colloquy.stop()
            # sleep(the time until when it needs to stop)
        # raise NotImplementedError(f"Implement the daily trigger. Sleep the good amount of time.")
    
    def _add_html_timer(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("div"):
            text(f"Colloquy will start in [NotImplementedError].")
        # self._write_html_action(value="colloquy/exposition/open", label=self.name, func=self.open)
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="colloquy/exposition/open", label=self.name, func=self.open)

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/start"):
                text(f"Start.")
                self.actions["colloquy/start"] = self.start
            
            
            self._write_html_action(value="colloquy/exposition/close", label="close", func=self.close)

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/stop"):
                text(f"Stop.")
        self.actions["colloquy/stop"] = self.colloquy.stop