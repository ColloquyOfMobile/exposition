from colloquy.markdown_document import MarkdownDocument


class CodeDocumentation(MarkdownDocument):
    """View and edit colloquy/CODE_DOCUMENTATION.md straight from the web
    UI, instead of needing a text editor on whichever machine the server
    happens to be running on.

    It was called "scenarios" and sat under `tests`, which said where it
    had been written rather than what it is: it documents `colloquy/`, not
    the scenarios that describe the artwork. It hangs off the root now,
    and the root only offers it off the installation's own machine -
    reading the source is a thing to do while working on the code, and the
    page in the gallery has no use for it. The hardware setup beside it is
    offered everywhere, for exactly the opposite reason.
    """

    file_name = "CODE_DOCUMENTATION.md"
    document_name = "code documentation"
