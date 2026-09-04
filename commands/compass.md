---
description: Draw the compass panel — heading, needle, and rail context for this task
---
!`python3 "${CLAUDE_PLUGIN_ROOT}/skills/chatrail/scripts/chatrail.py" read --thread-id "${CLAUDE_CODE_SESSION_ID}"`

Draw the compass panel fresh from the reading above, imitating references/examples/compass.txt in this plugin's chatrail skill exactly in style. Before drawing, compute the azimuth and status phrase with the math one-liner in SKILL.md "Draw the panels" — never eyeball the angle or phrase.
If the session has no tracked task: run the script's `recent` subcommand, show the list, and adopt only on the user's explicit words.
