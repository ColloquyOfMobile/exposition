from server.html_element import HTMLElement



class Exposition(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._is_open = False
        self.name = "exposition"

    @property
    def colloquy(self):
        return self.owner

    @property
    def is_open(self):
        return self._is_open

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return

        doc.stag("hr")
        if not self.colloquy.is_started:
            self._add_html_start()
        else:
            self._add_html_stop()
        doc.stag("hr")

    def open(self, **kwargs):
        if self._is_open:
            return
        self.colloquy.open()
        self.owner.opened = self
        # self._actions = {}
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        self.colloquy.close()
        self._is_open = False
        self.owner.opened = None
        # raise NotImplementedError
        # if self._is_open:
            # return
        # self.owner.opened = self
        # # self._actions = {}
        # self._is_open = True
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="colloquy/exposition/open", label=self.name, func=self.open)

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/start"):
                text(f"Start.")
                self.actions["colloquy/start"] = self.colloquy.start
            
            
            self._write_html_action(value="colloquy/exposition/close", label="close", func=self.close)
            # with tag("button", name="action", value="colloquy/close"):
                # text(f"close.")
                # self.actions["colloquy/exposition/close"] = self.close

        # self._add_html_interaction()

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/stop"):
                text(f"Stop.")
        self.actions["colloquy/stop"] = self.colloquy.stop