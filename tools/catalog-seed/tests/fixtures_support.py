"""Carga de los fixtures de validate/ (registros y paquetes hechos a mano)."""
import copy
import json
import os

import support  # noqa: F401

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "validate")


def load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return json.load(handle)


def record(name="matricaria"):
    return copy.deepcopy(load("record_%s.json" % name))


def bundle(name="matricaria"):
    return copy.deepcopy(load("bundle_%s.json" % name))
