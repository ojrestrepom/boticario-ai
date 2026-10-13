-- Deshace el esquema neutral: borra las tablas en orden inverso a su creación, primero las que dependen de otras por clave foránea.
DROP TABLE reference_source;
DROP TABLE plant_use_source;
DROP TABLE plant_part_source;
DROP TABLE plant_name_source;
DROP TABLE plant_use;
DROP TABLE reference;
DROP TABLE plant_part;
DROP TABLE plant_name;
DROP TABLE plant_source_id;
DROP TABLE plant;
DROP TABLE source;
DROP TABLE metadata;
