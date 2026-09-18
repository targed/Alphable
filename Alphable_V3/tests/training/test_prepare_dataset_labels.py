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
