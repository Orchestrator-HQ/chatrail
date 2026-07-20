from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "chatrail.py"
SPEC = importlib.util.spec_from_file_location("chatrail", SCRIPT)
assert SPEC and SPEC.loader
chatrail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chatrail)


class ChatRailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "codex"
        self.cwd = self.root / "plain"
        self.cwd.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def hook(self, payload: dict, expected: int = 0) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "CODEX_HOME": str(self.home)}
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload),
                                text=True, capture_output=True, env=env, cwd=self.cwd)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def prompt(self, session: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return self.hook({"hook_event_name": "UserPromptSubmit", "session_id": session,
                          "turn_id": "turn-1", "cwd": str(cwd or self.cwd)})

    def receipt(self, session: str) -> dict:
        return json.loads((self.home / "chatrail" / "receipts" / f"{chatrail.task_key(session)}.json").read_text())

    def test_non_git_tasks_get_separate_local_bundles_and_resume(self) -> None:
        for session in ("one", "two"):
            output = self.prompt(session)
            self.assertIn("additionalContext", output.stdout)
        one, two = self.receipt("one"), self.receipt("two")
        self.assertNotEqual(one["bundle"]["path"], two["bundle"]["path"])
        self.assertEqual(one["bundle"]["kind"], "local")
        first_path = one["bundle"]["path"]
        self.assertEqual(
            sorted(path.name for path in Path(first_path).iterdir()),
            ["conversation.rail.yaml", "orientation.events.jsonl", "working.compass.yaml"],
        )
        moved = self.root / "moved"; moved.mkdir()
        self.prompt("one", moved)
        self.assertEqual(self.receipt("one")["bundle"]["path"], first_path)
        chatrail.validate_bundle(Path(first_path))

    def test_project_bundle_is_discovered_without_git(self) -> None:
        project = self.root / "project"; nested = project / "a" / "b"; nested.mkdir(parents=True)
        chatrail.initialize(project / ".chatrail")
        self.prompt("project-session", nested)
        receipt = self.receipt("project-session")
        self.assertEqual(receipt["bundle"]["kind"], "project")
        self.assertEqual(Path(receipt["bundle"]["path"]), (project / ".chatrail").resolve())
        source = SCRIPT.read_text().lower()
        self.assertNotIn("git rev-parse", source)
        self.assertNotIn("import subprocess", source)

    def test_malformed_and_child_payloads_are_safe_noops(self) -> None:
        cases = [{}, {"hook_event_name": "UserPromptSubmit"},
                 {"hook_event_name": "UserPromptSubmit", "session_id": "child", "agent_id": "a"}]
        for payload in cases:
            with self.subTest(payload=payload):
                self.hook(payload)
        self.assertFalse((self.home / "chatrail").exists())

    def test_deleted_cwd_and_unavailable_storage_cannot_block_messages(self) -> None:
        self.prompt("survivor")
        deleted = self.cwd
        shutil.rmtree(deleted)
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "survivor",
                   "turn_id": "turn-2", "cwd": str(deleted)}
        env = {**os.environ, "CODEX_HOME": str(self.home)}
        resumed = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload),
                                 text=True, capture_output=True, env=env, cwd=self.root)
        self.assertEqual(resumed.returncode, 0)
        self.assertIn("additionalContext", resumed.stdout)
        unavailable = self.root / "not-a-directory"; unavailable.write_text("blocked")
        env["CODEX_HOME"] = str(unavailable)
        fresh = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({**payload, "session_id": "new"}),
                               text=True, capture_output=True, env=env, cwd=self.root)
        self.assertEqual(fresh.returncode, 0)
        self.assertNotIn('"decision":"block"', fresh.stdout.replace(" ", ""))

    def test_stop_blocks_once_then_fails_open(self) -> None:
        self.prompt("stopper")
        payload = {"hook_event_name": "Stop", "session_id": "stopper", "cwd": str(self.cwd)}
        first, second = self.hook(payload), self.hook(payload)
        self.assertEqual(json.loads(first.stdout)["decision"], "block")
        self.assertEqual(second.stdout, "")

    def test_reconcile_writes_full_before_after_event_and_completes_review(self) -> None:
        self.prompt("change")
        receipt = self.receipt("change")
        bundle = Path(receipt["bundle"]["path"])
        before = json.loads((bundle / "working.compass.yaml").read_text())
        patch = {"heading": {"coordinate": [20, 80], "context": "Useful side work is underway."},
                 "drift": "Twenty percent east.", "return_path": "Finish the bounded refactor."}
        env = {**os.environ, "CODEX_HOME": str(self.home)}
        result = subprocess.run([sys.executable, str(SCRIPT), "reconcile", "--session-id", "change",
            "--review-id", receipt["review"]["id"], "--reason", "Direction changed",
            "--compass", json.dumps(patch)], text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        event = json.loads((bundle / "orientation.events.jsonl").read_text().splitlines()[-1])
        change = event["transitions"][0]
        self.assertEqual(change["before"], before)
        self.assertEqual(change["after"]["drift"], "Twenty percent east.")
        self.assertEqual(self.receipt("change")["review"]["status"], "complete")
        chatrail.validate_bundle(bundle)

    def test_no_change_review_does_not_append_event(self) -> None:
        self.prompt("quiet")
        receipt = self.receipt("quiet"); bundle = Path(receipt["bundle"]["path"])
        events = (bundle / "orientation.events.jsonl").read_bytes()
        env = {**os.environ, "CODEX_HOME": str(self.home)}
        result = subprocess.run([sys.executable, str(SCRIPT), "reconcile", "--session-id", "quiet",
            "--review-id", receipt["review"]["id"], "--reason", "No meaning changed"], env=env)
        self.assertEqual(result.returncode, 0)
        self.assertEqual((bundle / "orientation.events.jsonl").read_bytes(), events)

    def test_appended_event_recovers_an_interrupted_write(self) -> None:
        self.prompt("crash")
        bundle = Path(self.receipt("crash")["bundle"]["path"])
        old = json.loads((bundle / "conversation.rail.yaml").read_text())
        new = {**old, "north": "Recovered North"}
        event = {"version": 1, "event_id": "crash", "review_id": "crash", "ts": chatrail.now(),
                 "reason": "crash test", "transitions": [{"target": "rail", "before": old, "after": new,
                 "before_sha256": chatrail.digest(old), "after_sha256": chatrail.digest(new)}]}
        chatrail.append_event(bundle / "orientation.events.jsonl", event)
        chatrail.validate_bundle(bundle)
        self.assertEqual(json.loads((bundle / "conversation.rail.yaml").read_text())["north"], "Recovered North")

    def test_stale_concurrent_review_cannot_clobber_newer_state(self) -> None:
        project = self.root / "shared"; project.mkdir(); bundle = project / ".chatrail"
        chatrail.initialize(bundle)
        self.prompt("first", project); self.prompt("second", project)
        first, second = self.receipt("first"), self.receipt("second")
        env = {**os.environ, "CODEX_HOME": str(self.home)}
        changed = subprocess.run([sys.executable, str(SCRIPT), "reconcile", "--session-id", "first",
            "--review-id", first["review"]["id"], "--reason", "New North",
            "--rail", json.dumps({"north": "Newer shared North"})], env=env)
        stale = subprocess.run([sys.executable, str(SCRIPT), "reconcile", "--session-id", "second",
            "--review-id", second["review"]["id"], "--reason", "Stale no-change"], env=env)
        self.assertEqual(changed.returncode, 0)
        self.assertEqual(stale.returncode, 1)
        self.assertEqual(json.loads((bundle / "conversation.rail.yaml").read_text())["north"], "Newer shared North")

    def test_direct_tampering_freezes_writes_but_prompt_fails_open(self) -> None:
        self.prompt("tamper")
        receipt = self.receipt("tamper"); bundle = Path(receipt["bundle"]["path"])
        rail = json.loads((bundle / "conversation.rail.yaml").read_text())
        rail["north"] = "Unjournaled rewrite"
        (bundle / "conversation.rail.yaml").write_text(json.dumps(rail))
        result = self.prompt("tamper")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("paused its own writes", result.stderr)

    def test_two_target_crash_recovers_only_missing_live_write(self) -> None:
        self.prompt("two-target")
        bundle = Path(self.receipt("two-target")["bundle"]["path"])
        old_compass = json.loads((bundle / "working.compass.yaml").read_text())
        old_rail = json.loads((bundle / "conversation.rail.yaml").read_text())
        new_compass = {**old_compass, "drift": "Recovered mixed transition"}
        new_rail = {**old_rail, "north": "Recovered mixed North"}
        transitions = []
        for target, old, new in (("compass", old_compass, new_compass), ("rail", old_rail, new_rail)):
            transitions.append({"target": target, "before": old, "after": new,
                "before_sha256": chatrail.digest(old), "after_sha256": chatrail.digest(new)})
        chatrail.append_event(bundle / "orientation.events.jsonl", {"version": 1, "event_id": "mixed",
            "review_id": "mixed", "ts": chatrail.now(), "reason": "mixed crash", "transitions": transitions})
        chatrail.atomic(bundle / "working.compass.yaml", new_compass)
        chatrail.validate_bundle(bundle)
        self.assertEqual(json.loads((bundle / "working.compass.yaml").read_text())["drift"], "Recovered mixed transition")
        self.assertEqual(json.loads((bundle / "conversation.rail.yaml").read_text())["north"], "Recovered mixed North")

    def test_corrupt_and_partial_bundles_warn_once_but_never_block(self) -> None:
        project = self.root / "broken"; project.mkdir(); bundle = project / ".chatrail"; bundle.mkdir()
        (bundle / "conversation.rail.yaml").write_text("{}")
        first = self.prompt("broken", project)
        second = self.prompt("broken", project)
        self.assertIn("paused its own writes", first.stderr)
        self.assertEqual(second.stderr, "")
        self.assertEqual(first.stdout, second.stdout, "fail-open hooks should return no blocking output")


if __name__ == "__main__":
    unittest.main()
