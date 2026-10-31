import 'dart:convert';

import 'package:flutter/services.dart';

class PlantSpecies {
  const PlantSpecies(this.classIndex, this.speciesId, this.scientificName);
  final int classIndex;
  final String speciesId;
  final String scientificName;
}

class PlantSpeciesMetadata {
  PlantSpeciesMetadata._(this.classes);
  final List<PlantSpecies> classes;
  static const classCount = 1081;

  static Future<PlantSpeciesMetadata> load({AssetBundle? bundle}) async {
    final assets = bundle ?? rootBundle;
    return PlantSpeciesMetadata.parse(
      await assets.loadString('assets/metadata/class_idx_to_species_id.json'),
      await assets.loadString(
        'assets/metadata/plantnet300K_species_id_2_name.json',
      ),
    );
  }

  factory PlantSpeciesMetadata.parse(String indicesJson, String namesJson) {
    final indices = jsonDecode(indicesJson);
    final names = jsonDecode(namesJson);
    if (indices is! Map ||
        names is! Map ||
        indices.length != classCount ||
        names.length != classCount) {
      throw const FormatException('Expected metadata for 1081 classes.');
    }
    final classes = <PlantSpecies>[];
    final speciesIds = <String>{};
    for (var index = 0; index < classCount; index++) {
      final id = indices['$index'];
      if ((id is! String && id is! int) || '$id'.trim().isEmpty) {
        throw FormatException('Invalid species ID at class $index.');
      }
      final name = names['$id'];
      if (name is! String || name.trim().isEmpty || !speciesIds.add('$id')) {
        throw FormatException('Missing name or duplicate species at $index.');
      }
      classes.add(PlantSpecies(index, '$id', name));
    }
    return PlantSpeciesMetadata._(List.unmodifiable(classes));
  }
}
