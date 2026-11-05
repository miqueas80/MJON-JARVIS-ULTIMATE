"""Standalone GUI entrypoint for MJON AI OS Windows Edition.

The UI is served from packaged static assets and rendered with WebView2 via
pywebview. Never edits Windows policies, installs weights, or starts agents.
"""
from __future__ import annotations

import sys
from mjon_windows.desktop_host import main, self_test


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        raise SystemExit(self_test())
    if len(sys.argv) > 1:
        raise SystemExit(2)
    raise SystemExit(main())
