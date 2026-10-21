"""Resolvedor taxonómico de la semilla del catálogo (tareas 2.1 a 2.5 de `consolidate-catalog-seed`)."""
from .index import Backbone, build_index, open_backbone  # noqa: F401
from .names import (ParsedName, author_score, authors_match, canonical_rank, clean_text, make_keys,  # noqa: F401
                    parse_name, split_source_names)
from .resolver import (epithet_variants, resolve, resolve_name, resolve_variants, synonyms)  # noqa: F401
from .ids import plant_slug, slug  # noqa: F401
from .universe import Entry, Plant, Universe, UniverseError, build_universe  # noqa: F401
