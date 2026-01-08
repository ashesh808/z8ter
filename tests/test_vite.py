from __future__ import annotations

import json

import pytest

from z8ter import vite


def test_vite_script_tag_dev_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vite, "VITE_DEV_SERVER", "http://localhost:5173")
    tag = str(vite.vite_script_tag("main.ts"))
    assert 'src="http://localhost:5173/main.ts"' in tag


def test_vite_script_tag_manifest_mode(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_dir = tmp_path
    manifest_dir.mkdir(exist_ok=True)
    manifest = {
        "main.ts": {
            "file": "assets/main.js",
            "imports": ["chunk.ts"],
            "css": ["styles.css"],
        },
        "chunk.ts": {"file": "assets/chunk.js"},
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest))

    monkeypatch.setattr(vite, "_get_dist_path", lambda: manifest_dir)
    monkeypatch.setattr(vite, "_manifest_cache", None)
    monkeypatch.setattr(vite, "_manifest_mtime", None)
    monkeypatch.setattr(vite, "VITE_DEV_SERVER", "")

    markup = str(vite.vite_script_tag("main.ts"))
    assert '<script type="module" src="/static/js/assets/main.js"></script>' in markup
    assert "modulepreload" in markup
    assert "styles.css" in markup

    with pytest.raises(KeyError):
        vite.vite_script_tag("unknown.ts")
