from __future__ import annotations

from pathlib import Path

from src._sourceless import export_public_attributes, load_compiled_module


_COMPILED = load_compiled_module(
    "app_compiled",
    Path(__file__).resolve().parent / "compiled_backup" / "app.cpython-313.pyc",
)

__all__ = export_public_attributes(_COMPILED, globals())


if __name__ == "__main__":
    main()
