# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware/test_pcb_files.py

"""The two downloads: the fabrication package, and the KiCad projects.

The first half is a check on **files in the repository**, not on code.
The Gerbers under `CAD/KiCad/production/` are plotted on a machine that
has KiCad and committed, and the machine that hands them out has none -
so nothing at the point of download can tell a package plotted from last
week's layout from a current one, except the digest the manifest keeps.
A board edited without `py export_gerbers.py` being run again fails here,
which is the same arrangement as the drawings under `static/hardware/`.

The second half is the arithmetic of the packaging, run against
throwaway folders.
"""
import io
import json
import zipfile

import pytest

from colloquy.hardware.pcb_files import gerbers, kicad_projects


@pytest.fixture(scope="module")
def boards():
    return gerbers.load()


# --- the package in the repository ---------------------------------------


def test_there_is_a_package(boards):
    assert boards, "run `py export_gerbers.py`"


def test_every_file_the_manifest_names_is_there(boards):
    for board in boards:
        assert gerbers.missing_files(board) == (), board.id


def test_every_board_has_the_layers_a_fab_needs(boards):
    """Both coppers, both masks, both legends, the outline and a drill
    file - and the two inner coppers on a four-layer board, without which
    a fab makes a two-layer board out of a four-layer design."""
    for board in boards:
        assert gerbers.missing_layers(board) == (), board.id


def test_no_package_is_older_than_its_board(boards):
    """The one that fails when a board is edited and not re-plotted."""
    stale = [board.source for board in boards if gerbers.is_stale(board)]

    assert stale == [], "re-run `py export_gerbers.py`"


def test_nothing_was_plotted_over_a_failing_rule_check(boards):
    for board in boards:
        assert (board.drc_errors, board.unconnected) == (0, 0), board.id


def test_every_board_has_a_size_and_a_thickness(boards):
    """What the order form asks for. A zero here is a manifest that was
    written without reading the plot."""
    for board in boards:
        assert board.width_mm > 0 and board.height_mm > 0, board.id
        assert board.thickness_mm > 0, board.id
        assert board.smallest_drill_mm > 0, board.id
        assert board.quantity >= 1, board.id


def test_the_documents_a_package_points_at_exist(boards):
    for board in boards:
        for name in board.read_first + board.assembly:
            assert (gerbers.KICAD_FOLDER / name).is_file(), f"{board.id}: {name}"


def test_board_ids_are_safe_in_a_url_and_a_file_name(boards):
    """An id is a path segment of /download/gerbers/<id> and the middle
    of a zip's name."""
    ids = [board.id for board in boards]

    assert len(set(ids)) == len(ids)
    for board_id in ids:
        assert board_id.replace("-", "").isalnum() and board_id == board_id.lower()


# --- what the zips hold --------------------------------------------------


def test_a_boards_zip_is_flat_and_holds_only_its_plots(boards):
    """Both fabs read the layer off the file name; anything else in the
    zip is one more file for an upload form not to recognise."""
    board = boards[0]
    names = zipfile.ZipFile(io.BytesIO(gerbers.board_zip(board))).namelist()

    assert sorted(names) == sorted(board.files)
    assert all("/" not in name for name in names)


def test_the_package_holds_a_zip_per_board_and_says_what_they_are(boards):
    package = zipfile.ZipFile(io.BytesIO(gerbers.package_zip(boards, "abc1234")))
    names = package.namelist()

    for board in boards:
        assert board.zip_name in names
        # A real zip inside, not a renamed folder.
        inner = zipfile.ZipFile(io.BytesIO(package.read(board.zip_name)))
        assert inner.testzip() is None

    text = package.read("README.txt").decode("utf-8")
    assert "abc1234" in text
    for board in boards:
        assert board.zip_name in text
        assert f"{board.copper_layers} copper layers" in text
        assert f"the piece needs {board.quantity}" in text


def test_the_readme_does_not_call_a_plot_a_release(boards):
    """Every one of these designs lists physical checks still open. The
    package carries those documents and says to read them."""
    text = gerbers.readme(boards)

    assert "BEFORE ORDERING" in text
    assert "still" in text and "open" in text


# --- the manifest, read defensively --------------------------------------


def make_board(tmp_path, monkeypatch, files=("b-F_Cu.gtl",), layers=2):
    """A one-board package in a throwaway folder."""
    kicad = tmp_path / "KiCad"
    production = kicad / "production"
    (production / "b").mkdir(parents=True)
    (kicad / "b.kicad_pcb").write_bytes(b"(kicad_pcb)\n")
    for name in files:
        (production / "b" / name).write_bytes(b"G04*\n")

    monkeypatch.setattr(gerbers, "KICAD_FOLDER", kicad)
    monkeypatch.setattr(gerbers, "PRODUCTION_FOLDER", production)

    manifest = production / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "boards": [
                    {
                        "id": "b",
                        "source": "b.kicad_pcb",
                        "source sha256": gerbers.digest(kicad / "b.kicad_pcb"),
                        "copper layers": layers,
                        "files": list(files),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest, kicad


def test_a_missing_manifest_is_a_sentence_not_a_traceback(tmp_path):
    with pytest.raises(gerbers.PackageError, match="export_gerbers"):
        gerbers.load(tmp_path / "manifest.json")


@pytest.mark.parametrize("content", ["", "{", "[]", '{"boards": [{}]}', '{"boards": []}'])
def test_a_broken_manifest_is_a_sentence_not_a_traceback(tmp_path, content):
    """It is a file in a working tree: a merge or an editor can leave it
    in any state, and the page that reads it is the front page."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(content, encoding="utf-8")

    with pytest.raises(gerbers.PackageError):
        gerbers.load(manifest)


def test_a_sparse_entry_still_loads(tmp_path, monkeypatch):
    manifest, _kicad = make_board(tmp_path, monkeypatch)

    (board,) = gerbers.load(manifest)

    assert board.title == "b" and board.quantity == 1


def test_a_changed_board_is_stale(tmp_path, monkeypatch):
    manifest, kicad = make_board(tmp_path, monkeypatch)
    (board,) = gerbers.load(manifest)
    assert gerbers.is_stale(board) is False

    (kicad / "b.kicad_pcb").write_bytes(b"(kicad_pcb (moved))\n")

    assert gerbers.is_stale(board) is True
    assert any("changed since" in problem for problem in gerbers.problems(board))


def test_line_endings_do_not_make_a_board_stale(tmp_path, monkeypatch):
    """The repository is checked out with autocrlf on Windows, so the
    same commit's board file is different bytes on the machine that
    plotted it and on the machine that pulled it."""
    manifest, kicad = make_board(tmp_path, monkeypatch)
    (board,) = gerbers.load(manifest)

    (kicad / "b.kicad_pcb").write_bytes(b"(kicad_pcb)\r\n")

    assert gerbers.is_stale(board) is False


def test_a_missing_file_is_named_and_not_packaged(tmp_path, monkeypatch):
    manifest, kicad = make_board(tmp_path, monkeypatch, files=("b-F_Cu.gtl", "b.drl"))
    (kicad / "production" / "b" / "b.drl").unlink()
    (board,) = gerbers.load(manifest)

    assert gerbers.missing_files(board) == ("b.drl",)
    with pytest.raises(gerbers.PackageError, match="b.drl"):
        gerbers.board_zip(board)
    # The whole download still comes, without that board and saying so.
    package = zipfile.ZipFile(io.BytesIO(gerbers.package_zip((board,))))
    assert board.zip_name not in package.namelist()
    assert "missing" in package.read("README.txt").decode("utf-8")


def test_a_four_layer_board_without_its_inner_coppers_is_caught(tmp_path, monkeypatch):
    outer = tuple(f"b{suffix}" for suffix in gerbers.REQUIRED_SUFFIXES) + ("b.drl",)
    manifest, _kicad = make_board(tmp_path, monkeypatch, files=outer, layers=4)
    (board,) = gerbers.load(manifest)

    assert gerbers.missing_layers(board) == gerbers.INNER_SUFFIXES


def test_an_unknown_board_is_refused_by_name(boards):
    with pytest.raises(gerbers.PackageError, match="nonesuch"):
        gerbers.find(boards, "nonesuch")


# --- the KiCad projects --------------------------------------------------


def make_projects(tmp_path, monkeypatch):
    cad = tmp_path / "CAD"
    kicad = cad / "KiCad"
    (kicad / "board" / "board-backups").mkdir(parents=True)
    (kicad / "board" / "board.kicad_pcb").write_text("(kicad_pcb)")
    (kicad / "board" / "board.kicad_prl").write_text("{}")
    (kicad / "board" / "fp-info-cache").write_text("0")
    (kicad / "board" / "board-backups" / "old.zip").write_bytes(b"PK")
    (kicad / "notes.pdf").write_bytes(b"%PDF")

    monkeypatch.setattr(kicad_projects, "REPO_FOLDER", tmp_path)
    monkeypatch.setattr(kicad_projects, "KICAD_FOLDER", kicad)
    monkeypatch.setattr(kicad_projects, "ARCHIVE_ROOT", cad)
    return kicad


def test_the_walk_leaves_out_what_kicad_leaves_behind(tmp_path, monkeypatch):
    kicad = make_projects(tmp_path, monkeypatch)

    names = [path.relative_to(kicad).as_posix() for path in kicad_projects.walked()]

    assert names == ["board/board.kicad_pcb", "notes.pdf"]


def test_git_is_believed_when_it_answers(tmp_path, monkeypatch):
    kicad = make_projects(tmp_path, monkeypatch)

    listed = kicad_projects.files(
        lambda folder: ["CAD/KiCad/board/board.kicad_pcb", "CAD/KiCad/gone.txt"]
    )

    # Only what is on disk: a file git lists and the tree has lost is not
    # a file anybody can be handed.
    assert listed == (kicad / "board" / "board.kicad_pcb",)


@pytest.mark.parametrize("answer", [lambda folder: [], None])
def test_with_nothing_from_git_it_walks(tmp_path, monkeypatch, answer):
    make_projects(tmp_path, monkeypatch)

    assert len(kicad_projects.files(answer)) == 2


def test_git_failing_is_not_the_downloads_problem(tmp_path, monkeypatch):
    """Whatever it raises. A laptop that cannot reach its remote is
    exactly where somebody wants the files off it."""
    make_projects(tmp_path, monkeypatch)

    def broken(folder):
        raise RuntimeError("git is not installed")

    assert len(kicad_projects.files(broken)) == 2


def test_the_archive_unpacks_as_a_kicad_folder(tmp_path, monkeypatch):
    make_projects(tmp_path, monkeypatch)
    listed = kicad_projects.walked()

    path = kicad_projects.archive(tmp_path / "downloads", listed)

    names = zipfile.ZipFile(path).namelist()
    assert sorted(names) == ["KiCad/board/board.kicad_pcb", "KiCad/notes.pdf"]


def test_the_same_files_are_not_zipped_twice(tmp_path, monkeypatch):
    make_projects(tmp_path, monkeypatch)
    listed = kicad_projects.walked()
    cache = tmp_path / "downloads"

    first = kicad_projects.archive(cache, listed)
    stamp = first.stat().st_mtime_ns
    second = kicad_projects.archive(cache, listed)

    assert second == first and second.stat().st_mtime_ns == stamp


def test_a_changed_file_gets_a_new_archive_and_the_old_one_goes(tmp_path, monkeypatch):
    kicad = make_projects(tmp_path, monkeypatch)
    cache = tmp_path / "downloads"
    first = kicad_projects.archive(cache, kicad_projects.walked())

    (kicad / "board" / "board.kicad_pcb").write_text("(kicad_pcb (moved))")
    second = kicad_projects.archive(cache, kicad_projects.walked())

    assert second != first
    assert [path.name for path in cache.iterdir()] == [second.name]


def test_a_file_is_handed_out_whole_in_pieces(tmp_path):
    path = tmp_path / "big.bin"
    path.write_bytes(bytes(range(256)) * 10)

    pieces = list(kicad_projects.chunks(path, size=1000))

    assert len(pieces) == 3
    assert b"".join(pieces) == path.read_bytes()
