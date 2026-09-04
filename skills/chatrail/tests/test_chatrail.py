from __future__ import annotations

import datetime as dt
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

TRUTH_SENTENCE = (
    "This is ChatRail's LAST saved reading, not live truth. Truth order: the "
    "user's latest words beat fresh evidence you gather; fresh evidence beats "
    "these files. Reconcile this reading against the conversation before "
    "acting on it."
)

DRIFT_SENTENCE = (
    "If the work no longer points at the latest user-approved direction, say "
    "one plain line in chat before the turn ends, naming both the work "
    "underway and the approved direction and offering refocus or approval of "
    "the new direction — stay silent only if the same divergence was "
    "already said and is unanswered, or the user's own words ordered the "
    "detour."
)

HEADING_OK = """```chatrail-heading
N: 7  # direct work on the PDF goal
E: 2  # tooling sidework
S: 0  # no reversal
W: 1  # small drift risk
```
"""


class ChatRailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "chatrail-home"
        self.work = self.root / "work"
        self.work.mkdir()
        self.env = os.environ.copy()
        self.env.pop("CODEX_HOME", None)
        self.env["CHATRAIL_HOME"] = str(self.home)
        self.env["CHATRAIL_THREAD_ID"] = "thread-123"
        self.env.pop("CODEX_THREAD_ID", None)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @property
    def tasks(self) -> Path:
        return self.home / "tasks"

    @property
    def task(self) -> Path:
        return self.tasks / "thread-123"

    @property
    def aliases(self) -> Path:
        return self.home / "aliases"

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

    def make_task(self, thread_id: str = "thread-123") -> Path:
        directory = self.tasks / thread_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "rail.md").write_text("# Rail\n")
        (directory / "compass.md").write_text(COMPASS)
        return directory

    @staticmethod
    def iso(path: Path) -> str:
        return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(
            timespec="seconds"
        )

    # --- read -----------------------------------------------------------

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

                result = self.command("read", "--thread-id", "thread-123")

                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("TOP-SECRET-LOCAL-DATA", result.stdout)
                self.assertIn(filename, result.stderr)

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

                result = self.command("read", "--thread-id", "thread-123")

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("wrong header", result.stderr)

    def test_read_with_a_malformed_alias_errors_and_names_the_file(self) -> None:
        self.make_task()
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").write_text("../escape\n")

        result = self.command("read")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(self.aliases / "thread-123"), result.stderr)

    # --- save -----------------------------------------------------------

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

        result = self.command(
            "save", "--thread-id", "thread-123", "--append", str(entry),
            "--compass", str(compass),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertFalse((outside / "rail.md").exists())
        self.assertFalse((outside / "compass.md").exists())

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
                    "save", "--thread-id", "thread-123", "--append", str(entry),
                    "--compass", str(compass),
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(filename, result.stderr)
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
                    "save", "--thread-id", "thread-123", "--append", str(entry),
                    "--compass", str(compass),
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("wrong header", result.stderr)
                self.assertEqual((self.task / filename).read_text(), bad_text)

    def test_save_rejects_a_symlinked_lock_file(self) -> None:
        self.task.parent.mkdir(parents=True)
        outside_lock = self.root / "outside.lock"
        outside_lock.write_text("keep me")
        (self.task.parent / ".thread-123.lock").symlink_to(outside_lock)
        entry, compass = self.proposals()

        result = self.command(
            "save", "--thread-id", "thread-123", "--append", str(entry),
            "--compass", str(compass),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("invalid thread id", result.stderr)
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

        with mock.patch.dict(
            os.environ,
            {"CHATRAIL_HOME": str(self.home), "CHATRAIL_THREAD_ID": "thread-123"},
        ):
            with mock.patch.object(module, "atomic_write", side_effect=fail_rail):
                code = module.save_files("thread-123", compass, entry)

            self.assertNotEqual(code, 0)
            self.assertEqual((self.task / "compass.md").read_text(), COMPASS)
            self.assertFalse((self.task / "rail.md").exists())
            code = module.save_files("thread-123", compass, entry)
        self.assertEqual(code, 0)
        self.assertEqual((self.task / "rail.md").read_text().count(ENTRY.strip()), 1)
        self.assertEqual((self.task / "compass.md").read_text(), COMPASS)

    # --- save heading block ---------------------------------------------

    def heading_save(self, block: str) -> subprocess.CompletedProcess[str]:
        compass = self.root / "compass.md"
        compass.write_text(COMPASS + "\n" + block)
        return self.command("save", "--compass", str(compass))

    def test_save_accepts_a_valid_heading_block(self) -> None:
        result = self.heading_save(HEADING_OK)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("chatrail-heading", (self.task / "compass.md").read_text())

    def test_save_accepts_a_compass_without_a_heading_block(self) -> None:
        _, compass = self.proposals()
        result = self.command("save", "--compass", str(compass))

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_save_rejects_malformed_heading_blocks(self) -> None:
        shapes = (
            (  # duplicate key
                "```chatrail-heading\nN: 7  # one\nN: 3  # twice\n"
                "S: 0  # ok\nW: 1  # ok\n```\n",
                "N: 3  # twice",
            ),
            (  # score out of range
                "```chatrail-heading\nN: 11  # too big\nE: 2  # ok\n"
                "S: 0  # ok\nW: 1  # ok\n```\n",
                "N: 11  # too big",
            ),
            (  # empty reason
                "```chatrail-heading\nN: 7  # ok\nE: 2  # \n"
                "S: 0  # ok\nW: 1  # ok\n```\n",
                "E: 2  # ",
            ),
            (  # single-space separator
                "```chatrail-heading\nN: 7 # one space\nE: 2  # ok\n"
                "S: 0  # ok\nW: 1  # ok\n```\n",
                "N: 7 # one space",
            ),
            (  # unclosed fence
                "```chatrail-heading\nN: 7  # ok\nE: 2  # ok\n"
                "S: 0  # ok\nW: 1  # ok\n",
                "chatrail-heading",
            ),
        )
        for block, offending in shapes:
            with self.subTest(offending=offending):
                result = self.heading_save(block)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(offending, result.stderr)
                self.assertFalse((self.task / "compass.md").exists())

    # --- on -------------------------------------------------------------

    def test_on_creates_the_task_and_seeds_both_files(self) -> None:
        result = self.command("on")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            f"ChatRail created new task thread-123: {self.task.resolve()}",
        )
        self.assertEqual((self.task / "rail.md").read_text(), "# Rail\n")
        self.assertTrue(
            (self.task / "compass.md").read_text().startswith("# Compass\n")
        )

    def test_on_attaches_with_entry_count_and_last_save(self) -> None:
        directory = self.make_task()
        (directory / "rail.md").write_text(f"# Rail\n\n{ENTRY}\n{ENTRY}")

        result = self.command("on")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "ChatRail attached to thread-123 · 2 rail entries · "
            f"last save {self.iso(directory / 'compass.md')}",
        )

    def test_on_never_overwrites_existing_saved_bytes(self) -> None:
        self.task.mkdir(parents=True)
        rail = "# Rail\n\n## Entry: keep me\n\nBasis: user\n\nMeaning: keep me\n"
        (self.task / "rail.md").write_text(rail)
        (self.task / "compass.md").write_text(COMPASS)

        result = self.command("on")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.task / "rail.md").read_text(), rail)
        self.assertEqual((self.task / "compass.md").read_text(), COMPASS)

    def test_on_is_idempotent(self) -> None:
        first = self.command("on")
        second = self.command("on")

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("ChatRail attached to thread-123", second.stdout)

    def test_on_unpauses_and_says_so(self) -> None:
        self.make_task()
        (self.task / ".paused").touch()

        result = self.command("on")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.task / ".paused").exists())
        self.assertIn("(resumed from pause)", result.stdout)

    def test_on_name_creates_the_named_task_and_writes_the_alias(self) -> None:
        result = self.command("on", "proj-x", "--session-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("ChatRail created new task proj-x:"))
        self.assertTrue((self.tasks / "proj-x" / "rail.md").exists())
        self.assertEqual((self.aliases / "thread-123").read_text(), "proj-x\n")

    def test_on_name_without_a_session_writes_no_alias(self) -> None:
        self.env.pop("CHATRAIL_THREAD_ID")

        result = self.command("on", "proj-y")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.tasks / "proj-y").is_dir())
        self.assertFalse(self.aliases.exists())

    def test_on_without_a_name_follows_the_alias(self) -> None:
        self.make_task("older-task")
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").write_text("older-task\n")

        result = self.command("on")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ChatRail attached to older-task", result.stdout)

    def test_on_rejects_a_name_over_64_bytes(self) -> None:
        result = self.command("on", "x" * 65)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("invalid choice", result.stderr)
        self.assertFalse(self.tasks.exists() and any(self.tasks.iterdir()))

    # --- pause ----------------------------------------------------------

    def test_pause_marks_an_existing_task(self) -> None:
        self.make_task()

        result = self.command("pause", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), f"ChatRail paused: {self.task.resolve()}"
        )
        self.assertTrue((self.task / ".paused").exists())

    def test_pause_without_a_task_fails_and_creates_nothing(self) -> None:
        result = self.command("pause", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 1)
        self.assertIn("ChatRail pause: no task for thread-123", result.stderr)
        self.assertFalse(self.task.exists())

    def test_pause_twice_says_already_paused(self) -> None:
        self.make_task()
        self.command("pause", "--thread-id", "thread-123")

        second = self.command("pause", "--thread-id", "thread-123")

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(
            second.stdout.strip(), f"ChatRail already paused: {self.task.resolve()}"
        )

    def test_stop_is_silent_while_paused(self) -> None:
        self.make_task()
        (self.task / ".paused").touch()

        result = self.command(
            "stop", payload={"hook_event_name": "Stop", "session_id": "thread-123"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_read_still_works_while_paused(self) -> None:
        self.make_task()
        (self.task / ".paused").touch()

        result = self.command("read")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(COMPASS, result.stdout)

    def test_save_is_unchanged_while_paused(self) -> None:
        self.make_task()
        (self.task / ".paused").touch()
        entry, compass = self.proposals()

        result = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "ChatRail saved: rail=appended compass=replaced"
        )
        self.assertIn(ENTRY.strip(), (self.task / "rail.md").read_text())

    # --- inject ---------------------------------------------------------

    def inject(self, **extra: object) -> subprocess.CompletedProcess[str]:
        payload = {"hook_event_name": "SessionStart", "session_id": "thread-123"}
        payload.update(extra)
        return self.command("inject", payload=payload)

    def test_inject_is_silent_for_an_untracked_session(self) -> None:
        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_inject_is_silent_for_a_child_agent(self) -> None:
        self.make_task()

        by_id = self.inject(agent_id="child-1")
        by_type = self.inject(agent_type="explorer")

        self.assertEqual(by_id.returncode, 0, by_id.stderr)
        self.assertEqual(by_id.stdout, "")
        self.assertEqual(by_type.returncode, 0, by_type.stderr)
        self.assertEqual(by_type.stdout, "")

    def test_inject_reports_a_paused_task_in_one_line(self) -> None:
        self.make_task()
        marker = self.task / ".paused"
        marker.touch()

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0],
            f"ChatRail: task thread-123 is paused (since {self.iso(marker)}). "
            "/chatrail:on resumes.",
        )

    def test_inject_frames_the_payload_exactly(self) -> None:
        directory = self.make_task()

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(
            lines[0],
            "=== CHATRAIL ORIENTATION · thread thread-123 · "
            f"compass saved {self.iso(directory / 'compass.md')} ===",
        )
        self.assertIn(TRUTH_SENTENCE, result.stdout)
        self.assertIn("--- COMPASS (whole) ---", result.stdout)
        self.assertIn("--- RAIL (newest tail) ---", result.stdout)
        self.assertIn(
            "=== END CHATRAIL ORIENTATION (latest copy replaces any earlier "
            "copy) ===",
            result.stdout,
        )

    def test_inject_carries_the_whole_compass(self) -> None:
        self.make_task()

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(COMPASS.strip(), result.stdout)

    def test_inject_snaps_the_rail_tail_to_an_entry_boundary(self) -> None:
        directory = self.make_task()
        filler = "x" * 3000
        rail = (
            "# Rail\n\n"
            f"## Entry: old one\n\nBasis: user\n\nMeaning: OLDEST-MARKER {filler}\n\n"
            f"## Entry: middle one\n\nBasis: user\n\nMeaning: MIDDLE-MARKER {filler}\n\n"
            "## Entry: newest one\n\nBasis: user\n\nMeaning: NEWEST-MARKER\n"
        )
        (directory / "rail.md").write_text(rail)

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Entry: newest one", result.stdout)
        self.assertNotIn("OLDEST-MARKER", result.stdout)
        tail = result.stdout[result.stdout.index("## Entry:") :]
        self.assertTrue(tail.startswith("## Entry: "))

    def test_inject_caps_the_payload_and_marks_the_truncation(self) -> None:
        directory = self.make_task()
        big_compass = "# Compass\n\n" + ("compass filler line\n" * 900)
        (directory / "compass.md").write_text(big_compass)
        (directory / "rail.md").write_text(
            "# Rail\n\n## Entry: big\n\nBasis: user\n\nMeaning: "
            + ("rail filler " * 900)
            + "\n"
        )

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLessEqual(len(result.stdout.encode()), 8192)
        self.assertIn(
            "…[truncated — full history: python3 \"", result.stdout
        )
        self.assertIn('" read --thread-id "thread-123"]', result.stdout)

    def inject_bytes(self) -> subprocess.CompletedProcess[bytes]:
        payload = {"hook_event_name": "SessionStart", "session_id": "thread-123"}
        return subprocess.run(
            [sys.executable, str(SCRIPT), "inject"],
            input=json.dumps(payload).encode(),
            capture_output=True,
            cwd=self.work,
            env=self.env,
            check=False,
        )

    def test_inject_never_splits_a_multibyte_compass_char(self) -> None:
        directory = self.make_task()
        (directory / "compass.md").write_text("# Compass\n" + "─" * 3000 + "\n")

        result = self.inject_bytes()

        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout.decode("utf-8")  # must not raise
        self.assertNotIn("�", text)

    def test_inject_never_splits_a_multibyte_char_when_trimming_the_rail(self) -> None:
        directory = self.make_task()
        (directory / "compass.md").write_text(
            "# Compass\n" + ("compass pad line\n" * 300)
        )
        (directory / "rail.md").write_bytes(
            b"# Rail\n\n## Entry: pad\n\nMeaning: " + b"p" * 600 + b"\n\n"
            b"## Entry: uni\n\nMeaning: " + "─".encode() * 1350
        )

        result = self.inject_bytes()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLessEqual(len(result.stdout), 8192)
        text = result.stdout.decode("utf-8")  # must not raise
        self.assertIn("…[truncated", text)

    def test_inject_adds_no_truncation_marker_when_nothing_was_cut(self) -> None:
        self.make_task()

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("…[truncated", result.stdout)

    def test_inject_survives_a_task_with_no_saved_compass(self) -> None:
        self.task.mkdir(parents=True)
        (self.task / "rail.md").write_text("# Rail\n")

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("thread thread-123", result.stdout.splitlines()[0])
        self.assertIn("No ChatRail reading has been saved", result.stdout)

    def test_inject_warns_on_stdout_for_a_malformed_file(self) -> None:
        directory = self.make_task()
        (directory / "compass.md").write_text("# Compassage\n\nbroken\n")

        result = self.inject()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout.strip(),
            "ChatRail: saved task files are malformed; orientation skipped.",
        )
        self.assertNotIn("Compassage", result.stdout)

    # --- alias hop ------------------------------------------------------

    def test_inject_follows_an_alias_to_the_adopted_task(self) -> None:
        self.make_task("older-task")
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").write_text("older-task\n")

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("older-task", result.stdout.splitlines()[0])

    def test_alias_hops_exactly_once_and_never_chains(self) -> None:
        self.make_task("real-task")
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").write_text("middle-alias\n")
        (self.aliases / "middle-alias").write_text("real-task\n")

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_a_symlinked_alias_is_not_followed(self) -> None:
        self.make_task("real-task")
        outside = self.root / "outside-alias"
        outside.write_text("real-task\n")
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").symlink_to(outside)

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_a_malformed_alias_keeps_hooks_silent(self) -> None:
        self.make_task("real-task")
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").write_text("../escape/../real-task\n")

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    # --- inject weld (continue the most recent road) --------------------

    def test_inject_welds_an_unbound_session_onto_the_one_existing_task(self) -> None:
        self.make_task("other-task")

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.aliases / "thread-123").read_text(), "other-task\n")
        self.assertIn("other-task", result.stdout.splitlines()[0])
        self.assertIn("joined the existing road other-task", result.stdout)
        self.assertIn("/chatrail:on <a different name> starts a separate road", result.stdout)
        self.assertNotIn("/chatrail:on other-task starts a separate road", result.stdout)

    def test_inject_weld_picks_the_most_recent_task_by_compass_mtime(self) -> None:
        older = self.make_task("older-task")
        newer = self.make_task("newer-task")
        os.utime(older / "compass.md", (1_700_000_000, 1_700_000_000))
        os.utime(newer / "compass.md", (1_700_000_100, 1_700_000_100))

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.aliases / "thread-123").read_text(), "newer-task\n")
        self.assertIn("newer-task", result.stdout.splitlines()[0])

    def test_inject_weld_is_silent_with_zero_tasks(self) -> None:
        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.aliases.exists())

    def test_inject_weld_does_not_auto_continue_onto_a_paused_task(self) -> None:
        directory = self.make_task("other-task")
        (directory / ".paused").touch()

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.aliases.exists())

    def test_inject_leaves_an_already_bound_session_completely_unchanged(self) -> None:
        self.make_task()

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("joined the existing road", result.stdout)
        self.assertFalse(self.aliases.exists())

    def test_inject_leaves_an_existing_alias_binding_completely_unchanged(self) -> None:
        self.make_task("older-task")
        self.aliases.mkdir(parents=True)
        (self.aliases / "thread-123").write_text("older-task\n")

        result = self.inject()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("joined the existing road", result.stdout)
        self.assertEqual((self.aliases / "thread-123").read_text(), "older-task\n")

    def test_resolve_is_unchanged_by_the_weld_feature(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "chatrail_runtime_resolve", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with mock.patch.dict(
            os.environ,
            {"CHATRAIL_HOME": str(self.home), "CHATRAIL_THREAD_ID": "thread-123"},
        ):
            self.assertEqual(module.resolve(), "thread-123")
            self.assertEqual(module.resolve(explicit="explicit-id"), "explicit-id")
            with self.assertRaises(ValueError):
                module.resolve(explicit="bad id")

    # --- recent ---------------------------------------------------------

    def test_recent_says_so_when_there_are_no_tasks(self) -> None:
        result = self.command("recent")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ChatRail: no tasks.")

    def test_recent_lists_the_newest_five_by_compass_mtime(self) -> None:
        for index in range(7):
            directory = self.make_task(f"task-{index}")
            stamp = 1_700_000_000 + index
            os.utime(directory / "compass.md", (stamp, stamp))

        result = self.command("recent")

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 5)
        self.assertEqual(
            [line.split("\t")[0] for line in lines],
            ["task-6", "task-5", "task-4", "task-3", "task-2"],
        )

    def test_recent_prints_id_time_and_byte_count_per_line(self) -> None:
        directory = self.make_task("task-a")
        size = (directory / "compass.md").stat().st_size

        result = self.command("recent")

        self.assertEqual(result.returncode, 0, result.stderr)
        fields = result.stdout.strip().split("\t")
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0], "task-a")
        self.assertEqual(fields[1], self.iso(directory / "compass.md"))
        self.assertEqual(fields[2], f"{size}B")

    def test_recent_skips_unsafe_names_and_symlinked_task_dirs(self) -> None:
        self.make_task("task-a")
        outside = self.root / "outside-task"
        outside.mkdir()
        (self.tasks / "bad name").mkdir()
        (self.tasks / "linked-task").symlink_to(outside, target_is_directory=True)

        result = self.command("recent")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("bad name", result.stdout)
        self.assertNotIn("linked-task", result.stdout)
        self.assertIn("task-a", result.stdout)

    # --- adopt ----------------------------------------------------------

    def test_adopt_writes_an_alias_file_for_the_current_session(self) -> None:
        self.make_task("older-task")

        result = self.command("adopt", "older-task", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "ChatRail adopted: thread-123 -> older-task"
        )
        self.assertEqual((self.aliases / "thread-123").read_text(), "older-task\n")

    def test_adopt_never_creates_and_lists_recent_tasks_on_a_miss(self) -> None:
        self.make_task("older-task")

        result = self.command("adopt", "ghost", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 1)
        self.assertIn("older-task", result.stderr)
        self.assertFalse((self.tasks / "ghost").exists())
        self.assertFalse(self.aliases.exists())

    def test_adopt_rejects_unsafe_ids(self) -> None:
        self.make_task("older-task")

        for current, target in (
            ("../escape", "older-task"),
            ("thread-123", "../older-task"),
        ):
            with self.subTest(current=current, target=target):
                result = self.command("adopt", target, "--thread-id", current)

                self.assertNotEqual(result.returncode, 0)
                # Not an unknown-subcommand error: adopt must exist and reject
                # the id itself, or this test would pass before adopt is built.
                self.assertNotIn("invalid choice", result.stderr)
                self.assertFalse(self.aliases.exists() and any(self.aliases.iterdir()))

    # --- clean ----------------------------------------------------------

    def test_clean_thread_id_removes_the_task_lock_and_aliases(self) -> None:
        self.make_task("thread-123")
        (self.tasks / ".thread-123.lock").write_text("")
        self.aliases.mkdir(parents=True)
        (self.aliases / "session-x").write_text("thread-123\n")
        (self.aliases / "session-y").write_text("other-task\n")

        result = self.command("clean", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "ChatRail cleaned: task thread-123 and 1 alias(es)"
        )
        self.assertFalse(self.task.exists())
        self.assertFalse((self.tasks / ".thread-123.lock").exists())
        self.assertFalse((self.aliases / "session-x").exists())
        self.assertTrue((self.aliases / "session-y").exists())

    def test_clean_missing_thread_id_fails(self) -> None:
        result = self.command("clean", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 1)
        self.assertNotEqual(result.stderr.strip(), "")

    def test_clean_aliases_drops_only_the_stale_ones(self) -> None:
        self.make_task("live-task")
        self.aliases.mkdir(parents=True)
        (self.aliases / "session-live").write_text("live-task\n")
        (self.aliases / "session-stale").write_text("gone-task\n")

        result = self.command("clean", "--aliases")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1", result.stdout)
        self.assertTrue((self.aliases / "session-live").exists())
        self.assertFalse((self.aliases / "session-stale").exists())

    def make_legacy(self) -> Path:
        legacy = self.root / "legacy-codex"
        for name in ("old-1", "old-2", "old-3"):
            (legacy / "chatrail" / "tasks" / name).mkdir(parents=True)
        self.env["CODEX_HOME"] = str(legacy)
        return legacy

    def test_clean_legacy_counts_and_removes_the_old_tree(self) -> None:
        legacy = self.make_legacy()

        result = self.command("clean", "--legacy", "--confirm")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "ChatRail cleaned legacy: 3 task dirs removed from", result.stdout
        )
        self.assertFalse((legacy / "chatrail").exists())

    def test_clean_legacy_without_confirm_previews_and_deletes_nothing(self) -> None:
        legacy = self.make_legacy()

        result = self.command("clean", "--legacy")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            f"ChatRail legacy target: {legacy / 'chatrail'} (3 task dirs). "
            "Re-run with --confirm to delete.",
        )
        self.assertTrue((legacy / "chatrail" / "tasks" / "old-1").is_dir())

    def test_clean_refuses_an_empty_home_env_var(self) -> None:
        # HOME is faked so a buggy empty-string fallback can never reach the
        # real ~/.codex or ~/.chatrail.
        fake_home = self.root / "fake-home"
        (fake_home / ".codex" / "chatrail" / "tasks" / "keep").mkdir(parents=True)
        for variable in ("CODEX_HOME", "CHATRAIL_HOME"):
            with self.subTest(variable=variable):
                self.env["HOME"] = str(fake_home)
                self.env["CODEX_HOME"] = str(self.root / "legacy-unused")
                self.env["CHATRAIL_HOME"] = str(self.home)
                self.env[variable] = ""

                result = self.command("clean", "--legacy", "--confirm")

                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"ChatRail: {variable} is set but empty — refusing",
                    result.stderr,
                )
                self.assertTrue(
                    (fake_home / ".codex" / "chatrail" / "tasks" / "keep").is_dir()
                )

    def test_clean_legacy_with_nothing_to_clean_is_quietly_fine(self) -> None:
        legacy = self.root / "legacy-empty"
        legacy.mkdir()
        self.env["CODEX_HOME"] = str(legacy)

        result = self.command("clean", "--legacy")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ChatRail: no legacy state at", result.stdout)

    def test_clean_without_a_target_flag_is_an_argparse_error(self) -> None:
        self.make_task()

        result = self.command("clean")

        self.assertEqual(result.returncode, 2)
        # The error must be the missing target flag, not an unknown subcommand,
        # or this test would pass before clean is built.
        self.assertNotIn("invalid choice", result.stderr)
        self.assertIn("--thread-id", result.stderr)
        self.assertIn("--aliases", result.stderr)
        self.assertIn("--legacy", result.stderr)
        self.assertTrue(self.task.exists())

    # --- stop -----------------------------------------------------------

    def test_stop_wakes_only_the_first_root_stop(self) -> None:
        base = {"hook_event_name": "Stop", "session_id": "thread-123"}

        untracked = self.command("stop", payload=base)
        self.assertEqual(untracked.stdout, "")

        self.task.mkdir(parents=True)
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

    def test_stop_reason_carries_the_drift_sentence_verbatim(self) -> None:
        self.task.mkdir(parents=True)

        result = self.command(
            "stop", payload={"hook_event_name": "Stop", "session_id": "thread-123"}
        )

        reason = json.loads(result.stdout)["reason"]
        self.assertIn(DRIFT_SENTENCE, reason)

    # --- archive --------------------------------------------------------

    @property
    def archives(self) -> Path:
        return self.home / "archive"

    def archive_files(self) -> list[Path]:
        return sorted(self.archives.iterdir()) if self.archives.is_dir() else []

    def test_archive_writes_one_file_with_both_saved_bytes(self) -> None:
        directory = self.make_task()
        rail = f"# Rail\n\n{ENTRY}"
        (directory / "rail.md").write_text(rail)

        result = self.command("archive", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        files = self.archive_files()
        self.assertEqual(len(files), 1)
        archived = files[0]
        self.assertRegex(
            archived.name, r"^thread-123-\d{8}T\d{6}Z\.md$"
        )
        text = archived.read_text()
        first, blank = text.splitlines()[0], text.splitlines()[1]
        self.assertRegex(
            first,
            r"^# ChatRail archive · task thread-123 · archived "
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        )
        self.assertEqual(blank, "")
        self.assertIn(rail, text)
        self.assertIn(COMPASS, text)
        self.assertEqual(
            result.stdout.strip(),
            f"ChatRail archived: {archived.resolve()} — "
            "task thread-123 reset to a fresh road.",
        )

    def test_archive_resets_the_live_task_without_pausing_it(self) -> None:
        directory = self.make_task()
        (directory / "rail.md").write_text(f"# Rail\n\n{ENTRY}")

        result = self.command("archive", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(directory.is_dir())
        self.assertEqual((directory / "rail.md").read_text(), "# Rail\n")
        self.assertEqual(
            (directory / "compass.md").read_bytes(),
            b"# Compass\n\nNo ChatRail reading has been saved for this task yet.\n",
        )
        self.assertFalse((directory / ".paused").exists())

    def test_archive_without_a_task_fails_and_creates_nothing(self) -> None:
        result = self.command("archive", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("invalid choice", result.stderr)
        self.assertNotEqual(result.stderr.strip(), "")
        self.assertFalse(self.task.exists())
        self.assertFalse(self.archives.exists())

    def test_two_archives_in_the_same_second_never_overwrite(self) -> None:
        self.make_task()

        first = self.command("archive", "--thread-id", "thread-123")
        second = self.command("archive", "--thread-id", "thread-123")

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(len(self.archive_files()), 2)
        self.assertNotEqual(
            first.stdout.strip(), second.stdout.strip()
        )

    def test_archive_touches_no_other_task_and_no_alias(self) -> None:
        self.make_task()
        other = self.make_task("other-task")
        (other / "rail.md").write_text(f"# Rail\n\n{ENTRY}")
        self.aliases.mkdir(parents=True, exist_ok=True)
        (self.aliases / "session-x").write_text("other-task\n")

        result = self.command("archive", "--thread-id", "thread-123")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((other / "rail.md").read_text(), f"# Rail\n\n{ENTRY}")
        self.assertEqual((other / "compass.md").read_text(), COMPASS)
        self.assertEqual((self.aliases / "session-x").read_text(), "other-task\n")

    def test_save_after_archive_appends_onto_the_fresh_seed(self) -> None:
        self.make_task()
        archived = self.command("archive", "--thread-id", "thread-123")
        self.assertEqual(archived.returncode, 0, archived.stderr)
        entry, compass = self.proposals()

        result = self.command("save", "--append", str(entry), "--compass", str(compass))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.task / "rail.md").read_text(), f"# Rail\n\n{ENTRY}")
        self.assertEqual((self.task / "compass.md").read_text(), COMPASS)

    # --- runtime shape --------------------------------------------------

    def test_runtime_is_small_and_has_no_semantic_engine(self) -> None:
        source = SCRIPT.read_text()
        nonblank = sum(bool(line.strip()) for line in source.splitlines())

        self.assertLessEqual(nonblank, 330)
        self.assertNotIn("sqlite", source.lower())
        self.assertNotIn("On course", source)
        self.assertNotIn("Drifting", source)
        self.assertNotIn("--rail", source)


if __name__ == "__main__":
    unittest.main()
