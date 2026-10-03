import 'plant_catalog_provenance.dart';

enum PlantKind { plant }

/// An explicitly registered plant part with its source identifier.
class PlantPart {
  PlantPart({
    required this.name,
    required this.sourceCode,
    required Iterable<SourceRecord> sources,
  }) : sources = List.unmodifiable(sources);

  final String name;
  final String sourceCode;

  /// Source rows linking the plant to this part and defining the part.
  final List<SourceRecord> sources;
}

/// Immutable catalog entry. Null optional fields mean unavailable, not
/// inferred or editorially filled content.
class Plant {
  Plant({
    required this.usdaPlantId,
    required this.editorialCommonName,
    required this.sourceScientificName,
    this.kind = PlantKind.plant,
    this.origin,
    this.description,
    this.identitySource,
    Iterable<PlantPart> parts = const [],
    Iterable<TraditionalUse> traditionalUses = const [],
    this.propertiesNotEvaluated = true,
  }) : parts = List.unmodifiable(parts),
       traditionalUses = List.unmodifiable(traditionalUses);

  /// Stable internal identity corresponding to the source FNFNUM.
  final int usdaPlantId;
  final String editorialCommonName;
  final String sourceScientificName;
  final PlantKind kind;
  final String? origin;
  final String? description;
  final SourceRecord? identitySource;
  final List<PlantPart> parts;
  final List<TraditionalUse> traditionalUses;
  final bool propertiesNotEvaluated;
}

/// Ordered, immutable catalog with unambiguous nullable ID lookup.
class PlantCatalog {
  PlantCatalog({required Iterable<Plant> plants, required this.provenance})
    : plants = List.unmodifiable(plants) {
    final ids = <int>{};
    for (final plant in this.plants) {
      if (!ids.add(plant.usdaPlantId)) {
        throw ArgumentError.value(
          plant.usdaPlantId,
          'plants',
          'Plant IDs must be unique',
        );
      }
    }
  }

  final List<Plant> plants;
  final PlantCatalogProvenance provenance;

  Plant? findById(int usdaPlantId) {
    for (final plant in plants) {
      if (plant.usdaPlantId == usdaPlantId) return plant;
    }
    return null;
  }
}
