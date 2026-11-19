"""Backwards compatibility shim for legacy alphable_v4 imports."""
import sys
import alphable

# Forward module attributes
sys.modules[__name__] = alphable
