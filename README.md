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
npx skills add Orchestrator-HQ/chatrail@ChatRail
```

Hosts that do not support lifecycle hooks can still use the ChatRail skill
manually for reorientation.

## How it behaves

North is the lasting product outcome. Heading is the direction the work points
right now. The Rail keeps the agreed next move and route. A temporary detour can
change heading and next without silently replacing North.

Project tasks may keep `.chatrail/` beside the project. Tasks without a project
get a private bundle under `~/.codex/chatrail/tasks/`. One task stays pinned to
one bundle for its life.

## Prove it

```text
python3 -m unittest discover -s skills/ChatRail/tests -v
```

The behavior suite covers non-Git tasks, resumed sessions, folder changes,
corrupt state, crash recovery, concurrent updates, child-agent isolation, and
the one-time Stop reminder.

The full design is in [SPEC.md](skills/ChatRail/SPEC.md).

## License

MIT. Built by [Orchestrator HQ](https://github.com/Orchestrator-HQ).
