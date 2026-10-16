"""
Unit tests for SmolLM2CandidateRanker.
"""

import pytest
import torch
from alphable.models.transformer_ranker import (
    SmolLM2CandidateRanker,
    coords_to_str,
    CANDIDATE_LABELS,
)
from alphable.core import simulator


def test_coords_to_str():
    assert coords_to_str(7, 6, "Across") == "8G"
    assert coords_to_str(7, 6, "down") == "G8"
    assert coords_to_str(11, 7, "Down") == "H12"
    assert coords_to_str(0, 0, "Across") == "1A"


def test_format_candidate_str():
    board = simulator.create_empty_board()
    rack = ["C", "A", "R", "E", "S", "T", "O"]

    # Initialize ranker on CPU or CUDA (we can test helper directly)
    ranker = SmolLM2CandidateRanker.__new__(SmolLM2CandidateRanker)

    # 1. Normal move
    m1 = {"row": 7, "col": 7, "dir": "Across", "word": "CARE"}
    cand_str1 = ranker.format_candidate_str(board, rack, m1, score_diff=0, bag_remaining=86)
    assert "8H CARE" in cand_str1
    assert "pts" in cand_str1
    assert "leave:" in cand_str1

    # 2. Exchange move
    m_ex = {"is_exchange": True, "tiles": ["A", "E"]}
    cand_str_ex = ranker.format_candidate_str(board, rack, m_ex, score_diff=0, bag_remaining=86)
    assert "EXCHANGE(A,E)" in cand_str_ex
    assert "0 pts" in cand_str_ex

    # 3. Pass move
    m_pass = {"is_pass": True}
    cand_str_pass = ranker.format_candidate_str(board, rack, m_pass, score_diff=0, bag_remaining=86)
    assert "PASS" in cand_str_pass


def test_format_prompt():
    board = simulator.create_empty_board()
    rack = ["A", "E", "I", "I", "O", "U", "?"]
    candidates = [
        {"row": 7, "col": 7, "dir": "Across", "word": "EUOI"},
        {"is_exchange": True, "tiles": ["A", "E", "I", "I", "O", "U"]},
        {"is_pass": True},
    ]

    ranker = SmolLM2CandidateRanker.__new__(SmolLM2CandidateRanker)
    ranker.max_candidates = 26

    prompt, active_labels = ranker.format_prompt(
        board, rack, score_diff=14, bag_remaining=72, candidates=candidates
    )

    assert "<|im_start|>system" in prompt
    assert "Score Margin: +14 | Bag: 72 tiles remaining" in prompt
    assert "Hand Rack: [?AEIIOU]" in prompt
    assert "[A] 8H EUOI" in prompt
    assert "[B] EXCHANGE(A,E,I,I,O,U)" in prompt
    assert "[C] PASS" in prompt
    assert prompt.endswith("Best Move: [")
    assert active_labels == ["A", "B", "C"]


@pytest.fixture(scope="module")
def ranker_instance():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SmolLM2CandidateRanker(device=device)


def test_rank_candidates_live(ranker_instance):
    board = simulator.create_empty_board()
    rack = ["R", "E", "T", "I", "N", "A", "S"]
    candidates = [
        {"row": 7, "col": 4, "dir": "Across", "word": "RETINAS"},
        {"row": 7, "col": 6, "dir": "Across", "word": "AT"},
        {"is_exchange": True, "tiles": ["R", "E"]},
        {"is_pass": True},
    ]

    ranked = ranker_instance.rank_candidates(
        board, rack, score_diff=0, bag_remaining=86, candidates=candidates
    )

    assert len(ranked) == 4
    # Probabilities should sum to approximately 1.0
    total_prob = sum(item[1] for item in ranked)
    assert abs(total_prob - 1.0) < 1e-4

    # Ranking should be sorted descending by probability
    probs = [item[1] for item in ranked]
    assert probs == sorted(probs, reverse=True)

    # select_best_move should return the first candidate
    best_move = ranker_instance.select_best_move(
        board, rack, score_diff=0, bag_remaining=86, candidates=candidates
    )
    assert best_move == ranked[0][0]


def test_empty_candidates(ranker_instance):
    board = simulator.create_empty_board()
    rack = ["A", "B", "C"]
    assert ranker_instance.rank_candidates(board, rack, candidates=[]) == []
    assert ranker_instance.select_best_move(board, rack, candidates=[]) is None
