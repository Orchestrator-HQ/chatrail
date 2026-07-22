# ChatRail

AI coding agents lose the plot during long work. ChatRail gives each task a
small compass, a committed work rail, and an append-only history of meaningful
detours.

It works with or without Git. It follows a conversation across folder changes
and restarts. If ChatRail itself breaks, the user's message still goes through.

## What it keeps

- `working.compass.yaml`: where the work points now
- `conversation.rail.yaml`: North, next, route, open work, and parked work
- `orientation.events.jsonl`: the before-and-after history of real changes

ChatRail stores short summaries and direction. It does not store raw chat
transcripts or secrets.

## Install

### Codex

```text
codex plugin marketplace add Orchestrator-HQ/chatrail
codex plugin add chatrail@chatrail
```

Open `/hooks`, trust the `UserPromptSubmit` and `Stop` hooks, then restart Codex
once. New and existing tasks use ChatRail on their next message.

### Claude Code

```text
/plugin marketplace add Orchestrator-HQ/chatrail
/plugin install chatrail@chatrail
```

### Any Agent Skills host

```text
npx skills add Orchestrator-HQ/chatrail --skill chatrail --global --yes
```

Hosts that do not support lifecycle hooks can still use the ChatRail skill
manually for reorientation.

Ask the agent:

```text
Use $chatrail to reorient this task.
```

Manual use asks the active agent to apply the ChatRail instructions. It does
not run automatic turn reviews.

Update the portable skill with:

```text
npx skills update chatrail --global --yes
```

Portable installation does not register lifecycle hooks. Use a native plugin
path when you need automatic turn review.

### Runtime limits

ChatRail requires Python 3. Its file lock uses the POSIX-only `fcntl` module.
This release does not support Windows. Automatic turn review also requires a
host that can register and trust the included lifecycle hooks.

## How it behaves

North is the lasting product outcome. Heading is the direction the work points
right now. The Rail keeps the agreed next move and route. A temporary detour can
change heading and next without silently replacing North.

Project tasks may keep `.chatrail/` beside the project. Tasks without a project
get a private bundle under `~/.codex/chatrail/tasks/`. One task stays pinned to
one bundle for its life.

## Prove it

```text
python3 -m unittest discover -s skills/chatrail/tests -v
```

The behavior suite covers non-Git tasks, resumed sessions, folder changes,
corrupt state, crash recovery, concurrent updates, child-agent isolation, and
the one-time Stop reminder.

The full design is in [SPEC.md](skills/chatrail/SPEC.md).

## License

MIT. Built by [Orchestrator HQ](https://github.com/Orchestrator-HQ).
