import 'package:flutter/foundation.dart';

/// A citation attached to a use group, a goal or the precautions. A reference
/// the seed could not tie to a work has no [id] and `resolved == false`, and
/// its [citation] reads `<key> (sin resolver)` so the UI can dim it.
@immutable
class CitedReference {
  const CitedReference({
    required this.id,
    required this.citation,
    required this.resolved,
  });

  final String? id;
  final String citation;
  final bool resolved;

  @override
  bool operator ==(Object other) =>
      other is CitedReference &&
      other.id == id &&
      other.citation == citation &&
      other.resolved == resolved;

  @override
  int get hashCode => Object.hash(id, citation, resolved);
}

/// Oil of the plant (`Esencial` for now).
@immutable
class PlantOil {
  const PlantOil({required this.type});

  final String type;

  @override
  bool operator ==(Object other) => other is PlantOil && other.type == type;

  @override
  int get hashCode => type.hashCode;
}

/// Traditional-use group: one activity with its record count, countries and
/// every citation.
@immutable
class UseGroup {
  UseGroup({
    required this.activity,
    required this.activitySource,
    required this.count,
    required List<String> countries,
    required List<CitedReference> references,
  }) : countries = List.unmodifiable(countries),
       references = List.unmodifiable(references);

  final String activity;
  final String? activitySource;
  final int count;
  final List<String> countries;
  final List<CitedReference> references;

  @override
  bool operator ==(Object other) =>
      other is UseGroup &&
      other.activity == activity &&
      other.activitySource == activitySource &&
      other.count == count &&
      listEquals(other.countries, countries) &&
      listEquals(other.references, references);

  @override
  int get hashCode => Object.hash(
    activity,
    activitySource,
    count,
    Object.hashAll(countries),
    Object.hashAll(references),
  );
}

/// An EMA goal registered for the plant (a classification, not an indication).
@immutable
class PlantGoal {
  PlantGoal({
    required this.id,
    required this.name,
    required this.subarea,
    required this.area,
    required this.evidence,
    required List<CitedReference> references,
  }) : references = List.unmodifiable(references);

  final String id;
  final String name;
  final String? subarea;
  final String area;
  final String evidence;
  final List<CitedReference> references;

  @override
  bool operator ==(Object other) =>
      other is PlantGoal &&
      other.id == id &&
      other.name == name &&
      other.subarea == subarea &&
      other.area == area &&
      other.evidence == evidence &&
      listEquals(other.references, references);

  @override
  int get hashCode => Object.hash(
    id,
    name,
    subarea,
    area,
    evidence,
    Object.hashAll(references),
  );
}

enum SafetyLevel { high, medium, low }

/// Precautions of the plant. A `null` [level] is valid: the sources carry
/// warnings but none sets a level.
@immutable
class PlantSafety {
  PlantSafety({
    required this.level,
    required this.text,
    required List<CitedReference> references,
  }) : references = List.unmodifiable(references);

  final SafetyLevel? level;
  final String text;
  final List<CitedReference> references;

  @override
  bool operator ==(Object other) =>
      other is PlantSafety &&
      other.level == level &&
      other.text == text &&
      listEquals(other.references, references);

  @override
  int get hashCode => Object.hash(level, text, Object.hashAll(references));
}

/// Image data with its attribution. The API never serves the bytes.
@immutable
class PlantImage {
  const PlantImage({
    required this.url,
    required this.pageUrl,
    required this.author,
    required this.license,
    required this.licenseUrl,
    required this.attributionRequired,
  });

  final String url;
  final String pageUrl;
  final String? author;
  final String license;
  final String? licenseUrl;
  final bool attributionRequired;

  @override
  bool operator ==(Object other) =>
      other is PlantImage &&
      other.url == url &&
      other.pageUrl == pageUrl &&
      other.author == author &&
      other.license == license &&
      other.licenseUrl == licenseUrl &&
      other.attributionRequired == attributionRequired;

  @override
  int get hashCode => Object.hash(
    url,
    pageUrl,
    author,
    license,
    licenseUrl,
    attributionRequired,
  );
}

/// A dataset that backs the plant data (plant level, not per field).
@immutable
class PlantCredit {
  const PlantCredit({
    required this.name,
    required this.license,
    required this.licenseUrl,
    required this.attribution,
    required this.url,
  });

  final String name;
  final String license;
  final String? licenseUrl;
  final String attribution;
  final String? url;

  @override
  bool operator ==(Object other) =>
      other is PlantCredit &&
      other.name == name &&
      other.license == license &&
      other.licenseUrl == licenseUrl &&
      other.attribution == attribution &&
      other.url == url;

  @override
  int get hashCode => Object.hash(name, license, licenseUrl, attribution, url);
}
