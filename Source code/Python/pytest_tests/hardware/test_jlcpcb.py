"""Assembly jobs have exact parts and place precisely the requested SMD set."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile

import pytest

from colloquy.hardware.pcb_files import catalog, gerbers

SPEC = importlib.util.spec_from_file_location("export_jlcpcb", gerbers.REPO_FOLDER / "export_jlcpcb.py")
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)
PARTS = json.loads(exporter.PARTS_PATH.read_text())
COUNTS = {"backplane": 72, "teensy-adapter": 65, "voice-thomas": 1,
          "analyser-carrier": 0, "microphone-flex": 6, "female-base-v2": 4, "male-static-v2": 4}


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


@pytest.mark.parametrize("board", gerbers.load(), ids=lambda b: b.id)
def test_manufacturing_job_matches_its_board_and_has_complete_assembly_files(board):
    with zipfile.ZipFile(io.BytesIO(catalog.production_bytes(board))) as archive:
        bom = rows(archive.read("BOM.csv"))
        cpl = rows(archive.read("CPL.csv"))
        manual = rows(archive.read("manual-and-DNP.csv"))
        refs = [row["Designator"] for row in bom]
        assert len(refs) == len(set(refs)) == COUNTS[board.id]
        assert set(refs) == {row["Designator"] for row in cpl}
        assert not set(refs) & {row["reference"] for row in manual}
        assert all(row["Manufacturer Part Number"] and row["Manufacturer"] and row["LCSC Part #"] for row in bom)
        assert all(row["Quantity"] == "1" for row in bom)
        assert all(row["Layer"] == "Top" and 0 <= float(row["Rotation"]) < 360 for row in cpl)
        native = {row["Ref"]: row for row in rows(archive.read("reference/positions-all-kicad.csv"))}
        assert set(native) <= set(refs) | {row["reference"] for row in manual}
        for row in cpl:
            original = native[row["Designator"]]
            assert float(row["Mid X"].removesuffix("mm")) == float(original["PosX"])
            assert float(row["Mid Y"].removesuffix("mm")) == float(original["PosY"])
            assert float(row["Rotation"]) == float(original["Rot"]) % 360
        if board.id == "backplane":
            assert not {"M1", "J2", "J6"} & set(refs)
        if board.id == "voice-thomas":
            assert refs == ["R3"]
        if board.id == "microphone-flex":
            assert set(refs) == {"R4", "R5", "R6", "C6", "C7", "D1"}
            assert {"JP1", "JP2"} <= {row["reference"] for row in manual}
            assert "proposed-solutions/shields/microphone-flex/" in board.source
        manifest = json.loads(archive.read("manifest.json"))
        for filename, digest in manifest["files"].items():
            assert hashlib.sha256(archive.read(filename)).hexdigest() == digest
        with zipfile.ZipFile(io.BytesIO(archive.read("gerbers.zip"))) as plots:
            suffixes = {Path(name).suffix for name in plots.namelist()}
            assert set(gerbers.REQUIRED_SUFFIXES) | {".drl", ".gtp"} <= suffixes
            if board.copper_layers == 4:
                assert {".g1", ".g2"} <= suffixes


def test_unknown_parts_are_not_guessed():
    with pytest.raises((KeyError, ValueError)):
        exporter.part_for("R_0603_1608Metric", "99K", PARTS)
    with pytest.raises(ValueError):
        exporter.part_for("C_0805_2012Metric", "10nF C0G", PARTS)


@pytest.mark.parametrize("selection,manufacturer", [
    (["RC0603FR-07160RL", "C185369"], "YAGEO"),
    (["UNI-ROYAL", "0603WAF1600T5E", "C22814"], "UNI-ROYAL"),
])
def test_lamp_resistor_selection_reaches_the_assembly_bom(selection, manufacturer):
    catalog = {**PARTS, "resistors_0603": {**PARTS["resistors_0603"], "160R": selection}}
    component = {"reference": "RA1", "value": "160R", "footprint": "R_0603_1608Metric"}
    position = {"Side": "top", "Val": "160R", "Package": "R_0603_1608Metric",
                "PosX": "204", "PosY": "-165", "Rot": "0"}
    bom, cpl = exporter.assembly_rows([component], {"RA1": position}, catalog)
    assert bom[0]["Manufacturer"] == manufacturer
    assert bom[0]["Manufacturer Part Number"] == selection[-2]
    assert bom[0]["LCSC Part #"] == selection[-1]
    assert bom[0]["Specification"] == "160R 0603, +/-1%, 0.1W"
    assert cpl[0]["Designator"] == "RA1"


def test_a_new_footprint_or_value_cannot_reuse_old_placement():
    component = {"reference": "R1", "value": "100K", "footprint": "R_0603_1608Metric"}
    position = {"Side": "top", "Val": "10K", "Package": "R_0603_1608Metric"}
    with pytest.raises(ValueError, match="disagree"):
        exporter.assembly_rows([component], {"R1": position}, PARTS)


def test_aggregate_download_includes_the_assembly_files_for_every_board():
    status, _, content = catalog.response(("all", "fabrication"))
    assert status == "200 OK"
    with zipfile.ZipFile(io.BytesIO(content)) as outer:
        assert len(outer.namelist()) == len(gerbers.load())
        for name in outer.namelist():
            with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
                assert {"BOM.csv", "CPL.csv", "gerbers.zip"} <= set(inner.namelist())


def test_a_stale_assembly_job_is_refused(monkeypatch):
    monkeypatch.setattr(gerbers, "digest", lambda path: "new board or part table")
    assert catalog.response(("backplane", "fabrication"))[0] == "404 Not Found"
    assert "assembly export is stale" in catalog.html()


def test_download_is_uncached_and_identifies_the_exact_bytes():
    status, headers, content = catalog.response(("backplane", "fabrication"))
    assert status == "200 OK"
    assert dict(headers)["Cache-Control"] == "no-store"
    assert hashlib.sha256(content).hexdigest()[:10] in dict(headers)["Content-Disposition"]


def test_catalog_shows_the_export_version():
    with zipfile.ZipFile(io.BytesIO(catalog.production_bytes(gerbers.load()[0]))) as package:
        recorded = json.loads(package.read("manifest.json"))
    page = catalog.html()
    assert recorded["exported_at"] in page
    assert recorded["source_sha256"][:10] in page
