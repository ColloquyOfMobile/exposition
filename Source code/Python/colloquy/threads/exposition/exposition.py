from server.html_element import HTMLElement
from time import sleep, time


class Exposition(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner=owner)
        self._name = "exposition"
        self._is_open = False

    @property
    def near_origin_threashold(self):
        return self.owner.near_origin_threashold 

    @property
    def agenda(self):
        return self.owner.agenda 

    # @property
    # def hardware(self):
        # return self.owner.hardware

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
            text(self._name.title())
        
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
                with tag("ul"):
                    with tag("li"):
                        text("400 => around 100 interaction per hour.")
            self.actions[path] = self.set_near_origin_threashold
            doc.stag("hr")
        
        self.agenda.write_html()
        if not self.agenda.is_enabled:            
            with tag("div"):
                doc.stag("hr")
                if not self.hardware.is_started:
                    self._add_html_start()
                else:
                    self._add_html_stop()
                doc.stag("hr")

    
    def stop(self, **kwargs):        
        # self.stop_event.set()
        if self.agenda.is_enabled:
            self.agenda.stop()
            self.agenda.join()
            return
        self.hardware.stop()
        self.hardware.join()
        # ThreadElement.stop(self, **kwargs)     
        # self.stop_event.clear()

    
    def _start(self, **kwargs):        
        # self.stop_event.set()
        # if self.agenda.is_enabled:
            # self.agenda.start()
            # return
        assert not self.agenda.is_enabled
        self.hardware.start()
        # ThreadElement.stop(self, **kwargs)     
        # self.stop_event.clear()

    def open(self, **kwargs):
        if self._is_open:
            return
        self.hardware.connect()
        self.owner.opened = self
        
        self._is_open = True

    def close(self, **kwargs):
        assert not  self.agenda.is_started, (
            f"Stop the exposition run before closing ! This is probably due to an outdated UI... Reload the page without sending the form and retry.")
        if not self._is_open:
            return
        self.hardware.close()
        self._is_open = False
        self.owner.opened = None
   
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/exposition/open", label=self._name, func=self.open)

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="hardware/start"):
                text(f"Start.")
                self.actions["hardware/start"] = self._start
            
            
            self._write_html_action(value="hardware/exposition/close", label="close", func=self.close)

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="hardware/stop"):
                text(f"Stop.")
        self.actions["hardware/stop"] = self.stop