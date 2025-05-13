from utils import CustomDoc

class HTMLElement:

    def __init__(self, owner):
        self._owner = owner
        self._html_doc = None
        self._start_response = None

    @property
    def html_doc(self):
        if self._html_doc is None:
            return self.owner.html_doc
        return self._html_doc

    @property
    def owner(self):
        return self._owner

    @property
    def start_response(self):
        if self._start_response is None:
            return self.owner.start_response
        return self._start_response

    def _init_html_doc(self):
        self.start_response('200 OK', [('Content-Type', 'text/html')])
        self._html_doc = CustomDoc()