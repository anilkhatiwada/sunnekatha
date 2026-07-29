---
description: Run Architect, Engineer, and Reviewer in sequence
---

# AI Engineering Team

1. Read `/AGENTS.md` and all templates in `/.ai/personas/`.
2. Run the user's task through Architect and retain its structured handoff.
3. Run Engineer against that handoff and retain its implementation handoff.
4. Run Reviewer against the task, handoffs, actual diff, and validation evidence.
5. If review has blocking findings, return to Engineer for focused fixes and
   review again.
6. Keep every stage explicit and chainable. Pause only for decisions that
   `AGENTS.md` says require the developer.
