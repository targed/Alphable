# Alphable V3 Documentation Portal

Welcome to the comprehensive technical documentation for **Alphable V3**, an expert-level deep reinforcement learning and Monte Carlo lookahead Scrabble engine capable of competing at and exceeding tournament grandmaster performance.

---

## 🏆 Project Milestone Progression

| Generation | Engine / Core Innovation | Benchmark Opponent | Win Rate | Avg Score Diff | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **V1** | Naive Point Maximizer + Simple Value Net | GreedyBot | 16.7% | -82.4 pts | Superseded |
| **V2** | Supervised Value Net (36-dim state) | GreedyBot | 60.0% | +18.2 pts | Superseded |
| **V3 Early** | Dual-Stream ResNet + 1-Ply Lookahead | GreedyBot | **80.0%** | **+63.4 pts** | Superseded |
| **V3 Online** | Baseline Lookahead ($W=25$) | HastyBot (Woogles) | 20.0% | -65.4 pts | Baseline |
| **V3 5-Pillars** | Super-Leaves + Endgame Minimax + 63-dim Bag Tracking | HastyBot (Woogles) | 41.3% | -21.0 pts | Upgraded |
| **V3 Production** | **Macondo Distillation + CRN Search + GADDAG Blank Hooks** | **HastyBot (Woogles)** | **53.3%** | **+12.4 pts** | **⭐ CURRENT CHAMPION** |

---

## 📚 Complete Documentation Index

### 1. High-Level Overviews & Catalogs
- [**Quick Start Guide**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/QUICK_START.md): 2-minute setup, testing, and running your first match against HastyBot.
- [**Master Technical Manual**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/ALPHABLE_V3_DOCUMENTATION.md): Definitive technical specification covering all systems, mathematical formulations, and algorithms.
- [**Models & Resources Catalog**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/RESOURCES_AND_MODELS.md): Inventory of all checkpoints (`alphable_v3_macondo_v2.pth`, etc.), lexicons (`CSW24.txt`, `NWL2023.txt`), and telemetry archives.

### 2. Architecture & Algorithmic Foundations
- [**System Architecture & Representations**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/architecture/ARCHITECTURE.md):
  - 31-channel board tensor ($15 \times 15$ spatial encoding).
  - 63-dimensional state vector (rack counts, leave metrics, unseen bag distributions).
  - Dual-stream ResNet + MLP architecture and backward-compatible checkpoint loader.
- [**Search & Move Equity Formulation**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/architecture/SEARCH_AND_EQUITY.md):
  - Move equity equation: $\text{Equity} = \text{Points} + \text{Leave} + \text{Def} + 25.0 \times V(s')$.
  - 1-Ply Monte Carlo Lookahead with **Common Random Numbers (CRN)** variance reduction.
  - Selective 2-ply counter-response search.
  - Sub-millisecond deterministic exact endgame minimax solver ($bag=0$).

### 3. Decisions, Research Trajectory & Post-Mortems
- [**What We Have Tried**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/decisions/WHAT_WE_HAVE_TRIED.md):
  - Chronological history of all experiments from V1 to V3.
  - The Pure Outcome Self-Play Failure: Why symmetric self-play collapsed into a timid, low-scoring local Nash equilibrium.
  - The Macondo Distillation Anchor Breakthrough.
  - 75-match empirical analysis against HastyBot and the final CRN/blank hook fixes.
- [**Bugs Resolved & Post-Mortems**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/decisions/BUGS_AND_POSTMORTEMS.md):
  - Exhaustive post-mortems for all 10 critical bugs solved in Alphable V3 (symptoms, root causes, code diffs, and verifications).

### 4. Component Deep-Dives
- [**Core Modules Reference**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/components/CORE_MODULES.md):
  - `structure.pyx`: Cython/C++ GADDAG bidirectional move generation and blank tile hooks.
  - `simulator.py`: Move placement, primary scoring, multipliers, and perpendicular cross-words.
  - `inference.py`: Feature extraction and batch evaluation.
  - `leave_eval.py`: Super-Leaves empirical tables, duplicate blank formula, and vowel/consonant balance.
  - `defense.py`: Line-of-sight Triple Word / Double Word safety analysis.
  - `endgame.py`: Alpha-beta exact minimax solver.
  - `search.py`: Lookahead search with CRN and 2-stage opponent pruning.
- [**Training Pipeline Reference**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/components/TRAINING_PIPELINE.md):
  - `distill_macondo.py`: Grandmaster knowledge distillation from Woogles GCG + Macondo analysis.
  - `prepare_dataset.py`: Supervised dataset creation with negative mining and continuous deficit scaling.
  - `train_supervised.py`: PyTorch training loop and learning rate scheduling.
  - `self_play_rl.py`: AlphaZero-style in-memory self-play outcome RL.
- [**Evaluation & Analytics Reference**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/components/EVALUATION_AND_ANALYTICS.md):
  - `evaluate_matches.py` & `evaluate_vs_baseline.py`: Checkpoint-vs-checkpoint and baseline testing.
  - Platform runner telemetry, GCG parsing, Macondo equity loss measurement, and Web Visualizer.

### 5. Operational Workflows & Runbooks
- [**CLI Reference Manual**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/CLI_REFERENCE.md):
  - Complete, flag-by-flag syntax and copy-pasteable examples for every `alphable` subcommand.
- [**Woogles Bot Operational Runbook**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/WOOGLES_BOT_OPERATION.md):
  - Step-by-step guide to running autonomous series on Woogles.io, reading live console telemetry, managing persistent profiles, and error recovery.
- [**5-Pillars Verification Guide**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/FIVE_PILLARS_VERIFICATION_GUIDE.md):
  - Verification checklist for the 5 engine pillars and 4 critical fixes.
- [**End-to-End Training Lifecycle**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/TRAINING_WORKFLOW.md):
  - Step-by-step guide from raw game replays to supervised foundation, curriculum generation, and gatekeeper evaluation.

---

## 🛠️ Verification & Testing

Verify that all 205 unit tests pass:
```bash
cd /home/targed/Documents/Git/Alphable/Alphable_V3
source ../venv/bin/activate
pytest tests/
```
