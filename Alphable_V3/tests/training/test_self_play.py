import pytest
import torch
from unittest.mock import patch
from alphable.training.self_play import choose_move_with_temperature

def test_choose_move_empty_evals():
    """Test that empty move lists return None."""
    assert choose_move_with_temperature([]) is None
    assert choose_move_with_temperature([], temperature=1.0) is None

def test_choose_move_low_temperature():
    """Test that a temperature <= 1e-6 always returns the highest value move deterministically."""
    evals = [
        {'move': 'A1', 'value': 0.8},
        {'move': 'B1', 'value': 0.5},
        {'move': 'C1', 'value': 0.1}
    ]
    # At very low temperature, it should bypass multinomial completely
    with patch('torch.multinomial') as mock_multinomial:
        result = choose_move_with_temperature(evals, temperature=1e-7, top_k=5)
        assert result == evals[0]
        mock_multinomial.assert_not_called()

def test_choose_move_zero_top_k():
    """Test that zero or negative top_k is handled safely, defaulting to at least 1."""
    evals = [
        {'move': 'A1', 'value': 0.8},
        {'move': 'B1', 'value': 0.5}
    ]
    # The max(1, min(top_k, ...)) bounds check should clamp 0 to 1
    # Thus only 1 item is considered, and it will be selected
    with patch('torch.multinomial') as mock_multinomial:
        # Since there's only 1 item, multinomial should pick idx 0
        mock_multinomial.return_value = torch.tensor([0])
        result = choose_move_with_temperature(evals, temperature=1.0, top_k=0)
        assert result == evals[0]

def test_choose_move_top_k_exceeds_length():
    """Test when top_k is greater than the number of available moves."""
    evals = [
        {'move': 'A1', 'value': 0.8},
        {'move': 'B1', 'value': 0.5}
    ]
    # top_k=10, len=2. Should just use the 2 elements.
    with patch('torch.multinomial') as mock_multinomial:
        mock_multinomial.return_value = torch.tensor([1])
        result = choose_move_with_temperature(evals, temperature=1.0, top_k=10)

        # We enforce multinomial is called on a 2-element distribution
        args, kwargs = mock_multinomial.call_args
        assert len(args[0]) == 2

        # It returned 1, so it picked 'B1'
        assert result == evals[1]

def test_choose_move_probability_distribution():
    """Test that probabilities are calculated using softmax with temperature."""
    evals = [
        {'move': 'A1', 'value': 1.0},
        {'move': 'B1', 'value': 0.0}
    ]
    temperature = 0.5

    with patch('torch.multinomial') as mock_multinomial:
        mock_multinomial.return_value = torch.tensor([0])
        choose_move_with_temperature(evals, temperature=temperature, top_k=2)

        args, kwargs = mock_multinomial.call_args
        probs = args[0]

        # Calculate expected probs manually
        logits = torch.tensor([1.0, 0.0])
        expected_probs = torch.softmax(logits / temperature, dim=0)

        # Use torch.testing.assert_close
        torch.testing.assert_close(probs, expected_probs)

def test_choose_move_deterministic_random():
    """Integration style test without mocks to ensure it works with real torch calls."""
    evals = [
        {'move': 'A1', 'value': 0.9},
        {'move': 'B1', 'value': 0.8},
        {'move': 'C1', 'value': 0.7}
    ]

    # Set seed for determinism
    torch.manual_seed(42)
    # Run multiple times to ensure we don't crash and returns are valid
    for _ in range(5):
        res = choose_move_with_temperature(evals, temperature=0.5, top_k=3)
        assert res in evals
import random
from collections import Counter
import pytest

from alphable.training.self_play import build_bag, STANDARD_TILE_COUNTS

def test_build_bag_length():
    """Test that the bag contains exactly 100 tiles."""
    bag = build_bag()
    assert len(bag) == 100, f"Expected 100 tiles, got {len(bag)}"

def test_build_bag_tile_counts():
    """Test that the bag contains the correct frequencies of each tile."""
    bag = build_bag()
    counts = Counter(bag)

    # Assert each tile in the standard distribution matches the counts in the bag
    for tile, expected_count in STANDARD_TILE_COUNTS.items():
        assert counts[tile] == expected_count, f"Expected {expected_count} for tile '{tile}', got {counts[tile]}"

    # Ensure no extra unexpected tiles were added
    assert len(counts) == len(STANDARD_TILE_COUNTS), "Bag contains unexpected tile types"

def test_build_bag_deterministic():
    """Test that the bag is generated deterministically when seeded."""
    rng1 = random.Random(42)
    bag1 = build_bag(rng=rng1)

    rng2 = random.Random(42)
    bag2 = build_bag(rng=rng2)

    assert bag1 == bag2, "Bags generated with the same seed should be identical"

    # Verify exact first 10 items for the seed 42 to detect any future behavioral changes
    expected_start = ['I', 'I', 'V', 'B', 'O', 'L', 'A', 'R', 'D', 'S']
    assert bag1[:10] == expected_start, f"Expected start {expected_start}, got {bag1[:10]}"

def test_build_bag_default_rng():
    """Test that calling build_bag without an rng argument works and uses random."""
    # Since random without seed is non-deterministic, we just ensure it builds correctly
    bag1 = build_bag()
    bag2 = build_bag()

    assert len(bag1) == 100
    assert len(bag2) == 100
    # While highly unlikely to be identical, it's not strictly impossible, but they shouldn't be the same list object
    assert bag1 is not bag2
    assert Counter(bag1) == STANDARD_TILE_COUNTS
    assert Counter(bag2) == STANDARD_TILE_COUNTS
import pytest
from alphable.training.self_play import compute_turn_temperature

def test_compute_turn_temperature_temp_end_none():
    assert compute_turn_temperature(0, 10, 1.5, None) == 1.5
    assert compute_turn_temperature(5, 10, 1.5, None) == 1.5

def test_compute_turn_temperature_max_turns_leq_one():
    assert compute_turn_temperature(0, 1, 1.5, 0.5) == 0.5
    assert compute_turn_temperature(0, 0, 1.5, 0.5) == 0.5
    assert compute_turn_temperature(0, -1, 1.5, 0.5) == 0.5

def test_compute_turn_temperature_interpolation():
    # turn_idx=0 -> alpha=0 -> temp_start
    assert compute_turn_temperature(0, 11, 1.0, 0.0) == 1.0
    # turn_idx=5 -> alpha=0.5 -> midpoint
    assert compute_turn_temperature(5, 11, 1.0, 0.0) == 0.5
    # turn_idx=10 -> alpha=1.0 -> temp_end
    assert compute_turn_temperature(10, 11, 1.0, 0.0) == 0.0

    # Another test case
    assert compute_turn_temperature(2, 5, 2.0, 1.0) == 1.5  # alpha = 2/4 = 0.5

def test_compute_turn_temperature_out_of_bounds():
    # alpha floored at 0
    assert compute_turn_temperature(-1, 11, 1.0, 0.0) == 1.0
    # alpha capped at 1
    assert compute_turn_temperature(11, 11, 1.0, 0.0) == 0.0
    assert compute_turn_temperature(100, 11, 1.0, 0.0) == 0.0
from alphable.training.self_play import draw_tiles

def test_draw_tiles_normal():
    """Test drawing fewer items than available."""
    bag = ['A', 'B', 'C', 'D', 'E']
    drawn = draw_tiles(bag, 3)
    # pop() takes from the end of the list
    assert drawn == ['E', 'D', 'C']
    assert bag == ['A', 'B']

def test_draw_tiles_exact():
    """Test drawing exactly the number of items available."""
    bag = ['A', 'B', 'C']
    drawn = draw_tiles(bag, 3)
    assert drawn == ['C', 'B', 'A']
    assert bag == []

def test_draw_tiles_more_than_available():
    """Test drawing more items than are available in the bag."""
    bag = ['A', 'B']
    drawn = draw_tiles(bag, 5)
    assert drawn == ['B', 'A']
    assert bag == []

def test_draw_tiles_zero():
    """Test drawing 0 items."""
    bag = ['A', 'B', 'C']
    drawn = draw_tiles(bag, 0)
    assert drawn == []
    assert bag == ['A', 'B', 'C']

def test_draw_tiles_negative():
    """Test drawing a negative number of items."""
    bag = ['A', 'B', 'C']
    drawn = draw_tiles(bag, -2)
    assert drawn == []
    assert bag == ['A', 'B', 'C']

def test_draw_tiles_empty_bag():
    """Test drawing from an empty bag."""
    bag = []
    drawn = draw_tiles(bag, 5)
    assert drawn == []
    assert bag == []
from alphable.training.self_play import rack_penalty

def test_rack_penalty_empty_rack():
    """Test that an empty rack results in 0 penalty."""
    assert rack_penalty([]) == 0

def test_rack_penalty_standard_letters():
    """Test standard uppercase letters."""
    # A=1, B=3, C=3 => 1 + 3 + 3 = 7
    assert rack_penalty(['A', 'B', 'C']) == 7
    # Z=10, Q=10 => 20
    assert rack_penalty(['Z', 'Q']) == 20

def test_rack_penalty_blank_tile():
    """Test that a blank tile ('?') results in 0 penalty."""
    # A=1, ?=0 => 1
    assert rack_penalty(['A', '?']) == 1

def test_rack_penalty_all_blanks():
    """Test a rack full of blank tiles."""
    assert rack_penalty(['?', '?']) == 0

def test_rack_penalty_lowercase_letters():
    """Test that lowercase letters are correctly converted and penalized."""
    # The current code uses `.upper()` to fetch values from LETTER_VALUES.
    # a=1, b=3 => 4
    assert rack_penalty(['a', 'b']) == 4

def test_rack_penalty_invalid_characters():
    """Test that invalid/unknown characters result in 0 penalty."""
    # A=1, !=0, -=0 => 1
    assert rack_penalty(['A', '!', '-']) == 1

def test_rack_penalty_mixed_case_and_symbols():
    """Test a mix of uppercase, lowercase, blanks, and symbols."""
    # Z=10, q=10, ?=0, *=0, x=8 => 28
    assert rack_penalty(['Z', 'q', '?', '*', 'x']) == 28


def test_apply_endgame_adjustments():
    from alphable.training.self_play import apply_endgame_adjustments

    # Case 1: P0 emptied rack, P1 has 'Z' (penalty 10)
    scores = [100, 100]
    racks = [[], ['Z']]
    apply_endgame_adjustments(scores, racks)
    assert scores == [110, 90]

    # Case 2: P1 emptied rack, P0 has 'Q' (penalty 10)
    scores = [100, 100]
    racks = [['Q'], []]
    apply_endgame_adjustments(scores, racks)
    assert scores == [90, 110]

    # Case 3: Both have unplayed tiles (game ended on passes)
    scores = [100, 100]
    racks = [['A'], ['B']] # A=1, B=3
    apply_endgame_adjustments(scores, racks)
    assert scores == [99, 97]


def test_compute_player_target():
    from alphable.training.self_play import compute_player_target

    # Outcome mode
    assert compute_player_target(0, [100, 50], reward_mode='outcome') == 1.0
    assert compute_player_target(0, [50, 100], reward_mode='outcome') == -1.0
    assert compute_player_target(0, [100, 100], reward_mode='outcome') == 0.0

    # Margin mode
    m_target = compute_player_target(0, [100, 50], reward_mode='margin', margin_scale=100.0)
    assert 0.0 < m_target < 1.0

    # Blend mode
    b_target = compute_player_target(0, [100, 50], reward_mode='blend', margin_scale=100.0, margin_mix=0.5)
    assert 0.0 < b_target <= 1.0


def test_compute_turn_temperature():
    from alphable.training.self_play import compute_turn_temperature
    assert compute_turn_temperature(0, 10, 0.5, None) == 0.5
    assert compute_turn_temperature(0, 1, 0.5, 0.1) == 0.1
    assert compute_turn_temperature(0, 10, 0.5, 0.1) == 0.5
    assert compute_turn_temperature(9, 10, 0.5, 0.1) == pytest.approx(0.1)


def test_choose_greedy_move():
    from unittest.mock import MagicMock
    from alphable.training.self_play import choose_greedy_move
    from alphable.core import simulator

    board = simulator.create_empty_board()
    rack = ['C', 'A', 'T']
    mock_gen = MagicMock()
    # No moves
    mock_gen.generate.return_value = []
    assert choose_greedy_move(board, rack, mock_gen) is None

    # With moves
    mock_gen.generate.return_value = [
        {'word': 'AT', 'row': 7, 'col': 7, 'dir': 'across'},
        {'word': 'CAT', 'row': 7, 'col': 7, 'dir': 'across'},
    ]
    move = choose_greedy_move(board, rack, mock_gen)
    assert move is not None
    assert move['move']['word'] == 'CAT'


def test_play_one_game_mock():
    from unittest.mock import MagicMock
    from alphable.training.self_play import play_one_game
    mock_engine = MagicMock()
    mock_engine.device = 'cpu'
    # Return empty moves so it ends quickly via consecutive passes
    mock_engine.move_gen.generate.return_value = []

    samples, scores = play_one_game(
        mock_engine,
        mock_engine,
        max_turns=4,
    )
    assert isinstance(samples, list)
    assert len(scores) == 2
    assert isinstance(scores[0], (int, float))
    assert isinstance(scores[1], (int, float))


def test_self_play_main_single_worker(tmp_path):
    from alphable.training import self_play
    from unittest.mock import patch, MagicMock

    out_file = tmp_path / "selfplay.jsonl"
    dict_file = tmp_path / "dict.txt"
    dict_file.write_text("HELLO\n")

    mock_engine = MagicMock()
    mock_engine.device = "cpu"
    mock_engine.move_gen.generate.return_value = []

    with patch("alphable.core.inference.AlphableInference", return_value=mock_engine), \
         patch("sys.argv", [
             "self_play.py",
             "--output", str(out_file),
             "--games", "1",
             "--workers", "1",
             "--dict", str(dict_file),
             "--device", "cpu",
             "--max-turns", "2",
         ]):
        self_play.main()

    assert out_file.exists()
