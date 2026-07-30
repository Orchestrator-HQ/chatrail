---
name: chatrail
description: Keep a long root Codex task pointed at the user's real goal after compaction, interruption, or time away. Use when ChatRail wakes a Stop review, when the user names ChatRail, or when someone asks where the work stands.
---

# ChatRail

ChatRail gives one Codex task a road that chat history cannot erase.

It has two meaning files and one lock:

- `rail.md` is the lasting road. Old entries never change.
- `compass.md` says where the work points now.
- `.<thread-id>.lock` keeps two saves from crossing.

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

The command prints Rail and Compass. It makes no saved change.

Read the words as a whole. Do not turn the task into fixed states, scores,
degrees, or labels. The user may change the goal. A short side task may leave
the goal alone. New proof may show that an old progress note was wrong.

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

Use plain, exact words. Keep Compass short enough to scan. Do not hide needed
detail.

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

If the script reports a partial save, retry the same command. The exact Rail
entry will not be added twice. Compass is written first. A partial save means
Compass is current but Rail is still old. If the retry fails, let the turn end
and tell the user what did and did not save.

The Stop hook wakes once. A second Stop passes, so ChatRail cannot trap the
chat.

## Answer “Where are we?”

Say:

- the lasting goal;
- what is truly behind;
- what is ahead;
- the next move;
- any unknown that can change the road.

Use short human words. Do not dump file text unless asked.

The full build and release contract is in `PLUGIN-SPEC.md`.
