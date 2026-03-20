from __future__ import annotations

import z8ter
import z8ter.cli
import z8ter.endpoints


def test_cli_exports_track_core_module() -> None:
    assert z8ter.cli.__version__ == z8ter.__version__
    assert z8ter.cli.VIEWS_DIR == z8ter.VIEWS_DIR
    assert z8ter.cli.API_DIR == z8ter.API_DIR


def test_endpoints_exports_track_core_module() -> None:
    assert z8ter.endpoints.__version__ == z8ter.__version__
    assert z8ter.endpoints.VIEWS_DIR == z8ter.VIEWS_DIR
    assert z8ter.endpoints.TEMPLATES_DIR == z8ter.TEMPLATES_DIR
