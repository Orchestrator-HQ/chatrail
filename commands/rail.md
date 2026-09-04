---
description: Draw the rail panel — the task's timeline, newest at top
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" read --thread-id "${CLAUDE_CODE_SESSION_ID}"`

Draw the rail panel fresh from the reading above, imitating references/examples/rail.txt in this plugin's chatrail skill exactly in style: ghosts above, the boxed TRUE NORTH item carrying `▲ now`, laid track with times below.
If the session has no tracked task: run the script's `recent` subcommand, show the list, and adopt only on the user's explicit words.
