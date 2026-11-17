# Paper Revision: Single-Column Layout, Fluid Academic Prose, and Visual Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the Alphable research paper into an authentic, publication-grade academic manuscript in single-column format, transforming bullet-pointed and over-mathematized sections into fluid prose, enriching visual presentation with architecture and tactical board figures, while strictly preserving Luke Kaiser's author attribution and verified 10,000-game dataset.

**Architecture:** Transition LaTeX structure from `twocolumn` to single-column `11pt` with balanced margins (`geometry`); convert list-heavy enumerations into coherent paragraphs; prune superficial mathematical clutter while retaining rigorous proofs; embed vector TikZ diagrams for system architecture and first-turn initiative; recompile cleanly via `pdflatex` with zero warnings.

**Tech Stack:** LaTeX2e, TikZ, PGFPlots, `booktabs`, `microtype`, `natbib`, `pdflatex`, `bibtex`.

**Spec:** User directives from chat: single-column layout, removal of list/bullet clutter in favor of academic prose, pruning of overused formulas and AI phrasing, addition of architectural and board visualization diagrams, strict preservation of author edits (Luke Kaiser, `ltklionel@gmail.com`, `https://github.com/targed/Alphable`, 10,000 games / 5,000 duplicate pairs, $\nu=5,000$).

## Global Constraints

- Author MUST remain `\textbf{Luke Kaiser}`, correspondence `\texttt{ltklionel@gmail.com}`, repository `\url{https://github.com/targed/Alphable}`.
- Primary empirical dataset MUST remain 10,000 games (5,000 duplicate pairs), $\nu = 5,000$, with $+4.15$ pts/game, $t = 5.5517$, $p = 2.83 \times 10^{-8}$.
- Layout MUST be single column (`11pt,letterpaper` or similar).
- Zero overfull `\hbox` warnings and zero undefined citations/references upon compilation.
- Elimination of AI writing tells (no robotic contrast formulas, no decorative bold labels, no bullet lists masquerading as paragraphs).

---

### Task 1: Reconfigure Main LaTeX Document to Single-Column Layout and Refined Typography

**Files:**
- Modify: `paper/main.tex`
- Modify: `paper/macros.tex`

**Interfaces:**
- Produces: Clean single-column layout with standard academic margins (`geometry`), 11pt font, elegant spacing for tables and figures.

- [ ] **Step 1: Update documentclass and geometry in `paper/main.tex`**
Change `\documentclass[10pt,twocolumn,letterpaper]{article}` to `\documentclass[11pt,letterpaper]{article}` with `geometry` margins `margin=1.0in` or `top=1.0in,bottom=1.0in,left=1.1in,right=1.1in` and line spacing `\linespread{1.05}`.

- [ ] **Step 2: Ensure author block and metadata match Luke Kaiser's exact specifications**
Verify:
```latex
\author{
  \textbf{Luke Kaiser}\thanks{Correspondence: \texttt{ltklionel@gmail.com}. Source code, datasets, and pre-trained models are publicly available at \url{https://github.com/targed/Alphable}.} \\
  \textit{Department of Computer Science, Missouri University of Science and Technology}
}
```

- [ ] **Step 3: Test compilation of `paper/main.tex`**
Run: `cd paper && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex`
Expected: Returncode 0.

---

### Task 2: De-Bullet and Humanize Abstract, Introduction, and Related Work

**Files:**
- Modify: `paper/sections/00_abstract.tex`
- Modify: `paper/sections/01_introduction.tex`
- Modify: `paper/sections/02_related_work.tex`

**Interfaces:**
- Converts: Enumerated action spaces, contribution bullet lists, and rigid sub-task lists into cohesive academic paragraphs.
- Eliminates: Staged AI openers ("In this paper, we introduce..."), robotic contrasts ("not only X, but Y"), and formulaic headings.

- [ ] **Step 1: Rewrite `paper/sections/00_abstract.tex` as a unified, compelling single-column abstract**
Ensure clear flow from problem context to core contribution, 10,000-game empirical findings, and open-source availability without bullet points.

- [ ] **Step 2: Rewrite `paper/sections/01_introduction.tex` in narrative prose**
Convert the 4-item Scrabble properties into flowing narrative prose explaining combinatorial branching, private racks, tile bag stochasticity, and asymmetric board topology.
Convert the "Summary of Contributions" bullet points into two focused paragraphs detailing the methodological innovations and empirical breakthroughs.

- [ ] **Step 3: Refine `paper/sections/02_related_work.tex` for academic flow**
Integrate historical context (Appel & Jacobson 1988, Gordon 1994, Sheppard 2002, Quackle, Macondo) with modern imperfect-information AI (DeepStack, Pluribus, Ataraxos) without bulleted breaks.

- [ ] **Step 4: Verify LaTeX compilation of Tasks 1-2**
Run: `cd paper && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex`
Expected: Returncode 0.

---

### Task 3: Streamline Mathematical Formulation and Add System Architecture Diagram

**Files:**
- Modify: `paper/sections/03_game_formulation.tex`
- Modify: `paper/sections/04_neural_architecture.tex`
- Create/Embed: System Architecture Diagram in TikZ

**Interfaces:**
- Prunes: Unused symbols ($\Omega, \gamma$) and cosmetic formulas in Section 3; keeps core POMDP structure and strategy fusion proof.
- Enriches: Adds a publication-grade TikZ visual diagram illustrating the interaction between board tensor, rack queries, C GADDAG candidate generator, PIMC simulation, and Bayesian belief tracking.

- [ ] **Step 1: Streamline Section 3 (Game Formulation)**
Condense POMDP notation to focus directly on information sets $o_1(s) = (\board, \rack_1, U, \Delta)$, hypergeometric bag draws, and the strategy fusion flaw via Jensen's inequality and minimax swap.

- [ ] **Step 2: Streamline Section 4 (Neural Architecture)**
Convert input tensor bullet lists into flowing prose describing the 28-channel spatial representation, 7-tile rack token embeddings, and cross-attention synergy mechanism.

- [ ] **Step 3: Construct TikZ System Architecture Diagram**
Design a TikZ flowchart showing the unified data pipeline:
Board Tensor & Rack Tokens $\to$ ResNet-18 Cross-Attention $\to$ C Candidate Generator $\to$ PIMC Rollout Engine $\to$ Bayesian Opponent Tracker $\to$ Volatility & Late-Game Solver.

- [ ] **Step 4: Verify LaTeX compilation**
Run: `cd paper && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex`
Expected: Returncode 0.

---

### Task 4: De-Bullet and Refine Search, Late-Game, and Tactical Board Visualization

**Files:**
- Modify: `paper/sections/05_bams_search.tex`
- Modify: `paper/sections/06_late_game.tex`

**Interfaces:**
- Converts: Enumerated 2-ply search steps and Hybrid PIMC stages into fluid narrative prose.
- Adds: A concrete tactical Scrabble board diagram / scenario illustrating how Bayesian negative-evidence tracking enables offensive play without ghost-threat paralysis.

- [ ] **Step 1: Rewrite Section 5 (Search and Hybrid PIMC)**
Unify 2-ply BAMS lookahead, Bayesian belief updates, volatility control, and compiled C simulation re-ranking into narrative prose with clean mathematical equations.

- [ ] **Step 2: Create a tactical board scenario diagram in TikZ**
Illustrate an actual board position where an opponent's bypass of an open 60-point bingo hook updates the posterior belief distribution, enabling Alphable to exploit an offensive scoring lane.

- [ ] **Step 3: Rewrite Section 6 (Late-Game Optimization)**
Convert pre-endgame bag parity and exact minimax endgame solver descriptions into cohesive academic text.

- [ ] **Step 4: Verify LaTeX compilation**
Run: `cd paper && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex`
Expected: Returncode 0.

---

### Task 5: Upgrade Experimental Results, Tables, and Charts for Single-Column Reading

**Files:**
- Modify: `paper/sections/07_experiments.tex`
- Modify: `paper/sections/08_critical_audit.tex`
- Modify: `paper/sections/09_conclusion.tex`

**Interfaces:**
- Formats: Adapts all tables (Table 1 to Table 5) to natural full single-column width with clean `booktabs` rules (removing awkward column-cramped `\resizebox` artifacts).
- Adds: A TikZ First-Turn Initiative breakdown bar chart alongside the Convergence Plot.
- Humanizes: Section 8 (Critical Audit) and Section 9 (Conclusion) into rigorous, intellectually honest academic discussions of the 40-game variance trap, negative results, and HPC cluster systems engineering.

- [ ] **Step 1: Format Tables 1-5 for single-column width**
Reformat Table 1 (Baseline 10k), Table 2 (Consistency Blocks), Table 3 (Phase Breakdown), Table 4 (HPC Supercomputer 10k), and Table 5 (Convergence Trajectory) so they sit naturally within the single-column margins.

- [ ] **Step 2: Add First-Turn Initiative comparison chart in TikZ**
Render a two-bar comparison chart displaying Game A (+20.48 pts) vs. Game B ($-12.18$ pts) and the net duplicate spread (+8.30 pts/pair).

- [ ] **Step 3: Refine Section 8 (Critical Audit) and Section 9 (Conclusion)**
Convert bulleted lists into analytical paragraphs discussing sample variance ($\mathrm{SEM} \approx 23.6$ pts/pair in small samples vs. $0.75$ pts in 10k tournament), failed 1-ply experiments, and SLURM multiprocessing memory tuning.

- [ ] **Step 4: Run full LaTeX and BibTeX build**
Run: `cd paper && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home bibtex main && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex && TEXMFVAR=/tmp/texmf-var TEXMFHOME=/tmp/texmf-home pdflatex -interaction=nonstopmode main.tex`
Expected: Returncode 0, zero warnings, clean PDF.

---

### Task 6: Final Verification, PDF Delivery, and Git Synchronization

**Files:**
- Update: `paper/alphable_v4.pdf`
- Sync: Git status, commit, and push to `alphable_V4_paper_base`

- [ ] **Step 1: Verify final PDF output**
Confirm `paper/main.pdf` is generated cleanly and copy to `paper/alphable_v4.pdf`.
- [ ] **Step 2: Verify all author edits are preserved**
Check diff against commit `40d1161` to ensure Luke Kaiser, contact information, and 10,000 games / 5,000 pairs remain intact.
- [ ] **Step 3: Stage, commit, and push**
Commit and push changes to `origin/alphable_V4_paper_base`.
