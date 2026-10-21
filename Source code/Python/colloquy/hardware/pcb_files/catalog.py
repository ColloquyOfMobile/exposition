"""Read-only PCB previews and downloads, available without KiCad."""
from html import escape
import re

from . import gerbers

WEB_FOLDER = gerbers.PRODUCTION_FOLDER / "web"


def fabrication(board):
    return board.source_path.parent / "manufacturing" / f"{board.id}-manufacturing.zip"


def html():
    """Home-page furniture; a damaged export must never break the server."""
    try:
        cards = []
        for board in gerbers.load():
            board_id = escape(board.id, quote=True)
            base = f"/pcb/{board_id}"
            problems = " ".join(gerbers.problems(board))
            cards.append(
                '<article style="border:1px solid #8886;padding:1rem;max-width:28rem">'
                f'<h3>{escape(board.title)}</h3>'
                f'<a href="{base}/preview"><img src="{base}/preview" '
                f'alt="{escape(board.title, quote=True)} PCB preview" loading="lazy" '
                'style="width:100%;height:180px;object-fit:contain"></a>'
                f'<p>{escape(board.what)}</p>'
                f'<p>{board.copper_layers} copper layers · {escape(board.size)} · '
                f'{board.quantity} needed</p>'
                f'<p><a href="{base}/fabrication">fabrication package (.zip)</a></p>'
                f'<p><a href="{base}/schematic">wired schematic (SVG)</a></p>'
                f'<p>{escape(problems)}</p></article>'
            )
        return (
            '<section name="pcb catalog"><h2>PCBs</h2>'
            '<p>Open a preview or schematic full page; use the browser Back button to return.</p>'
            '<div style="display:flex;flex-wrap:wrap;gap:1rem">'
            + "".join(cards) + '</div></section>'
        )
    except Exception as error:
        return f'<p>PCB files unavailable: {escape(str(error))}</p>'


def response(parts):
    """Only named assets of a manifest board are exposed, never arbitrary paths."""
    try:
        if len(parts) != 2:
            raise gerbers.PackageError("Unknown PCB file")
        board_id, kind = parts
        if not re.fullmatch(r"[a-z0-9-]+", board_id):
            raise gerbers.PackageError("Invalid PCB name")
        board = gerbers.find(gerbers.load(), board_id)
        headers = [("Cache-Control", "no-cache")]
        if kind == "fabrication":
            package = fabrication(board)
            content = package.read_bytes() if package.is_file() else gerbers.board_zip(board)
            headers += [
                ("Content-Type", "application/zip"),
                ("Content-Disposition", f'attachment; filename="{board.id}-fabrication.zip"'),
            ]
        elif kind in ("preview", "schematic"):
            path = WEB_FOLDER / board.id / f"{kind}.svg"
            # Do not permit a malformed manifest to point outside the export folder.
            if not path.resolve().is_relative_to(WEB_FOLDER.resolve()):
                raise gerbers.PackageError("Invalid PCB file")
            content = path.read_bytes()
            headers.append(("Content-Type", "image/svg+xml"))
        else:
            raise gerbers.PackageError("Unknown PCB file")
        headers.append(("Content-Length", str(len(content))))
        return "200 OK", headers, content
    except Exception as error:
        return "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], str(error).encode("utf-8")
