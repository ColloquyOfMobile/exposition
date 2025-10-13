from pathlib import Path
import urllib
from wsgiref.simple_server import make_server, WSGIRequestHandler
import os
import webbrowser
import sys
# from .calibration import Calibration
# from .threads import Threads
# from .http_element import HTTPElement
from utils import CustomDoc
from .wsgi import WSGI
from .events import Events


class CustomHandler(WSGIRequestHandler):

    def log_message(self, *args, **kwargs):
        return
        
class Colloquy():
    
    def __init__(self, mode=None):
        self._mode = mode        
        self._events = Events()
        self._wsgi = WSGI(owner=self)
        # self._threads = Threads()
        
        self.run()
    
    @property
    def threads(self):
        return self._threads
    
    @property
    def events(self):
        return self._events

    @property
    def path(self):
        return Path()

    def run(self, ):
        mode = self._mode
        port = 8000
        if Path("Local/logs.txt").exists():
            Path("Local/logs.txt").unlink()
        with make_server("0.0.0.0", port, self._wsgi, handler_class=CustomHandler) as httpd:
            WSGIRequestHandler.log_message = lambda *args, **kwargs: None
            print(f"Serving on port {port}...")
            
            print(f"{mode=}")
            if mode != "restart":
                webbrowser.open(url=f"http://127.0.0.1:{port}", new=2)

            while True:
                httpd.handle_request()
                if self.events.shutdown.is_set():
                    print(f"Shutdown event!")
                    break
                    
            if self.events.restart.is_set():
                print(f"restart event!")
                self.restart()
    
    def restart(self):        
        python = sys.executable
        args = ["main.py", "restart"]
        # args.append()
        os.execl(python, python, *args)