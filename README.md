# agent-context

> **Status: dev & test mode.** Everything here is experimental and may change or break without notice.

Reusable context for coding agents (skills and related files), kept in one repo so it can be versioned and shared across projects.

## Layout

```
skills/
  guided-review/   # review a PR through pointed questions
```

## Skills

### guided-review

Invoked as `/guided-review <PR number or URL> [--dry-run]`.

Instead of reading an agent's report, the reviewer answers pointed questions on a local page, with the diff beside each one. A hidden subagent reviews the PR independently and writes its findings to a file kept out of the conversation. A one-shot local server (`serve.py`) serves `page.html`, collects the reviewer's answers, and exits. The agent then drafts a GitHub review from those answers: a body with finding counts and what nobody checked, plus one inline comment per must-fix or suggestion. It posts only after the reviewer approves the final text. `--dry-run` shows the draft without posting.

Files:

- `SKILL.md`: the skill instructions
- `page.html`: the review page
- `serve.py`: the one-shot local server

Requires `gh` (authenticated), `python3`, and Chrome (falls back to the default browser).

## Installing

Link a skill into your user-level skills directory:

```bash
ln -s ~/p/agent-context/skills/guided-review ~/.claude/skills/guided-review
```

`SKILL.md` runs `serve.py` from `~/.claude/skills/guided-review/`, so keep the link at that path.
