from __future__ import annotations

from pathlib import Path

from src._sourceless import export_public_attributes, load_compiled_module


_COMPILED = load_compiled_module(
    "src.data._compiled.fetch",
    Path(__file__).resolve().parents[2] / "compiled_backup" / "fetch.cpython-313.pyc",
)

__all__ = export_public_attributes(_COMPILED, globals())
