# ChatRail

Long AI tasks can lose the plot. ChatRail keeps one task's road in two plain
Markdown files:

- `rail.md` keeps lasting history. Old entries do not change.
- `compass.md` says where the work points now.

AI owns the meaning: it writes the entries, scores the pulls, and draws the
panels. A small Python writer moves the bytes. It does not choose goals,
score work, or use a database.

## What it does

- At the end of a turn, a `Stop` hook asks AI to review the newest user
  words, fresh tool proof, Rail, and Compass, and save only real change.
- At session start, resume, and compaction, a `SessionStart` hook injects the
  last saved reading back into the session — capped at 8 KB, silent for child
  sessions or when no eligible road exists, never blocking.
- When the work drifts off the approved direction, the AI says so in one
  plain line in chat and offers two outs: refocus, or approve the new
  direction.

## Tasks and names

State lives under `~/.chatrail` (override with `CHATRAIL_HOME`):

```text
~/.chatrail/tasks/<id>/rail.md
~/.chatrail/tasks/<id>/compass.md
~/.chatrail/aliases/<session-id>
```

A task is keyed by the session id unless you name it. A named task outlives
any one session: start it with `/chatrail:on ship-the-pr`. At a fresh session
with no binding, ChatRail joins the newest road once when that road is unpaused
and names the road it joined. Choosing a different saved road still requires your
explicit words; `read`, `save`, and `stop` never rebind a session.

## Commands

Eight slash commands:

- `/chatrail:on [name]` — start a task, or attach to an existing one; resumes
  a paused task.
- `/chatrail:off` — pause the task. History is kept.
- `/chatrail:compass` — draw the compass panel.
- `/chatrail:rail` — draw the rail panel.
- `/chatrail:status` — draw both, compass over rail.
- `/chatrail:clean` — list tasks, then delete only the one you name.
- `/chatrail:archive` — save the road to one dated file, then start the live task fresh without deleting history.
- `/chatrail:backfill` — reconstruct the lasting road from conversation evidence already in the current session.

There is no render script. The AI draws every panel fresh from the saved
files, following the reference examples that ship with the skill. The heading
needle comes from four saved scores (N, E, S, W) and a one-line arithmetic
check — computed, never eyeballed.

## Check the source

```text
python3 -m unittest discover -s skills/chatrail/tests -v
```

The tests cover read, append-only Rail, Compass replace, the heading block,
aliases, pause, injection caps, bad input, concurrent saves, safe retry, and
task-folder guards.

The full contract is in
`skills/chatrail/references/spec.md`.

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

Skill-only hosts can still use ChatRail: at task start, run the writer's
`read` command and reconcile the saved reading with the conversation before
acting. They cannot promise automatic review or re-injection without working
lifecycle hooks.

## Remove

```text
codex plugin remove chatrail@chatrail
claude plugin uninstall chatrail@chatrail --scope user
```

MIT. Built by [Orchestrator HQ](https://github.com/Orchestrator-HQ).
