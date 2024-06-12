import tomlkit
from pathlib import Path

import ccli


def test_version():
    """Check README.md, pyproject.toml, and ccli.__version__"""
    toml = Path(__file__).parent.parent / "pyproject.toml"
    data = tomlkit.loads(toml.read_text())
    assert data['tool']['poetry']['version'] == ccli.__version__
    readme = toml.parent / "README.md"
    with open(readme) as fh:
        for line in fh:
            if line.startswith("## Version Information"):
                break
        for line in fh:
            if line.startswith("###"):
                assert line.split()[-1] == ccli.__version__
                break
