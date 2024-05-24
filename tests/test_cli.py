from click.testing import CliRunner

from ccli.cli import CLI


def test_CLI():
    assert "Custom Command-Line Utilities." in CliRunner().invoke(
        CLI,
        ("--help",),
    ).output
