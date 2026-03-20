from __future__ import annotations

import sys

import pytest

from z8ter.cli import main as cli_main


def _run(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> str:
    monkeypatch.setattr(sys, "argv", ["z8"] + args)
    out = []

    def fake_print(*values, **kwargs):
        out.append(" ".join(str(v) for v in values))

    monkeypatch.setattr("builtins.print", fake_print)
    cli_main.main()
    return "\n".join(out)


def test_cli_dispatches_create_page(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_create_page(name: str) -> None:
        captured["name"] = name

    monkeypatch.setattr(cli_main, "create_page", fake_create_page)
    output = _run(monkeypatch, ["create_page", "home"])

    assert captured["name"] == "home"
    assert "Page created." in output


def test_cli_dispatches_create_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_create_api(name: str) -> None:
        captured["name"] = name

    monkeypatch.setattr(cli_main, "create_api", fake_create_api)
    output = _run(monkeypatch, ["create_api", "billing"])

    assert captured["name"] == "billing"
    assert "API created." in output


def test_cli_dispatches_new_project(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_new(name: str) -> int:
        captured["name"] = name
        return 0

    monkeypatch.setattr(cli_main, "new_project", fake_new)
    output = _run(monkeypatch, ["new", "demo"])

    assert captured["name"] == "demo"
    assert "Project created." not in output


def test_cli_returns_new_project_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "new_project", lambda name: 4)
    output = _run(monkeypatch, ["new", "demo"])

    assert output == ""


def test_cli_dispatches_run(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_run(mode: str) -> None:
        captured["mode"] = mode

    monkeypatch.setattr(cli_main, "run_server", fake_run)
    _run(monkeypatch, ["run"])

    assert captured["mode"] == "prod"
