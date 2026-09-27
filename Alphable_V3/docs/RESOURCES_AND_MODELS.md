# Alphable V3: Models, Checkpoints & Resource Catalog

This document provides a comprehensive inventory and reference catalog for all trained model weights, lexicons, datasets, and file formats used in **Alphable V3**.

---

## 1. Neural Network Checkpoints (`models/`)

All neural network weights are PyTorch state dictionaries saved in standard `.pth` format.

```
models/
├── alphable_v3_macondo_v2.pth          # ⭐ PRODUCTION CHAMPION (Macondo Distilled, 63-dim)
├── alphable_v3_supervised_clean.pth    # Supervised Base Model (Human Tournament Samples)
├── alphable_v3_rl_gen1.pth             # RL Generation 1 (Curriculum vs GreedyBot)
├── alphable_v3_rl_gen2.pth             # RL Generation 2 (80% Win Rate vs GreedyBot)
├── alphable_v3_rl_gen3_distilled.pth   # RL Generation 3 (Early Distillation Checkpoint)
└── alphable_v3_rl_gen4.pth             # RL Generation 4 (5,000-Game Pure Self-Play)
```

### Detailed Checkpoint Specifications

| Checkpoint | State Vector Size | Training Methodology | Target Evaluation Quality | Status / Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **`alphable_v3_macondo_v2.pth`** | **63 dims** | **Grandmaster Distillation:** Fine-tuned on 2,300+ Macondo Grandmaster board states from Woogles expert matches with normalized equity targets. | Superhuman positional evaluation; understands complex board dynamics, rack balance, and long-term bingo lane control. | **⭐ PRODUCTION CHAMPION** (Default for all Woogles live play and evaluation). |
| **`alphable_v3_supervised_clean.pth`** | 36 dims | **Supervised Learning:** Trained on expert human and bot tournament games with continuous deficit negative scaling. | High-quality tactical play; strong opening and midgame moves. | Base model for new training experiments and distillation. |
| **`alphable_v3_rl_gen2.pth`** | 36 dims | **Anti-Greedy RL Curriculum:** Trained on self-play with `--vs-greedy` and `--keep-p0-only`. | Achieves 80% win rate against GreedyBot. Excellent at scoring bingos when opponents open the board. | Benchmark baseline for offline evaluation. |
| **`alphable_v3_rl_gen3_distilled.pth`** | 36 dims | **Hybrid RL / Early Distillation:** Distilled checkpoint combining supervised and early Macondo evaluations. | Strong positional awareness, 41.3% win rate vs HastyBot in early 75-match run. | Historical milestone checkpoint. |
| **`alphable_v3_rl_gen4.pth`** | 63 dims | **Pure Outcome Self-Play RL:** Trained on 5,000 mirror self-play games without an external anchor. | **Policy Collapse / Timid Play:** Illustrated the symmetric self-play local Nash equilibrium trap. | Archived research model (see post-mortem in [BUGS_AND_POSTMORTEMS.md](file:///home/targed/Documents/Git/Alphable/Alphable_V3/docs/decisions/BUGS_AND_POSTMORTEMS.md)). |

### Checkpoint Compatibility Loader
Alphable includes an intelligent weights loader ([`load_checkpoint_compatible`](file:///home/targed/Documents/Git/Alphable/Alphable_V3/src/alphable/core/alphable_net.py)) that allows seamless warm-starting between models of different generations:
- When loading a 36-dimensional checkpoint into a 63-dimensional network, the first 36 channels of `scalar_stream.0.weight` are populated, and the remaining 27 channels (unseen tile bag tracking) are cleanly initialized to zeros or identity.
- Allows immediate zero-shot deployment of upgraded architectures without breaking legacy compatibility.

---

## 2. Tournament Lexicons (`resources/`)

Scrabble lexicons are stored as plain newline-delimited text files containing valid tournament words in uppercase ASCII.

```
resources/
├── CSW24.txt      # Collins Scrabble Words 2024 (International Standard)
└── NWL2023.txt    # NASPA Word List 2023 (North American Standard)
```

### Lexicon Specifications
| File | Word Count | Standards Body | Primary Tournament Regions |
| :--- | :--- | :--- | :--- |
| **`resources/CSW24.txt`** | **279,496 words** | WESPA (World English-Language Scrabble Players' Association) | UK, Europe, Australia, Asia, Africa, International Championships (Woogles Default). |
| **`resources/NWL2023.txt`** | **192,111 words** | NASPA (North American Scrabble Players Association) | USA, Canada. |

*Note: In-memory GADDAG compilation occurs automatically upon startup and takes under 1.5 seconds for the full 279k CSW24 lexicon.*

---

## 3. Data Storage & Match Telemetry (`data/`)

```
data/
├── woogles/
│   ├── matches/                      # Individual match telemetry folders
│   │   └── <timestamp>_<game_id>/
│   │       ├── game.gcg              # Official tournament Scrabble record
│   │       ├── analysis.json         # Macondo Grandmaster Analyzer turn-by-turn evaluations
│   │       ├── replay.json           # Board-by-board states for Web Visualizer
│   │       └── summary.json          # Game outcome and point margin metadata
│   └── summaries/                    # Multi-game series summaries
│       └── run_<timestamp>_series.json
├── supervised/
│   └── samples.jsonl                 # Processed supervised after-state dataset
└── macondo_distill_cache.pt          # Serialized PyTorch tensor cache for rapid distillation
```

### Telemetry Formats

#### 1. `game.gcg` (Scrabble Championship Format)
```text
#player1 Alphable Alphable
#player2 HastyBot HastyBot
>Alphable: AEEIIOU 8G EUOI +8 8
>HastyBot: ADENRRW 7G WARDEN +28 28
>Alphable: AEIIPST 9B PIETAS +86 94
```

#### 2. `analysis.json` (Macondo Analyzer Output)
```json
[
  {
    "turn": 1,
    "player": "Alphable",
    "rack": "AEEIIOU",
    "suggestions": [
      {
        "move": "EUOI 8G",
        "score": 8,
        "equity": -34.2,
        "win_pct": 0.48
      }
    ]
  }
]
```

#### 3. `series.json` (Series Summary)
```json
{
  "total_games": 15,
  "wins": 8,
  "losses": 7,
  "draws": 0,
  "win_rate": 0.533,
  "avg_score_diff": 12.4,
  "avg_alphable_score": 454.8,
  "avg_opponent_score": 442.4
}
```
