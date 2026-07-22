---
name: chatrail
description: Keep long AI tasks oriented and resumable without requiring Git. Use when the user says ChatRail, reorient, refocus, recalibrate, or asks to recover the main line after drift.
---

# ChatRail

ChatRail is a quiet continuity layer. It keeps the user from having to explain
the whole task again after compaction, a detour, a restart, or a folder change.

It has two live truths:

- `working.compass.yaml` says where the work actually stands and points.
- `conversation.rail.yaml` says the agreed road: North, next, route, open, parked.

`orientation.events.jsonl` preserves every meaningful before-and-after change.
It is recovery history, not a third live truth.

## Turn Review

At the end of a root turn:

1. Update Compass only if present reality or direction truly changed.
2. Update Rail only if the agreed road truly changed.
3. Otherwise complete the review with no patches.

Never edit ChatRail files directly. Run the exact `reconcile` command supplied
by the hook. Add `--compass '<json>'` or `--rail '<json>'` only when meaning
changed. Patches contain complete replacement values for the named top-level
fields.

Compass changes for a real completion, failure, blocker, disproved claim,
meaningful discovery, drift, or changed return move. Discussion and effort do
not count as movement.

Rail changes when North changes, the next move completes or changes, the route
changes, a real question opens or closes, or work is parked or resumed.

## Bearings

- North: direct movement toward Rail North.
- East: useful side work that delays North.
- South: movement against North or false progress.
- West: costly or weak-payoff drift.

The four bearing coordinates are fixed. The heading is `[x, y]`, uses multiples
of ten, and satisfies `abs(x) + abs(y) = 100`. Its context explains the coarse
judgment. `[30, 70]` means 70% north and 30% east.

## Reorient

When asked to reorient, answer briefly:

```text
North: <main outcome>
Now: <present truth>
Drift: <direction and why>
Return path: <next move toward North>
```

Do not turn this into a new roadmap or a long recap unless asked.

## Storage And Failure

A task already pinned to a bundle keeps it for its whole life. A task with a
nearby complete `.chatrail` uses that project bundle. Otherwise it gets a
private local bundle under `~/.codex/chatrail/tasks/`.

Git is optional. ChatRail failures never block a user message. A corrupt bundle
is preserved and frozen rather than silently replaced. The Stop hook may pause
once when a healthy review was skipped, then it must let the task finish.

Child agents may read orientation but never update the root task's state.
