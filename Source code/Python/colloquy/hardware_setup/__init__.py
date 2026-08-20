from colloquy.markdown_document import MarkdownDocument


class HardwareSetup(MarkdownDocument):
    """View and edit colloquy/HARDWARE_SETUP.md from the page.

    Deliberately **not** gated by is_simulated, unlike the code
    documentation next to it. This is the document you want open on the
    machine that is wired to the thing you are wiring - which is the
    installation's own, the one place the code documentation is no use.
    """

    file_name = "HARDWARE_SETUP.md"
    document_name = "hardware setup"
