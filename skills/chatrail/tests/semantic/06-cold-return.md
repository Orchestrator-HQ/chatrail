# Case 6: Cold return from files only

## Case input

Mode: Cold return. There is no old chat, latest user message, or new tool
proof. Read only the two files below. State where the task stands.

Rail:

```markdown
# Rail

## Entry: PDF import chosen

Basis: "The main goal is now PDF invoice import."

Meaning: PDF invoice import is the user-approved main goal.

## Entry: One invoice is still missing

Basis: "FAIL test_pdf_import: expected 4 invoices, got 3"

Meaning: The import is not ready to ship. Fresh proof corrected the old green claim.
```

Compass:

```markdown
# Compass

## Current heading

Fix the missing fourth invoice.

## Relation to the latest user-approved direction

This is the blocker before PDF invoice import can ship.

## Behind us

The PDF goal was chosen. The test now reproduces one missing invoice.

## Ahead

Trace where the fourth invoice drops, make the smallest fix, and rerun the test.

## Unclear

Why the fourth invoice is dropped.
```

## Pass signs

- `ACTION` is exactly `NO_SAVE`.
- `ENTRY` is exactly `NONE`.
- `COMPASS` is exactly `UNCHANGED`.
- `RETURN` states the PDF import goal, the reproduced failure, and the blocker.
- `RETURN` says the next move is to trace and fix the missing invoice, then test.
- `RETURN` names the drop cause as unclear.
- It does not say the product is green, approved to release, or already shipped.
