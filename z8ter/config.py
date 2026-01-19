"""Configuration utilities for Z8ter.

Provides helpers to build a configuration accessor with framework-specific
defaults injected.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, TypeVar

from starlette.config import Config

T = TypeVar("T")


class Z8terConfig:
    """Configuration wrapper with Z8ter-specific defaults.

    Wraps a Starlette Config object and provides additional framework-level
    defaults that take precedence over environment variables.

    Attributes:
        _config: The underlying Starlette Config object
        _defaults: Framework-level default values

    """

    def __init__(self, env_file: str) -> None:
        """Initialize with environment file.

        Args:
            env_file: Path to a .env file to load environment variables from.
                      If the file doesn't exist, only environment variables are used.

        """
        # Check if env file exists - Starlette Config handles missing files gracefully
        env_path = Path(env_file)
        if env_path.exists():
            self._config = Config(env_file)
        else:
            self._config = Config()

        # Framework-level defaults (computed lazily)
        self._defaults: dict[str, Callable[[], Any]] = {
            "BASE_DIR": self._get_base_dir,
        }

    @staticmethod
    def _get_base_dir() -> str:
        """Get the base directory lazily."""
        import z8ter

        return str(z8ter.BASE_DIR)

    def __call__(
        self,
        key: str,
        *,
        cast: Callable[[Any], T] | type[T] | None = None,
        default: T | None = None,
    ) -> T | str | None:
        """Get a configuration value.

        Resolution order:
        1. Environment variables (via Starlette Config)
        2. Z8ter framework defaults
        3. Provided default value

        Args:
            key: The configuration key to look up
            cast: Optional type to cast the value to
            default: Default value if not found

        Returns:
            The configuration value, cast if specified

        """
        # Check if there's a framework default
        if key in self._defaults:
            # Check if environment overrides it
            env_value = os.getenv(key)
            if env_value is not None:
                if cast is not None:
                    return cast(env_value)
                return env_value
            # Use framework default
            value = self._defaults[key]()
            if cast is not None:
                return cast(value)
            return value

        # Delegate to Starlette Config
        if cast is not None:
            return self._config(key, cast=cast, default=default)
        if default is not None:
            return self._config(key, default=default)
        return self._config(key)


def build_config(env_file: str) -> Z8terConfig:
    """Build a Config object with Z8ter defaults.

    Loads environment variables from the given `.env` file and provides
    additional framework-level defaults.

    Args:
        env_file: Path to a .env file to load environment variables from.

    Returns:
        Z8terConfig: A configuration accessor with framework defaults.

    Injected defaults:
        - BASE_DIR: Absolute path to the current application base directory.

    Note:
        If the .env file doesn't exist, only environment variables are used.
        This is not an error - it allows deployment without .env files.

    """
    return Z8terConfig(env_file)
