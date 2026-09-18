#!/usr/bin/env python3
"""Install pinned EPUB tools in this worktree using only Python's standard library.

Run: python3 scripts/install_epub_tools.py
Java is a separate prerequisite, never installed here. Downloads and staging stay
under book/epub/.tools; neither PATH nor user configuration is modified.
Checksum provenance is recorded in book/epub/tools.json. Archive links are
validated but omitted: Pandoc's optional command aliases are not needed.
"""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "book/epub/tools.json"
TOOLS = ROOT / "book/epub/.tools"
MAX_UNPACKED = 512 * 1024 * 1024
MAX_MEMBERS = 10000
JAVA_HELP = (
    "Install Java separately (for example, Temurin 17 or newer): "
    "macOS: brew install --cask temurin; "
    "Debian/Ubuntu: sudo apt-get install default-jre-headless. "
    "Then set JAVA_HOME to that installation or put java on PATH and rerun. "
    "This installer does not install Java."
)


class InstallError(ValueError):
    """A prerequisite, checksum, or archive validation failed."""


def require(condition, message):
    if not condition:
        raise InstallError(message)


def ensure_directory(path):
    """Never follow a pre-existing directory link out of this worktree."""
    relative = path.relative_to(ROOT)
    current = ROOT
    for part in relative.parts:
        current /= part
        require(not current.is_symlink(), f"Refusing symbolic link: {current}")
        current.mkdir(exist_ok=True)
        require(current.is_dir(), f"Not a directory: {current}")


def platform_key():
    system = {"Darwin": "macos", "Linux": "linux"}.get(platform.system())
    machine = platform.machine().lower()
    architecture = {
        "arm64": "arm64", "aarch64": "arm64",
        "x86_64": "x64", "amd64": "x64",
    }.get(machine)
    require(system and architecture,
            f"Unsupported platform: {platform.system()} {machine}. "
            "Supported: macOS/Linux on arm64 or x64.")
    return f"{system}-{architecture}"


def java_command():
    java_home = os.environ.get("JAVA_HOME")
    java = str(Path(java_home) / "bin/java") if java_home else shutil.which("java")
    require(java, f"Java was not found. {JAVA_HELP}")
    try:
        result = subprocess.run(
            [java, "-version"], capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise InstallError(f"Cannot run Java: {error}. {JAVA_HELP}") from error
    require(result.returncode == 0,
            f"Java is unavailable: {(result.stderr or result.stdout).strip()}\n{JAVA_HELP}")
    return java


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_archive(path, artifact):
    require(not path.is_symlink() and path.is_file(),
            f"Not a regular archive file: {path}")
    require(path.stat().st_size == artifact["size"],
            f"Archive size mismatch: {path}. Remove it and rerun.")
    actual = sha256(path)
    require(actual == artifact["sha256"],
            f"SHA-256 mismatch: {path}\n"
            f"Expected {artifact['sha256']}; received {actual}. Remove it and rerun.")


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        require(urllib.parse.urlsplit(new_url).scheme == "https",
                "Refusing a non-HTTPS download redirect.")
        return super().redirect_request(request, response, code, message, headers, new_url)


def download(artifact, downloads):
    parsed = urllib.parse.urlsplit(artifact["url"])
    require(parsed.scheme == "https" and parsed.netloc == "github.com"
            and parsed.path.startswith(("/jgm/pandoc/releases/download/",
                                        "/w3c/epubcheck/releases/download/"))
            and not parsed.query and not parsed.fragment,
            f"Not an official release URL: {artifact['url']}")
    require(re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]),
            "The tool manifest must contain a fixed SHA-256 digest.")
    require(isinstance(artifact["size"], int) and 0 < artifact["size"] <= MAX_UNPACKED,
            "Invalid archive size in tool manifest.")
    filename = parsed.path.rsplit("/", 1)[-1]
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", filename) and filename not in (".", ".."),
            "Invalid release filename.")
    destination = downloads / filename
    if destination.exists() or destination.is_symlink():
        verify_archive(destination, artifact)
        print(f"Verified cached {filename}", flush=True)
        return destination

    opener = urllib.request.build_opener(HTTPSRedirectHandler())
    request = urllib.request.Request(
        artifact["url"], headers={"User-Agent": "awesome-ai-roadmap-epub-installer"},
    )
    for attempt in range(3):
        partial = downloads / f".{filename}.{uuid.uuid4().hex}.part"
        try:
            print(f"Downloading {filename}", flush=True)
            with opener.open(request, timeout=60) as response, partial.open("xb") as output:
                total = 0
                while block := response.read(1024 * 1024):
                    total += len(block)
                    require(total <= artifact["size"], f"Oversized download: {filename}")
                    output.write(block)
            verify_archive(partial, artifact)
            partial.replace(destination)
            return destination
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt == 2:
                raise InstallError(f"Download failed for {filename}: {error}") from error
            time.sleep(attempt + 1)
        finally:
            partial.unlink(missing_ok=True)
    raise InstallError(f"Download failed for {filename}")


@dataclass
class Member:
    name: str
    kind: str
    size: int
    mode: int
    info: object
    target: str = ""


def safe_parts(name):
    require(name and "\\" not in name and ":" not in name
            and not any(ord(character) < 32 for character in name),
            f"Invalid archive path: {name!r}")
    parts = name.rstrip("/").split("/")
    require(all(part not in ("", ".", "..") for part in parts),
            f"Unsafe archive path: {name!r}")
    return parts


def validate_members(members, root):
    require(len(members) <= MAX_MEMBERS, "Too many archive members.")
    require(sum(member.size for member in members) <= MAX_UNPACKED,
            "Archive exceeds the unpacked size limit.")
    safe_parts(root)
    require("/" not in root, "Archive root must be a single directory.")
    by_name = {}
    for member in members:
        parts = safe_parts(member.name)
        require(parts[0] == root, f"Unexpected archive root: {member.name!r}")
        require(member.size >= 0, f"Invalid member size: {member.name!r}")
        require(member.kind in ("file", "directory", "symlink"),
                f"Unsupported archive member type: {member.name!r}")
        require(len(parts) > 1 or member.kind == "directory",
                "Archive root must be a directory.")
        key = "/".join(parts).casefold()
        require(key not in by_name, f"Duplicate archive path: {member.name!r}")
        by_name[key] = member
    for member in members:
        path = PurePosixPath(member.name)
        for parent in path.parents:
            other = by_name.get(str(parent).casefold())
            require(other is None or other.kind == "directory",
                    f"Archive entry has a non-directory parent: {member.name!r}")
        if member.kind == "symlink":
            target_parts = safe_parts(member.target)
            target = path.parent.joinpath(*target_parts)
            other = by_name.get(str(target).casefold())
            require(other is not None and other.kind == "file",
                    f"Archive link must point directly to an archived regular file: "
                    f"{member.name!r}")


@contextmanager
def archive_members(path, format_name):
    if format_name == "zip":
        with zipfile.ZipFile(path) as archive:
            members = []
            require(len(archive.infolist()) <= MAX_MEMBERS, "Too many archive members.")
            for info in archive.infolist():
                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                kind = "unsupported"
                if info.is_dir() and file_type in (0, stat.S_IFDIR):
                    kind = "directory"
                elif not info.is_dir() and file_type in (0, stat.S_IFREG):
                    kind = "file"
                elif file_type == stat.S_IFLNK:
                    kind = "symlink"
                require(not info.flag_bits & 1, "Encrypted archives are not supported.")
                target = ""
                if kind == "symlink":
                    require(info.file_size <= 4096, "Oversized archive link.")
                    target = archive.read(info).decode("utf-8")
                members.append(Member(info.filename, kind, info.file_size, mode, info, target))
            yield members, archive.open
    elif format_name == "tar.gz":
        with tarfile.open(path, "r:gz") as archive:
            members = []
            for info in archive:
                require(len(members) < MAX_MEMBERS, "Too many archive members.")
                kind = ("directory" if info.isdir() else "file" if info.isfile()
                        else "symlink" if info.issym() else "unsupported")
                require(not info.sparse, "Sparse archive members are not supported.")
                members.append(Member(info.name, kind, info.size, info.mode, info, info.linkname))
            yield members, archive.extractfile
    else:
        raise InstallError(f"Unsupported archive format: {format_name}")


def extract_archive(path, artifact, destination):
    verify_archive(path, artifact)
    require(not destination.exists() and not destination.is_symlink(),
            f"Extraction destination already exists: {destination}")
    with archive_members(path, artifact["format"]) as (members, open_member):
        validate_members(members, artifact["root"])
        destination.mkdir()
        for member in members:
            parts = safe_parts(member.name)[1:]
            if not parts or member.kind == "symlink":
                continue
            target = destination.joinpath(*parts)
            if member.kind == "directory":
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with open_member(member.info) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            require(target.stat().st_size == member.size,
                    f"Unpacked member size mismatch: {member.name}")
            target.chmod(0o755 if member.mode & 0o111 else 0o644)


def check_version(command, expected, label):
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    output = (result.stdout + "\n" + result.stderr).strip()
    require(result.returncode == 0 and re.search(
        rf"(?<![\d.]){re.escape(expected)}(?![\d.])", output),
        f"{label} version check failed:\n{output}")
    return output.splitlines()[0]


def replace_installation(source, destination, backup):
    require(not destination.is_symlink(), f"Refusing symbolic link: {destination}")
    require(not destination.exists() or destination.is_dir(),
            f"Not a tool directory: {destination}")
    if destination.exists():
        destination.rename(backup)
    try:
        source.rename(destination)
    except OSError:
        if backup.exists():
            backup.rename(destination)
        raise


def install():
    key = platform_key()
    java = java_command()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["schema_version"] == 1, "Unsupported tool manifest schema.")
    pandoc_artifact = manifest["pandoc"]["platforms"][key]
    epubcheck_artifact = manifest["epubcheck"]["artifact"]
    ensure_directory(TOOLS)
    downloads = TOOLS / "downloads"
    ensure_directory(downloads)
    lock = TOOLS / ".install-lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise InstallError(
            f"Installer lock exists: {lock}. If no installer is running, remove this "
            "empty directory and retry."
        ) from error
    staging = TOOLS / f".install-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        pandoc_archive = download(pandoc_artifact, downloads)
        epubcheck_archive = download(epubcheck_artifact, downloads)
        extract_archive(pandoc_archive, pandoc_artifact, staging / "pandoc")
        extract_archive(epubcheck_archive, epubcheck_artifact, staging / "epubcheck")
        pandoc = staging / "pandoc/bin/pandoc"
        jar = staging / "epubcheck/epubcheck.jar"
        require(pandoc.is_file(), "Pandoc executable is missing from the archive.")
        require(jar.is_file() and (jar.parent / "lib").is_dir(),
                "EPUBCheck JAR or its lib directory is missing from the archive.")
        pandoc.chmod(0o755)
        pandoc_version = check_version(
            [str(pandoc), "--version"], manifest["pandoc"]["version"], "Pandoc",
        )
        try:
            epubcheck_version = check_version(
                [java, "-jar", str(jar), "--version"],
                manifest["epubcheck"]["version"], "EPUBCheck",
            )
        except (InstallError, OSError, subprocess.TimeoutExpired) as error:
            raise InstallError(f"{error}\n{JAVA_HELP}") from error
        promoted = []
        try:
            for name in ("pandoc", "epubcheck"):
                replace_installation(staging / name, TOOLS / name, staging / f"old-{name}")
                promoted.append(name)
        except (InstallError, OSError):
            for name in reversed(promoted):
                shutil.rmtree(TOOLS / name)
                backup = staging / f"old-{name}"
                if backup.exists():
                    backup.rename(TOOLS / name)
            raise
        print(f"{pandoc_version}: {TOOLS / 'pandoc/bin/pandoc'}")
        print(f"{epubcheck_version}: {TOOLS / 'epubcheck/epubcheck.jar'}")
        print(f"Java: {java}")
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        install()
    except (InstallError, OSError, ValueError, KeyError, tarfile.TarError,
            zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(f"EPUB tool installation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
