#!/usr/bin/env python3
"""Check English/Chinese coverage and reviewed version pairs; never translate text.

The default is read-only. After reviewing both editions, use --record PATH.md
--note REASON (or explicitly --record-all --note REASON for initial migration).
Matching hashes identify reviewed versions, not semantic translation quality.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "book/i18n/config.json"
CHAPTER = re.compile(r"^(\d{2})-.+\.md$")
HASH = re.compile(r"[a-f0-9]{64}")


class TranslationError(ValueError):
    """An edition or synchronization record cannot be validated."""


def require(condition, message):
    if not condition:
        raise TranslationError(message)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TranslationError(f"{path}: cannot read JSON: {error}") from error


def repository_path(root, name):
    require(isinstance(name, str) and bool(name), "expected repository-relative path")
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ".." not in relative.parts and
            "\\" not in name and str(relative) == name,
            f"non-canonical repository path: {name}")
    path = root / name
    require(path.resolve() == path, f"symlink path is not allowed: {name}")
    return path


def source_name(name):
    return name[:-6] + ".md" if name.endswith(".zh.md") else name


def translation_name(name):
    require(name.endswith(".md") and not name.endswith(".zh.md"),
            f"expected English .md source: {name}")
    return name[:-3] + ".zh.md"


def is_chapter(name):
    return not name.endswith(".zh.md") and bool(CHAPTER.fullmatch(PurePosixPath(name).name))


def load_config(root, name=CONFIG):
    config = read_json(repository_path(root, name))
    require(isinstance(config, dict), "translation config must be an object")
    expected = {
        "version", "source_language", "translation_language", "translation_suffix",
        "reader_roots", "extra_pages", "expected_reader_pages", "expected_chapters", "sync_file",
    }
    require(set(config) == expected, f"{name}: unexpected or missing config fields")
    require(config["version"] == 1 and config["source_language"] == "en" and
            config["translation_language"] == "zh-CN" and config["translation_suffix"] == ".zh.md",
            f"{name}: expected English source and .zh.md Simplified Chinese companions")
    for key in ("reader_roots", "extra_pages"):
        values = config[key]
        require(isinstance(values, list) and all(isinstance(v, str) for v in values),
                f"{name}: {key} must be a path array")
        require(len(values) == len(set(values)), f"{name}: duplicate {key}")
        for value in values:
            repository_path(root, value)
    require(bool(config["reader_roots"]), f"{name}: reader_roots cannot be empty")
    for key in ("expected_reader_pages", "expected_chapters"):
        require(type(config[key]) is int and config[key] > 0, f"{name}: invalid {key}")
    for value in config["extra_pages"]:
        translation_name(value)
    repository_path(root, config["sync_file"])
    return config


def inventory(root, config):
    """Return logical English paths, with counts independent of translation files."""
    readers = set()
    orphaned = []
    for directory in config["reader_roots"]:
        base = repository_path(root, directory)
        require(base.is_dir(), f"missing reader directory: {directory}")
        for path in sorted(base.rglob("*.md")):
            name = path.relative_to(root).as_posix()
            repository_path(root, name)
            if name.endswith(".zh.md"):
                if not (root / source_name(name)).is_file():
                    orphaned.append(name)
            else:
                readers.add(name)
    sources = readers | set(config["extra_pages"])
    chapters = {name for name in readers if is_chapter(name)}
    problems = [f"{name}: orphaned Chinese translation" for name in orphaned]
    if len(readers) != config["expected_reader_pages"]:
        problems.append(f"reader pages={len(readers)}, expected={config['expected_reader_pages']}")
    if len(chapters) != config["expected_chapters"]:
        problems.append(f"knowledge chapters={len(chapters)}, expected={config['expected_chapters']}")
    for name in sorted(sources):
        for path in (name, translation_name(name)):
            if not repository_path(root, path).is_file():
                problems.append(f"{path}: missing {'Chinese companion' if path.endswith('.zh.md') else 'English source'}")
    return sorted(sources), sorted(chapters), problems


def headings(text, name):
    if __package__:
        from .build_book import segments, visible_headings
    else:
        from build_book import segments, visible_headings

    return [(len(match[1]), match[2]) for match in visible_headings(list(segments(text, name)))]


def content_problems(root, sources):
    if __package__:
        from .build_book import BookError, chinese
    else:
        from build_book import BookError, chinese

    problems = []
    for name in sources:
        companion = translation_name(name)
        if not (root / name).is_file() or not (root / companion).is_file():
            continue
        try:
            english = (root / name).read_text(encoding="utf-8")
            chinese_text = (root / companion).read_text(encoding="utf-8")
            en_headings, zh_headings = headings(english, name), headings(chinese_text, companion)
        except (OSError, UnicodeError, BookError) as error:
            problems.append(f"{name}: {error}")
            continue
        if english == chinese_text:
            problems.append(f"{name}: identical editions; a fallback is not a translation")
        en_h1 = [title for level, title in en_headings if level == 1]
        zh_h1 = [title for level, title in zh_headings if level == 1]
        for path, titles in ((name, en_h1), (companion, zh_h1)):
            if len(titles) != 1:
                problems.append(f"{path}: expected one H1, found {len(titles)}")
        if len(en_h1) == 1 and not re.search(r"[A-Za-z]{2}", en_h1[0]):
            problems.append(f"{name}: English H1 is missing; check for untranslated fallback")
        if is_chapter(name):
            number = int(PurePosixPath(name).name.split("-", 1)[0])
            if number == 0:
                problems.append(f"{name}: chapter numbers start at 1")
                continue
            if len(en_h1) == 1 and not re.fullmatch(rf"Chapter {number}: \S.*", en_h1[0]):
                problems.append(f"{name}: expected H1 '# Chapter {number}: Title'")
            if len(zh_h1) == 1 and not re.fullmatch(
                rf"第(?:{number}|{chinese(number)})章[：:]\s*\S.*", zh_h1[0]
            ):
                problems.append(f"{companion}: Chinese H1 chapter number does not match filename")
        numbered = lambda items: [
            (level, match[1])
            for level, title in items if level in (2, 3)
            if (match := re.match(r"(\d+(?:\.\d+)+)\s", title))
        ]
        if numbered(en_headings) != numbered(zh_headings):
            problems.append(f"{name}: English/Chinese H2/H3 section numbers differ")
    return problems


def empty_records():
    return {"version": 1, "source_language": "en", "translation_language": "zh-CN", "pairs": {}}


def load_records(root, config, allow_missing=False):
    path = repository_path(root, config["sync_file"])
    if allow_missing and not path.exists():
        return empty_records()
    records = read_json(path)
    require(isinstance(records, dict) and set(records) == set(empty_records()),
            f"{path}: invalid synchronization record fields")
    require(records["version"] == 1 and records["source_language"] == "en" and
            records["translation_language"] == "zh-CN" and isinstance(records["pairs"], dict),
            f"{path}: expected English-source synchronization records")
    for name, pair in records["pairs"].items():
        repository_path(root, name)
        require(isinstance(pair, dict) and set(pair) == {
            "translation", "source_sha256", "translation_sha256", "reviewed_at", "note",
        }, f"{name}: invalid pair record")
        require(pair["translation"] == translation_name(name), f"{name}: wrong translation path")
        for key in ("source_sha256", "translation_sha256"):
            require(isinstance(pair[key], str) and HASH.fullmatch(pair[key]),
                    f"{name}: invalid {key}")
        require(isinstance(pair["note"], str) and pair["note"].strip(),
                f"{name}: missing review note")
        require(isinstance(pair["reviewed_at"], str), f"{name}: invalid review timestamp")
        try:
            timestamp = datetime.fromisoformat(pair["reviewed_at"])
        except ValueError as error:
            raise TranslationError(f"{name}: invalid review timestamp") from error
        require(timestamp.tzinfo is not None, f"{name}: review timestamp needs a timezone")
    return records


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synchronization_problems(root, sources, records):
    pairs = records["pairs"]
    problems = [f"{name}: synchronization record outside reader coverage"
                for name in sorted(pairs.keys() - set(sources))]
    for name in sources:
        if name not in pairs:
            problems.append(f"{name}: missing reviewed version pair")
            continue
        for path, key, label in (
            (name, "source_sha256", "English source"),
            (translation_name(name), "translation_sha256", "Chinese companion"),
        ):
            if (root / path).is_file() and digest(root / path) != pairs[name][key]:
                problems.append(f"{path}: stale version pair ({label} changed); review both editions")
    return problems


def validate_translations(root=ROOT, config_name=CONFIG):
    """Return all coverage/version errors without writing or refreshing records."""
    root = Path(root).resolve()
    try:
        config = load_config(root, config_name)
        sources, _, problems = inventory(root, config)
        problems.extend(content_problems(root, sources))
        try:
            records = load_records(root, config)
            problems.extend(synchronization_problems(root, sources, records))
        except TranslationError as error:
            problems.append(str(error))
        return problems
    except (TranslationError, OSError, UnicodeError) as error:
        return [str(error)]


def write_records(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".sync-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository or fixture root")
    parser.add_argument("--config", default=CONFIG, help="repository-relative coverage configuration")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--record", nargs="+", metavar="PATH.md", help="explicitly record reviewed English paths")
    action.add_argument("--record-all", action="store_true", help="explicitly record every reviewed pair")
    parser.add_argument("--note", help="nonempty account of the review, not a claim based only on hashes")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    recording = bool(args.record or args.record_all)
    try:
        require(recording == (args.note is not None), "--note is required only with --record or --record-all")
        if recording:
            require(bool(args.note.strip()), "--note must describe the review")
        config = load_config(root, args.config)
        sources, chapters, problems = inventory(root, config)
        problems.extend(content_problems(root, sources))
        if problems:
            raise TranslationError("\n".join(problems))
        records = load_records(root, config, allow_missing=recording)
        if recording:
            selected = sources if args.record_all else args.record
            require(len(selected) == len(set(selected)), "duplicate --record path")
            for name in selected:
                require(name in sources, f"{name}: --record requires an English path in reader coverage")
            require(not (records["pairs"].keys() - set(sources)),
                    "record contains removed pages; review and remove their obsolete entries explicitly")
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for name in selected:
                records["pairs"][name] = {
                    "translation": translation_name(name),
                    "source_sha256": digest(root / name),
                    "translation_sha256": digest(root / translation_name(name)),
                    "reviewed_at": stamp,
                    "note": args.note.strip(),
                }
            write_records(repository_path(root, config["sync_file"]), records)
            print(f"Recorded {len(selected)} reviewed version pairs; hashes do not establish semantic quality.")
        else:
            problems = synchronization_problems(root, sources, records)
            if problems:
                raise TranslationError("\n".join(problems))
            print(f"English/Chinese pairs={len(sources)} knowledge chapters={len(chapters)} issues=0")
    except (TranslationError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
