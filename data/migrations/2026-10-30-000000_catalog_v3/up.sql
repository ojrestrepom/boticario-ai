-- Ampliación del esquema neutral con el glosario de actividades (esquema v3).
-- Las tablas de la v1 y la v2 no cambian, salvo la columna nueva de `plant_use_group`.
-- Convenciones de la v1: claves primarias con NOT NULL explícito y valores lógicos como BOOLEAN con CHECK (0, 1).

-- Glosario de actividades: una explicación breve por término, tomada de una fuente abierta citada.
-- `key` es la forma base normalizada del término (texto antes del primer paréntesis, en minúsculas NFC, sin quitar acentos): con ella se enlazan los grupos de uso.
-- `term` es el término tal como se muestra; `text` es la explicación tal como la guarda la semilla.
-- `entry_url` es la URL permanente de la revisión de la entrada o del artículo de la que sale el texto, y `revision_date` la fecha (AAAA-MM-DD) de esa revisión.
-- `source_id` apunta a la fuente del manifiesto; `source_name` es su nombre corto para mostrar; `adapted` es verdadero si el texto es una paráfrasis y no el texto literal de la fuente.
CREATE TABLE activity_glossary (
    key           TEXT NOT NULL PRIMARY KEY CHECK (key <> ''),
    term          TEXT NOT NULL CHECK (term <> ''),
    text          TEXT NOT NULL CHECK (text <> ''),
    entry_url     TEXT NOT NULL CHECK (entry_url LIKE 'https://%'),
    revision_date TEXT NOT NULL,
    source_id     TEXT NOT NULL REFERENCES source (id),
    source_name   TEXT NOT NULL CHECK (source_name <> ''),
    adapted       BOOLEAN NOT NULL CHECK (adapted IN (0, 1))
);
CREATE INDEX idx_activity_glossary_source ON activity_glossary (source_id);

-- Término del glosario que explica la actividad del grupo; nulo si la actividad no tiene término.
ALTER TABLE plant_use_group ADD COLUMN glossary_key TEXT REFERENCES activity_glossary (key);
CREATE INDEX idx_plant_use_group_glossary ON plant_use_group (glossary_key);
