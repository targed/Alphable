# Alphable V3 Documentation

Welcome to the comprehensive technical documentation for **Alphable V3**, a state-of-the-art Deep Reinforcement Learning Scrabble engine capable of superhuman-level play.

Alphable uses an **After-State Value Network** (PyTorch dual-stream ResNet) combined with a high-speed C++ GADDAG move generator (via Cython) and a **minimax zero-sum 1-ply Monte Carlo lookahead search** engine.

---

## 📚 Documentation Index

### 1. High-Level Overviews & Setup
- [**Quick Start Guide**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/QUICK_START.md): Installation, environment configuration (including Blackwell RTX 5070 Ti CUDA notes), and immediate execution examples.
- [**Master Specification (V3)**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/ALPHABLE_V3_DOCUMENTATION.md): Complete high-level project reference, phase breakdown, mathematical objectives, and directory structure.

### 2. Architecture & Algorithms
- [**Neural Network & Representation Architecture**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/architecture/ARCHITECTURE.md):
  - 31-channel board tensor encoding (letter planes 0–25, empty plane 26, open premium squares 27–30).
  - 36-dimensional scalar state vector (rack frequencies, leave metrics, vowel/consonant balance, duplicate penalties, score diff, bag count).
  - Dual-stream ResNet fusion architecture (5 residual blocks with BatchNorm and LeakyReLU, dense MLP trunk).
  - Backwards-compatible weight loading across model generations.
- [**Search & Move Equity Formulation**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/architecture/SEARCH_AND_EQUITY.md):
  - The Scrabble After-State Value paradigm vs standard MCTS.
  - The Move Equity Equation: $\text{Equity} = \text{Points} + 25.0 \times V(s')$.
  - 1-Ply Monte Carlo Rack Sampling with exact unseen tile distributions.
  - Zero-Sum Minimax Opponent Reply Equity deduction: $\text{Net Equity} = \text{Points} - \text{Expected Opponent Equity}$.

### 3. File-by-File Component References
- [**Core Modules**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/components/CORE_MODULES.md):
  - `src/alphable/core/simulator.py`: Board mutation, cross-word perpendicular scoring rules, multipliers, blank handling.
  - `src/alphable/core/inference.py`: Feature extraction, tensor conversion, batch inference, move ranking.
  - `src/alphable/core/search.py`: Monte Carlo lookahead, rack sampling, opponent reply simulation.
  - `src/alphable/core/alphable_net.py`: PyTorch network implementation, layers, checkpoint compatibility.
  - `src/alphable/core/structure.py`: Cython wrapper over C++ GADDAG move generator.
- [**Training Pipeline**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/components/TRAINING_PIPELINE.md):
  - `src/alphable/training/prepare_dataset.py`: Woogles JSON ingestion, player username mapping, exact tile accounting, continuous deficit negative scaling.
  - `src/alphable/training/train_supervised.py`: Supervised foundation training, AdamW, Plateau learning rate scheduling, early stopping.
  - `src/alphable/training/self_play.py`: Mirror self-play, anti-greedy curriculum generation, temperature annealing, `--keep-p0-only` contamination protection.
  - `src/alphable/training/train_rl.py`: Reinforcement learning value training from self-play trajectories.
- [**Evaluation & Analytics**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/components/EVALUATION_AND_ANALYTICS.md):
  - `src/alphable/eval/evaluate_matches.py`: Direct head-to-head evaluation between checkpoints with first-mover alternation.
  - `src/alphable/eval/evaluate_vs_baseline.py`: Benchmark suite vs RandomBot and GreedyBot with replay JSON and TXT logging.
  - `src/alphable/eval/analyze.py`: Loss curve plotting utility and CLI command.
  - `src/alphable/logging/game_logger.py`: Match event and move logger.
  - `src/alphable/cli/main.py`: Master CLI dispatcher.

### 4. Workflows & Processes
- [**End-to-End Training Lifecycle**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/TRAINING_WORKFLOW.md):
  - How to move from raw Woogles replays to Supervised Foundation, Curriculum Self-Play, Reinforcement Learning, and Gatekeeper Evaluation.
- [**CLI Reference Manual**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/workflows/CLI_REFERENCE.md):
  - Comprehensive flag-by-flag syntax and examples for all `alphable` subcommands.

### 5. Decisions, Experiments & Post-Mortems
- [**What We Have Tried (Experiment History)**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/decisions/WHAT_WE_HAVE_TRIED.md):
  - Chronological history of V1, V2, and V3 iterations.
  - Empirical progression: 16.7% $\to$ 60.0% $\to$ **80.0% win rate** against GreedyBot.
  - Key lessons learned: leave values, anti-greedy sample contamination, bingo equity.
- [**Bugs Resolved & Post-Mortems**](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/decisions/BUGS_AND_POSTMORTEMS.md):
  - In-depth technical breakdown of the 5 major bugs identified and resolved in V3.
