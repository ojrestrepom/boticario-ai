import 'package:flutter/foundation.dart';

/// Display names for a plant: [primary] is the first common name as the API
/// sent it (never translated) and [secondary] the scientific name. Without
/// common names the scientific name is primary and there is no secondary.
typedef DisplayNames = ({String primary, String? secondary});

DisplayNames displayNamesFor({
  required String scientificName,
  required List<String> commonNames,
}) {
  if (commonNames.isEmpty) {
    return (primary: scientificName, secondary: null);
  }
  return (primary: commonNames.first, secondary: scientificName);
}

/// A common name with the language tag the API reports (`en`, `und`, ...).
@immutable
class CommonName {
  const CommonName({required this.text, required this.language});

  final String text;
  final String language;

  @override
  bool operator ==(Object other) =>
      other is CommonName && other.text == text && other.language == language;

  @override
  int get hashCode => Object.hash(text, language);
}

/// One entry of `GET /v1/plants`.
@immutable
class PlantSummary {
  PlantSummary({
    required this.id,
    required this.scientificName,
    required List<CommonName> commonNames,
    this.family,
  }) : commonNames = List.unmodifiable(commonNames);

  final String id;
  final String scientificName;
  final List<CommonName> commonNames;
  final String? family;

  DisplayNames get displayNames => displayNamesFor(
    scientificName: scientificName,
    commonNames: [for (final name in commonNames) name.text],
  );

  String get primaryName => displayNames.primary;
  String? get secondaryName => displayNames.secondary;

  @override
  bool operator ==(Object other) =>
      other is PlantSummary &&
      other.id == id &&
      other.scientificName == scientificName &&
      other.family == family &&
      listEquals(other.commonNames, commonNames);

  @override
  int get hashCode =>
      Object.hash(id, scientificName, family, Object.hashAll(commonNames));
}

/// A page of `GET /v1/plants`.
@immutable
class PlantPage {
  PlantPage({
    required List<PlantSummary> items,
    required this.total,
    required this.limit,
    required this.offset,
  }) : items = List.unmodifiable(items);

  final List<PlantSummary> items;
  final int total;
  final int limit;
  final int offset;

  @override
  bool operator ==(Object other) =>
      other is PlantPage &&
      other.total == total &&
      other.limit == limit &&
      other.offset == offset &&
      listEquals(other.items, items);

  @override
  int get hashCode => Object.hash(total, limit, offset, Object.hashAll(items));
}
