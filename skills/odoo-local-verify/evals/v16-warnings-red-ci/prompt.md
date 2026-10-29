---
tags: [odoo-local-verify]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

el ci/odoo.sh (dev) me quedó amarillo en mi PR de cashea-odoo (v16), reproducilo en local con --stop-after-init y fijate qué warnings salen
