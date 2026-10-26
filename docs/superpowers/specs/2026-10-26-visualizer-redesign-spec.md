# Visualizer Studio 2.5: Broadcast Redesign & AI Match Arena Spec

**Date**: 2026-10-26  
**Status**: Ready for Implementation  
**Focus**: Visual Design Overhaul (`frontend-design`), AI vs AI Match Arena, Duplicate Position Swapping, Move Undo/Rewind, and Bag Inspection.

---

## 1. Design Philosophy & Aesthetic Identity

### Moving Away from Generic AI Tells
- **No generic slate SaaS kit**: Eliminating the ubiquitous `#0f172a` navy/purple card grid with identical rounded pill buttons and all-caps labels.
- **Bespoke Championship Table Aesthetic**:
  - **Atmosphere**: Fine tournament Scrabble salon — deep warm walnut `#141210`, warm charcoal surfaces `#201c18`, rich parchment undertones, and warm bronze borders `#383028`.
  - **Board Realism**: Tournament emerald felt `#163324` or rich lacquered dark wood grid `#1f1a15` with crisp grid markers and engraved premium square insets.
  - **Authentic Scrabble Tiles**: Tactile boxwood/maple tiles (`#fef3c7` body with `#e2d5b8` bottom bevel shadow), dark charcoal letter glyphs (`#1c1917`), and small authentic subscript point values (`#78350f`).
  - **Restraint**: The board and the active play arena are the hero. Everything else is disciplined, clean, and legibly formatted.
  - **Typography**: Editorial clarity with `Outfit` / `Inter` for clean hierarchy, coupled with monospace `JetBrains Mono` for Scrabble coordinates and game notation. Sentence case throughout.

---

## 2. Core Functional Additions

### A. AI vs AI Live Match Arena
- Full freedom to select **any two players**:
  - **Player 1**: Human, Alphable V4 (any model preset: `latest`, `5-frontiers`, `v4-baseline`, `rl-gen1`), Alphable V3 (Macondo ResNet / Transformer), Base MAGPIE, or Score Greedy.
  - **Player 2**: Human, Alphable V4, Alphable V3, Base MAGPIE, or Score Greedy.
- **Play Controls**:
  - "Next Move (Step)": Advance exactly one AI move at a time.
  - "Auto-Play": Automatically steps through the game with selectable delay (0.5s, 1s, 2s).
  - "Pause": Halts auto-play at any moment.
  - "Undo Move (Rewind)": Steps back to the previous turn, restoring previous racks, scores, and board state.
  - "Reset Match": Starts a fresh match with a newly randomized or seeded tile bag.

### B. Duplicate Position Swapping ("Duplicate Lab")
- In championship Scrabble, duplicate play removes tile luck by having players evaluate the exact same rack on the exact same board.
- **"Duplicate Swap" Button**:
  - For the current board and rack, simultaneously queries Player 1 and Player 2.
  - Displays a side-by-side Decision Comparison Modal:
    - Player 1 Move: Word, Coordinate, Points, Leave, Strategic Equity, BAMS simulation details.
    - Player 2 Move: Word, Coordinate, Points, Leave, Strategic Equity.
  - Lets the user pick which move to execute to explore branching game trees!

### C. Tile Bag Inspector Modal
- Clickable bag counter that opens a visual inventory modal:
  - Vowels remaining (A, E, I, O, U) with vowel/consonant ratio.
  - Consonants remaining.
  - High-value power tiles (Q, Z, X, J, K) and Blanks (?).
  - Probability of drawing a blank or bingo-friendly tile on next replenishment.

### D. Move History & Branching Rewind
- Full turn list on the side. Clicking *any* past turn jumps directly to that turn's board state, allowing the user to inspect what happened or play out an alternative branch from that position.

---

## 3. Architecture & File Plan

- `visualizer/frontend/src/index.css`: Complete overhaul of color palette, board styling, tile bevels, and typography.
- `visualizer/frontend/src/types.ts`: Extended types for game history snapshots, duplicate comparisons, and bag tracking.
- `visualizer/frontend/src/components/Board.tsx`: Upgraded 15×15 grid with coordinate gutters, premium badges, and play animations.
- `visualizer/frontend/src/components/TileRack.tsx`: Sleek wooden rack with tile drag/click and point subscripts.
- `visualizer/frontend/src/components/PlayerHUD.tsx`: Redesigned broadcast header with active player halo, live score differentials, and bag inspector pill.
- `visualizer/frontend/src/components/CandidateTable.tsx`: Interactive candidate table with board hover preview.
- `visualizer/frontend/src/components/BagModal.tsx`: New modal displaying remaining bag tiles and distributions.
- `visualizer/frontend/src/components/DuplicateModal.tsx`: New modal showing side-by-side engine decision comparison on identical positions.
- `visualizer/frontend/src/components/ArenaControls.tsx`: Match controls (Step, Play/Pause, Undo, Duplicate Swap, Speed).
- `visualizer/frontend/src/App.tsx`: Refactored arena orchestration managing game history stack for seamless undo and AI vs AI stepping.
- `visualizer/tests/test_e2e_visualizer.py`: Updated and extended tests verifying all features.
