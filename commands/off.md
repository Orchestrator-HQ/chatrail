---
description: Pause ChatRail for this session's task; all saved history is kept
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" pause --thread-id "${CLAUDE_CODE_SESSION_ID}"`

Relay the script's output verbatim. Tell the user the rail and compass are kept, and /chatrail:on resumes the task.
