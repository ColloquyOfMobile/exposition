import mimetypes

class FileHandler():
    def __init__(self, wsgi):
        self._wsgi = wsgi

    def __call__(self, **kwargs):
        file_path = self._wsgi.path
        try:
            # Open the requested file
            with open(file_path, 'rb') as f:
                content = f.read()

            # Use mimetypes.guess_type to determine the content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'  # Default content type

            self._wsgi.start_response('200 OK', [('Content-Type', content_type)])
            yield content

        except IOError:
            # File not found
            self._wsgi.start_response('404 Not Found', [('Content-Type', 'text/plain')])
            message = f'{file_path.as_posix()} not found !'
            print(message)
            yield message.encode()


    def open(self):
        pass

    def close(self):
        pass