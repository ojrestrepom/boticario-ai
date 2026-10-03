/// A selector that identifies a source row or a set of related source rows.
class SourceRecord {
  SourceRecord({required this.table, required Map<String, Object?> selectors})
    : selectors = _immutableMap(selectors);

  final String table;
  final Map<String, Object?> selectors;
}

/// Bibliographic entry resolved from the source dataset.
class PlantReference {
  const PlantReference({
    required this.id,
    required this.citation,
    required this.source,
  });

  final String id;
  final String citation;

  /// Selector for the resolved REFERENCES row (including its source key).
  final SourceRecord source;
}

/// Provenance for a traditional-use row; selectors and bibliography are kept
/// together so a future importer can validate their relationship.
class TraditionalUse {
  TraditionalUse({
    required this.activity,
    required this.source,
    required Iterable<PlantReference> references,
  }) : references = List.unmodifiable(references);

  final String activity;
  final SourceRecord source;
  final List<PlantReference> references;
}

/// Provenance manifest for a packaged catalog snapshot.
class PlantCatalogProvenance {
  const PlantCatalogProvenance({
    required this.sourceName,
    required this.license,
    required this.version,
    required this.sourceUrl,
    required this.datasetId,
    required this.downloadUrl,
    required this.fileId,
    required this.fileName,
    required this.fileSizeBytes,
    required this.md5,
    required this.inspectedOn,
    required this.recommendedCitation,
  });

  final String sourceName;
  final String license;
  final String version;
  final String sourceUrl;
  final String datasetId;
  final String downloadUrl;
  final String fileId;
  final String fileName;
  final int fileSizeBytes;
  final String md5;

  /// Inspection date, not a claim about the dataset's coverage period.
  final DateTime inspectedOn;

  /// Citation text is distinct from the inspection date and file version.
  final String recommendedCitation;
}

Map<String, Object?> _immutableMap(Map<String, Object?> input) {
  final result = <String, Object?>{};
  for (final entry in input.entries) {
    result[entry.key] = _immutableValue(entry.value);
  }
  return Map.unmodifiable(result);
}

Object? _immutableValue(Object? value) {
  if (value == null || value is String || value is bool) return value;
  if (value is num) {
    if (value is double && !value.isFinite) {
      throw ArgumentError.value(value, 'selectors', 'Number must be finite');
    }
    return value;
  }
  if (value is Map) {
    final map = <String, Object?>{};
    for (final entry in value.entries) {
      if (entry.key is! String) {
        throw ArgumentError.value(
          entry.key,
          'selectors',
          'Map keys must be strings',
        );
      }
      map[entry.key as String] = _immutableValue(entry.value);
    }
    return Map<String, Object?>.unmodifiable(map);
  }
  if (value is List) {
    return List<Object?>.unmodifiable(value.map(_immutableValue));
  }
  throw ArgumentError.value(value, 'selectors', 'Value is not JSON-compatible');
}
