"""IDs públicos: el mismo slug que `catalog_core::normalize::slug` del backend, con `×` como `x`."""
import unicodedata


def _normalize_name(text):
    """Equivale a `normalize_name` de Rust: minúsculas, NFD sin marcas combinantes, espacios colapsados."""
    stripped = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))
    return " ".join(stripped.split())


def slug(text):
    """Slug de `backend/catalog-core/src/normalize.rs`: ASCII alfanumérico en minúsculas, `-` entre secuencias."""
    out = []
    pending_dash = False
    for c in _normalize_name(text):
        if c.isascii() and c.isalnum():
            if pending_dash and out:
                out.append("-")
            pending_dash = False
            out.append(c)
        else:
            pending_dash = True
    return "".join(out)


def plant_slug(name):
    """ID público de una planta a partir de su nombre científico (`×` y `+` de híbrido se escriben como `x`)."""
    return slug((name or "").replace("×", "x").replace("+", " "))
