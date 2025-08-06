from utils import CustomDoc
import inspect
from .http_element import HTTPElement

class HTMLElement(HTTPElement):

    def __init__(self, owner):
        HTTPElement.__init__(self, owner)
        self._html_doc = None
        self._actions = None
        # self._start_response = None

    @property
    def actions(self):
        if self._actions is None:
            return self.owner.actions
        return self._actions

    @property
    def html_doc(self):
        if self._html_doc is None:
            return self.owner.html_doc
        return self._html_doc

    def _init_html_doc(self):
        self.start_response('200 OK', [('Content-Type', 'text/html')])
        self._html_doc = CustomDoc()

    def _write_html_action(self, value, label, func):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=value):
                text(label)
        # if value in self.actions:
            # lines = ["", f"{value=}"]
            # for key in self.actions:
                # lines.append(
                    # f"- {key=}"
                # )
            # raise ValueError("\n".join(lines))
        # assert value not in self.actions
        self.actions[value] = func