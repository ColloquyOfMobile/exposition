from pathlib import Path

class Shutdown():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None
        self.path = Path("shutdown")

    def __eq__(self, other):
        return other.name == self.name

    def __lt__(self, other):
        return self.name < other.name

    def __call__(self, **kwargs):
        self._wsgi.shut_server = True
        self._wsgi.start_response('200 OK', [('Content-Type', 'text/plain')])

        yield b'Goodbye!'

    @property
    def name(self):
        return "shutdown"

    def _handle_shutdown(self):
        self._start_response('200 OK', [('Content-Type', 'text/plain')])
        return []

    def add_html_link(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("h2",):
            with tag("a", href=self.path.as_posix()):
                text("Shudown server.")

    def open(self):
        pass

    def close(self):
        pass