from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "chatrail.py"

ENTRY = """## Entry: PDF is now the goal

Basis: "The goal is now PDF invoice import."

Meaning: PDF invoice import is the new main direction.
"""

COMPASS = """# Compass

## Current heading

Build PDF invoice import.

## Relation to the latest user-approved direction

This work follows the new PDF goal.

## Behind us

The old CSV goal remains visible in Rail.

## Ahead

Build PDF text extraction, then confirmation.

## Unclear

The PDF layouts are not known.
"""


class ChatRailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "codex-home"
        self.work = self.root / "work"
        self.work.mkdir()
        self.env = os.environ.copy()
        self.env["CODEX_HOME"] = str(self.home)
        self.env["CODEX_THREAD_ID"] = "thread-123"

    def tearDown(self) -> None:
        self.temp.cleanup()

    @property
    def task(self) -> Path:
        return self.home / "chatrail" / "tasks" / "thread-123"

    def command(
        self, *args: str, payload: dict | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=None if payload is None else json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=self.work,
            env=self.env,
            check=False,
        )

    def proposals(self) -> tuple[Path, Path]:
        entry = self.root / "entry.md"
        compass = self.root / "compass.md"
        entry.write_text(ENTRY)
        compass.write_text(COMPASS)
        return entry, compass

    def test_read_missing_task_is_read_only(self) -> None:
        result = self.command("read")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Rail", result.stdout)
        self.assertIn("# Compass", result.stdout)
        self.assertFalse(self.task.exists())

        self.task.mkdir(parents=True)
        (self.task / "compass.md").write_text(COMPASS)
        partial = self.command("read")
        self.assertEqual(partial.returncode, 0, partial.stderr)
        self.assertIn("# Rail", partial.stdout)
        self.assertIn(COMPASS, partial.stdout)

    def test_save_appends_rail_and_replaces_compass(self) -> None:
        entry, compass = self.proposals()
        result = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.task / "rail.md").read_text(), f"# Rail\n\n{ENTRY}")
        self.assertEqual((self.task / "compass.md").read_text(), COMPASS)

    def test_save_keeps_every_old_rail_byte(self) -> None:
        self.task.mkdir(parents=True)
        old = b"# Rail\n\nOLD BYTES WITHOUT FINAL NEWLINE"
        (self.task / "rail.md").write_bytes(old)
        entry, compass = self.proposals()

        result = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.task / "rail.md").read_bytes().startswith(old))

    def test_exact_retry_does_not_duplicate_rail(self) -> None:
        entry, compass = self.proposals()
        first = self.command("save", "--append", str(entry), "--compass", str(compass))
        second = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual((self.task / "rail.md").read_text().count(ENTRY.strip()), 1)

    def test_two_concurrent_entries_are_both_kept(self) -> None:
        _, compass = self.proposals()
        entries = []
        for name in ("A", "B"):
            path = self.root / f"{name}.md"
            path.write_text(f"## Entry: {name}\n\nBasis: user\n\nMeaning: keep {name}\n")
            entries.append(path)
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "save",
                    "--append",
                    str(entry),
                    "--compass",
                    str(compass),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.work,
                env=self.env,
            )
            for entry in entries
        ]
        results = [process.communicate() for process in processes]

        self.assertEqual([process.returncode for process in processes], [0, 0], results)
        rail = (self.task / "rail.md").read_text()
        self.assertIn("## Entry: A", rail)
        self.assertIn("## Entry: B", rail)

    def test_save_rejects_a_symlinked_task_folder(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        self.task.parent.mkdir(parents=True)
        self.task.symlink_to(outside, target_is_directory=True)
        entry, compass = self.proposals()

        result = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((outside / "rail.md").exists())
        self.assertFalse((outside / "compass.md").exists())

    def test_read_rejects_symlinked_meaning_files(self) -> None:
        secret = self.root / "secret.txt"
        secret.write_text("TOP-SECRET-LOCAL-DATA")

        for filename in ("rail.md", "compass.md"):
            with self.subTest(filename=filename):
                self.task.mkdir(parents=True, exist_ok=True)
                for path in self.task.iterdir():
                    path.unlink()
                (self.task / "rail.md").write_text("# Rail\n")
                (self.task / "compass.md").write_text(COMPASS)
                (self.task / filename).unlink()
                (self.task / filename).symlink_to(secret)

                result = self.command("read")

                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("TOP-SECRET-LOCAL-DATA", result.stdout)

    def test_read_rejects_bad_saved_headers(self) -> None:
        for filename, bad_text in (
            ("rail.md", "# Railroad\n"),
            ("compass.md", "# Compassage\n"),
        ):
            with self.subTest(filename=filename):
                self.task.mkdir(parents=True, exist_ok=True)
                for path in self.task.iterdir():
                    path.unlink()
                (self.task / "rail.md").write_text("# Rail\n")
                (self.task / "compass.md").write_text(COMPASS)
                (self.task / filename).write_text(bad_text)

                result = self.command("read")

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_save_rejects_symlinked_meaning_files(self) -> None:
        secret = self.root / "secret.txt"
        secret.write_text("keep me")
        entry, compass = self.proposals()

        for filename in ("rail.md", "compass.md"):
            with self.subTest(filename=filename):
                self.task.mkdir(parents=True, exist_ok=True)
                for path in self.task.iterdir():
                    path.unlink()
                (self.task / "rail.md").write_text("# Rail\n")
                (self.task / "compass.md").write_text(COMPASS)
                (self.task / filename).unlink()
                (self.task / filename).symlink_to(secret)

                result = self.command(
                    "save", "--append", str(entry), "--compass", str(compass)
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(secret.read_text(), "keep me")

    def test_save_rejects_bad_saved_headers(self) -> None:
        entry, compass = self.proposals()
        for filename, bad_text in (
            ("rail.md", "# Railroad\n"),
            ("compass.md", "# Compassage\n"),
        ):
            with self.subTest(filename=filename):
                self.task.mkdir(parents=True, exist_ok=True)
                for path in self.task.iterdir():
                    path.unlink()
                (self.task / "rail.md").write_text("# Rail\n")
                (self.task / "compass.md").write_text(COMPASS)
                (self.task / filename).write_text(bad_text)

                result = self.command(
                    "save", "--append", str(entry), "--compass", str(compass)
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.task / filename).read_text(), bad_text)

    def test_save_rejects_a_symlinked_lock_file(self) -> None:
        self.task.parent.mkdir(parents=True)
        outside_lock = self.root / "outside.lock"
        outside_lock.write_text("keep me")
        (self.task.parent / ".thread-123.lock").symlink_to(outside_lock)
        entry, compass = self.proposals()

        result = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(outside_lock.read_text(), "keep me")
        self.assertFalse(self.task.exists())

    def test_bad_input_changes_no_saved_file(self) -> None:
        self.task.mkdir(parents=True)
        old_rail = "# Rail\n\nKeep me.\n"
        old_compass = "# Compass\n\nKeep me.\n"
        (self.task / "rail.md").write_text(old_rail)
        (self.task / "compass.md").write_text(old_compass)
        bad = self.root / "bad.md"
        bad.write_text("not a compass")

        result = self.command("save", "--compass", str(bad))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.task / "rail.md").read_text(), old_rail)
        self.assertEqual((self.task / "compass.md").read_text(), old_compass)

    def test_compass_header_must_match_the_whole_first_line(self) -> None:
        self.task.mkdir(parents=True)
        old_rail = "# Rail\n\nKeep me.\n"
        old_compass = "# Compass\n\nKeep me.\n"
        (self.task / "rail.md").write_text(old_rail)
        (self.task / "compass.md").write_text(old_compass)
        bad_compass = self.root / "bad-compass.md"
        bad_compass.write_text("# Compassage\n\nDo not save me.\n")
        entry = self.root / "entry.md"
        entry.write_text(ENTRY)

        result = self.command(
            "save", "--append", str(entry), "--compass", str(bad_compass)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.task / "rail.md").read_text(), old_rail)
        self.assertEqual((self.task / "compass.md").read_text(), old_compass)

    def test_entry_header_must_match_the_whole_first_line(self) -> None:
        self.task.mkdir(parents=True)
        old_rail = "# Rail\n\nKeep me.\n"
        old_compass = "# Compass\n\nKeep me.\n"
        compass = self.root / "compass.md"
        compass.write_text(COMPASS)

        for first_line in (
            "## Entryway: Do not save me",
            "## Entry:way",
            "## Entry:",
        ):
            with self.subTest(first_line=first_line):
                (self.task / "rail.md").write_text(old_rail)
                (self.task / "compass.md").write_text(old_compass)
                bad_entry = self.root / "bad-entry.md"
                bad_entry.write_text(f"{first_line}\n")

                result = self.command(
                    "save", "--append", str(bad_entry), "--compass", str(compass)
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.task / "rail.md").read_text(), old_rail)
                self.assertEqual((self.task / "compass.md").read_text(), old_compass)

    def test_compass_is_written_even_without_rail_append(self) -> None:
        _, compass = self.proposals()
        result = self.command("save", "--compass", str(compass))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.task / "rail.md").read_text(), "# Rail\n")
        self.assertEqual((self.task / "compass.md").read_text(), COMPASS)

    def test_partial_save_is_safe_to_retry(self) -> None:
        spec = importlib.util.spec_from_file_location("chatrail_runtime", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        entry, compass = self.proposals()
        real_write = module.atomic_write

        def fail_rail(path: Path, data: bytes) -> None:
            if path.name == "rail.md":
                raise OSError("planned rail failure")
            real_write(path, data)

        with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.home)}):
            with mock.patch.object(module, "atomic_write", side_effect=fail_rail):
                code = module.save_files("thread-123", compass, entry)

            self.assertNotEqual(code, 0)
            self.assertEqual((self.task / "compass.md").read_text(), COMPASS)
            self.assertFalse((self.task / "rail.md").exists())
            code = module.save_files("thread-123", compass, entry)
        self.assertEqual(code, 0)
        self.assertEqual((self.task / "rail.md").read_text().count(ENTRY.strip()), 1)
        self.assertEqual((self.task / "compass.md").read_text(), COMPASS)

    def test_stop_wakes_only_the_first_root_stop(self) -> None:
        base = {"hook_event_name": "Stop", "session_id": "thread-123"}
        root = self.command("stop", payload=base)
        active = self.command("stop", payload={**base, "stop_hook_active": True})
        child = self.command("stop", payload={**base, "agent_id": "child-1"})

        self.assertEqual(json.loads(root.stdout)["decision"], "block")
        reason = json.loads(root.stdout)["reason"]
        self.assertIn("AI review", reason)
        self.assertIn("NO_SAVE", reason)
        self.assertIn("goal, proof, direction, progress, blocker, next move", reason)
        self.assertIn("write Compass only", reason)
        self.assertEqual(active.stdout, "")
        self.assertEqual(child.stdout, "")

    def test_runtime_is_small_and_has_no_semantic_engine(self) -> None:
        source = SCRIPT.read_text()
        nonblank = sum(bool(line.strip()) for line in source.splitlines())

        self.assertLessEqual(nonblank, 200)
        self.assertNotIn("sqlite", source.lower())
        self.assertNotIn("On course", source)
        self.assertNotIn("Drifting", source)
        self.assertNotIn("--rail", source)


if __name__ == "__main__":
    unittest.main()
