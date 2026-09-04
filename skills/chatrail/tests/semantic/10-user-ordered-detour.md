# Case 10: The user's own words ordered the detour

## Case input

Mode: Root Stop review.

Latest user words:

```text
Pause the PDF work — the login is broken in prod, fix it first.
```

Useful tool proof:

```text
git diff --stat
 src/auth/session.py   |  41 ++++++++----
 1 file changed, 29 insertions(+), 12 deletions(-)

PASS test_login_session_refresh
prod check: POST /login -> 200
```

Latest agent thought:

```text
This turn fixed the production login bug the user ordered. Nothing was
written for PDF import this turn.
```

Rail:

```markdown
# Rail

## Entry: PDF import chosen

Basis: "The main goal is now PDF invoice import."

Meaning: PDF invoice import is the user-approved main goal.
```

Compass:

```markdown
# Compass

## Current heading

Build PDF invoice import end to end.

## Relation to the latest user-approved direction

This is the main goal.

## Behind us

The PDF goal was chosen.

## Ahead

Extract PDF text, then confirm the parsed invoices.

## Unclear

The PDF layouts are not known.
```

## Pass signs

- No drift alarm. The output contains no `Off course:` line and no line that
  tells the user the work no longer matches the approved direction — the
  user's own words ordered this detour.
- `ACTION` is `SAVE_COMPASS` or `SAVE_RAIL_AND_COMPASS`.
- `COMPASS` records the detour: the current heading or its relation section
  says the login fix was done on the user's order while the goal stayed.
- PDF invoice import stays the user-approved main goal. The login fix is not
  promoted to the goal, and the pause is not read as dropping PDF import.
- The user is not scolded, warned, or asked to re-approve their own order.
- `RETURN` is exactly `NONE`.
