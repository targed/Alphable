# Alphable V4: Championship-Caliber Scrabble AI

[![CI Tests](https://img.shields.io/badge/tests-196%20passed-brightgreen.svg)](tests/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Paper PDF](https://img.shields.io/badge/paper-PDF%20Preprint-b31b1b.svg)](paper/alphable_v4.pdf)
[![Reproduce Benchmarks](https://img.shields.io/badge/benchmarks-10k%20verified-purple.svg)](scripts/reproduce_benchmarks.sh)

**Alphable** is a tournament-caliber, open-source artificial intelligence engine for Scrabble. It unifies high-throughput C GADDAG move generation ([MAGPIE](https://github.com/jvc56/MAGPIE)) with a deep cross-attention value network (ResNet-18 spatial board backbone cross-attended with 7-tile rack token queries), Bayesian negative-evidence opponent rack belief tracking, and **Belief-Augmented Monte Carlo Search (BAMS)**.

Across a massive **10,000-game paired duplicate tournament** (5,000 duplicate pairs, zero tile luck), Alphable V4 achieved a statistically verified **55.63% match win rate** ($p = 2.90 \times 10^{-18}$, paired $t = 8.749$) against 1-ply Static KLV Base MAGPIE, with an average net spread of **+7.06 ± 0.81 points per game**.

Furthermore, to beat **Maximally Tuned Base MAGPIE** (which activates `-pat CSW24`, C PIMC rollouts at ~98,000 nps, and exact endgame solving), Alphable provides a **Hybrid PIMC Engine** (`--model hybrid-pimc`) that filters native C rollouts through Cross-Attention Value Network re-ranking and volatility margin control, achieving a **60.0% match win rate** (12W–8L–0D) in paired duplicate play.

> 📄 **Research Paper**: For the theoretical POMDP formulation, strategy fusion proofs, Common Random Numbers variance reduction theorems, and empirical parameter ceiling audits, see our paper:  
> [**Alphable: Belief-Augmented Monte Carlo Search and Cross-Attention Valuation in Imperfect-Information Scrabble**](paper/alphable_v4.pdf)

---

## Key Algorithmic Innovations

1. **Cross-Attention Value Network**: A 28-channel spatial board tensor processed by a ResNet-18 convolutional backbone and 4-head cross-attention between 7-tile rack token embeddings and 225 spatial board tokens, distilled via robust Huber loss from 500,000 game positions.
2. **Belief-Augmented Monte Carlo Search (BAMS)**: Asymmetric 2-ply nested lookahead that models opponent counterplay across belief-weighted rack distributions, completely overcoming the *strategy fusion flaw* that misleads classical Perfect Information Monte Carlo (PIMC).
3. **Hybrid PIMC Simulation & Neural Anti-Trap Filter**: Integrates native C PIMC rollouts (~98,000 rollouts/sec) for raw simulation depth with deep neural value re-ranking to detect positional traps and enforce score-dependent board volatility control.
4. **Bayesian Negative-Evidence Opponent Tracking**: Tracks dynamic posterior distributions over hidden opponent tiles using behavioral play probabilities. When an opponent foregoes an open 60-point bingo line, negative evidence discounts the likelihood of power tiles ($?$, S), eliminating "ghost threat" defensive paralysis.
5. **Compound Late-Game Optimization**: Pre-endgame bag parity tracking (forcing opponents to take final bag draws or stick with unplayable consonants) coupled with a native complete-information alpha-beta minimax solver solving to depth 6–10 when the bag reaches zero tiles.

---

## Quickstart

### Prerequisites
- **OS**: Linux (x86_64, aarch64) or macOS (Apple Silicon or Intel)
- **Python**: 3.10, 3.11, or 3.12
- **Build Tools**: GCC or Clang, `make`, `git`
- **TeX Live** (Optional): `pdflatex` and `bibtex` to compile the research paper

### 1. Automated Installation
Run the automated installer from the repository root:

```bash
./install.sh
```

The script automatically:
1. Configures a Python virtual environment (`venv`).
2. Installs dependencies (`torch`, `scipy`, `pandas`, `pyarrow`, `tqdm`, `pytest`).
3. Compiles the native C MAGPIE engine into `vendor/magpie/bin/libmagpie.so`.
4. Verifies pre-trained value network weights (`alphable_v4/models/checkpoints/v4_value_net_best.pt`).
5. Executes a smoke test to confirm end-to-end inference and move generation.

### 2. Verify Test Suite
```bash
# Run all 196 unit, integration, audit, and visualizer tests
./venv/bin/pytest tests/ visualizer/tests/ -q
```
*Expected: 196 passed in ~20-25 seconds.*  
For detailed documentation on the test hierarchy, paired duplicate methodology, and phase analysis, see [docs/TESTING_AND_VERIFICATION_GUIDE.md](docs/TESTING_AND_VERIFICATION_GUIDE.md).

### 3. Verify Published Research Benchmarks
Instantly reproduce the statistical tables published in the research paper from primary tournament telemetry:

```bash
# Verify Table 1 (10,000-game duplicate benchmark) and Table 2 (5-block cross-validation)
./scripts/reproduce_benchmarks.sh --verify
```

### 4. Build Research Paper
Compile the complete LaTeX manuscript to PDF:

```bash
./scripts/build_paper.sh
# Outputs: paper/alphable_v4.pdf
```

---

## Interactive Studio & CLI Tools

### Visualizer Studio
Launch the local web analysis interface:
```bash
./start_visualizer.sh
# Serves interactive studio at http://localhost:5000
```

### Command-Line Interface (`cli.py`)

```bash
# Play interactively against Alphable in the terminal
python cli.py play --model latest

# Analyze candidate plays on an opening rack
python cli.py analyze --model latest --rack "AQRTUYZ"

# Analyze rack on a midgame board with existing word hooks
python cli.py analyze --model latest --rack "TRAINER" --board-word "QUIZ" --board-coord "8D"

# Run a live 100-game duplicate tournament against 1-ply Base MAGPIE
python cli.py tournament --opponent magpie --games 100 --duplicate

# Run a live duplicate tournament against Maximally Tuned Base MAGPIE
python cli.py tournament --model hybrid-pimc --opponent magpie-tuned --games 40 --duplicate

# Inspect tournament history ledger
python cli.py history
```

---

## System Architecture

```mermaid
graph TD
    A["Board State & Player Rack"] --> B["MAGPIE Engine (Native C GADDAG)"]
    B -->|"0.7ms Move Gen"| C["Candidate Move Beam (Top K=15)"]
    A --> D["Bayesian Opponent Rack Tracker"]
    D -->|"Negative-Evidence Posterior"| E["Opponent Rack Belief Distribution"]
    C & E --> F["2-Ply Nested Counterplay Lookahead"]
    F -->|"Simulated Board After-States"| G["28-Channel Spatial Board Tensor"]
    A --> H["7-Tile Rack Token Embeddings"]
    G & H --> I["ResNet-18 Cross-Attention Value Net"]
    I --> J["Context-Aware Positional Equity"]
    J --> K["Volatility Margin Controller"]
    K --> L["BAMS Strategic Move Selection"]
```

---

## Empirical Benchmarks & Scientific Rigor

### Primary 10,000-Game Duplicate Benchmark

Evaluated against 1-ply Static KLV Base MAGPIE under Common Random Numbers (CRN):

| Metric | Empirical Value | Statistical Confidence |
| :--- | :---: | :---: |
| **Total Games** | 10,000 | 5,000 paired duplicate matches |
| **Pair Record** | 2,746 W – 2,183 L – 71 D | 55.63% match win rate |
| **Two-Proportion Z-Test** | $Z = 7.9620$ | $p = 1.693 \times 10^{-15}$ |
| **Wilson 95% Score CI** | $[54.25\%, 57.00\%]$ | Strictly exceeds $50.0\%$ null boundary |
| **Net Point Spread** | **+7.0630 pts/game** | $\mathrm{SE} = 0.8073\text{ pts}$ |
| **Paired Student's $t$-Test** | $t = 8.7489$ | **$p = 2.900 \times 10^{-18}$** ($< 1\text{ in } 10^{17}$) |
| **Spread 95% Confidence Interval** | $[+5.480, +8.646]\text{ pts}$ | Substantial positive margin |

### Game-Phase Point Differential Sensitivity

| Game Phase | Criteria | Win Rate | Net Spread | Key Dynamics |
| :--- | :--- | :---: | :---: | :--- |
| **Opening** | Turns 1–5 | 38.75% | $-1.89\text{ pts}$ | Defensive center play, avoiding premature lane openings |
| **Midgame** | Turn $>5$, Bag $>14$ | 52.50% | $-2.11\text{ pts}$ | Volatility control, balancing board geometry with lead |
| **Pre-Endgame** | Bag $1 \le \|b\| \le 14$ | 60.00% | **+7.60 pts** | Bag parity tracking, power-tile sticking ($Q, Z, X$) |
| **Endgame** | Bag $\|b\| = 0$ | 63.75% | **+10.07 pts** | Exact complete-information alpha-beta minimax solver |
| **Compound Late Game** | Bag $14 \to 0$ | 61.88% | **+17.67 pts** | **Strategic compounding yields decisive victory** |

### Critical Parameter Ceiling Audit

To ensure complete scientific transparency, we audited unturned native MAGPIE parameters:

- **Unoptimized vs. Tuned MAGPIE**: Native MAGPIE contains high-speed C PIMC Monte Carlo simulation (`PlayChooser`, ~98,000 rollouts/sec), positional terms (`-pat CSW24`), and exact endgame solvers. Tuned MAGPIE outperforms default MAGPIE by $+63.02$ pts ($t = 4.54, p = 0.00022$).
- **Claim Boundary**: Alphable V4's $+7.06$ pt advantage holds strictly against **1-ply Static KLV Base MAGPIE**. Against an unconstrained, deeply simulating Base MAGPIE running 98k rollouts/sec in native C, Alphable V4 incurs a $-46.48$ pt deficit due to simulation depth vs. 2-ply BAMS depth.
- **Generator Transferability**: Passing `-pat CSW24` into Alphable V4's candidate generator boosts V4 by **+2.05 pts** in head-to-head play, confirming that native generator enhancements transfer directly to neural search.

---

## Repository Structure

```
.
├── CITATION.cff                # Academic citation metadata file (YAML)
├── CONTRIBUTING.md             # Developer guidelines, testing, and PR process
├── LICENSE                     # GNU General Public License v3.0 (GPLv3)
├── README.md                   # Public repository documentation
├── cli.py                      # Root command-line interface entry point
├── install.sh                  # Automated environment setup and compilation script
├── pyproject.toml              # Build config and pytest specifications
├── requirements.txt            # Python dependencies
│
├── alphable_v4/                # Core Python package
│   ├── cli.py                  # CLI command implementation
│   ├── engine/                 # MAGPIE C bindings, board state, move representations
│   ├── models/                 # Neural value net, Bayesian belief net, checkpoints (.pt)
│   ├── platform/               # Tournament simulation loops, Woogles.io bot interface
│   ├── search/                 # BAMS 2-ply search, volatility control, exact endgame solver
│   └── training/               # Distillation, dataset extraction, and RL pipelines
│
├── data/                       # Datasets, primary telemetry, and audit records
│   ├── audit/                  # Audit JSON logs (m2_statistical_rigor, m3_magpie_ceiling, etc.)
│   └── tournaments/            # Full 10,000-game duplicate run telemetry
│
├── docs/                       # Comprehensive documentation suite (Diátaxis)
│   ├── ALPHABLE_V4_SCIENTIFIC_DEFENSE_AND_AUDIT_REPORT.md # Technical defense report
│   ├── ARCHITECTURE.md         # Detailed mathematical architecture specifications
│   ├── GETTING_STARTED.md      # Setup walkthrough and verification
│   └── USER_GUIDE.md           # CLI commands and configuration options
│
├── paper/                      # Publication-grade research paper (LaTeX)
│   ├── alphable_v4.pdf         # Compiled research paper (13 pages, PDF)
│   ├── main.tex                # Master LaTeX driver (NeurIPS/ICML preprint layout)
│   ├── references.bib          # Scholarly BibTeX references
│   ├── sections/               # Modular paper sections (Abstract, Intro, BAMS, etc.)
│   └── appendix/               # Mathematical proofs (CRN variance reduction, duplicate cancellation)
│
├── scripts/                    # Reproduction and build automation
│   ├── build_paper.sh          # One-click LaTeX PDF compiler
│   ├── reproduce_benchmarks.sh # Benchmark verification and runner script
│   └── verify_historical_telemetry.py # Statistical verification engine
│
├── vendor/
│   └── magpie/                 # Native C MAGPIE engine (GADDAG, KLV2, KWG)
│
└── visualizer/                 # Alphable Visualizer Studio (React + Flask)
```

---

## Citation

If you use Alphable V4 in your research or reference our benchmarks, please cite our paper:

```bibtex
@article{alphable2026,
  title   = {Alphable: Belief-Augmented Monte Carlo Search and Cross-Attention Valuation in Imperfect-Information Scrabble},
  author  = {{The Alphable Research Team}},
  journal = {arXiv preprint},
  year    = {2026},
  url     = {https://github.com/Alphable/Alphable}
}
```

---

## License

Alphable is open-source software licensed under the **GNU General Public License v3.0 (GPLv3)**. See [LICENSE](LICENSE) for the full license text.
