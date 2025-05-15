from utils import CustomDoc
import inspect

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

    @staticmethod
    def retrieve_call_origin():
        # Get the current call stack
        stack = inspect.stack()

        # stack[0] = this function (retrieve_call_origin)
        # stack[1] = the load() method
        # stack[2] = the function that called load() → this is what we want
        if len(stack) > 2:
            caller_frame = stack[2]
            caller_filename = caller_frame.filename  # File where the call happened
            caller_lineno = caller_frame.lineno      # Line number of the call
            return f"{caller_filename}:{caller_lineno}"
        else:
            return "unknown origin"

    def _init_html_doc(self):
        self.start_response('200 OK', [('Content-Type', 'text/html')])
        self._html_doc = CustomDoc()