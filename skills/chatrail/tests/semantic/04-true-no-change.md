# Case 4: True no-change

## Case input

Mode: Root Stop review.

Latest user words:

```text
Okay.
```

Assistant words:

```text
CSV fields that contain commas use quotes.
```

Useful tool proof: None.

Rail:

```markdown
# Rail

## Entry: Fix the missing invoice

Basis: "expected 4 invoices, got 3"

Meaning: PDF invoice import is not ready to ship.
```

Compass:

```markdown
# Compass

## Current heading

Fix the missing fourth invoice.

## Relation to the latest user-approved direction

This is needed before PDF invoice import can ship.

## Behind us

The test proved that only three of four invoices import.

## Ahead

Find the dropped invoice, fix it, and rerun the test.

## Unclear

Why the fourth invoice is dropped.
```

## Pass signs

- `ACTION` is exactly `NO_SAVE`.
- `ENTRY` is exactly `NONE`.
- `COMPASS` is exactly `UNCHANGED`.
- The assistant's explanation does not become task history.
- The model does not rewrite Compass just to make the words newer or nicer.
- `RETURN` is exactly `NONE`.
