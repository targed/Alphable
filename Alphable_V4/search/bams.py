"""
Belief-Augmented Monte Carlo Search (BAMS) for Alphable V4.

BAMS combines:
1. Candidate pruning from MAGPIE's KLV static equity generation.
2. Bayesian opponent rack sampling using Common Random Numbers (CRN).
3. 1-ply Monte Carlo rollout with MAGPIE opponent best-response simulation.
4. ResNet-18 + Cross-Attention Value Network after-state evaluation on GPU.
5. Deterministic fast path in the endgame (unseen <= 7 tiles).
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any

import numpy as np
import torch

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.models.belief_net import BayesianRackInference
from alphable_v4.models.value_net import V4ValueNetwork


@dataclass
class BAMSConfig:
    """Configuration hyperparameters for BAMS search."""
    num_samples: int = 32           # Number of opponent rack simulations (N)
    candidate_beam: int = 15        # Top static-equity candidates to rollout (K)
    value_weight: float = 12.0       # Points-scale multiplier for normalized equity [-1, 1]
    static_equity_weight: float = 1.0 # Blending weight for MAGPIE's static leave equity
    opp_penalty_weight: float = 0.25  # Defensive counter-play risk penalty weight
    max_static_deficit: float = 4.0   # Maximum static equity deficit allowed for rollout
    use_crn: bool = True            # Common Random Numbers for opponent rack samples
    seed: Optional[int] = None       # Random seed for reproducible simulations
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


@dataclass
class BAMSCandidateEval:
    """Evaluation summary for a single candidate move."""
    move: Move
    static_equity: float
    immediate_score: int
    mean_opp_reply_score: float
    mean_value_pred: float
    bams_score: float


class BAMSSearch:
    """
    Belief-Augmented Monte Carlo Search engine.
    """

    def __init__(
        self,
        engine: MagpieEngine,
        value_net: Optional[V4ValueNetwork] = None,
        belief_net: Optional[BayesianRackInference] = None,
        config: Optional[BAMSConfig] = None,
    ):
        self.engine = engine
        self.config = config or BAMSConfig()
        self.belief_net = belief_net or BayesianRackInference()
        self.device = torch.device(self.config.device)

        if value_net is not None:
            self.value_net = value_net.to(self.device)
            self.value_net.eval()
        else:
            self.value_net = None

    @classmethod
    def from_checkpoint(
        cls,
        engine: MagpieEngine,
        checkpoint_path: str,
        config: Optional[BAMSConfig] = None,
    ) -> BAMSSearch:
        """Instantiates BAMSSearch by loading a trained Value Network checkpoint."""
        conf = config or BAMSConfig()
        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
        checkpoint = torch.load(checkpoint_path, map_location=conf.device, weights_only=False)
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)
        return cls(engine=engine, value_net=model, config=conf)

    def select_move(
        self,
        game_state: GameState,
        candidates: Optional[List[Move]] = None,
        num_samples: Optional[int] = None,
    ) -> Tuple[Move, Dict[str, Any]]:
        """
        Selects the best legal move using Belief-Augmented Monte Carlo Search.

        Returns:
            (selected_move, search_metadata)
        """
        start_time = time.perf_counter()
        N = num_samples if num_samples is not None else self.config.num_samples
        K = self.config.candidate_beam

        # 1. Candidate Generation
        if candidates is None:
            candidates = self.engine.generate_moves(
                game_state=game_state, max_candidates=max(100, K)
            )

        if not candidates:
            # Fallback pass if no moves legal
            pass_move = Move.create_pass()
            return pass_move, {"method": "fallback_pass", "latency_ms": (time.perf_counter() - start_time) * 1000}

        # If only one candidate or forced play, return immediately
        if len(candidates) == 1:
            return candidates[0], {"method": "forced_move", "latency_ms": (time.perf_counter() - start_time) * 1000}

        # Filter candidates: top K by static equity, and within max_static_deficit of top move
        top_equity = candidates[0].equity
        max_deficit = getattr(self.config, "max_static_deficit", 4.0)
        eval_candidates = [
            c for c in candidates[:K]
            if (top_equity - c.equity) <= max_deficit
        ]
        if not eval_candidates:
            eval_candidates = candidates[:1]

        # 2. Check for Endgame Fast Path (unseen tiles <= 7)
        total_unseen = sum(game_state.unseen_counts.values())
        if total_unseen <= 7:
            # Deterministic endgame: opponent holds all remaining unseen tiles
            opp_rack_str = "".join(self.belief_net.get_unseen_tile_pool(game_state))
            selected, evals = self._evaluate_deterministic_endgame(game_state, eval_candidates, opp_rack_str)
            latency_ms = (time.perf_counter() - start_time) * 1000
            return selected, {
                "method": "deterministic_endgame",
                "latency_ms": latency_ms,
                "evaluations": evals,
                "opp_rack": opp_rack_str,
            }

        # 3. Sample N opponent racks using Bayesian inference with CRN
        seed = self.config.seed if self.config.use_crn else None
        sampled_rack_lists = self.belief_net.sample_opponent_racks(
            game_state, num_samples=N, seed=seed
        )
        sampled_racks = ["".join(r) for r in sampled_rack_lists]

        # 4. Monte Carlo 1-ply Simulation
        cand_results: List[Dict[str, Any]] = []
        after_states_to_eval: List[GameState] = []
        state_index_mapping: List[Tuple[int, int]] = []  # (cand_idx, sample_idx)

        for c_idx, cand in enumerate(eval_candidates):
            # Apply our move
            try:
                state_after_cand = game_state.apply_move(cand)
            except Exception:
                continue

            cand_entry = {
                "candidate": cand,
                "immediate_score": cand.score,
                "static_equity": cand.equity,
                "opp_scores": [],
            }

            # Simulate opponent's best response for each sampled rack
            for s_idx, opp_r in enumerate(sampled_racks):
                try:
                    opp_reply = self.engine.best_reply(state_after_cand, opp_r)
                    if opp_reply is not None and opp_reply.is_placement:
                        opp_score = opp_reply.score
                        resulting_state = state_after_cand.apply_move(opp_reply)
                    else:
                        opp_score = 0
                        resulting_state = state_after_cand
                except Exception:
                    opp_score = 0
                    resulting_state = state_after_cand

                cand_entry["opp_scores"].append(opp_score)
                if self.value_net is not None:
                    after_states_to_eval.append(resulting_state)
                    state_index_mapping.append((c_idx, s_idx))

            cand_results.append(cand_entry)

        # 5. Batched Neural Evaluation on GPU
        value_preds = {}
        if self.value_net is not None and after_states_to_eval:
            board_tensors = torch.stack([s.to_board_tensor() for s in after_states_to_eval]).to(self.device)
            state_vectors = torch.stack([s.to_state_vector() for s in after_states_to_eval]).to(self.device)

            with torch.no_grad():
                preds = self.value_net.evaluate_batch(board_tensors, state_vectors)
                preds_np = preds.squeeze(1).cpu().numpy()

            for idx, (c_idx, s_idx) in enumerate(state_index_mapping):
                value_preds[(c_idx, s_idx)] = float(preds_np[idx])

        # 6. Aggregate BAMS Scores
        evaluated_candidates: List[BAMSCandidateEval] = []
        for c_idx, cand_dict in enumerate(cand_results):
            cand = cand_dict["candidate"]
            opp_scores = cand_dict["opp_scores"]
            mean_opp_score = float(np.mean(opp_scores)) if opp_scores else 0.0

            if self.value_net is not None:
                preds_for_c = [value_preds.get((c_idx, s_idx), 0.0) for s_idx in range(len(opp_scores))]
                mean_value = float(np.mean(preds_for_c)) if preds_for_c else 0.0
            else:
                mean_value = 0.0

            # BAMS Score Formula:
            # cand.equity (immediate score + leave value)
            # - opp_penalty_weight * Mean(OppScore) (defensive lane vulnerability)
            # + ValueWeight * Mean(ValueNet) (long-term strategic board control)
            bams_score = (
                (self.config.static_equity_weight * cand.equity)
                - (self.config.opp_penalty_weight * mean_opp_score)
                + (self.config.value_weight * mean_value)
            )

            evaluated_candidates.append(
                BAMSCandidateEval(
                    move=cand,
                    static_equity=cand.equity,
                    immediate_score=cand.score,
                    mean_opp_reply_score=mean_opp_score,
                    mean_value_pred=mean_value,
                    bams_score=bams_score,
                )
            )

        if not evaluated_candidates:
            return eval_candidates[0], {"method": "fallback_top_static", "latency_ms": (time.perf_counter() - start_time) * 1000}

        # Select candidate with highest BAMS score
        best_eval = max(evaluated_candidates, key=lambda e: e.bams_score)
        latency_ms = (time.perf_counter() - start_time) * 1000

        metadata = {
            "method": "bams_mc_rollout",
            "latency_ms": latency_ms,
            "num_candidates_evaluated": len(evaluated_candidates),
            "num_samples": N,
            "best_bams_score": best_eval.bams_score,
            "evaluations": [
                {
                    "word": e.move.word,
                    "row": e.move.row,
                    "col": e.move.col,
                    "direction": e.move.direction,
                    "score": e.immediate_score,
                    "opp_reply_mean": round(e.mean_opp_reply_score, 2),
                    "value_net_mean": round(e.mean_value_pred, 4),
                    "bams_score": round(e.bams_score, 2),
                }
                for e in sorted(evaluated_candidates, key=lambda x: x.bams_score, reverse=True)
            ],
        }

        return best_eval.move, metadata

    def _evaluate_deterministic_endgame(
        self,
        game_state: GameState,
        candidates: List[Move],
        opp_rack_str: str,
    ) -> Tuple[Move, List[Dict[str, Any]]]:
        """Evaluates candidate moves against known opponent rack in the endgame."""
        evals = []
        for cand in candidates:
            try:
                next_state = game_state.apply_move(cand)
                reply = self.engine.best_reply(next_state, opp_rack_str)
                opp_score = reply.score if reply is not None and reply.is_placement else 0
            except Exception:
                opp_score = 0

            net_delta = cand.score - opp_score
            evals.append({
                "move": cand,
                "net_delta": net_delta,
                "score": cand.score,
                "opp_score": opp_score,
            })

        best = max(evals, key=lambda x: x["net_delta"])
        return best["move"], evals
