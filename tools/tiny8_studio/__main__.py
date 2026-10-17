"""Tiny8 Studio — command-line entrypoint.

Run with:
    python -m tools.tiny8_studio
or:
    python tools/tiny8_studio/__main__.py
or:
    Tiny8Studio.exe                  (packaged build)
    Tiny8Studio.exe --version        (print version, exit 0)
    Tiny8Studio.exe --debug          (force diagnostic mode)
"""

import os
import sys

from .app import App
from . import __version__


def main() -> int:
    # Headless flags for the packaged build.  These let the user (or
    # a CI smoke check) confirm the binary is functional without
    # opening a GUI window.
    args = sys.argv[1:]
    if "--version" in args or "-V" in args:
        print(f"Tiny8Studio {__version__}  (python {sys.version.split()[0]})")
        return 0
    if "--help" in args or "-h" in args:
        print("Tiny8Studio — desktop GUI for the Tiny8 game engine.")
        print("")
        print("Usage:")
        print("  Tiny8Studio.exe                launch the GUI")
        print("  Tiny8Studio.exe --version      print version and exit")
        print("  Tiny8Studio.exe --help         print this help and exit")
        print("")
        print("Environment:")
        print("  TINY8_STUDIO_DEBUG=1   print a startup banner to stderr and")
        print("                        re-raise on unhandled exceptions")
        return 0

    app = App()
    # Diagnostic mode: when TINY8_STUDIO_DEBUG=1 the studio prints a
    # one-line banner to stderr so the user can confirm the packaged
    # .exe actually launched, and re-raises on unhandled exceptions
    # instead of swallowing them.  This is intended for troubleshooting
    # a packaged build where the GUI would otherwise exit silently.
    debug = os.environ.get("TINY8_STUDIO_DEBUG") == "1" or "--debug" in args
    if debug:
        print(f"[tiny8-studio] starting (python {sys.version.split()[0]}, "
              f"cwd={os.getcwd()!r})", file=sys.stderr, flush=True)
        try:
            app.mainloop()
        except Exception:
            import traceback
            traceback.print_exc()
            return 1
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
