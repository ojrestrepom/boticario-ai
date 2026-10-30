"""Soporte de las pruebas del resolvedor: índice SQLite construido una sola vez desde los fixtures recortados."""
import atexit
import os
import shutil
import tempfile

import support  # noqa: F401  (ajusta sys.path)
from catalog_seed.taxonomy import build_index, open_backbone

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "taxonomy")

_state = {}


def backbones():
    """(wcvp, wfo) sobre un índice temporal construido desde `tests/fixtures/taxonomy/`."""
    if "wcvp" not in _state:
        tmp = tempfile.mkdtemp(prefix="taxonomy-index-")
        atexit.register(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "taxonomy.db")
        _state["stats"] = build_index(
            path, os.path.join(FIXTURES, "wcvp_names.csv"), os.path.join(FIXTURES, "wcvp_distribution.csv"),
            os.path.join(FIXTURES, "wfo_classification.csv"), "fixture", "fixture")
        _state["wcvp"] = open_backbone(path, "wcvp")
        _state["wfo"] = open_backbone(path, "wfo")
    return _state["wcvp"], _state["wfo"]


def build_stats():
    backbones()
    return _state["stats"]
