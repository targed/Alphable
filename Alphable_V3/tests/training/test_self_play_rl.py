import pytest
import torch
from alphable.training.self_play_rl import SelfPlayTrajectory, SelfPlayRLTrainer


def test_self_play_trajectory_target_assignment():
    traj = SelfPlayTrajectory()
    # Turn 0 (Player 0)
    traj.record_turn(player=0, board_str="." * 225, rack=['A', 'B'], score_diff=0, bag_count=80)
    # Turn 1 (Player 1)
    traj.record_turn(player=1, board_str="." * 225, rack=['C', 'D'], score_diff=0, bag_count=78)

    # Player 0 wins 420 - 380 (+40 pts margin)
    samples = traj.finalize(scores=(420, 380), margin_scale=100.0)
    assert len(samples) == 2

    # Player 0 sample must have positive target
    assert samples[0]['target'] > 0.0
    # Player 1 sample must have negative target
    assert samples[1]['target'] < 0.0
    # Targets should be antisymmetric (sum to ~0)
    assert abs(samples[0]['target'] + samples[1]['target']) < 1e-4


def test_self_play_trajectory_draw_assignment():
    traj = SelfPlayTrajectory()
    traj.record_turn(player=0, board_str="." * 225, rack=['A'], score_diff=0, bag_count=50)
    traj.record_turn(player=1, board_str="." * 225, rack=['B'], score_diff=0, bag_count=50)

    # Draw 400 - 400
    samples = traj.finalize(scores=(400, 400), margin_scale=100.0)
    assert len(samples) == 2
    assert samples[0]['target'] == 0.0
    assert samples[1]['target'] == 0.0


def test_self_play_trainer_train_step(tmp_path):
    trainer = SelfPlayRLTrainer(
        model_path=None,
        state_vector_size=63,
        device='cpu',
    )
    # Generate mock dataset
    samples = [
        {
            'board_str': "." * 225,
            'rack': ['A', 'E', 'R', 'S'],
            'score_diff': 15,
            'bag_count': 60,
            'unseen_counts': {'A': 5, 'E': 6},
            'target': 0.5,
        },
        {
            'board_str': "." * 225,
            'rack': ['Q', 'V', 'Z', 'W'],
            'score_diff': -30,
            'bag_count': 30,
            'unseen_counts': {'A': 1, 'E': 1},
            'target': -0.7,
        },
    ] * 8

    initial_loss = trainer.evaluate_loss(samples)
    assert initial_loss >= 0.0

    # Train for 2 epochs
    trained_loss = trainer.train_epoch(samples, batch_size=4, lr=1e-3)
    assert trained_loss is not None


def test_self_play_trainer_generate_games():
    import os
    dict_path = 'resources/CSW24.txt' if os.path.exists('resources/CSW24.txt') else 'resources/NWL2023.txt'
    trainer = SelfPlayRLTrainer(model_path=None, state_vector_size=63, device='cpu')
    samples = trainer.generate_games(num_games=1, dict_path=dict_path, temp=0.5, top_k=2)
    assert len(samples) > 0
    # Every sample has target in [-1, 1]
    for s in samples:
        assert -1.0 <= s['target'] <= 1.0

