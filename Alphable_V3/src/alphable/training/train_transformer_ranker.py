"""
Training and Fine-Tuning Pipeline for SmolLM2 Scrabble Candidate Ranker.

Extracts Grandmaster-evaluated candidate moves from Woogles match telemetry
(analysis.json + game.gcg) and fine-tunes SmolLM2 to rank the optimal moves.
"""

import os
import glob
import json
import random
import argparse
from typing import List, Dict, Tuple, Any, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, get_cosine_schedule_with_warmup

from alphable.models.transformer_ranker import CANDIDATE_LABELS


class ScrabbleRankingDataset(Dataset):
    """
    Dataset of (prompt_ids, target_label_idx) pairs for fine-tuning SmolLM2.
    """

    def __init__(self, samples: List[Dict[str, Any]], tokenizer, max_length: int = 384):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        item = self.samples[idx]
        prompt = item["prompt"]
        target_idx = item["target_label_idx"]

        encoded = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors="pt",
        )

        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "target_label_idx": torch.tensor(target_idx, dtype=torch.long),
        }


def collate_ranking_batch(batch: List[Dict[str, Any]], pad_token_id: int):
    """Pads variable-length input sequences to the max length in the batch."""
    input_ids = [item["input_ids"] for item in batch]
    attention_mask = [item["attention_mask"] for item in batch]
    targets = torch.stack([item["target_label_idx"] for item in batch])

    padded_ids = torch.nn.utils.rnn.pad_sequence(
        input_ids, batch_first=True, padding_value=pad_token_id
    )
    padded_masks = torch.nn.utils.rnn.pad_sequence(
        attention_mask, batch_first=True, padding_value=0
    )

    return {
        "input_ids": padded_ids,
        "attention_mask": padded_masks,
        "target_label_idx": targets,
    }


def parse_gcg_state_history(gcg_file: str) -> List[Dict[str, int]]:
    """
    Parses game.gcg to track player cumulative scores and bag counts turn-by-turn.
    Returns list of dicts: {'score_diff': int, 'bag_remaining': int} for each turn.
    """
    if not os.path.exists(gcg_file):
        return []

    player_scores = {}
    turns = []
    tiles_played_total = 0

    with open(gcg_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line.startswith(">"):
                continue
            parts = line[1:].split()
            if len(parts) < 3:
                continue

            p_name = parts[0].rstrip(":")
            cum_score = None
            for item in reversed(parts):
                if item.isdigit():
                    cum_score = int(item)
                    break

            if p_name not in player_scores:
                player_scores[p_name] = 0

            other_scores = [score for name, score in player_scores.items() if name != p_name]
            opp_score = other_scores[0] if other_scores else 0
            curr_score = player_scores[p_name]
            score_diff = curr_score - opp_score

            bag_rem = max(0, 100 - tiles_played_total)
            turns.append({"score_diff": score_diff, "bag_remaining": bag_rem})

            if cum_score is not None:
                player_scores[p_name] = cum_score
            if len(parts) >= 4:
                word_part = parts[3]
                tiles_played = len([c for c in word_part if c != "."])
                tiles_played_total += tiles_played

    return turns


def extract_match_ranking_samples(
    match_dir: str,
    max_candidates_per_turn: int = 8,
) -> List[Dict[str, Any]]:
    """
    Extracts candidate ranking prompts and target move indices from a single match folder.
    """
    analysis_file = os.path.join(match_dir, "analysis.json")
    if not os.path.exists(analysis_file):
        return []

    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)
    except Exception:
        return []

    gcg_file = os.path.join(match_dir, "game.gcg")
    gcg_history = parse_gcg_state_history(gcg_file)

    samples = []

    for t_idx, turn in enumerate(analysis_data):
        suggestions = turn.get("suggestions", [])
        if len(suggestions) < 2:
            continue

        rack = turn.get("rack", [])
        rack_str = "".join(sorted(rack)) if rack else "?"

        # Best move according to Macondo is suggestions[0]
        best_sugg = suggestions[0]

        # Select up to max_candidates_per_turn candidates
        cands_to_use = suggestions[:max_candidates_per_turn]
        if len(cands_to_use) < 2:
            continue

        # Shuffle the candidates so the target is not always in position [A]
        indexed_cands = list(enumerate(cands_to_use))
        random.shuffle(indexed_cands)

        target_label_idx = None
        prompt_cands = []

        for label_pos, (orig_idx, sugg) in enumerate(indexed_cands):
            label = CANDIDATE_LABELS[label_pos]
            if orig_idx == 0:
                target_label_idx = label_pos

            coords = sugg.get("coords", "")
            word = sugg.get("word", "")
            pts = sugg.get("points", 0)
            leave = sugg.get("leave", "")
            equity = sugg.get("equity", 0.0)

            cand_line = f"[{label}] {coords} {word} (+{pts} pts, leave: [{leave}], eq: {equity:+.1f})"
            prompt_cands.append(cand_line)

        if target_label_idx is None:
            continue

        # Exact game state margin and bag counts
        if t_idx < len(gcg_history):
            score_diff = gcg_history[t_idx]["score_diff"]
            bag_remaining = gcg_history[t_idx]["bag_remaining"]
        else:
            score_diff = 0
            bag_remaining = max(0, 100 - (t_idx * 7))

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
        prompt_lines.extend(prompt_cands)
        prompt_lines.append("<|im_end|>")
        prompt_lines.append("<|im_start|>assistant")
        prompt_lines.append("Best Move: [")

        full_prompt = "\n".join(prompt_lines)

        samples.append({
            "prompt": full_prompt,
            "target_label_idx": target_label_idx,
            "num_candidates": len(cands_to_use),
        })

    return samples


def prepare_ranking_dataset(
    matches_dir: str = "data/woogles/matches",
    max_candidates: int = 8,
    max_samples: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Loads all matches and builds ranking training samples."""
    match_folders = glob.glob(os.path.join(matches_dir, "*"))
    all_samples = []

    for folder in match_folders:
        if os.path.isdir(folder):
            samples = extract_match_ranking_samples(folder, max_candidates_per_turn=max_candidates)
            all_samples.extend(samples)
            if max_samples and len(all_samples) >= max_samples:
                all_samples = all_samples[:max_samples]
                break

    random.shuffle(all_samples)
    return all_samples


def train_transformer_ranker(
    matches_dir: str = "data/woogles/matches",
    model_name: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
    output_dir: str = "models/transformer_ranker_v2",
    epochs: int = 5,
    batch_size: int = 8,
    gradient_accumulation_steps: int = 2,
    lr: float = 5e-5,
    max_candidates: int = 8,
    max_samples: Optional[int] = None,
    device: Optional[str] = None,
):
    """
    Fine-tunes SmolLM2 on Scrabble Grandmaster candidate ranking.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Loading tokenizer: {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Extracting ranking samples from {matches_dir}...")
    samples = prepare_ranking_dataset(matches_dir, max_candidates=max_candidates, max_samples=max_samples)
    print(f"Total extracted ranking positions: {len(samples)}")

    if len(samples) < 10:
        raise ValueError(f"Insufficient training samples found in {matches_dir} ({len(samples)} found).")

    # Split into train/validation (90/10)
    split_idx = int(0.9 * len(samples))
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]
    print(f"Train samples: {len(train_samples)}, Validation samples: {len(val_samples)}")

    train_dataset = ScrabbleRankingDataset(train_samples, tokenizer)
    val_dataset = ScrabbleRankingDataset(val_samples, tokenizer)

    pad_id = tokenizer.pad_token_id
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_ranking_batch(b, pad_id),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_ranking_batch(b, pad_id),
    )

    print(f"Initializing SmolLM2 on {device}...")
    if device == "cuda":
        torch.backends.cudnn.enabled = False
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch.bfloat16,
            device_map="cuda",
            attn_implementation="eager",
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch.float32,
            device_map="cpu",
        )

    # Precompute candidate label token IDs
    label_token_ids = torch.tensor(
        [tokenizer.convert_tokens_to_ids(label) for label in CANDIDATE_LABELS[:max_candidates]],
        device=device,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    best_val_acc = 0.0

    gradient_accumulation_steps = max(1, gradient_accumulation_steps)
    total_opt_steps = (len(train_loader) // gradient_accumulation_steps) * epochs
    warmup_steps = min(150, max(10, total_opt_steps // 10))
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=max(1, total_opt_steps)
    )

    os.makedirs(output_dir, exist_ok=True)

    optimizer.zero_grad()
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct_top1 = 0
        total_samples = 0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs} [Train]")
        for step_idx, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            target_indices = batch["target_label_idx"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            # Find the position of the last non-padded token for each sequence in batch
            seq_lens = attention_mask.sum(dim=1) - 1
            batch_size_cur = input_ids.shape[0]

            last_logits = outputs.logits[torch.arange(batch_size_cur, device=device), seq_lens]
            # Extract logits for candidate labels and cast to float32 for stable cross-entropy
            cand_logits = last_logits[:, label_token_ids].float()

            raw_loss = F.cross_entropy(cand_logits, target_indices)
            loss = raw_loss / gradient_accumulation_steps
            loss.backward()

            if (step_idx + 1) % gradient_accumulation_steps == 0 or (step_idx + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            total_loss += raw_loss.item() * batch_size_cur
            preds = torch.argmax(cand_logits, dim=-1)
            correct_top1 += (preds == target_indices).sum().item()
            total_samples += batch_size_cur

            pbar.set_postfix({
                "loss": f"{raw_loss.item():.4f}",
                "acc": f"{(correct_top1 / total_samples) * 100:.1f}%",
            })

        train_loss = total_loss / total_samples
        train_acc = (correct_top1 / total_samples) * 100

        # Validation
        model.eval()
        val_loss = 0.0
        val_top1 = 0
        val_top3 = 0
        val_samples_count = 0

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                target_indices = batch["target_label_idx"].to(device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                seq_lens = attention_mask.sum(dim=1) - 1
                batch_size_cur = input_ids.shape[0]

                last_logits = outputs.logits[torch.arange(batch_size_cur, device=device), seq_lens]
                cand_logits = last_logits[:, label_token_ids].float()

                loss = F.cross_entropy(cand_logits, target_indices)
                val_loss += loss.item() * batch_size_cur

                preds = torch.argmax(cand_logits, dim=-1)
                val_top1 += (preds == target_indices).sum().item()

                # Top-3 accuracy
                top3_preds = torch.topk(cand_logits, k=min(3, max_candidates), dim=-1).indices
                for i in range(batch_size_cur):
                    if target_indices[i] in top3_preds[i]:
                        val_top3 += 1

                val_samples_count += batch_size_cur

        val_loss_avg = val_loss / val_samples_count
        val_top1_acc = (val_top1 / val_samples_count) * 100
        val_top3_acc = (val_top3 / val_samples_count) * 100

        print(
            f"Epoch {epoch}/{epochs} Results | "
            f"Train Loss: {train_loss:.4f}, Train Top-1 Acc: {train_acc:.1f}% | "
            f"Val Loss: {val_loss_avg:.4f}, Val Top-1 Acc: {val_top1_acc:.1f}%, Val Top-3 Acc: {val_top3_acc:.1f}%"
        )

        # Save best model
        if val_top1_acc > best_val_acc:
            best_val_acc = val_top1_acc
            print(f"New best validation Top-1 accuracy ({val_top1_acc:.1f}%)! Saving model to {output_dir}...")
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

    print(f"SmolLM2 Candidate Ranker training complete! Best Val Top-1: {best_val_acc:.1f}%")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Fine-tune SmolLM2 Candidate Ranker on Scrabble Grandmaster data.")
    parser.add_argument("--matches-dir", type=str, default="data/woogles/matches", help="Directory with match data.")
    parser.add_argument("--model-name", type=str, default="HuggingFaceTB/SmolLM2-135M-Instruct", help="Base model name.")
    parser.add_argument("--output-dir", type=str, default="models/transformer_ranker_v2", help="Save directory.")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=8, help="Training batch size.")
    parser.add_argument("--grad-accum", type=int, default=2, help="Gradient accumulation steps.")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate.")
    parser.add_argument("--max-candidates", type=int, default=8, help="Max candidates per turn.")
    parser.add_argument("--max-samples", type=int, default=None, help="Max samples to train on.")
    args = parser.parse_args()

    train_transformer_ranker(
        matches_dir=args.matches_dir,
        model_name=args.model_name,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        lr=args.lr,
        max_candidates=args.max_candidates,
        max_samples=args.max_samples,
    )


if __name__ == "__main__":
    main()
