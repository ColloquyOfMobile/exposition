from pathlib import Path
import webbrowser
from wsgiref.simple_server import make_server, WSGIRequestHandler
from colloquy.base import Base
from .wsgi import WSGI


class CustomHandler(WSGIRequestHandler):

    def log_message(self, *args, **kwargs):
        return

class Server(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._owner = owner
        self._port = None
        owner.add(self)

        self._wsgi = WSGI(owner=self)

    def __repr__(self):
        return f"{type(self).__name__}({self.path.as_posix()})"

    def __call__(self):
        port = 8000

        if self.cli_path is None:
            webbrowser.open(url=f"http://127.0.0.1:{self.port}", new=2)

        elif not self.cli_path.parts:
            webbrowser.open(url=f"http://127.0.0.1:{self.port}", new=2)

        else:
            key, *_ = self.cli_path.parts
            if key != "restart":
                raise NotImplementedError(f"{key=} in {self=}")



        if Path("Local/logs.txt").exists():
            Path("Local/logs.txt").unlink()
        with make_server("0.0.0.0", port, self.wsgi, handler_class=CustomHandler) as httpd:
            # WSGIRequestHandler.log_message = lambda *args, **kwargs: None
            print(f"Serving on port {port}...")

            while True:
                httpd.handle_request()
                if self.events.shutdown.is_set():
                    print(f"Shutdown event!")
                    break

            if self.events.restart.is_set():
                print(f"restart event!")
                self.owner.restart()

    @property
    def name(self):
        return "server"

    @property
    def cli_path(self):
        if self.owner.cli_path is None:
            return None
        return self.owner.cli_path.relative_to(self.path)

    @property
    def owner(self):
        return self._owner

    @property
    def port(self):
        return 8000

    @property
    def wsgi(self):
        return self._wsgi

    @property
    def path(self):
        return self.owner.path / self.name
