# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout: single-context

This repo is **single-context**: one shared vocabulary for the whole repository, so there is exactly one `GLOSSARY.md` at the repo root and architecture decisions live in `docs/adr/` at the repo root. There is no `GLOSSARY-MAP.md`, and no per-subproject `GLOSSARY.md` — do not introduce them unless the repo is re-initialised as multi-context.

Neither file exists yet. That is expected: this setup deliberately did not create `GLOSSARY.md` or `docs/adr/`. They are created lazily by `/domain-modeling` (reached via `/grill-with-docs` and `/improve-codebase-architecture`) the first time a term or decision is actually written down.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root (single-context: the only glossary).
- **`docs/adr/`**: read ADRs that touch the area you're about to work in.

If either doesn't exist, **proceed silently**. Don't flag its absence; don't suggest creating it upfront.

## File structure

```
/
├── GLOSSARY.md              ← created on first term, not by setup
├── docs/
│   ├── adr/                 ← created on first decision, not by setup
│   │   ├── 0001-....md
│   │   └── 0002-....md
│   └── agents/              ← this setup's output
└── ... (music.py, tools/, 分轨/, 成品/, 字幕/, 文档/ ...)
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
