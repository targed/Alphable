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
import os
import time
from dataclasses import dataclass, field, replace
from typing import List, Tuple, Dict, Optional, Any, Union

import numpy as np
import torch

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState, TW_SQUARES, DW_SQUARES, VOWELS
from alphable_v4.engine.magpie_bindings import MagpieEngine
from alphable_v4.models.belief_net import BayesianRackInference, OpponentTracker
from alphable_v4.models.value_net import V4ValueNetwork
from alphable_v4.models.compiled_inference import CompiledValueNetwork


@dataclass
class BAMSConfig:
    """Configuration hyperparameters for BAMS search."""
    num_samples: int = 24           # Number of opponent rack simulations (N)
    candidate_beam: int = 15        # Base top static-equity candidates to rollout (K)
    value_weight: float = 4.5       # Points-scale multiplier for centered normalized equity [-1, 1]
    static_equity_weight: float = 1.0 # Blending weight for MAGPIE's static leave equity
    opp_penalty_weight: float = 0.12  # Relative excess counter-play risk penalty weight
    max_static_deficit: float = 3.5   # Base maximum static equity deficit allowed for rollout
    use_crn: bool = True            # Common Random Numbers for opponent rack samples
    dynamic_beam: bool = True       # Context-adaptive beam size and deficit scaling
    use_exact_endgame: bool = True  # Native alpha-beta minimax endgame solver (depth 6-10)
    use_pre_endgame: bool = True    # Pre-endgame parity & tile-sticking solver (bag 1 to 5) (Frontier 3)
    use_belief_tracker: bool = True # History-conditioned Bayesian belief tracker (Frontier 2)
    use_volatility_control: bool = True # Asymmetric board topology and volatility control (Pillar 2)
    volatility_weight: float = 1.0  # Blending multiplier for board volatility adjustments
    nested_2ply: bool = True        # True 2-ply nested Monte Carlo rollout lookahead (Frontier 1)
    candidate_beam_2ply: int = 6    # Number of top candidates evaluated with full 2-ply search
    samples_2ply: int = 12          # Number of opponent rack samples for 2-ply stage
    weight_2ply: float = 0.18       # Weight for 2-ply net exchange score in BAMS score
    hybrid_pimc: bool = False       # Hybrid native C PIMC simulation + Neural Value Network re-ranking
    sim_iterations: int = 25        # Iterations per candidate in native C PIMC simulation (~98k nps)
    use_pat: bool = True            # Positional Adjustment Term candidate generator
    pimc_weight: float = 1.0        # Weight for native PIMC simulated return
    win_prob_weight: float = 15.0   # Weight for simulated win probability
    use_compiled_model: bool = True # Fast TorchScript/ONNX compiled model if available
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
    mean_2ply_net: Optional[float] = None


class BAMSSearch:
    """
    Belief-Augmented Monte Carlo Search engine.
    """

    def __init__(
        self,
        engine: MagpieEngine,
        value_net: Optional[Union[V4ValueNetwork, CompiledValueNetwork]] = None,
        belief_net: Optional[BayesianRackInference] = None,
        config: Optional[BAMSConfig] = None,
    ):
        self.engine = engine
        self.config = config or BAMSConfig()
        self.belief_net = belief_net or BayesianRackInference()
        self.opp_tracker = OpponentTracker()
        self.device = torch.device(self.config.device)

        if value_net is not None:
            self.value_net = value_net.to(self.device)
            self.value_net.eval()
        else:
            self.value_net = None

    def record_opponent_move(
        self,
        opp_move: Move,
        state_before: Optional[GameState] = None,
    ) -> None:
        """Records opponent's move to update Bayesian belief tracker (Frontier 2)."""
        if getattr(self.config, "use_belief_tracker", True):
            self.opp_tracker.update_after_opponent_move(
                opp_move, state_before=state_before, engine=self.engine
            )

    @classmethod
    def from_checkpoint(
        cls,
        engine: MagpieEngine,
        checkpoint_path: str,
        config: Optional[BAMSConfig] = None,
    ) -> BAMSSearch:
        """Instantiates BAMSSearch by loading a trained Value Network checkpoint."""
        conf = config or BAMSConfig()

        # Check if a compiled TorchScript model is available alongside checkpoint
        candidates = [
            checkpoint_path.replace(".pt", "_compiled.pt"),
            checkpoint_path.replace("_best.pt", "_compiled.pt"),
            os.path.join(os.path.dirname(checkpoint_path), "v4_value_net_compiled.pt"),
        ]
        if getattr(conf, "use_compiled_model", True):
            for c_path in candidates:
                if os.path.exists(c_path):
                    try:
                        model = CompiledValueNetwork(c_path, device=conf.device)
                        return cls(engine=engine, value_net=model, config=conf)
                    except Exception:
                        pass

        model = V4ValueNetwork(board_channels=32, state_dim=64, feature_dim=512, num_heads=8)
        checkpoint = torch.load(checkpoint_path, map_location=conf.device, weights_only=False)
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"], strict=False)
        else:
            model.load_state_dict(checkpoint, strict=False)
        return cls(engine=engine, value_net=model, config=conf)

    def get_dynamic_search_params(self, game_state: GameState) -> Tuple[int, float]:
        """
        Dynamically adjusts candidate beam size K and maximum static equity deficit
        based on match context, score differential, and tile bag exhaustion.
        """
        if not getattr(self.config, "dynamic_beam", True):
            return self.config.candidate_beam, getattr(self.config, "max_static_deficit", 5.0)

        score_diff = game_state.score - game_state.opp_score
        bag_count = game_state.bag_count

        base_beam = self.config.candidate_beam
        base_deficit = getattr(self.config, "max_static_deficit", 5.0)

        # Trailing by >= 25 points: Widen deficit and beam to find high-ceiling comeback plays
        if score_diff <= -25:
            beam = min(25, max(base_beam, 18))
            deficit = max(base_deficit, 7.5)
        # Leading by >= 35 points: Tighten search to safe, high-equity plays
        elif score_diff >= 35:
            beam = max(8, min(base_beam, 10))
            deficit = min(base_deficit, 3.0)
        # Early game (bag >= 50): Allow broader strategic exploration
        elif bag_count >= 50:
            beam = max(base_beam, 15)
            deficit = max(base_deficit, 6.0)
        else:
            beam = base_beam
            deficit = base_deficit

        return beam, deficit

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
        if getattr(self.config, "hybrid_pimc", False):
            return self.select_move_hybrid_pimc(game_state, candidates=candidates)

        start_time = time.perf_counter()
        N = num_samples if num_samples is not None else self.config.num_samples
        beam_size, max_deficit = self.get_dynamic_search_params(game_state)

        # 1. Candidate Generation
        if candidates is None:
            candidates = self.engine.generate_moves(
                game_state=game_state, max_candidates=max(100, beam_size)
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
        eval_candidates = [
            c for c in candidates[:beam_size]
            if (top_equity - c.equity) <= max_deficit
        ]
        if not eval_candidates:
            eval_candidates = candidates[:1]

        # 2. Check for Endgame Fast Path (unseen tiles <= 7)
        total_unseen = sum(game_state.unseen_counts.values())
        if total_unseen <= 7:
            if game_state.bag_count == 0 and getattr(self.config, "use_exact_endgame", True):
                exact_m, exact_meta = self._solve_exact_endgame(game_state, candidates)
                if exact_m is not None:
                    exact_meta["latency_ms"] = (time.perf_counter() - start_time) * 1000
                    return exact_m, exact_meta

            # Fallback deterministic endgame: opponent holds all remaining unseen tiles
            opp_rack_str = "".join(self.belief_net.get_unseen_tile_pool(game_state))
            selected, evals = self._evaluate_deterministic_endgame(game_state, eval_candidates, opp_rack_str)
            latency_ms = (time.perf_counter() - start_time) * 1000
            return selected, {
                "method": "deterministic_endgame",
                "latency_ms": latency_ms,
                "evaluations": evals,
                "opp_rack": opp_rack_str,
            }

        # 2.5. Pre-Endgame Parity & Fishing Adjustment (bag count 1 to 5) (Frontier 3)
        if 1 <= game_state.bag_count <= 5 and getattr(self.config, "use_pre_endgame", True):
            eval_candidates = self._evaluate_pre_endgame(game_state, eval_candidates)

        # 3. Sample N opponent racks using Bayesian inference with CRN & History Belief (Frontier 2)
        seed = self.config.seed if self.config.use_crn else None
        tracker = self.opp_tracker if getattr(self.config, "use_belief_tracker", True) else None
        sampled_rack_lists = self.belief_net.sample_opponent_racks(
            game_state, num_samples=N, seed=seed, tracker=tracker
        )
        sampled_racks = ["".join(r) for r in sampled_rack_lists]

        # 4. Monte Carlo 1-ply & 2-ply Simulation (Frontier 1)
        cand_results: List[Dict[str, Any]] = []
        after_states_to_eval: List[GameState] = []
        state_index_mapping: List[Tuple[int, int]] = []  # (cand_idx, sample_idx)

        use_2ply = getattr(self.config, "nested_2ply", True)
        beam_2ply = getattr(self.config, "candidate_beam_2ply", 6)
        samples_2ply_n = min(N, getattr(self.config, "samples_2ply", 12))
        unseen_pool = self.belief_net.get_unseen_tile_pool(game_state) if use_2ply else []

        for c_idx, cand in enumerate(eval_candidates):
            # Apply our move
            try:
                state_after_cand = game_state.apply_move(cand)
            except Exception:
                continue

            resulting_board = state_after_cand.board if cand.is_placement else game_state.board
            cand_entry = {
                "candidate": cand,
                "immediate_score": cand.score,
                "static_equity": cand.equity,
                "opp_scores": [],
                "2ply_scores": [],
                "volatility": self.compute_board_volatility(resulting_board) if getattr(self.config, "use_volatility_control", True) else 0.0,
            }
            is_2ply_cand = use_2ply and cand.is_placement and (c_idx < beam_2ply)

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

                # True 2-Ply Nested Lookahead (Frontier 1)
                if is_2ply_cand and (s_idx < samples_2ply_n):
                    try:
                        tiles_needed = 7 - len(cand.leave or "")
                        rem_pool = list(unseen_pool)
                        for t in opp_r:
                            if t in rem_pool:
                                rem_pool.remove(t)
                        rng = np.random.RandomState(42 + s_idx * 17) if self.config.use_crn else np.random
                        drawn_idx = rng.choice(len(rem_pool), size=min(len(rem_pool), tiles_needed), replace=False) if rem_pool else []
                        sim_rack = list(cand.leave or "") + [rem_pool[i] for i in drawn_idx]

                        followups = self.engine.generate_moves(game_state=resulting_state, rack="".join(sim_rack), max_candidates=1)
                        followup_eq = followups[0].equity if followups else 0.0
                        net_2ply = cand.score - opp_score + followup_eq
                    except Exception:
                        net_2ply = cand.score - opp_score + (cand.equity - cand.score)
                    cand_entry["2ply_scores"].append(net_2ply)

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

        # 6. Aggregate BAMS Scores with Relative Counterplay Risk & 2-Ply Net Exchange
        all_opp_means = [float(np.mean(cand_dict["opp_scores"])) if cand_dict["opp_scores"] else 0.0 for cand_dict in cand_results]
        baseline_opp_score = float(np.mean(all_opp_means)) if all_opp_means else 0.0

        all_2ply_means = [
            float(np.mean(cand_dict["2ply_scores"])) if cand_dict.get("2ply_scores") else None
            for cand_dict in cand_results
        ]
        valid_2ply = [m for m in all_2ply_means if m is not None]
        baseline_2ply = float(np.mean(valid_2ply)) if valid_2ply else 0.0

        if self.value_net is not None:
            all_val_means = [
                float(np.mean([value_preds.get((c_idx, s_idx), 0.0) for s_idx in range(len(cand_dict["opp_scores"]))]))
                if cand_dict["opp_scores"] else 0.0
                for c_idx, cand_dict in enumerate(cand_results)
            ]
            baseline_value = float(np.mean(all_val_means)) if all_val_means else 0.0
        else:
            all_val_means = [0.0] * len(cand_results)
            baseline_value = 0.0

        all_vols = [cd.get("volatility", 0.0) for cd in cand_results]
        baseline_vol = float(np.mean(all_vols)) if all_vols else 0.0

        evaluated_candidates: List[BAMSCandidateEval] = []
        for c_idx, cand_dict in enumerate(cand_results):
            cand = cand_dict["candidate"]
            mean_opp_score = all_opp_means[c_idx]
            mean_value = all_val_means[c_idx]
            mean_2ply = all_2ply_means[c_idx]

            # Relative counterplay threat: only penalize above-average opponent leakiness
            relative_threat = mean_opp_score - baseline_opp_score
            # Relative positional advantage from Value Network
            relative_value = mean_value - baseline_value
            # Relative 2-ply net exchange advantage (strictly for placement moves)
            if cand.is_placement and mean_2ply is not None:
                relative_2ply = mean_2ply - baseline_2ply
                w_2ply = getattr(self.config, "weight_2ply", 0.18)
            else:
                relative_2ply = 0.0
                w_2ply = 0.0

            # Asymmetric Game-State Volatility Control (Pillar 2)
            if getattr(self.config, "use_volatility_control", True):
                score_diff = game_state.score - game_state.opp_score
                # Continuous linear ramp saturating at +/- 2.0 (reached at score_diff = +/- 80)
                clamped_ratio = max(-2.0, min(2.0, float(score_diff) / 40.0))
                lambda_vol = -0.15 * clamped_ratio
                relative_vol = cand_dict.get("volatility", 0.0) - baseline_vol
                vol_adjustment = lambda_vol * getattr(self.config, "volatility_weight", 1.0) * relative_vol
            else:
                vol_adjustment = 0.0

            # BAMS Score Formula:
            # cand.equity (immediate score + leave value)
            # - opp_penalty_weight * relative_threat (penalizes plays leakier than alternatives)
            # + weight_2ply * relative_2ply (rewards superior 2-turn net point exchange)
            # + value_weight * relative_value (rewards superior future board control)
            # + vol_adjustment (rewards board closure when leading, openness when trailing)
            bams_score = (
                (self.config.static_equity_weight * cand.equity)
                - (self.config.opp_penalty_weight * relative_threat)
                + (w_2ply * relative_2ply)
                + (self.config.value_weight * relative_value)
                + vol_adjustment
            )

            evaluated_candidates.append(
                BAMSCandidateEval(
                    move=cand,
                    static_equity=cand.equity,
                    immediate_score=cand.score,
                    mean_opp_reply_score=mean_opp_score,
                    mean_value_pred=mean_value,
                    bams_score=bams_score,
                    mean_2ply_net=mean_2ply,
                )
            )

        if not evaluated_candidates:
            return eval_candidates[0], {"method": "fallback_top_static", "latency_ms": (time.perf_counter() - start_time) * 1000}

        # Select candidate with highest BAMS score
        best_eval = max(evaluated_candidates, key=lambda e: e.bams_score)
        latency_ms = (time.perf_counter() - start_time) * 1000

        metadata = {
            "method": "bams_mc_rollout_2ply" if use_2ply else "bams_mc_rollout",
            "latency_ms": latency_ms,
            "num_candidates_evaluated": len(evaluated_candidates),
            "num_samples": N,
            "sampled_racks": sampled_racks[:8],
            "best_bams_score": best_eval.bams_score,
            "evaluations": [
                {
                    "word": e.move.word,
                    "row": e.move.row,
                    "col": e.move.col,
                    "direction": e.move.direction,
                    "score": e.immediate_score,
                    "opp_reply_mean": round(e.mean_opp_reply_score, 2),
                    "mean_2ply_net": round(e.mean_2ply_net, 2) if e.mean_2ply_net is not None else None,
                    "value_net_mean": round(e.mean_value_pred, 4),
                    "bams_score": round(e.bams_score, 2),
                }
                for e in sorted(evaluated_candidates, key=lambda x: x.bams_score, reverse=True)
            ],
        }

        return best_eval.move, metadata

    def select_move_hybrid_pimc(
        self,
        game_state: GameState,
        candidates: Optional[List[Move]] = None,
    ) -> Tuple[Move, Dict[str, Any]]:
        """
        Hybrid decision policy: Combines native C PIMC simulation rollouts (~98k nps)
        with Cross-Attention Value Network re-ranking and volatility control.
        """
        start_time = time.perf_counter()

        # 1. Candidate Generation
        if candidates is None:
            candidates = self.engine.generate_moves(game_state=game_state, max_candidates=15)

        if not candidates:
            return Move.create_pass(), {"method": "fallback_pass", "latency_ms": (time.perf_counter() - start_time) * 1000}

        if len(candidates) == 1:
            return candidates[0], {"method": "forced_move", "latency_ms": (time.perf_counter() - start_time) * 1000}

        # 2. Check for Endgame Fast Path (unseen tiles <= 7)
        total_unseen = sum(game_state.unseen_counts.values())
        if total_unseen <= 7 and game_state.bag_count == 0 and getattr(self.config, "use_exact_endgame", True):
            exact_m, exact_meta = self._solve_exact_endgame(game_state, candidates)
            if exact_m is not None:
                exact_meta["latency_ms"] = (time.perf_counter() - start_time) * 1000
                return exact_m, exact_meta

        # 3. Native C Monte Carlo Simulation
        sim_results = self.engine.simulate_candidates(
            iterations=getattr(self.config, "sim_iterations", 25),
            candidate_moves=candidates,
            game_state=game_state,
        )

        if not sim_results:
            return candidates[0], {"method": "pimc_fallback_static", "latency_ms": (time.perf_counter() - start_time) * 1000}

        # 4. Neural Value & Volatility Re-Ranking on top simulated candidates (top 4)
        top_sim = sim_results[:4]
        scored_candidates = []
        score_diff = game_state.score - game_state.opp_score

        for entry in top_sim:
            cand = entry["move"]
            sim_equity = entry["sim_equity"]
            win_prob = entry["win_prob"]

            # Construct after-state
            try:
                state_after = game_state.apply_move(cand)
                resulting_board = state_after.board if cand.is_placement else game_state.board
            except Exception:
                state_after = game_state
                resulting_board = game_state.board

            # Neural Value Prediction
            neural_val = 0.0
            if self.value_net is not None:
                try:
                    with torch.no_grad():
                        b_tensor = state_after.to_board_tensor().unsqueeze(0).to(self.device)
                        s_vector = state_after.to_state_vector().unsqueeze(0).to(self.device)
                        neural_pred = self.value_net.evaluate_batch(b_tensor, s_vector)
                        neural_val = float(neural_pred.squeeze().cpu().numpy())
                except Exception:
                    neural_val = 0.0

            # Volatility control: penalize variance when ahead, reward variance when trailing
            volatility = self.compute_board_volatility(resulting_board) if getattr(self.config, "use_volatility_control", True) else 0.0
            vol_clamp = max(-0.30, min(0.60, 0.15 + (score_diff / 100.0)))

            pimc_w = getattr(self.config, "pimc_weight", 1.0)
            win_w = getattr(self.config, "win_prob_weight", 15.0)
            val_w = getattr(self.config, "value_weight", 4.5)

            composite_score = (sim_equity * pimc_w) + (win_prob * win_w) + (neural_val * val_w) - (volatility * vol_clamp)

            scored_candidates.append({
                "candidate": cand,
                "composite_score": composite_score,
                "sim_equity": sim_equity,
                "win_prob": win_prob,
                "neural_val": neural_val,
                "volatility": volatility,
            })

        best = max(scored_candidates, key=lambda x: x["composite_score"])
        latency_ms = (time.perf_counter() - start_time) * 1000

        return best["candidate"], {
            "method": "hybrid_pimc",
            "latency_ms": latency_ms,
            "composite_score": best["composite_score"],
            "sim_equity": best["sim_equity"],
            "win_prob": best["win_prob"],
            "neural_val": best["neural_val"],
            "scored_candidates": scored_candidates,
        }

    def _solve_exact_endgame(
        self,
        game_state: GameState,
        candidates: List[Move],
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        """
        Solves the endgame using MAGPIE's exact alpha-beta minimax solver (depth 6-10).
        Matches the returned play against legal candidate moves.
        """
        # First try direct native move solver
        try:
            native_m = self.engine.solve_endgame_move(game_state=game_state, candidate_moves=candidates)
            if native_m is not None:
                return native_m, {"method": "exact_alphabeta_endgame", "native": True}
        except Exception:
            pass

        try:
            cgp_str = game_state.to_cgp()
            self.engine.set_cgp(cgp_str)
            raw_output = self.engine.run_command("endgame")
            lines = [l.strip() for l in raw_output.splitlines() if l.strip()]

            header_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("Play"):
                    header_idx = i
                    break

            if header_idx != -1 and header_idx + 1 < len(lines):
                play_line = lines[header_idx + 1]
                tokens = play_line.split()
                if len(tokens) >= 3:
                    coord_str = tokens[0].upper()
                    clean_word = tokens[1].replace("(", "").replace(")", "").upper()
                    score_val = int(tokens[2]) if tokens[2].lstrip("-").isdigit() else None

                    # Primary match: coordinate + word
                    for c in candidates:
                        if c.coord_str.upper() == coord_str and c.word.upper() == clean_word:
                            return c, {
                                "method": "exact_alphabeta_endgame",
                                "raw_solver": play_line,
                            }

                    # Secondary match: coordinate + score
                    if score_val is not None:
                        for c in candidates:
                            if c.coord_str.upper() == coord_str and c.score == score_val:
                                return c, {
                                    "method": "exact_alphabeta_endgame",
                                    "raw_solver": play_line,
                                }
        except Exception:
            pass

        return None, {}

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

    def _evaluate_pre_endgame(
        self,
        game_state: GameState,
        candidates: List[Move],
    ) -> List[Move]:
        """
        Frontier 3: Pre-Endgame Parity & Tile-Sticking Adjustment (bag count 1 to 5).
        
        Calculates:
        1. Bag-emptying parity: Empties the bag, freezing opponent with their current rack
           and transitioning directly into exact minimax endgame.
        2. Dangerous tile sticking: Analyzes unseen tile hazards (e.g. stranded Q without U,
           hard-to-play heavy consonants) and rewards plays that force the opponent to draw them.
        3. Favorable tile capture: Rewards plays that secure valuable tiles (e.g. Blank or S).
        """
        unseen_pool = self.belief_net.get_unseen_tile_pool(game_state)
        n_unseen = max(1, len(unseen_pool))
        bag_count = game_state.bag_count

        # Identify U-tile availability on board or rack for Q assessment
        has_u_on_board_or_leave = any(
            row_cell == "U" or row_cell == "u"
            for row in game_state.board
            for row_cell in row
            if row_cell
        )

        def _tile_hazard(t: str, leave_str: str) -> float:
            t_upper = t.upper()
            if t_upper == "Q":
                can_pair_u = has_u_on_board_or_leave or ("U" in leave_str)
                return -3.5 if can_pair_u else -7.5
            elif t_upper in ("Z", "J", "X"):
                return -2.5
            elif t_upper in ("V", "W"):
                return -2.0
            elif t_upper == "?":
                return 4.0
            elif t_upper == "S":
                return 2.0
            return 0.0

        adjusted_candidates: List[Move] = []
        rack_size = len(game_state.rack) if game_state.rack else 7
        for cand in candidates:
            leave_str = cand.leave or ""
            tiles_played = cand.get_tiles_played(rack_len=rack_size)

            pool_hazard_sum = sum(_tile_hazard(t, leave_str) for t in unseen_pool)
            mean_pool_hazard = pool_hazard_sum / n_unseen

            parity_delta = 0.0

            if tiles_played >= bag_count:
                # Bag is emptied!
                # Tempo bonus: freezes opponent and closes the bag
                parity_delta += 2.0
                draw_count = min(bag_count, 7 - len(leave_str))
                parity_delta += (draw_count / n_unseen) * pool_hazard_sum
            else:
                # Bag has tiles remaining: bag_rem = bag_count - tiles_played >= 1
                bag_rem = bag_count - tiles_played
                if bag_rem == 1:
                    # Opponent will draw the final tile if they play >= 1 tile!
                    # If unseen tiles are hazardous (pool_hazard < 0), sticking opp is positive
                    parity_delta -= mean_pool_hazard * 1.5
                else:
                    parity_delta -= (bag_rem / n_unseen) * pool_hazard_sum * 0.5

            if len(leave_str) <= 2:
                parity_delta += 0.8

            new_equity = cand.equity + parity_delta
            adjusted_candidates.append(replace(cand, equity=new_equity))

        # Re-sort candidates by updated equity descending
        adjusted_candidates.sort(key=lambda c: c.equity, reverse=True)
        return adjusted_candidates

    def compute_board_volatility(self, board: List[List[Optional[str]]]) -> float:
        """
        Measures board topological openness and vulnerability to high-scoring hooks (Pillar 2).
        Higher values indicate volatile, open boards with accessible premium squares.
        """
        tw_open = 0
        for r, c in TW_SQUARES:
            if board[r][c] is None:
                if any(board[r][i] is not None for i in range(15)) or any(board[j][c] is not None for j in range(15)):
                    tw_open += 1

        dw_open = 0
        for r, c in DW_SQUARES:
            if board[r][c] is None:
                if any(board[r][i] is not None for i in range(15)) or any(board[j][c] is not None for j in range(15)):
                    dw_open += 1

        open_vowels = 0
        for r in range(15):
            for c in range(15):
                val = board[r][c]
                if val and val.upper() in VOWELS:
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 15 and 0 <= nc < 15 and board[nr][nc] is None:
                            open_vowels += 1
                            break

        return float(tw_open * 1.5 + dw_open * 0.5 + open_vowels * 0.2)
