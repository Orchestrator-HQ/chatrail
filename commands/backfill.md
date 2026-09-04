---
description: Rebuild the rail and compass from conversation history that already happened
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" read --thread-id "${CLAUDE_CODE_SESSION_ID}"`

Follow the "Retro-initialization" section of this plugin's chatrail SKILL.md. Its constraints, restated:

- Reconstruct only from the conversation you already hold. Do not re-read files to invent history.
- Write one Rail entry per lasting event, oldest first: the goal when it was set, each decision that stuck, each proof or correction that changed the road.
- Every entry's Basis quotes or points at words or tool output that actually happened, and is marked `(retro)`.
- An event you cannot trace to something real gets no entry.
- Planned-but-not-done items are not Rail entries. They go in the Compass under Ahead, as ghost planks.
- Finish with one full Compass including fresh four-pull scores.
- Save through the writer per SKILL.md "Save through the writer", one append per entry. Never hand-edit rail.md or compass.md.
- Then show the panels so the user can dispute the captured road.

Hold retro entries to a higher bar than live entries: fewer, only the spine of the work.

A session normally already has a task at this point: ChatRail welds each new session to the most recent road at session start, so backfill fills in that same road. Only when no task exists anywhere is the session genuinely task-less. In that case, do not show a menu — start a task and backfill it.
