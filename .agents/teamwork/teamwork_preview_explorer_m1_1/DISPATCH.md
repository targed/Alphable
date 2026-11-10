# Dispatch for M1 Explorer (Code Remediation Plan)

**Task**: Formulate the exact implementation and test strategy for Milestone M1 (Code Remediation & Bug Fixes).
**Scope**: 
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md` and `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_1/handoff.md`.
Formulate exact patch specifications for:
1. BUG-01: C heap memory leak in `alphable_v4/engine/magpie_bindings.py` (freeing output and error strings).
2. BUG-02: Pre-endgame parity neutralization in `alphable_v4/search/bams.py` and `alphable_v4/engine/move.py`.
3. BUG-03: Woogles bot pass command formatting in `alphable_v4/platform/woogles_bot.py`.
4. BUG-04: Volatility formula jump discontinuity in `alphable_v4/search/bams.py`.
5. BUG-05: Coordinate range validation in `alphable_v4/engine/move.py`.
6. BUG-06: Sign inversion in alternating tournament mode in `alphable_v4/cli.py`.
7. BUG-07: Phase telemetry instrumentation in `alphable_v4/platform/eval.py` / `alphable_v4/cli.py`.
Define exact test execution commands ensuring all 57 core unit tests and 20 visualizer tests pass cleanly under pure CPU mode.
**Output**: Write the plan to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/handoff.md`.


## 2026-11-09T22:34:59Z
You are the M1 Explorer for Milestone M1 (Code Remediation & Bug Fixes).
Your working directory is `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/`.
Your parent orchestrator is conversation ID `d0ac5384-dff3-498c-b189-b11d798c2489`.

MANDATORY FIRST STEP: Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md`.
Read your dispatch file at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/DISPATCH.md`.
Read `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_1/handoff.md`.

YOUR MISSION:
1. Formulate exact file-by-file patch specifications and line-level instructions for Worker implementation on:
   - BUG-01: C heap memory leak in `alphable_v4/engine/magpie_bindings.py` (freeing output strings with `magpie_free_string` via `c_void_p` wrapper).
   - BUG-02: Pre-endgame parity neutralization in `alphable_v4/search/bams.py` and `alphable_v4/engine/move.py` (ensure `tiles_played` is accurately calculated and `tiles_placed` correctly preserved).
   - BUG-03: Woogles bot pass formatting in `alphable_v4/platform/woogles_bot.py` (checking `move.is_pass or move.word in ("--", "pass")`).
   - BUG-04: Volatility formula discontinuity in `alphable_v4/search/bams.py` (continuous linear/sigmoid ramp without 50% step at ±20).
   - BUG-05: Coordinate range validation in `alphable_v4/engine/move.py` (rejecting coordinates outside 1-15, A-O).
   - BUG-06: Sign inversion in alternating tournament mode in `alphable_v4/cli.py:878-881`.
   - BUG-07: Phase telemetry instrumentation in `alphable_v4/platform/eval.py` / `alphable_v4/cli.py` to tag moves and compute phase score spreads (Opening, Midgame, Pre-endgame, Endgame).
2. Specify exact unit tests to add or run to verify each fix, confirming all 57 core unit tests and 20 visualizer tests pass cleanly under pure CPU mode (`CUDA_VISIBLE_DEVICES=""`).
3. Write your detailed handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_m1_1/handoff.md`.
4. Send a message to your parent orchestrator when complete.
