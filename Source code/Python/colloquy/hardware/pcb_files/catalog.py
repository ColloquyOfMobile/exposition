"""Read-only PCB previews and downloads, available without KiCad."""
from html import escape
import io
import hashlib
import json
import re
import zipfile

from . import gerbers

WEB_FOLDER = gerbers.PRODUCTION_FOLDER / "web"


def fabrication(board):
    return gerbers.PRODUCTION_FOLDER / "assembly" / board.id / f"{board.id}-manufacturing.zip"


def production_bytes(board):
    """Never offer an assembly job for an older PCB or older part selection."""
    package = fabrication(board)
    content = package.read_bytes()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        recorded = json.loads(archive.read("manifest.json"))
        if not {"BOM.csv", "CPL.csv", "gerbers.zip"} <= set(archive.namelist()):
            raise gerbers.PackageError(f"{board.title}: assembly files are missing")
    if (recorded["board"] != board.id
            or recorded["source_sha256"] != gerbers.digest(board.source_path)
            or recorded["parts_sha256"] != gerbers.digest(gerbers.KICAD_FOLDER / "assembly-parts.json")
            or recorded.get("generator_sha256") != gerbers.digest(gerbers.REPO_FOLDER / "export_jlcpcb.py")):
        raise gerbers.PackageError(f"{board.title}: assembly export is stale; run export_jlcpcb.py")
    return content


def html():
    """Home-page furniture; a damaged export must never break the server."""
    try:
        cards = []
        for board in gerbers.load():
            board_id = escape(board.id, quote=True)
            base = f"/pcb/{board_id}"
            try:
                content = production_bytes(board)
                with zipfile.ZipFile(io.BytesIO(content)) as package:
                    recorded = json.loads(package.read("manifest.json"))
                revision = (f'Exported {recorded["exported_at"]}; '
                            f'PCB {recorded["source_sha256"][:10]}; package {hashlib.sha256(content).hexdigest()[:10]}')
                problems = ""
            except Exception as error:
                revision = ""
                problems = f"Production package unavailable: {error}"
            cards.append(
                '<article style="border:1px solid #8886;padding:1rem;max-width:28rem">'
                f'<h3>{escape(board.title)}</h3>'
                f'<a href="{base}/preview"><img src="{base}/preview" '
                f'alt="{escape(board.title, quote=True)} 3D model at 45 degrees" loading="lazy" '
                'style="width:100%;height:180px;object-fit:contain"></a>'
                f'<p>{escape(board.what)}</p>'
                f'<p>{board.copper_layers} copper layers · {escape(board.size)} · '
                f'{board.quantity} needed</p>'
                f'<p><a href="{base}/fabrication">fabrication + SMD BOM/CPL (.zip)</a></p>'
                f'<p><a href="{base}/schematic">wired schematic (SVG)</a></p>'
                f'<p>{escape(revision)}</p>'
                f'<p>{escape(problems)}</p></article>'
            )
        return (
            '<section name="pcb catalog"><h2>PCBs</h2>'
            '<p><a href="/pcb/all/fabrication">download all production packages '
            '(Gerbers, SMD BOM and CPL)</a></p>'
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
        if board_id == "all" and kind == "fabrication":
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
                for board in gerbers.load():
                    package = fabrication(board)
                    archive.writestr(package.name, production_bytes(board))
            content = buffer.getvalue()
            return "200 OK", [("Content-Type", "application/zip"),
                ("Content-Disposition", f'attachment; filename="colloquy-production-{hashlib.sha256(content).hexdigest()[:10]}.zip"'),
                ("Cache-Control", "no-store"), ("Content-Length", str(len(content)))], content
        board = gerbers.find(gerbers.load(), board_id)
        headers = [("Cache-Control", "no-cache")]
        if kind == "fabrication":
            content = production_bytes(board)
            headers += [
                ("Content-Type", "application/zip"),
                ("Content-Disposition", f'attachment; filename="{board.id}-fabrication-{hashlib.sha256(content).hexdigest()[:10]}.zip"'),
            ]
            headers[0] = ("Cache-Control", "no-store")
        elif kind in ("preview", "schematic"):
            suffix = ".png" if kind == "preview" else ".svg"
            path = WEB_FOLDER / board.id / f"{kind}{suffix}"
            # Do not permit a malformed manifest to point outside the export folder.
            if not path.resolve().is_relative_to(WEB_FOLDER.resolve()):
                raise gerbers.PackageError("Invalid PCB file")
            recorded = json.loads(path.with_name("manifest.json").read_text())
            if (recorded["board_sha256"] != gerbers.digest(board.source_path)
                    or recorded["generator_sha256"] != gerbers.digest(gerbers.REPO_FOLDER / "export_pcb_web.py")
                    or (kind == "schematic" and any(
                        gerbers.digest(gerbers.KICAD_FOLDER / name) != digest
                        for name, digest in recorded["schematics"].items()))):
                raise gerbers.PackageError(f"{board.title}: preview export is stale; run export_pcb_web.py")
            content = path.read_bytes()
            headers.append(("Content-Type", "image/png" if kind == "preview" else "image/svg+xml"))
        else:
            raise gerbers.PackageError("Unknown PCB file")
        headers.append(("Content-Length", str(len(content))))
        return "200 OK", headers, content
    except Exception as error:
        return "404 Not Found", [("Content-Type", "text/plain; charset=utf-8")], str(error).encode("utf-8")
