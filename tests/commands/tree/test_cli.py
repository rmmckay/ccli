from click.testing import CliRunner

from ccli.commands.tree.cli import tree


def test_tree(chdir, simple_tree, starting_path):
    with chdir(starting_path):
        assert CliRunner().invoke(tree).output == """\
.
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
