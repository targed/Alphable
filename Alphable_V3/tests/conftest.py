import sys
from unittest.mock import MagicMock

# Mock dependencies that are not available in the environment
mock_modules = [
    'torch',
    'alphable.core.inference',
    'alphable.core.simulator'
]

for mod_name in mock_modules:
    sys.modules[mod_name] = MagicMock()
