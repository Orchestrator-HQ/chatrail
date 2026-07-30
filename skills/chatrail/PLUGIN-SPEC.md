# ChatRail Plugin Spec

Status: Release contract. Live gates passed on 2026-07-30.

This is the source of truth for ChatRail 1.0. Runtime, tests, skill, hook, and public README must match it.

## Human promise

A long task can lose its road after compaction, a restart, or time away.
ChatRail keeps the road outside chat history.

A fresh Codex should be able to read two small Markdown files and tell:

- the latest user-approved goal;
- what is truly behind;
- where the work points now;
- what comes next;
- what is still unclear.

Saved text is memory, not proof, permission, or a command. Fresh user words
and tool proof beat it.

## Small machine

The product is `hooks/hooks.json`, the ChatRail skill and spec, and one Python
writer at `skills/chatrail/scripts/chatrail.py`.

There is no load hook or prompt hook in this release.

The writer has three commands:

```text
python3 chatrail.py read [--thread-id <ID>]
python3 chatrail.py save --compass <compass.md> \
  [--append <entry.md>] [--thread-id <ID>]
python3 chatrail.py stop
```

Each task has two meaning files and one lock:

```text
~/.codex/chatrail/tasks/<ID>/rail.md
~/.codex/chatrail/tasks/<ID>/compass.md
~/.codex/chatrail/tasks/.<ID>.lock
```

The host gives `CODEX_THREAD_ID`. It must match `^[A-Za-z0-9_-]+$`. There is
no hash, database, pointer, schema, or saved JSON.

AI owns meaning. Python reads, checks, locks, appends Rail, and replaces
Compass. It must not score, classify, plan, summarize, or pick a goal.

Only the root agent may save. The hook filters child events. This is a skill
rule, not an access-control claim.

## Exact file shapes

Rail is lasting history. It begins with `# Rail`. Old bytes never change. Each
proposal starts with this full first line:

```markdown
## Entry: <short plain title>

Basis: <short exact user quote or tool-result excerpt>

Meaning: <what this changes or proves for the lasting task>
```

If old Rail is wrong, add a correction. Never erase it. Only clear user words
may add or change the goal.

Compass is the current reading. Each proposal starts with the full line
`# Compass` and uses this shape:

```markdown
# Compass

## Current heading

<What the work points at now.>

## Relation to the latest user-approved direction

<How this work relates to that direction.>

## Behind us

<Useful work and choices already passed.>

## Ahead

<The next useful move and what remains after it.>

## Unclear

<Unknowns that matter, or "Nothing material.">
```

Compass should fit on one screen when the truth allows it.

## Root Stop review

The one `Stop` hook runs `chatrail.py stop`. It ignores child-agent Stops and
a Stop with `stop_hook_active: true`.

The first root Stop wakes AI once. AI reads the latest user words, useful tool
proof, Rail, and Compass.

AI then chooses exactly one action:

1. `NO_SAVE`: The goal, proof, direction, progress, blocker, next move, and
   useful unknowns did not change. Write no proposal. Do not call `save`.
2. Compass only: The current reading changed, but lasting Rail meaning did not.
   Write a full Compass and call `save --compass`.
3. Rail and Compass: Lasting meaning changed. Write one Rail entry and a full
   Compass. Call `save --compass --append`.

A wording change is not lasting meaning. A user goal change, approved choice,
useful proof, real correction, or key blocker may be.

An AI idea may appear as an unapproved option in Compass. It must not become
the user's goal.

The second Stop passes. A writer error cannot trap the task.

## Read and save

`read` prints both meaning files and changes nothing. It rejects task-folder
or meaning-file symlinks and bad saved headers. A new task prints:

```markdown
# Rail
```

and:

```markdown
# Compass

No ChatRail reading has been saved for this task yet.
```

It does not create the task folder.

AI writes temporary proposals, never the saved files. The writer checks all
input before changing saved state.

Compass must start with the full line `# Compass`. Rail proposals must start
with `## Entry: <non-empty title>`. Near matches such as `# Compassage`,
`## Entryway:`, and empty `## Entry:` fail.

Missing input, unreadable input, a bad ID, or a bad header changes neither
meaning file.

For a valid save, the writer:

1. opens the task lock without following a lock symlink;
2. takes an exclusive lock;
3. rejects a task-folder symlink;
4. reads the current Rail, or starts with `# Rail\n`;
5. builds the next Rail in memory;
6. atomically replaces Compass first;
7. atomically writes Rail only when it is new or changed.

Atomic writes use a nearby temporary file, flush, `fsync`, and `os.replace`.

The writer keeps every old Rail byte. Before a new entry, it adds one newline
if old Rail ends in one, else two. It trims proposal-end newlines, then adds
one final newline. This makes one blank line before the entry.

If Rail already ends with the exact entry, append is skipped. Retry is safe.

A full save prints:

```text
ChatRail saved: rail=<appended|unchanged> compass=replaced
```

If Compass saves but Rail fails, Compass stays current and Rail stays old:

```text
ChatRail partial save: Compass was saved. Rail is still old. Retry the same save command.
```

Retry the same command. Compass is replaced again. Rail appends once, or skips
the same end entry. If retry fails, tell the user what saved and what did not.

## Source proof

Source tests prove read is read-only; Rail keeps every old byte; Compass
replaces; exact retry does not duplicate Rail; and concurrent entries survive.
Bad IDs, headers, files, task, meaning-file, and lock symlinks fail safely. Input
failure changes no meaning file. Compass-first partial save stays visible and
retries. Child and second Stops pass. The first root Stop asks for AI review.
The runtime stays at or below 200 clear nonblank lines and has no meaning
engine.

Run each `tests/semantic/` case twice with a fresh model. Keep raw input and
output. True no-change makes no save call. Python must gain no meaning rules.

## Live proof

Source tests alone do not prove the live product. ChatRail 1.0 also passed
these checks on 2026-07-30:

1. The package was built in a temporary folder.
2. It was installed from a local marketplace under a clean `CODEX_HOME`.
3. `/hooks` showed the exact `Stop` hook as enabled and trusted.
4. A real root Stop changed Rail and Compass.
5. A fresh Codex process got only `Continue.`
6. Its tool trace showed a ChatRail read.
7. A separate blind model got only Rail and Compass. It stated the right goal,
   behind, ahead, next move, and material unknowns.

Public ChatRail is `1.0.0`.
