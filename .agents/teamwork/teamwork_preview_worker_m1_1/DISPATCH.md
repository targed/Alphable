# Dispatch for M1 Worker (Code Remediation Implementation)

**Task**: Implement BUG-01 through BUG-07 fixes according to the detailed patch specifications in `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/handoff.md`.
**Files Owned**:
- `alphable_v4/engine/magpie_bindings.py` (BUG-01: C memory leak fix via `_take_string` and `magpie_free_string`)
- `alphable_v4/engine/move.py` (BUG-02: tiles_placed preservation and BUG-05: coordinate range validation)
- `alphable_v4/search/bams.py` (BUG-02: tiles_played evaluation and BUG-04: continuous volatility ramp)
- `alphable_v4/platform/woogles_bot.py` (BUG-03: pass formatting fix)
- `alphable_v4/platform/eval.py` (BUG-07: game phase categorization and phase score tracking)
- `alphable_v4/cli.py` (BUG-06: alternating tournament margin fix and BUG-07: phase telemetry logging)
- `tests/engine/test_bug_fixes.py` (Dedicated regression test suite verifying BUG-01 through BUG-07)

**Mandatory Integrity Warning**:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

**Verification Command**:
`CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/ -v`
`CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest visualizer/tests/ -v`

**Output**: Write completion report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m1_1/handoff.md`.

## 2026-11-09T22:42:47Z
You are the M1 Worker for Milestone M1 (Code Remediation & Bug Fixes: BUG-01 through BUG-07).
Your working directory is `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m1_1/`.
Your parent orchestrator is conversation ID `d0ac5384-dff3-498c-b189-b11d798c2489`.

MANDATORY FIRST STEP: Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md`.
Read your dispatch file at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m1_1/DISPATCH.md`.
Read `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read the detailed patch specifications in `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR MISSION:
1. Implement the exact code changes specified in `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/handoff.md` across the files you own:
   - `alphable_v4/engine/magpie_bindings.py`: BUG-01 C memory leak fix via `_take_string(ptr)` and `magpie_free_string(ptr)`.
   - `alphable_v4/engine/move.py`: BUG-02 preserve `tiles_placed` in `from_ucgi_line` and provide `get_tiles_played()`; BUG-05 coordinate range validation in `parse_coordinate`.
   - `alphable_v4/search/bams.py`: BUG-02 calculate `tiles_played = cand.get_tiles_played()`; BUG-04 continuous symmetrical volatility ramp.
   - `alphable_v4/platform/woogles_bot.py`: BUG-03 fix pass move formatting to output `"pass"`.
   - `alphable_v4/platform/eval.py`: BUG-07 add `get_game_phase()`, track `phase_scores` and `phase_counts` in `GameSimulator.play_game()`.
   - `alphable_v4/cli.py`: BUG-06 fix alternating tournament sign inversion (`margin = s1 - s2`); BUG-07 log phase telemetry in tournament output.
2. Create `tests/engine/test_bug_fixes.py` with comprehensive unit tests directly exercising and verifying BUG-01 through BUG-07 fixes.
3. Run the full test suites:
   `CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/ -v`
   `CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest visualizer/tests/ -v`
   Verify that all 57 existing unit tests + your new bug fix tests pass 100% cleanly without regressions.
4. Write your completion report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m1_1/handoff.md`.
5. Send a message to your parent orchestrator with your results and test outputs.
