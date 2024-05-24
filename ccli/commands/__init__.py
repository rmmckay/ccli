import importlib
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent


def invoke_main(package, args=(), kwargs=None):
    importlib.import_module(f"{package}.main").main(*args, **(kwargs or {}))
