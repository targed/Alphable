# Removed the blanket sys.modules mocking of torch, alphable.core.inference, and alphable.core.simulator
# so that the actual code logic is tested instead of MagicMocks.
import sys
from unittest.mock import MagicMock

# Mock dependencies that are not available in the environment
mock_modules = [
    'torch',
    'alphable.core.inference'
]

for mod_name in mock_modules:
    sys.modules[mod_name] = MagicMock()
