# Alphable V4 user guide

This guide covers model selection, command-line arguments, tournament benchmarking, run comparison, the Visualizer Studio, and how Alphable V4 differs from classical static engines.

Related references:
- [MODELS_AND_RESOURCES.md](MODELS_AND_RESOURCES.md): Neural checkpoints, search presets, architectures, parameters, and verified benchmarks.
- [TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md](TOURNAMENT_BENCHMARKS_AND_COMMAND_MANUAL.md): Master tournament logs, 1,000-game records, and duplicate benchmark reports.
- [STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md](STATISTICAL_SIGNIFICANCE_AND_BENCHMARKING_GUIDE.md): Methodology for paired duplicate matches and statistical tests.

---

## Commands cheat sheet

Run commands from the repository root within your activated virtual environment:

```bash
# 1. Activate environment
source venv/bin/activate

# 2. View available models and presets
python cli.py models

# 3. Run the test suite
pytest tests/ -v

# 4. Analyze positions (Base MAGPIE vs BAMS side-by-side)
python cli.py analyze --model latest --rack "AQRTUYZ"
python cli.py analyze --model latest --rack "TRAINER" --board-word "QUIZ" --board-coord "8D"

# 5. Play an interactive match in the terminal
python cli.py play --model latest

# 6. Run a tournament vs Base MAGPIE (100 games)
python cli.py tournament --opponent magpie --games 100

# 7. Compare two models directly
python cli.py tournament --model latest --opponent 5-frontiers --games 50

# 8. Run a duplicate tournament (zero tile luck)
python cli.py tournament --model latest --opponent 5-frontiers --games 30 --duplicate

# 9. Run an ablation experiment (neural evaluation on vs off)
python cli.py ablation --games 10

# 10. Start the Visualizer Studio
./start_visualizer.sh
# or: cd visualizer && ./run.sh
```

---

## Model selection and presets

Alphable V4 includes a model registry with several configured presets.

### 1. View all models
To display available checkpoints, search configurations, file sizes, and verified benchmark ratings:
```bash
python cli.py models
```

### 2. Available model presets
Pass any of the following names or aliases to `--model` (Player 1) or `--opponent` (Player 2):

| Preset Flag | Canonical Name | Checkpoint File | Description & Verified Performance |
| :--- | :--- | :--- | :--- |
| `--model latest` | V4 Scaled Champion | `v4_value_net_best.pt` | Scaled 2-ply search ($K=8, N=14$) with volatility control ($w=0.4$). 56.7% win rate (+13.1 pts spread) vs Base MAGPIE. Aliases: `champion`, `calibrated`. |
| `--model 5-frontiers` | V4 5-Frontiers Champion | `v4_value_net_best.pt` | 1,000-game baseline configuration with pre-endgame parity and belief tracking. 54.2% win rate (+9.8 pts spread) vs Base MAGPIE. Aliases: `frontiers`, `v5-frontier-v4`. |
| `--model rl-gen1` | V4 RL Gen-1 Policy | `v4_value_net_rl_gen1.pt` | Policy gradient fine-tuning with anchored teacher loss. Aliases: `rl`, `self-play`. |
| `--model scaled` | Deep Scaled 2-Ply | `v4_value_net_best.pt` | 2-ply lookahead ($K=12, N=20$) for deep tournament search. Aliases: `deep-scaled`, `deep`. |
| `--model v4-baseline` | V4 1-Ply Baseline | `v4_value_net_best.pt` | Standard 1-ply BAMS without 2-ply lookahead (52.2% win rate, +4.3 pts). Alias: `baseline`. |
| `--model static-magpie` | Base MAGPIE | None (C solver) | Classical C static equity solver using precomputed KLV tables (no neural evaluation). Alias: `magpie`. |

### 3. Loading custom checkpoints
To load a specific weight file:
```bash
python cli.py tournament --model-path alphable_v4/models/checkpoints/v4_value_net_rl_gen1.pt --opponent magpie --games 50
```

---

## Running and comparing models

### 1. Standard tournaments against Base MAGPIE
To test win rates against Base MAGPIE:
```bash
# Test the latest calibrated model
python cli.py tournament --model latest --opponent magpie --games 1000

# Test the 5-frontiers baseline
python cli.py tournament --model 5-frontiers --opponent magpie --games 1000

# Test the 1-ply baseline
python cli.py tournament --model v4-baseline --opponent magpie --games 1000

# Test the RL fine-tuned checkpoint
python cli.py tournament --model rl-gen1 --opponent magpie --games 1000
```
Omitting `--model` defaults to `latest`.

### 2. Head-to-head model comparisons
You can test two models directly with alternating first turns:
```bash
# Latest champion vs 5-frontiers
python cli.py tournament --model latest --opponent 5-frontiers --games 50

# Latest champion vs 1-ply baseline
python cli.py tournament --model latest --opponent v4-baseline --games 50

# RL Gen-1 vs 5-frontiers
python cli.py tournament --model rl-gen1 --opponent 5-frontiers --games 50
```

### 3. Duplicate matches (`--duplicate`)
Standard Scrabble matches have 5% to 10% outcome variance from tile bag draws. Using `--duplicate` plays every game seed twice with swapped player seats:
- Game A: Model 1 plays Player 1, Model 2 plays Player 2 on seed $S$.
- Game B: Model 2 plays Player 1, Model 1 plays Player 2 on the same seed $S$.
```bash
python cli.py tournament --model latest --opponent 5-frontiers --games 30 --duplicate
```
The CLI reports net pair score differentials and duplicate match wins, removing tile draw variance.

### 4. Cross-generation matches against Alphable V3
You can evaluate Alphable V4 against earlier Alphable V3 baselines:
```bash
# Against Alphable V3 Macondo ResNet (63 dimensions)
python cli.py tournament --model latest --opponent v3-resnet --games 100

# Against Alphable V3 SmolLM2-135M transformer candidate ranker
python cli.py tournament --model latest --opponent v3-transformer --games 10
```

---

## Visualizer Studio

Alphable includes a dedicated visualizer web application for inspecting games, evaluating move options, and reviewing tournament runs:

```bash
# Launch from the repository root
./start_visualizer.sh

# Or start from the visualizer directory
cd visualizer && ./run.sh
```

The server runs at `http://localhost:5000` and provides:
- Interactive board display with move coordinates and score annotations
- Move candidate ranker showing static equity, opponent threat, and neural value components
- Game replay browser that loads completed matches from `data/tournaments/`
- Real-time position analysis on custom board setups

---

## Tournament history and run comparison

Tournament runs automatically save telemetry to `data/tournaments/` and append a record to the master ledger at `data/tournaments/tournament_history.jsonl`.

### 1. View benchmark history
```bash
python cli.py history
```
Displays a table of completed runs with Run ID, timestamp, match type (standard or duplicate), matchup, game count, win rate, net spread with 95% confidence intervals, and paired t-test results.

### 2. Inspect a specific run
```bash
# Inspect by full run ID
python cli.py history --show run_20261015_215837

# Or by date prefix
python cli.py history --show 20261015
```

### 3. Compare two runs
```bash
python cli.py history --compare run_20261013_143000 run_20261015_215837
```
Calculates deltas for win rate, point spread, bingo rates, confidence interval widths, and turn speed.

### 4. Filtering history
```bash
# Filter by tag
python cli.py history --tag "duplicate"

# Filter by model
python cli.py history --model "5-frontiers"
```

---

## How Alphable V4 differs from Base MAGPIE

Base MAGPIE and Alphable V4 use different evaluation criteria when selecting plays.

### 1. Base MAGPIE evaluation
Base MAGPIE is a classical C Scrabble solver. Given a board and rack, it calculates:
$$\text{Static Equity} = \text{Immediate Points} + \text{Leave Value}$$
- Immediate points: score from the played tiles.
- Leave value: estimated value of remaining rack tiles from precomputed static tables (KLV).

Base MAGPIE does not track what tiles the opponent is likely to hold, does not simulate the opponent's counter-replies, and does not evaluate how the play alters the defensive topology of the board.

### 2. Alphable V4 evaluation
Alphable V4 searches candidate plays using Belief-Augmented Monte Carlo Search (BAMS):
$$\text{BAMS\_Score}(c) = \text{Static Eq}(c) - \beta \cdot \mathbb{E}[\text{OppScore}(c)] + \gamma \cdot \mathbb{E}[V(S')] + \Delta_{\text{2ply}}(c) + \Omega_{\text{vol}}(S')$$

The algorithm incorporates four factors:
1. Bayesian rack inference (`BayesianRackInference`): samples opponent racks from unseen tiles using Dirichlet-multinomial sampling with Common Random Numbers (CRN), ensuring consistent comparisons across candidate moves.
2. Monte Carlo rollouts: simulates opponent replies to estimate immediate counter-threats.
3. Neural value network (`V4ValueNetwork`): evaluates the resulting 15×15 after-state board tensor (32 channels) and 64-dimensional game state vector using ResNet-18 with cross-attention (1.96 ms on GPU for 100 states).
4. Volatility adjustment: penalizes open lanes when defending a lead ($\Delta \ge 20$) and values high-variance board positions when trailing ($\Delta \le -20$).

### 3. Example move divergence in terminal analysis

Running an analysis demonstrates where the evaluations differ:
```bash
python cli.py analyze --model latest --rack RETINAS
```

Example output:
```text
#   Move           Pts   Leave   Static Eq   Opp Threat   Neural Val   BAMS Score
--------------------------------------------------------------------------------
1   8B ANESTRI     66            66.00       46.7 pts     +0.1290      65.91      [BASE MAGPIE #1]
6   8D ANESTRI     66            66.00       42.5 pts     +0.3774      68.38      [AI CHOSEN #1]
--------------------------------------------------------------------------------
Base MAGPIE Latency: 0.67 ms | AI Policy Latency: 839.05 ms

DECISION SUMMARY:
  • Base MAGPIE Choice : 8B ANESTRI (Score: 66, Static Equity: 66.00)
  • AI Policy Choice   : 8D ANESTRI (Score: 66, BAMS Score: 68.38)

  >>> [AI DIVERGENCE DETECTED] <<<
  The AI policy selected 8D over Base MAGPIE's top choice 8B.
```

In this position:
- Both `8B ANESTRI` and `8D ANESTRI` score 66 points and leave empty racks.
- Base MAGPIE treats them as identical (static equity 66.00).
- The Monte Carlo simulation indicates that `8D` lowers the opponent's average reply from 46.7 points to 42.5 points.
- The neural value network rates the resulting board position higher for `8D` (+0.3774 vs +0.1290).
- BAMS selects `8D` based on lower counter-threat and stronger board control.
