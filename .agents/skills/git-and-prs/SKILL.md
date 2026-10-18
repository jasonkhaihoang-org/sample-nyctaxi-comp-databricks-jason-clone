---
name: git-and-prs
description: "Use when committing, naming a branch or writing a pull request description."
---

# Git and pull requests

## Commits (G4)

- Subject: `<type>: <what changed>`, lowercase, no full stop. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.
- One concern per commit. Stage named files, never `git add .`.
- Commit a model's SQL together with its properties YAML.

## Pull requests (G5)

The body has four sections, each stating "None" when empty:

1. `## Summary`
2. `## Verification`: the commands run and their results.
3. `## Approved contract changes`
4. `## Remaining manual checks`
