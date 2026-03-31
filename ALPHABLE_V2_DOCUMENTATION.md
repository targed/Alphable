# Alphable V2: The After-State Architecture

Welcome to the Alphable V2 documentation. This document explains the monumental pivot away from OpenSpiel/TensorFlow and details the custom, Scrabble-specific PyTorch architecture.

---

## 1. The Core Problem with V1 (OpenSpiel)

In the initial iteration, we attempted to map Scrabble onto the standard `alpha_zero.py` framework provided by DeepMind's OpenSpiel. That framework is designed for games like Chess and Go, where the action space is fixed (e.g., "Move piece from A to B").

**The Fatal Flaw:** Scrabble's action space is dynamic and dependent on a hidden, randomized rack. In V1:
1. The Neural Network (Policy Head) had to guess an arbitrary integer (1 to 452) representing a coordinate on the board, completely blind to the letters on the rack.
2. A python wrapper would intercept this coordinate and arbitrarily play the longest valid word that intersected it.
3. As a result, the AI had zero control over its rack leave, zero control over the words it formed, and effectively played blindfolded.

---

## 2. The Solution: The "After-State" Value Network

To solve this, we fundamentally changed the AI's objective. Instead of predicting *what move to make* (Policy), the network predicts *how good the board looks after a move is made* (Value).

### The Inference Pipeline (`inference.py`)
1. **Move Generation:** The fast C++ Cython GADDAG algorithm (`structure.pyx`) generates all 400+ mathematically legal words for the current rack.
2. **Simulation (`simulator.py`):** We temporarily apply each of those 400 words to a copy of the board to create 400 "After-States".
3. **Neural Evaluation (`alphable_net.py`):** We pass all 400 After-States through the custom PyTorch ResNet.
4. **Decision:** The network outputs a Win Probability `[-1.0, 1.0]`. The AI simply picks the move with the highest probability.

By evaluating the *result* of the move rather than the *coordinates* of the move, the AI naturally learns to balance points scored against the strategic value of the remaining rack and defensive board positioning.

### Neural Network Inputs
The AI uses a hybrid CNN + Dense architecture:
*   **The Board Tensor `[31, 15, 15]`:** 26 channels for A-Z letters, 1 channel for blanks, and 4 channels for premium squares (DL, TL, DW, TW). Processed via Residual Blocks.
*   **The State Vector `[29]`:** 26 counts for the remaining rack, 1 count for blanks, the Score Differential, and the Bag Remaining. Processed via Dense layers and concatenated with the flattened board representation.

---

## 3. Phase 2: Supervised Learning (Behavioral Cloning)

Self-play from scratch (Tabula Rasa) fails in Scrabble because random bots rarely form valid words, resulting in a sparse reward signal. To bootstrap the AI, we use Supervised Learning on expert human games from Woogles.io.

### The Training Pipeline
1. **Data Generation (`prepare_dataset.py`):**
   * Reads real human games.
   * For every turn, uses the GADDAG to find all moves the human *could* have played.
   * **Positive Sample (`target=1.0`):** The move the human actually played.
   * **Hard Negative Mining (`target=-1.0`):** We evaluate all unplayed moves, sort them by raw points, and take the Top 10 highest-scoring ones. By explicitly penalizing high-scoring moves that the expert human rejected, the AI learns advanced concepts like "Rack Leave Management" and "Board Defense".
   * Saves the data as compressed `[15x15]` string arrays to `data/supervised/samples.jsonl`.

2. **On-the-fly Expansion (`dataset.py`):**
   * To prevent terrabytes of tensor storage, the PyTorch `DataLoader` reads the compressed strings and dynamically expands them into the `[31, 15, 15]` float tensors right before sending them to the GPU.

3. **Training (`train_supervised.py`):**
   * A professional training loop using `AdamW`, `MSELoss`, `ReduceLROnPlateau` scheduling, and a 90/10 Train/Val split. Automatically checkpoints the best weights to `models/alphable_best_val_model.pth`.

---

## 4. Phase 3: Monte Carlo Rack Sampling (`search.py`)

Scrabble is a game of imperfect information. Even with a perfect Value Network, playing the highest 0-Ply (immediate) value move is often a mistake if it opens up a Triple Word Score for the opponent.

To solve this, we implemented a custom Monte Carlo Search tailored for hidden information:
1. **Top-K Candidates:** Generate all legal moves and use the Value Network to select the top 5 Candidate moves.
2. **Determine Unseen Tiles:** Calculate the exact distribution of tiles remaining in the bag/opponent's rack by subtracting the visible board and our rack from the standard 100-tile set.
3. **Sample Opponent Racks:** For each Candidate, draw $N$ random 7-letter racks from the Unseen Tiles.
4. **1-Ply Lookahead:** For each sampled opponent rack, generate their legal replies, evaluate them from the opponent's perspective, and assume they play their best move.
5. **Expected Value:** Average the final resulting board values across all $N$ simulations to find the True Expected Win Probability of our Candidate move.

This allows Alphable to play defensively, blocking high-value lanes if the opponent is mathematically likely to have the tiles to exploit them.

---

## Quick Start Guide

**1. Generate the Supervised Dataset**
```bash
# Requires data/training_dataset.jsonl from Woogles
python prepare_dataset.py
```
*(This will generate `data/supervised/samples.jsonl`)*

**2. Train the Value Network**
```bash
python train_supervised.py
```
*(Monitors validation loss and saves the best model to `models/`)*

**3. Run a Monte Carlo Search Test**
```bash
python search.py
```