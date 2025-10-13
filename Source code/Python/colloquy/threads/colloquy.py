from pathlib import Path
import traceback
from .hardware import Hardware
from virtual_hardware import VirtualHardware
import socket
from threading import Thread, Event, Lock
from server.html_element import HTMLElement
from parameters import Parameters
from parameters import Parameters
from .agenda import Agenda
from .exposition import Exposition
from .tests import Tests
from .logger import Logger as _Logger

class Colloquy(HTMLElement):
    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._is_started = True
        self._owner = owner
        self._actions = {}
        self.path = Path("")
        self._log = Logger(owner=self)
        self._opened = None
        self._items = {}
        self.elements = set()
        self.threads = set()
        self._hardware = None        
        self._params = Parameters(owner=self)
        self._tests = Tests(owner=self)
        self._exposition = Exposition(owner=self)
        self._agenda = Agenda(owner=self, params=self.params["agenda"])
        self._shutdown_event = Event()
        if not self.params.is_calibrated:
            self.params.open()
        
        self.init()

    def __call__(self, environ):
        self._init_html_doc()
        self.write_html(environ)
        return [self.html_doc.getvalue().encode()]

    @property
    def shutdown_event(self):
        return self._shutdown_event
        
    @property
    def stop_event(self):
        return self._shutdown_event

    @property
    def is_started(self):
        return self._is_started
        
    @property
    def near_origin_threashold(self):
        return self._params["near_origin_threashold"]

    @near_origin_threashold.setter
    def near_origin_threashold(self, value):
        self._params["near_origin_threashold"] = value 

    @property
    def hardware(self):
        return self._hardware

    @property
    def params(self):
        return self._params

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        self._opened = value

    @property
    def exposition(self):
        return self._exposition

    @property
    def tests(self):
        return self._tests

    @property
    def agenda(self):
        return self._agenda   

    @property
    def log(self):
        return self._log

    def init(self):
        params = self.params.as_dict()
        hostname = socket.gethostname()
        if hostname == "DESKTOP-MRSLS88":
            self._items["hardware"] = self._hardware = VirtualHardware(owner=self, params=params)
            return

        self._items["hardware"] = self._hardware = Hardware(owner=self, params=params)


    def write_html(self, environ):
        self._parse_data(environ)
        data = self.post_data
        action = data.get("action")
        doc, tag, text = self.html_doc.tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            self._write_html_head()
            
            
            if action == ["shutdown"]:                
                with tag("body"):
                    text("Goodbye !")
                return self.stop()
                
            if action == ["restart"]:                
                with tag("body"):
                    with tag("div"):
                        text("Restarting...")
                    with tag("div"):
                        with tag("a", href=""):
                            text("Click here to see the changes.")
                    
                return self.restart()
                
                

            self._write_body()

    def _write_html_head(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("head"):
            with tag("title"):
                text(f"Hardware of Mobiles")
            doc.asis(
                '<meta name="viewport"'
                ' content="width=device-width,'
                " initial-scale=1,"
                ' interopened-widget=resizes-content" />'
            )

    def _write_body(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("body"):
            with tag("div", style="display: flex; "):
                with tag("h1", style="display: flex; flex: 1; justify-items: center;"):
                    text(
                        f"Colloquy of Mobiles"
                        )

                with tag("form", method="post", style="display: flex;"):
                    with tag("button", name="action", value="shutdown", style="align-self:center;"):
                        text(f"Shutdown.")

                with tag("form", method="post", style="display: flex;"):
                    with tag("button", name="action", value="restart", style="align-self:center;"):
                        text(f"Restart.")

            data = self.post_data

            action = data.get("action")
            str_action = None
            if action:
                str_action = action[0]
            action = self.actions.get(str_action, )
            if action:
                try:
                    action(**data)
                except Exception as e:
                    with tag("div"):
                        with tag("h2"):
                            text(f"Error trying {str_action=}, {action=}!")
                        
                        with tag("pre", ):
                            text(traceback.format_exc())
            try:
                return self._write_root()
            except Exception as e:
                with tag("div"):
                    with tag("h2"):
                        text(f"Error building root html!")
                    
                    with tag("pre", ):
                        text(traceback.format_exc())
            
            # raise NotImplementedError(f"{data=}")

    def _write_root(self, **data):
        doc, tag, text = self.html_doc.tagtext()
        
        if self.opened:
            self.opened.write_html()
            return
        with tag("div"):            
            self.params.write_html()
            self.exposition.write_html()
            self.tests.write_html()
    
    def restart(self):
        self.owner.restart_server = True
    
    def stop(self):
        # self.events.shut.shut_server = True
        self._is_started = False
        self._shutdown_event.set()
        # if self._exposition.is_started:
        self._exposition.stop()
        self._tests.stop()
        
        # self._exposition.join()
        self._tests.join()
            
        if self._hardware.is_started:
            self._hardware.stop()
            print("Waiting hardware thread to stop...")
            self._hardware.join()
        print("... exposition and tests threads stopped.")

    # def _handle_request(self, environ):
        # raise NotImplementedError
        # if not kwargs:
            # action = kwargs.pop("action")[0]

            # self._hardware.actions[action](**kwargs)

        # self._hardware.add_html()

    # def _loop(self, **kwargs):
        # self._started_on = datetime.now()
        # pass
        # raise NotImplementedError(f"for {self.name}, ({kwargs=}) implement the timing!")

class Logger(_Logger):

    def __init__(self, owner):
        self._owner = owner
        self._folder = self._log_folder
        self._path = self._folder / f"root.log"
        self._line_count = None

        assert self._path not in self._instances, f"{self._path=}"
        self._instances[self._path] = self