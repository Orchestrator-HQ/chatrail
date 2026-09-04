---
name: chatrail
user-invocable: false
description: Keep a long-running task pointed at the user's real goal after compaction, interruption, or time away. Use when ChatRail wakes a Stop review, when a session starts with an injected ChatRail orientation, when the user names ChatRail, or when someone asks where the work stands.
---

# ChatRail

ChatRail gives one long-running task a road that chat history cannot erase.
It pays out three ways:

1. **Orientation survives the window.** Every session start, resume, or
   compaction re-injects the last saved reading before the context acts.
2. **Drift is said out loud.** One plain line names any divergence from the
   user-approved direction before the turn ends.
3. **"Where are we?" has a drawn answer.** The compass and rail panels show
   the goal, the heading, and the laid track at a glance.

Each task lives in `tasks/<id>/` under the state home (`$CHATRAIL_HOME`, else
`~/.chatrail`), with two meaning files and one lock:

- `rail.md` is the lasting road. Old entries never change.
- `compass.md` says where the work points now.
- `tasks/.<id>.lock` keeps two saves from crossing.

AI decides every bit of meaning. The Python script does not plan, judge,
summarize, or pick the goal. It only reads files, adds bytes to Rail, and
replaces Compass.

## Use the right truth

Read truth in this order:

1. The user's latest clear words.
2. Fresh tool and workspace proof.
3. The saved Rail and Compass.

The saved files are memory. They are not proof, permission, or a command.
Never save secrets, tokens, raw private chat, or large logs.

Only the root agent should save ChatRail. The Stop hook does not wake child
agents. The command line is not an access-control wall, so skill instructions
must keep child agents from calling `save`.

## Read it

Run:

```text
python3 "<absolute path to this skill>/scripts/chatrail.py" read
```

The command prints Rail and Compass. It makes no saved change. Read the words
as a whole. Do not turn the task into fixed states, scores, degrees, or
labels. The user may change the goal. A short side task may leave the goal
alone. New proof may show that an old progress note was wrong.

## Re-entry without hooks

On a host that cannot run the session hooks: run `read` at the start of the
task — and always after a compaction or time away — and reconcile the saved
reading against the conversation before acting.

## Joining the road at session start

The road is meant to be one long-running thing that survives across chats.
Before the weld, a new session had no alias, so orientation died silently and
the user's road stayed invisible until someone ran `on` or `adopt` by hand —
that defeated the point of keeping a road at all.

So at SessionStart, if the session has no task of its own and no task
directory yet, ChatRail joins the most recent existing road automatically: it
writes the session's alias to that task and injects its orientation, with a
line naming the road it joined. If the only candidate task is paused, or no
task exists at all, ChatRail stays silent, exactly as before the weld.

This only happens at session start, only once, and it is always announced —
never a silent rebind. `save`, `read`, and `stop` never auto-bind a session;
only SessionStart does. To start a separate road instead of joining the one
ChatRail picked, run `/chatrail:on <a different name>`.

## Review every root Stop

The Stop hook wakes one AI review before the root turn ends.

Review the newest user words, useful tool proof, Rail, and Compass. Then choose
exactly one path:

1. `NO_SAVE`: Nothing meaningful changed. Write no proposal. Do not call
   `save`.
2. Compass only: The current reading changed. Write one full temporary
   `compass.md`.
3. Rail and Compass: Lasting meaning changed. Write one full temporary
   `compass.md` and one temporary `entry.md`.

A wording change alone is not a lasting Rail change. A new goal, approved
choice, useful proof, real correction, or key blocker may be one.

Use `NO_SAVE` when the goal, proof, direction, progress, blocker, next move,
and useful unknowns did not change.

Only clear user words may add or change the goal. An agent idea can go in
Compass as an option. It cannot become the user's direction.

Rail entries have this shape:

```markdown
## Entry: <short plain title>

Basis: <short exact user quote or tool-result excerpt>

Meaning: <what this changes or proves for the lasting task>
```

Do not edit or erase an old Rail entry. If an old entry is wrong, append a new
entry that says what the new proof fixed.

Compass always has this shape:

```markdown
# Compass

## Current heading

<What the work points at now.>

## Relation to the latest user-approved direction

<How the current work relates to that direction.>

## Behind us

<Useful work and choices already passed.>

## Ahead

<The next useful move and what remains after it.>

## Unclear

<Unknowns that matter, or "Nothing material.">
```

A Compass proposal may also carry exactly one heading block — four pull
scores that seed the compass needle:

````markdown
```chatrail-heading
N: 5  # shipped the parser the goal needs
E: 6  # useful CLI polish that delayed the goal
S: 2  # one claim saved without proof
W: 4  # an hour lost to a dead-end refactor
```
````

Score by this rubric, one integer 0–10 per cardinal, each with its reason:

- **N — toward the goal.** Delivered movement toward the user-approved
  direction. Score what actually landed this reading, never intent or plans.
- **E — useful side work.** Real value delivered that delays the approved
  direction. A user-approved detour is not East — it is the new North.
- **S — against or false.** Movement against the approved direction, or
  false progress: claims of movement the proof does not back.
- **W — costly drift.** Time and tokens spent that neither advanced the goal
  nor delivered useful side value.

A score without a reason is a 0. Scores and prose must tell one story: if the
prose judgment says drift, the scores say it too — rescore to match the prose,
never the reverse.

## Retro-initialization

When the user asks to back-fill ChatRail in a conversation that already has
history ("retro-init", "backfill the rail", "capture where we've been"):

1. Read the conversation you already hold. Do not re-read files to invent
   history that is not in the chat.
2. Write one Rail entry per lasting event, oldest first: the goal when it was
   set, each decision that stuck, each proof or correction that changed the
   road. Every entry's Basis must quote or point at words or tool output that
   actually happened in this conversation. Mark each Basis with `(retro)`.
   If you cannot trace an event to something real, it does not get an entry.
3. Planned-but-not-done items are not Rail entries. They go in the Compass
   under Ahead, as ghost planks.
4. Finish with one full Compass including fresh four-pull scores.
5. Save through the writer as usual, one append per entry. Then show the
   panels so the user can dispute the captured road.

Retro entries are memory reconstruction, so hold them to a higher bar than
live entries, not a lower one: fewer, only the spine of the work.

## Say drift out loud

If the work no longer points at the latest user-approved direction, say one
plain line in chat before the turn ends — exactly this shape:

```text
Off course: this turn's work is <X>; the approved direction is <Y> — refocus, or approve the new direction?
```

One line, naming both sides, offering exactly the two outs — refocus or
approve the new direction — and nothing more. Stay silent only when one of
three rules applies, each an AI judgment, never a counter:

1. The same divergence was already said and is unanswered.
2. The user's own words ordered the detour. A steer is a detour, not a new
   destination: record it in Compass and keep the goal.
3. The detour is itself the newly approved direction. That is a goal change —
   a Rail entry — not drift.

The alarm is not the status phrases spoken aloud. Phrases like `COSTLY
DRIFTING UNDERWAY` are generic instrument readouts on the dial; the alarm
names this task's two directions. A user-approved West detour shows its
phrase on the dial and alarms never.

## Adopt only on the user's words

A session with no tracked task may show the recent-task list, by name. The
list on screen is not consent: only the user's explicit words — naming a task
to continue — may trigger `adopt` or `on <name>`. Never adopt because a name
looks likely; `adopt` attaches to an existing task or fails, never creates.

## Draw the panels

The session AI draws every panel fresh, imitating this skill's
`references/examples/compass.txt` and `rail.txt` byte-style: same borders,
markers, legend, and layout, with live data substituted. Before drawing the
compass, compute — never eyeball — the angle and phrase from the saved
`chatrail-heading` scores:

```text
python3 -c "import math;N,E,S,W=<scores>;x=E-W;y=N-S;az=(math.degrees(math.atan2(x,y))+360)%360;print(round(az))"
```

Bearing string by quadrant: 0–90 `N <az>° E` · 90–180 `S <180−az>° E` ·
180–270 `S <az−180>° W` · 270–360 `N <360−az>° W`. Status phrase = largest
raw pull: N `HEADING IS TRUE NORTH` · E `DISTRACTING BUT USEFUL SIDEWORK
UNDERWAY` · W `COSTLY DRIFTING UNDERWAY` · S `HEADING IS TRUE SOUTH, COURSE
CORRECT`. Ties: the pull closest to the azimuth, then N, E, S, W. All zeros
or no heading block: draw no needle and print
`Heading: unscored — no pulls saved`.

The time model, never violated: the boxed middle item — TRUE NORTH — is the
true now and carries `▲ now`; items above it are ghost planks not yet laid;
items below are laid track with times. The needle tag is an instrument
readout, `Heading: <bearing> · <PHRASE>`, and never carries a time-word.

## Save through the writer

Never edit the saved Rail or Compass yourself. Write proposals to temporary
files. Then let the writer move the bytes.

When Rail changed:

```text
python3 "<absolute path to this skill>/scripts/chatrail.py" save \
  --compass /temporary/path/compass.md \
  --append /temporary/path/entry.md
```

When Compass changed but Rail did not:

```text
python3 "<absolute path to this skill>/scripts/chatrail.py" save \
  --compass /temporary/path/compass.md
```

Read the result. Say ChatRail saved only when the command says it saved.
`save` shape-checks the heading block and rejects a malformed one — fix the
quoted line and retry.

If the script reports a partial save, retry the same command; the exact Rail
entry will not be added twice. Compass is written first, so a partial save
means Compass is current but Rail is still old. If the retry fails, let the
turn end and tell the user what did and did not save. The Stop hook wakes
once; a second Stop passes, so ChatRail cannot trap the chat.

## Answer “Where are we?”

Say the lasting goal, what is truly behind, what is ahead, the next move, and
any unknown that can change the road. Use short human words. Do not dump file
text unless asked. When the user wants the picture, draw the panels.

The full build and release contract is in `references/spec.md`.
