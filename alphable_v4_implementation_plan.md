# Alphable V4 — Implementation Plan

**Finalized Design Decisions:**
- Engine: MAGPIE (C) via ctypes
- Belief Network: Bayesian inference first, neural upgrade if needed
- Value Network: Hybrid ResNet-18 + cross-attention (from V3, upgraded)
- Training: Macondo equity distillation at 100K+ scale
- Data: Woogles.io public game archive scrape
- RL: Macondo distillation anchored (pure supervised Phases 0–3, optional RL in Phase 4)

---

## Phase 0: Foundation — MAGPIE Bindings (Week 1–2)

### Goals
- Get MAGPIE's move generation and equity evaluation callable from Python
- Validate parity with V3 on known positions
- Establish directory structure for V4

### Tasks

**0.1 Repository Setup**
```bash
mkdir /home/targed/Documents/Git/Alphable/Alphable_V4
cd Alphable_V4
git init
# Create structure:
# engine/, models/, search/, training/, platform/, docs/
```

**0.2 Clone & Build MAGPIE**
```bash
git clone https://github.com/jvc56/MAGPIE.git vendor/magpie
cd vendor/magpie
# Build as shared library
make shared   # or: cmake -DBUILD_SHARED_LIBS=ON ..
# Output: libmagpie.so
```

**0.3 MAGPIE ctypes Wrapper** (`engine/magpie_bindings.py`)
- Map MAGPIE C structs to Python ctypes: Board, Rack, Move, MoveList
- Expose: `generate_moves()`, `equity()`, `apply_move()`, `best_reply()`, `endgame_solve()`
- Validate on 5 known board positions (compare to V3 output)

**0.4 Game State Layer** (`engine/game_state.py`)
- Board: 15×15 grid, tile encoding, premium square map
- Rack: 7-letter rack, blank representation
- Bag: unseen tile tracking (carries V3's 63-dim state vector logic)
- Move: position, word, direction, score, leave

**0.5 Lexicon Loading**
- Load CSW24.txt and NWL23.txt into MAGPIE's KWG format
- Confirm lexicon switching works

### Success Criteria (Phase 0)
- [ ] `magpie_bindings.generate_moves(board, rack)` returns complete legal move list
- [ ] Move list matches V3 GADDAG output on 10 test positions
- [ ] `magpie_bindings.equity(move, game_state)` returns float
- [ ] Lexicon switch CSW24 ↔ NWL23 works without restart

---

## Phase 1: Data Collection Pipeline (Week 2–4)

### Goals
- Collect 100,000+ grandmaster-level games from Woogles
- Run Macondo analyzer on 200,000+ positions
- Build training dataset for belief network and value network

### Tasks

**1.1 Woogles Game Scraper** (`training/collect_woogles.py`)
- Use Woogles API or public game archive
- Filter: rating ≥ 1800 (or highest available bucket)
- Target: 100,000 games in GCG format
- Store: `data/raw_games/` as `.gcg` files

**1.2 GCG Parser** (`training/parse_gcg.py`)
- Parse `.gcg` game records into structured JSON
- Output per game: list of `{rack, move, board_before, board_after, score_delta, bag_remaining}` dicts
- Validate: racks must be consistent with tile counts
- Expected output: `data/parsed_games/game_XXXXX.json`

**1.3 Macondo Analysis Pipeline** (`training/macondo_distill.py`)
- For each parsed position, call Macondo analyzer
- Use Macondo's equity as the regression target
- Scale: target 200,000 analyzed positions (2 positions/game average)
- Output: `data/analyzed/position_XXXXX.json` with `{board, rack, top_moves, equities}`

**1.4 Belief Network Dataset** (`training/build_belief_dataset.py`)
- From each parsed game, extract:
  - `(move_history_so_far, opponent_rack)` for each turn
- Opponent rack is always ground truth (known from game record)
- Expected: 1.4M samples at 100K games × 14 turns/game
- Output: `data/belief/belief_XXXXX.parquet`

**1.5 Value Network Dataset** (`training/build_value_dataset.py`)
- Merge parsed game + Macondo equity analysis
- Each sample: `{board_tensor, state_vector, macondo_equity}`
- Apply continuous deficit scaling from V3
- Expected: 200K training samples
- Output: `data/value/value_XXXXX.parquet`

### Success Criteria (Phase 1)
- [ ] 100,000+ games downloaded and parsed without errors
- [ ] GCG parser validates rack consistency on all games
- [ ] 200,000+ positions analyzed by Macondo
- [ ] 1.4M belief network samples generated
- [ ] 200K value network samples with Macondo equity targets

---

## Phase 2: Model Training (Week 4–7)

### Goals
- Train the Bayesian belief network (opponent rack inference)
- Train the upgraded V4 after-state value network (Hybrid ResNet-18 + cross-attention)
- Validate both on held-out test sets

### Tasks

**2.1 Bayesian Rack Inference** (`models/belief_net.py`)

*Start simple*: Bayesian inference over observed tiles.

Given all tiles played by opponent so far, update a prior distribution over remaining tiles in the bag, then marginalize over what's in the opponent's rack:

```python
def infer_rack_distribution(game_state):
    """
    Simple Bayesian rack inference.
    P(opponent_rack | plays_seen) ∝ P(plays_seen | rack) * P(rack | unseen_tiles)
    """
    unseen = game_state.unseen_tiles  # tiles not on board or in our rack
    # Sample N racks from multinomial(unseen, 7)
    return DirichletMultinomial(unseen, n=7)
```

This is zero-training, immediately better than uniform sampling.

**2.2 Value Network Architecture** (`models/value_net.py`)

```python
class V4ValueNetwork(nn.Module):
    def __init__(self):
        # Board encoder: ResNet-18 pretrained on ImageNet (adapt for 32-channel input)
        self.board_encoder = ResNet18(in_channels=32)  # 15×15×32 → 512-dim
        
        # State cross-attention: attend board features over state vector
        self.state_proj = nn.Linear(64, 512)  # 64-dim state vector → 512
        self.cross_attn = nn.MultiheadAttention(512, heads=8)
        
        # Equity head
        self.equity_head = nn.Sequential(
            nn.Linear(512, 128), nn.ReLU(),
            nn.Linear(128, 1), nn.Tanh()  # output in [-1, 1]
        )
    
    def forward(self, board_tensor, state_vector):
        board_feat = self.board_encoder(board_tensor)  # (B, 512)
        state_feat = self.state_proj(state_vector)      # (B, 512)
        
        # Cross-attention: board features attend to state
        attended, _ = self.cross_attn(board_feat.unsqueeze(1), 
                                       state_feat.unsqueeze(1), 
                                       state_feat.unsqueeze(1))
        
        return self.equity_head(attended.squeeze(1))
```

**Board Tensor (32 channels — upgrade from V3's 31):**
- Channels 0–25: One-hot letter planes (A–Z)
- Channel 26: Blank tiles on board
- Channels 27–30: Dynamic premium squares (DL, TL, DW, TW — 1.0 if unoccupied)
- Channel 31: Our rack letters present on board (bingo opportunities)

**State Vector (64-dim — upgrade from V3's 63-dim):**
- All V3 63-dim features preserved
- Add: Bayesian rack inference confidence score (1 new dim)

**2.3 Training: Phase 1 (Supervised Macondo Distillation)** (`training/train_value.py`)

```python
# Training configuration
optimizer = AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
loss_fn = nn.HuberLoss(delta=0.1)  # Smooth L1

# Continuous deficit scaling (preserved from V3)
def deficit_target(pos_equity, neg_equity):
    deficit_ratio = min(1.0, (pos_equity - neg_equity) / max(10, pos_equity))
    return max(-1.0, 1.0 - 2.0 * deficit_ratio)

# Train for 50 epochs on 200K positions
# Validate on held-out 10K positions (Macondo equity correlation ≥ 0.90 target)
```

**2.4 Training: Phase 2 (MAGPIE Leave Distillation)**
- Generate 500K random (board, rack) pairs
- Label with MAGPIE's static equity (KLV leave tables)
- Fine-tune value network on this signal (2 epochs, lower LR)
- This teaches the network MAGPIE's leave intuition without re-implementing KLV

### Success Criteria (Phase 2)
- [ ] Bayesian inference: rack distribution is consistent with unseen tile counts
- [ ] Value network: Pearson correlation with Macondo equity ≥ 0.90 on validation set
- [ ] Value network: Validation Huber loss ≤ 0.05 (vs. V3's achieved 0.0293 with 800 samples)
- [ ] Model runs inference in < 5ms on GPU for 100 candidates

---

## Phase 3: BAMS Search Integration (Week 7–9)

### Goals
- Implement Belief-Augmented Monte Carlo Search
- Benchmark vs. HastyBot and BestBot
- Target: 65%+ win rate vs. HastyBot

### Tasks

**3.1 BAMS Implementation** (`search/bams.py`)

```python
def bams_select_move(game_state, candidates, belief_net, value_net, engine, N=64):
    """
    Belief-Augmented Monte Carlo Search.
    
    Args:
        game_state: Current board, rack, bag, transcript
        candidates: List of legal moves from MAGPIE (sorted by static equity)
        belief_net: BayesianRackInference or NeuralBeliefNet
        value_net: V4ValueNetwork
        engine: MAGPIE bindings
        N: Number of opponent rack samples
    
    Returns:
        Best candidate move
    """
    # 1. Sample N opponent racks from belief model
    rack_dist = belief_net.infer(game_state)
    sampled_racks = rack_dist.sample(N)  # List of N racks
    
    # 2. Pre-compute opponent best replies for all rack samples (CRN: same racks for all candidates)
    opp_replies = [engine.best_reply(game_state.board, rack) for rack in sampled_racks]
    
    # 3. Evaluate each candidate against all rack samples
    candidate_scores = {}
    for cand in candidates[:20]:  # Evaluate top-20 static equity candidates
        total_value = 0.0
        for i, (rack, opp_reply) in enumerate(zip(sampled_racks, opp_replies)):
            # Apply our move
            board_after = engine.apply_move(game_state.board, cand)
            # Apply opponent's reply
            board_after_2 = engine.apply_move(board_after, opp_reply)
            # Build resulting game state
            next_state = game_state.after(cand, opp_reply, board_after_2)
            # Score with value network
            value = value_net(next_state.board_tensor, next_state.state_vector)
            total_value += value.item()
        
        candidate_scores[cand] = total_value / N
    
    return max(candidate_scores, key=candidate_scores.get)
```

**3.2 N Calibration**
- Benchmark BAMS at N=8, 16, 32, 64, 128 vs. HastyBot
- Measure: win rate vs. computation time
- Target: N that gives best win rate within 5 second time budget

**3.3 Woogles Bot Integration** (`platform/woogles_bot.py`)
- Port V3 WebSocket bot client to V4
- Swap V3 search for BAMS search module
- Test: lexicon switching (CSW24/NWL23) via MAGPIE

**3.4 Evaluation Harness** (`platform/eval.py`)
- Play 100-game series vs. HastyBot (via Woogles)
- Play 50-game series vs. BestBot (via Woogles)
- Log: win rate, mean score, bingos/game, exchange rate

### Success Criteria (Phase 3)
- [ ] BAMS selects moves within 5-second time budget (N tuned appropriately)
- [ ] V4 beats HastyBot in 65%+ of 100 games
- [ ] V4 mean score ≥ 450 points/game
- [ ] Bingos/game ≥ 2.5 (parity with expert play)
- [ ] Zero "invalid move" rejections from Woogles

---

## Phase 4: RL Fine-Tuning (Week 9–12) — Optional

### Goals
- Apply Ataraxos-style dynamic damping self-play RL to further improve
- Target: 80%+ win rate vs. HastyBot, competitive vs. BestBot

### Conditions to Proceed
- Phase 3 achieves ≥ 65% vs. HastyBot
- Phase 3 has some remaining systematic weaknesses (e.g., endgame, specific tile configurations)

### Tasks

**4.1 Self-Play Data Collection**
- Run V4 Phase 3 vs. itself: 10,000 games
- Store positions with game outcome labels

**4.2 Dynamic Damping RL** (`training/train_rl.py`)
- Reward: Macondo equity delta per move (not raw win/loss — anchored!)
- Regularization: KL penalty vs. Phase 3 model (prevents policy collapse)
- Dynamic damping: increase regularization when policy update is large
- Train for 20 epochs of 500 games each

**4.3 Evaluation vs. BestBot**
- Play 50-game series vs. BestBot
- If win rate > 50%: write a blog post

### Success Criteria (Phase 4)
- [ ] V4 beats HastyBot in 80%+ of games
- [ ] V4 competitive vs. BestBot (≥ 40% win rate)
- [ ] No policy collapse (mean score doesn't drop vs. Phase 3)

---

## Directory Structure

```
Alphable_V4/
├── README.md
├── pyproject.toml
├── vendor/
│   └── magpie/             # MAGPIE git submodule
├── engine/
│   ├── magpie_bindings.py  # ctypes wrapper
│   ├── game_state.py       # Board/rack/bag state
│   └── move.py             # Move encoding
├── models/
│   ├── belief_net.py       # Bayesian (+ future neural) belief model
│   ├── value_net.py        # Hybrid ResNet-18 + cross-attention
│   └── checkpoints/        # Trained weights (gitignored)
├── search/
│   └── bams.py             # Belief-Augmented Monte Carlo Search
├── training/
│   ├── collect_woogles.py  # Scrape Woogles game archive
│   ├── parse_gcg.py        # Parse .gcg game files
│   ├── macondo_distill.py  # Run Macondo analyzer on positions
│   ├── build_belief_dataset.py
│   ├── build_value_dataset.py
│   ├── train_value.py      # Value network training
│   └── train_rl.py         # Phase 4 RL fine-tuning
├── platform/
│   ├── woogles_bot.py      # Woogles WebSocket bot client
│   └── eval.py             # Evaluation harness
├── resources/
│   ├── CSW24.txt
│   └── NWL23.txt
├── data/                   # gitignored (large files)
│   ├── raw_games/
│   ├── parsed_games/
│   ├── analyzed/
│   ├── belief/
│   └── value/
└── docs/
    ├── ARCHITECTURE.md
    ├── WHAT_WE_TRIED.md    # Link to V3 history
    └── V4_PROPOSAL.md      # This document
```

---

## Risk Mitigations

| Risk | Mitigation |
|---|---|
| MAGPIE can't be built as shared lib | Use Macondo gRPC subprocess instead (Phase 0 fallback) |
| Woogles scrape rate-limited | Use 1 req/sec, request public data dump from Woogles team |
| Policy collapse in Phase 4 | Keep Phase 3 checkpoint, RL is optional additive step |
| Belief network doesn't help | Bayesian inference still better than uniform; skip neural upgrade |
| Phase 3 < 65% vs HastyBot | Debug: profile move quality, check MAGPIE integration, add more training data |

---

## Dependencies

```toml
[project]
name = "alphable-v4"
dependencies = [
    "torch>=2.4",
    "torchvision>=0.19",
    "numpy>=2.0",
    "pandas>=2.2",
    "pyarrow>=17.0",    # Parquet
    "websockets>=13.0", # Woogles bot
    "grpcio>=1.66",     # Macondo fallback
    "requests>=2.32",   # Woogles scraper
    "tqdm>=4.67",
]
```

MAGPIE bindings require: GCC/Clang, cmake, libmagpie.so at runtime.

---

## Timeline Summary

| Phase | Duration | Key Deliverable | Success Gate |
|---|---|---|---|
| 0: MAGPIE Bindings | 1–2 weeks | `magpie_bindings.py` | Move parity with V3 |
| 1: Data Pipeline | 2–4 weeks | 200K analyzed positions | Macondo equity on all samples |
| 2: Model Training | 3–7 weeks | V4 value net (≥ 0.90 corr) | Validation loss ≤ 0.05 |
| 3: BAMS Search | 7–9 weeks | Woogles bot playing | 65%+ vs HastyBot |
| 4: RL Fine-Tune | 9–12 weeks | Championship model | 80%+ vs HastyBot |
