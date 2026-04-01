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
    def __init__(self, board_channels=31, num_res_blocks=5, num_filters=128, state_vector_size=29):
        """
        Args:
            board_channels: 31 (26 letters + 1 blank + 4 premium squares)
            num_res_blocks: Number of residual blocks for board feature extraction
            num_filters: Number of filters in convolutional layers
            state_vector_size: 29 (26 letter counts + 1 blank count + score diff + bag remaining)
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

        # Output of res blocks is (B, num_filters, 15, 15)
        # We'll use a final conv layer to reduce channels before flattening
        self.conv_reduce = nn.Sequential(
            nn.Conv2d(num_filters, 16, kernel_size=1, bias=False), # reduce to 16 channels
            nn.BatchNorm2d(16),
            nn.ReLU()
        )
        # Flatten size: 16 * 15 * 15 = 3600
        board_flatten_size = 16 * 15 * 15

        # 2. Game State Dense Layers
        self.state_fc = nn.Sequential(
            nn.Linear(state_vector_size, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU()
        )
        # Output of state_fc is 64

        # 3. Concatenation & Final Layers
        # Total size = board_flatten_size + 64 = 3664
        total_size = board_flatten_size + 64

        self.fc_final = nn.Sequential(
            nn.Linear(total_size, 1024),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(1024, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 1),
            nn.Tanh() # Output in range [-1.0, 1.0] (Win Probability)
        )

    def forward(self, board, state):
        """
        Args:
            board: Tensor of shape (B, 31, 15, 15)
            state: Tensor of shape (B, 29)
        Returns:
            win_prob: Tensor of shape (B, 1) in [-1.0, 1.0]
        """
        # 1. Process board
        x = self.conv_input(board)
        x = self.res_blocks(x)
        x = self.conv_reduce(x)
        x = x.view(x.size(0), -1) # Flatten -> (B, 3600)

        # 2. Process state vector
        s = self.state_fc(state)  # -> (B, 64)

        # 3. Concatenate
        combined = torch.cat((x, s), dim=1) # -> (B, 3664)

        # 4. Final output
        win_prob = self.fc_final(combined)
        return win_prob
