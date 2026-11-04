"""PyInstaller entrypoint for the isolated MJON Windows tools preview.

The approved MJON graphical shell is NOT bundled by this launcher.
"""
from __future__ import annotations

from mjon_windows.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
