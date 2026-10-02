"""
Online Game Runner.
Coordinates turn loop between a PlatformAdapter and Alphable AI engine,
applies human-like pacing delays, and saves standardized replay logs for the visualizer.
"""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from alphable.core import inference, search, simulator, leave_eval, defense, endgame
from alphable.platform.base import (
    AbstractPlatformAdapter,
    OnlineGameState,
    PlatformGameConfig,
    PlatformMove,
)


class OnlineGameRunner:
    """
    Manages end-to-end online game execution against human or computer opponents.
    """

    def __init__(
        self,
        adapter: AbstractPlatformAdapter,
        model_path: Optional[str] = None,
        dict_path: str = "resources/CSW24.txt",
        mode: str = "lookahead",
        value_weight: float = 25.0,
        delay_min: float = 2.0,
        delay_max: float = 6.0,
        output_dir: str = "data/woogles/games",
        num_simulations: int = 16,
        top_k: int = 3,
    ):
        self.adapter = adapter
        self.dict_path = dict_path
        self.mode = mode
        self.value_weight = float(value_weight)
        self.delay_min = float(delay_min)
        self.delay_max = float(delay_max)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.matches_dir = self.output_dir.parent / "matches"
        self.matches_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir = self.output_dir.parent / "summaries"
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

        # Initialize AI engine
        device = "cuda" if inference.torch.cuda.is_available() else "cpu"
        print(f"Initializing Alphable AI engine on {device} (model={model_path}, W={self.value_weight})...")
        self.engine = inference.AlphableInference(
            model_path=model_path,
            device=device,
            dict_path=dict_path,
            value_weight=self.value_weight,
        )
        self.searcher = search.AlphableSearch(
            inference_engine=self.engine,
            mode=mode,
            num_simulations=num_simulations,
            top_k_candidates=top_k,
            value_weight=self.value_weight,
            enable_2ply=(mode == "lookahead"),
            two_ply_threshold=8.0,
        )
        if self.mode == "transformer":
            from alphable.models.transformer_ranker import SmolLM2CandidateRanker
            print(f"Initializing SmolLM2 Transformer Candidate Ranker on {device}...")
            self.transformer_ranker = SmolLM2CandidateRanker(device=device)
        else:
            self.transformer_ranker = None

    def play_match(self, config: PlatformGameConfig) -> Dict[str, Any]:
        """
        Executes an online match or series of matches from lobby to completion,
        saving full replays, official GCG exports, and post-game Analyzer evaluations.
        """
        if config.num_games > 1:
            return self.play_series(config)
        return self._execute_single_game(config, game_idx=1, total_games=1)

    def _execute_single_game(
        self,
        config: PlatformGameConfig,
        game_idx: int = 1,
        total_games: int = 1,
        is_rematch: bool = False,
    ) -> Dict[str, Any]:
        """
        Runs a single match, exports GCG and Analyzer data, and organizes files into a per-game folder.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        opponent_display = config.bot_name if config.opponent_type == "bot" else "Human Opponent"

        if total_games > 1:
            print("\n" + "=" * 65)
            print(f"Match {game_idx}/{total_games}: Alphable vs {opponent_display}")
            print(f"Mode: {self.mode}, Dictionary: {config.dictionary}, Time: {config.time_control}")
            print("=" * 65)
        else:
            print("=" * 65)
            print(f"Starting Online Scrabble Match: Alphable vs {opponent_display}")
            print(f"Mode: {self.mode}, Dictionary: {config.dictionary}, Time: {config.time_control}")
            print("=" * 65)

        # 1. Ensure browser session is active and healthy
        if hasattr(self.adapter, "ensure_browser_active"):
            self.adapter.ensure_browser_active()

        turns_log: List[Dict[str, Any]] = []
        turn_idx = 0
        retry_count = 0
        game_url: Optional[str] = getattr(self.adapter, "current_game_url", None) or "unknown"
        match_error: Optional[str] = None

        try:
            if not is_rematch:
                game_url = self.adapter.create_game(config)
            else:
                game_url = getattr(self.adapter, "current_game_url", None) or "unknown"

            while True:
                if turn_idx > 0 and self.adapter.is_game_over():
                    print("Game over detected.")
                    break

                turn_idx += 1
                print(f"\n--- Turn {turn_idx}: Waiting for our turn... ---")
                state = self.adapter.wait_for_my_turn(poll_interval=0.5, timeout=180.0)

                if state.is_game_over:
                    print("Game over detected.")
                    break

                rack_str = "".join(state.rack)
                print(f"Rack: [{rack_str}] | Tiles in bag: {state.bag_remaining}")

                # 2. Compute best move via Alphable
                score_diff = state.my_score - state.opponent_score
                t0 = time.time()

                if self.mode == "lookahead":
                    best_move, best_val = self.searcher.find_best_move(
                        state.board,
                        state.rack,
                        score_diff,
                        state.bag_remaining,
                    )
                elif self.mode == "transformer":
                    legal_moves = self.engine.move_gen.generate(state.board, state.rack)
                    if legal_moves:
                        best_move = None
                        # 1. Exact Endgame Solver Handoff if bag is empty
                        if state.bag_remaining == 0:
                            from alphable.core.search import get_unseen_distribution
                            unseen = get_unseen_distribution(state.board, state.rack)
                            if len(unseen) <= 7:
                                solver = endgame.ExactEndgameSolver(self.engine)
                                eg_move, _ = solver.solve(state.board, state.rack, unseen, score_diff=score_diff)
                                if eg_move:
                                    best_move = eg_move

                        if best_move is None:
                            scored_cands = []
                            for m in legal_moves:
                                nb, pts, nr = simulator.simulate_move(state.board, m, state.rack)
                                l_eq = leave_eval.compute_leave_equity(nr, state.bag_remaining)
                                def_adj = defense.compute_board_defense_adjustment(state.board, nb, m, score_diff)
                                total_eq = float(pts) + l_eq + def_adj
                                scored_cands.append((m, total_eq, def_adj))
                            scored_cands.sort(key=lambda x: x[1], reverse=True)
                            best_heuristic_eq = scored_cands[0][1]
                            competitive_scored = [
                                x for x in scored_cands[:8]
                                if (best_heuristic_eq - x[1]) <= 12.0
                            ]
                            cands = [x[0] for x in competitive_scored]
                            ranked = self.transformer_ranker.rank_candidates(
                                state.board, state.rack, score_diff, state.bag_remaining, cands
                            )
                            if ranked:
                                cand_to_h_eq = {id(x[0]): x[1] for x in competitive_scored}
                                ranked_combined = []
                                for cand, prob, logit in ranked:
                                    h_eq = cand_to_h_eq.get(id(cand), 0.0)
                                    combined_score = h_eq + 8.0 * prob
                                    ranked_combined.append((cand, prob, combined_score))
                                ranked_combined.sort(key=lambda x: x[2], reverse=True)
                                best_cand, best_prob, _ = ranked_combined[0]

                                if len(ranked_combined) > 1 and ranked_combined[1][1] > 0.15:
                                    nb_best, _, _ = simulator.simulate_move(state.board, best_cand, state.rack)
                                    best_def = defense.compute_board_defense_adjustment(state.board, nb_best, best_cand, score_diff)
                                    if best_def <= -3.0:
                                        nb_alt, _, _ = simulator.simulate_move(state.board, ranked_combined[1][0], state.rack)
                                        alt_def = defense.compute_board_defense_adjustment(state.board, nb_alt, ranked_combined[1][0], score_diff)
                                        if alt_def > best_def:
                                            best_cand = ranked_combined[1][0]
                                best_move = best_cand
                        best_val = 0.0
                    else:
                        best_move, best_val = None, 0.0
                else:
                    best_move, best_val = self.engine.find_best_move(
                        state.board,
                        state.rack,
                        score_diff,
                        state.bag_remaining,
                    )

                calc_time = time.time() - t0

                # 3. Apply human-like pacing delay
                think_delay = random.uniform(self.delay_min, self.delay_max)
                actual_sleep = max(0.1, think_delay - calc_time)
                print(f"Move computed in {calc_time:.2f}s. Pacing delay: {actual_sleep:.2f}s...")
                time.sleep(actual_sleep)

                # 4. Submit move to platform
                if best_move is not None:
                    action = best_move.get("action", "PLAY")
                    if action == "EXCHANGE":
                        exch_tiles = best_move.get("tiles_to_exchange", [])
                        print(f"Executing EXCHANGE of {exch_tiles} (Value: {best_val:.3f})")
                        move_cmd = PlatformMove(
                            action="EXCHANGE",
                            tiles_to_exchange=exch_tiles,
                        )
                        success = self.adapter.play_move(move_cmd)
                        if not success:
                            retry_count += 1
                            print(f"⚠ Exchange was not accepted by platform (attempt {retry_count}/3). Retrying...")
                            time.sleep(1.0)
                            if retry_count < 3:
                                turn_idx -= 1
                                continue
                            else:
                                print("⚠ Maximum retries (3) exceeded for exchange. Passing turn to prevent timeout forfeit...")
                                self.adapter.play_move(PlatformMove(action="PASS"))
                                turns_log.append({
                                    "turn": turn_idx,
                                    "player": 0,
                                    "action_type": "PASS",
                                    "timestamp": datetime.now().isoformat(),
                                })
                                retry_count = 0
                                time.sleep(1.0)
                                continue

                        retry_count = 0
                        turns_log.append({
                            "turn": turn_idx,
                            "player": 0,
                            "action_type": "EXCHANGE",
                            "tiles_to_exchange": exch_tiles,
                            "points": 0,
                            "value": round(float(best_val), 4),
                            "rack": rack_str,
                            "timestamp": datetime.now().isoformat(),
                        })
                    else:
                        word = best_move["word"]
                        r = best_move["row"]
                        c = best_move["col"]
                        d = best_move["dir"]
                        pts = best_move.get("points", 0)

                        print(f"Playing: '{word}' at ({r},{c}) {d} (Est Points: {pts}, Value: {best_val:.3f})")

                        move_cmd = PlatformMove(
                            action="PLAY",
                            word=word,
                            row=r,
                            col=c,
                            direction=d,
                        )
                        success = self.adapter.play_move(move_cmd)
                        if not success:
                            retry_count += 1
                            print(f"⚠ Move was not accepted by platform (attempt {retry_count}/3). Recalling tiles and re-evaluating...")
                            self.adapter.recall_tiles()
                            time.sleep(1.0)
                            if retry_count < 3:
                                turn_idx -= 1
                                continue
                            else:
                                print("⚠ Maximum retries (3) exceeded for play. Passing turn to prevent timeout forfeit...")
                                self.adapter.play_move(PlatformMove(action="PASS"))
                                turns_log.append({
                                    "turn": turn_idx,
                                    "player": 0,
                                    "action_type": "PASS",
                                    "timestamp": datetime.now().isoformat(),
                                })
                                retry_count = 0
                                time.sleep(1.0)
                                continue

                        retry_count = 0

                        turns_log.append({
                            "turn": turn_idx,
                            "player": 0,
                            "action_type": "PLAY",
                            "word": word,
                            "row": r,
                            "col": c,
                            "direction": d,
                            "points": pts,
                            "value": round(float(best_val), 4),
                            "rack": rack_str,
                            "timestamp": datetime.now().isoformat(),
                        })
                else:
                    print("No legal plays found. Passing turn...")
                    self.adapter.play_move(PlatformMove(action="PASS"))
                    turns_log.append({
                        "turn": turn_idx,
                        "player": 0,
                        "action_type": "PASS",
                        "timestamp": datetime.now().isoformat(),
                    })
                    retry_count = 0

                # Allow server to register move
                time.sleep(1.0)

        except KeyboardInterrupt:
            print("\nMatch interrupted by user.")
            match_error = "interrupted"
        except Exception as e:
            import traceback
            print(f"Exception during match execution: {e}")
            traceback.print_exc()
            match_error = str(e)

        # 5. Extract Final Result
        final_result = self.adapter.get_final_result()
        opponent_name = final_result.get("opponent_name", opponent_display)

        # 6. Setup dedicated Match Directory
        raw_id = (game_url or "").rstrip("/").split("/")[-1] if game_url else "unknown"
        game_id = raw_id.split("?")[0] if raw_id else "unknown"
        match_folder_name = f"match_{timestamp}_{game_id}"
        match_dir = self.matches_dir / match_folder_name
        match_dir.mkdir(parents=True, exist_ok=True)

        # 7. Export GCG if requested
        gcg_path_str: Optional[str] = None
        if config.export_gcg:
            gcg_file = match_dir / "game.gcg"
            gcg_path_str = self.adapter.export_gcg(str(gcg_file))

        # 8. Extract Analyzer evaluations if requested
        analysis_data: List[Dict[str, Any]] = []
        if config.extract_analysis:
            analysis_data = self.adapter.extract_analysis()
            if analysis_data:
                analysis_path = match_dir / "analysis.json"
                with open(analysis_path, "w", encoding="utf-8") as f:
                    json.dump(analysis_data, f, indent=2)

        # 9. Save Replay JSON in match folder and backward compatibility in output_dir
        replay_path = match_dir / "replay.json"
        legacy_replay_path = self.output_dir / f"game_{timestamp}.json"

        replay_data = {
            "metadata": {
                "platform": "woogles",
                "game_url": game_url,
                "opponent": opponent_name,
                "bot_name": config.bot_name,
                "dictionary": config.dictionary,
                "time_control": config.time_control,
                "mode": self.mode,
                "value_weight": self.value_weight,
                "timestamp": timestamp,
                "game_index": game_idx,
                "total_games": total_games,
            },
            "player_names": [final_result.get("my_name", "Alphable"), opponent_name],
            "final_score": [final_result.get("my_score", 0), final_result.get("opponent_score", 0)],
            "winner": final_result.get("winner", "Unknown"),
            "gcg_export": gcg_path_str,
            "analysis_turns_count": len(analysis_data),
            "turns": turns_log,
        }

        with open(replay_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, indent=2)

        with open(legacy_replay_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, indent=2)

        # 10. Save Match Summary
        summary_path = match_dir / "summary.json"
        legacy_summary_path = self.summaries_dir / f"run_{timestamp}_summary.json"
        summary_data = {
            "timestamp": timestamp,
            "platform": "woogles",
            "match_id": game_id,
            "match_folder": str(match_dir),
            "opponent": opponent_name,
            "game_replay": str(replay_path),
            "gcg_file": gcg_path_str,
            "has_analysis": len(analysis_data) > 0,
            "final_score": replay_data["final_score"],
            "winner": replay_data["winner"],
            "turns_count": len(turns_log),
            "status": f"error: {match_error}" if match_error else "completed",
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        with open(legacy_summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        print("\n" + "=" * 65)
        print(f"MATCH COMPLETED: {summary_data['winner']} won ({summary_data['final_score'][0]} - {summary_data['final_score'][1]})")
        print(f"📁 Match folder: {match_dir}")
        if gcg_path_str:
            print(f"📄 GCG export: {gcg_path_str}")
        if analysis_data:
            print(f"📊 Macondo analysis: {len(analysis_data)} turns saved to analysis.json")
        print("=" * 65)

        return summary_data

    def play_series(self, config: PlatformGameConfig) -> Dict[str, Any]:
        """
        Executes a series of N online matches, chaining games via Rematch where available.
        """
        series_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        opponent_display = config.bot_name if config.opponent_type == "bot" else "Human"

        print("\n" + "#" * 65)
        print(f"STARTING ONLINE SCRABBLE SERIES ({config.num_games} Games)")
        print(f"Opponent: {opponent_display}, Mode: {self.mode}, Dictionary: {config.dictionary}")
        print("#" * 65)

        series_results: List[Dict[str, Any]] = []
        my_wins = 0
        opp_wins = 0
        draws = 0
        score_diffs = []

        is_rematch_ready = False
        for game_idx in range(1, config.num_games + 1):
            try:
                summary = self._execute_single_game(
                    config,
                    game_idx=game_idx,
                    total_games=config.num_games,
                    is_rematch=is_rematch_ready,
                )
            except Exception as e:
                import traceback
                print(f"\n❌ Uncaught error during Match {game_idx}/{config.num_games}: {e}")
                traceback.print_exc()

                summary = {
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "platform": "woogles",
                    "match_id": "error",
                    "match_folder": "",
                    "opponent": config.bot_name or "Opponent",
                    "game_replay": None,
                    "gcg_file": None,
                    "has_analysis": False,
                    "final_score": [0, 0],
                    "winner": config.bot_name or "Opponent",
                    "turns_count": 0,
                    "my_name": "Alphable",
                    "status": f"error: {e}",
                }

                # Reset browser to lobby so subsequent match starts with a clean slate
                try:
                    if hasattr(self.adapter, "ensure_browser_active"):
                        self.adapter.ensure_browser_active()
                    if hasattr(self.adapter, "reset_to_lobby"):
                        self.adapter.reset_to_lobby()
                except Exception as res_err:
                    print(f"Failed to reset browser to lobby after error: {res_err}")

            series_results.append(summary)

            my_score, opp_score = summary["final_score"]
            diff = my_score - opp_score
            score_diffs.append(diff)
            winner = summary["winner"]

            my_name = summary.get("my_name", "Alphable")
            if winner == my_name or (my_score > opp_score and winner not in ("Draw", summary["opponent"])):
                my_wins += 1
            elif winner == "Draw" or my_score == opp_score:
                draws += 1
            else:
                opp_wins += 1

            # Save intermediate series summary after each game so progress is never lost
            avg_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0.0
            series_summary_path = self.summaries_dir / f"run_{series_timestamp}_series.json"
            series_summary_data = {
                "timestamp": series_timestamp,
                "total_games": config.num_games,
                "completed_games": len(series_results),
                "alphable_wins": my_wins,
                "opponent_wins": opp_wins,
                "draws": draws,
                "average_score_diff": round(avg_diff, 2),
                "games": series_results,
            }
            try:
                with open(series_summary_path, "w", encoding="utf-8") as f:
                    json.dump(series_summary_data, f, indent=2)
            except Exception:
                pass

            is_rematch_ready = False
            if game_idx < config.num_games:
                time.sleep(1.0)
                rematch_success = False
                if summary.get("status") == "completed":
                    try:
                        rematch_success = self.adapter.trigger_rematch()
                    except Exception:
                        rematch_success = False

                if rematch_success:
                    is_rematch_ready = True
                else:
                    print("Rematch unavailable. Launching next match in lobby...")
                    if hasattr(self.adapter, "ensure_browser_active"):
                        self.adapter.ensure_browser_active()
                    if hasattr(self.adapter, "reset_to_lobby"):
                        self.adapter.reset_to_lobby()

        avg_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0.0
        series_summary_path = self.summaries_dir / f"run_{series_timestamp}_series.json"
        series_summary_data = {
            "timestamp": series_timestamp,
            "total_games": config.num_games,
            "completed_games": len(series_results),
            "alphable_wins": my_wins,
            "opponent_wins": opp_wins,
            "draws": draws,
            "average_score_diff": round(avg_diff, 2),
            "games": series_results,
        }

        with open(series_summary_path, "w", encoding="utf-8") as f:
            json.dump(series_summary_data, f, indent=2)

        print("\n" + "#" * 65)
        print("SERIES COMPLETED")
        print(f"Wins / Losses / Draws: {my_wins} / {opp_wins} / {draws}")
        print(f"Win Rate: {my_wins / config.num_games:.1%}")
        print(f"Average Score Diff: {avg_diff:+.1f}")
        print(f"Series summary saved: {series_summary_path}")
        print("#" * 65)

        return series_summary_data
