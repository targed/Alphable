import pytest
from alphable.training.self_play import evaluate_moves, choose_move_with_temperature
from alphable.core.inference import AlphableInference
from alphable.core import simulator

def test_evaluate_moves_calculates_equity():
    engine = AlphableInference(device='cpu')
    board = simulator.create_empty_board()
    rack = ['C', 'A', 'B', 'I', 'N', 'E', 'T']
    evals = evaluate_moves(engine, board, rack, score_diff=0, bag_remaining=86)
    assert len(evals) > 0

    top = evals[0]
    assert 'points' in top
    assert 'value' in top
    assert 'equity' in top

    # Every item must have equity = points + leave_equity + engine.value_weight * value
    from alphable.core.leave_eval import compute_leave_equity
    for item in evals:
        leave_eq = compute_leave_equity(item['new_rack'], bag_remaining=86)
        expected_equity = item['points'] + leave_eq + engine.value_weight * item['value']
        assert abs(item['equity'] - expected_equity) < 1e-3

    # Test with custom value_weight
    custom_evals = evaluate_moves(engine, board, rack, score_diff=0, bag_remaining=86, value_weight=75.0)
    for item in custom_evals:
        leave_eq = compute_leave_equity(item['new_rack'], bag_remaining=86)
        expected_equity = item['points'] + leave_eq + 75.0 * item['value']
        assert abs(item['equity'] - expected_equity) < 1e-3

    # Must be sorted by equity descending
    for i in range(len(evals) - 1):
        assert evals[i]['equity'] >= evals[i+1]['equity']

def test_choose_move_with_temperature_uses_equity():
    evals = [
        {'move': {'word': 'A'}, 'equity': 50.0, 'points': 45, 'value': 0.2},
        {'move': {'word': 'B'}, 'equity': 20.0, 'points': 15, 'value': 0.2},
    ]
    # At low temperature, should pick the highest equity move
    chosen = choose_move_with_temperature(evals, temperature=1e-6)
    assert chosen['move']['word'] == 'A'
