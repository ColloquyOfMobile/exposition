from pathlib import Path
from colloquy.wsgi.item import Item


class Shutdown(Item):
    def __init__(self, owner):
        Item.__init__(self, owner)

    def __call__(self, **kwargs):
        raise NotImplementedError
        self.owner.shut_server = True
        self.owner.start_response('200 OK', [('Content-Type', 'text/plain')])

        yield b'Goodbye!'

    @property
    def name(self):
        return "shutdown"

    # def add_html_link(self):
        # doc, tag, text = self._wsgi.doc.tagtext()
        # with tag("h2",):
            # with tag("a", href=self.path.as_posix()):
                # text("Shudown server.")

    # def open(self):
        # pass

    # def close(self):
        # pass