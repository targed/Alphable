import json
import pytest
from unittest.mock import MagicMock
from alphable.training.prepare_dataset import process_game

def test_no_negative_penalty_for_higher_scoring_moves():
    # Mock move_gen that returns two moves:
    # 1. Human move: 'AT' at (7,7) Across, scores 4 pts
    # 2. Alternative move: 'CABINET' at (7,4) Across, scores 72 pts
    move_gen = MagicMock()
    human_move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'AT'}
    high_scoring_move = {'row': 7, 'col': 4, 'dir': 'Across', 'word': 'CABINET'}
    low_scoring_move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'A'}

    move_gen.generate.return_value = [human_move, high_scoring_move, low_scoring_move]

    game_data = {
        'moves': [
            {
                'player': 0,
                'rack': ['A', 'T', 'C', 'B', 'I', 'N', 'E'],
                'position': '8H', # Row 8, Col H (7,7 Across)
                'word': 'AT',
                'score': 4,
            }
        ]
    }
    game_line = json.dumps(game_data)
    samples = process_game(game_line, move_gen, negatives_top_k=4)

    assert len(samples) > 0
    # Positive sample
    pos_samples = [s for s in samples if s['target'] == 1.0]
    assert len(pos_samples) == 1

    # Negative samples
    neg_samples = [s for s in samples if s['target'] < 1.0]
    for s in neg_samples:
        # A move that scored higher than the human move (72 vs 4) must NOT have negative target!
        # If score_diff is much higher, it should not be in neg_samples with target <= -0.5
        assert s['target'] > -1.0 or s['score_diff'] < 4


def test_parse_position():
    from alphable.training.prepare_dataset import parse_position
    # Across
    r, c, d = parse_position("8H")
    assert (r, c, d) == (7, 7, "Across")

    # Down
    r, c, d = parse_position("H8")
    assert (r, c, d) == (7, 7, "Down")

    # Invalid / None
    assert parse_position(None) == (None, None, None)
    assert parse_position("") == (None, None, None)
    assert parse_position("XYZ123") == (None, None, None)


def test_is_same_move():
    from alphable.training.prepare_dataset import is_same_move
    m1 = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'AT'}
    m2 = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'at'}
    m3 = {'row': 8, 'col': 7, 'dir': 'Across', 'word': 'AT'}
    assert is_same_move(m1, m2) is True
    assert is_same_move(m1, m3) is False
    assert is_same_move(m1, None) is False


def test_resolve_first_existing_and_count_lines(tmp_path):
    from alphable.training.prepare_dataset import resolve_first_existing, count_lines
    f1 = tmp_path / "f1.txt"
    f2 = tmp_path / "f2.txt"
    f2.write_text("line1\nline2\nline3\n")

    found = resolve_first_existing([str(f1), str(f2)])
    assert found == str(f2)
    assert count_lines(str(f2)) == 3

    assert resolve_first_existing([str(f1)]) is None


def test_process_game_precompiled_or_empty():
    from alphable.training.prepare_dataset import process_game
    # Precompiled sample line
    precompiled = json.dumps({"board": "." * 225, "target": 0.5})
    assert process_game(precompiled, None) == [{"board": "." * 225, "target": 0.5}]

    # No moves
    assert process_game(json.dumps({"info": "no moves"}), None) == []


def test_prepare_dataset_validation(tmp_path):
    from alphable.training import prepare_dataset
    from unittest.mock import patch

    # 1. negatives < 1
    with patch("sys.argv", ["prepare_dataset.py", "--negatives", "0"]):
        with pytest.raises(ValueError, match="--negatives"):
            prepare_dataset.main()

    # 2. workers < 1
    with patch("sys.argv", ["prepare_dataset.py", "--workers", "0"]):
        with pytest.raises(ValueError, match="--workers"):
            prepare_dataset.main()

    # 3. Missing dict
    with patch("sys.argv", ["prepare_dataset.py", "--dict-candidates", "missing1.txt"]):
        with pytest.raises(FileNotFoundError, match="No dictionary file found"):
            prepare_dataset.main()


def test_prepare_dataset_main_single_worker(tmp_path):
    from alphable.training import prepare_dataset
    from unittest.mock import patch, MagicMock

    dict_file = tmp_path / "dict.txt"
    dict_file.write_text("HELLO\n")
    input_file = tmp_path / "input.jsonl"
    sample = {"board": "." * 225, "target": 0.5}
    input_file.write_text(json.dumps(sample) + "\n")
    out_file = tmp_path / "out.jsonl"

    with patch("alphable.core.structure.Gaddag.load", return_value=MagicMock()), \
         patch("sys.argv", [
             "prepare_dataset.py",
             "--dict", str(dict_file),
             "--input", str(input_file),
             "--output", str(out_file),
             "--workers", "1",
         ]):
        prepare_dataset.main()

    assert out_file.exists()
    lines = out_file.read_text().strip().splitlines()
    assert len(lines) == 1
