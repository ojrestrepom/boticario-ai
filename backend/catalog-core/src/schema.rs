// @generated automatically by Diesel CLI.

diesel::table! {
    metadata (key) {
        key -> Text,
        value -> Text,
    }
}

diesel::table! {
    plant (id) {
        id -> Text,
        scientific_name -> Text,
        scientific_name_normalized -> Text,
        family -> Nullable<Text>,
        family_source_id -> Nullable<Text>,
    }
}

diesel::table! {
    plant_name (id) {
        id -> Integer,
        plant_id -> Text,
        text -> Text,
        kind -> Text,
        language -> Text,
        normalized -> Text,
    }
}

diesel::table! {
    plant_name_source (plant_name_id, source_id) {
        plant_name_id -> Integer,
        source_id -> Text,
    }
}

diesel::table! {
    plant_part (id) {
        id -> Integer,
        plant_id -> Text,
        label -> Text,
    }
}

diesel::table! {
    plant_part_source (plant_part_id, source_id) {
        plant_part_id -> Integer,
        source_id -> Text,
    }
}

diesel::table! {
    plant_source_id (plant_id, source_id) {
        plant_id -> Text,
        source_id -> Text,
        source_plant_id -> Text,
    }
}

diesel::table! {
    plant_use (id) {
        id -> Integer,
        plant_id -> Text,
        activity -> Text,
        language -> Text,
        reference_id -> Text,
    }
}

diesel::table! {
    plant_use_source (plant_use_id, source_id) {
        plant_use_id -> Integer,
        source_id -> Text,
    }
}

diesel::table! {
    reference (id) {
        id -> Text,
        citation -> Text,
    }
}

diesel::table! {
    reference_source (reference_id, source_id) {
        reference_id -> Text,
        source_id -> Text,
    }
}

diesel::table! {
    source (id) {
        id -> Text,
        name -> Text,
        version -> Text,
        license -> Text,
        citation -> Text,
        url -> Text,
        checksum -> Text,
    }
}

diesel::joinable!(plant -> source (family_source_id));
diesel::joinable!(plant_name -> plant (plant_id));
diesel::joinable!(plant_name_source -> plant_name (plant_name_id));
diesel::joinable!(plant_name_source -> source (source_id));
diesel::joinable!(plant_part -> plant (plant_id));
diesel::joinable!(plant_part_source -> plant_part (plant_part_id));
diesel::joinable!(plant_part_source -> source (source_id));
diesel::joinable!(plant_source_id -> plant (plant_id));
diesel::joinable!(plant_source_id -> source (source_id));
diesel::joinable!(plant_use -> plant (plant_id));
diesel::joinable!(plant_use -> reference (reference_id));
diesel::joinable!(plant_use_source -> plant_use (plant_use_id));
diesel::joinable!(plant_use_source -> source (source_id));
diesel::joinable!(reference_source -> reference (reference_id));
diesel::joinable!(reference_source -> source (source_id));

diesel::allow_tables_to_appear_in_same_query!(
    metadata,
    plant,
    plant_name,
    plant_name_source,
    plant_part,
    plant_part_source,
    plant_source_id,
    plant_use,
    plant_use_source,
    reference,
    reference_source,
    source,
);
