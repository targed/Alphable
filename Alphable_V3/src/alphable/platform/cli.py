"""
CLI interface for playing Alphable on online platforms.
Supports 'alphable play woogles' with rich configuration.
"""

import argparse
import os
import sys

from alphable.platform.base import PlatformGameConfig
from alphable.platform.runner import OnlineGameRunner
from alphable.platform.woogles.adapter import WooglesAdapter


def parse_args():
    parser = argparse.ArgumentParser(
        prog="alphable play woogles",
        description="Play live Scrabble on Woogles.io using Alphable AI.",
    )
    parser.add_argument(
        "--bot",
        type=str,
        default="HastyBot",
        help="Opponent bot name on Woogles (e.g. HastyBot, BestBot, BeginnerBot).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/alphable_v3_rl_gen2.pth",
        help="Path to neural network checkpoint to use.",
    )
    parser.add_argument(
        "--dict",
        type=str,
        default="resources/CSW24.txt",
        help="Lexicon dictionary path (e.g. resources/CSW24.txt).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="lookahead",
        choices=["lookahead", "bc_0ply"],
        help="Search mode: 'lookahead' (1-ply Monte Carlo) or 'bc_0ply' (direct evaluation).",
    )
    parser.add_argument(
        "--value-weight",
        type=float,
        default=60.0,
        help="Weight multiplier W applied to strategic leave values.",
    )
    parser.add_argument(
        "--time-control",
        type=str,
        default="15+0",
        help="Time control for match (e.g. 15+0, 5+0).",
    )
    parser.add_argument(
        "--game-mode",
        type=str,
        default="realtime",
        choices=["realtime", "correspondence"],
        help="Game mode: 'realtime' or 'correspondence'.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in background without visible window (default is headed).",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=2.0,
        help="Minimum thinking/pacing delay in seconds before submitting move.",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=6.0,
        help="Maximum thinking/pacing delay in seconds before submitting move.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/woogles/games",
        help="Directory to save game replays.",
    )
    parser.add_argument(
        "--profile-dir",
        type=str,
        default=os.path.expanduser("~/.alphable/woogles_profile"),
        help="Directory for persistent browser context.",
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=16,
        help="Number of opponent leave simulations per candidate in lookahead mode.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of candidate moves evaluated in lookahead search.",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        default=True,
        help="Keep browser window open after match completion (default: True).",
    )
    parser.add_argument(
        "--no-keep-open",
        dest="keep_open",
        action="store_false",
        help="Close browser immediately upon completion.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    adapter = WooglesAdapter()
    try:
        print(f"Launching browser (headless={args.headless}, profile={args.profile_dir})...")
        adapter.start(headless=args.headless, user_data_dir=args.profile_dir)
        user = adapter.ensure_logged_in()
        print(f"Logged in / Session established as: {user}")

        runner = OnlineGameRunner(
            adapter=adapter,
            model_path=args.model,
            dict_path=args.dict,
            mode=args.mode,
            value_weight=args.value_weight,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            output_dir=args.output_dir,
            num_simulations=args.simulations,
            top_k=args.top_k,
        )

        config = PlatformGameConfig(
            opponent_type="bot",
            bot_name=args.bot,
            dictionary="CSW24" if "CSW" in args.dict.upper() else "NWL23",
            game_mode=args.game_mode,
            time_control=args.time_control,
            rated=False,
        )

        runner.play_match(config)

        if args.keep_open and not args.headless:
            print("\nMatch session completed. Press Enter to close browser window...")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass

    finally:
        adapter.close()


if __name__ == "__main__":
    main()
