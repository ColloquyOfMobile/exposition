"""Ordering the PCBs at JLCPCB: the statuses, the five steps, the walk.

A board's status is a note in params, written only by a press on the
order pages, and the walk goes on past a board that went wrong. What is
pinned hardest is that one press changes one board, that nothing raised
leaves the route (outside a command that emergency-stops the
installation), and that what is served back as a screenshot is an image.

No live server, no real params: a dict stands in for `params["pcb
orders"]` and `tmp_path` for the screenshot folder.
"""
import io
import re
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from colloquy.hardware.pcb_files import catalog, gerbers, orders
from colloquy.server2.wsgi2 import WSGI2

BOARDS = gerbers.load()
# Has a CRLF and a boundary-like run in it, which a multipart parser that
# split on lines would mangle.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\r\n--x\r\n\xff" * 64


def get(parts, book, folder):
    return orders.response(tuple(parts), {"REQUEST_METHOD": "GET"}, book, folder)


def post(parts, book, folder, fields=None, files=None):
    boundary = "colloquy-test-boundary-3f9c2e"
    body = b""
    for name, value in (fields or {}).items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
                 + value.encode("utf-8") + b"\r\n")
    for name, (filename, data) in (files or {}).items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                 f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                 + data + b"\r\n")
    body += f"--{boundary}--\r\n".encode()
    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": f"multipart/form-data; boundary={boundary}",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    return orders.response(tuple(parts), environ, book, folder)


def location(answer):
    status, headers, _ = answer
    assert status == "303 See Other"
    return dict(headers)["Location"]


# --- the records --------------------------------------------------------


def test_a_board_nobody_has_pressed_for_is_waiting():
    assert {orders.status_of({}, board.id) for board in BOARDS} == {orders.WAITING}
    assert orders.status_of(None, BOARDS[0].id) == orders.WAITING


def test_a_hand_typed_status_is_an_error_not_waiting():
    """"Ordered" with a capital must not put a bought board back in the walk."""
    book = {BOARDS[0].id: {"status": "Ordered"}, BOARDS[1].id: "nonsense"}
    assert orders.status_of(book, BOARDS[0].id) == orders.ERROR
    assert orders.status_of(book, BOARDS[1].id) == orders.ERROR
    assert "Ordered" in orders.record(book, BOARDS[0].id)["note"]


def test_the_book_lives_in_params_and_is_none_without_them():
    params = {}
    assert orders.book_of(SimpleNamespace(params=params)) == {}
    assert orders.PARAMS_KEY in params
    assert orders.book_of(SimpleNamespace()) is None
    assert orders.book_of(SimpleNamespace(params={orders.PARAMS_KEY: [1]})) is None


# --- the walk -----------------------------------------------------------


def test_the_walk_goes_on_past_a_board_that_went_wrong(tmp_path):
    book = {}
    first, second, third = BOARDS[:3]

    assert location(post((first.id, "cart"), book, tmp_path)) == f"/pcb-order/{second.id}/1"
    assert book[first.id]["status"] == orders.IN_CART
    assert book[first.id]["pcb"] == first.source_sha256
    assert book[first.id]["uploads"] == orders.uploads(first)

    answer = post((second.id, "error"), book, tmp_path,
                  {"step": "3", "note": "écran: BOM refusée"}, {"screenshot": ("shot.png", PNG)})
    assert location(answer) == f"/pcb-order/{third.id}/1"
    found = book[second.id]
    assert found["status"] == orders.ERROR
    assert found["note"] == "écran: BOM refusée"
    assert (found["step"], found["step title"]) == (3, orders.STEPS[2])
    assert (tmp_path / found["screenshot"]).read_bytes() == PNG

    status, headers, body = get(("screenshot", found["screenshot"]), book, tmp_path)
    assert status == "200 OK" and dict(headers)["Content-Type"] == "image/png"
    assert body == PNG

    # Nobody else was touched, and a new walk starts with the one in error.
    assert set(book) == {first.id, second.id}
    assert orders.next_url(BOARDS, book) == f"/pcb-order/{second.id}/1"


def test_the_last_board_ends_on_the_cart(tmp_path):
    assert location(post((BOARDS[-1].id, "cart"), {}, tmp_path)) == "/pcb-order/done"


def test_a_walk_skips_what_is_in_the_cart_or_ordered():
    book = {BOARDS[1].id: {"status": orders.IN_CART}, BOARDS[2].id: {"status": orders.ORDERED}}
    assert orders.next_url(BOARDS, book, BOARDS[0]) == f"/pcb-order/{BOARDS[3].id}/1"


def test_ordered_marks_the_cart_and_only_the_cart(tmp_path):
    book = {BOARDS[0].id: {"status": orders.IN_CART, "pcb": "abc", "uploads": {"cpl": "c"},
                           "changed at": "2026-10-21T10:00:00"},
            BOARDS[1].id: {"status": orders.ERROR, "note": "refused"}}
    assert location(post(("ordered",), book, tmp_path, {"order number": " W2026102112 "})) == "/pcb-order/done"
    assert book[BOARDS[0].id]["status"] == orders.ORDERED
    assert book[BOARDS[0].id]["order number"] == "W2026102112"
    assert book[BOARDS[0].id]["pcb"] == "abc"
    assert book[BOARDS[0].id]["uploads"] == {"cpl": "c"}
    assert book[BOARDS[0].id]["in the cart at"] == "2026-10-21T10:00:00"
    assert book[BOARDS[1].id] == {"status": orders.ERROR, "note": "refused"}


def test_reset_puts_a_board_back_to_waiting(tmp_path):
    book = {BOARDS[0].id: {"status": orders.ORDERED}}
    assert location(post((BOARDS[0].id, "reset"), book, tmp_path)) == "/pcb-order/done"
    assert orders.status_of(book, BOARDS[0].id) == orders.WAITING


@pytest.mark.parametrize("action", ["cart", "error", "reset", "again"])
def test_a_link_or_a_reload_to_a_press_changes_nothing(tmp_path, action):
    book = {}
    assert location(get((BOARDS[0].id, action), book, tmp_path)) == f"/pcb-order/{BOARDS[0].id}/1"
    assert book == {}


def test_starting_again_puts_the_cart_back_in_the_walk_from_the_first_board(tmp_path):
    book = {BOARDS[0].id: {"status": orders.ERROR, "note": "white refused"},
            BOARDS[1].id: {"status": orders.ORDERED},
            BOARDS[2].id: {"status": orders.IN_CART, "pcb": "abc"},
            BOARDS[3].id: {"status": orders.IN_CART}}
    assert location(post(("start-again",), book, tmp_path)) == f"/pcb-order/{BOARDS[0].id}/1"
    # The error keeps what its next attempt starts from; the bought stays bought.
    assert book[BOARDS[0].id] == {"status": orders.ERROR, "note": "white refused"}
    assert book[BOARDS[1].id] == {"status": orders.ORDERED}
    assert orders.status_of(book, BOARDS[2].id) == orders.WAITING
    assert orders.status_of(book, BOARDS[3].id) == orders.WAITING
    assert orders.next_url(BOARDS, book, BOARDS[0]) == f"/pcb-order/{BOARDS[2].id}/1"


def test_a_link_to_start_again_changes_nothing(tmp_path):
    book = {BOARDS[0].id: {"status": orders.IN_CART}}
    assert location(get(("start-again",), book, tmp_path)) == "/pcb-order"
    assert orders.status_of(book, BOARDS[0].id) == orders.IN_CART


@pytest.mark.parametrize("page", [(), ("done",)])
def test_start_again_is_offered_while_something_is_in_the_cart(page, tmp_path):
    book = {BOARDS[2].id: {"status": orders.IN_CART}}
    assert 'action="/pcb-order/start-again"' in get(page, book, tmp_path)[2].decode()
    assert 'action="/pcb-order/start-again"' not in get(page, {}, tmp_path)[2].decode()


def test_again_walks_one_board_from_its_first_step(tmp_path):
    book = {BOARDS[2].id: {"status": orders.IN_CART}, BOARDS[3].id: {"status": orders.IN_CART}}
    assert location(post((BOARDS[2].id, "again"), book, tmp_path)) == f"/pcb-order/{BOARDS[2].id}/1"
    assert orders.status_of(book, BOARDS[2].id) == orders.WAITING
    assert orders.status_of(book, BOARDS[3].id) == orders.IN_CART


def test_without_records_a_press_is_refused_before_anything_is_kept(tmp_path):
    status, _, body = post((BOARDS[0].id, "error"), None, tmp_path,
                           {"step": "1", "note": "x"}, {"screenshot": ("shot.png", PNG)})
    assert status == "409 Conflict" and b"no order records" in body
    assert list(tmp_path.iterdir()) == []


# --- what went into the cart --------------------------------------------


def a_package(plot=b"X0Y0D01*", cpl=b"Designator,Rotation\nR1,0\n", stamp="2026-10-22T10:00:00"):
    """A package as `catalog.production_bytes` hands it over, with the
    time of the export in the comments of both plots, as KiCad writes it."""
    plots = io.BytesIO()
    with zipfile.ZipFile(plots, "w") as archive:
        archive.writestr("b-F_Cu.gtl", f"G04 #@! TF.CreationDate,{stamp}*\r\n%FSLAX46Y46*%\r\n".encode() + plot)
        archive.writestr("b-PTH.drl", f"; DRILL file {{KiCad 9.0.7}} date {stamp}\nM48\n".encode())
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("gerbers.zip", plots.getvalue())
        archive.writestr("BOM.csv", b"Comment,Designator\n100K,R1\n")
        archive.writestr("CPL.csv", cpl)
    return package.getvalue()


def serve(monkeypatch, content):
    monkeypatch.setattr(catalog, "production_bytes", lambda board: content)


def test_a_re_export_of_an_unchanged_board_uploads_the_same_files(monkeypatch):
    serve(monkeypatch, a_package())
    before = orders.uploads(BOARDS[0])
    serve(monkeypatch, a_package(stamp="2026-10-23T09:00:00"))
    assert orders.uploads(BOARDS[0]) == before


def test_each_upload_is_compared_on_its_own(monkeypatch):
    serve(monkeypatch, a_package())
    kept = {"status": orders.IN_CART, "uploads": orders.uploads(BOARDS[0])}
    assert orders.changes_since_cart(kept, BOARDS[0]) == ()
    serve(monkeypatch, a_package(cpl=b"Designator,Rotation\nR1,270\n"))
    assert orders.changes_since_cart(kept, BOARDS[0]) == ("CPL",)
    serve(monkeypatch, a_package(plot=b"X1Y0D01*", cpl=b"Designator,Rotation\nR1,270\n"))
    assert orders.changes_since_cart(kept, BOARDS[0]) == ("Gerbers", "CPL")


def test_the_cart_says_which_board_is_no_longer_what_the_package_holds(monkeypatch, tmp_path):
    serve(monkeypatch, a_package())
    book = {}
    post((BOARDS[0].id, "cart"), book, tmp_path)
    page = get(("done",), book, tmp_path)[2].decode()
    assert "earlier revision" not in page and "order it again" not in page
    assert "only its layout" not in page

    serve(monkeypatch, a_package(cpl=b"Designator,Rotation\nR1,270\n"))
    page = get(("done",), book, tmp_path)[2].decode()
    assert "the CPL has changed since it went in the cart" in page
    assert "1 of them may not be what the package holds now" in page
    assert f'action="/pcb-order/{BOARDS[0].id}/again"' in page
    assert "the CPL has changed" in orders.catalog_html(book)


def test_a_cart_from_before_the_uploads_were_kept_says_what_it_compares():
    book = {BOARDS[0].id: {"status": orders.IN_CART, "pcb": BOARDS[0].source_sha256}}
    page = orders.catalog_html(book)
    assert "only its layout is compared" in page and "earlier revision" not in page


def test_a_package_that_cannot_be_read_is_said_not_raised(monkeypatch, tmp_path):
    def refuse(board):
        raise gerbers.PackageError("assembly export is stale")

    monkeypatch.setattr(catalog, "production_bytes", refuse)
    book = {BOARDS[0].id: {"status": orders.IN_CART, "uploads": {"gerbers": "abc"}}}
    page = get(("done",), book, tmp_path)[2].decode()
    assert "cannot be compared with what went in the cart: assembly export is stale" in page
    # Nor is a press for it kept as in the cart.
    status, _, body = post((BOARDS[1].id, "cart"), book, tmp_path)
    assert status == "409 Conflict" and b"order it again once the package is back" in body
    assert BOARDS[1].id not in book


# --- screenshots --------------------------------------------------------


def test_only_an_image_is_kept(tmp_path):
    book = {}
    post((BOARDS[0].id, "error"), book, tmp_path, {"step": "2", "note": "see attached"},
         {"screenshot": ("shot.png", b"<html><script>alert(1)</script></html>")})
    assert book[BOARDS[0].id]["screenshot"] == ""
    assert "was not kept" in book[BOARDS[0].id]["note"]
    assert list(tmp_path.iterdir()) == []


def test_no_screenshot_and_no_note_still_records_the_error(tmp_path):
    book = {}
    post((BOARDS[0].id, "error"), book, tmp_path, {"step": "1", "note": "  "},
         {"screenshot": ("", b"")})
    assert book[BOARDS[0].id]["note"] == "(no note)"
    assert book[BOARDS[0].id]["screenshot"] == ""


@pytest.mark.parametrize("name", ["../params.json", "..", "x.png", "backplane-20261021-101010.html"])
def test_only_screenshot_names_are_served(tmp_path, name):
    (tmp_path / "x.png").write_bytes(PNG)
    assert get(("screenshot", name), {}, tmp_path)[0] == "409 Conflict"


def test_a_screenshot_is_served_as_what_its_bytes_say(tmp_path):
    name = "backplane-20261021-101010.png"
    (tmp_path / name).write_bytes(b"GIF89a" + b"\x00" * 16)
    assert dict(get(("screenshot", name), {}, tmp_path)[1])["Content-Type"] == "image/gif"


def test_an_urlencoded_form_is_read_too():
    body = b"order+number=W1&step=2"
    environ = {"CONTENT_TYPE": "application/x-www-form-urlencoded",
               "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
    assert orders.read_form(environ) == ({"order number": "W1", "step": "2"}, {})


def test_a_huge_upload_is_refused_unread(tmp_path):
    environ = {"REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(orders.MAX_UPLOAD_BYTES + 1),
               "CONTENT_TYPE": "multipart/form-data; boundary=x", "wsgi.input": None}
    book = {}
    assert orders.response((BOARDS[0].id, "error"), environ, book, tmp_path)[0] == "409 Conflict"
    assert book == {}


# --- the pages ----------------------------------------------------------


@pytest.mark.parametrize("board", BOARDS, ids=lambda b: b.id)
@pytest.mark.parametrize("step", range(1, len(orders.STEPS) + 1))
def test_every_step_of_every_board_has_its_page(board, step, tmp_path):
    status, _, body = get((board.id, str(step)), {}, tmp_path)
    page = body.decode()
    assert status == "200 OK"
    # The board being worked on, on every page.
    assert f'src="/pcb/{board.id}/preview"' in page
    assert board.title in page
    assert f"{step}. {orders.STEPS[step - 1]}" in page
    # Something went wrong, on every page; next, on every page but the last.
    assert f'action="/pcb-order/{board.id}/error"' in page
    assert 'enctype="multipart/form-data"' in page and 'name="screenshot"' in page
    if step < len(orders.STEPS):
        assert f'class="button" href="/pcb-order/{board.id}/{step + 1}"' in page
    else:
        assert f'action="/pcb-order/{board.id}/cart"' in page


@pytest.mark.parametrize("board", BOARDS, ids=lambda b: b.id)
def test_each_step_offers_what_it_asks_to_upload(board, tmp_path):
    found = orders.package(board)
    assert f"/pcb/{board.id}/gerbers" in get((board.id, "1"), {}, tmp_path)[2].decode()
    options = get((board.id, "2"), {}, tmp_path)[2].decode()
    assert orders.COLOUR in options
    assert f"at least {board.quantity}" in options
    files = get((board.id, "3"), {}, tmp_path)[2].decode()
    if found.smd_count:
        assert f"/pcb/{board.id}/bom" in files and f"/pcb/{board.id}/cpl" in files
        assert all(row["LCSC Part #"] in files for row in found.bom)
    else:
        assert "ordered bare" in files and f"/pcb/{board.id}/bom" not in files


def test_every_board_has_its_checks_and_every_source_is_a_document():
    assert {board.id for board in BOARDS} <= set(orders.CHECKS)
    for board_id, checks in orders.CHECKS.items():
        for _, source in checks + orders.COMMON_CHECKS:
            for document in re.findall(r"[^;]+?\.md", source.format(board=board_id)):
                assert (gerbers.KICAD_FOLDER / document.strip()).is_file(), (board_id, document)


def test_a_package_that_cannot_be_offered_has_no_next(monkeypatch, tmp_path):
    def refuse(board):
        raise gerbers.PackageError(f"{board.title}: assembly export is stale")

    monkeypatch.setattr(catalog, "production_bytes", refuse)
    status, _, body = get((BOARDS[0].id, "2"), {}, tmp_path)
    page = body.decode()
    assert status == "200 OK"
    assert "cannot be ordered from this checkout" in page
    assert f'class="button" href="/pcb-order/{BOARDS[0].id}/3"' not in page
    assert '<details class="error" name="something went wrong" open>' in page


def test_a_board_already_in_the_cart_says_so(tmp_path):
    book = {BOARDS[0].id: {"status": orders.IN_CART, "pcb": BOARDS[0].source_sha256}}
    assert b"orders it twice" in get((BOARDS[0].id, "5"), book, tmp_path)[2]


def test_the_overview_begins_with_the_first_board_still_to_order(tmp_path):
    book = {BOARDS[0].id: {"status": orders.ORDERED}}
    page = get((), book, tmp_path)[2].decode()
    assert f'href="/pcb-order/{BOARDS[1].id}/1"' in page
    everything = {board.id: {"status": orders.ORDERED} for board in BOARDS}
    assert b"Nothing is waiting" in get((), everything, tmp_path)[2]


def test_the_cart_page_lists_the_cart_and_draws_the_errors(tmp_path):
    book = {BOARDS[0].id: {"status": orders.IN_CART},
            BOARDS[1].id: {"status": orders.ERROR, "note": "white refused", "step": 2,
                           "screenshot": "x-20261021-101010.png"}}
    page = get(("done",), book, tmp_path)[2].decode()
    assert "mark the 1 PCBs in the cart as ordered" in page
    assert "white refused" in page
    assert '<img class="shot" src="/pcb-order/screenshot/x-20261021-101010.png"' in page


@pytest.mark.parametrize("parts", [("nope", "1"), (BOARDS[0].id, "6"), (BOARDS[0].id, "0"),
                                   ("a", "b", "c"), (BOARDS[0].id,), ("..", "1")])
def test_an_unknown_page_is_a_page_not_an_exception(parts, tmp_path):
    assert get(parts, {}, tmp_path)[0] == "404 Not Found"


def test_nothing_raised_leaves_the_route(monkeypatch, tmp_path):
    def broken(*args, **kwargs):
        raise RuntimeError("merged badly")

    monkeypatch.setattr(gerbers, "load", broken)
    status, _, body = get((), {}, tmp_path)
    assert status == "500 Internal Server Error" and b"merged badly" in body


# --- on the home page, and through the server ---------------------------


def test_each_card_carries_its_status_and_the_catalog_its_order_now():
    stale = {"status": orders.IN_CART, "pcb": "an older layout"}
    page = orders.catalog_html({BOARDS[0].id: stale})
    assert page.count('name="order status"') == len(BOARDS)
    assert page.count(orders.WAITING) == len(BOARDS) - 1
    assert "an earlier revision" in page
    assert 'href="/pcb-order"' in page
    # The mock keeps no records: its catalog is as it was.
    assert 'href="/pcb-order"' not in orders.catalog_html(None)


def test_the_home_page_offers_order_now():
    app = SimpleNamespace(is_simulated=False, repository=SimpleNamespace(auto_update=False),
                          params={})
    request = SimpleNamespace(
        colloquy=app, _root=Path("app"), all_threads=(),
        get_states=lambda *args: {"path": args},
        _html_restart_link=lambda: "", _html_navigation=lambda **kwargs: "",
        _html_recursion=lambda **kwargs: "",
    )
    assert b'href="/pcb-order"' in WSGI2._parse_app(request)[2]


def test_the_order_bypasses_the_board_out_gate():
    """Ordering is what the standby page is for: its presses are POSTs,
    which the gate otherwise sends back to /."""
    book = {}
    request = SimpleNamespace(
        _parse_path=lambda: ("pcb-order", BOARDS[0].id, "cart"),
        _board_is_out=lambda: True,
        _environ={"REQUEST_METHOD": "POST", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO()},
        colloquy=SimpleNamespace(params={orders.PARAMS_KEY: book}),
    )
    assert location(WSGI2._parse(request)) == f"/pcb-order/{BOARDS[1].id}/1"
    assert book[BOARDS[0].id]["status"] == orders.IN_CART
