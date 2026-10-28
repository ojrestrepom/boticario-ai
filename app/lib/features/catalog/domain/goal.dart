import 'package:flutter/foundation.dart';

import 'plant_consolidated.dart';
import 'plant_summary.dart';

/// A subarea of a goal in `GET /v1/goals` (only visible ones come back).
@immutable
class GoalSubarea {
  const GoalSubarea({
    required this.id,
    required this.name,
    required this.plantCount,
  });

  final String id;
  final String name;
  final int plantCount;

  @override
  bool operator ==(Object other) =>
      other is GoalSubarea &&
      other.id == id &&
      other.name == name &&
      other.plantCount == plantCount;

  @override
  int get hashCode => Object.hash(id, name, plantCount);
}

/// A goal of `GET /v1/goals`, in the order the API presents it.
@immutable
class Goal {
  Goal({
    required this.id,
    required this.name,
    required this.plantCount,
    required List<GoalSubarea> subareas,
  }) : subareas = List.unmodifiable(subareas);

  final String id;
  final String name;
  final int plantCount;
  final List<GoalSubarea> subareas;

  bool get hasSubareas => subareas.isNotEmpty;

  @override
  bool operator ==(Object other) =>
      other is Goal &&
      other.id == id &&
      other.name == name &&
      other.plantCount == plantCount &&
      listEquals(other.subareas, subareas);

  @override
  int get hashCode =>
      Object.hash(id, name, plantCount, Object.hashAll(subareas));
}

/// The `goal` or `subarea` reference (`id` and `name`) of a goal page.
@immutable
class GoalRef {
  const GoalRef({required this.id, required this.name});

  final String id;
  final String name;

  @override
  bool operator ==(Object other) =>
      other is GoalRef && other.id == id && other.name == name;

  @override
  int get hashCode => Object.hash(id, name);
}

/// One plant of `GET /v1/goals/{goalId}/plants`. [areas] are the EMA areas as
/// stored (a value may join two areas with "; "): show them as they come.
/// [safetyLevel] is `null` without a level, even when [hasSafety] is true.
@immutable
class GoalPlant {
  GoalPlant({
    required this.id,
    required this.scientificName,
    required List<CommonName> commonNames,
    required List<String> areas,
    required this.hasSafety,
    this.family,
    this.displayName,
    this.safetyLevel,
    this.image,
  }) : commonNames = List.unmodifiable(commonNames),
       areas = List.unmodifiable(areas);

  final String id;
  final String scientificName;
  final List<CommonName> commonNames;
  final String? family;

  /// Display name from the API; the display-name rule applies without it.
  final String? displayName;
  final List<String> areas;
  final SafetyLevel? safetyLevel;
  final bool hasSafety;
  final PlantImage? image;

  DisplayNames get displayNames => displayNamesFor(
    scientificName: scientificName,
    displayName: displayName,
    commonNames: [for (final name in commonNames) name.text],
  );

  String get primaryName => displayNames.primary;
  String? get secondaryName => displayNames.secondary;

  @override
  bool operator ==(Object other) =>
      other is GoalPlant &&
      other.id == id &&
      other.scientificName == scientificName &&
      other.family == family &&
      other.displayName == displayName &&
      other.safetyLevel == safetyLevel &&
      other.hasSafety == hasSafety &&
      other.image == image &&
      listEquals(other.commonNames, commonNames) &&
      listEquals(other.areas, areas);

  @override
  int get hashCode => Object.hash(
    id,
    scientificName,
    family,
    displayName,
    safetyLevel,
    hasSafety,
    image,
    Object.hashAll(commonNames),
    Object.hashAll(areas),
  );
}

/// A page of `GET /v1/goals/{goalId}/plants`.
@immutable
class GoalPlantPage {
  GoalPlantPage({
    required this.goal,
    required this.subarea,
    required List<GoalPlant> items,
    required this.total,
    required this.limit,
    required this.offset,
  }) : items = List.unmodifiable(items);

  final GoalRef goal;
  final GoalRef? subarea;
  final List<GoalPlant> items;
  final int total;
  final int limit;
  final int offset;

  @override
  bool operator ==(Object other) =>
      other is GoalPlantPage &&
      other.goal == goal &&
      other.subarea == subarea &&
      other.total == total &&
      other.limit == limit &&
      other.offset == offset &&
      listEquals(other.items, items);

  @override
  int get hashCode =>
      Object.hash(goal, subarea, total, limit, offset, Object.hashAll(items));
}
