# Dispatch for M2 Worker (Statistical Rigor & Phase Sensitivity Audit)

**Task**: Execute the empirical statistical validation and phase sensitivity audit for Milestone M2 (Requirement R1).
**Scope**:
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md` and `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read Survey 2 handoff at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/handoff.md` and Spec Miner 3 handoff at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_spec_miner_survey_3/handoff.md`.

**Deliverables**:
1. Run reproducible duplicate tournament matches using `cli.py tournament --duplicate` with newly instrumented phase telemetry (Opening, Midgame, Pre-endgame, Endgame).
2. Execute paired two-tailed Student's t-tests, Two-Proportion z-tests, and Wilson score 95% confidence intervals across tournament logs (3,000-game dataset and 10,000-game dataset).
3. Conduct quantitative sensitivity analysis proving how the win rate and score spread hold across each distinct game phase:
   - Opening (turns 1-5)
   - Midgame (bag > 14)
   - Pre-endgame (bag 1-14)
   - Endgame (bag == 0)
4. Formulate the mathematical proofs:
   - Proof of Common Random Numbers (CRN) variance reduction in duplicate Scrabble.
   - Proof of first-order tile luck cancellation in duplicate pair matches ($S_{\text{pair}} = \mu_1 - \mu_2$).
5. Save raw structured telemetry to `data/audit/m2_statistical_rigor.json`.
6. Write full handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m2_1/handoff.md`.

**Mandatory Integrity Warning**:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-11-09T23:03:26Z
You are the M2 Worker for Milestone M2 (Statistical Rigor & Phase Sensitivity Audit - Requirement R1).
Your working directory is `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m2_1/`.
Your parent orchestrator is conversation ID `d0ac5384-dff3-498c-b189-b11d798c2489`.

MANDATORY FIRST STEP: Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md`.
Read your dispatch file at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m2_1/DISPATCH.md`.
Read `/home/targed/Documents/Git/Alphable/PROJECT.md`.
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_explorer_survey_2/handoff.md`.
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_spec_miner_survey_3/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR MISSION:
1. Conduct empirical statistical verification:
   - Verify paired two-tailed t-test, two-proportion z-test, and Wilson score 95% intervals on reproducible duplicate tournament seeds.
   - Run duplicate tournament matches with newly instrumented phase telemetry (`OPENING`, `MIDGAME`, `PRE_ENDGAME`, `ENDGAME`).
   - Compute phase-by-phase score spreads and win-rate contributions, proving whether the win rate holds across each phase.
2. Formulate the mathematical proofs:
   - Proof of Common Random Numbers (CRN) variance reduction in Scrabble duplicate play.
   - Proof of first-order tile luck cancellation across symmetric pair matches.
3. Save structured statistical telemetry in `data/audit/m2_statistical_rigor.json`.
4. Write your comprehensive handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_worker_m2_1/handoff.md`.
5. Send a message to your parent orchestrator with your findings.
