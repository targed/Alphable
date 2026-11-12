# Beat Tuned MAGPIE & Formal Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formally organize the test suite with full documentation, and implement the four-approach architectural roadmap enabling Alphable V4 to match and surpass Tuned Base MAGPIE in general play.

**Architecture:** 
1. Consolidate testing methodologies into a formal, structured test suite with a Diátaxis How-To/Reference guide (`docs/TESTING_AND_VERIFICATION_GUIDE.md`).
2. Approach 1 (Ponytail Hybrid): Permanently integrate `-pat CSW24` candidate generation and native C exact endgame/pre-endgame solving into Alphable V4.
3. Approach 2 (Neural-Guided PIMC): Combine native C PIMC simulation rollouts (98k nps) with Cross-Attention Value Network re-ranking to resolve strategy fusion.
4. Approach 3 (High-Throughput Inference): Export the value network to ONNX for low-latency CPU/GPU inference.
5. Approach 4 (Calibration & Benchmarking): Tune hyperparameter weights and benchmark against Tuned MAGPIE in paired duplicate tournaments.

**Tech Stack:** Python 3.10+, PyTorch, ONNX / ONNX Runtime, ctypes, C (MAGPIE backend), SciPy, pytest.

**Branch:** `alphable_V4_paper_base`

---

## Global Constraints
- Primary claim in existing publications remains strictly bounded to 1-ply Static KLV Base MAGPIE until verified against Tuned MAGPIE.
- Every modification must preserve backwards compatibility with all 185 existing tests.
- All testing must use Common Random Numbers (CRN) and paired duplicate seeds to control tile luck.
- Documentation must follow Diátaxis guidelines and avoid AI writing clichés per the `humanizer` skill.

---

### Task 1: Formal Test Suite Consolidation

**Files:**
- Create: `tests/platform/test_audit.py`
- Modify: `pyproject.toml` (add pytest markers: `unit`, `e2e`, `audit`)
- Modify: `tests/conftest.py` (if needed for shared fixtures)

**Interfaces:**
- Consumes: `alphable_v4/cli.py`, `data/tournaments/run_20261016_155029_V4-Champion_vs_Base-MAGPIE_10000g_dup.json`.
- Produces: Integrated pytest test cases verifying statistical audit metrics and duplicate tournament consistency.

- [ ] **Step 1: Update `pyproject.toml` with pytest markers (`unit`, `e2e`, `audit`, `benchmark`)**
- [ ] **Step 2: Write `tests/platform/test_audit.py` with test cases verifying historical 10,000-game metrics, Wilson intervals, and paired t-tests**
- [ ] **Step 3: Run pytest on new audit test module to verify it passes**
- [ ] **Step 4: Commit Task 1 changes**

---

### Task 2: Authoring `docs/TESTING_AND_VERIFICATION_GUIDE.md`

**Files:**
- Create: `docs/TESTING_AND_VERIFICATION_GUIDE.md`
- Modify: `docs/README.md` (add entry to documentation index)

**Interfaces:**
- Consumes: Test suite architecture, Diátaxis guidelines, `humanizer` rules.
- Produces: Professional, human-written guide for running, understanding, and interpreting all tests.

- [ ] **Step 1: Write `docs/TESTING_AND_VERIFICATION_GUIDE.md` covering CRN philosophy, 4-tier E2E suite, paired duplicate math, and phase-sensitivity telemetry**
- [ ] **Step 2: Review text with `humanizer` rules to eliminate AI tells, staging phrases, and robotic triads**
- [ ] **Step 3: Update `docs/README.md` to link to the new guide**
- [ ] **Step 4: Commit Task 2 documentation**

---

### Task 3: Approach 1 — The Ponytail Hybrid Pipeline (Zero-Latency Native Leverage)

**Files:**
- Modify: `alphable_v4/search/bams.py` (wire native endgame and pre-endgame solvers directly to C engine)
- Modify: `alphable_v4/engine/magpie_bindings.py` (expose clean `solve_endgame_move` and `solve_peg_move`)
- Modify: `alphable_v4/cli.py` (configure default V4 policies with `use_pat=True`)
- Create: `tests/search/test_native_solvers.py`

**Interfaces:**
- Consumes: `libmagpie.so` functions (`engine.solve_endgame()`, `engine.set_pat("CSW24")`).
- Produces: Seamless native C endgame and pre-endgame execution inside BAMS search.

- [ ] **Step 1: Write failing test in `tests/search/test_native_solvers.py` testing native endgame and PAT integration**
- [ ] **Step 2: Implement `solve_endgame_move` in `alphable_v4/engine/magpie_bindings.py` that parses C output into a valid `Move`**
- [ ] **Step 3: Update `BAMSSearch._solve_exact_endgame` in `alphable_v4/search/bams.py` to use native solver when `bag_count == 0`**
- [ ] **Step 4: Ensure default V4 presets in `alphable_v4/cli.py` activate PAT-enhanced candidate generation**
- [ ] **Step 5: Run tests and verify zero regressions**
- [ ] **Step 6: Commit Task 3 changes**

---

### Task 4: Approach 2 — Neural-Guided PIMC Filter (Deep Simulation + Neural Valuation)

**Files:**
- Modify: `alphable_v4/search/bams.py` (add `select_move_hybrid_pimc` and `hybrid_pimc` config flag)
- Modify: `alphable_v4/engine/magpie_bindings.py` (add `simulate_candidates` helper)
- Create: `tests/search/test_hybrid_pimc.py`

**Interfaces:**
- Consumes: `engine.run_command("simulate -iterations N")`, `V4ValueNetwork`, `OpponentTracker`.
- Produces: Hybrid move selection combining 98k nps C rollouts with neural anti-trap valuation.

- [ ] **Step 1: Write failing test in `tests/search/test_hybrid_pimc.py` testing simulated move extraction and neural re-ranking**
- [ ] **Step 2: Implement `simulate_candidates(game_state, iterations)` in `MagpieEngine` returning candidate moves with win probabilities and spread**
- [ ] **Step 3: Implement `select_move_hybrid_pimc` in `BAMSSearch` to re-rank top PIMC candidates using Cross-Attention value predictions**
- [ ] **Step 4: Add `hybrid-pimc` preset to `build_policy` in `alphable_v4/cli.py`**
- [ ] **Step 5: Run tests to verify hybrid search functionality and latency**
- [ ] **Step 6: Commit Task 4 changes**

---

### Task 5: Approach 3 — High-Throughput ONNX Model Export

**Files:**
- Create: `alphable_v4/models/onnx_inference.py`
- Create: `scripts/export_onnx.py`
- Create: `tests/models/test_onnx_inference.py`

**Interfaces:**
- Consumes: `alphable_v4/models/checkpoints/v4_value_net_best.pt`, `V4ValueNetwork`.
- Produces: `alphable_v4/models/checkpoints/v4_value_net.onnx` and fast ONNX Runtime inference wrapper.

- [ ] **Step 1: Write `scripts/export_onnx.py` to export the ResNet-18 + Cross-Attention Value Network to ONNX format**
- [ ] **Step 2: Execute export script to generate `v4_value_net.onnx`**
- [ ] **Step 3: Implement `ONNXValueNetwork` in `alphable_v4/models/onnx_inference.py`**
- [ ] **Step 4: Write `tests/models/test_onnx_inference.py` verifying numerical parity ($\Delta < 1e-4$) between PyTorch and ONNX**
- [ ] **Step 5: Allow `BAMSConfig` to transparently use ONNX when available**
- [ ] **Step 6: Run tests and commit Task 5 changes**

---

### Task 6: Approach 4 — Calibration & Paired Duplicate Benchmark vs. Tuned MAGPIE

**Files:**
- Modify: `alphable_v4/search/bams.py` (optimal default weights for hybrid search)
- Execute: Live duplicate tournament benchmark vs. Tuned MAGPIE
- Create: `data/tournaments/run_hybrid_vs_tuned_magpie.json`

**Interfaces:**
- Consumes: `cli.py tournament --model hybrid-pimc --opponent magpie-tuned --duplicate`.
- Produces: Empirical head-to-head match data testing whether Alphable beats Tuned MAGPIE.

- [ ] **Step 1: Calibrate hybrid scoring weights ($w_{\text{pimc}}, w_{\text{value}}, w_{\text{volatility}}$)**
- [ ] **Step 2: Run a live duplicate match (20 pairs / 40 games) between Hybrid Alphable V4 and Maximally Tuned MAGPIE**
- [ ] **Step 3: Compute paired t-statistic, net spread, and win rate**
- [ ] **Step 4: Document the benchmark results in `data/tournaments/` and summary telemetry**
- [ ] **Step 5: Commit Task 6 results**

---

### Task 7: Full System Verification, Paper & Documentation Alignment

**Files:**
- Modify: `README.md`
- Verify: Full test suite (`pytest tests/ visualizer/tests/ -q`)
- Verify: Paper build (`scripts/build_paper.sh`)

- [ ] **Step 1: Run full pytest suite across all unit, e2e, and audit tests**
- [ ] **Step 2: Run `scripts/build_paper.sh` to ensure LaTeX paper compiles cleanly**
- [ ] **Step 3: Verify clean git status on `alphable_V4_paper_base`**
