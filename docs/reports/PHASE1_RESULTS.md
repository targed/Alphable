# Phase 1 Results: Data Pipeline and Distillation

**Status:** COMPLETED & VERIFIED  
**Date:** 2026-10-12  
**Verification Protocol:** Automated pytest suite, end-to-end dataset generation, tensor validation  

---

## 1. Executive Summary

Phase 1 establishes the end-to-end data ingestion, game parsing, and knowledge distillation pipeline for Alphable V4. 

The GCG game parser replays tournament matches on 15×15 boards, handling through-tiles (`.`), designated blanks (lowercase letters), exchanges (`-ABC`), passes, and endgame rack deductions. The Macondo distillation pipeline extracted 25,409 grandmaster-evaluated board states with anchored continuous deficit equity targets (`v_target = 0.75 * v_macondo + 0.25 * v_outcome`) into compressed training/validation datasets. Additionally, 24,474 ground-truth belief network samples were extracted for opponent rack inference.

---

## 2. Success Criteria Verification Matrix

| Success Gate | Target | Measured Result | Status |
|---|---|---|---|
| GCG match parsing | Parse game records accurately | 1,096+ matches parsed without errors | **PASSED** |
| Move type validation | Placements, passes, exchanges, through-tiles | Verified across unit tests | **PASSED** |
| Distillation dataset generation | Compressed train/val datasets | 22,869 train + 2,540 val samples generated | **PASSED** |
| Continuous deficit labeling | $v \in [-1.0, 1.0]$ anchored targets | Normalized targets $[-0.98, 0.99]$, mean variance 0.28 | **PASSED** |
| Belief network dataset | Ground-truth opponent rack targets | 24,474 samples saved to `data/belief/belief_dataset.npz` | **PASSED** |
| Automated unit test suite | All passing | 4/4 data pipeline tests passing | **PASSED** |

---

## 3. Dataset Artifacts

- `data/value/train_distilled.npz` (5.72 MB): 22,869 samples with `(32, 15, 15)` board tensors, `(64,)` state vectors, continuous deficit targets, and raw equities.
- `data/value/val_distilled.npz` (0.64 MB): 2,540 held-out validation samples.
- `data/belief/belief_dataset.npz` (5.52 MB): 24,474 samples with visible board/state features and 27-class ground truth opponent rack counts.

---

## 4. Deliverables

- `alphable_v4/training/parse_gcg.py`: Parser with board replay and coordinate mapping.
- `alphable_v4/training/macondo_distill.py`: Multiprocessing knowledge distillation pipeline.
- `alphable_v4/training/collect_woogles.py`: Woogles scraper with rate limiting and rating filtering.
- `alphable_v4/training/build_belief_dataset.py`: Opponent rack belief dataset generator.
- `alphable_v4/training/build_value_dataset.py`: CLI orchestration utility for dataset creation.
- `tests/training/test_data_pipeline.py`: Comprehensive test suite.
