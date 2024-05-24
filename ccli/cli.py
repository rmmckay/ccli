import click
import importlib

from .commands import COMMANDS_DIR

_HELP = "Custom Command-Line Utilities."


class LazyCLI(click.MultiCommand):
    def list_commands(self, ctx):
        return sorted(
            path.parent.name
            for path in COMMANDS_DIR.glob("*/cli.py")
        )

    def get_command(self, ctx, name):
        module = importlib.import_module(".".join((
            __package__,
            COMMANDS_DIR.name,
            name,
            "cli",
        )))
        return getattr(module, name)


CLI = LazyCLI(help=_HELP)
