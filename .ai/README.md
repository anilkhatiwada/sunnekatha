# AI Team Quick Start

`AGENTS.md` is the single source of truth. The files here only provide reusable
invocation prompts; tool folders contain thin launchers.

The active project is SunneKatha. Read its product scope, stack, architecture,
design system, milestones, and current implementation status from `AGENTS.md`
before invoking a role.

## Standard workflow

1. Invoke Architect with the task. Save or retain its structured output.
2. Give the task and Architect output to Engineer.
3. Give the task, plan, Engineer handoff, and diff to Reviewer.
4. If Reviewer requests changes, return to Engineer and repeat review.

For very small changes, run all three stages in one conversation and keep each
stage brief. A request such as the following works in any assistant:

```text
Follow AGENTS.md. Run the Architect → Engineer → Reviewer workflow for:
<task>
Keep each stage explicit and pause only for blocking decisions.
```

## Tool entry points

- Codex: ask for a role by name or use the all-stage prompt above.
- Claude Code: `/architect`, `/engineer`, `/reviewer`, or `/team`.
- Gemini CLI: `/architect`, `/engineer`, `/reviewer`, or `/team`.
- GitHub Copilot Chat: use the prompt files named `architect`, `engineer`,
  `reviewer`, and `team` where prompt files are supported; otherwise paste the
  all-stage prompt above.
- Antigravity: `/architect`, `/engineer`, `/reviewer`, or `/team`.

Role outputs follow the chainable stage schema in `AGENTS.md`. Paste the previous
stage's output where a launcher asks for it.
