# Visualizer Studio 2.5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the visualizer UI with a distinctive championship salon aesthetic (`frontend-design`), add full AI vs AI live match play, duplicate position decision swapping, manual turn undo/rewind, and bag inventory inspection.

**Architecture:** Extended React state model tracking a turn-history snapshot stack for zero-overhead undo/branching, coupled with modular modals for bag inspection and duplicate comparisons. Refactored CSS design system replacing generic dark SaaS tokens with tactile wooden/parchment tournament styling.

**Tech Stack:** React 18, TypeScript, CSS3, Flask REST API.

**Spec:** [`docs/superpowers/specs/2026-10-26-visualizer-redesign-spec.md`](file:///home/targed/Documents/Git/Alphable/docs/superpowers/specs/2026-10-26-visualizer-redesign-spec.md)

---

### Task 1: Type Definitions & Domain Model Extensions
- Files:
  - Modify: `visualizer/frontend/src/types.ts`
- Add: `GameSnapshot`, `DuplicateDecision`, `BagDistribution`.

### Task 2: Design System & CSS Overhaul (`frontend-design`)
- Files:
  - Modify: `visualizer/frontend/src/index.css`
- Replace generic palette with deep walnut `#141210`, warm charcoal surfaces `#201c18`, rich tournament green board `#163324`, and tactile boxwood tiles.
- Improve typography, spacing, active turn halos, and modal animations.

### Task 3: Bag Inspector Modal & Duplicate Decision Modal
- Files:
  - Create: `visualizer/frontend/src/components/BagModal.tsx`
  - Create: `visualizer/frontend/src/components/DuplicateModal.tsx`
- Implement visual unseen tile breakdown and side-by-side duplicate play decision explorer.

### Task 4: Arena Match Controls & Player Setup
- Files:
  - Create: `visualizer/frontend/src/components/ArenaControls.tsx`
  - Modify: `visualizer/frontend/src/components/PlayerHUD.tsx`
  - Modify: `visualizer/frontend/src/components/EngineSelector.tsx`
- Support selecting any two players (Human or AI), step-by-step next move, auto-play with speed slider, pause, undo move, duplicate swap, and reset.

### Task 5: App Component Orchestration & Undo Stack
- Files:
  - Modify: `visualizer/frontend/src/App.tsx`
- Implement turn snapshot stack (`historyStack`) allowing unlimited undo and branch rewinding.
- Implement AI vs AI match loop with cancellation safety.
- Wire duplicate position comparison and bag modal.

### Task 6: Frontend Build & Verification
- Compile production bundle: `npm run build` in `visualizer/frontend/`.
- Run visualizer backend test suite and E2E checks: `pytest visualizer/tests/ -v`.
