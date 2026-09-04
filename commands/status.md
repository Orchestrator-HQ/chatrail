---
description: Draw the full status — compass panel, then rail panel, stacked
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" read --thread-id "${CLAUDE_CODE_SESSION_ID}"`

Draw the compass panel, then the rail panel, stacked, following the drawing rules of /chatrail:compass and /chatrail:rail (styles in this skill's references/examples/). Compute the azimuth and status phrase with the SKILL.md math one-liner first — never eyeball them.
If the session has no tracked task: run the script's `recent` subcommand, show the list, and adopt only on the user's explicit words.
