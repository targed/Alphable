# Dispatch for M1 Challenger 2

**Task**: Empirically verify pre-endgame parity logic, Woogles bot pass formatting, alternating tournament margin calculations, and phase telemetry.
**Scope**:
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md` and `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read Worker handoff at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m1_1/handoff.md`.
Construct stress tests and empirical tests:
- Parity logic: verify candidate moves with bag counts 1..5 receive appropriate parity adjustments when emptying or holding tiles.
- Woogles pass formatting: verify `make_pass()` outputs `"pass"`, never `"exchange pass"`.
- Alternating tournament: simulate alternating matches and confirm spread signs match game outcome.
- Phase telemetry: run a multi-game duplicate simulation and confirm all 4 phases are populated with non-zero stats.
Determine verdict: APPROVE or REQUEST_CHANGES.
Write report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_challenger_m1_2/handoff.md`.

## 2026-11-09T22:54:05Z
You are M1 Challenger 2 for Milestone M1 (Code Remediation & Bug Fixes).
Your working directory is `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_challenger_m1_2/`.
Your parent orchestrator is conversation ID `d0ac5384-dff3-498c-b189-b11d798c2489`.

MANDATORY FIRST STEP: Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md`.
Read your dispatch file at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_challenger_m1_2/DISPATCH.md`.
Read `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read Worker handoff at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m1_1/handoff.md`.

YOUR MISSION:
1. Empirically verify BUG-02 (parity tempo), BUG-03 (Woogles pass format), BUG-06 (alternating tournament margin), BUG-07 (phase telemetry):
   - Verify `cand.get_tiles_played()` correctly returns tile counts and triggers parity bonuses when `bag_count <= 5`.
   - Verify pass formatting across multiple scenarios.
   - Run duplicate match simulations and verify alternating matches produce mathematically consistent margins (`p1_scores - p2_scores`).
   - Verify all 4 game phases are populated in `MatchStats.phase_scores` with non-empty move histories.
2. Record your explicit verdict: APPROVE or REQUEST_CHANGES.
3. Write your handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_challenger_m1_2/handoff.md`.
4. Send a message to your parent orchestrator with your verdict.
