# `ccli` - Custom Command-Line Interface

Interface for various command-line utilities that have been customized in some way. Includes classic
utilities with slight customizations as well as new utilities.

## Installation

Please install [pipx](!https://github.com/pypa/pipx) and run:

```zsh
pipx install git+https://github.com/rmmckay/ccli.git
```

## Quick Start

```zsh
% ccli --help
Usage: ccli [OPTIONS] COMMAND [ARGS]...

  Custom Command-Line Utilities.

Options:
  --help  Show this message and exit.

Commands:
  tree  Pretty listing of directory structures.
% ccli tree
.
├―― a_dir
│   ├―― a_file
│   ├―― b_file
│   └―― c_dir
├―― a_file
├―― b_file
├―― broken_link
└―― c_file
2 directories, 1 file link, 4 files, 1 directory link, 1 broken link
```

## Project Structure

Some considerations went into designing the commands to allow them to be lazily loaded and easily
extensible.

### Lazy Loading

`ccli` uses `click` for command-line interfaces. It modifies
[this recipe](!https://click.palletsprojects.com/en/8.1.x/complex/#defining-the-lazy-group)
to allow quick help options. The procedure for making a new command is:

1. Add a new subpackage under ccli/commands. It should have the following structure:

  ```zsh
  <name of the subpackage>
  ├―― __init__.py
  ├―― cli.py # has the click command/group function. This will be auto-imported.
  ├―― main.py # has the real workings and won't be imported unless cli.py does so.
  └―― <other files optional>
  ```

1. cli.py should `invoke_main()`. See examples of how this is done.

### Testing

``ccli`` uses the ``pytest`` framework.
Tests go inside the "tests" directory and should have a similar structure to:

  ```zsh
  tests
  ├―― __init__.py
  └―― commands
      └―― <command name>
          ├―― test_cli.py
          ├―― test_main.py
          └―― <other files optional>
  ```

Integration tests should be marked as such:
``pytest.mark.integration``
The intent is to (A) make unit tests run faster, (B) de-couple coverage from behavior, and (C) make
it obvious where to find/add associated tests. Then, ``pytest -k`` makes it simple to select which
tests to run.

## Version Information

### 0.1.4

* Adds `-u` (user)

### 0.1.3

* Adds `-C` (force color)
* Adds `-n` (no color)

### 0.1.2

* `-f` (follow links)
  * Handles previously-encountered paths.
  * Corrects report.
* Report shows broken links instead of bundling them with file links.

### 0.1.1

* Adds report (default) and `--noreport` option.
* Fixes bug with non-existing input paths.
* Adds versioning test.

### 0.1.0

* Custom version of the `tree` utility.
