from .utils import CustomDoc

class Root():
    def __init__(self, wsgi):
        self._wsgi = wsgi
        self._doc = None

    def __call__(self, **kwargs):
        self._doc = CustomDoc()
        doc, tag, text = self._doc.tagtext()
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
        doc, tag, text = self._doc.tagtext()
        with tag("body"):
            with tag("h1",):
                text("Colloquy of Mobiles")
            with tag("h2",):
                with tag("a", href="calibration"):
                    text("Calibration.")

            with tag("h2",):
                with tag("a", href="tests"):
                    text("Tests.")

            with tag("h2",):
                with tag("a", href="TATU"):
                    text("TATU.")

            yield doc.read().encode()


    def open(self):
        pass

    def close(self):
        pass