"""Candidatas de cita para las claves cortas de REFERENCE de ETHNOBOT (tarea 3.2, decisión D13).

La selección es una heurística simple y deliberada: no resuelve la cita. Quien decide a qué entrada de `usda_reference`
corresponde cada clave es el LLM, que cita el ref de la candidata. Orden de prioridad, con tope `MAX_CANDIDATES`:

1. la entrada exacta (la misma clave);
2. las de clave normalizada igual (minúsculas, sin espacios ni puntuación): `Burkill,1966` encuentra `Burkill, 1966`;
3. las que comparten el prefijo alfabético de la clave normalizada: `Woi.10` encuentra `WOI`; `Eb24: 441` encuentra `EB` y las `EBxx:yyy`.
   Se ordenan por el prefijo común más largo de la clave normalizada (de mayor a menor), después por la clave normalizada más corta
   (así la obra general `EB` va antes que sus tomos) y por la clave literal.

Una clave sin prefijo alfabético (numérica, por ejemplo `15`) solo puede tener candidata exacta o normalizada igual.
"""
import re

MAX_CANDIDATES = 5
REFERENCE_REF = "usda_reference:%s"
MATCH_EXACT, MATCH_NORMALIZED, MATCH_PREFIX = "exacta", "normalizada", "prefijo"

_NON_ALNUM = re.compile(r"[\W_]+", re.UNICODE)
_ALPHA_PREFIX = re.compile(r"^[^\W\d_]+", re.UNICODE)


def normalize_key(key):
    """Minúsculas y solo letras y dígitos."""
    return _NON_ALNUM.sub("", (key or "").lower())


def alpha_prefix(key):
    """Letras iniciales de la clave normalizada (`woi`, `eb`, `burkill`); cadena vacía si empieza por un dígito."""
    match = _ALPHA_PREFIX.match(normalize_key(key))
    return match.group(0) if match else ""


def _common_length(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


class ReferenceIndex(object):
    """Índice de las entradas `usda_reference` (lista de dicts con `reference` y `longref`) para elegir candidatas."""

    def __init__(self, references):
        self.by_key = {}
        self.by_norm = {}
        self.by_prefix = {}
        for ref in references:
            key = ref["reference"]
            self.by_key[key] = ref
            norm = normalize_key(key)
            self.by_norm.setdefault(norm, []).append(key)
            prefix = alpha_prefix(key)
            if prefix:
                self.by_prefix.setdefault(prefix, []).append(key)
        self._cache = {}

    def candidates(self, short_key, limit=MAX_CANDIDATES):
        """Hasta `limit` candidatas para la clave corta: `[{ref, reference, longref, match}]`, en orden de prioridad."""
        short_key = (short_key or "").strip()
        cache_key = (short_key, limit)
        if cache_key in self._cache:
            return self._cache[cache_key]
        chosen, seen = [], set()

        def add(key, match):
            if key not in seen and len(chosen) < limit:
                seen.add(key)
                entry = self.by_key[key]
                chosen.append({"ref": REFERENCE_REF % key, "reference": key, "longref": entry.get("longref") or "", "match": match})

        if short_key in self.by_key:
            add(short_key, MATCH_EXACT)
        norm = normalize_key(short_key)
        for key in sorted(self.by_norm.get(norm, ())):
            add(key, MATCH_NORMALIZED)
        prefix = alpha_prefix(short_key)
        if prefix:
            pool = self.by_prefix.get(prefix, ())
            ranked = sorted(pool, key=lambda k: (-_common_length(normalize_key(k), norm), len(normalize_key(k)), k))
            for key in ranked:
                add(key, MATCH_PREFIX)
        self._cache[cache_key] = chosen
        return chosen
