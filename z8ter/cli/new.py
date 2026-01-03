"""Project scaffolding command for Z8ter.

This module implements the `z8 new <name>` functionality by copying a bundled
template tree into a new project directory.

Design goals (v0.2):
- Zero external dependencies.
- Work from both editable installs and built wheels (zip-safe).
- Fail fast with clear, actionable error messages.
- Keep behavior minimal and predictable; no placeholder substitution yet.

Future plans:
- Optional substitutions (e.g., project name in README).
- Flags for opinionated scaffolds (e.g., --auth, --stripe).
- Rich templates using Jinja2 under `z8ter/scaffold/`.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Final

__all__ = ["new_project"]

_TEMPLATE_RELPATH: Final[tuple[str, ...]] = ("scaffold", "create_project_template")

RC_OK: Final[int] = 0
RC_NONEMPTY_DIR: Final[int] = 2
RC_TEMPLATE_MISSING: Final[int] = 3
RC_COPY_ERROR: Final[int] = 4


@dataclass(frozen=True)
class CopyStats:
    """Simple copy statistics for debugging and tests."""

    files_copied: int
    dirs_created: int


def _iter_dirnames(root: Path) -> Iterable[Path]:
    """Yield all directories under `root`, including `root` itself."""
    for current, _dirnames, _filenames in os.walk(root):
        yield Path(current)


def _copy_tree(src: Path, dst: Path) -> CopyStats:
    """Recursively copy the directory tree from `src` into `dst`.

    Copies regular files as raw bytes (preserving contents only).
    Symlinks, fifos, and special files are ignored for v0.2.

    Args:
        src: Source directory to copy from. Must exist and be a directory.
        dst: Destination directory to copy into. Must exist.

    Returns:
        CopyStats with counts of created directories and copied files.

    Raises:
        OSError: If any filesystem operation fails.
        ValueError: If `src` is not a directory.

    """
    if not src.is_dir():
        raise ValueError(f"Source is not a directory: {src}")

    dirs_created = 0
    files_copied = 0

    for d in _iter_dirnames(src):
        rel = d.relative_to(src)
        target_dir = dst / rel
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            dirs_created += 1

    for current, _dirnames, filenames in os.walk(src):
        current_path = Path(current)
        rel_dir = current_path.relative_to(src)
        for name in filenames:
            s = current_path / name
            d = (dst / rel_dir) / name
            try:
                if not s.is_file():
                    continue
                d.write_bytes(s.read_bytes())
            except OSError as exc:
                raise OSError(f"Failed to copy '{s}' → '{d}': {exc}") from exc
            files_copied += 1

    return CopyStats(files_copied=files_copied, dirs_created=dirs_created)


def _template_root_path() -> Path | None:
    """Resolve the on-disk path to the bundled project template (zip-safe)."""
    try:
        traversable = files("z8ter")
        for part in _TEMPLATE_RELPATH:
            traversable = traversable / part
    except ModuleNotFoundError:
        return None

    with as_file(traversable) as p:
        path = Path(p)
        return path if path.is_dir() else None


def new_project(project_name: str, path: str | None = None) -> int:
    """Create a new Z8ter project by copying the bundled template tree.

    Behavior:
        - Creates `<path or project_name>` if it does not exist.
        - Copies the contents of `z8ter/scaffold/create_project_template/` into it.
        - Prints friendly next steps.

    Args:
        project_name: Logical name for the project; used when `path` is not provided.
        path: Optional target directory; defaults to `project_name`.

    Returns:
        Process-style return code:
            RC_OK (0)               on success
            RC_NONEMPTY_DIR (2)     if target exists and is not empty
            RC_TEMPLATE_MISSING (3) if packaged template cannot be located
            RC_COPY_ERROR (4)       on filesystem copy errors

    Notes:
        - No placeholder substitution is performed in v0.2.
        - The template is accessed via importlib.resources to support zip-safe wheels.

    """
    target = Path(path or project_name).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"✖ Target directory is not empty: {target}", file=sys.stderr, flush=True)
        return RC_NONEMPTY_DIR

    template_path = _template_root_path()
    if template_path is None:
        print("✖ Project template missing inside package.", file=sys.stderr, flush=True)
        return RC_TEMPLATE_MISSING

    try:
        target.mkdir(parents=True, exist_ok=True)
        _ = _copy_tree(template_path, target)
    except OSError as exc:
        print(f"✖ Failed to create project: {exc}", file=sys.stderr, flush=True)
        return RC_COPY_ERROR

    print(f"✓ Created new Z8ter project at: {target}")
    print("Next steps:")
    print(f"  cd {target}")
    print("  uv sync && npm install")
    print("  uv run z8 run dev")
    return RC_OK
