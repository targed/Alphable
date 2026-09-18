import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        out = F.relu(out)
        return out

class AlphableValueNet(nn.Module):
    def __init__(self, board_channels=31, num_res_blocks=5, num_filters=128, state_vector_size=36):
        """
        Args:
            board_channels: 31 (26 letters + 1 blank + 4 open premium squares)
            num_res_blocks: Number of residual blocks for board feature extraction
            num_filters: Number of filters in convolutional layers
            state_vector_size: 36 (rack counts + score diff + bag + strategic leave equity features)
        """
        super(AlphableValueNet, self).__init__()

        # 1. Board Convolutional Layers
        self.conv_input = nn.Sequential(
            nn.Conv2d(board_channels, num_filters, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(num_filters),
            nn.ReLU()
        )

        self.res_blocks = nn.Sequential(
            *[ResidualBlock(num_filters) for _ in range(num_res_blocks)]
        )

        # Reduce spatial channels before dense projection
        self.conv_reduce = nn.Sequential(
            nn.Conv2d(num_filters, 16, kernel_size=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU()
        )
        # Flatten size: 16 * 15 * 15 = 3600 -> projected to 256
        self.board_fc = nn.Sequential(
            nn.Linear(16 * 15 * 15, 256),
            nn.ReLU()
        )

        # 2. Game State Dense Layers
        self.state_fc = nn.Sequential(
            nn.Linear(state_vector_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )

        # 3. Concatenation & Final Layers (Balanced 256 board + 128 state = 384)
        self.fc_final = nn.Sequential(
            nn.Linear(256 + 128, 256),
            nn.ReLU(),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh() # Output in range [-1.0, 1.0] (Win Probability / Normalized Margin)
        )

    def forward(self, board, state):
        """
        Args:
            board: Tensor of shape (B, 31, 15, 15)
            state: Tensor of shape (B, 36)
        Returns:
            win_prob: Tensor of shape (B, 1) in [-1.0, 1.0]
        """
        # 1. Process board
        x = self.conv_input(board)
        x = self.res_blocks(x)
        x = self.conv_reduce(x)
        x = x.view(x.size(0), -1) # Flatten -> (B, 3600)
        x = self.board_fc(x)       # -> (B, 256)

        # 2. Process state vector
        s = self.state_fc(state)   # -> (B, 128)

        # 3. Concatenate balanced representations
        combined = torch.cat((x, s), dim=1) # -> (B, 384)

        # 4. Final output
        win_prob = self.fc_final(combined)
        return win_prob


def load_checkpoint_compatible(model, checkpoint_path, device=None):
    """
    Loads a model checkpoint, gracefully transferring matching weights (e.g. conv trunk)
    even if the state vector or dense head dimensions differ across architecture versions.
    """
    if device is None:
        device = next(model.parameters()).device
    ckpt = torch.load(checkpoint_path, map_location=device)
    if isinstance(ckpt, dict) and 'model_state_dict' in ckpt:
        ckpt = ckpt['model_state_dict']

    try:
        model.load_state_dict(ckpt)
        return len(ckpt), len(ckpt)
    except RuntimeError:
        model_dict = model.state_dict()
        compatible = {
            k: v for k, v in ckpt.items()
            if k in model_dict and v.shape == model_dict[k].shape
        }
        model_dict.update(compatible)
        model.load_state_dict(model_dict)
        return len(compatible), len(model_dict)

