from __future__ import annotations

from pathlib import Path

from src._sourceless import export_public_attributes, load_compiled_module


_COMPILED = load_compiled_module(
    "src.analytics._compiled.metrics",
    Path(__file__).resolve().parents[2] / "compiled_backup" / "metrics.cpython-313.pyc",
)

__all__ = export_public_attributes(_COMPILED, globals())
