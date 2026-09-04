# chatrail 1.1 release contract

This is the source of truth for ChatRail 1.1. Runtime, tests, skill, hooks,
commands, and the public README must match it. It replaces the 1.0 contract.

## Identity and core rule

ChatRail keeps a long task's road outside chat history, in two plain Markdown
files per task. AI owns all meaning: goals, scores, summaries, judgments,
drawings. Python moves bytes and does arithmetic only. Stdlib only. The writer
keeps its safety style: no-follow opens, atomic writes, per-task flock, exact
header checks.

## State layout

- Home: `$CHATRAIL_HOME` (expanded) if set, else `~/.chatrail`.
- `tasks/<id>/rail.md` · `tasks/<id>/compass.md` · `tasks/<id>/.paused`
  (empty marker) · `tasks/.<id>.lock` · `aliases/<session-id>` (regular file,
  one line = task id).
- `archive/<id>-<UTC YYYYMMDDTHHMMSSZ>.md` (dir mode 0o700, created on first
  archive): one file per `archive` run, never deleted by the writer.
- No legacy fallback reads. `~/.codex/chatrail` is only the named target of
  `clean --legacy`.
- Ids match `^[A-Za-z0-9_-]+$` with a 64-byte length cap.

## Writer surface — ten commands, none may hold meaning rules

`scripts/chatrail.py`, at most 330 nonblank lines, cap-tested:

read · save · stop · inject · on · pause · recent · adopt · clean · archive

`archive` copies the saved rail and compass bytes into one dated file under
`archive/`, then reseeds the live task; it deletes nothing and never pauses.

There is no render script and no render cap. Drawing is AI work: the session
model draws every compass and rail panel fresh from the saved files, imitating
the reference examples, and computes the heading angle with the arithmetic
one-liner in the skill — never by eye.

## Heading block

`compass.md` may contain exactly one fenced block opened by
```` ```chatrail-heading ```` and closed by ```` ``` ````. Inside: exactly four
lines, keys N, E, S, W once each, each line `K: <int 0-10>  # <nonempty
reason>`. `save` validates this byte shape with a regex, quotes the offending
line, and rejects malformed blocks. Needle = net vector (`x = E−W`,
`y = N−S`, azimuth from `atan2(x, y)`); status phrase = largest raw pull.

## Inject hook guarantees

A SessionStart hook (matcher `startup|resume|compact`) runs `inject`:

- payload hard cap 8192 bytes: compass head-capped at 4096 bytes, rail tail
  capped at 4096 bytes snapped to an entry boundary; any cut is visible and
  names the recovery command;
- untracked session, or a child agent: complete silence;
- exit 0 on every path — inject never blocks a session.

## Contract amendments from 1.0

- "Three writer commands only" → the surface above, with "none may hold
  meaning rules."
- "No session-start hook" → the `inject` hook: ≤8192 bytes, silence for
  untracked, exit 0 on every path.
- "No pointer" → "One pointer, human-authored": one alias file per session,
  one line, one hop, written only downstream of the human's words; no other
  pointer, index, or registry may exist.
- State home → `~/.chatrail` (`CHATRAIL_HOME` override); `tasks/<id>/` +
  `aliases/<session-id>`; no legacy fallback.
- Compass format → may contain exactly one `chatrail-heading` block; `save`
  validates its byte shape.
- Line caps → per-script: the writer's cap is 330 nonblank lines with an
  enforcing test. No render script exists, so no render cap exists.

## Semantic suite

`tests/semantic/` holds ten cases, 01–10. Case 07 (drift alarm) carries the
amended pass sign: the alarm "offers exactly the two outs — refocus or
approve the new direction — and nothing more". Case 10 (user-ordered detour):
a detour the user ordered raises no alarm; it is recorded, and the standing
goal stays the goal. Ceremony-lite live protocol: run cases 07, 08, and 10
with a fresh model before ship.

## Live-proof gates

Source tests alone do not prove the live product. Before 1.1 ships:

1. a real compaction followed by a correct reorientation from the injected
   payload;
2. a real cross-day adopt by name from a fresh session;
3. the cost of the inject payload measured and recorded.

Public ChatRail is 1.1.0.
