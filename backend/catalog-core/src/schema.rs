// @generated automatically by Diesel CLI.

diesel::table! {
    goal (id) {
        id -> Text,
        label -> Text,
        position -> Integer,
    }
}

diesel::table! {
    goal_subarea (id) {
        id -> Text,
        goal_id -> Text,
        label -> Text,
        position -> Integer,
    }
}

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
    plant_alias (alias) {
        alias -> Text,
        plant_id -> Text,
    }
}

diesel::table! {
    plant_goal (id) {
        id -> Integer,
        plant_id -> Text,
        goal_id -> Text,
        subarea_id -> Nullable<Text>,
        position -> Integer,
        area -> Text,
        evidence -> Text,
        pending_review -> Bool,
    }
}

diesel::table! {
    plant_goal_ref (plant_goal_id, reference_id) {
        plant_goal_id -> Integer,
        reference_id -> Text,
    }
}

diesel::table! {
    plant_image (plant_id) {
        plant_id -> Text,
        url -> Text,
        page_url -> Text,
        author -> Nullable<Text>,
        license -> Text,
        license_url -> Nullable<Text>,
        attribution_required -> Bool,
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
    plant_profile (plant_id) {
        plant_id -> Text,
        display_name -> Nullable<Text>,
        authors -> Nullable<Text>,
        origin -> Nullable<Text>,
        description -> Nullable<Text>,
        oil_type -> Nullable<Text>,
        record_version -> Integer,
        bundle_hash -> Text,
        prompt_version -> Integer,
    }
}

diesel::table! {
    plant_profile_ref (plant_id, field, reference_id) {
        plant_id -> Text,
        field -> Text,
        reference_id -> Text,
    }
}

diesel::table! {
    plant_review_flag (id) {
        id -> Integer,
        plant_id -> Text,
        code -> Text,
        target -> Text,
        message -> Text,
    }
}

diesel::table! {
    plant_safety (plant_id) {
        plant_id -> Text,
        level -> Nullable<Text>,
        text -> Text,
    }
}

diesel::table! {
    plant_safety_ref (plant_id, reference_id) {
        plant_id -> Text,
        reference_id -> Text,
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
    plant_use_group (id) {
        id -> Integer,
        plant_id -> Text,
        position -> Integer,
        activity -> Text,
        activity_source -> Text,
        n -> Integer,
        countries -> Text,
        pending_review -> Bool,
    }
}

diesel::table! {
    plant_use_group_ref (use_group_id, key) {
        use_group_id -> Integer,
        key -> Text,
        position -> Integer,
        text -> Text,
        resolved -> Bool,
        reference_id -> Nullable<Text>,
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
        dataset -> Nullable<Text>,
        license -> Nullable<Text>,
        url -> Nullable<Text>,
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

diesel::joinable!(goal_subarea -> goal (goal_id));
diesel::joinable!(plant -> source (family_source_id));
diesel::joinable!(plant_alias -> plant (plant_id));
diesel::joinable!(plant_goal -> goal (goal_id));
diesel::joinable!(plant_goal -> plant (plant_id));
diesel::joinable!(plant_goal_ref -> plant_goal (plant_goal_id));
diesel::joinable!(plant_goal_ref -> reference (reference_id));
diesel::joinable!(plant_image -> plant (plant_id));
diesel::joinable!(plant_name -> plant (plant_id));
diesel::joinable!(plant_name_source -> plant_name (plant_name_id));
diesel::joinable!(plant_name_source -> source (source_id));
diesel::joinable!(plant_part -> plant (plant_id));
diesel::joinable!(plant_part_source -> plant_part (plant_part_id));
diesel::joinable!(plant_part_source -> source (source_id));
diesel::joinable!(plant_profile -> plant (plant_id));
diesel::joinable!(plant_profile_ref -> plant (plant_id));
diesel::joinable!(plant_profile_ref -> reference (reference_id));
diesel::joinable!(plant_review_flag -> plant (plant_id));
diesel::joinable!(plant_safety -> plant (plant_id));
diesel::joinable!(plant_safety_ref -> plant_safety (plant_id));
diesel::joinable!(plant_safety_ref -> reference (reference_id));
diesel::joinable!(plant_source_id -> plant (plant_id));
diesel::joinable!(plant_source_id -> source (source_id));
diesel::joinable!(plant_use -> plant (plant_id));
diesel::joinable!(plant_use -> reference (reference_id));
diesel::joinable!(plant_use_group -> plant (plant_id));
diesel::joinable!(plant_use_group_ref -> plant_use_group (use_group_id));
diesel::joinable!(plant_use_group_ref -> reference (reference_id));
diesel::joinable!(plant_use_source -> plant_use (plant_use_id));
diesel::joinable!(plant_use_source -> source (source_id));
diesel::joinable!(reference_source -> reference (reference_id));
diesel::joinable!(reference_source -> source (source_id));

diesel::allow_tables_to_appear_in_same_query!(
    goal,
    goal_subarea,
    metadata,
    plant,
    plant_alias,
    plant_goal,
    plant_goal_ref,
    plant_image,
    plant_name,
    plant_name_source,
    plant_part,
    plant_part_source,
    plant_profile,
    plant_profile_ref,
    plant_review_flag,
    plant_safety,
    plant_safety_ref,
    plant_source_id,
    plant_use,
    plant_use_group,
    plant_use_group_ref,
    plant_use_source,
    reference,
    reference_source,
    source,
);
