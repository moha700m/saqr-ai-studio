"""Single entry point for the frozen app: GUI by default, CLI when asked."""

import sys

CLI_COMMANDS = {"doctor", "models", "serve", "pair-code", "benchmark", "process"}


def _hide_console() -> None:
    """Keep the console for CLI commands, hide it for the GUI on Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        handle = ctypes.windll.kernel32.GetConsoleWindow()
        if handle:
            ctypes.windll.user32.ShowWindow(handle, 0)
    except Exception:  # noqa: BLE001 - cosmetic only
        pass


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in CLI_COMMANDS:
        from saqr_engine.cli import main as cli_main

        return cli_main(sys.argv[1:])
    _hide_console()
    from saqr_desktop.app import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
