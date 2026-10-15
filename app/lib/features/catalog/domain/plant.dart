import 'package:flutter/foundation.dart';

import 'plant_summary.dart';

enum PlantNameKind { scientific, common }

@immutable
class PlantName {
  const PlantName({
    required this.text,
    required this.kind,
    required this.language,
  });

  final String text;
  final PlantNameKind kind;
  final String language;

  @override
  bool operator ==(Object other) =>
      other is PlantName &&
      other.text == text &&
      other.kind == kind &&
      other.language == language;

  @override
  int get hashCode => Object.hash(text, kind, language);
}

@immutable
class UseReference {
  const UseReference({required this.id, required this.citation});

  final String id;
  final String citation;

  @override
  bool operator ==(Object other) =>
      other is UseReference && other.id == id && other.citation == citation;

  @override
  int get hashCode => Object.hash(id, citation);
}

@immutable
class PlantUse {
  const PlantUse({
    required this.activity,
    required this.language,
    required this.reference,
  });

  final String activity;
  final String language;
  final UseReference reference;

  @override
  bool operator ==(Object other) =>
      other is PlantUse &&
      other.activity == activity &&
      other.language == language &&
      other.reference == reference;

  @override
  int get hashCode => Object.hash(activity, language, reference);
}

/// Detail of `GET /v1/plants/{id}`.
@immutable
class Plant {
  Plant({
    required this.id,
    required this.scientificName,
    required this.family,
    required List<PlantName> names,
    required List<String> parts,
    required List<PlantUse> uses,
  }) : names = List.unmodifiable(names),
       parts = List.unmodifiable(parts),
       uses = List.unmodifiable(uses);

  final String id;
  final String scientificName;
  final String? family;
  final List<PlantName> names;

  /// Part labels, in the order the API sent them.
  final List<String> parts;
  final List<PlantUse> uses;

  List<PlantName> get commonNames => [
    for (final name in names)
      if (name.kind == PlantNameKind.common) name,
  ];

  DisplayNames get displayNames => displayNamesFor(
    scientificName: scientificName,
    commonNames: [for (final name in commonNames) name.text],
  );

  String get primaryName => displayNames.primary;
  String? get secondaryName => displayNames.secondary;

  @override
  bool operator ==(Object other) =>
      other is Plant &&
      other.id == id &&
      other.scientificName == scientificName &&
      other.family == family &&
      listEquals(other.names, names) &&
      listEquals(other.parts, parts) &&
      listEquals(other.uses, uses);

  @override
  int get hashCode => Object.hash(
    id,
    scientificName,
    family,
    Object.hashAll(names),
    Object.hashAll(parts),
    Object.hashAll(uses),
  );
}
