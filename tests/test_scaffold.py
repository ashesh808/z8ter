from __future__ import annotations

from pathlib import Path

import pytest

from z8ter.cli.new import RC_NONEMPTY_DIR, RC_OK, new_project


def test_new_project_copies_template_tree(tmp_path, capsys) -> None:
    target = tmp_path / "my_app"
    rc = new_project("ignored", path=str(target))
    captured = capsys.readouterr()

    assert rc == RC_OK
    assert "Created new Z8ter project" in captured.out
    assert (target / "templates" / "base.jinja").exists()
    assert (target / "endpoints" / "views" / "index.py").exists()
    assert (target / "package.json").exists()
    assert not (target / "views").exists()
    assert not any(target.rglob("__pycache__"))
    assert not any(path.name == ".DS_Store" for path in target.rglob("*"))


def test_new_project_rejects_nonempty_directory(tmp_path, capsys) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "marker.txt").write_text("present")

    rc = new_project("ignored", path=str(target))
    captured = capsys.readouterr()

    assert rc == RC_NONEMPTY_DIR
    assert "Target directory is not empty" in captured.err


def test_new_project_rejects_existing_file(tmp_path, capsys) -> None:
    target = tmp_path / "existing.txt"
    target.write_text("present")

    rc = new_project("ignored", path=str(target))
    captured = capsys.readouterr()

    assert rc == RC_NONEMPTY_DIR
    assert "not a directory" in captured.err


def test_new_project_skips_known_junk_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    template = tmp_path / "template"
    (template / "templates").mkdir(parents=True)
    (template / "templates" / "base.jinja").write_text("ok")
    (template / "endpoints" / "views").mkdir(parents=True)
    (template / "endpoints" / "views" / "index.py").write_text("ok")
    (template / "views").mkdir(parents=True)
    (template / "views" / "legacy.py").write_text("legacy")
    (template / "__pycache__").mkdir()
    (template / "__pycache__" / "junk.pyc").write_bytes(b"junk")
    (template / ".DS_Store").write_text("junk")

    monkeypatch.setattr("z8ter.cli.new._template_root_path", lambda: template)

    target = tmp_path / "my_app"
    rc = new_project("ignored", path=str(target))
    captured = capsys.readouterr()

    assert rc == RC_OK
    assert "Created new Z8ter project" in captured.out
    assert not (target / "views").exists()
    assert not (target / "__pycache__").exists()
    assert not (target / ".DS_Store").exists()
