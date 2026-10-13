-- Esquema neutral del catálogo de plantas.
-- Es el único contrato que lee la API: no contiene nombres ni estructuras propias de ningún dataset.
-- La configuración de conexión (claves foráneas, journal, etc.) se hace al abrir la conexión, no aquí.
-- Las claves primarias llevan NOT NULL explícito: SQLite admite NULL en las de texto por una rareza histórica y Diesel las leería como Option.
-- En las de tipo INTEGER, NOT NULL no impide que SQLite asigne el id solo cuando no se indica.

-- Metadatos de la base; guarda, entre otros, la versión del esquema ("schema_version").
CREATE TABLE metadata (
    key   TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL
);

-- Fuentes de datos con su procedencia y licencia.
CREATE TABLE source (
    id       TEXT NOT NULL PRIMARY KEY,
    name     TEXT NOT NULL,
    version  TEXT NOT NULL,
    license  TEXT NOT NULL,
    citation TEXT NOT NULL,
    url      TEXT NOT NULL,
    checksum TEXT NOT NULL
);

-- Plantas; el id público es el slug del nombre científico canónico.
-- La familia es un valor único: family_source_id registra qué fuente fue elegida.
CREATE TABLE plant (
    id                         TEXT NOT NULL PRIMARY KEY,
    scientific_name            TEXT NOT NULL,
    scientific_name_normalized TEXT NOT NULL UNIQUE,
    family                     TEXT,
    family_source_id           TEXT REFERENCES source (id),
    CHECK ((family IS NULL) = (family_source_id IS NULL))
);

-- Enlace de procedencia: el identificador que cada fuente le da a la planta.
CREATE TABLE plant_source_id (
    plant_id        TEXT NOT NULL REFERENCES plant (id),
    source_id       TEXT NOT NULL REFERENCES source (id),
    source_plant_id TEXT NOT NULL,
    PRIMARY KEY (plant_id, source_id)
);
CREATE INDEX idx_plant_source_id_source ON plant_source_id (source_id);

-- Nombres de planta (científicos o comunes) con idioma y versión normalizada para buscar.
CREATE TABLE plant_name (
    id         INTEGER NOT NULL PRIMARY KEY,
    plant_id   TEXT NOT NULL REFERENCES plant (id),
    text       TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('scientific', 'common')),
    language   TEXT NOT NULL,
    normalized TEXT NOT NULL,
    UNIQUE (plant_id, text, kind, language)
);
CREATE INDEX idx_plant_name_normalized ON plant_name (normalized);
CREATE INDEX idx_plant_name_plant ON plant_name (plant_id);

-- Partes de la planta.
CREATE TABLE plant_part (
    id       INTEGER NOT NULL PRIMARY KEY,
    plant_id TEXT NOT NULL REFERENCES plant (id),
    label    TEXT NOT NULL,
    UNIQUE (plant_id, label)
);
CREATE INDEX idx_plant_part_plant ON plant_part (plant_id);

-- Referencias bibliográficas.
CREATE TABLE reference (
    id       TEXT NOT NULL PRIMARY KEY,
    citation TEXT NOT NULL
);

-- Usos de la planta (actividad e idioma) respaldados por una referencia.
CREATE TABLE plant_use (
    id           INTEGER NOT NULL PRIMARY KEY,
    plant_id     TEXT NOT NULL REFERENCES plant (id),
    activity     TEXT NOT NULL,
    language     TEXT NOT NULL,
    reference_id TEXT NOT NULL REFERENCES reference (id),
    UNIQUE (plant_id, activity, language, reference_id)
);
CREATE INDEX idx_plant_use_plant ON plant_use (plant_id);
CREATE INDEX idx_plant_use_reference ON plant_use (reference_id);

-- Atribución: qué fuentes aportan cada nombre.
CREATE TABLE plant_name_source (
    plant_name_id INTEGER NOT NULL REFERENCES plant_name (id),
    source_id     TEXT NOT NULL REFERENCES source (id),
    PRIMARY KEY (plant_name_id, source_id)
);

-- Atribución: qué fuentes aportan cada parte.
CREATE TABLE plant_part_source (
    plant_part_id INTEGER NOT NULL REFERENCES plant_part (id),
    source_id     TEXT NOT NULL REFERENCES source (id),
    PRIMARY KEY (plant_part_id, source_id)
);

-- Atribución: qué fuentes aportan cada uso.
CREATE TABLE plant_use_source (
    plant_use_id INTEGER NOT NULL REFERENCES plant_use (id),
    source_id    TEXT NOT NULL REFERENCES source (id),
    PRIMARY KEY (plant_use_id, source_id)
);

-- Atribución: qué fuentes aportan cada referencia.
CREATE TABLE reference_source (
    reference_id TEXT NOT NULL REFERENCES reference (id),
    source_id    TEXT NOT NULL REFERENCES source (id),
    PRIMARY KEY (reference_id, source_id)
);
