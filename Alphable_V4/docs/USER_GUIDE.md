# Alphable V4: Complete User & Operator Guide

Welcome to **Alphable V4**, the championship-tier competitive Scrabble artificial intelligence engine. This guide explains how to run, use, test, evaluate, and benchmark the engine.

> **Catalogs & References**:
> - [MODELS_AND_RESOURCES.md](file:///home/targed/Documents/Git/Alphable/Alphable_V4/docs/MODELS_AND_RESOURCES.md): Detailed catalog of neural checkpoints, search presets, architectures, parameters, and verified benchmarks.
> - [TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md](file:///home/targed/Documents/Git/Alphable/Alphable_V4/docs/TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md): Master tournament logs, 1,000-game records, and duplicate benchmark reports.

---

## ⚡ Quick Start: Commands Cheat Sheet

Run all commands from `/home/targed/Documents/Git/Alphable/Alphable_V4` inside the virtual environment:

```bash
# 1. Activate Environment
source /home/targed/Documents/Git/Alphable/venv/bin/activate
export PYTHONPATH=/home/targed/Documents/Git/Alphable/Alphable_V4:$PYTHONPATH

# 2. View All Available Models & Presets
python cli.py models

# 3. Run the Full Test Suite (57 unit tests)
pytest -v

# 4. Analyze Any Position (Compare Base MAGPIE vs BAMS AI Side-by-Side)
python cli.py analyze --model latest --rack "AQRTUYZ"
python cli.py analyze --model latest --rack "TRAINER" --board-word "QUIZ" --board-coord "8D"

# 5. Play an Interactive Match Against Alphable V4 in the Terminal
python cli.py play --model latest

# 6. Run a Tournament vs Base MAGPIE (1,000 Games)
python cli.py tournament --opponent magpie --games 1000

# 7. Compare Two Models Directly (e.g. Latest Champion vs 5-Frontiers)
python cli.py tournament --model latest --opponent 5-frontiers --games 50

# 8. Run a Duplicate Tournament (Zero Tile Luck)
python cli.py tournament --model latest --opponent 5-frontiers --games 30 --duplicate

# 9. Run an AI Ablation Experiment (Neural Network ON vs OFF)
python cli.py ablation --games 10
```

---

## 🏷️ How to Select and Specify Models in Alphable V4

Alphable V4 features a flexible model registry and preset system inspired by Alphable V3, but upgraded for V4's multi-stage BAMS architecture.

### 1. View All Models (`python cli.py models`)
To view all available checkpoints, search configurations, file sizes, and verified benchmark ratings, simply run:
```bash
python cli.py models
```

### 2. Available Model Presets
You can pass any of the following names or aliases to `--model` (Player 1) or `--opponent` (Player 2):

| Preset Flag | Canonical Name | Checkpoint File | Description & Win Rate |
| :--- | :--- | :--- | :--- |
| `--model latest` | **V4 Scaled Champion** | `v4_value_net_best.pt` | ⭐ **Current Champion**: Scaled 2-ply search ($K=8, N=14$) + volatility control ($w=0.4$). **56.7% Win Rate (+13.1 pts spread)**. Aliases: `champion`, `calibrated`. |
| `--model 5-frontiers` | **V4 5-Frontiers Champion** | `v4_value_net_best.pt` | 🏆 **Official 1,000-Game Baseline**: Search with pre-endgame parity & belief tracking. **54.2% Win Rate (+9.8 pts spread)**. Aliases: `frontiers`, `v5-frontier-v4`. |
| `--model rl-gen1` | **V4 RL Gen-1 Policy** | `v4_value_net_rl_gen1.pt` | 🔬 **RL Fine-Tuned**: Policy gradient fine-tuning with anchored teacher loss. Aliases: `rl`, `self-play`. |
| `--model scaled` | **Deep Scaled 2-Ply** | `v4_value_net_best.pt` | ⚡ **Grandmaster Depth**: Deep 2-ply lookahead ($K=12, N=20$) for high-precision tournament play. Aliases: `deep-scaled`, `deep`. |
| `--model v4-baseline` | **V4 1-Ply Baseline** | `v4_value_net_best.pt` | 📦 **V4 Baseline**: Standard 1-ply BAMS without 2-ply nesting ($52.2\%$ WR, $+4.3$ pts). Alias: `baseline`. |
| `--model static-magpie` | **Base MAGPIE** | None (C solver) | ⚙️ **Pure Static KLV**: Classical C-based static equity solver (zero neural). Alias: `magpie`. |

### 3. Loading Custom Checkpoint Files (`--model-path`)
If you train a new checkpoint or want to load specific weights from disk:
```bash
python cli.py tournament --model-path models/checkpoints/v4_value_net_rl_gen1.pt --opponent magpie --games 50
```

---

## ⚔️ How to Test, Run, and Compare Models

### 1. The Standard 1,000-Game Tournament vs Base MAGPIE
To reproduce or verify large-scale win rate benchmarks against Base MAGPIE:
```bash
# 1. Test the latest calibrated champion (56.7% WR target):
python cli.py tournament --model latest --opponent magpie --games 1000

# 2. Test the 5-frontiers 1,000-game baseline (54.2% WR verified):
python cli.py tournament --model 5-frontiers --opponent magpie --games 1000

# 3. Test the original V4 1-ply baseline (52.2% WR verified):
python cli.py tournament --model v4-baseline --opponent magpie --games 1000

# 4. Test the RL fine-tuned model:
python cli.py tournament --model rl-gen1 --opponent magpie --games 1000
```
*(Note: If you omit `--model`, it automatically defaults to `latest`)*

### 2. Head-to-Head Comparison Between Two Models
You can pit any two models directly against each other with alternating first turns:
```bash
# Latest Champion vs 5-Frontiers:
python cli.py tournament --model latest --opponent 5-frontiers --games 50

# Latest Champion vs V4 Baseline:
python cli.py tournament --model latest --opponent v4-baseline --games 50

# RL Gen-1 Policy vs 5-Frontiers:
python cli.py tournament --model rl-gen1 --opponent 5-frontiers --games 50
```

### 3. Zero-Tile-Luck Duplicate Matches (`--duplicate`)
In standard Scrabble tournaments, tile draw luck introduces $\approx 5\text{--}10\%$ outcome noise. Using `--duplicate` plays every board seed twice with swapped player seats:
- Game A: Model 1 plays Player 1, Model 2 plays Player 2 on seed $S$.
- Game B: Model 2 plays Player 1, Model 1 plays Player 2 on the **exact same seed $S$**.
```bash
python cli.py tournament --model latest --opponent 5-frontiers --games 30 --duplicate
```
Outputs net match pair score differential and duplicate match wins, completely neutralizing tile luck.

### 4. Cross-Generation Tournaments vs Alphable V3
You can pit Alphable V4 directly against the legacy Alphable V3 champions:
```bash
# Vs Alphable V3 Macondo ResNet Champion (63 dims):
python cli.py tournament --model latest --opponent v3-resnet --games 100

# Vs Alphable V3 SmolLM2-135M Transformer Candidate Ranker:
python cli.py tournament --model latest --opponent v3-transformer --games 10
```

---

## 📜 Automated Tournament History & Run Comparison

Every tournament run automatically persists full statistical telemetry to `Alphable_V4/data/tournaments/` and appends an entry to the master ledger `tournament_history.jsonl`.

### 1. View Benchmark History Ledger (`python cli.py history`)
```bash
python cli.py history
```
Displays an aligned historical ledger with Run ID, timestamp, mode (standard vs duplicate), matchup, game count, 95% Confidence Intervals for Win Rate and Net Spread, paired t-test results, and tags.

### 2. Inspect Full Details of a Specific Run (`--show`)
```bash
# View exact scores, error bars, bingos, and duration:
python cli.py history --show run_20261015_215837
# Or by prefix / date:
python cli.py history --show 20261015
```

### 3. Compare Two Runs Side-by-Side (`--compare`)
```bash
# Compare the 5-Frontiers 1,000-game run vs the 3,000-game Duplicate Championship:
python cli.py history --compare run_20261013_143000 run_20261015_215837
```
Computes and displays exact mathematical deltas ($\Delta \text{Win Rate}$, $\Delta \text{Spread}$, $\Delta \text{Bingos}$, confidence interval narrowing, and speed).

### 4. Tagging and Filtering Runs
```bash
# Run tournament with a custom tag:
python cli.py tournament --opponent magpie --games 100 --tag "depth-scaling-test"

# Filter history by tag or model:
python cli.py history --tag "duplicate"
python cli.py history --model "5-frontiers"
```

---

## 🧠 How Do I Know If It Is Just MAGPIE or If the AI Is Actually Doing Something?

This is the most critical question in AI engine development. Here is the exact architectural and mathematical breakdown:

### 1. What Base MAGPIE Does (The Static Engine)
Base MAGPIE is a classical C-based Scrabble solver. When given a board and rack, it calculates:
$$\text{Static Equity} = \text{Immediate Points} + \text{Leave Value}$$
- **Immediate Points**: Points earned from the tiles placed this turn.
- **Leave Value**: Estimated future value of the remaining rack tiles from precomputed static leave tables (KLV).

**What Base MAGPIE CANNOT See:**
1. **It has NO idea what tiles the opponent holds**: It assumes a generic, static probability.
2. **It does NOT simulate the opponent's counter-move**: It doesn't see if playing a word gives the opponent an easy 60-point triple-word hook or opens a dangerous bingo lane.
3. **It does NOT evaluate the future board geometry**: It does not evaluate how open, congested, or defensively vulnerable the resulting board is for the rest of the game.

---

### 2. What the AI Adds (Belief Inference + Rollouts + Volatility + Neural Value Net)
When Alphable V4 searches, it executes **Belief-Augmented Monte Carlo Search (BAMS)**:
$$\text{BAMS\_Score}(c) = \text{Static Eq}(c) - \beta \cdot \mathbb{E}[\text{OppScore}(c)] + \gamma \cdot \mathbb{E}[V(S')] + \Delta_{\text{2ply}}(c) + \Omega_{\text{vol}}(S')$$

1. **Bayesian Rack Inference (`BayesianRackInference`)**:
   - Inspects the unseen tile pool and samples $N$ opponent racks using Dirichlet-multinomial sampling with **Common Random Numbers (CRN)**.
2. **Nested 2-Ply Monte Carlo Rollout**:
   - Simulates the opponent's strongest counter-plays and tests follow-up turns to measure true net exchanges.
3. **ResNet-18 + Cross-Attention Value Network (`V4ValueNetwork`)**:
   - Evaluates the resulting 15×15 after-board tensor (32 channels) and 64-dimensional game state vector on GPU in **1.96 ms**.
4. **Asymmetric Board Topology Control**:
   - When leading ($\Delta \ge 20$), penalizes exposed premium lanes to protect leads; when trailing ($\Delta \le -20$), injects volatility to open comeback bingo lanes.

---

### 3. Concrete Visual Proof in the Terminal

When you run:
```bash
python cli.py analyze --model latest --rack RETINAS
```
You get a breakdown showing the exact numbers:
```text
#   Move           Pts   Leave   Static Eq   Opp Threat   Neural Val   BAMS Score
--------------------------------------------------------------------------------
1   8B ANESTRI     66            66.00       46.7 pts     +0.1290      65.91      [BASE MAGPIE #1]
6   8D ANESTRI     66            66.00       42.5 pts     +0.3774      68.38      [AI CHOSEN #1 ★]
--------------------------------------------------------------------------------
Base MAGPIE Latency: 0.67 ms | AI Policy Latency: 839.05 ms

DECISION SUMMARY:
  • Base MAGPIE Choice : 8B ANESTRI (Score: 66, Static Equity: 66.00)
  • AI Policy Choice   : 8D ANESTRI (Score: 66, BAMS Score: 68.38)

  >>> [AI DIVERGENCE DETECTED] <<<
  The AI actively overrode Base MAGPIE's #1 move!
```

#### What this proves:
- Both `8B ANESTRI` and `8D ANESTRI` score the exact same **66 points** and leave empty racks.
- Base MAGPIE rates them identical ($66.00$).
- But the AI rollout discovers that `8D` reduces the opponent's counter-attack reply from **46.7 pts down to 42.5 pts**.
- The AI Value Network also rates `8D` higher (+0.3774 vs +0.1290).
- **The AI actively steers the choice toward defensive safety and board control!**
