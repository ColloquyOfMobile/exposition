from pathlib import Path

class Shutdown():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None
        self.wsgi_path = Path("shutdown")

    def _handle_shutdown(self):
        self._start_response('200 OK', [('Content-Type', 'text/plain')])
        return []

    def __call__(self, **kwargs):
        self._wsgi.shut_server = True
        self._wsgi.start_response('200 OK', [('Content-Type', 'text/plain')])

        yield b'Goodbye!'

    def add_html_link(self):
        doc, tag, text = self._wsgi.doc.tagtext()
        with tag("h2",):
            with tag("a", href=self.wsgi_path.as_posix()):
                text("Shudown server.")

    def open(self):
        pass

    def close(self):
        pass