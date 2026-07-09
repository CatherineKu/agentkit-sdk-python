"""Helpers used by generated framework migration apps."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


def _prepend_sys_path(path: Path) -> None:
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)


def _load_module_from_file(entry_path: Path, import_name: str) -> ModuleType:
    if not entry_path.is_file():
        raise FileNotFoundError(f"Entry file does not exist: {entry_path}")

    spec = importlib.util.spec_from_file_location(import_name, entry_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load entry module from {entry_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(import_name) is module:
            del sys.modules[import_name]
        raise
    return module


def _resolve_object(module: ModuleType, object_path: str) -> Any:
    if not object_path:
        raise ValueError("entry object path is required")

    target: Any = module
    for attr in object_path.split("."):
        if not attr:
            raise ValueError(
                f"entry object path contains an empty attribute: {object_path!r}"
            )
        try:
            target = getattr(target, attr)
        except AttributeError as exc:
            raise AttributeError(
                f"Entry object {object_path!r} was not found; "
                f"missing attribute {attr!r} on {target!r}."
            ) from exc
    return target


def load_entry_object(
    *,
    file: str,
    object_path: str,
    module: str | None = None,
    project_root: str | Path = ".",
    base_dir: str | Path | None = None,
    import_name: str = "agentkit_migrated_entry",
) -> Any:
    """Load an object from a migrated project's original entry reference.

    The generated migration app lives beside or below the user's project files.
    This helper keeps that app small while preserving the import behavior that
    users expect from running their original project.
    """

    base_path = (
        Path(base_dir).resolve() if base_dir is not None else Path.cwd().resolve()
    )
    project_root_path = (base_path / project_root).resolve()
    _prepend_sys_path(project_root_path)

    if module:
        loaded_module = importlib.import_module(module)
    else:
        entry_path = (base_path / file).resolve()
        loaded_module = _load_module_from_file(entry_path, import_name)

    return _resolve_object(loaded_module, object_path)
