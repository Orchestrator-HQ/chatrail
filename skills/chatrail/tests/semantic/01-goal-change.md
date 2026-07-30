# Case 1: User changes the goal

## Case input

Mode: Root Stop review.

Latest user words:

```text
Drop CSV export. The main goal is now PDF invoice import.
```

Useful tool proof: None.

Rail:

```markdown
# Rail

## Entry: CSV export chosen

Basis: "Build CSV export first."

Meaning: CSV export is the user-approved main goal.
```

Compass:

```markdown
# Compass

## Current heading

Build CSV export.

## Relation to the latest user-approved direction

This is the main goal.

## Behind us

The CSV fields were named.

## Ahead

Write the CSV exporter.

## Unclear

Nothing material.
```

## Pass signs

- `ACTION` is exactly `SAVE_RAIL_AND_COMPASS`.
- `ENTRY` has the exact Rail entry shape.
- `Basis` includes the user's goal-change words, not an invented tool claim.
- `Meaning` makes PDF invoice import the new user-approved main goal.
- `COMPASS` has every required heading and points at PDF invoice import.
- Old CSV work stays visible as old or behind. It is not erased or still main.
- `RETURN` is exactly `NONE`.
