from utils import CustomDoc
from threading import Lock
import inspect
from .http_element import HTTPElement

class HTMLElement(HTTPElement):

    _thread_pool = set()

    def __init__(self, owner):
        HTTPElement.__init__(self, owner)
        self._html_doc = None
        self._actions = None
        self._pool_lock = Lock()
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

    @property
    def thread_count(self):
        return len(self._thread_pool)

    def _add_thread_to_pool(self, value):
        with self._pool_lock:
            self._thread_pool.add(value)

    def iter_thread_pool(self):
        yield from sorted(self._thread_pool, key=lambda x:x.name)

    def _init_html_doc(self):
        self.start_response('200 OK', [('Content-Type', 'text/html')])
        self._html_doc = CustomDoc()

    def _write_html_action(self, value, label, func):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=value):
                text(label)
        self.actions[value] = func

    def _add_html_thread_count(self):
        doc, tag, text = self.html_doc.tagtext()
        if self.thread_count:
            with tag("details",):
                with tag("summary",):
                    text(
                        f"threads: {self.thread_count}"
                        )
                for e in self.iter_thread_pool():
                    with tag("summary",):
                        text(
                            f"{e.name}"
                            )