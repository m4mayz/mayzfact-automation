# Top 3 playful CTA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accept the approved four-beat CTA with a bounded CTA-only budget and unchanged source/protected-audio behavior.

**Architecture:** Extend the existing shared `cta_beat_indices` contract instead of adding independent heuristics to consumers. Keep invitation token detection in cta.py, span detection and structural validation in narration.py, and total budget selection in steps/script.py.

**Tech Stack:** Python, Pydantic, pytest; offline fixture alignment and ffmpeg fixture frames only.

**Spec:** `docs/superpowers/specs/2026-11-02-top3-playful-cta-design.md`

## Global Constraints

- Original ranks 3/2/1, non-CTA wording and per-beat ≤10 words remain intact.
- CTA 1–4 beats, empty subject, point=false, contiguous immediately before Number one.
- Base speed-scaled budget + max(0, actual CTA words - 10); source mode unchanged.
- No TTS, render, upload, push, commit, production/audio changes, or brief startup.
- Existing paid-audio resume must not reapply pre-TTS budgets.

## Review Focus

- Triggerless transition/question beats cannot leak into item two explanations or inherit its subject.
- Detached/early/late invitation anchors cannot be hidden by the block detector.
- Descriptive like remains distinct from tapping like; no semantic claims are enforced via regex.
- Actual CTA delta is not speed-scaled twice and cannot exempt excess body words.
- Legacy source and locked-audio resume retain their original code paths.

### Task 1: Invitation and shared CTA block

**Files:** `mayzfact/cta.py`, `mayzfact/narration.py`, `tests/test_cta.py`, `tests/test_top3_script.py`.
**Interfaces:** preserve `cta_kinds(text) -> set[str]` and `cta_beat_indices(beats: list) -> list[int]` for dict/model beats.

- [x] Add failing test for exact `But before number one, try tapping like.` invitation, retain simile/opinion exclusions; run focused pytest (expected missing like), add minimal tapping support, rerun green.
- [x] Add failing detector test: exact four beats map to all four indices including the question; triggerless separate lead-in included; countdown boundary never bridged. Run (expected omitted indices), implement anchored per-section span, rerun green.
- [x] Add failing structural tests for accepting four beats and rejecting subject/point on CTA; update obsolete three-beat rejection fixture to five. Run RED, allow max four and validate CTA annotations, rerun all Top 3/script/CTA tests green.

### Task 2: Bounded budget and integrations

**Files:** `mayzfact/steps/script.py`, `tests/top3_fixtures.py`, `tests/test_top3_script.py`, `tests/test_top3_plan.py`, `tests/test_top3_timeline.py`; external `D:/akmal/_notes/tools/tests/test_top3_audit.py` if needed.
**Interfaces:** `narration_word_range(script, duration_s, video_speed=1.1) -> tuple[int,int,int]` consumes Task 1 detector; CLI/audit already consume it. Plan/timeline already consume detector.

- [x] Add failing budget test asserting old ten-word CTA tuple unchanged, approved 21-word CTA tuple `(91,87,95)` at 1.1x and `(84,81,87)` at 1.0x; actual total low/high boundary checks. Run RED, implement actual-word delta and adapt controlled fixture to ten-word baseline, rerun green.
- [x] Add compatibility tests for previous CTA wording, source mode budget, CLI shared target and unchanged body; add plan assertions on all four CTA beats, including no rank/subject/hook inheritance, plus timeline exact invitation token frames in spoken order before Number one. Run focused integration tests; only change production consumers if tests expose need.
- [x] Exercise operator audit on temporary roots for approved CTA and annotation failures, keeping source/pre-Top3 fallback tests. Reuse shared APIs; modify operator only if a real failing test proves incompatibility.

### Task 3: Documentation and verification

**Files:** `.agents/skills/bikin-short/SKILL.md`, `docs/DECISIONS.md` (D-046), `docs/HANDOFF.md`, previous Top 3 spec/plan supersession note.

- [x] Update active authoring limits, new style, example and exact budget formula; scope 30–40 seconds as baseline and report measured extension after authorized TTS. Historical design remains with an explicit supersession link.
- [x] Run `source /d/akmal/_notes/env.sh && uv run pytest`, external audit tests, Ruff F/I on changed Python files, `git diff --check`, and inspect complete diff in a separate review pass.
- [x] Record real RED/GREEN outputs, full-suite totals and uncertainties. Leave edits uncommitted for parent review.
