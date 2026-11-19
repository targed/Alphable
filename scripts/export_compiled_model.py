#!/usr/bin/env python3
"""
scripts/export_compiled_model.py

Exports the trained V4ValueNetwork PyTorch checkpoint into an optimized,
high-throughput TorchScript compiled model for fast C++ execution.
"""

import os
import sys
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from alphable.models.value_net import V4ValueNetwork


def export_compiled(
    checkpoint_path: str,
    output_path: str,
    device: str = "cpu",
):
    print(f"Loading weights from {checkpoint_path}...")
    net = V4ValueNetwork()
    
    if os.path.exists(checkpoint_path):
        state_dict = torch.load(checkpoint_path, map_location=device)
        if "model_state_dict" in state_dict:
            state_dict = state_dict["model_state_dict"]
        net.load_state_dict(state_dict)
    else:
        print(f"Warning: Checkpoint {checkpoint_path} not found. Exporting initialized weights.")

    net.to(device)
    net.eval()

    dummy_board = torch.zeros((1, 32, 15, 15), dtype=torch.float32, device=device)
    dummy_state = torch.zeros((1, 64), dtype=torch.float32, device=device)

    print("Compiling model via torch.jit.trace...")
    with torch.no_grad():
        traced_model = torch.jit.trace(net, (dummy_board, dummy_state))
        
        # Parity check
        orig_out = net(dummy_board, dummy_state)
        traced_out = traced_model(dummy_board, dummy_state)
        max_diff = (orig_out - traced_out).abs().max().item()
        assert max_diff < 1e-4, f"Compilation parity check failed: max_diff={max_diff}"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    traced_model.save(output_path)
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Successfully exported compiled model to {output_path} ({file_size_mb:.2f} MB)")
    print(f"Numerical parity verified (max absolute error: {max_diff:.2e})")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    ckpt = str(repo_root / "alphable" / "models" / "checkpoints" / "v4_value_net_best.pt")
    out = str(repo_root / "alphable" / "models" / "checkpoints" / "v4_value_net_compiled.pt")
    export_compiled(ckpt, out)
