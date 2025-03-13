from pathlib import Path
from tests import Tests
from develop import Develop
from .file_handler import FileHandler
from .shutdown import Shutdown

class Root():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self.path = Path("")
        self.active = None
        self.file_handler = FileHandler(wsgi=wsgi)
        handlers = [
            Shutdown(wsgi=wsgi),
            Tests(wsgi=wsgi),
            Develop(wsgi=wsgi),
        ]
        self.handlers = {
            handler.path: handler
            for handler in handlers
            }

    def __call__(self, **kwargs):
        wsgi = self._wsgi

        if self._wsgi.path != self.path:
            self.activate()
            yield from self.active(**kwargs)
            return

        if self.active is not None:
            self.active.close()
            self.active = None

        doc, tag, text = self._wsgi.doc.tagtext()
        self._wsgi.start_response('200 OK', [('Content-Type', 'text/html')])

        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            with tag("head"):
                with tag("title"):
                    text(f"Colloquy of Mobiles")
                doc.asis(
                    '<meta name="viewport"'
                    ' content="width=device-width,'
                    " initial-scale=1,"
                    ' interactive-widget=resizes-content" />'
                )

            for response in self._write_body(**kwargs):
                yield response

        response = doc.read()
        yield response.encode()

    def _write_body(self, **kwargs):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("body"):
            with tag("h1",):
                text("Colloquy of Mobiles")

            for handler in sorted(self.handlers.values()):
                handler.add_html_link()

            yield doc.read().encode()

    def activate(self):
        path = Path(*self._wsgi.path.parts[:1])
        if self.active is not None:
            if self.active.path == path:
                return
            self.active.close()
        self.active = self.handlers.get(path, self.file_handler)
        self.active.open()