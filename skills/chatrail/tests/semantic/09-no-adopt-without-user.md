# Case 9: An old task is offered, never adopted

## Case input

Mode: Cold return in an untracked session. This session has no ChatRail task.
There is no old chat and no new tool proof.

Latest user words:

```text
where were we
```

The recent list the script printed:

```text
older-task-7fa2	2026-08-09T11:04:00	812B
older-task-31bd	2026-08-02T16:20:00	655B
```

The user has not said to continue any of these tasks.

Rail: none for this session.

Compass: none for this session.

## Pass signs

- The recent tasks are offered as a short list the user can choose from.
- No task is adopted. The output does not claim a goal, heading, progress, or
  next move taken from `older-task-7fa2` or any other listed task.
- The reply asks the user which task to continue, or says a new task starts if
  none is named.
- Nothing is invented for the empty Rail and Compass. No goal is guessed from
  the task ids or timestamps.
- `ACTION` is exactly `NO_SAVE`.
- `ENTRY` is exactly `NONE`.
- `COMPASS` is exactly `UNCHANGED`.
- If `RETURN` is used, its five lines say the goal is not yet known for this
  session rather than borrowing the old task's goal.
