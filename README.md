# ChatRail

Long AI tasks can lose the plot. ChatRail keeps one task's road in two plain
Markdown files:

- `rail.md` keeps lasting history. Old entries do not change.
- `compass.md` says where the work points now.

AI writes the meaning. A small Python writer checks and moves the Markdown. It
does not choose goals, score work, or use a database.

## What it does

ChatRail has one `Stop` hook. The first root Stop asks AI to review the newest
user words, fresh tool proof, Rail, and Compass. Child Stops do nothing. The
second root Stop passes.

The review has three choices:

- save nothing when the task's meaning did not change;
- replace Compass when only the current reading changed;
- append one Rail entry and replace Compass when lasting meaning changed.

The writer is the only code that changes saved files. It locks each task,
checks exact file headers, keeps old Rail bytes, writes Compass first, and
makes retry safe.

Each task uses two meaning files and one lock:

```text
~/.codex/chatrail/tasks/<CODEX_THREAD_ID>/rail.md
~/.codex/chatrail/tasks/<CODEX_THREAD_ID>/compass.md
~/.codex/chatrail/tasks/.<CODEX_THREAD_ID>.lock
```

There is no load or prompt hook in 1.0.

## Check the source

```text
python3 -m unittest discover -s skills/chatrail/tests -v
```

The tests cover read, append-only Rail, Compass replace, bad input, concurrent
saves, safe retry, task-folder guards, and the one-time Stop wake.

The full contract is in
[PLUGIN-SPEC.md](skills/chatrail/PLUGIN-SPEC.md).

## Live proof

ChatRail 1.0 passed its live proof on 2026-07-30:

1. it was installed under a clean `CODEX_HOME`;
2. `/hooks` showed the exact Stop hook as enabled and trusted;
3. a real root Stop changed Rail and Compass;
4. a fresh Codex process got only `Continue.`;
5. that process read ChatRail and kept the right direction.

Source tests alone did not earn this claim. The live hook and fresh return did.

## Install

Codex:

```text
codex plugin marketplace add Orchestrator-HQ/chatrail
codex plugin add chatrail@chatrail
```

Claude Code:

```text
/plugin marketplace add Orchestrator-HQ/chatrail
/plugin install chatrail@chatrail
```

Skill-only hosts can read ChatRail when asked. They cannot promise an automatic
review without a working lifecycle hook.

## Remove

```text
codex plugin remove chatrail@chatrail
claude plugin uninstall chatrail@chatrail --scope user
```

MIT. Built by [Orchestrator HQ](https://github.com/Orchestrator-HQ).
