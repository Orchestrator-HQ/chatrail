---
description: Start or attach a ChatRail task, optionally named; resumes a paused task
argument-hint: "[name]"
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" on $ARGUMENTS --session-id "${CLAUDE_CODE_SESSION_ID}"`

Relay the script's one output line verbatim. It says whether the task was created or attached — do not paraphrase it.
