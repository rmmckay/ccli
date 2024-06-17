import os
import pwd
import pytest
import typing
from contextlib import contextmanager
from getpass import getuser
from pathlib import Path


@pytest.fixture
def chdir():
    @contextmanager
    def chdir(path):
        cwd = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(cwd)
    return chdir


@pytest.fixture
def gid():
    return pwd.getpwnam(getuser()).pw_gid


@pytest.fixture
def starting_path(gid, tmp_path):
    """In case tmp_path needs to be used for something else, nest."""
    starting_path = tmp_path / "starting_path"
    starting_path.mkdir()
    os.chown(starting_path, -1, gid)
    return starting_path


@pytest.fixture
def make_path(gid, starting_path):
    def make_path(
        name: typing.Union[str, Path],
        kind: str,
        mode: typing.Optional[int] = None,
        src: typing.Optional[str] = None,
    ):
        """Make a path with the specified name under starting_path.

        If the path is already relative to starting_path, it will be
        handled relative to starting_path.
        """
        if str(name).startswith(str(starting_path)):
            name = Path(name).relative_to(starting_path)
        path = starting_path / name
        if kind == "file":
            path.touch()
        elif kind == "dir":
            path.mkdir(parents=True)
        elif kind == "link":
            if src is None:
                raise ValueError(f"{src!r} is required for symlinks.")
            path.symlink_to(src)
        else:
            raise ValueError(
                f"Expected one of 'file', 'dir', or 'link', but got {kind!r}"
            )
        if kind != "link":
            os.chown(path, -1, gid)
        if mode is not None:
            path.chmod(mode)
        return path

    return make_path


@pytest.fixture
def simple_tree(make_path):
    """A simple directory structure."""
    make_path(name="b_file", kind="file", mode=0o664)
    make_path(name="a_file", kind="file", mode=0o664)
    make_path(name="c_file", kind="file", mode=0o664)
    hidden_dir = make_path(name=".hidden_dir", kind="dir", mode=0o775)
    make_path(name=hidden_dir / "b_file", kind="file", mode=0o664)
    make_path(name=hidden_dir / "a_file", kind="file", mode=0o664)
    make_path(name=hidden_dir / "c_file", kind="file", mode=0o664)
    a_dir = make_path(name="a_dir", kind="dir", mode=0o775)
    make_path(name=a_dir / "b_file", kind="file", mode=0o664)
    make_path(name=a_dir / "a_file", kind="link", src="b_file")
    make_path(name=a_dir / "c_dir", kind="link", src="../.hidden_dir")
    make_path(name="broken_link", kind="link", src="does/not/exist")
    make_path(name=".hidden", kind="file")


@pytest.fixture
def recursive_link(make_path):
    make_path(name="points_to_self", kind="link", src="points_to_self")


@pytest.fixture
def nested_link_recursion(make_path):
    chicken = make_path(name="chicken", kind="dir", mode=0o775)
    egg = make_path(name="egg", kind="dir", mode=0o775)
    make_path(name=egg / "chicken", kind="link", src="../chicken")
    make_path(name=chicken / "egg", kind="link", src="../egg")


@pytest.fixture
def tree_kwargs(starting_path):
    """Basic keyword arguments for Tree."""
    return {
        "color": False,
        "date": False,
        "dirs_first": None,
        "fifos": False,
        "file_limit": None,
        "follow_links": False,
        "full_path": False,
        "group": False,
        "ignore_pattern": None,
        "ignore_tree": False,
        "indent": 4,
        "inodes": False,
        "level": None,
        "list_hidden": False,
        "list_only_dirs": False,
        "nice_size": False,
        "no_color": False,
        "paths": (str(starting_path),),
        "pattern": None,
        "permissions": False,
        "report": True,
        "reverse": False,
        "size": False,
        "time": False,
        "user": False,
    }
