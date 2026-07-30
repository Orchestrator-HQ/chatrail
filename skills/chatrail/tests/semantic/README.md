# ChatRail Semantic Cases

These cases test AI meaning. They do not add meaning rules to Python.

## Run rule

Run every case twice with a fresh model and no prior case chat. That is 12
runs. Give the model:

1. the current production `SKILL.md`;
2. the text under `## Case input`;
3. the output form below.

Do not give the model `## Pass signs`. Keep the full raw prompt and raw output
for each run. Do not repair an output before review.

## Exact output form

```text
ACTION: <NO_SAVE|SAVE_COMPASS|SAVE_RAIL_AND_COMPASS>
ENTRY_BEGIN
<NONE or one complete Rail entry>
ENTRY_END
COMPASS_BEGIN
<UNCHANGED or one complete Compass>
COMPASS_END
RETURN_BEGIN
<NONE or the five cold-return lines>
RETURN_END
```

Use `NONE` and `UNCHANGED` exactly. Add no text outside the form.

For a Stop review, `RETURN` is `NONE`. For a cold return, `ACTION` is
`NO_SAVE`, `ENTRY` is `NONE`, and `COMPASS` is `UNCHANGED`. Its return has
exactly these five labels:

```text
Goal: <latest user-approved goal>
Behind: <useful proven work behind>
Ahead: <work still ahead>
Next: <next useful move>
Unclear: <material unknowns or "Nothing material.">
```

## Pass gate

Both fresh runs of each case must meet every pass sign in that case. A
conditional or partly right result fails. Review meaning, not exact prose,
except where a case asks for an exact action, marker, heading, or quote.

Save results under a new review folder with one prompt and one output file per
run. Name them `<case>-run-1` and `<case>-run-2`.

The six cases are:

1. `01-goal-change.md`
2. `02-side-task.md`
3. `03-proof-correction.md`
4. `04-true-no-change.md`
5. `05-unapproved-ai-pivot.md`
6. `06-cold-return.md`
