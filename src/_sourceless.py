from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def load_compiled_module(module_name: str, compiled_path: Path) -> ModuleType:
    if not compiled_path.exists():
        raise ImportError(f"Compiled module not found: {compiled_path}")

    spec = spec_from_file_location(module_name, compiled_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load compiled module: {compiled_path}")

    module = module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def export_public_attributes(
    compiled_module: ModuleType,
    target_globals: dict[str, object],
) -> list[str]:
    public_names = getattr(compiled_module, "__all__", None)
    if public_names is None:
        public_names = [
            name
            for name in vars(compiled_module)
            if not name.startswith("__")
        ]

    for name in public_names:
        target_globals[name] = getattr(compiled_module, name)

    if getattr(compiled_module, "__doc__", None):
        target_globals["__doc__"] = compiled_module.__doc__

    return list(public_names)
