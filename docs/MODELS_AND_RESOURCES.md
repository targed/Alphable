# Alphable V4: Models, Checkpoints & Resource Catalog

This reference catalogs trained model checkpoints, search presets, lexicons, and CLI workflows in Alphable V4.

---

## 1. Neural Network Checkpoints (`alphable_v4/models/checkpoints/`)

Weights are stored as PyTorch state dictionaries in standard `.pt` format.

```
alphable_v4/models/checkpoints/
├── v4_value_net_best.pt               # Production value network (52.6 MB, 32-ch ResNet-18 + Cross-Attention)
├── v4_value_net_rl_gen1.pt           # Reinforcement learning Gen-1 policy (52.9 MB, self-play fine-tuned)
├── v4_belief_net_best.pt             # Bayesian opponent belief model (366 KB, Dirichlet tile posterior estimator)
└── v4_value_net_best_full_training.pt # Complete local training checkpoint with optimizer state (157.8 MB)
```

### Checkpoint Specifications

| Checkpoint File | Size | Architecture | State Vector | Training Setup | Evaluation Focus | Status |
| :--- | :---: | :--- | :---: | :--- | :--- | :--- |
| [`v4_value_net_best.pt`](file:///home/targed/Documents/Git/Alphable/alphable_v4/models/checkpoints/v4_value_net_best.pt) | 52.6 MB | ResNet-18 + Cross-Attention (32 channels, 512-dim embedding, 8 heads) | 64 dims | Supervised distillation on 10,000+ grandmaster games with normalized equity targets. Full 157.8 MB Adam training checkpoint is archived as [`v4_value_net_best_full_training.pt`](file:///home/targed/Documents/Git/Alphable/alphable_v4/models/checkpoints/v4_value_net_best_full_training.pt). | Evaluates full-board positions for multi-turn bingo lanes, rack balance, vowel congestion, and defense. | Production default for `latest`, `5-frontiers`, and `scaled` presets. |
| [`v4_value_net_rl_gen1.pt`](file:///home/targed/Documents/Git/Alphable/alphable_v4/models/checkpoints/v4_value_net_rl_gen1.pt) | 52.9 MB | ResNet-18 Value Network | 64 dims | Policy-gradient fine-tuning against anchored teacher weights ($D_{\text{KL}}$ penalty) to prevent policy collapse. | Tactical evaluation in contested midgame positions. | RL policy checkpoint, selectable via `--model rl-gen1`. |
| [`v4_belief_net_best.pt`](file:///home/targed/Documents/Git/Alphable/alphable_v4/models/checkpoints/v4_belief_net_best.pt) | 366 KB | Bayesian Dirichlet-Multinomial Estimator | 27 dims | Unseen tile pool tracking combined with negative-evidence observation of opponent plays. | Predicts opponent rack distributions with dynamic blank-probability decay when high-value tiles are withheld. | Active inference tracker used across all BAMS searches. |

---

## 2. Search Presets Catalog

Alphable V4 separates model weights from search execution policies. Checkpoints can be paired with any search preset using `--model <preset>` and `--model-path <path>`.

| Preset Key | Canonical Name | Beam ($K$) | MC Samples ($N$) | 2-Ply Nested Lookahead | Volatility Control ($w$) | Verified Win Rate vs Base MAGPIE | Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`latest`** (or `champion`, `calibrated`) | V4 Scaled 2-Ply + Volatility | $K=15$ | $N=24$ | Yes ($K=8, N=14$) | $w=0.4$ (Lead/Deficit Adaptive) | 56.7% (+13.1 pts spread) | Production default; pairs 2-ply search with dynamic volatility damping. |
| **`5-frontiers`** (or `frontiers`, `v5-frontier-v4`) | V4 5-Frontiers Champion | $K=15$ | $N=24$ | Yes ($K=6, N=12$) | Disabled ($w=0.0$) | 54.2% (+9.8 pts in 1,000 games) | Standard 1,000-game baseline configuration. |
| **`rl-gen1`** (or `rl`, `self-play`) | V4 RL Gen-1 Policy | $K=15$ | $N=24$ | Yes ($K=8, N=14$) | $w=0.4$ | RL Fine-Tuned Policy | Self-play policy evaluation against baselines. |
| **`scaled`** (or `deep-scaled`, `deep`) | Deep 2-Ply Scaled Search | $K=20$ | $N=32$ | Yes ($K=12, N=20$) | $w=0.4$ | 57.0%+ (High-Depth Profile) | High-depth tactical search for complex boards. |
| **`v4-baseline`** (or `baseline`) | V4 1-Ply Search Baseline | $K=10$ | $N=16$ | No (1-Ply Rollout) | Disabled ($w=0.0$) | 52.2% (+4.3 pts in 1,000 games) | Reference baseline without 2-ply search. |
| **`static-magpie`** (or `magpie`) | Base MAGPIE Solver | N/A | N/A | No | No | 50.0% (0.0 pts baseline) | Pure C KLV static leave equity evaluation. |

---

## 3. Command Line Interface (CLI) Manual

All commands execute from the repository root:

```bash
python cli.py --help
```

### 1. View Models Catalog (`python cli.py models`)
Prints a summary table of registered models, checkpoints, search parameters, file sizes, and benchmark win rates:

```bash
python cli.py models
```

### 2. Run Head-to-Head Tournaments (`python cli.py tournament`)

#### Official 1,000-Game Benchmark vs Base MAGPIE
```bash
# Run latest champion (56.7% WR) against Base MAGPIE:
python cli.py tournament --opponent magpie --games 1000

# Run 5-frontiers 1,000-game baseline model (54.2% WR):
python cli.py tournament --model 5-frontiers --opponent magpie --games 1000

# Run original V4 1-ply baseline (52.2% WR):
python cli.py tournament --model v4-baseline --opponent magpie --games 1000
```

#### Model vs Model Comparisons
```bash
# Compare Scaled Champion against V4 Baseline:
python cli.py tournament --model latest --opponent v4-baseline --games 50

# Compare Scaled Champion against 5-Frontiers:
python cli.py tournament --model latest --opponent 5-frontiers --games 50

# Compare RL fine-tuned model against 5-Frontiers:
python cli.py tournament --model rl-gen1 --opponent 5-frontiers --games 50
```

#### Duplicate Pair-Swapped Tournaments (Equal Tile Seed Benchmark)
In standard Scrabble tournaments, tile draw variance accounts for 5% to 10% of match noise. Using `--duplicate` plays each board seed twice with swapped seats, canceling out initial tile luck:

```bash
python cli.py tournament --model latest --opponent magpie --games 30 --duplicate
python cli.py tournament --model latest --opponent 5-frontiers --games 20 --duplicate
```

#### Tournaments Against Legacy Alphable V3 Engines
```bash
# Play against Alphable V3 Macondo ResNet Champion (63 dims):
python cli.py tournament --opponent v3-resnet --games 100

# Play against Alphable V3 SmolLM2 Transformer Ranker:
python cli.py tournament --opponent v3-transformer --games 10
```

#### Load Custom Checkpoints
```bash
python cli.py tournament --model-path alphable_v4/models/checkpoints/my_custom_weights.pt --opponent magpie --games 20
```

---

## 4. Positional Analysis (`python cli.py analyze`)

Compare Base MAGPIE and BAMS evaluations side-by-side on any rack and board setup:

```bash
# Empty opening board:
python cli.py analyze --model latest --rack "AQRTUYZ"

# Mid-game board with hook word:
python cli.py analyze --model latest --rack "RETINAS" --board-word "QUIZ" --board-coord "8D"

# Compare analysis across models:
python cli.py analyze --model rl-gen1 --rack "RETINAS"
python cli.py analyze --model 5-frontiers --rack "RETINAS"
```

---

## 5. Interactive Terminal Play (`python cli.py play`)

Play a game against any Alphable V4 model in your terminal:

```bash
# Play against the latest champion:
python cli.py play

# Play against the RL Gen-1 policy:
python cli.py play --model rl-gen1

# Play against the 5-Frontiers champion:
python cli.py play --model 5-frontiers
```

Type `hint` during your turn for BAMS tactical recommendations, or enter plays using standard Scrabble notation (e.g. `8H CATS`).

---

## 6. Lexicons & Engine Binaries

Alphable V4 uses native dictionary resources and compiled C binaries:

- **CSW24 Lexicon**: [`resources/CSW24.txt`](file:///home/targed/Documents/Git/Alphable/resources/CSW24.txt) (Collins Scrabble Words 2024, international tournament standard).
- **NWL23 Lexicon**: [`resources/NWL23.txt`](file:///home/targed/Documents/Git/Alphable/resources/NWL23.txt) (NASPA Word List 2023, North American tournament standard).
- **MAGPIE C Shared Library**: [`vendor/magpie/bin/libmagpie.so`](file:///home/targed/Documents/Git/Alphable/vendor/magpie/bin/libmagpie.so) (compiled move generation and leave valuation engine). Source code lives in [`vendor/magpie/`](file:///home/targed/Documents/Git/Alphable/vendor/magpie/).

---

## 7. Historical Benchmark Records

| Series Description | Total Games | Win Rate | BAMS Mean | Opp Mean | Net Spread | Divergence Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BAMS (Scaled 2-Ply + Volatility $w=0.4$) vs Base MAGPIE** | 30 | 56.7% | 457.5 pts | 444.4 pts | +13.1 pts | 20.4% |
| **BAMS (All 5 Frontiers Active) vs Base MAGPIE** | 1,000 | 54.2% | 458.1 pts | 448.3 pts | +9.8 pts | 16.2% |
| **BAMS (All 5 Frontiers Active) vs Base MAGPIE** | 30 | 63.3% | 456.3 pts | 448.5 pts | +7.8 pts | 15.9% |
| **BAMS Duplicate Pairs (Zero Luck, 2-Ply BAMS)** | 10 (5 pairs) | 100.0% | 498.4 pts | 410.8 pts | +87.6 pts | 17.2% |
| **BAMS (Calibrated V4) vs Base MAGPIE** | 1,000 | 52.2% | 454.4 pts | 450.1 pts | +4.3 pts | 15.7% |
| **BAMS vs Alphable V3 (Macondo ResNet)** | 100 | 65.5% | 457.4 pts | 442.4 pts | +15.0 pts | 22.4% |
| **BAMS vs Alphable V3 (SmolLM2 Transformer)** | 5 | 100.0% | 529.3 pts | 229.3 pts | +300.0 pts | 28.1% |
| **BAMS vs Score-Greedy** | 10 | 100.0% | 492.6 pts | 312.4 pts | +180.2 pts | 41.2% |
