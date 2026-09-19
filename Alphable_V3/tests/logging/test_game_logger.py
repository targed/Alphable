import os
import json
import pytest
from alphable.logging.game_logger import GameLogger, MoveEntry


def test_move_entry():
    entry = MoveEntry(
        turn_index=0,
        player=0,
        action_type="PLAY",
        action_id=1,
        word="TESTING",
        position=(7, 7),
        direction="across",
        score=72.0,
        rack_before=["T", "E", "S", "T", "I", "N", "G"],
        rack_after=["A", "B", "C", "D", "E", "F", "G"],
        board_state="mock_board",
        tiles_in_bag=86,
        consecutive_passes=0,
        additional_info={"eval_score": 15.5}
    )
    assert entry.turn_index == 0
    assert entry.player == 0
    assert entry.action_type == "PLAY"
    assert entry.word == "TESTING"
    assert entry.score == 72.0
    assert entry.position == (7, 7)
    assert entry.additional_info["eval_score"] == 15.5


def test_game_logger_workflow(tmp_path):
    logger = GameLogger(player0_name="Alphable", player1_name="Opponent")
    logger.set_metadata(
        agent_type="Alphable_V3",
        model_path="models/test_model.pth",
        lexicon="CSW24",
    )

    # Log moves
    logger.log_move(MoveEntry(
        turn_index=0,
        player=0,
        action_type="PLAY",
        action_id=1,
        word="RETINAS",  # 7-letter bingo
        position=(7, 7),
        direction="across",
        score=74.0,
        rack_before=["R", "E", "T", "I", "N", "A", "S"],
        rack_after=["A", "B", "C", "D", "E", "F", "G"],
        tiles_in_bag=86,
        consecutive_passes=0,
        additional_info={"eval_score": 20.0}
    ))

    logger.log_move(MoveEntry(
        turn_index=1,
        player=1,
        action_type="EXCHANGE",
        action_id=2,
        score=0.0,
        tiles_in_bag=86,
        consecutive_passes=0,
        additional_info={"exchanged_tiles": "QQQ"}
    ))

    logger.log_move(MoveEntry(
        turn_index=2,
        player=0,
        action_type="PASS",
        action_id=3,
        score=0.0,
        tiles_in_bag=86,
        consecutive_passes=1
    ))

    logger.set_final_score([74.0, 0.0])

    # Check stats
    stats = logger.get_statistics()
    assert stats["total_turns"] == 3
    p0_stats = stats["player_stats"][0]
    p1_stats = stats["player_stats"][1]

    assert p0_stats["total_moves"] == 2
    assert p0_stats["plays"] == 1
    assert p0_stats["passes"] == 1
    assert p0_stats["bingos"] == 1
    assert p0_stats["total_score"] == 74.0
    assert p0_stats["highest_scoring_move"] == 74.0

    assert p1_stats["total_moves"] == 1
    assert p1_stats["exchanges"] == 1
    assert p1_stats["total_score"] == 0.0

    # Test export to dict
    d = logger.to_dict()
    assert d["player_names"] == ["Alphable", "Opponent"]
    assert d["final_score"] == [74.0, 0.0]
    assert d["metadata"]["agent_type"] == "Alphable_V3"
    assert len(d["turns"]) == 3

    # Test file saving
    save_path = tmp_path / "game_test.json"
    logger.save_json(str(save_path))
    assert save_path.exists()
    with open(save_path, "r") as f:
        saved_data = json.load(f)
    assert saved_data["metadata"]["lexicon"] == "CSW24"
    assert len(saved_data["turns"]) == 3

    # Test empty game stats
    empty_logger = GameLogger()
    empty_stats = empty_logger.get_statistics()
    assert empty_stats["total_turns"] == 0
    assert empty_stats["player_stats"][0]["average_score_per_move"] == 0
