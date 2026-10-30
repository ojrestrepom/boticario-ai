import 'package:flutter/foundation.dart';

import 'plant_consolidated.dart';
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
    this.displayName,
    List<String> synonyms = const [],
    this.description,
    this.origin,
    this.oil,
    List<UseGroup>? useGroups,
    List<PlantGoal> goals = const [],
    this.safety,
    this.image,
    List<PlantCredit> credits = const [],
  }) : names = List.unmodifiable(names),
       parts = List.unmodifiable(parts),
       uses = List.unmodifiable(uses),
       synonyms = List.unmodifiable(synonyms),
       useGroups = List.unmodifiable(useGroups ?? deriveUseGroups(uses)),
       goals = List.unmodifiable(goals),
       credits = List.unmodifiable(credits);

  final String id;
  final String scientificName;
  final String? family;
  final List<PlantName> names;

  /// Part labels, in the order the API sent them.
  final List<String> parts;
  final List<PlantUse> uses;

  /// Display name from the API; `null` when the backend predates it.
  final String? displayName;
  final List<String> synonyms;
  final String? description;
  final String? origin;
  final PlantOil? oil;

  /// Traditional-use groups. When the response has none of its own they are
  /// derived from [uses], one per activity (older backend fallback).
  final List<UseGroup> useGroups;
  final List<PlantGoal> goals;

  /// `null` only when the sources have no precaution data at all.
  final PlantSafety? safety;
  final PlantImage? image;
  final List<PlantCredit> credits;

  List<PlantName> get commonNames => [
    for (final name in names)
      if (name.kind == PlantNameKind.common) name,
  ];

  DisplayNames get displayNames => displayNamesFor(
    scientificName: scientificName,
    displayName: displayName,
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
      listEquals(other.uses, uses) &&
      other.displayName == displayName &&
      listEquals(other.synonyms, synonyms) &&
      other.description == description &&
      other.origin == origin &&
      other.oil == oil &&
      listEquals(other.useGroups, useGroups) &&
      listEquals(other.goals, goals) &&
      other.safety == safety &&
      other.image == image &&
      listEquals(other.credits, credits);

  @override
  int get hashCode => Object.hash(
    id,
    scientificName,
    family,
    Object.hashAll(names),
    Object.hashAll(parts),
    Object.hashAll(uses),
    displayName,
    Object.hashAll(synonyms),
    description,
    origin,
    oil,
    Object.hashAll(useGroups),
    Object.hashAll(goals),
    safety,
    image,
    Object.hashAll(credits),
  );
}

/// Older-backend fallback: one group per activity, in the contract order
/// (`count` descending, then activity). Countries and source are unknown.
List<UseGroup> deriveUseGroups(List<PlantUse> uses) {
  final byActivity = <String, List<PlantUse>>{};
  for (final use in uses) {
    byActivity.putIfAbsent(use.activity, () => []).add(use);
  }
  final groups = [
    for (final entry in byActivity.entries)
      UseGroup(
        activity: entry.key,
        activitySource: null,
        count: entry.value.length,
        countries: const [],
        references: [
          for (final use in entry.value)
            CitedReference(
              id: use.reference.id,
              citation: use.reference.citation,
              resolved: true,
            ),
        ],
      ),
  ];
  groups.sort((a, b) {
    final byCount = b.count.compareTo(a.count);
    return byCount != 0 ? byCount : a.activity.compareTo(b.activity);
  });
  return groups;
}
