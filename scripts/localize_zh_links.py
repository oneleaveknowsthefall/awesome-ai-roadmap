#!/usr/bin/env python3
"""Check or atomically migrate local Markdown links in Chinese translations."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from urllib.parse import unquote

try:
    from .markdown_links import MarkdownLinkError, markup_url, rewrite_links
except ImportError:
    from markdown_links import MarkdownLinkError, markup_url, rewrite_links


ROOT = Path(__file__).absolute().parents[1]
REQUIRED_PAGES = ("README.md", "CONTRIBUTING.md", "book/README.md")


class MigrationError(ValueError):
    """A migration precondition failed; no partial migration is acceptable."""


@dataclass
class Change:
    path: Path
    before: bytes
    after: bytes
    mode: int
    links: int


def _no_symlinks(path):
    for component in reversed((path, *path.parents)):
        if component.is_symlink():
            raise MigrationError(f"symlink path is not allowed: {component}")


def _root(value):
    path = Path(value)
    if ".." in path.parts or any(ord(char) < 32 for char in str(value)):
        raise MigrationError(f"path traversal in --root: {value}")
    path = path.absolute()
    _no_symlinks(path)
    if not path.is_dir():
        raise MigrationError(f"repository root is not a directory: {path}")
    return path


def _checked(root, relative, *, file=False):
    path = root / relative
    if not path.is_relative_to(root) or ".." in path.parts:
        raise MigrationError(f"path escapes repository root: {relative}")
    _no_symlinks(path)
    if not path.exists():
        raise MigrationError(f"missing target: {relative}")
    if file and not path.is_file():
        raise MigrationError(f"target is not a regular file: {relative}")
    if not path.is_file() and not path.is_dir():
        raise MigrationError(f"unsupported target type: {relative}")
    return path


def _normal(relative):
    return relative[:-6] + ".md"


def _companion(relative):
    return relative[:-3] + ".zh.md"


def _source(root, value):
    path = Path(value)
    if (".." in path.parts or "\\" in str(value) or
            any(ord(char) < 32 for char in str(value))):
        raise MigrationError(f"path traversal/non-portable source path: {value}")
    if path.is_absolute():
        if not path.is_relative_to(root):
            raise MigrationError(f"source escapes repository root: {value}")
        path = path.relative_to(root)
    relative = path.as_posix()
    if not relative.endswith(".zh.md"):
        raise MigrationError(f"source must be a .zh.md translation: {value}")
    _checked(root, relative, file=True)
    _checked(root, _normal(relative), file=True)
    return relative


def _discover(root):
    names = []
    docs = root / "docs"
    if docs.exists() or docs.is_symlink():
        _checked(root, "docs")
        if not docs.is_dir():
            raise MigrationError("docs is not a directory")
        for directory, directories, files in os.walk(docs, followlinks=False):
            for name in directories:
                path = Path(directory) / name
                if path.is_symlink():
                    raise MigrationError(f"symlink directory is not allowed: {path.relative_to(root)}")
            for name in files:
                if name.endswith(".zh.md"):
                    names.append((Path(directory) / name).relative_to(root).as_posix())
    for normal in REQUIRED_PAGES:
        name = _companion(normal)
        if (root / name).exists() or (root / name).is_symlink():
            names.append(name)
        else:
            raise MigrationError(f"missing required Chinese companion: {name}")
    if not names:
        raise MigrationError("no Chinese translations found")
    return sorted(names)


def _relative_target(source, path):
    parts = [] if path.startswith("/") else source.split("/")[:-1]
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise MigrationError(f"link escapes repository root: {path}")
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


class _Plan:
    def __init__(self, root):
        self.root = root
        self.checked = set()

    def check(self, relative, *, file=False):
        path = _checked(self.root, relative, file=file)
        self.checked.add((relative, file))
        return path

    def rewrite(self, source, raw):
        url, offsets = markup_url(raw)
        if (not url or url.startswith(("#", "?", "//")) or
                re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", url) or
                re.fullmatch(r"[^/\s@]+@[^/\s@]+\.[^/\s@]+", url)):
            return raw
        path = re.split(r"[?#]", url, maxsplit=1)[0]
        if re.search(r"%(?![0-9A-Fa-f]{2})", path):
            raise MigrationError(f"invalid URL escape: {raw}")
        try:
            decoded = unquote(path, errors="strict")
        except UnicodeError as error:
            raise MigrationError(f"invalid UTF-8 URL: {raw}") from error
        if "\\" in decoded or any(ord(char) < 32 or ord(char) == 127 for char in decoded):
            raise MigrationError(f"unsafe/non-portable local URL: {raw}")
        target = _relative_target(source, decoded)
        self.check(target, file=target.endswith(".md"))
        if not target.endswith(".md"):
            return raw
        if target.endswith(".zh.md"):
            self.check(_normal(target), file=True)
            return raw
        companion = _companion(target)
        candidate = self.root / companion
        # A broken symlink must not look like an absent, optional companion.
        if candidate.exists() or candidate.is_symlink():
            self.check(companion, file=True)
            extension = re.search(r"(?:\.|%2[eE])(?:m|%6[dD])(?:d|%64)$", path)
            if extension is None:
                raise MigrationError(f"cannot preserve source spelling of URL: {raw}")
            insertion = offsets[extension.start()]
            return raw[:insertion] + ".zh" + raw[insertion:]
        if target.startswith("docs/") or target in REQUIRED_PAGES:
            raise MigrationError(f"missing required Chinese companion: {companion} (linked as {raw})")
        return raw

    def recheck(self):
        for relative, file in sorted(self.checked):
            _checked(self.root, relative, file=file)


def _stage(path, data, mode):
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.localize-", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _write(plan, changes):
    """Stage both versions before replacing anything; retain failed recoveries."""
    staged, backups, attempted = {}, {}, []
    retained = set()
    try:
        plan.recheck()
        for change in changes:
            _no_symlinks(change.path)
            if (change.path.read_bytes() != change.before or
                    stat.S_IMODE(change.path.stat().st_mode) != change.mode):
                raise MigrationError(f"source changed during preflight: {change.path}")
        for change in changes:
            staged[change.path] = _stage(change.path, change.after, change.mode)
            backups[change.path] = _stage(change.path, change.before, change.mode)
        plan.recheck()
        for change in changes:
            if (change.path.read_bytes() != change.before or
                    stat.S_IMODE(change.path.stat().st_mode) != change.mode):
                raise MigrationError(f"source changed during staging: {change.path}")
        for change in changes:
            _no_symlinks(change.path)
            attempted.append(change.path)
            os.replace(staged[change.path], change.path)
    except BaseException as error:
        failures = []
        for path in reversed(attempted):
            try:
                _no_symlinks(path)
                os.replace(backups[path], path)
            except BaseException as rollback_error:
                retained.add(backups[path])
                failures.append(f"{path}: {rollback_error}; original retained at {backups[path]}")
        if failures:
            raise MigrationError(f"write failed: {error}; ROLLBACK FAILED: " + "; ".join(failures)) from error
        raise MigrationError(f"write failed; all original bytes restored: {error}") from error
    finally:
        for path in (*staged.values(), *backups.values()):
            if path not in retained:
                path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Losslessly localize links in .zh.md translations. By default, check "
            "docs/**/*.zh.md, root README.zh.md/CONTRIBUTING.zh.md and book/README.zh.md without writing. "
            "Only local .md destinations with existing .zh.md companions change; "
            "reader links under docs/, root README/CONTRIBUTING and book/README require companions. "
            "Code, math, comments, front matter, labels, titles and URL suffixes stay intact. "
            "All inputs and targets are checked before atomic sibling replacements; "
            "a write failure rolls back the complete batch."
        ),
        epilog="Exit status: 0 clean or successfully written; 1 changes needed or an error; 2 invalid arguments.",
    )
    parser.add_argument("--root", default=str(ROOT), metavar="ROOT", help="repository root (default: script's repository)")
    parser.add_argument("--write", action="store_true", help="apply the complete validated batch (default: check only)")
    parser.add_argument("paths", nargs="*", metavar="PATH.zh.md", help="optional translation paths relative to --root")
    arguments = parser.parse_args(argv)
    try:
        root = _root(arguments.root)
        names = arguments.paths or _discover(root)
    except (MigrationError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    plan = _Plan(root)
    changes, errors, seen = [], [], set()
    for name in names:
        try:
            relative = _source(root, name)
            if relative in seen:
                continue
            seen.add(relative)
            path = plan.check(relative, file=True)
            plan.check(_normal(relative), file=True)
            before = path.read_bytes()
            text = before.decode("utf-8")
            count = 0

            def rewrite(url):
                nonlocal count
                result = plan.rewrite(relative, url)
                count += result != url
                return result

            after = rewrite_links(text, relative, rewrite).encode("utf-8")
            if before != after:
                changes.append(Change(path, before, after, stat.S_IMODE(path.stat().st_mode), count))
        except (MigrationError, MarkdownLinkError, OSError, UnicodeError) as error:
            errors.append(f"{name}: {error}")
    for change in changes:
        print(f"{change.path.relative_to(root)}: {change.links} link(s) need localization")
    print(f"Checked {len(seen)} translation(s); {len(changes)} file(s), "
          f"{sum(change.links for change in changes)} destination(s) need changes.")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("No files written: preflight failed.", file=sys.stderr)
        return 1
    if not arguments.write:
        if changes:
            print("Check only: no files written. Run with --write to apply.")
        return int(bool(changes))
    try:
        _write(plan, changes)
    except (MigrationError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {len(changes)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
