---
name: maintain-handoff
description: Maintain the workspace HANDOFF.md as a compact current-state snapshot when project state, verification, risks, or next steps change. Use before every HANDOFF.md update; do not use it to keep a chronological project log.
---

# Maintain the handoff

Keep the workspace-root `HANDOFF.md` cheap to cold-read and sufficient to resume the next concrete work unit. It is an operational cache, not the system of record.

## Update gate

Update only when code, configuration, dependencies, verification evidence, runtime state, risks, or next steps changed. Discussion and rule-only edits do not justify adding project-status prose.

Before editing, verify the current Git state and the facts affected by the latest work. Never copy credentials or private data.

## Rewrite, do not append

For every new fact, find the older fact it supersedes and replace or delete it in the same edit. Merge related evidence into one current statement. Do not add dated diary entries merely because work happened.

Retain information in this order:

1. current repository, branch, HEAD, remote divergence, and uncommitted state;
2. current architecture, defaults, safety invariants, and runtime availability needed to work safely;
3. latest effective automated and human verification;
4. unresolved risks that change the next decision;
5. three to five ordered next actions and essential file entry points.

Move durable history, root-cause narratives, superseded A/B results, old commit ranges, and interview material to `docs/PROJECT_CASE_STUDY_ZH.md`, another relevant project document, or Git history. Do not duplicate those details in `HANDOFF.md`.

## Size budget

The completed file must stay within both limits:

- at most 120 lines;
- at most 6000 non-whitespace characters.

Use no more than five bullets under recent verification and no more than five numbered next steps. If a fact can be recovered quickly from Git, tests, or a linked document and does not affect the next action, omit it.

## Required shape

Prefer these compact sections:

- current state;
- current behavior and safety boundaries;
- latest verification;
- unresolved risks;
- next steps;
- entry points.

Do not repeat workspace rules already present in `AGENTS.md`.

## Final audit

After editing:

1. compare every statement with current repository/runtime facts;
2. remove contradictions, superseded states, and repeated claims;
3. count lines and non-whitespace characters and compress again if either budget is exceeded;
4. confirm a fresh agent can identify the next safe work unit without reading history;
5. report the resulting size when handing off.
