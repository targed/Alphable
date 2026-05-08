import sys
from unittest.mock import MagicMock

# Simple mock for modules
def mock_module(name):
    if name not in sys.modules:
        sys.modules[name] = MagicMock()

# Mock torch and its submodules
mock_module('torch')
mock_module('torch.nn')
mock_module('torch.nn.functional')
mock_module('torch.optim')
mock_module('torch.multiprocessing')

# Mock other external dependencies
mock_module('numpy')
mock_module('tqdm')
