import mimetypes
from colloquy.base import Base

class FileHandler(Base):

    def __call__(self, ):
        file_path = self.owner.request
        try:
            # Open the requested file
            with open(file_path, 'rb') as f:
                content = f.read()

            # Use mimetypes.guess_type to determine the content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'  # Default content type

            self.owner.start_response('200 OK', [('Content-Type', content_type)])
            yield content

        except IOError:
            # File not found
            self.owner.start_response('404 Not Found', [('Content-Type', 'text/plain')])
            message = f'{file_path.as_posix()} not found !'
            
            self.log(message)
            yield message.encode()

    @property
    def name(self):
        return "file handler"