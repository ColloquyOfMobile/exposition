# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_static_files.py

"""Serving a file that can change under the server.

The bug this was written after: Thomas's four board photographs were
replaced on disk with versions carrying his pin labels, the server served
the new bytes to anything that asked, and the page went on drawing the
old ones. Nothing was broken at either end - the browser had been told
`Cache-Control: public, max-age=3600` with no validator beside it, which
does not mean "keep a copy", it means **do not ask again for an hour**.

Every one of these files can change while the server is up: the
photographs, the SVGs a hardware test writes next to its CSV, the
stylesheets somebody is editing on the mock. So the header is a validator
now - an ETag off the file's mtime and size, and `no-cache`, which means
store it and check first. The check is a conditional request answered
with a 304 and no body, to a server on the same machine, which is what
the max-age was ever saving.

Both UIs serve their own static/ and vendor/, so both are tested: this is
one of the fixes that has to be made twice (see CLAUDE.md).
"""
import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI

RENDERERS = (WSGI2, MockWSGI)
IDS = ("installation", "mock")


class FakeWSGI:
    """`_parse_static` reads nothing but the environ."""

    def __init__(self, renderer, environ=None):
        self._environ = environ or {}
        self._parse_static = renderer._parse_static.__get__(self)


@pytest.fixture
def root(tmp_path):
    (tmp_path / "hardware").mkdir()
    return tmp_path


@pytest.fixture
def photograph(root):
    path = root / "hardware" / "a-board.jpg"
    path.write_bytes(b"the first photograph, with no labels on it")
    return path


def serve(renderer, root, *parts, environ=None):
    return FakeWSGI(renderer, environ)._parse_static(root, *parts)


def header(headers, name):
    for key, value in headers:
        if key.lower() == name.lower():
            return value
    return None


# --- the bug ------------------------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_file_replaced_on_disk_is_served_with_a_new_validator(
    renderer, root, photograph
):
    """The whole point. A browser holding the first copy has to be able to
    find out that it is out of date, and the ETag is what tells it."""
    _status, headers, first = serve(renderer, root, "hardware", "a-board.jpg")
    first_etag = header(headers, "ETag")

    photograph.write_bytes(b"the second photograph, with Thomas's pin labels")
    _status, headers, second = serve(renderer, root, "hardware", "a-board.jpg")

    assert second != first
    assert header(headers, "ETag") != first_etag


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_nothing_is_cached_without_asking_first(renderer, root, photograph):
    """`max-age` with no validator is a promise the server cannot keep
    about files it does not control the lifetime of."""
    _status, headers, _body = serve(renderer, root, "hardware", "a-board.jpg")

    cache_control = header(headers, "Cache-Control")

    assert cache_control == "no-cache"
    assert "max-age" not in cache_control


# --- and the cheapness that replaces it ----------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_an_unchanged_file_comes_back_as_304_with_no_body(
    renderer, root, photograph
):
    """What keeps revalidation cheap: the bytes are not sent twice."""
    _status, headers, _body = serve(renderer, root, "hardware", "a-board.jpg")
    etag = header(headers, "ETag")

    status, _headers, body = serve(
        renderer,
        root,
        "hardware",
        "a-board.jpg",
        environ={"HTTP_IF_NONE_MATCH": etag},
    )

    assert status == "304 Not Modified"
    assert body == b""


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_stale_validator_gets_the_file(renderer, root, photograph):
    status, _headers, body = serve(
        renderer,
        root,
        "hardware",
        "a-board.jpg",
        environ={"HTTP_IF_NONE_MATCH": '"something-else"'},
    )

    assert status == "200 OK"
    assert body == photograph.read_bytes()


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_weak_validator_counts_and_so_does_a_list(renderer, root, photograph):
    """Both are ordinary in the header, and neither is worth a stale
    photograph."""
    _status, headers, _body = serve(renderer, root, "hardware", "a-board.jpg")
    etag = header(headers, "ETag")

    for sent in (f"W/{etag}", f'"other", {etag}', f"  {etag}  "):
        status, _headers, _body = serve(
            renderer,
            root,
            "hardware",
            "a-board.jpg",
            environ={"HTTP_IF_NONE_MATCH": sent},
        )
        assert status == "304 Not Modified", sent


# --- unchanged behaviour -------------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_photograph_is_still_served_as_an_image(renderer, root, photograph):
    """Without a type the browser is handed application/octet-stream and
    offers to save it instead of showing it."""
    _status, headers, _body = serve(renderer, root, "hardware", "a-board.jpg")

    assert header(headers, "Content-Type") == "image/jpeg"


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_walk_up_the_tree_is_still_refused(renderer, root, photograph):
    status, _headers, body = serve(renderer, root, "..", "params.json")

    assert status == "404 Not found"
    assert body == b""


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_file_that_is_not_there_is_still_a_404(renderer, root):
    status, _headers, _body = serve(renderer, root, "hardware", "nothing.jpg")

    assert status == "404 Not found"
