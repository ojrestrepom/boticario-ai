-- Deshace la ampliación v2: borra las tablas nuevas en orden inverso a su creación y las columnas añadidas a `reference`.
DROP TABLE plant_review_flag;
DROP TABLE plant_alias;
DROP TABLE plant_image;
DROP TABLE plant_safety_ref;
DROP TABLE plant_safety;
DROP TABLE plant_goal_ref;
DROP TABLE plant_goal;
DROP TABLE goal_subarea;
DROP TABLE goal;
DROP TABLE plant_use_group_ref;
DROP TABLE plant_use_group;
DROP TABLE plant_profile;
ALTER TABLE reference DROP COLUMN url;
ALTER TABLE reference DROP COLUMN license;
ALTER TABLE reference DROP COLUMN dataset;
