# Azure DevOps PM/EA Agent

This repository treats [CLAUDE.md](C:\Users\yingkiat.gan\Documents\Work\azure-devops-pm-agent\CLAUDE.md) as the canonical operating guide.

If your coding tool prefers `AGENTS.md`, use this file as the entry point and follow `CLAUDE.md` for the full project instructions, workflows, and conventions.

## Canonical Rule

- `CLAUDE.md` is the primary instruction file for this repo.
- `AGENTS.md` exists for tool compatibility.
- When updating shared repo operating rules, update `CLAUDE.md` first.
- Keep `AGENTS.md` aligned with `CLAUDE.md` when cross-tool behavior matters.

## Standing Conventions

- Always fix regenerable issues at the source artifact first.
- For diagram and portal work, source usually means the YAML spec, template, prompt, or generator code.
- Do not default to patching generated outputs such as SVG, draw.io exports, or built portal files unless a one-off patch is explicitly intended.
- If an issue is likely to recur, record the rule in source guidance so future artifacts inherit the fix.
