from __future__ import annotations

import z8ter
from z8ter.config import build_config


def test_build_config_injects_base_dir(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("")

    config = build_config(str(env_file))
    assert config("BASE_DIR") == str(z8ter.BASE_DIR)
