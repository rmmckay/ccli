import grp
import math
import os
import stat
from collections import Counter
from functools import partial, wraps
from termcolor import cprint


def _default_missing(default):
    """Decorator to provide a default if self._get_stats(path) is None.

    The method must have the following arguments:
        'path', which must be path-like.
        'stats', the returned value of self._get_stats(path)
    """
    def decorator(function):
        @wraps(function)
        def _default_missing(self, *args, path, stats=None, **kwargs):
            stats = self._get_stats(path)
            if stats is None:
                return default
            return function(self, *args, path=path, stats=stats, **kwargs)
        return _default_missing
    return decorator


class Tree:
    _FILE_TYPE_MAP = {
        stat.S_IFREG: "-",  # Regular file.
        stat.S_IFBLK: "b",  # Block special file.
        stat.S_IFCHR: "c",  # Character special file.
        stat.S_IFDIR: "d",  # Directory.
        stat.S_IFLNK: "l",  # Symbolic link.
        stat.S_IFIFO: "p",  # FIFO.
        stat.S_IFSOCK: "s",  # Socket.
        stat.S_IFWHT: "w",  # Whiteout.
    }
    _SI_SUFFIXES = (
        "",
        "K",
        "M",
        "G",
        "T",
        "P",
    )
    corner_ = "└"
    hbar_ = "―"
    tee_ = "├"
    vbar_ = "│"
    broken_link_color = "red"
    tree_color = "yellow"
    tree_attrs = ()
    dir_color = "cyan"
    dir_attrs = ("bold",)
    file_color = "white"
    file_attrs = ()
    link_color = "green"
    link_attrs = ("underline",)
    permissions_color = "magenta"
    permissions_attrs = ()
    prefix = ""
    size_color = "white"
    size_attrs = ()

    def __init__(self, **kwargs):
        vars(self).update(kwargs)
        self._counter = Counter()
        for path in self.paths:
            # Broken links OK
            if os.path.exists(path) or os.path.islink(path):
                self._run(path=path)
        if self.report:
            self._summarize()

    @property
    def corner(self):
        return self.corner_ + self.hbar

    @property
    def hbar(self):
        return self.hbar_ * (self.indent - 2)

    @property
    def vbar(self):
        return self.vbar_

    @property
    def tee(self):
        return self.tee_ + self.hbar

    def _details(self, path):
        ospath = os.path
        inside = []
        islink = ospath.islink(path)
        if isdir := ospath.isdir(path):
            if not islink or (islink and self.follow_links):
                inside = self._ls(path)
        if islink:
            if ospath.exists(path):
                return self.link_color, self.link_attrs, inside
            return self.broken_link_color, self.link_attrs, inside
        if isdir:
            return self.dir_color, self.dir_attrs, inside
        return self.file_color, self.file_attrs, inside

    def _get_stats(self, path):
        if os.path.exists(path):
            return os.stat(path)
        return None

    @_default_missing("???")
    def _get_group(self, path, stats=None):
        return grp.getgrgid(stats.st_gid)[0]

    @_default_missing(float("inf"))
    def _get_mtime_(self, path, stats=None):
        return stats.st_mtime

    def _get_mtime(self, name, parent):
        """Used for sorting purposes. Non-existing get inf."""
        return self._get_mtime_(path=os.path.join(parent, name))

    @_default_missing("??????????")
    def _get_permissions(self, path, stats=None):
        """Extract ls-style permission string from the path.

        Example return values:
            "-rw-r--r--"
            "drwxrwxr-x"
        """
        mode = stats.st_mode
        chrs = [self._FILE_TYPE_MAP[stat.S_IFMT(mode)]]
        for read_mask, write_mask, exe_mask, special_mask, special_chr in (
            (stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR, stat.S_ISUID, "s"),
            (stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP, stat.S_ISGID, "s"),
            (stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH, stat.S_ISVTX, "t"),
        ):
            chrs.append("r" if read_mask & mode else "-")
            chrs.append("w" if write_mask & mode else "-")
            exe = exe_mask & mode
            if special_mask & mode:
                exe_chr = special_chr if exe else special_chr.upper()
            else:
                exe_chr = "x" if exe else "-"
            chrs.append(exe_chr)
        return "".join(chrs)

    @_default_missing("?")
    def _get_size(self, path, stats=None):
        size = stats.st_size
        if self.nice_size:
            if size <= 0:
                return f"{size}{self._SI_SUFFIXES[0]}"
            log10 = math.floor(math.log10(size))
            index = min(math.floor(log10 / 3), len(self._SI_SUFFIXES))
            return f"{round(size / 1024**index, 2)}{self._SI_SUFFIXES[index]}"
        return str(size)

    def _ls(self, path):
        """List the requested path's contents in the correct order."""
        if self.time:
            key = partial(self._get_mtime, parent=path)
        else:
            key = str.casefold
        return sorted(
            (
                name
                for name in os.listdir(path)
                if self._to_print(path, name)
            ),
            key=key,
            reverse=self.reverse,
        )

    def _print_permissions(self, path):
        for var, callback in (
            (self.permissions, self._get_permissions),
            (self.group, self._get_group),
        ):
            if var:
                cprint(
                    callback(path=path),
                    color=self.permissions_color,
                    attrs=self.permissions_attrs,
                    end=" ",
                )

    def _print_size(self, path):
        if self.size or self.nice_size:
            cprint(
                self._get_size(path=path),
                color=self.size_color,
                attrs=self.size_attrs,
                end=" ",
            )

    def _register_path(self, path):
        isdir = os.path.isdir(path)
        islink = os.path.islink(path)
        if islink:
            key = "directory links" if isdir else "file links"
        else:
            key = "directories" if isdir else "files"
        self._counter[key] += 1

    def _print_and_register_path(self, path, color, attrs):
        self._register_path(path)
        printpath = path if self.full_path else os.path.basename(path)
        cprint(printpath, color=color, attrs=attrs)

    def _run(self, path, _prefix=""):
        """Recursively print the tree for the specified path."""
        color, attrs, inside = self._details(path=path)
        cprint(_prefix, color=self.tree_color, attrs=self.tree_attrs, end="")
        self._print_permissions(path=path)
        self._print_size(path=path)
        self._print_and_register_path(path=path, color=color, attrs=attrs)
        if self.ignore_tree:
            prefixes = [""] * len(inside)
        else:
            corner, tee, vbar = self.corner, self.tee, self.vbar
            _prefix = _prefix.replace(
                corner, " " * len(corner),
            ).replace(tee, vbar + " " * len(self.hbar))
            prefixes = [f"{tee} "] * (len(inside) - 1) + [f"{corner} "]
        for sub, prefix in zip(inside, prefixes):
            self._run(_prefix=_prefix + prefix, path=os.path.join(path, sub))

    def _summarize(self):
        cprint(", ".join(
            f"{value} {self._singluar_or_plural(name=key, number=value)}"
            for key, value in self._counter.items()
        ))

    def _to_print(self, path, name):
        if not self.list_hidden and name.startswith("."):
            return False
        if self.list_only_dirs and not os.path.isdir(os.path.join(path, name)):
            return False
        return True

    @staticmethod
    def _singluar_or_plural(name, number):
        """Change plural name to singular if number is 1"""
        if number == 1:
            if name.endswith("ies"):
                return name.removesuffix("ies") + "y"
            return name.removesuffix("s")
        return name


def main(*args, **kwargs):
    Tree(*args, **kwargs)
