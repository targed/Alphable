# Dispatch for M3 Worker (MAGPIE Ceiling & Parameter Rigor Investigation)

**Task**: Execute the empirical investigation of Base MAGPIE configuration, parameter ceiling, and generator transferability for Milestone M3 (Requirement R2).
**Scope**:
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md` and `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read Survey 2 handoff at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/handoff.md`.

**Deliverables**:
1. Investigate unturned native MAGPIE parameters, flags, leave tables, and runtime options (`-pat CSW24`, `-wmp`, simulation lookahead via PlayChooser/simmer, PEG solver, endgame alpha-beta depth).
2. Run empirical tournament simulations comparing:
   - Default Base MAGPIE (1-ply static KLV)
   - Maximally tuned Base MAGPIE (with PAT / enhanced evaluation)
   - Alphable V4
3. Empirically test and verify generator enhancement transfer: evaluate whether improvements to MAGPIE's parameters (e.g. `-pat CSW24`) directly transfer to Alphable V4 as its candidate move generator and 2-ply counterplay simulator.
4. Quantify the exact performance delta and ceiling in spread and win-rate terms.
5. Save raw structured empirical benchmark data to `data/audit/m3_magpie_ceiling.json`.
6. Write full handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m3_1/handoff.md`.

**Mandatory Integrity Warning**:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-11-09T23:03:26Z
You are the M3 Worker for Milestone M3 (Base MAGPIE Parameter Ceiling & Transferability - Requirement R2).
Your working directory is `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m3_1/`.
Your parent orchestrator is conversation ID `d0ac5384-dff3-498c-b189-b11d798c2489`.

MANDATORY FIRST STEP: Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md`.
Read your dispatch file at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m3_1/DISPATCH.md`.
Read `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR MISSION:
1. Investigate Base MAGPIE configuration options and ceiling:
   - Analyze unturned parameters in `vendor/magpie/`: Positional Adjustment Term (`-pat CSW24`), Winning Margin Play (`-wmp`), PIMC multi-ply simulation lookahead (PlayChooser), Pre-Endgame solver, and endgame search depth.
   - Quantify the empirical performance delta between 1-ply static KLV and tuned MAGPIE.
2. Run empirical duplicate tournament benchmark games comparing:
   - Default Base MAGPIE (1-ply static KLV)
   - Maximally tuned Base MAGPIE
   - Alphable V4
3. Verify generator enhancement transfer:
   - Test whether supplying tuned parameters (e.g. `-pat CSW24`) to MAGPIE improves Alphable V4's candidate move generation and 2-ply counterplay rollouts.
4. Save structured benchmark data to `data/audit/m3_magpie_ceiling.json`.
5. Write your comprehensive handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m3_1/handoff.md`.
6. Send a message to your parent orchestrator with your findings.


## 2026-11-09T23:51:58Z
**Context**: Milestone M3 empirical benchmark execution
**Content**: We observed that background task-276 has been executing Matchup 4 (`v4-pat` vs `latest`, 25 pairs with full un-overridden 2-ply BAMS search) for ~25 minutes on CPU. Because both sides run full BAMS neural rollouts, 50 games without overrides takes ~60 minutes on CPU.
**Action**: Please check on task-276. If it is still crunching slowly, kill task-276 and run Matchup 4 with calibrated beam overrides (`candidate_beam: 6, num_samples: 4, candidate_beam_2ply: 2, samples_2ply: 2`, 10 pairs) or your updated `scripts/run_m3_audit.py` script so that `data/audit/m3_magpie_ceiling.json` is generated quickly and you can deliver your handoff.

## 2026-11-10T00:07:06Z
I think your script froze/did not complete. Make sure to set a timer and try again

