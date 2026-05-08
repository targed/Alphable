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
