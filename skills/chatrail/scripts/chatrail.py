#!/usr/bin/env python3
"""Small, Git-independent continuity rail for Codex tasks."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

FILES = ("conversation.rail.yaml", "working.compass.yaml", "orientation.events.jsonl")
TARGETS = {"rail": FILES[0], "compass": FILES[1]}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def task_key(session_id: str) -> str:
    return hashlib.sha256(("codex-chatrail-v1\0" + session_id).encode()).hexdigest()


def roots() -> tuple[Path, Path]:
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "chatrail"
    tasks, receipts = home / "tasks", home / "receipts"
    for path in (home, tasks, receipts):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path, 0o700)
    return tasks, receipts


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a mapping")
    return value


def atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def append_event(path: Path, event: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, 0o600)


def defaults() -> dict[str, dict]:
    return {
        "rail": {"schema": 1, "north": "Name the main outcome.", "next": None,
                 "route": [], "open": [], "parked": []},
        "compass": {"schema": 1, "bearings": {
            "north": {"coordinate": [0, 100], "definition": "Direct movement toward Rail North."},
            "east": {"coordinate": [100, 0], "definition": "Useful side work that delays Rail North."},
            "south": {"coordinate": [0, -100], "definition": "Movement against Rail North or false progress."},
            "west": {"coordinate": [-100, 0], "definition": "Costly or weak-payoff drift."}},
            "heading": {"coordinate": [0, 100], "context": "A new task is starting."},
            "drift": "No drift is known yet.", "return_path": "Name the first move toward North."},
    }


def validate_state(target: str, value: dict) -> None:
    expected = ({"schema", "north", "next", "route", "open", "parked"} if target == "rail"
                else {"schema", "bearings", "heading", "drift", "return_path"})
    if set(value) != expected or value.get("schema") != 1:
        raise ValueError(f"invalid {target} fields")
    if target == "rail":
        if not isinstance(value["north"], str) or any(not isinstance(value[k], list) for k in ("route", "open", "parked")):
            raise ValueError("invalid Rail values")
        items = ([value["next"]] if value["next"] is not None else []) + value["route"] + value["open"] + value["parked"]
        if any(not isinstance(i, dict) or set(i) != {"id", "summary"} or not all(isinstance(i[k], str) and i[k].strip() for k in i) for i in items):
            raise ValueError("Rail items require non-empty id and summary")
    else:
        if not isinstance(value["bearings"], dict) or set(value["bearings"]) != {"north", "east", "south", "west"}:
            raise ValueError("invalid Compass bearings")
        if any(value["bearings"][k].get("coordinate") != c for k, c in {"north":[0,100],"east":[100,0],"south":[0,-100],"west":[-100,0]}.items()):
            raise ValueError("Compass bearing coordinates are fixed")
        heading = value["heading"].get("coordinate")
        if not isinstance(heading, list) or len(heading) != 2 or any(not isinstance(n, int) or n % 10 for n in heading) or sum(map(abs, heading)) != 100:
            raise ValueError("heading must be two multiples of ten totaling 100")


def initialize(bundle: Path) -> None:
    bundle.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(bundle, 0o700)
    states = defaults()
    for target, value in states.items():
        atomic(bundle / TARGETS[target], value)
    event = {"version": 1, "event_id": str(uuid.uuid4()), "review_id": "genesis",
             "ts": now(), "reason": "Create ChatRail", "transitions": []}
    for target in ("compass", "rail"):
        event["transitions"].append({"target": target, "before": None,
            "after": states[target], "before_sha256": None, "after_sha256": digest(states[target])})
    append_event(bundle / FILES[2], event)


def discover(cwd: Path) -> tuple[Path, str]:
    home = Path.home().resolve()
    current = cwd.resolve()
    while current != home and current != current.parent:
        candidate = current / ".chatrail"
        if candidate.exists():
            if all((candidate / name).is_file() for name in FILES):
                return candidate.resolve(), "project"
            raise ValueError(f"incomplete ChatRail bundle at {candidate}", candidate)
        current = current.parent
    tasks, _ = roots()
    raise LookupError(tasks)


def validate_bundle(bundle: Path, recover: bool = True) -> dict[str, str]:
    states = {target: load(bundle / name) for target, name in TARGETS.items()}
    for target, value in states.items():
        validate_state(target, value)
    lines = [json.loads(line) for line in (bundle / FILES[2]).read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        raise ValueError("orientation event history is empty")
    expected: dict[str, str | None] = {"rail": None, "compass": None}
    for event in lines:
        for change in event.get("transitions", []):
            target = change.get("target")
            if target not in TARGETS or change.get("before_sha256") != expected[target]:
                raise ValueError("orientation event chain is broken")
            if digest(change.get("after")) != change.get("after_sha256"):
                raise ValueError("orientation event hash is broken")
            expected[target] = change["after_sha256"]
    for target, value in states.items():
        live = digest(value)
        if live != expected[target]:
            last = next((c for c in reversed(lines[-1].get("transitions", [])) if c.get("target") == target), None)
            if recover and last and live == last.get("before_sha256"):
                atomic(bundle / TARGETS[target], last["after"])
                states[target] = last["after"]
            else:
                raise ValueError(f"{target} does not match its event history")
    return {target: digest(value) for target, value in states.items()}


def receipt_path(session_id: str) -> Path:
    _, receipts = roots()
    return receipts / f"{task_key(session_id)}.json"


def pin(session_id: str, cwd: Path) -> tuple[Path, Path, dict]:
    path = receipt_path(session_id)
    if path.exists():
        receipt = load(path)
        return Path(receipt["bundle"]["path"]), path, receipt
    try:
        bundle, kind = discover(cwd)
    except LookupError as missing:
        bundle, kind = Path(missing.args[0]) / task_key(session_id), "local"
        initialize(bundle)
    except ValueError as broken:
        bundle, kind = Path(broken.args[1]), "project"
    receipt = {"version": 1, "task_key": task_key(session_id),
               "bundle": {"path": str(bundle), "kind": kind}, "review": None,
               "warning_fingerprint": None}
    atomic(path, receipt)
    return bundle, path, receipt


def warning(receipt_file: Path | None, receipt: dict | None, exc: Exception) -> None:
    fingerprint = hashlib.sha256(str(exc).encode()).hexdigest()[:12]
    if receipt_file and receipt and receipt.get("warning_fingerprint") != fingerprint:
        receipt["warning_fingerprint"] = fingerprint
        try:
            atomic(receipt_file, receipt)
        except Exception:
            pass
        print(f"ChatRail paused its own writes: {exc}", file=sys.stderr)


def reconcile(args: argparse.Namespace) -> int:
    path, receipt = receipt_path(args.session_id), None
    try:
        receipt = load(path)
        review = receipt.get("review") or {}
        if review.get("id") != args.review_id or review.get("status") != "pending":
            raise ValueError("review is missing, stale, or already complete")
        bundle = Path(receipt["bundle"]["path"])
        locks = path.parent.parent / "locks"; locks.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = locks / f"{hashlib.sha256(str(bundle).encode()).hexdigest()}.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            hashes = validate_bundle(bundle)
            if hashes != review.get("expected"):
                raise ValueError("ChatRail changed after this review began; review current state again")
            patches = {"compass": json.loads(args.compass) if args.compass else None,
                       "rail": json.loads(args.rail) if args.rail else None}
            transitions = []
            for target in ("compass", "rail"):
                if patches[target] is None:
                    continue
                old = load(bundle / TARGETS[target])
                if not isinstance(patches[target], dict) or not set(patches[target]) <= set(old):
                    raise ValueError(f"invalid {target} patch")
                new = {**old, **patches[target]}
                validate_state(target, new)
                if new != old:
                    transitions.append({"target": target, "before": old, "after": new,
                        "before_sha256": digest(old), "after_sha256": digest(new)})
            if transitions:
                event = {"version": 1, "event_id": str(uuid.uuid4()), "review_id": args.review_id,
                         "ts": now(), "reason": args.reason, "transitions": transitions}
                append_event(bundle / FILES[2], event)
                for change in transitions:
                    atomic(bundle / TARGETS[change["target"]], change["after"])
            review.update({"status": "complete", "completed_at": now()})
            receipt["review"] = review
            atomic(path, receipt)
        return 0
    except Exception as exc:
        warning(path, receipt, exc)
        return 1


def hook() -> int:
    receipt_file = receipt = None
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if payload.get("agent_id") or payload.get("agent_type"):
            return 0
        session_id = payload.get("session_id") or payload.get("sessionId")
        event = (payload.get("hook_event_name") or "").lower()
        if not isinstance(session_id, str) or not session_id.strip() or event not in {"userpromptsubmit", "stop"}:
            return 0
        bundle, receipt_file, receipt = pin(session_id, Path(payload.get("cwd") or Path.cwd()))
        hashes = validate_bundle(bundle)
        if event == "stop":
            review = receipt.get("review") or {}
            if review.get("status") == "pending" and not review.get("stop_blocked"):
                review["stop_blocked"] = True
                receipt["review"] = review
                atomic(receipt_file, receipt)
                print(json.dumps({"decision": "block", "reason": "Finish the pending ChatRail review once, then stop normally."}))
            return 0
        review_id = str(uuid.uuid4())
        receipt["review"] = {"id": review_id, "status": "pending", "expected": hashes,
                             "stop_blocked": False, "turn_id": payload.get("turn_id") or payload.get("turnId")}
        atomic(receipt_file, receipt)
        command = f'python3 "{Path(__file__).resolve()}" reconcile --session-id "{session_id}" --review-id "{review_id}" --reason "<why or no-change>"'
        context = ("At turn end, reconcile ChatRail once. Patch Compass only if present reality changed; "
                   "then Rail only if the agreed road changed. Never edit its files directly. "
                   f"Run `{command}` and add --compass/--rail JSON patches only when meaning changed.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}))
        return 0
    except Exception as exc:
        warning(receipt_file, receipt, exc)
        return 0


def main() -> int:
    if len(sys.argv) == 1:
        return hook()
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("reconcile")
    rec.add_argument("--session-id", required=True); rec.add_argument("--review-id", required=True)
    rec.add_argument("--reason", required=True); rec.add_argument("--compass"); rec.add_argument("--rail")
    check = sub.add_parser("validate"); check.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "reconcile":
        return reconcile(args)
    try:
        print(json.dumps({"valid": True, "hashes": validate_bundle(args.bundle)}, indent=2)); return 0
    except Exception as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
