from utils import CustomDoc
from colloquy.base import Base

class Head(Base):

    def __call__(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("head"):
            with tag("title"):
                text(f"Colloquy of Mobiles")
            doc.asis(
                '<meta name="viewport"'
                ' content="width=device-width,'
                " initial-scale=1,"
                ' interopened-widget=resizes-content" />'
            )
        return doc.getvalue()

    @property
    def name(self):
        return "head"