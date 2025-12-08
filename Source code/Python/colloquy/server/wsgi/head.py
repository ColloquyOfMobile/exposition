from utils import CustomDoc
from colloquy.base import Base


BUTTON_STYLE = """
.int-button {
    display: flex;
    border: 1px solid darkgrey;
    border-radius: 0.2rem;
    place-content: center;
    min-width: 1rem; 
    padding: 0 0.5ch;
    }
.int-button:hover {
    background: lightgrey;
    }
"""


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
            with tag("style"):
                text(BUTTON_STYLE)
                
        return doc.getvalue()

    @property
    def name(self):
        return "head"