from yattag import Doc, indent


class CustomDoc(Doc):
    def __init__(self):
        Doc.__init__(self)
        self._cursor = 0

    def read(self):
        result = self.result[self._cursor:]
        self._cursor += len(result)
        return "".join(result)