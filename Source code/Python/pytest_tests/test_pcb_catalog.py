"""PCB home-page files work on both servers, including with the board out."""
import io
import zipfile
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest
from PIL import Image

from colloquy.hardware.pcb_files import catalog, gerbers
from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI


@pytest.mark.parametrize("renderer", [WSGI2, MockWSGI])
def test_home_shows_catalog_but_node_pages_do_not(renderer):
    app = SimpleNamespace(is_simulated=False, repository=SimpleNamespace(auto_update=False))
    request = SimpleNamespace(
        colloquy=app, _root=Path("app"), all_threads=(),
        get_states=lambda *args: {"path": args},
        _html_restart_link=lambda: "", _html_navigation=lambda **kwargs: "",
        _html_recursion=lambda **kwargs: "",
    )
    home = renderer._parse_app(request)[2]
    node = renderer._parse_app(request, "hardware")[2]
    for board in gerbers.load():
        assert f'/pcb/{board.id}/fabrication'.encode() in home
        assert f'/pcb/{board.id}/schematic'.encode() in home
        assert f'/pcb/{board.id}/preview'.encode() in home
    assert b'name="pcb catalog"' not in node


@pytest.mark.parametrize("renderer", [WSGI2, MockWSGI])
def test_files_bypass_tree_and_board_out_gate(renderer):
    request = SimpleNamespace(
        _parse_path=lambda: ["pcb", "backplane", "schematic"],
        _board_is_out=lambda: True, _environ={},
    )
    status, headers, body = renderer._parse(request)
    assert status == "200 OK"
    assert dict(headers)["Content-Type"] == "image/svg+xml"
    ET.fromstring(body)


@pytest.mark.parametrize("board", gerbers.load(), ids=lambda b: b.id)
def test_every_link_returns_a_usable_file(board):
    for kind in ("preview", "schematic", "fabrication"):
        status, headers, body = catalog.response((board.id, kind))
        assert status == "200 OK", body
        assert int(dict(headers)["Content-Length"]) == len(body)
        if kind == "fabrication":
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                assert archive.testzip() is None
                assert {"BOM.csv", "CPL.csv", "gerbers.zip"} <= set(archive.namelist())
                with zipfile.ZipFile(io.BytesIO(archive.read("gerbers.zip"))) as plots:
                    assert any(name.endswith(".drl") for name in plots.namelist())
        elif kind == "preview":
            assert dict(headers)["Content-Type"] == "image/png"
            with Image.open(io.BytesIO(body)) as preview:
                # KiCad on Windows can subtract window borders from the requested size.
                assert preview.width >= 1000 and preview.height >= 700
                preview.verify()
            assert "Content-Disposition" not in dict(headers)
        else:
            assert ET.fromstring(body).tag.endswith("svg")
            assert "Content-Disposition" not in dict(headers)


@pytest.mark.parametrize("board", gerbers.load(), ids=lambda b: b.id)
def test_each_upload_of_an_order_is_its_own_download(board):
    """What JLC's form takes one file at a time, out of the checked package."""
    with zipfile.ZipFile(io.BytesIO(catalog.production_bytes(board))) as package:
        for kind, (name, content_type, attached) in catalog.PACKAGE_FILES.items():
            status, headers, body = catalog.response((board.id, kind))
            assert status == "200 OK", body
            assert body == package.read(name)
            assert dict(headers)["Content-Type"] == content_type
            assert ("Content-Disposition" in dict(headers)) == attached
    with zipfile.ZipFile(io.BytesIO(catalog.response((board.id, "gerbers"))[2])) as plots:
        assert any(name.endswith(".drl") for name in plots.namelist())
    assert catalog.response((board.id, "bom"))[2].decode("utf-8-sig").startswith("Comment,Designator")


@pytest.mark.parametrize("parts", [(), ("backplane",), ("..", "preview"),
    ("backplane", "../schematic"), ("unknown", "preview"),
    ("backplane", "schematic", "extra"), ("C:\\", "preview")])
def test_unknown_files_and_traversal_are_404(parts):
    assert catalog.response(parts)[0] == "404 Not Found"


def test_missing_export_does_not_take_down_server(monkeypatch, tmp_path):
    monkeypatch.setattr(catalog, "WEB_FOLDER", tmp_path)
    assert catalog.response(("backplane", "schematic"))[0] == "404 Not Found"
    assert "Shields backplane" in catalog.html()


@pytest.mark.parametrize("kind", ["preview", "schematic"])
def test_stale_drawings_are_refused(monkeypatch, kind):
    monkeypatch.setattr(gerbers, "digest", lambda path: "changed source")
    status, _, content = catalog.response(("backplane", kind))
    assert status == "404 Not Found"
    assert b"preview export is stale" in content
