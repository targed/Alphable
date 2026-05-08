import sys
import os
import unittest
from unittest.mock import MagicMock

# Mock torch before importing anything that might use it
sys.modules['torch'] = MagicMock()
sys.modules['torch.multiprocessing'] = MagicMock()

# Add current directory to path
sys.path.append(os.path.abspath('Alphable_V2'))

import simulator

class TestGreedyOptimization(unittest.TestCase):
    def setUp(self):
        self.board = simulator.create_empty_board()
        self.rack = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

    def test_basic_scoring(self):
        move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'CAB'}
        # C=3, A=1, B=3 -> 7 points. Center square is DW -> 14 points.
        points = simulator._calculate_move_points(self.board, move, {'C':1, 'A':1, 'B':1})
        self.assertEqual(points, 14)

        # Test consistency with simulate_move
        _, sim_points, _ = simulator.simulate_move(self.board, move, ['C', 'A', 'B'])
        self.assertEqual(points, sim_points)

    def test_bingo_scoring(self):
        move = {'row': 7, 'col': 4, 'dir': 'Across', 'word': 'CABINET'}
        # C=3, A=1, B=3, I=1, N=1, E=1, T=1 -> 11 points
        # Premiums: (7,7)=DW -> word multiplier 2
        # 11 * 2 + 50 = 72
        points = simulator._calculate_move_points(self.board, move, {'C':1, 'A':1, 'B':1, 'I':1, 'N':1, 'E':1, 'T':1})
        self.assertEqual(points, 72)

        _, sim_points, _ = simulator.simulate_move(self.board, move, ['C', 'A', 'B', 'I', 'N', 'E', 'T'])
        self.assertEqual(points, sim_points)

    def test_blank_scoring(self):
        # Using a blank for 'C'
        move = {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'CAB'}
        # blank=0, A=1, B=3 -> 4 points. Center square DW -> 8 points.
        points = simulator._calculate_move_points(self.board, move, {'?':1, 'A':1, 'B':1})
        self.assertEqual(points, 8)

        _, sim_points, _ = simulator.simulate_move(self.board, move, ['?', 'A', 'B'])
        self.assertEqual(points, sim_points)

    def test_find_best_greedy_move(self):
        moves = [
            {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'CAB'}, # 14 points
            {'row': 7, 'col': 7, 'dir': 'Across', 'word': 'BEAD'} # B=3, E=1, A=1, D=2 -> 7 * 2 = 14 points
        ]
        best_move = simulator.find_best_greedy_move(self.board, moves, ['C', 'A', 'B', 'E', 'D'])
        self.assertIn(best_move, moves)

        # Add a higher scoring move
        higher_move = {'row': 7, 'col': 4, 'dir': 'Across', 'word': 'CABINET'} # 94 points
        moves.append(higher_move)
        best_move = simulator.find_best_greedy_move(self.board, moves, ['C', 'A', 'B', 'I', 'N', 'E', 'T'])
        self.assertEqual(best_move, higher_move)

    def test_return_simulation(self):
        moves = [{'row': 7, 'col': 7, 'dir': 'Across', 'word': 'CAB'}]
        result = simulator.find_best_greedy_move(self.board, moves, ['C', 'A', 'B'], return_simulation=True)
        self.assertEqual(result['move'], moves[0])
        self.assertEqual(result['points'], 14)
        self.assertEqual(result['new_board'][7][7], 'C')
        self.assertEqual(result['new_rack'], [])

if __name__ == '__main__':
    unittest.main()
