# Alphable V4: Scientific Paper & Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a publication-grade, arXiv-level machine learning research paper in modular LaTeX and prepare the Alphable repository for public GitHub release under GPLv3 with full reproducibility tooling.

**Architecture:** A modular LaTeX manuscript in `paper/` compiled via `scripts/build_paper.sh` alongside public open-source standards (`LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`, polished `README.md`, and `scripts/reproduce_benchmarks.sh`).

**Tech Stack:** LaTeX (`pdflatex`, `bibtex`, `booktabs`, `microtype`, `amsmath`, `algorithm2e`), Python 3.10+ (`alphable_v4`, `torch`, `scipy`, `pandas`), Bash, Markdown.

**Spec:** [docs/superpowers/specs/2026-11-10-alphable-v4-paper-and-public-release-design.md](file:///home/targed/Documents/Git/Alphable/docs/superpowers/specs/2026-11-10-alphable-v4-paper-and-public-release-design.md)

## Global Constraints
- Target branch: `alphable_V4_paper_base`.
- License: GNU General Public License v3.0 (GPLv3) throughout.
- Claims: Primary claim strictly bounded to **1-ply Static KLV Base MAGPIE** (+7.06 pts, $55.63\%$ WR, $p < 10^{-17}$); parameter ceiling of Tuned MAGPIE and Macondo explicitly documented.
- All 185 existing tests in `tests/` and `visualizer/tests/` must continue to pass without regression.
- LaTeX document must compile cleanly with `scripts/build_paper.sh` into `paper/alphable_v4.pdf`.

---

### Task 1: Public Release Licensing & Academic Metadata

**Files:**
- Create: `LICENSE`
- Create: `CITATION.cff`
- Create: `CONTRIBUTING.md`

**Interfaces:**
- Consumes: Project details, GPLv3 text, citation information.
- Produces: GitHub standard open-source metadata.

- [ ] **Step 1: Create `LICENSE` with standard GNU GPLv3 text**
- [ ] **Step 2: Create `CITATION.cff` with complete CFF 1.2.0 metadata for Alphable V4**
- [ ] **Step 3: Create `CONTRIBUTING.md` with development setup, testing instructions, and PR guidelines**
- [ ] **Step 4: Verify metadata file syntax and commit**

---

### Task 2: LaTeX Document Foundation & Compilation Tooling

**Files:**
- Create: `paper/main.tex`
- Create: `paper/macros.tex`
- Create: `paper/references.bib`
- Create: `scripts/build_paper.sh`

**Interfaces:**
- Consumes: TeX Live pdflatex and bibtex binaries.
- Produces: Compilable LaTeX harness and automated build script.

- [ ] **Step 1: Create `paper/macros.tex` with mathematical operators and shorthand notation**
- [ ] **Step 2: Create `paper/references.bib` with verified scholarly references (Sokota et al. 2026, Sheppard 2002, O'Laughlin 2006, Silver et al., etc.)**
- [ ] **Step 3: Create `paper/main.tex` with two-column preprint layout, package imports, and section includes**
- [ ] **Step 4: Create executable `scripts/build_paper.sh` running multi-pass pdflatex and bibtex**
- [ ] **Step 5: Test compilation of initial skeleton and commit**

---

### Task 3: Scientific Paper Sections: Abstract, Introduction, Related Work, and POMDP Formulation

**Files:**
- Create: `paper/sections/00_abstract.tex`
- Create: `paper/sections/01_introduction.tex`
- Create: `paper/sections/02_related_work.tex`
- Create: `paper/sections/03_game_formulation.tex`

**Interfaces:**
- Consumes: `paper/macros.tex`, `paper/references.bib`.
- Produces: Core front-matter and theoretical foundation of the paper.

- [ ] **Step 1: Write `paper/sections/00_abstract.tex` summarizing imperfect information in Scrabble, BAMS, +7.06 pt spread, and ceiling limits**
- [ ] **Step 2: Write `paper/sections/01_introduction.tex` establishing motivation, baseline gaps, and four primary scientific contributions**
- [ ] **Step 3: Write `paper/sections/02_related_work.tex` positioning Alphable within classical engines (Maven, Quackle, Macondo) and modern RL in IIGs (Ataraxos, AlphaZero)**
- [ ] **Step 4: Write `paper/sections/03_game_formulation.tex` detailing formal POMDP tuple, information sets, and the Strategy Fusion flaw of classical PIMC**
- [ ] **Step 5: Compile paper and verify zero syntax errors in Sections 0–3**

---

### Task 4: Scientific Paper Sections: Neural Value Network, BAMS Search, and Late Game Solvers

**Files:**
- Create: `paper/sections/04_neural_architecture.tex`
- Create: `paper/sections/05_bams_search.tex`
- Create: `paper/sections/06_late_game.tex`

**Interfaces:**
- Consumes: Codebase architectures (`alphable_v4/models/`, `alphable_v4/search/bams.py`, `alphable_v4/search/endgame.py`).
- Produces: Complete algorithmic methodology sections with formal pseudo-code algorithm blocks.

- [ ] **Step 1: Write `paper/sections/04_neural_architecture.tex` (28-channel spatial tensor, ResNet-18 residual blocks, Cross-Attention rack embeddings, Huber loss KLV2 distillation)**
- [ ] **Step 2: Write `paper/sections/05_bams_search.tex` (2-ply nested BAMS algorithm block, Bayesian negative-evidence belief updates, volatility margin control)**
- [ ] **Step 3: Write `paper/sections/06_late_game.tex` (pre-endgame bag parity sticking, exact minimax alpha-beta solver with transposition tables)**
- [ ] **Step 4: Compile paper and verify algorithm blocks and mathematical typesetting**

---

### Task 5: Scientific Paper Sections: Empirical Benchmarks, Critical Parameter Ceiling Audit, and Mathematical Appendix

**Files:**
- Create: `paper/sections/07_experiments.tex`
- Create: `paper/sections/08_critical_audit.tex`
- Create: `paper/sections/09_conclusion.tex`
- Create: `paper/appendix/proof_crn.tex`
- Create: `paper/appendix/proof_duplicate.tex`

**Interfaces:**
- Consumes: Audit data (`data/audit/m2_statistical_rigor.json`, `data/audit/m3_magpie_ceiling.json`, `data/audit/m4_sota_comparative.json`).
- Produces: Empirical results, critical audit analysis, conclusion, and rigorous mathematical proofs.

- [ ] **Step 1: Write `paper/sections/07_experiments.tex` with publication booktabs tables (10,000-game duplicate benchmark, 5-block consistency, phase breakdown)**
- [ ] **Step 2: Write `paper/sections/08_critical_audit.tex` detailing unoptimized vs tuned MAGPIE ceiling (+63 pt gap), PAT generator transferability (+2.05 pts), and C vs PyTorch throughput trade-offs**
- [ ] **Step 3: Write `paper/sections/09_conclusion.tex` summarizing findings, limitations, and future research directions**
- [ ] **Step 4: Write `paper/appendix/proof_crn.tex` (formal theorem and proof of CRN variance reduction via Harris-FKG inequality) and `paper/appendix/proof_duplicate.tex` (proof of duplicate score cancellation)**
- [ ] **Step 5: Compile complete paper into `paper/alphable_v4.pdf` and verify all citations, cross-references, equations, and tables**

---

### Task 6: Benchmark Reproduction Script & Historical Data Validator

**Files:**
- Create: `scripts/reproduce_benchmarks.sh`
- Test: Historical telemetry in `data/tournaments/` and `data/audit/`

**Interfaces:**
- Consumes: `alphable_v4/cli.py`, `data/tournaments/run_20261016_155029_V4-Champion_vs_Base-MAGPIE_10000g_dup.json`.
- Produces: Executable CLI tool for reproducible tournament validation.

- [ ] **Step 1: Create `scripts/reproduce_benchmarks.sh` with modes for (a) fast statistical verification of the 10,000-game dataset, (b) 10-game duplicate smoke test, (c) full duplicate tournament**
- [ ] **Step 2: Make `scripts/reproduce_benchmarks.sh` executable and test mode (a) verifying identical numbers reported in paper**
- [ ] **Step 3: Commit reproduction script**

---

### Task 7: Root Documentation & Public Presentation Overhaul

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Paper abstract, benchmark tables, CLI syntax, visualizer overview.
- Produces: Professional GitHub landing page.

- [ ] **Step 1: Overhaul `README.md` with shields.io badges (Tests, License, Python, arXiv PDF link)**
- [ ] **Step 2: Add visual ASCII / Mermaid architecture diagram showing MAGPIE $\to$ Value Net $\to$ Bayesian Belief $\to$ BAMS Search $\to$ Move Selection**
- [ ] **Step 3: Add quickstart installation, CLI usage examples, and reproduction guide**
- [ ] **Step 4: Add benchmark results summary table and academic BibTeX citation snippet**
- [ ] **Step 5: Verify all links and formatting in `README.md`**

---

### Task 8: Full End-to-End Build, Verification, and Git Integrity Check

**Files:**
- Verify: `paper/alphable_v4.pdf`
- Verify: Full pytest test suite
- Verify: Git working tree clean on `alphable_V4_paper_base`

- [ ] **Step 1: Execute `scripts/build_paper.sh` and verify clean PDF generation**
- [ ] **Step 2: Execute `./venv/bin/pytest tests/ visualizer/tests/ -q` and verify all 185 tests pass**
- [ ] **Step 3: Run `git status` and verify clean working tree with all artifacts committed**
