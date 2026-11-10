# Alphable V4: Scientific Paper & Public Release Design Specification

- **Date:** 2026-11-10
- **Status:** Approved
- **Target Branch:** `alphable_V4_paper_base`
- **Authors:** Alphable Research Team
- **License:** GNU General Public License v3.0 (GPLv3)

---

## 1. Executive Summary

This design specification establishes two interconnected deliverables for the Alphable project:
1. **An arXiv-tier Machine Learning Research Paper** authored in modular LaTeX, providing a rigorous mathematical formulation, architectural description, empirical statistical proofs, and an adversarial ceiling audit of Alphable V4 in imperfect-information Scrabble.
2. **A Production-Grade Public GitHub Repository Release**, structuring Alphable for open-source publication in accordance with open-science reproducibility standards, complete with GPLv3 licensing, GitHub citation metadata (`CITATION.cff`), visual architecture documentation, and automated benchmark reproduction scripts.

---

## 2. Scientific Paper Specification (`paper/`)

### 2.1 File Organization & Architecture
The LaTeX manuscript is decomposed into modular files under `paper/`:

```
paper/
├── main.tex                    # Master driver: documentclass, typography, layout, bibliography
├── macros.tex                  # Global notation macros (\E, \Var, \Cov, \cS, \cA, \cB, \Delta)
├── references.bib              # BibTeX database with verified scholarly entries
├── sections/
│   ├── 00_abstract.tex         # Abstract: POMDP, BAMS, Cross-Attention, +7.06 pt spread, limits
│   ├── 01_introduction.tex     # Imperfect-information challenges, baseline gap, contributions
│   ├── 02_related_work.tex     # Maven, Quackle, Macondo, MAGPIE, Sokota et al. 2026, AlphaZero
│   ├── 03_game_formulation.tex # POMDP tuple, hidden information, Strategy Fusion flaw
│   ├── 04_neural_architecture.tex # 28-channel tensor, ResNet-18, Cross-Attention rack embeddings
│   ├── 05_bams_search.tex      # 2-ply nested BAMS, Bayesian opponent belief tracking, volatility
│   ├── 06_late_game.tex        # Bag parity tracking, power-tile sticking, exact alpha-beta solver
│   ├── 07_experiments.tex      # 10,000-game duplicate benchmark, paired t-tests, Wilson CIs, phase breakdown
│   ├── 08_critical_audit.tex   # Default vs Tuned MAGPIE ceiling, PAT transferability, SOTA comparison
│   └── 09_conclusion.tex       # Summary of contributions, throughput trade-offs, future directions
└── appendix/
    ├── proof_crn.tex           # Mathematical proof of CRN variance reduction via Harris-FKG inequality
    └── proof_duplicate.tex     # Mathematical proof of duplicate score cancellation
```

### 2.2 Mathematical Content & Proofs
- **Formal POMDP Definition**:
  $$\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{T}, \mathcal{R}, \Omega, \mathcal{O}, \gamma \rangle$$
  where hidden state $s = (B, r_1, r_2, b, \Delta, t, p)$ is partially observed via $o_1(s) = (B, r_1, b \cup r_2, \Delta, t, p)$.
- **Strategy Fusion Flaw**: Detailed theoretical derivation demonstrating why classical Perfect Information Monte Carlo (PIMC) fails in Scrabble due to assuming future clairvoyance over opponent unplayed tiles, overvaluing brittle speculative defenses.
- **Theorem 1 (CRN Variance Reduction)**: Formal proof using the Harris-FKG inequality that candidate evaluations under Common Random Numbers achieve strictly positive covariance ($\rho \in [0.65, 0.85]$), eliminating $65\%$ to $85\%$ of candidate estimation variance:
  $$\mathbb{V}\text{ar}(\hat{\Delta}_{\text{CRN}}) = \mathbb{V}\text{ar}(\hat{\Delta}_{\text{IRN}}) \left( 1 - \frac{2 \rho \sigma_1 \sigma_2}{\sigma_1^2 + \sigma_2^2} \right)$$
- **Theorem 2 (Duplicate Score Algebraic Cancellation)**: Proof that paired duplicate scoring cancels out first-mover advantage and tile distribution luck:
  $$\Delta_{\text{pair}}(s) = (\mu_1 - \mu_2) + \bar{\xi}(s), \quad \mathbb{E}[\Delta_{\text{pair}}(s)] = \mu_1 - \mu_2$$

### 2.3 Empirical Reporting & Scientific Rigor
- **Primary Claim**: Alphable V4 Champion outperforms **1-ply Static KLV Base MAGPIE** by $+7.06 \pm 0.81$ pts/game ($55.63\%$ win rate across 10,000 duplicate games, paired $t = 8.749, p = 2.9 \times 10^{-18}$).
- **Phase Sensitivity**: Early game absorbs slight deficits ($-4.00$ pts over turns 1–5 and midgame) to engineer an insurmountable $+17.67$ point compound late-game advantage (pre-endgame bag parity $+7.60$ pts; exact endgame solver $+10.07$ pts).
- **Explicit Parameter Ceiling & Limitations**:
  - Unqualified claims of defeating "MAGPIE" are rejected; Tuned MAGPIE (incorporating `-pat CSW24`, native C PIMC rollouts at 98,134 nps, and exact endgame solvers) achieves $+46.48$ pts over V4.
  - Candidate generator transferability: passing `-pat CSW24` into V4's generator yields a $+2.05$ pt net spread boost and $50\%$ decision divergence on benchmark positions.
  - Native throughput trade-off: C implementation (~98k nps) vs. PyTorch neural inference (~65 ms/turn).

---

## 3. Public GitHub Repository Release Specification

### 3.1 Licensing & Compliance
- **License**: GNU General Public License v3.0 (`LICENSE`), ensuring complete copyleft compliance with the dynamically linked `vendor/magpie/` C library.

### 3.2 Academic Metadata & Contribution
- **`CITATION.cff`**: Standardized Citation File Format metadata providing title, authors, repository URL, date, and preferred bibtex citation.
- **`CONTRIBUTING.md`**: Guide for development, environment setup, pytest test suite execution, and pull request workflows.

### 3.3 Root Documentation Overhaul (`README.md`)
- **Badges**:
  - Test Suite: 185 Passed (`pytest`)
  - License: GPLv3
  - Python: 3.10+
  - Paper: arXiv Preprint PDF
- **Architecture Diagram**: Mermaid/ASCII workflow showing MAGPIE C candidate generation $\to$ Cross-Attention Value Network $\to$ Bayesian Opponent Rack Tracker $\to$ BAMS 2-Ply Search $\to$ Move Selection.
- **Quickstart Guide**:
  - One-line installation (`./install.sh`)
  - Running sample game / position analysis (`python cli.py analyze --rack ...`)
  - Running tournament evaluations (`python cli.py tournament --duplicate --games 100`)
- **Key Empirical Results**: Formatted markdown tables summarizing the 10,000-game duplicate benchmark and phase breakdown.
- **BibTeX Citation Snippet**.

### 3.4 Automation & Reproducibility Scripts
- **`scripts/build_paper.sh`**: Automated shell script running `pdflatex` $\to$ `bibtex` $\to$ `pdflatex` $\to$ `pdflatex` to produce `paper/alphable_v4.pdf` with error checking and clean artifact management.
- **`scripts/reproduce_benchmarks.sh`**: One-entry script offering:
  1. Instant statistical verification of the 10,000-game dataset.
  2. Quick 10-game duplicate validation run.
  3. Configurable full tournament benchmark execution.

---

## 4. Verification Criteria
1. `paper/alphable_v4.pdf` compiles cleanly with zero LaTeX errors or missing reference warnings.
2. All 185 tests in `tests/` and `visualizer/tests/` pass cleanly without regression.
3. `scripts/reproduce_benchmarks.sh` verifies the 10,000-game statistical calculations identically to the paper.
4. Repository root is fully documented, properly licensed under GPLv3, and clean of untracked temporary files.
