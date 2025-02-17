
class Root():
    def __init__(self, wsgi):
        self._wsgi = wsgi

    def __call__(self, **kwargs):
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
            # with tag("h2",):
                # with tag("a", href="calibration"):
                    # text("Calibration.")

            # with tag("h2",):
                # with tag("a", href="tests"):
                    # text("Tests.")

            for handler in self._wsgi.handlers:
                handler.add_html_link()

            yield doc.read().encode()


    def open(self):
        pass

    def close(self):
        pass