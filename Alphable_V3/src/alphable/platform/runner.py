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

from alphable.core import inference, search
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
        value_weight: float = 60.0,
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
        )

    def play_match(self, config: PlatformGameConfig) -> Dict[str, Any]:
        """
        Executes a single online match from lobby creation to game over and replay saving.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print("=" * 65)
        print(f"Starting Online Scrabble Match: Alphable vs {config.bot_name}")
        print(f"Mode: {self.mode}, Dictionary: {config.dictionary}, Time: {config.time_control}")
        print("=" * 65)

        # 1. Create or join game
        game_url = self.adapter.create_game(config)

        turns_log: List[Dict[str, Any]] = []
        turn_idx = 0
        final_scores = [0, 0]

        try:
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
                        print("⚠ Move was not accepted by platform. Re-evaluating next play...")
                        time.sleep(1.0)
                        turn_idx -= 1
                        continue

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
                    # Pass or Exchange
                    print("No viable legal move found. Passing turn...")
                    move_cmd = PlatformMove(action="PASS")
                    self.adapter.play_move(move_cmd)

                    turns_log.append({
                        "turn": turn_idx,
                        "player": 0,
                        "action_type": "PASS",
                        "rack": rack_str,
                        "timestamp": datetime.now().isoformat(),
                    })

                # Allow server to register move
                time.sleep(1.0)

        except KeyboardInterrupt:
            print("\nMatch interrupted by user.")
        except Exception as e:
            import traceback
            print(f"Exception during match execution: {e}")
            traceback.print_exc()

        # 5. Compile Final Result & Replay
        final_result = self.adapter.get_final_result()
        replay_filename = f"game_{timestamp}.json"
        replay_path = self.output_dir / replay_filename

        replay_data = {
            "metadata": {
                "platform": "woogles",
                "game_url": game_url,
                "bot_name": config.bot_name,
                "dictionary": config.dictionary,
                "time_control": config.time_control,
                "mode": self.mode,
                "value_weight": self.value_weight,
                "timestamp": timestamp,
            },
            "player_names": [final_result.get("my_name", "Alphable"), final_result.get("opponent_name", config.bot_name)],
            "final_score": [final_result.get("my_score", 0), final_result.get("opponent_score", 0)],
            "winner": final_result.get("winner", "Unknown"),
            "turns": turns_log,
        }

        with open(replay_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, indent=2)

        summary_filename = f"run_{timestamp}_summary.json"
        summary_path = self.summaries_dir / summary_filename
        summary_data = {
            "timestamp": timestamp,
            "platform": "woogles",
            "opponent": config.bot_name,
            "game_replay": str(replay_path),
            "final_score": replay_data["final_score"],
            "winner": replay_data["winner"],
            "turns_count": len(turns_log),
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        print("\n" + "=" * 65)
        print(f"MATCH COMPLETED: {summary_data['winner']} won ({summary_data['final_score'][0]} - {summary_data['final_score'][1]})")
        print(f"Replay saved to: {replay_path}")
        print(f"Summary saved to: {summary_path}")
        print("=" * 65)

        return summary_data
