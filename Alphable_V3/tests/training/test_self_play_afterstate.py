import pytest
from alphable.training.self_play import play_one_game
from alphable.core.inference import AlphableInference

def test_self_play_records_after_states():
    engine = AlphableInference(device='cpu')
    samples, scores = play_one_game(
        engine, engine,
        max_turns=6,
        reward_mode='blend',
        top_k=2
    )
    assert len(samples) > 0

    # In after-state representation:
    # When a move was played, the rack leave has <= 6 tiles.
    # Check that at least one played sample has a rack leave <= 6 tiles.
    leaves = [s for s in samples if len(s['rack']) < 7]
    assert len(leaves) > 0, "Self-play should record after-state leaves (rack len < 7) for played moves"

    # Also verify that the board in after-state samples contains tiles played
    for s in samples:
        assert len(s['board']) == 225
        assert 'target' in s
        assert -1.0 <= s['target'] <= 1.0
