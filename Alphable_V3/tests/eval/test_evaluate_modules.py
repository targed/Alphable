import os
import pytest
from unittest.mock import MagicMock, patch

from alphable.core import simulator
from alphable.eval.evaluate_vs_baseline import (
    board_to_visualizer_string,
    move_to_desc,
    choose_baseline_move,
    run_game,
)
from alphable.eval.evaluate_matches import play_match


def test_board_to_visualizer_string():
    board = simulator.create_empty_board()
    board[7][7] = "A"
    res = board_to_visualizer_string(board)
    assert " 7 " in res
    assert "A" in res
    assert len(res.splitlines()) == 15


def test_move_to_desc():
    move = {"word": "HELLO", "row": 7, "col": 7, "dir": "across"}
    desc = move_to_desc(move)
    assert desc == "Plays 'HELLO' at 7,7 across"


def test_choose_baseline_move_empty():
    board = simulator.create_empty_board()
    assert choose_baseline_move("random", [], board, ["A", "B"]) is None
    assert choose_baseline_move("greedy", [], board, ["A", "B"]) is None


def test_choose_baseline_move_random_and_greedy():
    board = simulator.create_empty_board()
    moves = [
        {"word": "AT", "row": 7, "col": 7, "dir": "across"},
        {"word": "CAT", "row": 7, "col": 7, "dir": "across"},
    ]
    rack = ["A", "T", "C", "D", "E", "F", "G"]

    # Random move
    chosen_rand = choose_baseline_move("random", moves, board, rack)
    assert chosen_rand in moves

    # Greedy move should pick the one with highest score
    chosen_greedy = choose_baseline_move("greedy", moves, board, rack)
    # simulator will score CAT higher than AT
    assert chosen_greedy["word"] == "CAT"

    # Invalid opponent
    with pytest.raises(ValueError, match="Unknown opponent type"):
        choose_baseline_move("superman", moves, board, rack)


def test_play_match_mock():
    mock_engine_a = MagicMock()
    mock_engine_b = MagicMock()

    # We can mock evaluate_moves so it plays 1 move then passes
    turn_counter = {"count": 0}

    def mock_eval(engine, board, rack, score_diff, bag_remaining, infer_batch_size=256):
        turn_counter["count"] += 1
        if turn_counter["count"] <= 2:
            new_board = [row.copy() for row in board]
            new_board[7][7] = "A"
            return [{
                "move": {"word": "A", "row": 7, "col": 7, "dir": "across"},
                "new_board": new_board,
                "points": 10,
                "new_rack": rack[1:],
                "value": 0.5,
                "equity": 20.0,
            }]
        return []

    with patch("alphable.eval.evaluate_matches.evaluate_moves", side_effect=mock_eval):
        scores = play_match(mock_engine_a, mock_engine_b, max_turns=10)
        assert len(scores) == 2
        # Endgame adjustment should have taken place
        assert isinstance(scores[0], (int, float))
        assert isinstance(scores[1], (int, float))


def test_run_game_mock(tmp_path):
    mock_engine = MagicMock()
    mock_engine.model_path = "models/test_model.pth"
    mock_searcher = MagicMock()
    mock_searcher.mode = "bc_0ply"
    mock_searcher.num_simulations = 0
    mock_searcher.top_k_candidates = 3
    mock_searcher.opp_reply_top_k = 2

    # Legal moves generation
    mock_engine.move_gen.generate.return_value = [
        {"word": "HI", "row": 7, "col": 7, "dir": "across"}
    ]

    def mock_eval(engine, board, rack, score_diff, bag_remaining, infer_batch_size=256):
        return [{
            "move": {"word": "HI", "row": 7, "col": 7, "dir": "across"},
            "points": 8,
            "value": 0.2,
            "equity": 13.0,
        }]

    with patch("alphable.eval.evaluate_vs_baseline.evaluate_moves", side_effect=mock_eval):
        game_result = run_game(
            game_idx=0,
            engine=mock_engine,
            searcher=mock_searcher,
            opponent="greedy",
            output_dir=str(tmp_path),
            timestamp="20260919_000000",
            max_turns=4,
            infer_batch_size=256,
        )
        assert game_result is not None
        assert "alphable_won" in game_result
        assert "az_score" in game_result
        assert "opp_score" in game_result
        # Verify files were created
        assert (tmp_path / "game1_20260919_000000.txt").exists()
        assert (tmp_path / "game1_20260919_000000.json").exists()

    # Also test non-bc_0ply mode (e.g. 1ply search)
    mock_searcher.mode = "1ply"
    mock_searcher.find_best_move.return_value = (
        {"word": "HI", "row": 7, "col": 7, "dir": "across"},
        0.5
    )
    with patch("alphable.eval.evaluate_vs_baseline.evaluate_moves", side_effect=mock_eval):
        game_result_1ply = run_game(
            game_idx=1,
            engine=mock_engine,
            searcher=mock_searcher,
            opponent="random",
            output_dir=str(tmp_path),
            timestamp="20260919_000000",
            max_turns=2,
            infer_batch_size=256,
        )
        assert game_result_1ply is not None
        assert (tmp_path / "game2_20260919_000000.txt").exists()


def test_evaluate_vs_baseline_missing_model():
    from alphable.eval.evaluate_vs_baseline import evaluate
    args = MagicMock()
    args.model = "non_existent_model_12345.pth"
    args.output_dir = "tmp/out"
    args.seed = 42
    args.device = "cpu"
    with pytest.raises(FileNotFoundError):
        evaluate(args)


def test_evaluate_matches_main(tmp_path):
    from alphable.eval import evaluate_matches
    with patch("alphable.eval.evaluate_matches.inference.AlphableInference"), \
         patch("alphable.eval.evaluate_matches.play_match", return_value=[350, 300]), \
         patch("sys.argv", ["evaluate_matches.py", "--model-a", "mock_a.pth", "--model-b", "mock_b.pth", "--games", "2"]):
        evaluate_matches.main()


def test_evaluate_vs_baseline_main(tmp_path):
    from alphable.eval import evaluate_vs_baseline
    with patch("alphable.eval.evaluate_vs_baseline.inference.AlphableInference"), \
         patch("alphable.eval.evaluate_vs_baseline.AlphableSearch"), \
         patch("alphable.eval.evaluate_vs_baseline.run_game", return_value={
             "alphable_won": True,
             "az_score": 350,
             "opp_score": 300,
             "summary_path": str(tmp_path / "summary.json"),
             "txt_path": str(tmp_path / "game.txt"),
             "json_path": str(tmp_path / "game.json"),
         }), \
         patch("os.path.exists", return_value=True), \
         patch("sys.argv", ["evaluate_vs_baseline.py", "--opponent", "greedy", "--games", "1", "--output-dir", str(tmp_path)]):
        evaluate_vs_baseline.main()


def test_plot_loss_history(tmp_path):
    from alphable.eval.analyze import plot_loss_history, main as analyze_main
    import json

    # 1. Non-existent file
    plot_loss_history("non_existent.json")

    # 2. Empty data
    empty_json = tmp_path / "empty.json"
    empty_json.write_text("[]")
    plot_loss_history(str(empty_json))

    # 3. Valid data
    valid_json = tmp_path / "history.json"
    data = [
        {"epoch": 1, "train_loss": 0.5, "val_loss": 0.6},
        {"epoch": 2, "train_loss": 0.4, "val_loss": 0.5},
    ]
    valid_json.write_text(json.dumps(data))
    out_png = tmp_path / "test_plot.png"
    plot_loss_history(str(valid_json), output_png=str(out_png))
    assert out_png.exists()

    # 4. analyze main
    with patch("sys.argv", ["analyze.py", "--history", str(valid_json), "--output", str(out_png)]):
        analyze_main()
