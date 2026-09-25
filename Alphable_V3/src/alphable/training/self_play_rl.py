"""
Pure Outcome-Driven Self-Play Reinforcement Learning Pipeline for Alphable.

Replaces imitation learning on external bots with true AlphaZero-style self-play.
Supervises value network predictions directly with the actual end-of-game victory margin
z = tanh((score_player - score_opponent) / margin_scale).
This removes the imitation ceiling, allowing Alphable to discover strategies that exceed
the bots it trains against.
"""

from typing import List, Dict, Tuple, Optional
import copy
import math
import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
from alphable.core.alphable_net import AlphableValueNet, load_checkpoint_compatible
from alphable.core import inference


class SelfPlayTrajectory:
    """
    Stores moves and board states throughout an entire self-play match,
    and assigns terminal reward targets upon game conclusion.
    """
    def __init__(self):
        self.turns: List[Dict] = []

    def record_turn(
        self,
        player: int,
        board_str: str,
        rack: List[str],
        score_diff: int,
        bag_count: int,
        unseen_counts: Optional[Dict[str, int]] = None,
    ):
        """Records a single turn's decision state."""
        self.turns.append({
            'player': int(player),
            'board_str': board_str,
            'rack': list(rack),
            'score_diff': score_diff,
            'bag_count': bag_count,
            'unseen_counts': copy.deepcopy(unseen_counts) if unseen_counts else None,
        })

    def finalize(self, scores: Tuple[int, int], margin_scale: float = 100.0) -> List[Dict]:
        """
        Assigns terminal game outcome targets to all recorded turns.

        Args:
            scores: (score_player0, score_player1).
            margin_scale: Scaling factor for tanh normalized margin.

        Returns:
            List of sample dicts with 'target' in [-1.0, 1.0].
        """
        samples = []
        for t in self.turns:
            p = t['player']
            opp_p = 1 - p
            margin = float(scores[p] - scores[opp_p])
            target = math.tanh(margin / margin_scale)
            sample = dict(t)
            sample['target'] = target
            samples.append(sample)
        return samples


class SelfPlayRLTrainer:
    """
    Trains Alphable's Value Network directly from self-play outcome targets.
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        state_vector_size: int = 63,
        device: str = 'cpu',
        lr: float = 5e-4,
        weight_decay: float = 1e-4,
    ):
        self.device = torch.device(device)
        self.state_vector_size = state_vector_size
        self.model = AlphableValueNet(state_vector_size=state_vector_size).to(self.device)

        if model_path and os.path.exists(model_path):
            load_checkpoint_compatible(self.model, model_path, self.device)

        self.criterion = nn.MSELoss()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)

    def _board_from_str(self, board_str: str) -> List[List[str]]:
        """Converts a 225-character compact string into a 15x15 board."""
        return [list(board_str[r * 15:(r + 1) * 15]) for r in range(15)]

    def _samples_to_tensors(self, samples: List[Dict]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Converts a batch of sample dicts into PyTorch training tensors."""
        boards = []
        states = []
        targets = []

        for s in samples:
            b_matrix = self._board_from_str(s['board_str'])
            b_tensor = inference.board_to_tensor(b_matrix)
            s_tensor = inference.state_to_tensor(
                rack=s['rack'],
                score_diff=s['score_diff'],
                bag_remaining=s['bag_count'],
                unseen_counts=s.get('unseen_counts'),
                state_vector_size=self.state_vector_size,
            )
            boards.append(b_tensor)
            states.append(s_tensor)
            targets.append(float(s['target']))

        boards_t = torch.stack(boards).to(self.device)
        states_t = torch.stack(states).to(self.device)
        targets_t = torch.tensor(targets, dtype=torch.float32).unsqueeze(1).to(self.device)
        return boards_t, states_t, targets_t

    def evaluate_loss(self, samples: List[Dict], batch_size: int = 64) -> float:
        """Evaluates MSE loss on a set of self-play outcome samples."""
        if not samples:
            return 0.0

        self.model.eval()
        total_loss = 0.0
        batches = 0

        with torch.no_grad():
            for i in range(0, len(samples), batch_size):
                chunk = samples[i:i + batch_size]
                boards, states, targets = self._samples_to_tensors(chunk)
                preds = self.model(boards, states)
                loss = self.criterion(preds, targets)
                total_loss += loss.item()
                batches += 1

        return total_loss / max(1, batches)

    def train_epoch(self, samples: List[Dict], batch_size: int = 64, lr: Optional[float] = None) -> float:
        """Runs one training epoch over self-play outcome samples."""
        if not samples:
            return 0.0

        if lr is not None:
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = lr

        self.model.train()
        shuffled = list(samples)
        random.shuffle(shuffled)

        total_loss = 0.0
        batches = 0

        for i in range(0, len(shuffled), batch_size):
            chunk = shuffled[i:i + batch_size]
            boards, states, targets = self._samples_to_tensors(chunk)

            self.optimizer.zero_grad()
            preds = self.model(boards, states)
            loss = self.criterion(preds, targets)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            batches += 1

        return total_loss / max(1, batches)

    def save_model(self, save_path: str):
        """Saves current model weights to disk."""
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
        torch.save(self.model.state_dict(), save_path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pure outcome-driven self-play RL training")
    parser.add_argument('--model', type=str, default=None, help='Model checkpoint to load')
    parser.add_argument('--save-model', type=str, default='models/alphable_v3_rl_selfplay.pth')
    parser.add_argument('--state-size', type=int, default=63)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=5e-4)
    parser.add_argument('--epochs', type=int, default=10)
    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    trainer = SelfPlayRLTrainer(
        model_path=args.model,
        state_vector_size=args.state_size,
        device=device,
        lr=args.lr,
    )
    print(f"Initialized SelfPlayRLTrainer on {device} with state_vector_size={args.state_size}")


if __name__ == '__main__':
    main()
