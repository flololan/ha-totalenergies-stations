"""Pytest configuration.

The parsing helpers are framework-free, but importing the package normally
would execute ``custom_components/totalenergies_stations/__init__.py`` which
needs Home Assistant. We therefore register a lightweight package stub whose
``__path__`` points at the integration folder so ``parsing``/``const`` can be
imported as submodules without Home Assistant installed.
"""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT / "custom_components" / "totalenergies_stations"

for name, path in (
    ("custom_components", ROOT / "custom_components"),
    ("custom_components.totalenergies_stations", PKG_DIR),
):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
