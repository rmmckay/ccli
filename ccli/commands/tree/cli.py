import click

from ...commands import invoke_main


@click.command()
@click.argument("paths", nargs=-1)
@click.option(
    "-a",
    "list_hidden",
    is_flag=True,
    help="List hiddden files / directories.",
)
@click.option(
    "-d", "list_only_dirs", is_flag=True, help="List only directories."
)
@click.option(
    "-f", "full_path", is_flag=True, help="Print the full path prefix."
)
@click.option(
    "-g", "group", is_flag=True, help="Print the group name (or GID #)."
)
@click.option(
    "-h",
    "nice_size",
    is_flag=True,
    help="Print the size of each file (human-readable).",
)
@click.option(
    "-i",
    "ignore_tree",
    is_flag=True,
    help="No visual tree or indentation.",
)
@click.option(
    "-l",
    "follow_links",
    is_flag=True,
    help="Descend into symbolic links.",
)
@click.option(
    "-n",
    "no_color",
    is_flag=True,
    help="Turn off colors (overridden by -C).",
)
@click.option(
    "-p",
    "permissions",
    is_flag=True,
    help="Print file type and permissions.",
)
@click.option(
    "-r",
    "reverse",
    is_flag=True,
    help="Sort the output in reverse (alphabetic by default).",
)
@click.option(
    "-s",
    "size",
    is_flag=True,
    help="Print the size of each file in bytes.",
)
@click.option(
    "-t",
    "time",
    is_flag=True,
    help="Sort the output by last modification time.",
)
@click.option(
    "-u", "user", is_flag=True, help="Print the username (or UID #)."
)
@click.option(
    "-C", "force_color", is_flag=True, help="Turn on colors (overrides -n)."
)
@click.option(
    "-D",
    "date",
    is_flag=True,
    help="Print the date of the last modification time.",
)
# @click.option(
#     "-F",
#     "fifos",
#     is_flag=True,
#     help="Append '/' to dirs, '=' to socket files, "
#     "'*' to executables, and '|' for FIFOs.",
# )
# @click.option(
#     "-I",
#     "ignore_pattern",
#     help="Do not list files matching the wildcard pattern.",
# )
# @click.option("-L", "level", type=int, help="Maximum display limit.")
# @click.option(
#     "-P",
#     "pattern",
#     help="List only files that match the wild-card pattern. Note: "
#     "you must use the -a option to also consider those files beginning "
#     "with a dot '.' for matching. Valid wildcard operators are '*' (any "
#     "zero or more characters), '?' (any single character), '[...]' "
#     "(any single character listed between brackets (optional - (dash) for "
#     "character range may be used: ex: [A-Z]), and '[^...]' (any single "
#     "character not listed in brackets) and '|' separates alternate "
#     "patterns).",
# )
# @click.option(
#     "--filelimit",
#     "file_limit",
#     type=int,
#     help="Do not descend directories that contain more than # entries.",
# )
# @click.option(
#     "--dirsfirst", "dirs_first", help="List directories before files."
# )
@click.option(
    "--indent",
    default=4,
    show_default=True,
    type=int,
    help="Tree indent level (minimum of 2).",
)
# @click.option(
#     "--inodes", is_flag=True, help="Print the inode number."
# )
@click.option(
    "--noreport",
    "report",
    is_flag=True,
    default=True,
    help="Skip the file / directory summary.",
)
def tree(paths=(), **kwargs):
    """Pretty listing of directory structures.

    Sequentially print the tree of each path.
    """
    if not paths:
        paths = (".",)
    kwargs["paths"] = paths
    invoke_main(package=__package__, kwargs=kwargs)
