"""Offline installer tests; fixtures and scratch files stay in this checkout."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import unittest
from unittest.mock import patch
import uuid
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "install_epub_tools.py"
SPEC = importlib.util.spec_from_file_location("install_epub_tools", SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = installer
with patch("subprocess.run", side_effect=AssertionError("Command invoked during import")), \
        patch("urllib.request.build_opener", side_effect=AssertionError("Network used during import")):
    SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.root = SCRIPT.parent.parent / f".installer-tests-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root)
        self.mock(installer, "ROOT", self.root)
        self.tools = self.root / "book/epub/.tools"
        self.mock(installer, "TOOLS", self.tools)
        self.mock(installer, "MANIFEST", self.root / "book/epub/tools.json")
        self.run = self.mock(
            installer.subprocess, "run",
            side_effect=AssertionError("Unexpected external command"),
        )
        self.network = self.mock(
            installer.urllib.request, "build_opener",
            side_effect=AssertionError("Unexpected network access"),
        )
        self.mock(installer.sys, "stdout", io.StringIO())

    def mock(self, target, name, *args, **kwargs):
        patcher = patch.object(target, name, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def archive(self, format_name="zip", entries=None, name="fixture"):
        if entries is None:
            entries = [("release/bin/tool", "file", b"fixture", 0o755)]
        path = self.root / f"{name}.{format_name}"
        if format_name == "zip":
            with zipfile.ZipFile(path, "w") as archive:
                for member_name, kind, payload, mode in entries:
                    info = zipfile.ZipInfo(member_name)
                    info.create_system = 3
                    kind_mode = {
                        "file": stat.S_IFREG, "directory": stat.S_IFDIR,
                        "symlink": stat.S_IFLNK, "device": stat.S_IFCHR,
                    }[kind]
                    info.external_attr = (kind_mode | mode) << 16
                    archive.writestr(info, payload)
        else:
            with tarfile.open(path, "w:gz") as archive:
                for member_name, kind, payload, mode in entries:
                    info = tarfile.TarInfo(member_name)
                    info.mode = mode
                    info.type = {
                        "file": tarfile.REGTYPE, "directory": tarfile.DIRTYPE,
                        "symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE,
                        "device": tarfile.CHRTYPE,
                    }[kind]
                    if kind in ("symlink", "hardlink"):
                        info.linkname = payload.decode()
                    info.size = len(payload) if kind == "file" else 0
                    archive.addfile(info, io.BytesIO(payload) if kind == "file" else None)
        data = path.read_bytes()
        return path, {
            "root": "release", "format": format_name, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "url": f"https://github.com/jgm/pandoc/releases/download/3.6.4/{path.name}",
        }

    def member(self, name="release/bin/tool", kind="file", target="", size=1):
        return installer.Member(name, kind, size, 0o644, None, target)

    def installation_fixture(self, existing=True):
        self.tools.mkdir(parents=True)
        pandoc, pandoc_artifact = self.archive(name="pandoc", entries=[
            ("release/bin/pandoc", "file", b"new pandoc", 0o755),
        ])
        epubcheck, epubcheck_artifact = self.archive(name="epubcheck", entries=[
            ("release/epubcheck.jar", "file", b"new epubcheck", 0o644),
            ("release/lib/dependency.jar", "file", b"dependency", 0o644),
        ])
        manifest = {
            "schema_version": 1,
            "pandoc": {"version": "3.6.4", "platforms": {"linux-x64": pandoc_artifact}},
            "epubcheck": {"version": "5.2.1", "artifact": epubcheck_artifact},
        }
        installer.MANIFEST.write_text(json.dumps(manifest), encoding="utf-8")
        self.mock(installer, "platform_key", return_value="linux-x64")
        self.mock(installer, "java_command", return_value="fixture-java")
        self.mock(installer, "download", side_effect=[pandoc, epubcheck])
        self.run.side_effect = [
            subprocess.CompletedProcess([], 0, "pandoc 3.6.4\n", ""),
            subprocess.CompletedProcess([], 0, "EPUBCheck v5.2.1\n", ""),
        ]
        if existing:
            for name in ("pandoc", "epubcheck"):
                (self.tools / name).mkdir()
                (self.tools / name / "original").write_text(name)

    def assert_original_installation(self):
        for name in ("pandoc", "epubcheck"):
            path = self.tools / name
            self.assertEqual(list(path.iterdir()), [path / "original"])
            self.assertEqual((path / "original").read_text(), name)

    def assert_no_staging(self):
        self.assertEqual(list(self.tools.glob(".install-*")), [])

    def test_supported_platforms_and_architecture_aliases(self):
        for system, machine, expected in [
            ("Darwin", "arm64", "macos-arm64"),
            ("Darwin", "x86_64", "macos-x64"),
            ("Linux", "aarch64", "linux-arm64"),
            ("Linux", "arm64", "linux-arm64"),
            ("Linux", "x86_64", "linux-x64"),
            ("Linux", "AMD64", "linux-x64"),
        ]:
            with self.subTest(system=system, machine=machine), \
                    patch.object(installer.platform, "system", return_value=system), \
                    patch.object(installer.platform, "machine", return_value=machine):
                self.assertEqual(installer.platform_key(), expected)

    def test_unsupported_platforms(self):
        for system, machine in [("Windows", "AMD64"), ("Linux", "riscv64")]:
            with self.subTest(system=system, machine=machine), \
                    patch.object(installer.platform, "system", return_value=system), \
                    patch.object(installer.platform, "machine", return_value=machine):
                with self.assertRaisesRegex(installer.InstallError, "Unsupported platform"):
                    installer.platform_key()

    def test_digest_is_checked_before_opening_or_extracting_archive(self):
        path, artifact = self.archive()
        artifact["sha256"] = "0" * 64
        destination = self.root / "unpacked"
        with patch.object(installer, "archive_members") as open_archive:
            with self.assertRaisesRegex(installer.InstallError, "SHA-256 mismatch"):
                installer.extract_archive(path, artifact, destination)
        open_archive.assert_not_called()
        self.assertFalse(destination.exists())

    def test_size_mismatch_is_rejected(self):
        path, artifact = self.archive()
        artifact["size"] += 1
        with self.assertRaisesRegex(installer.InstallError, "size mismatch"):
            installer.verify_archive(path, artifact)

    def test_cached_archive_is_verified_without_network(self):
        path, artifact = self.archive()
        self.assertEqual(installer.download(artifact, self.root), path)
        self.network.assert_not_called()
        artifact["sha256"] = "0" * 64
        with self.assertRaisesRegex(installer.InstallError, "SHA-256 mismatch"):
            installer.download(artifact, self.root)
        self.network.assert_not_called()

    def test_failed_download_checksum_leaves_no_cached_or_partial_file(self):
        path, artifact = self.archive()
        data = path.read_bytes()
        downloads = self.root / "downloads"
        downloads.mkdir()
        self.network.side_effect = None
        self.network.return_value.open.return_value = io.BytesIO(
            bytes([data[0] ^ 1]) + data[1:],
        )
        with self.assertRaisesRegex(installer.InstallError, "SHA-256 mismatch"):
            installer.download(artifact, downloads)
        self.assertEqual(list(downloads.iterdir()), [])

    def test_missing_java_provides_installation_instructions(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(installer.shutil, "which", return_value=None):
            with self.assertRaisesRegex(installer.InstallError, "Install Java separately"):
                installer.java_command()
        self.run.assert_not_called()

    def test_missing_java_does_not_create_installation_output(self):
        self.mock(installer, "platform_key", return_value="linux-x64")
        self.mock(installer, "java_command", side_effect=installer.InstallError("Missing Java"))
        with self.assertRaisesRegex(installer.InstallError, "Missing Java"):
            installer.install()
        self.assertFalse(self.tools.exists())
        self.network.assert_not_called()
        self.run.assert_not_called()

    def test_broken_java_home_and_timeout_provide_instructions(self):
        for error in (FileNotFoundError("not installed"), subprocess.TimeoutExpired("java", 30)):
            with self.subTest(error=type(error).__name__), \
                    patch.dict(os.environ, {"JAVA_HOME": str(self.root / "jdk")}, clear=True):
                self.run.side_effect = error
                with self.assertRaisesRegex(installer.InstallError, "Install Java separately"):
                    installer.java_command()

    def test_java_launcher_failure_is_not_treated_as_installed(self):
        self.run.side_effect = None
        self.run.return_value = subprocess.CompletedProcess([], 1, "", "No Java runtime present")
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(installer.shutil, "which", return_value="fixture-java"):
            with self.assertRaisesRegex(installer.InstallError, "No Java runtime present"):
                installer.java_command()

    def test_java_home_takes_precedence_over_path(self):
        java_home = str(self.root / "jdk")
        self.run.side_effect = None
        self.run.return_value = subprocess.CompletedProcess([], 0, "", "openjdk version 17")
        with patch.dict(os.environ, {"JAVA_HOME": java_home}, clear=True), \
                patch.object(installer.shutil, "which") as which:
            self.assertEqual(installer.java_command(), str(Path(java_home) / "bin/java"))
        which.assert_not_called()
        self.run.assert_called_once_with(
            [str(Path(java_home) / "bin/java"), "-version"],
            capture_output=True, text=True, timeout=30,
        )

    def test_java_on_path_is_supported(self):
        self.run.side_effect = None
        self.run.return_value = subprocess.CompletedProcess([], 0, "", "openjdk version 17")
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(installer.shutil, "which", return_value="fixture-java"):
            self.assertEqual(installer.java_command(), "fixture-java")

    def test_paths_reject_traversal_absolute_and_ambiguous_names(self):
        for name in (
            "../outside", "/release/tool", "release/../outside", "release/./tool",
            "release//tool", r"release\tool", "C:/release/tool", "release/\0tool",
        ):
            with self.subTest(name=name):
                with self.assertRaises(installer.InstallError):
                    installer.validate_members([self.member(name)], "release")

    def test_member_roots_duplicates_and_non_directory_parents(self):
        cases = [
            [self.member("other/tool")],
            [self.member("release")],
            [self.member(), self.member()],
            [self.member(), self.member("release/bin/TOOL")],
            [self.member(), self.member("release/bin/tool/child")],
        ]
        for members in cases:
            with self.subTest(names=[member.name for member in members]):
                with self.assertRaises(installer.InstallError):
                    installer.validate_members(members, "release")

    def test_links_must_target_a_direct_archived_regular_file(self):
        for target in ("../tool", "/outside", r"..\tool", "missing", "alias"):
            with self.subTest(target=target):
                members = [
                    self.member(),
                    self.member("release/bin/alias", "symlink", target),
                ]
                with self.assertRaises(installer.InstallError):
                    installer.validate_members(members, "release")
        for other in (
            self.member("release/bin/directory", "directory"),
            self.member("release/bin/second", "symlink", "tool"),
        ):
            with self.subTest(target_kind=other.kind):
                with self.assertRaises(installer.InstallError):
                    installer.validate_members([
                        self.member(), other,
                        self.member("release/bin/alias", "symlink", Path(other.name).name),
                    ], "release")

    def test_safe_zip_and_tar_links_are_validated_but_not_materialized(self):
        for format_name in ("zip", "tar.gz"):
            with self.subTest(format=format_name):
                path, artifact = self.archive(format_name, [
                    ("release/", "directory", b"", 0o755),
                    ("release/bin/tool", "file", b"fixture", 0o755),
                    ("release/bin/alias", "symlink", b"tool", 0o777),
                    ("release/lib/dependency.jar", "file", b"dependency", 0o644),
                ])
                destination = self.root / f"unpacked-{format_name}"
                installer.extract_archive(path, artifact, destination)
                self.assertEqual((destination / "bin/tool").read_bytes(), b"fixture")
                self.assertEqual((destination / "lib/dependency.jar").read_bytes(), b"dependency")
                self.assertFalse((destination / "bin/alias").exists())
                self.assertFalse(any(path.is_symlink() for path in destination.rglob("*")))
                self.assertEqual(stat.S_IMODE((destination / "bin/tool").stat().st_mode), 0o755)

    def test_invalid_members_are_rejected_before_any_output(self):
        for format_name in ("zip", "tar.gz"):
            for entry in [
                ("release/../outside", "file", b"fixture", 0o644),
                ("release/bin/alias", "symlink", b"../../outside", 0o777),
                ("release/device", "device", b"", 0o644),
            ]:
                with self.subTest(format=format_name, entry=entry[:2]):
                    path, artifact = self.archive(format_name, [
                        ("release/bin/tool", "file", b"fixture", 0o755), entry,
                    ])
                    destination = self.root / "unpacked"
                    with self.assertRaises(installer.InstallError):
                        installer.extract_archive(path, artifact, destination)
                    self.assertFalse(destination.exists())
                    self.assertFalse((self.root / "outside").exists())

    def test_tar_hardlinks_are_not_supported(self):
        path, artifact = self.archive("tar.gz", [
            ("release/bin/tool", "file", b"fixture", 0o755),
            ("release/bin/alias", "hardlink", b"release/bin/tool", 0o755),
        ])
        with self.assertRaisesRegex(installer.InstallError, "Unsupported archive member"):
            installer.extract_archive(path, artifact, self.root / "unpacked")
        self.assertFalse((self.root / "unpacked").exists())

    def test_archive_limits_are_enforced(self):
        with patch.object(installer, "MAX_MEMBERS", 1):
            with self.assertRaisesRegex(installer.InstallError, "Too many archive members"):
                installer.validate_members([self.member(), self.member("release/second")], "release")
        with patch.object(installer, "MAX_UNPACKED", 1):
            with self.assertRaisesRegex(installer.InstallError, "unpacked size limit"):
                installer.validate_members([self.member(size=2)], "release")

    def test_existing_extraction_destination_is_preserved(self):
        path, artifact = self.archive()
        destination = self.root / "unpacked"
        destination.mkdir()
        sentinel = destination / "original"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(installer.InstallError, "already exists"):
            installer.extract_archive(path, artifact, destination)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(list(destination.iterdir()), [sentinel])

    def test_directory_creation_rejects_symlinked_ancestors(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "book").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "Refusing symbolic link"):
            installer.ensure_directory(self.tools)
        self.assertEqual(list(outside.iterdir()), [])

    def test_directory_creation_cannot_leave_worktree(self):
        with self.assertRaises(ValueError):
            installer.ensure_directory(self.root.parent / "not-this-worktree")

    def test_archive_and_output_symlinks_are_rejected(self):
        path, artifact = self.archive()
        link = self.root / "linked-archive"
        link.symlink_to(path)
        with self.assertRaisesRegex(installer.InstallError, "Not a regular archive"):
            installer.verify_archive(link, artifact)
        destination = self.root / "linked-output"
        destination.symlink_to(self.root / "missing", target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "already exists"):
            installer.extract_archive(path, artifact, destination)
        self.assertFalse((self.root / "missing").exists())

    def test_replacement_rejects_symlinked_installation(self):
        source = self.root / "new"
        source.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        destination = self.root / "current"
        destination.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, "Refusing symbolic link"):
            installer.replace_installation(source, destination, self.root / "backup")
        self.assertTrue(source.is_dir())
        self.assertTrue(destination.is_symlink())
        self.assertEqual(list(outside.iterdir()), [])

    def test_replacement_failure_restores_previous_directory(self):
        source = self.root / "new"
        source.mkdir()
        destination = self.root / "current"
        destination.mkdir()
        (destination / "original").write_text("keep")
        backup = self.root / "backup"
        rename = Path.rename

        def fail_promotion(path, target):
            if path == source:
                raise OSError("simulated promotion failure")
            return rename(path, target)

        with patch.object(Path, "rename", fail_promotion):
            with self.assertRaisesRegex(OSError, "simulated promotion failure"):
                installer.replace_installation(source, destination, backup)
        self.assertEqual((destination / "original").read_text(), "keep")
        self.assertTrue(source.is_dir())
        self.assertFalse(backup.exists())

    def test_successful_installation_uses_expected_paths_and_cleans_staging(self):
        self.installation_fixture()
        installer.install()
        self.assertEqual((self.tools / "pandoc/bin/pandoc").read_bytes(), b"new pandoc")
        self.assertEqual((self.tools / "epubcheck/epubcheck.jar").read_bytes(), b"new epubcheck")
        self.assertTrue((self.tools / "epubcheck/lib/dependency.jar").is_file())
        self.assert_no_staging()
        self.assertEqual(self.run.call_count, 2)
        self.assertEqual(self.run.call_args_list[1].args[0][:2], ["fixture-java", "-jar"])
        self.network.assert_not_called()

    def test_version_failure_preserves_both_existing_installations(self):
        self.installation_fixture()
        self.run.side_effect = [
            subprocess.CompletedProcess([], 0, "pandoc 3.6.4\n", ""),
            subprocess.CompletedProcess([], 1, "", "fixture Java failure"),
        ]
        with self.assertRaisesRegex(installer.InstallError, "fixture Java failure"):
            installer.install()
        self.assert_original_installation()
        self.assert_no_staging()

    def test_second_promotion_failure_rolls_back_both_tools(self):
        self.installation_fixture()
        rename = Path.rename

        def fail_second_promotion(path, target):
            if path.name == "epubcheck" and path.parent.name.startswith(".install-"):
                raise OSError("simulated second promotion failure")
            return rename(path, target)

        with patch.object(Path, "rename", fail_second_promotion):
            with self.assertRaisesRegex(OSError, "simulated second promotion failure"):
                installer.install()
        self.assert_original_installation()
        self.assert_no_staging()

    def test_failed_first_installation_leaves_neither_tool(self):
        self.installation_fixture(existing=False)
        rename = Path.rename

        def fail_second_promotion(path, target):
            if path.name == "epubcheck" and path.parent.name.startswith(".install-"):
                raise OSError("simulated second promotion failure")
            return rename(path, target)

        with patch.object(Path, "rename", fail_second_promotion):
            with self.assertRaisesRegex(OSError, "simulated second promotion failure"):
                installer.install()
        self.assertFalse((self.tools / "pandoc").exists())
        self.assertFalse((self.tools / "epubcheck").exists())
        self.assert_no_staging()

    def test_existing_lock_is_preserved_without_modifying_installation(self):
        self.installation_fixture()
        lock = self.tools / ".install-lock"
        lock.mkdir()
        with self.assertRaisesRegex(installer.InstallError, "Installer lock exists"):
            installer.install()
        self.assertTrue(lock.is_dir())
        self.assert_original_installation()
        installer.download.assert_not_called()
        self.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
