import grp
import math
import os
import pwd
import stat
from collections import Counter
from datetime import datetime, timedelta
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
    _YEAR_CUTOFF_AGE_DAYS = 182.5
    corner_ = "└"
    hbar_ = "―"
    tee_ = "├"
    vbar_ = "│"
    broken_link_color = "red"
    tree_attrs = ()
    tree_color = "yellow"
    date_attrs = ()
    date_color = "magenta"
    dir_attrs = ("bold",)
    dir_color = "cyan"
    file_attrs = ()
    file_color = "white"
    link_attrs = ("underline",)
    link_color = "green"
    permissions_attrs = ()
    permissions_color = "magenta"
    prefix = ""
    size_attrs = ()
    size_color = "white"

    def __init__(self, **kwargs):
        vars(self).update(kwargs)
        self._counter = Counter()
        self._now = datetime.now()
        self._resolved_paths = set()
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

    def _cprint(self, *args, **kwargs):
        cprint(
            *args,
            no_color=self.no_color if not self.force_color else False,
            force_color=self.force_color,
            **kwargs,
        )

    def _details(self, path):
        inside = []
        islink = os.path.islink(path)
        if isdir := os.path.isdir(path):
            if self._seen_inside(path):
                inside = ["..."]
            elif not islink or (islink and self.follow_links):
                inside = self._ls(path)
        if islink:
            if os.path.exists(path):
                return self.link_color, self.link_attrs, inside
            return self.broken_link_color, self.link_attrs, inside
        if isdir:
            return self.dir_color, self.dir_attrs, inside
        return self.file_color, self.file_attrs, inside

    @_default_missing("??? ?? ?????")
    def _get_date(self, path, stats=None):
        date = datetime.fromtimestamp(stats.st_mtime)
        if timedelta(days=0) < (
            self._now - date
        ) < timedelta(days=self._YEAR_CUTOFF_AGE_DAYS):
            suffix = f"{date:%H:%M}"
        else:
            suffix = f"{date.year:>5}"
        return f"{date:%b} {date.day:>2} {suffix}"

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

    @_default_missing("?")
    def _get_user(self, path, stats=None):
        try:
            pwuid = pwd.getpwuid(stats.st_uid)
        except KeyError:
            return stats.st_gid
        return pwuid.pw_name

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

    def _print_mod_time(self, path):
        if self.date:
            self._cprint(
                self._get_date(path=path),
                color=self.date_color,
                attrs=self.date_attrs,
                end=" ",
            )

    def _print_path(self, path, color, attrs):
        print_path = path if self.full_path else os.path.basename(path)
        self._cprint(print_path, color=color, attrs=attrs)

    def _print_permissions(self, path):
        for var, callback in (
            (self.permissions, self._get_permissions),
            (self.user, self._get_user),
            (self.group, self._get_group),
        ):
            if var:
                self._cprint(
                    callback(path=path),
                    color=self.permissions_color,
                    attrs=self.permissions_attrs,
                    end=" ",
                )

    def _print_size(self, path):
        if self.size or self.nice_size:
            self._cprint(
                self._get_size(path=path),
                color=self.size_color,
                attrs=self.size_attrs,
                end=" ",
            )

    def _register_path(self, path):
        if path in self._resolved_paths:
            return
        self._resolved_paths.add(os.path.realpath(path))
        isdir = os.path.isdir(path)
        islink = os.path.islink(path)
        exists = os.path.exists(path)
        if islink:
            if exists:
                key = "directory links" if isdir else "file links"
            else:
                key = "broken links"
        else:
            if exists:
                key = "directories" if isdir else "files"
            else:
                return
        self._counter[key] += 1

    def _run(self, path, _prefix=""):
        """Recursively print the tree for the specified path."""
        color, attrs, inside = self._details(path=path)
        self._cprint(
            _prefix,
            color=self.tree_color,
            attrs=self.tree_attrs,
            end="",
        )
        self._print_permissions(path=path)
        self._print_size(path=path)
        self._print_mod_time(path=path)
        self._print_path(path=path, color=color, attrs=attrs)
        self._register_path(path=path)
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

    def _seen_inside(self, path):
        return self.follow_links and (
            os.path.realpath(path) in self._resolved_paths
        )

    def _summarize(self):
        self._cprint(", ".join(
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
