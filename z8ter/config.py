"""Configuration utilities for Z8ter.

Provides helpers to build a Starlette `Config` object with framework-specific
defaults injected.
"""

from __future__ import annotations

from starlette.config import Config


def build_config(env_file: str) -> Config:
    """Build a Config object with Z8ter defaults.

    Loads environment variables from the given `.env` file and injects
    additional values required by Z8ter.

    Args:
        env_file: Path to a .env file to load environment variables from.

    Returns:
        Config: A Starlette `Config` object populated with environment
        variables, plus framework defaults.

    Injected defaults:
        - BASE_DIR: Absolute path to the current application base directory.

    """
    import z8ter

    cf: Config = Config(env_file)
    cf.file_values["BASE_DIR"] = str(z8ter.BASE_DIR)
    return cf
