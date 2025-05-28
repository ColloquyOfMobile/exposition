from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse

class HTTPElement:

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

    def __init__(self, owner):
        self._owner = owner
        self._start_response = None
        self._post_data = None

    @property
    def owner(self):
        return self._owner

    @property
    def start_response(self):
        if self._start_response is None:
            return self.owner.start_response
        return self._start_response

    @property
    def post_data(self):
        if self._post_data is None:
            return self.owner.post_data
        return self._post_data


    def _parse_path(self, environ):
        """Parse the path."""
        request_path = environ["PATH_INFO"]
        request_path = unquote(request_path)
        request_path = request_path.strip("/")
        request_path = request_path.encode("iso-8859-1").decode("utf-8")
        request_path = Path(request_path)
        return request_path

    def _parse_data(self, environ):
        """Parse the form data."""
        method = environ.get('REQUEST_METHOD', 'GET')
        content_type = environ.get('CONTENT_TYPE', '')

        # Parse form data for POST requests
        if method == 'POST' and content_type.startswith('multipart/form-data'):
            form_data = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
            data = {key: form_data[key].value for key in form_data}
            raise NotImplementedError()

        elif method == 'POST' and content_type.startswith('application/x-www-form-urlencoded'):
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            post_data = environ['wsgi.input'].read(content_length)
            data = urllib.parse.parse_qs(post_data.decode('utf-8'))

        else:
            data = {}

        self._post_data = data