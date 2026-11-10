# Dispatch for E2E Test Writer (Opaque-Box E2E Testing Suite)

**Task**: Design and implement the opaque-box E2E test suite derived from user requirements in `ORIGINAL_REQUEST.md` and feature inventory in `PROJECT.md`.
**Scope**:
Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md` and `/home/targed/Documents/Git/Alphable/PROJECT.md`.
1. Create `/home/targed/Documents/Git/Alphable/TEST_INFRA.md` following the template in Project Pattern:
   - Category-Partition + BVA + Pairwise + Workload Testing.
   - Enumerate all features from `PROJECT.md § Feature Inventory`.
2. Implement comprehensive E2E tests in `tests/e2e/`:
   - Tier 1: Feature Coverage (>=5 test cases per feature covering core engine, search, tournament duplicate execution, position analysis).
   - Tier 2: Boundary & Corner Cases (empty bag, single tile left, pass chains, zero-score placements, maximum tiles, coordinate edge bounds).
   - Tier 3: Cross-Feature Combinations (BAMS search + Opponent Belief tracking + duplicate tournament execution).
   - Tier 4: Real-World Workload Scenarios (reproducible duplicate match simulations, paired t-test execution, full game replays).
3. Ensure the test suite runner can be invoked cleanly (e.g. `CUDA_VISIBLE_DEVICES="" python3 -m pytest tests/e2e/ -v`).
4. Publish `/home/targed/Documents/Git/Alphable/TEST_READY.md` summarizing the test suite, test commands, and feature coverage matrix.
**Output**: Write completion report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_test_writer_e2e_1/handoff.md`.


## 2026-11-09T22:34:59Z
You are the E2E Test Writer for the Alphable V4 audit and scientific defense.
Your working directory is `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_test_writer_e2e_1/`.
Your parent orchestrator is conversation ID `d0ac5384-dff3-498c-b189-b11d798c2489`.

MANDATORY FIRST STEP: Read `/home/targed/Documents/Git/Alphable/.agents/teamwork/ORIGINAL_REQUEST.md`.
Read your dispatch file at `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_test_writer_e2e_1/DISPATCH.md`.
Read `/home/targed/Documents/Git/Alphable/PROJECT.md`.

YOUR MISSION:
1. Create `/home/targed/Documents/Git/Alphable/TEST_INFRA.md` following the template in Project Pattern:
   - Category-Partition + BVA + Pairwise + Workload Testing.
   - Enumerate all features from `PROJECT.md § Feature Inventory`.
2. Implement comprehensive, production-grade E2E tests in `tests/e2e/`:
   - Tier 1: Feature Coverage (>=5 test cases per feature covering core engine, search, tournament duplicate execution, position analysis).
   - Tier 2: Boundary & Corner Cases (empty bag, single tile left, pass chains, zero-score placements, maximum tiles, coordinate edge bounds).
   - Tier 3: Cross-Feature Combinations (BAMS search + Opponent Belief tracking + duplicate tournament execution).
   - Tier 4: Real-World Workload Scenarios (reproducible duplicate match simulations, paired t-test execution, full game replays).
3. Ensure all tests run and pass cleanly using:
   `CUDA_VISIBLE_DEVICES="" PYTHONPATH=./venv/lib/python3.11/site-packages:. python3 -m pytest tests/e2e/ -v`
4. Publish `/home/targed/Documents/Git/Alphable/TEST_READY.md` summarizing the test suite, test commands, and feature coverage matrix.
5. Write your handoff report to `/home/targed/Documents/Git/Alphable/.agents/teamwork/teamwork_preview_test_writer_e2e_1/handoff.md`.
6. Send a message to your parent orchestrator when complete.
