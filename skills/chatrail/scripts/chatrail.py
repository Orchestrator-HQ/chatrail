#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
EMPTY_RAIL = b"# Rail\n"
EMPTY_COMPASS = b"""# Compass

No ChatRail reading has been saved for this task yet.
"""


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def safe_thread_id(value: str | None) -> str:
    value = value or os.environ.get("CODEX_THREAD_ID")
    if not value or not SAFE_ID.fullmatch(value):
        raise ValueError("invalid thread id")
    return value


def task_dir(thread_id: str) -> Path:
    return codex_home() / "chatrail" / "tasks" / safe_thread_id(thread_id)


def read_regular(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError(f"{path.name} must be a regular file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            return stream.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_compass(path: Path) -> bytes:
    data = read_regular(path)
    if data.splitlines()[:1] != [b"# Compass"]:
        raise ValueError(f"{path.name} has the wrong header")
    return data


def read_entry(path: Path) -> bytes:
    data = read_regular(path)
    first = data.splitlines()[:1]
    if not first or not first[0].startswith(b"## Entry: ") or not first[0][10:].strip():
        raise ValueError(f"{path.name} has the wrong header")
    return data


def read_saved(path: Path, header: bytes) -> bytes | None:
    try:
        data = read_regular(path)
    except FileNotFoundError:
        return None
    if data.splitlines()[:1] != [header]:
        raise ValueError(f"{path.name} has the wrong header")
    return data


def atomic_write(path: Path, data: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def next_rail(old: bytes, entry: bytes) -> tuple[bytes, str]:
    entry = entry.rstrip(b"\n")
    if old.rstrip(b"\n").endswith(entry):
        return old, "unchanged"
    gap = b"\n" if old.endswith(b"\n") else b"\n\n"
    return old + gap + entry + b"\n", "appended"


def save_files(
    thread_id: str,
    compass_path: Path,
    entry_path: Path | None = None,
) -> int:
    try:
        compass = read_compass(compass_path)
        entry = read_entry(entry_path) if entry_path is not None else None
        directory = task_dir(thread_id)
    except (OSError, ValueError) as error:
        print(f"ChatRail not saved: {error}", file=sys.stderr)
        return 1

    compass_written = False
    try:
        directory.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(directory.parent / f".{directory.name}.lock", flags, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if directory.is_symlink():
                raise OSError("task folder must not be a symlink")
            directory.mkdir(exist_ok=True)
            rail_path = directory / "rail.md"
            compass_target = directory / "compass.md"
            old_saved = read_saved(rail_path, b"# Rail")
            read_saved(compass_target, b"# Compass")
            old = old_saved if old_saved is not None else EMPTY_RAIL
            new, rail_result = (
                next_rail(old, entry) if entry is not None else (old, "unchanged")
            )
            atomic_write(compass_target, compass)
            compass_written = True
            if old_saved is None or new != old:
                atomic_write(rail_path, new)
    except (OSError, ValueError) as error:
        if compass_written:
            print(
                "ChatRail partial save: Compass was saved. Rail is still old. "
                "Retry the same save command.",
                file=sys.stderr,
            )
        else:
            print(f"ChatRail not saved: {error}", file=sys.stderr)
        return 2
    print(f"ChatRail saved: rail={rail_result} compass=replaced")
    return 0


def read_files(thread_id: str) -> int:
    try:
        directory = task_dir(thread_id)
        if directory.is_symlink():
            raise OSError("task folder must not be a symlink")
        rail = read_saved(directory / "rail.md", b"# Rail") or EMPTY_RAIL
        compass = read_saved(directory / "compass.md", b"# Compass") or EMPTY_COMPASS
    except (OSError, ValueError) as error:
        print(f"ChatRail not read: {error}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(b"=== RAIL ===\n" + rail + b"\n=== COMPASS ===\n" + compass)
    return 0


def stop_review() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if payload.get("agent_id") or payload.get("agent_type"):
            return 0
        if payload.get("stop_hook_active"):
            return 0
        thread_id = safe_thread_id(payload.get("session_id"))
    except (AttributeError, json.JSONDecodeError, ValueError) as error:
        print(f"ChatRail warning: {error}", file=sys.stderr)
        return 0
    script = Path(__file__).resolve()
    reason = (
        "Run one ChatRail AI review now. AI must decide all meaning. "
        f'First run: python3 "{script}" read --thread-id "{thread_id}". '
        "Only clear user words may add or change the goal. "
        "Choose NO_SAVE only if goal, proof, direction, progress, blocker, "
        "next move, and useful unknowns did not change. If the current reading "
        "changed but lasting Rail meaning did not, write Compass only. If "
        "lasting Rail meaning changed, write Compass and one Rail entry. "
        "Save proposals with the script. "
        "Do not edit the saved Rail or Compass."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("read")
    read.add_argument("--thread-id")
    save = commands.add_parser("save")
    save.add_argument("--thread-id")
    save.add_argument("--compass", type=Path, required=True)
    save.add_argument("--append", type=Path)
    commands.add_parser("stop")
    args = parser.parse_args()
    if args.command == "read":
        return read_files(args.thread_id)
    if args.command == "save":
        return save_files(args.thread_id, args.compass, args.append)
    return stop_review()


if __name__ == "__main__":
    raise SystemExit(main())
