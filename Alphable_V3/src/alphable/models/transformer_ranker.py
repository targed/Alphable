"""
SmolLM2-135M Transformer Candidate Ranker for Alphable Scrabble.

Reranks GADDAG-generated candidate moves (including word placements,
blank tile assignments, tile exchanges, and passes) using an attention-based
causal language model head over candidate index tokens.
"""

import os
from typing import List, Dict, Tuple, Optional, Any, Union
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForCausalLM

from alphable.core import simulator, leave_eval, defense


CANDIDATE_LABELS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z"
]


def coords_to_str(row: int, col: int, direction: str) -> str:
    """Formats 0-indexed coordinates into standard Scrabble notation (e.g. 8G or H12)."""
    col_letter = chr(ord('A') + col)
    row_num = row + 1
    if direction.lower() in ("down", "d"):
        return f"{col_letter}{row_num}"
    else:
        return f"{row_num}{col_letter}"


class SmolLM2CandidateRanker:
    """
    Reranks candidate Scrabble moves using a pre-trained or fine-tuned
    SmolLM2-135M causal transformer.
    """

    def __init__(
        self,
        model_name_or_path: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
        device: Optional[str] = None,
        max_candidates: int = 26,
    ):
        """
        Initializes the candidate ranker.

        Args:
            model_name_or_path: Hugging Face model identifier or local directory.
            device: 'cuda' or 'cpu'. If None, auto-detected.
            max_candidates: Maximum number of candidate moves to evaluate per turn (default 26 for A-Z).
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.max_candidates = min(max_candidates, len(CANDIDATE_LABELS))
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)

        # On Blackwell architecture (RTX 50-series), disable cuDNN SDPA and use eager attention
        if self.device == "cuda":
            torch.backends.cudnn.enabled = False
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path,
                dtype=torch.bfloat16,
                device_map="cuda",
                attn_implementation="eager",
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path,
                dtype=torch.float32,
                device_map="cpu",
            )

        self.model.eval()

        # Precompute token IDs for candidate labels 'A' through 'Z'
        self.label_token_ids = [
            self.tokenizer.convert_tokens_to_ids(label)
            for label in CANDIDATE_LABELS[:self.max_candidates]
        ]

    def format_candidate_str(
        self,
        board: List[List[str]],
        rack: List[str],
        move: Dict[str, Any],
        score_diff: int,
        bag_remaining: int,
    ) -> str:
        """Formats a single candidate move dictionary into a clean informative string."""
        if move.get("is_pass", False):
            return "PASS (0 pts, leave unchanged)"

        if move.get("is_exchange", False):
            ex_tiles = move.get("tiles", [])
            leave_tiles = [t for t in rack]
            for t in ex_tiles:
                if t in leave_tiles:
                    leave_tiles.remove(t)
            l_eq = leave_eval.compute_leave_equity(leave_tiles, bag_remaining)
            return f"EXCHANGE({','.join(ex_tiles)}) (0 pts, leave: [{''.join(leave_tiles)}], eq: {l_eq:+.1f})"

        # Regular board placement
        new_board, pts, new_rack = simulator.simulate_move(board, move, rack)
        coords = coords_to_str(move["row"], move["col"], move["dir"])
        word = move["word"]
        l_eq = leave_eval.compute_leave_equity(new_rack, bag_remaining)
        def_adj = defense.compute_board_defense_adjustment(board, new_board, move, score_diff)
        is_bingo = " [BINGO!]" if (len(rack) - len(new_rack) == 7) else ""

        return (
            f"{coords} {word} (+{pts} pts{is_bingo}, "
            f"leave: [{''.join(new_rack)}], leave_eq: {l_eq:+.1f}, def: {def_adj:+.1f})"
        )

    def format_prompt(
        self,
        board: List[List[str]],
        rack: List[str],
        score_diff: int,
        bag_remaining: int,
        candidates: List[Dict[str, Any]],
    ) -> Tuple[str, List[str]]:
        """
        Builds the structured chat prompt for SmolLM2.

        Returns:
            Tuple of (formatted_prompt_string, active_candidate_labels).
        """
        num_cands = min(len(candidates), self.max_candidates)
        active_labels = CANDIDATE_LABELS[:num_cands]

        rack_str = "".join(sorted(rack))
        margin_str = f"+{score_diff}" if score_diff > 0 else str(score_diff)

        prompt_lines = [
            "<|im_start|>system",
            "You are an expert Scrabble grandmaster. Analyze the board state, tile rack, point margins, and candidate plays, then select the optimal move.<|im_end|>",
            "<|im_start|>user",
            f"[GAME STATE]",
            f"Score Margin: {margin_str} | Bag: {bag_remaining} tiles remaining",
            f"Hand Rack: [{rack_str}]",
            "",
            "[CANDIDATE PLAYS]",
        ]

        for idx, (label, cand) in enumerate(zip(active_labels, candidates[:num_cands])):
            cand_info = self.format_candidate_str(board, rack, cand, score_diff, bag_remaining)
            prompt_lines.append(f"[{label}] {cand_info}")

        prompt_lines.append("<|im_end|>")
        prompt_lines.append("<|im_start|>assistant")
        prompt_lines.append("Best Move: [")

        return "\n".join(prompt_lines), active_labels

    def rank_candidates(
        self,
        board: List[List[str]],
        rack: List[str],
        score_diff: int = 0,
        bag_remaining: int = 100,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Tuple[Dict[str, Any], float, float]]:
        """
        Ranks the provided candidate moves using SmolLM2.

        Args:
            board: 15x15 Scrabble board.
            rack: Current player's rack.
            score_diff: Current score difference (my_score - opp_score).
            bag_remaining: Remaining tiles in the bag.
            candidates: List of candidate move dictionaries.

        Returns:
            List of tuples: (candidate_dict, softmax_probability, raw_logit),
            sorted by probability in descending order.
        """
        if not candidates:
            return []

        prompt, active_labels = self.format_prompt(
            board, rack, score_diff, bag_remaining, candidates
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            # Logits for the final token position
            next_token_logits = outputs.logits[0, -1]

        active_token_ids = self.label_token_ids[:len(active_labels)]
        cand_logits = next_token_logits[active_token_ids].float()
        cand_probs = torch.softmax(cand_logits, dim=-1)

        ranked_results = []
        for i, (cand, prob, logit) in enumerate(zip(
            candidates[:len(active_labels)],
            cand_probs.cpu().tolist(),
            cand_logits.cpu().tolist(),
        )):
            ranked_results.append((cand, prob, logit))

        ranked_results.sort(key=lambda x: x[1], reverse=True)
        return ranked_results

    def select_best_move(
        self,
        board: List[List[str]],
        rack: List[str],
        score_diff: int = 0,
        bag_remaining: int = 100,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Selects the single best candidate move according to SmolLM2.
        """
        ranked = self.rank_candidates(board, rack, score_diff, bag_remaining, candidates)
        if not ranked:
            return None
        return ranked[0][0]
