-- Deshace la ampliación v3: borra la columna de enlace y después la tabla del glosario.
DROP INDEX idx_plant_use_group_glossary;
ALTER TABLE plant_use_group DROP COLUMN glossary_key;
DROP TABLE activity_glossary;
