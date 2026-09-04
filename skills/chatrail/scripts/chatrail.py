#!/usr/bin/env python3
from __future__ import annotations

import argparse, datetime as dt, fcntl, json, os, re, shutil, stat, sys, tempfile
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
HEADING_LINE = re.compile(r"([NESW]): (10|[0-9])  # (\S.*)")
EMPTY_RAIL = b"# Rail\n"
EMPTY_COMPASS = b"# Compass\n\nNo ChatRail reading has been saved for this task yet.\n"
TRUTH = "This is ChatRail's LAST saved reading, not live truth. Truth order: the user's latest words beat fresh evidence you gather; fresh evidence beats these files. Reconcile this reading against the conversation before acting on it."
DRIFT = "If the work no longer points at the latest user-approved direction, say one plain line in chat before the turn ends, naming both the work underway and the approved direction and offering refocus or approval of the new direction — stay silent only if the same divergence was already said and is unanswered, or the user's own words ordered the detour."


def _home(variable: str, default: str) -> Path:
    configured = os.environ.get(variable)
    return Path(configured).expanduser() if configured else Path.home() / default


def home() -> Path: return _home("CHATRAIL_HOME", ".chatrail")


def valid_id(value: str | None) -> bool:
    return bool(value) and len(value.encode()) <= 64 and bool(SAFE_ID.fullmatch(value))


def task_dir(thread_id: str) -> Path: return home() / "tasks" / thread_id


def ts(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def follow_alias(thread_id: str) -> str:
    path = home() / "aliases" / thread_id
    try: data = read_regular(path)
    except FileNotFoundError: return thread_id
    except OSError as error: raise ValueError(f"alias file is unusable: {path}") from error
    target = data.decode("utf-8", "replace").rstrip("\n")
    if "\n" in target or not valid_id(target): raise ValueError(f"alias file is malformed: {path}")
    return target


def resolve(explicit: str | None = None, session: str | None = None, hop: bool = True) -> str:
    for source in (explicit, os.environ.get("CHATRAIL_THREAD_ID"), os.environ.get("CODEX_THREAD_ID"), session):
        if not source: continue
        if not valid_id(source): raise ValueError("invalid thread id")
        return source if source is explicit or not hop else follow_alias(source)
    raise ValueError("no thread id")


def read_regular(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode): raise OSError(f"{path.name} must be a regular file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            return stream.read()
    finally:
        if descriptor >= 0: os.close(descriptor)


def read_checked(path: Path, header: bytes) -> bytes:
    data = read_regular(path)
    if data.splitlines()[:1] != [header]: raise ValueError(f"{path.name} has the wrong header")
    return data


def read_entry(path: Path) -> bytes:
    data = read_regular(path)
    first = data.splitlines()[:1]
    if not first or not first[0].startswith(b"## Entry: ") or not first[0][10:].strip():
        raise ValueError(f"{path.name} has the wrong header")
    return data


def read_saved(path: Path, header: bytes) -> bytes | None:
    try: return read_checked(path, header)
    except FileNotFoundError: return None


def atomic_write(path: Path, data: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def next_rail(old: bytes, entry: bytes) -> tuple[bytes, str]:
    entry = entry.rstrip(b"\n")
    if old.rstrip(b"\n").endswith(entry): return old, "unchanged"
    return old + (b"\n" if old.endswith(b"\n") else b"\n\n") + entry + b"\n", "appended"


def utf8_snap(data: bytes) -> bytes:
    """Trim a raw byte slice back to whole UTF-8 characters at both ends."""
    while data and data[0] & 0xC0 == 0x80: data = data[1:]
    for _ in range(4):
        try: data.decode("utf-8"); return data
        except UnicodeDecodeError as error:
            if error.start < len(data) - 4: return data
            data = data[:-1]
    return data


def check_heading(compass: bytes) -> None:
    lines = compass.decode("utf-8", "replace").splitlines()
    opens = [i for i, line in enumerate(lines) if line.strip() == "```chatrail-heading"]
    if not opens: return
    if len(opens) > 1: raise ValueError(f'bad heading block line: "{lines[opens[1]]}"')
    closes = [i for i in range(opens[0] + 1, len(lines)) if lines[i].strip() == "```"]
    if not closes: raise ValueError(f'bad heading block line: "{lines[opens[0]]}"')
    seen: list[str] = []
    for line in lines[opens[0] + 1 : closes[0]]:
        match = HEADING_LINE.fullmatch(line)
        if not match or match.group(1) in seen: raise ValueError(f'bad heading block line: "{line}"')
        seen.append(match.group(1))
    if len(seen) != 4: raise ValueError(f'bad heading block line: "{lines[opens[0]]}"')


def save_files(thread_flag: str | None, compass_path: Path, entry_path: Path | None = None) -> int:
    try:
        compass = read_checked(compass_path, b"# Compass")
        check_heading(compass)
        entry = read_entry(entry_path) if entry_path is not None else None
        directory = task_dir(resolve(thread_flag))
    except (OSError, ValueError) as error:
        print(f"ChatRail not saved: {error}", file=sys.stderr); return 1
    compass_written = False
    try:
        directory.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(directory.parent / f".{directory.name}.lock", flags, 0o600), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if directory.is_symlink(): raise OSError("task folder must not be a symlink")
            directory.mkdir(exist_ok=True)
            old_saved = read_saved(directory / "rail.md", b"# Rail")
            read_saved(directory / "compass.md", b"# Compass")
            old = old_saved if old_saved is not None else EMPTY_RAIL
            new, rail_result = next_rail(old, entry) if entry is not None else (old, "unchanged")
            atomic_write(directory / "compass.md", compass)
            compass_written = True
            if old_saved is None or new != old: atomic_write(directory / "rail.md", new)
    except (OSError, ValueError) as error:
        retry = "ChatRail partial save: Compass was saved. Rail is still old. Retry the same save command."
        print(retry if compass_written else f"ChatRail not saved: {error}", file=sys.stderr); return 2
    print(f"ChatRail saved: rail={rail_result} compass=replaced")
    return 0


def read_files(thread_flag: str | None) -> int:
    try:
        directory = task_dir(resolve(thread_flag))
        if directory.is_symlink(): raise OSError("task folder must not be a symlink")
        rail = read_saved(directory / "rail.md", b"# Rail") or EMPTY_RAIL
        compass = read_saved(directory / "compass.md", b"# Compass") or EMPTY_COMPASS
    except (OSError, ValueError) as error:
        print(f"ChatRail not read: {error}", file=sys.stderr); return 1
    sys.stdout.buffer.write(b"=== RAIL ===\n" + rail + b"\n=== COMPASS ===\n" + compass)
    return 0


def hook_session(want_root_stop: bool = False) -> tuple[str | None, Path | None]:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if payload.get("agent_id") or payload.get("agent_type") or (want_root_stop and payload.get("stop_hook_active")): return None, None
        return (session := resolve(session=payload.get("session_id"), hop=False)), task_dir(follow_alias(session))
    except (AttributeError, json.JSONDecodeError, ValueError): return None, None


def stop_review() -> int:
    _, directory = hook_session(want_root_stop=True)
    # Opt-in: only threads that already have a ChatRail task get reviewed.
    if directory is None or (os.environ.get("CHATRAIL_ALWAYS") != "1" and not directory.exists()): return 0
    if (directory / ".paused").exists(): return 0
    reason = (
        f'Run one ChatRail AI review now. AI must decide all meaning. First run: python3 "{Path(__file__).resolve()}" read --thread-id "{directory.name}". '
        "Only clear user words may add or change the goal. Choose NO_SAVE only if goal, proof, direction, progress, blocker, next move, and useful unknowns did not change. "
        "If the current reading changed but lasting Rail meaning did not, write Compass only. If lasting Rail meaning changed, write Compass and one Rail entry. "
        "Save proposals with the script. Do not edit the saved Rail or Compass. " + DRIFT
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def on_task(name: str | None, session: str | None) -> int:
    try:
        if name and not valid_id(name): raise ValueError("invalid task name")
        session = session if session and valid_id(session) else None
        directory = task_dir(name or resolve(session=session))
        if directory.is_symlink(): raise ValueError("task folder must not be a symlink")
    except ValueError as error:
        print(f"ChatRail on: {error}", file=sys.stderr); return 1
    created = not directory.is_dir()
    directory.mkdir(parents=True, exist_ok=True)
    for filename, seed in (("rail.md", EMPTY_RAIL), ("compass.md", EMPTY_COMPASS)):
        if not (directory / filename).exists(): atomic_write(directory / filename, seed)
    resumed = (directory / ".paused").exists()
    (directory / ".paused").unlink(missing_ok=True)
    if name and session:
        (home() / "aliases").mkdir(parents=True, exist_ok=True)
        atomic_write(home() / "aliases" / session, f"{directory.name}\n".encode())
    if created:
        print(f"ChatRail created new task {directory.name}: {directory.resolve()}"); return 0
    try: rail = read_regular(directory / "rail.md")
    except OSError: rail = b""
    entries = rail.count(b"\n## Entry: ") + rail.startswith(b"## Entry: ")
    line = f"ChatRail attached to {directory.name} · {entries} rail entries · last save {ts(directory / 'compass.md')}"
    print(line + (" (resumed from pause)" if resumed else ""))
    return 0


def pause_task(thread_flag: str | None) -> int:
    try:
        directory = task_dir(resolve(thread_flag))
        if not directory.is_dir(): raise ValueError(f"no task for {directory.name}")
    except ValueError as error:
        print(f"ChatRail pause: {error}", file=sys.stderr); return 1
    already = (directory / ".paused").exists()
    (directory / ".paused").touch()
    print(f"ChatRail {'already paused' if already else 'paused'}: {directory.resolve()}")
    return 0


def archive_path(name: str, stamp: dt.datetime) -> Path:
    folder = home() / "archive"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    base = f"{name}-{stamp.strftime('%Y%m%dT%H%M%SZ')}"
    path, suffix = folder / f"{base}.md", 2
    while path.exists():
        path, suffix = folder / f"{base}-{suffix}.md", suffix + 1
    return path


def archive_task(thread_flag: str | None) -> int:
    try:
        directory = task_dir(resolve(thread_flag))
        if directory.is_symlink(): raise ValueError("task folder must not be a symlink")
        if not directory.is_dir(): raise ValueError(f"no task for {directory.name}")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(directory.parent / f".{directory.name}.lock", flags, 0o600), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rail = read_saved(directory / "rail.md", b"# Rail") or EMPTY_RAIL
            compass = read_saved(directory / "compass.md", b"# Compass") or EMPTY_COMPASS
            stamp = dt.datetime.now(dt.timezone.utc)
            path = archive_path(directory.name, stamp)
            head = f"# ChatRail archive · task {directory.name} · archived {stamp.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            atomic_write(path, head.encode() + b"\n\n" + rail + b"\n" + compass)
            atomic_write(directory / "rail.md", EMPTY_RAIL)
            atomic_write(directory / "compass.md", EMPTY_COMPASS)
    except (OSError, ValueError) as error:
        print(f"ChatRail archive: {error}", file=sys.stderr); return 1
    print(f"ChatRail archived: {path.resolve()} — task {directory.name} reset to a fresh road.")
    return 0


def inject() -> int:
    session, directory, woven = *hook_session(), None
    if directory is None or directory.is_symlink(): return 0
    if directory.name == session and not directory.is_dir() and (target := most_recent_task()) is not None and not (task_dir(target) / ".paused").exists():
        (home() / "aliases").mkdir(parents=True, exist_ok=True); atomic_write(home() / "aliases" / session, f"{target}\n".encode()); directory, woven = task_dir(target), target
    if not directory.is_dir(): return 0
    if (directory / ".paused").exists():
        print(f"ChatRail: task {directory.name} is paused (since {ts(directory / '.paused')}). /chatrail:on resumes."); return 0
    try:
        rail = read_saved(directory / "rail.md", b"# Rail") or EMPTY_RAIL
        saved_compass = read_saved(directory / "compass.md", b"# Compass")
        compass = saved_compass or EMPTY_COMPASS
        stamp = ts(directory / "compass.md" if saved_compass is not None else directory)
    except (OSError, ValueError):
        print("ChatRail: saved task files are malformed; orientation skipped."); return 0
    cut, tail = False, rail
    if len(compass) > 4096:
        newline = compass.rfind(b"\n", 0, 4096)
        compass, cut = (compass[: newline + 1] if newline >= 0 else utf8_snap(compass[:4096])), True
    if len(rail) > 4096:
        found = rail[-4096:].find(b"\n## Entry: ")
        tail, cut = (rail[-4096:][found + 1 :] if found >= 0 else b""), True
    marker = f'…[truncated — full history: python3 "{Path(__file__).resolve()}" read --thread-id "{directory.name}"]'.encode()
    note = [f"ChatRail: this session had no task of its own — joined the existing road {woven}. /chatrail:on <a different name> starts a separate road.".encode()] if woven else []

    def body_of(tail_bytes: bytes) -> bytes:
        return b"\n".join([f"=== CHATRAIL ORIENTATION · thread {directory.name} · compass saved {stamp} ===".encode()] + note + [TRUTH.encode(), b"--- COMPASS (whole) ---", compass.rstrip(b"\n"), b"--- RAIL (newest tail) ---", tail_bytes.rstrip(b"\n"), b"=== END CHATRAIL ORIENTATION (latest copy replaces any earlier copy) ==="])

    body = body_of(tail)
    budget = 8192 - len(marker) - 2
    if len(body) > budget:
        trimmed = tail[len(body) - budget :]
        newline = trimmed.find(b"\n")
        body, cut = body_of(trimmed[newline + 1 :] if newline >= 0 else utf8_snap(trimmed)), True
    sys.stdout.buffer.write(body + (b"\n" + marker if cut else b"") + b"\n")
    return 0


def task_rows() -> list[tuple[float, str, int]]:
    rows, tasks = [], home() / "tasks"
    for entry in tasks.iterdir() if tasks.is_dir() else ():
        if not valid_id(entry.name) or entry.is_symlink() or not entry.is_dir(): continue
        try: info = (entry / "compass.md").stat()
        except OSError: info = None
        rows.append((info.st_mtime if info else 0, entry.name, info.st_size if info else 0))
    rows.sort(key=lambda row: row[0], reverse=True); return rows


def most_recent_task() -> str | None:
    return next((name for _, name, _ in task_rows()), None)


def recent(stream=sys.stdout) -> int:
    if not (rows := task_rows()):
        print("ChatRail: no tasks.", file=stream); return 0
    for mtime, name, size in rows[:5]:
        print(f"{name}\t{dt.datetime.fromtimestamp(mtime).isoformat(timespec='seconds')}\t{size}B", file=stream)
    return 0


def adopt(name: str, thread_flag: str | None) -> int:
    try:
        if not valid_id(name): raise ValueError("invalid task name")
        session = resolve(thread_flag, hop=False)
    except ValueError as error:
        print(f"ChatRail adopt: {error}", file=sys.stderr); return 1
    if not task_dir(name).is_dir():
        print(f"ChatRail adopt: no task named {name} — recent tasks:", file=sys.stderr); recent(sys.stderr); return 1
    (home() / "aliases").mkdir(parents=True, exist_ok=True)
    atomic_write(home() / "aliases" / session, f"{name}\n".encode())
    print(f"ChatRail adopted: {session} -> {name}")
    return 0


def alias_target(file: Path) -> str:
    try: return read_regular(file).decode("utf-8", "replace").rstrip("\n")
    except OSError: return ""


def clean(args: argparse.Namespace) -> int:
    for variable in ("CHATRAIL_HOME", "CODEX_HOME"):
        if os.environ.get(variable) == "":
            print(f"ChatRail: {variable} is set but empty — refusing", file=sys.stderr); return 1
    alias_dir = home() / "aliases"
    alias_files = list(alias_dir.iterdir()) if alias_dir.is_dir() else []
    if args.thread_id:
        if not valid_id(args.thread_id) or not task_dir(args.thread_id).is_dir():
            print(f"ChatRail clean: no task {args.thread_id}", file=sys.stderr); return 1
        shutil.rmtree(task_dir(args.thread_id))
        (home() / "tasks" / f".{args.thread_id}.lock").unlink(missing_ok=True)
        stale = [file for file in alias_files if alias_target(file) == args.thread_id]
        for file in stale: file.unlink()
        print(f"ChatRail cleaned: task {args.thread_id} and {len(stale)} alias(es)")
    elif args.aliases:
        stale = [file for file in alias_files if not (valid_id(alias_target(file)) and task_dir(alias_target(file)).is_dir())]
        for file in stale: file.unlink()
        print(f"ChatRail cleaned: {len(stale)} stale alias(es)")
    else:
        legacy = _home("CODEX_HOME", ".codex") / "chatrail"
        if not legacy.exists():
            print(f"ChatRail: no legacy state at {legacy}"); return 0
        tasks = legacy / "tasks"
        count = sum(1 for entry in tasks.iterdir() if entry.is_dir()) if tasks.is_dir() else 0
        if not args.confirm:
            print(f"ChatRail legacy target: {legacy} ({count} task dirs). Re-run with --confirm to delete."); return 0
        shutil.rmtree(legacy)
        print(f"ChatRail cleaned legacy: {count} task dirs removed from {legacy}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for simple in ("stop", "inject", "recent"): commands.add_parser(simple)
    for with_thread in ("read", "pause", "archive"): commands.add_parser(with_thread).add_argument("--thread-id")
    save_command = commands.add_parser("save")
    save_command.add_argument("--thread-id"); save_command.add_argument("--compass", type=Path, required=True); save_command.add_argument("--append", type=Path)
    on_command = commands.add_parser("on")
    on_command.add_argument("name", nargs="?"); on_command.add_argument("--session-id")
    adopt_command = commands.add_parser("adopt")
    adopt_command.add_argument("name"); adopt_command.add_argument("--thread-id")
    clean_command = commands.add_parser("clean"); clean_command.add_argument("--confirm", action="store_true")
    group = clean_command.add_mutually_exclusive_group(required=True)
    group.add_argument("--thread-id"); group.add_argument("--aliases", action="store_true"); group.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    handlers = {
        "read": lambda: read_files(args.thread_id), "save": lambda: save_files(args.thread_id, args.compass, args.append),
        "stop": stop_review, "inject": inject, "recent": recent,
        "on": lambda: on_task(args.name, args.session_id), "pause": lambda: pause_task(args.thread_id),
        "archive": lambda: archive_task(args.thread_id),
        "adopt": lambda: adopt(args.name, args.thread_id), "clean": lambda: clean(args),
    }
    return handlers[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
