-- Ampliación del esquema neutral con los datos consolidados de la semilla (esquema v2).
-- Las tablas de la v1 siguen siendo las que lee la API actual; todo lo nuevo va en tablas aparte.
-- Convenciones de la v1: claves primarias con NOT NULL explícito y valores lógicos como BOOLEAN con CHECK (0, 1).
-- Las posiciones (`position`) conservan el orden del registro de origen, para que las lecturas sean estables.

-- Procedencia de cada referencia: dataset, licencia y URL de la que sale.
-- Son nulables porque las filas de la v1 no los traen; la construcción desde la semilla los escribe siempre y rechaza un dato sin dataset o sin licencia.
ALTER TABLE reference ADD COLUMN dataset TEXT;
ALTER TABLE reference ADD COLUMN license TEXT;
-- URL de la referencia (por ejemplo, el artículo concreto cuando la licencia exige enlazarlo); nulable porque no todas la tienen.
ALTER TABLE reference ADD COLUMN url TEXT;

-- Perfil de la planta: un registro por planta.
-- `display_name` es la fuente de verdad del nombre para mostrar (la API actual no lo usa).
-- `authors` son los autores del nombre científico canónico.
CREATE TABLE plant_profile (
    plant_id       TEXT NOT NULL PRIMARY KEY REFERENCES plant (id),
    display_name   TEXT,
    authors        TEXT,
    origin         TEXT,
    description    TEXT,
    oil_type       TEXT,
    record_version INTEGER NOT NULL,
    bundle_hash    TEXT NOT NULL,
    prompt_version INTEGER NOT NULL
);

-- Grupos de uso tradicional: una actividad (en español) con su etiqueta original, el número de registros y los países.
-- `countries` es un arreglo JSON de textos ya en español: solo se lee completo, nunca se filtra por país.
-- `pending_review` es verdadero solo si ninguna cita del grupo está resuelta; esos grupos no generan filas en `plant_use`.
CREATE TABLE plant_use_group (
    id              INTEGER NOT NULL PRIMARY KEY,
    plant_id        TEXT NOT NULL REFERENCES plant (id),
    position        INTEGER NOT NULL,
    activity        TEXT NOT NULL,
    activity_source TEXT NOT NULL,
    n               INTEGER NOT NULL CHECK (n >= 1),
    countries       TEXT NOT NULL DEFAULT '[]',
    pending_review  BOOLEAN NOT NULL CHECK (pending_review IN (0, 1)),
    UNIQUE (plant_id, position)
);

-- Citas de cada grupo de uso, resueltas o no.
-- Una cita sin resolver no tiene `reference_id`; conserva su clave y su texto para mostrarla como «(sin resolver)».
CREATE TABLE plant_use_group_ref (
    use_group_id INTEGER NOT NULL REFERENCES plant_use_group (id),
    key          TEXT NOT NULL,
    position     INTEGER NOT NULL,
    text         TEXT NOT NULL,
    resolved     BOOLEAN NOT NULL CHECK (resolved IN (0, 1)),
    reference_id TEXT REFERENCES reference (id),
    PRIMARY KEY (use_group_id, key),
    CHECK (resolved = (reference_id IS NOT NULL))
);
CREATE INDEX idx_plant_use_group_ref_reference ON plant_use_group_ref (reference_id);

-- Catálogo de objetivos, con el orden en que se muestran.
CREATE TABLE goal (
    id       TEXT NOT NULL PRIMARY KEY,
    label    TEXT NOT NULL,
    position INTEGER NOT NULL
);

-- Subáreas de un objetivo. El par (goal_id, id) es único para que `plant_goal` pueda comprobar que la subárea pertenece al objetivo.
CREATE TABLE goal_subarea (
    id       TEXT NOT NULL PRIMARY KEY,
    goal_id  TEXT NOT NULL REFERENCES goal (id),
    label    TEXT NOT NULL,
    position INTEGER NOT NULL,
    UNIQUE (goal_id, id)
);

-- Objetivos de cada planta, con su subárea (si la hay), área, evidencia y marca de revisión pendiente.
-- La clave foránea compuesta exige que la subárea sea del objetivo; si `subarea_id` es nulo no se comprueba.
CREATE TABLE plant_goal (
    id             INTEGER NOT NULL PRIMARY KEY,
    plant_id       TEXT NOT NULL REFERENCES plant (id),
    goal_id        TEXT NOT NULL REFERENCES goal (id),
    subarea_id     TEXT,
    position       INTEGER NOT NULL,
    area           TEXT NOT NULL,
    evidence       TEXT NOT NULL,
    pending_review BOOLEAN NOT NULL CHECK (pending_review IN (0, 1)),
    FOREIGN KEY (goal_id, subarea_id) REFERENCES goal_subarea (goal_id, id)
);
-- Un mismo objetivo, subárea y área no se repite en una planta (el COALESCE hace que el nulo también cuente como valor).
CREATE UNIQUE INDEX idx_plant_goal_unique ON plant_goal (plant_id, goal_id, COALESCE(subarea_id, ''), area);
-- Plantas por objetivo y subárea.
CREATE INDEX idx_plant_goal_goal ON plant_goal (goal_id, subarea_id, plant_id);

-- Referencias que respaldan cada objetivo de una planta.
CREATE TABLE plant_goal_ref (
    plant_goal_id INTEGER NOT NULL REFERENCES plant_goal (id),
    reference_id  TEXT NOT NULL REFERENCES reference (id),
    PRIMARY KEY (plant_goal_id, reference_id)
);
CREATE INDEX idx_plant_goal_ref_reference ON plant_goal_ref (reference_id);

-- Seguridad: como máximo un registro por planta. Sin registro no hay ningún dato.
-- `level` nulo es una precaución sin nivel: se conserva el texto.
CREATE TABLE plant_safety (
    plant_id TEXT NOT NULL PRIMARY KEY REFERENCES plant (id),
    level    TEXT CHECK (level IN ('alto', 'medio', 'bajo')),
    text     TEXT NOT NULL
);

-- Referencias que respaldan la seguridad de una planta.
CREATE TABLE plant_safety_ref (
    plant_id     TEXT NOT NULL REFERENCES plant_safety (plant_id),
    reference_id TEXT NOT NULL REFERENCES reference (id),
    PRIMARY KEY (plant_id, reference_id)
);
CREATE INDEX idx_plant_safety_ref_reference ON plant_safety_ref (reference_id);

-- Imagen de la planta con su licencia: como máximo una por planta.
-- `author` y `license_url` pueden faltar; `attribution_required` indica si hay que mostrar la atribución.
CREATE TABLE plant_image (
    plant_id             TEXT NOT NULL PRIMARY KEY REFERENCES plant (id),
    url                  TEXT NOT NULL,
    page_url             TEXT NOT NULL,
    author               TEXT,
    license              TEXT NOT NULL,
    license_url          TEXT,
    attribution_required BOOLEAN NOT NULL CHECK (attribution_required IN (0, 1))
);

-- IDs anteriores de una planta. El alias es único en toda la base porque resuelve a una sola planta.
CREATE TABLE plant_alias (
    alias    TEXT NOT NULL PRIMARY KEY,
    plant_id TEXT NOT NULL REFERENCES plant (id)
);
CREATE INDEX idx_plant_alias_plant ON plant_alias (plant_id);

-- Marcas de revisión del registro: código, a qué dato apuntan y el mensaje.
CREATE TABLE plant_review_flag (
    id       INTEGER NOT NULL PRIMARY KEY,
    plant_id TEXT NOT NULL REFERENCES plant (id),
    code     TEXT NOT NULL,
    target   TEXT NOT NULL,
    message  TEXT NOT NULL
);
CREATE INDEX idx_plant_review_flag_plant ON plant_review_flag (plant_id);
CREATE INDEX idx_plant_review_flag_code ON plant_review_flag (code);
