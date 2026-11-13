---
name: maintain-project-case-study
description: Maintain the logistics voice-agent resume and interview case study before a milestone push. Use when a project phase is complete and commits are being prepared for push, or when verified implementation, testing, runtime evidence, risks, or architecture decisions materially change.
---

# Maintain the project case study

Keep `docs/PROJECT_CASE_STUDY_ZH.md` aligned with the repository's real, current evidence so it remains useful for resumes and technical interviews.

## When to update

Run this maintenance pass before a milestone push after a meaningful phase completes. Update the document only when at least one of these changed:

- implemented behavior, architecture, configuration, dependency, or safety boundary;
- automated test, simulation, smoke-test, UI, audio, or human-acceptance evidence;
- diagnosed root cause, rejected alternative, operational lesson, known risk, or next step;
- a quantitative result or claim that is now stale.

Do not add an entry for routine discussion, formatting-only work, or commits that add no durable project or interview value.

## Evidence workflow

1. Read the workspace `HANDOFF.md`, the pending push range, and the relevant source, tests, logs, and documentation. Never read or reproduce credential values.
2. Determine the exact milestone delta since the last pushed revision. Prefer verified repository evidence over recollection.
3. Update the most relevant existing section instead of appending a chronological diary. Add a new problem section only when it represents a distinct engineering challenge.
4. For each material issue, preserve this reasoning chain where applicable: symptom, evidence, root cause, alternatives considered, chosen solution, implementation boundary, verification, remaining risk, and interview value.
5. Refresh resume bullets, metrics, interview questions, STAR material, code references, and the unresolved-work section only when the new phase changes them.
6. Reconcile conflicts immediately. Remove or correct claims that no longer match the code or current runtime state.

## Truth and safety rules

- Distinguish `implemented`, `automatically verified`, `human verified`, and `not yet verified` explicitly.
- Never turn a small sample into a general accuracy claim. Retain sample size and test conditions with quantitative results.
- Do not claim deployment, production readiness, or end-to-end validation without direct evidence.
- Do not include secrets, environment values, customer data, private recordings, or unnecessary absolute local paths.
- Describe failures and rejected approaches constructively; do not hide unresolved risks for resume polish.
- Preserve exact commit IDs, run IDs, test counts, and timings only after verifying them. Replace stale values rather than accumulating contradictory history.

## Pre-push validation

Before the push is considered ready:

1. Run checks proportional to the milestone and record only checks that actually ran.
2. Run `git diff --check` and scan the case-study diff for credential-like values and private data.
3. Review the full pending push range and verify that the case study describes all interview-worthy changes without overstating them.
4. Update the root `HANDOFF.md` when project state or evidence changed, following its retention rules.
5. Commit the documentation update with the milestone or as a separate documentation checkpoint. A push remains an external action and still requires the user's authorization.

The canonical case study is `docs/PROJECT_CASE_STUDY_ZH.md`; the README should retain a discoverable link to it.
