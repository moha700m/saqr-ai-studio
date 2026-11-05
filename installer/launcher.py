"""Single entry point for the frozen app: GUI by default, CLI when asked."""

import sys

CLI_COMMANDS = {"doctor", "models", "serve", "pair-code", "benchmark", "process"}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in CLI_COMMANDS:
        from saqr_engine.cli import main as cli_main

        return cli_main(sys.argv[1:])
    from saqr_desktop.app import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
