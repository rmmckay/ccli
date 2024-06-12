import grp
import math
import os
import pytest
import stat
from types import SimpleNamespace
from unittest import mock

from ccli.commands.tree import main


@pytest.fixture
def mock_get_stats():
    with mock.patch(
        "ccli.commands.tree.main.Tree._get_stats",
        autospec=True,
    ) as mock_get_stats:
        yield mock_get_stats


class TestTree:
    @pytest.fixture(autouse=True)
    def mock_run(self):
        """Don't need to run inside these unit tests."""
        with mock.patch("ccli.commands.tree.main.Tree._run", autospec=True):
            yield

    @pytest.mark.usefixtures("simple_tree")
    @pytest.mark.parametrize("follow_links", (False, True))
    def test_details(self, follow_links, starting_path, tree_kwargs):
        tree_kwargs["follow_links"] = follow_links
        tree = main.Tree(**tree_kwargs)
        details = tree._details(path=starting_path / "a_dir" / "c_dir")
        if follow_links:
            assert details == (
                tree.link_color,
                tree.link_attrs,
                ["a_file", "b_file", "c_file"],
            )
        else:
            assert details == (tree.link_color, tree.link_attrs, [])

    @pytest.mark.parametrize("exists", [False, True])
    @mock.patch("grp.getgrgid", autospec=True, return_value=[mock.MagicMock()])
    def test_get_group(
        self,
        mock_getgrgid,
        exists,
        mock_get_stats,
        starting_path,
        tree_kwargs,
    ):
        if not exists:
            mock_get_stats.return_value = None
            expectation = "???"
        else:
            expectation = mock_getgrgid.return_value[0]
        group = main.Tree(**tree_kwargs)._get_group(path=starting_path)
        assert group == expectation

    @pytest.mark.parametrize("exists", [False, True])
    def test_get_mtime(
        self,
        exists,
        mock_get_stats,
        starting_path,
        tree_kwargs,
    ):
        if not exists:
            mock_get_stats.return_value = None
        tree = main.Tree(**tree_kwargs)
        mtime = tree._get_mtime(
            name=starting_path.name,
            parent=starting_path.parent,
        )
        mock_get_stats.assert_called_once_with(tree, str(starting_path))
        if exists:
            assert mtime == mock_get_stats.return_value.st_mtime
        else:
            assert mtime == float("inf")

    @pytest.mark.parametrize("kind", main.Tree._FILE_TYPE_MAP)
    @pytest.mark.parametrize("read", (0, stat.S_IROTH))
    @pytest.mark.parametrize("write", (0, stat.S_IWOTH))
    @pytest.mark.parametrize("exe", (0, stat.S_IXOTH))
    @pytest.mark.parametrize("special", (0, stat.S_ISVTX))
    @pytest.mark.parametrize("triple_index", (0, 1, 2))
    def test_get_permissions(
        self,
        kind,
        read,
        write,
        exe,
        special,
        triple_index,
        tree_kwargs,
    ):
        """There are 32768 combinations
        (2 ^ 12 permission bits combinations * 8 file types)
        to test exhaustively, which is prohibitively slow for this
        simple application.

        Since there's no interaction between groups of three (triples),
        only within the group of three and the associated special bit,
        tests are simplified by looking at each triple + associated
        special bit individually. This reduces the number of
        combinations to test to 384.
        (2 ^ 4 permission bits * 3 triples * 8 file types)
        """
        left_shift = triple_index * 3
        read <<= left_shift
        write <<= left_shift
        exe <<= left_shift
        special <<= triple_index
        triples = ["---", "---"]
        special_chr = "s" if triple_index else "t"
        triple = "".join((
            ("r" if read else "-"),
            ("w" if write else "-"),
            (
                special_chr.upper() if not exe and special
                else special_chr if exe and special
                else "x" if exe else "-"
            ),
        ))
        triples.insert(2 - triple_index, triple)
        tree = main.Tree(**tree_kwargs)
        expectation = "".join((
            tree._FILE_TYPE_MAP[kind],
            "".join(triples),
        ))
        with mock.patch(
            "os.stat",
            autospec=True,
            return_value=SimpleNamespace(
                st_mode=sum((kind, read, write, exe, special)),
            ),
        ):
            assert tree._get_permissions(path=".") == expectation

    @pytest.mark.parametrize("nice_size", [False, True])
    @pytest.mark.parametrize(
        "exists, size, expectation, nice_expectation",
        [
            (True, 3e6, str(3e6), "2.86M"),
            (True, 3e3, str(3e3), "2.93K"),
            (True, 53248, "53248", "52.0K"),
            (True, math.pi, str(math.pi), "3.14"),
            (True, 0, "0", "0"),
            (False, None, "?", "?"),
        ],
    )
    def test_get_size(
        self,
        exists,
        size,
        expectation,
        nice_expectation,
        nice_size,
        tree_kwargs,
    ):
        tree_kwargs["nice_size"] = nice_size
        tree = main.Tree(**tree_kwargs)
        with mock.patch(
            "os.stat",
            autospec=True,
            return_value=SimpleNamespace(st_size=size) if exists else None,
        ):
            result = tree._get_size(path=".")
        if nice_size:
            assert result == nice_expectation
        else:
            assert result == expectation

    @pytest.mark.parametrize("permissions", [False, True])
    @pytest.mark.parametrize("group", [False, True])
    @mock.patch("ccli.commands.tree.main.Tree._summarize", autospec=True)
    @mock.patch("ccli.commands.tree.main.Tree._get_permissions", autospec=True)
    @mock.patch("ccli.commands.tree.main.Tree._get_group", autospec=True)
    @mock.patch("ccli.commands.tree.main.cprint", autospec=True)
    def test_print_permissions(
        self,
        mock_cprint,
        mock_get_group,
        mock_get_permissions,
        mock_summarize,
        permissions,
        group,
        tree_kwargs,
    ):
        tree_kwargs.update({
            "permissions": permissions,
            "group": group,
        })
        tree = main.Tree(**tree_kwargs)
        mock_path = mock.MagicMock(spec=str)
        tree._print_permissions(path=mock_path)
        mock_calls = []
        for var, callback in (
            (permissions, mock_get_permissions),
            (group, mock_get_group),
        ):
            if var:
                callback.assert_called_once_with(tree, path=mock_path)
                mock_calls.append(mock.call(
                    callback.return_value,
                    color=tree.permissions_color,
                    attrs=tree.permissions_attrs,
                    end=" ",
                ))
        mock_cprint.assert_has_calls(mock_calls)

    @pytest.mark.parametrize("files_num, files_name", [
        (0, "files"),
        (1, "file"),
        (2, "files"),
    ])
    @pytest.mark.parametrize("file_links_num, file_links_name", [
        (0, "file links"),
        (1, "file link"),
        (2, "file links"),
    ])
    @pytest.mark.parametrize("directories_num, directories_name", [
        (0, "directories"),
        (1, "directory"),
        (2, "directories"),
    ])
    @pytest.mark.parametrize("directory_links_num, directory_links_name", [
        (0, "directory links"),
        (1, "directory link"),
        (2, "directory links"),
    ])
    def test_summarize(
        self,
        files_num,
        files_name,
        file_links_num,
        file_links_name,
        directories_num,
        directories_name,
        directory_links_num,
        directory_links_name,
        tree_kwargs,
        capfd,
    ):
        tree = main.Tree(**tree_kwargs)
        tree._counter.clear()
        tree._counter.update({
            "directories": directories_num,
            "directory links": directory_links_num,
            "files": files_num,
            "file links": file_links_num,
        })
        capfd.readouterr()
        tree._summarize()
        result = capfd.readouterr().out
        assert result == ", ".join(
            f"{num} {name}"
            for num, name in (
                (directories_num, directories_name),
                (directory_links_num, directory_links_name),
                (files_num, files_name),
                (file_links_num, file_links_name),
            )
        ) + "\n"

    @pytest.mark.parametrize("list_hidden", [False, True])
    @pytest.mark.parametrize("hidden", [False, True])
    @pytest.mark.parametrize("list_only_dirs", [False, True])
    @pytest.mark.parametrize("is_dir", [False, True])
    @mock.patch("ccli.commands.tree.main.os.path.isdir", autospec=True)
    def test_to_print(
        self,
        mock_isdir,
        is_dir,
        list_only_dirs,
        hidden,
        list_hidden,
        tree_kwargs,
    ):
        name = ".name" if hidden else "name"
        mock_isdir.return_value = is_dir
        tree_kwargs.update({
            "list_hidden": list_hidden,
            "list_only_dirs": list_only_dirs,
        })
        tree = main.Tree(**tree_kwargs)
        if (hidden and not list_hidden) or (list_only_dirs and not is_dir):
            expectation = False
        else:
            expectation = True
        assert tree._to_print(path="", name=name) is expectation


@pytest.mark.integration
@pytest.mark.usefixtures("simple_tree")
class TestSimpleTree:
    """Tests that use multiple components instead of a single unit."""

    def test(self, tree_kwargs, capfd):
        main.Tree(**tree_kwargs)
        assert capfd.readouterr().out == """\
starting_path
├―― a_dir
│   ├―― a_file
│   ├―― b_file
│   └―― c_dir
├―― a_file
├―― b_file
├―― broken_link
└―― c_file
2 directories, 2 file links, 4 files, 1 directory link
"""

    def test_permissions(self, tree_kwargs, capfd):
        tree_kwargs["permissions"] = True
        main.Tree(**tree_kwargs)
        assert capfd.readouterr().out == """\
drwxr-xr-x starting_path
├―― drwxrwxr-x a_dir
│   ├―― -rw-rw-r-- a_file
│   ├―― -rw-rw-r-- b_file
│   └―― drwxrwxr-x c_dir
├―― -rw-rw-r-- a_file
├―― -rw-rw-r-- b_file
├―― ?????????? broken_link
└―― -rw-rw-r-- c_file
2 directories, 2 file links, 4 files, 1 directory link
"""

    def test_group(self, gid, tree_kwargs, capfd):
        tree_kwargs["group"] = True
        group = grp.getgrgid(20).gr_name
        main.Tree(**tree_kwargs)
        assert capfd.readouterr().out == f"""\
{group} starting_path
├―― {group} a_dir
│   ├―― {group} a_file
│   ├―― {group} b_file
│   └―― {group} c_dir
├―― {group} a_file
├―― {group} b_file
├―― ??? broken_link
└―― {group} c_file
2 directories, 2 file links, 4 files, 1 directory link
"""

    def test_size(self, mock_get_stats, tree_kwargs, capfd):
        size = mock_get_stats.return_value.st_size
        tree_kwargs["size"] = True
        main.Tree(**tree_kwargs)
        assert capfd.readouterr().out == f"""\
{size} starting_path
├―― {size} a_dir
│   ├―― {size} a_file
│   ├―― {size} b_file
│   └―― {size} c_dir
├―― {size} a_file
├―― {size} b_file
├―― {size} broken_link
└―― {size} c_file
2 directories, 2 file links, 4 files, 1 directory link
"""

    def test_ignore_tree(self, tree_kwargs, capfd):
        tree_kwargs["ignore_tree"] = True
        main.Tree(**tree_kwargs)
        assert capfd.readouterr().out == """\
starting_path
a_dir
a_file
b_file
c_dir
a_file
b_file
broken_link
c_file
2 directories, 2 file links, 4 files, 1 directory link
"""

    @pytest.mark.parametrize("list_hidden", [False, True])
    @pytest.mark.parametrize("list_only_dirs", [False, True])
    @pytest.mark.parametrize("reverse", [False, True])
    @pytest.mark.parametrize("time", [False, True])
    def test_ls(
        self,
        list_hidden,
        list_only_dirs,
        reverse,
        time,
        starting_path,
        tree_kwargs,
    ):
        tree_kwargs.update({
            "list_hidden": list_hidden,
            "list_only_dirs": list_only_dirs,
            "reverse": reverse,
            "time": time,
        })
        expectation = []
        for name in os.listdir(starting_path):
            if not list_hidden and name.startswith("."):
                continue
            if list_only_dirs and not (starting_path / name).is_dir():
                continue
            expectation.append(name)
        expectation = sorted(
            expectation,
            key=lambda name:
                os.stat(path).st_mtime
                if time and (path := starting_path / name).exists()
                else float("inf") if time
                else name,
            reverse=reverse,
        )
        result = main.Tree(**tree_kwargs)._ls(starting_path)
        assert result == expectation

    @mock.patch("ccli.commands.tree.main.Tree", autospec=True)
    def test_main(self, mock_tree, tree_kwargs):
        main.main(**tree_kwargs)
        mock_tree.assert_called_once_with(**tree_kwargs)


@pytest.mark.integration
def test_missing_input_path(tmp_path, tree_kwargs, capfd):
    target = tmp_path / "does not exist"
    if target.exists():
        pytest.fail(f"Expected {target} to not exist - fix this test.")
    tree_kwargs['paths'] = (str(target),)
    main.Tree(**tree_kwargs)
    assert capfd.readouterr().out == "\n"
