# ChatRail

AI coding agents lose the plot during long work. ChatRail gives each task a
small compass, a committed work rail, and an append-only history of meaningful
detours.

It works with or without Git. With the native hooks installed, it follows a
conversation across folder changes and restarts. Manual skill use reorients the
current task but does not run the automatic review loop. If ChatRail itself
breaks, the user's message still goes through.

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

Update and verify it:

```text
codex plugin marketplace upgrade chatrail
codex plugin add chatrail@chatrail
codex plugin list
```

The ChatRail row must show version `0.2.1`. After an update, open `/hooks`
again. Trust either hook again if Codex marks it `new` or `modified`, then start
a new task.

Remove it and leave it removed:

```text
codex plugin remove chatrail@chatrail
```

If an update stays stale, refresh and reinstall it:

```text
codex plugin marketplace upgrade chatrail
codex plugin remove chatrail@chatrail
codex plugin add chatrail@chatrail
codex plugin list
```

### Claude Code

```text
/plugin marketplace add Orchestrator-HQ/chatrail
/plugin install chatrail@chatrail
```

From a terminal, update and verify it:

```text
claude plugin marketplace update chatrail
claude plugin update chatrail@chatrail --scope user
claude plugin list
```

The ChatRail row must show version `0.2.1`. Restart Claude Code after an
update.

Remove it and leave it removed:

```text
claude plugin uninstall chatrail@chatrail --scope user
```

If an update stays stale, refresh and reinstall it:

```text
claude plugin marketplace update chatrail
claude plugin uninstall chatrail@chatrail --scope user
claude plugin install chatrail@chatrail --scope user
claude plugin list
```

Restart Claude Code after the reinstall.

### Agent Skills hosts supported by the Skills CLI

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

For an installed Codex plugin, first open `/hooks`. The `UserPromptSubmit` and
`Stop` hooks must both be enabled and trusted. Start a new task and send:

```text
Use $chatrail. This is a live proof. Do not change project files. Complete any
ChatRail turn review as no-change, then reply exactly: CHATRAIL_LIVE_HOOK_OK
```

The agent must read the installed `skills/chatrail/SKILL.md`, reply with
`CHATRAIL_LIVE_HOOK_OK`, and run both hooks without an error. Then open the
newest JSON file under `~/.codex/chatrail/receipts/`. Its review status must be
`complete`. Registration alone is not proof.

For source behavior tests, run:

```text
python3 -m unittest discover -s skills/chatrail/tests -v
```

The behavior suite covers non-Git tasks, resumed sessions, folder changes,
corrupt state, crash recovery, concurrent updates, child-agent isolation, and
the one-time Stop reminder.

The full design is in [SPEC.md](skills/chatrail/SPEC.md).

## Troubleshoot

| Problem | Check |
|---|---|
| Plugin shows an old version | Refresh its marketplace, reinstall it, and start a new task. |
| Hook does not run | Open `/hooks`; check that both ChatRail hooks are enabled and trusted. |
| Hook changed after an update | Review the exact command and trust the `new` or `modified` hook again. |
| Python fails | Run `python3 --version`, then `python3 -c 'import fcntl'`. |
| Wrong skill is loaded | Remove old standalone ChatRail copies and confirm the loaded path contains the current plugin version and `skills/chatrail/SKILL.md`. |
| No completed receipt appears | Check the hook output, then inspect the newest file under `~/.codex/chatrail/receipts/`. |

## License

MIT. Built by [Orchestrator HQ](https://github.com/Orchestrator-HQ).
