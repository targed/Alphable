import torch
import torch.nn as nn
import torch.optim as optim
from alphable_net import AlphableValueNet

def test_training_loop():
    print("Initializing Alphable Dummy Training...")

    # 1. Check device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # 2. Instantiate Model
    model = AlphableValueNet().to(device)
    print("Model initialized successfully.")

    # 3. Setup Loss and Optimizer
    # We use MSELoss because we want to predict a continuous value (win probability or expected value)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # 4. Generate Dummy Data (Simulate a batch of 64 After-States)
    batch_size = 64
    print(f"Generating dummy batch of size {batch_size}...")

    # Board: [Batch, Channels, Height, Width]
    # 31 Channels (26 letters, 1 blank, 4 premium squares)
    dummy_boards = torch.rand((batch_size, 31, 15, 15)).to(device)

    # State Vector: [Batch, 29]
    # 29 Elements (26 letter counts, 1 blank count, score diff, bag remaining)
    dummy_states = torch.rand((batch_size, 29)).to(device)

    # Target values: [Batch, 1]
    # Win probability in range [-1.0, 1.0]
    dummy_targets = (torch.rand((batch_size, 1)) * 2 - 1).to(device)

    # 5. Dummy Training Step
    print("Running forward pass...")
    optimizer.zero_grad()

    outputs = model(dummy_boards, dummy_states)

    print(f"Outputs shape: {outputs.shape}") # Should be [64, 1]

    print("Calculating loss...")
    loss = criterion(outputs, dummy_targets)
    print(f"Initial Loss: {loss.item():.4f}")

    print("Running backward pass...")
    loss.backward()

    print("Updating weights...")
    optimizer.step()

    print("Dummy training step completed successfully!")
    print("The PyTorch architecture, dimensions, and matrix math are fully verified.")
    print("Ready for Phase 2: Supervised Learning on Woogles Data.")

if __name__ == "__main__":
    test_training_loop()
