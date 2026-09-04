---
description: Show recent ChatRail tasks and delete only the one the user names
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" recent`

Show the list above. Delete only a target the user names, with the matching flag: a task → `clean --thread-id <id>`; orphaned aliases → `clean --aliases`; the old ~/.codex pile → `clean --legacy`. Never delete anything the user did not name.
