"""Alphable Root Package."""

import sys

try:
    import torch
    torch.backends.cudnn.enabled = False
    torch.backends.cudnn.benchmark = False
except ImportError:
    pass

# Backwards compatibility alias for existing checkpoints and legacy code
sys.modules.setdefault("alphable_v4", sys.modules[__name__])

from . import engine, models, platform, search, training

sys.modules.setdefault("alphable_v4.engine", engine)
sys.modules.setdefault("alphable_v4.models", models)
sys.modules.setdefault("alphable_v4.platform", platform)
sys.modules.setdefault("alphable_v4.search", search)
sys.modules.setdefault("alphable_v4.training", training)

from .engine import game_state, magpie_bindings
from .models import value_net
from .search import bams
from .platform import eval

sys.modules.setdefault("alphable_v4.engine.game_state", engine.game_state)
sys.modules.setdefault("alphable_v4.engine.magpie_bindings", engine.magpie_bindings)
sys.modules.setdefault("alphable_v4.models.value_net", models.value_net)
sys.modules.setdefault("alphable_v4.search.bams", search.bams)
sys.modules.setdefault("alphable_v4.platform.eval", platform.eval)
