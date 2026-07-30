# Case 3: Fresh proof corrects old progress

## Case input

Mode: Root Stop review.

Latest user words:

```text
Check the test result before we move on.
```

Useful tool proof:

```text
FAIL test_pdf_import: expected 4 invoices, got 3
```

Rail:

```markdown
# Rail

## Entry: PDF tests passed

Basis: "12 tests passed"

Meaning: PDF invoice import is green and ready to ship.
```

Compass:

```markdown
# Compass

## Current heading

Ship PDF invoice import.

## Relation to the latest user-approved direction

The build is done.

## Behind us

All PDF tests passed.

## Ahead

Publish the release.

## Unclear

Nothing material.
```

## Pass signs

- `ACTION` is exactly `SAVE_RAIL_AND_COMPASS`.
- `ENTRY` has the exact Rail entry shape and uses the failing tool line as basis.
- The entry corrects the old green claim without deleting or rewriting it.
- `COMPASS` has every required heading and does not call the build done.
- Ahead says to fix or study the missing invoice before release.
- `RETURN` is exactly `NONE`.
