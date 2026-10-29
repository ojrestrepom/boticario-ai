#!/bin/sh
# 6.2: crea una copia de data/build/catalog.db con casos que la base real no tiene (objetivo y subarea vacios,
# planta sin datos de seguridad, revision pendiente en un solo objetivo, nombres para el orden con acentos).
# Uso: make_modified_db.sh <catalog.db original> <copia de salida>. La copia no se versiona ni se sirve fuera de la prueba.
set -eu
cp "$1" "$2"
sqlite3 "$2" <<'SQL'
-- 1. objetivo sin plantas visibles
DELETE FROM plant_goal WHERE goal_id = 'cansancio-y-fatiga';
-- 2. subarea sin plantas visibles: todas sus filas pendientes de revision (la unica planta de molestias-oculares)
UPDATE plant_goal SET pending_review = 1 WHERE subarea_id = 'molestias-oculares';
-- 3. subarea omitida por filas pendientes y planta que sigue visible en otra subarea
UPDATE plant_goal SET pending_review = 1 WHERE subarea_id = 'circulacion' AND plant_id = 'ginkgo-biloba';
-- 4. planta con datos ausentes: sin seguridad y sin imagen
DELETE FROM plant_safety WHERE plant_id = 'lavandula-angustifolia';
DELETE FROM plant_image WHERE plant_id = 'lavandula-angustifolia';
-- 5. revision pendiente en un objetivo y no en otro (lavanda sigue en relajacion-estres)
UPDATE plant_goal SET pending_review = 1 WHERE plant_id = 'lavandula-angustifolia' AND goal_id = 'mejorar-el-sueno';
-- 6. nombres con acentos y mayusculas para el orden (escenario: abedul, Abutilon theophrasti, Arnica, Zarzaparrilla)
UPDATE plant_profile SET display_name = 'Árnica' WHERE plant_id = 'aloysia-citrodora';
UPDATE plant_profile SET display_name = 'abedul' WHERE plant_id = 'avena-sativa';
UPDATE plant_profile SET display_name = 'Zarzaparrilla' WHERE plant_id = 'eschscholzia-californica';
UPDATE plant_profile SET display_name = 'Abutilon theophrasti' WHERE plant_id = 'humulus-lupulus';
SQL
chmod 644 "$2"
