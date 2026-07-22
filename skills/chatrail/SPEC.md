# ChatRail Fresh-Build Specification

## Promise

The user can leave, return, compact context, change folders, or work outside a
Git repository without losing the main job or babysitting another system.

At the end of each root turn, the current agent uses the conversation it already
has to decide:

1. Did present reality or direction change? If yes, update Compass.
2. Did the agreed road change? If yes, update Rail.
3. If neither changed, write nothing and complete the review.

There is no second model call. Git may preserve project history, but ChatRail
never calls or requires Git at runtime.

## Surfaces

The permanent bundle contains exactly:

```text
.chatrail/
├── conversation.rail.yaml
├── working.compass.yaml
└── orientation.events.jsonl
```

One script owns hook handling, validation, reconciliation, locking, journaling,
atomic replacement, recovery, and the private task receipt.

The `.yaml` files use the JSON-compatible safe subset of YAML 1.2. This keeps
the files readable, deterministic, and dependency-free while avoiding a custom
general YAML parser.

## Live State

Rail contains:

```yaml
{
  "schema": 1,
  "north": "The main outcome.",
  "next": {"id": "stable-id", "summary": "Exactly one immediate move."},
  "route": [],
  "open": [],
  "parked": []
}
```

`next` is one item or `null`. Every item has only a non-empty stable `id` and
`summary`.

Compass contains fixed cardinal bearings plus:

```yaml
{
  "schema": 1,
  "bearings": {
    "north": {"coordinate": [0, 100], "definition": "..."},
    "east": {"coordinate": [100, 0], "definition": "..."},
    "south": {"coordinate": [0, -100], "definition": "..."},
    "west": {"coordinate": [-100, 0], "definition": "..."}
  },
  "heading": {"coordinate": [30, 70], "context": "Present truth and direction."},
  "drift": "Why this is or is not on the agreed path.",
  "return_path": "The concrete move toward North."
}
```

Heading values are multiples of ten and `abs(x) + abs(y) = 100`. Coordinates
measure direction, not completion, effort, speed, or confidence.

## Task Identity And Pinning

The task key is:

```text
sha256("codex-chatrail-v1\0" + stable_session_id)
```

It never uses the current folder, process ID, repository path, or time.

The private receipt is:

```text
${CODEX_HOME:-~/.codex}/chatrail/receipts/<task-key>.json
```

It pins one canonical bundle path and stores only the current review state and
one warning fingerprint. Once pinned, a task never rediscovers because its
folder, branch, repository, or process changed.

On the first valid root prompt:

1. Reuse an existing receipt pin.
2. Otherwise walk from `cwd` toward, but not including, the home directory.
3. Use the nearest complete new-format `.chatrail` found.
4. If none exists, create a private local bundle at
   `${CODEX_HOME:-~/.codex}/chatrail/tasks/<task-key>/`.
5. If a nearer partial or corrupt bundle exists, pin and freeze it. Never fork
   a second hidden history.

Local directories use mode `0700`; files use `0600`. Local history is not
deleted automatically and does not sync unless explicitly exported.

## Append-Only Preservation

Each accepted semantic change appends one event before replacing live files:

```json
{
  "version": 1,
  "event_id": "uuid",
  "review_id": "uuid",
  "ts": "UTC timestamp",
  "reason": "why meaning changed",
  "transitions": [{
    "target": "compass",
    "before": {},
    "after": {},
    "before_sha256": "...",
    "after_sha256": "..."
  }]
}
```

One event may contain Compass and Rail transitions, always in that order. A
no-change review writes no event. Initial creation writes one genesis event
with the complete starting snapshots.

The script appends and fsyncs the event, then atomically writes Compass and
Rail. On restart:

- A live after-hash means the transition completed.
- A live before-hash means the script completes the recorded transition.
- Any third hash freezes writes rather than blessing unknown state.

Expected-before hashes reject stale concurrent reconciliation. A private lock
under `${CODEX_HOME:-~/.codex}/chatrail/locks/` serializes root tasks that share
one project bundle without adding a fourth bundle file.

## Hooks

Only `UserPromptSubmit` and `Stop` are registered.

`UserPromptSubmit` creates one pending review and injects a short command for
the current agent. Missing or malformed identity, child-agent payloads, storage
errors, permission errors, and corrupt state all fail open. A user message is
never blocked by ChatRail.

`Stop` passes when the review completed. If a healthy review is pending, it
blocks once with one bounded reminder. A second Stop passes. Any ChatRail
internal failure also passes.

The agent-facing operation is:

```text
reconcile(session_id, review_id, reason, compass_patch?, rail_patch?)
```

Unknown fields, invalid shapes, stale reviews, and changed expected hashes are
rejected. Reconcile completes the receipt even when there was no semantic
change.

## Corruption And Privacy

A corrupt or incomplete bundle is never silently replaced. The script preserves
the bytes, freezes writes, records one warning fingerprint, warns once, and lets
normal work continue. Explicit repair is required before ChatRail writes again.

Rail, Compass, and events contain compact orientation summaries only. They must
not contain credentials, secrets, private raw conversations, or large task
outputs.

## Acceptance

One table-driven behavior suite proves:

- Fresh non-Git tasks get separate local bundles and survive resume or cwd changes.
- Complete project bundles are discovered without Git.
- Missing identity and child hooks are safe no-ops.
- Stop blocks at most once.
- No-change review writes no event.
- Changes preserve full before and after snapshots with a valid hash chain.
- An appended event recovers an interrupted live write.
- Partial or corrupt bundles warn once and never block conversation.
- Stale expected hashes prevent concurrent clobbering.

Live acceptance requires one non-Git Codex task and one project Codex task. Both
must receive the semantic review prompt, accumulate the right bundle, and finish
without a retry loop.

## Cutover

The Git-first implementation is preserved at remote branch
`codex/archive-chatrail-git-first-2026-07-19`. The fresh build deletes the old
control flow and migration machinery. The current approved project meaning is
imported through one genesis event; no permanent migration framework ships.
