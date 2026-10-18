import 'dart:convert';

import 'package:flutter/services.dart';

import '../domain/plant.dart';
import '../domain/plant_catalog_provenance.dart';

const plantCatalogAssetPath = 'assets/data/plant_catalog.json';

typedef PlantCatalogAssetLoader = Future<String> Function(String assetPath);

/// A safe, user-displayable catalog loading/validation failure.
class PlantCatalogLoadException implements Exception {
  const PlantCatalogLoadException(this.message);

  final String message;

  @override
  String toString() => message;
}

class PlantCatalogAssetDataSource {
  PlantCatalogAssetDataSource({PlantCatalogAssetLoader? loadAsset})
    : _loadAsset = loadAsset ?? rootBundle.loadString;

  final PlantCatalogAssetLoader _loadAsset;

  Future<PlantCatalog> load() async {
    try {
      return parse(await _loadAsset(plantCatalogAssetPath));
    } on PlantCatalogLoadException {
      rethrow;
    } catch (_) {
      throw const PlantCatalogLoadException(
        'No se pudo cargar el catálogo local. Inténtalo de nuevo.',
      );
    }
  }

  /// Parses and validates one schema-versioned catalog snapshot.
  static PlantCatalog parse(String json) {
    late final Object? decoded;
    try {
      decoded = jsonDecode(json);
    } on FormatException {
      throw const PlantCatalogLoadException(
        'El catálogo local no tiene un formato JSON válido.',
      );
    }
    final root = _object(decoded, 'catálogo');
    final version = root['schemaVersion'];
    if (version is! int || version != 1) {
      throw const PlantCatalogLoadException(
        'La versión del catálogo local no es compatible.',
      );
    }
    final provenance = _provenance(_object(root['provenance'], 'procedencia'));
    final referenceList = _array(root['references'], 'referencias');
    final references = <String, PlantReference>{};
    for (var i = 0; i < referenceList.length; i++) {
      final path = 'referencias[$i]';
      final item = _object(referenceList[i], path);
      final id = _string(item['id'], '$path.id');
      final citation = _string(item['citation'], '$path.citation');
      final source = _source(item['source'], '$path.source');
      final selectors = source.selectors;
      if (source.table != 'REFERENCES' ||
          selectors['REFERENCE'] != id ||
          selectors['LONGREF'] != citation) {
        _invalid(path, 'no coincide con su selector bibliográfico');
      }
      if (references.containsKey(id)) {
        _invalid(path, 'ID bibliográfico duplicado');
      }
      references[id] = PlantReference(
        id: id,
        citation: citation,
        source: source,
      );
    }
    final plants = <Plant>[];
    final ids = <int>{};
    final plantList = _array(root['plants'], 'plantas');
    for (var i = 0; i < plantList.length; i++) {
      final path = 'plantas[$i]';
      final item = _object(plantList[i], path);
      final id = _positiveInt(item['usdaPlantId'], '$path.usdaPlantId');
      if (!ids.add(id)) {
        _invalid(path, 'ID de planta duplicado');
      }
      final scientificName = _string(
        item['sourceScientificName'],
        '$path.sourceScientificName',
      );
      final identity = _source(item['identitySource'], '$path.identitySource');
      final identitySelectors = identity.selectors;
      if (identity.table != 'FNFTAX' ||
          identitySelectors['FNFNUM'] != id ||
          identitySelectors['TAXON'] != scientificName) {
        _invalid(path, 'la identidad fuente no coincide con la planta');
      }
      _string(identitySelectors['GENUS'], '$path.identitySource.GENUS');
      _string(identitySelectors['SPECIES'], '$path.identitySource.SPECIES');
      if (identitySelectors.containsKey('SUBSPECIES')) {
        _string(
          identitySelectors['SUBSPECIES'],
          '$path.identitySource.SUBSPECIES',
        );
      }
      final kind = _string(item['kind'], '$path.kind');
      if (kind != 'plant') {
        _invalid('$path.kind', 'solo se admite plant');
      }
      final origin = _nullableString(item['origin'], '$path.origin');
      final description = _nullableString(
        item['description'],
        '$path.description',
      );
      final partList = _array(item['parts'], '$path.parts');
      final parts = <PlantPart>[];
      for (var j = 0; j < partList.length; j++) {
        final partPath = '$path.parts[$j]';
        final part = _object(partList[j], partPath);
        final name = _string(part['name'], '$partPath.name');
        final code = _string(part['sourceCode'], '$partPath.sourceCode');
        final sources = _array(
          part['sources'],
          '$partPath.sources',
        ).map((v) => _source(v, '$partPath.sources')).toList();
        if (sources.length != 2 ||
            sources[0].table != 'FARMACY_NEW' ||
            sources[1].table != 'PARTS' ||
            sources[0].selectors['FNFNUM'] != id ||
            sources[0].selectors['PPCO'] != code ||
            sources[1].selectors['PPCO'] != code ||
            sources[1].selectors['PPNA'] != name) {
          _invalid(
            partPath,
            'las fuentes de la parte no corresponden a la planta',
          );
        }
        parts.add(PlantPart(name: name, sourceCode: code, sources: sources));
      }
      final propertiesNotEvaluated = item['propertiesNotEvaluated'];
      if (propertiesNotEvaluated != true) {
        _invalid('$path.propertiesNotEvaluated', 'debe ser true');
      }
      final useList = _array(item['traditionalUses'], '$path.traditionalUses');
      final uses = <TraditionalUse>[];
      for (var j = 0; j < useList.length; j++) {
        final usePath = '$path.traditionalUses[$j]';
        final use = _object(useList[j], usePath);
        final activity = _string(use['activity'], '$usePath.activity');
        final source = _source(use['source'], '$usePath.source');
        final selectors = source.selectors;
        final genus = _string(
          identitySelectors['GENUS'],
          '$path.identitySource.GENUS',
        );
        final species = _string(
          identitySelectors['SPECIES'],
          '$path.identitySource.SPECIES',
        );
        if (source.table != 'ETHNOBOT' ||
            selectors['GENUS'] != genus ||
            selectors['SPECIES'] != species ||
            selectors['TAXON'] != scientificName ||
            selectors['ACTIVITY'] != activity) {
          _invalid(
            usePath,
            'la identidad o actividad fuente no coincide con la planta',
          );
        }
        _string(selectors['ETHNO'], '$usePath.source.ETHNO');
        final referenceKey = _string(
          selectors['REFERENCE'],
          '$usePath.source.REFERENCE',
        );
        final referenceIds = _array(
          use['referenceIds'],
          '$usePath.referenceIds',
        );
        if (referenceIds.isEmpty) {
          _invalid('$usePath.referenceIds', 'no puede estar vacío');
        }
        final unique = <String>{};
        final resolved = <PlantReference>[];
        for (var k = 0; k < referenceIds.length; k++) {
          final refId = _string(referenceIds[k], '$usePath.referenceIds[$k]');
          if (!unique.add(refId)) {
            _invalid('$usePath.referenceIds', 'contiene IDs duplicados');
          }
          final reference = references[refId];
          if (reference == null) {
            _invalid(
              '$usePath.referenceIds',
              'incluye una referencia no resuelta',
            );
          }
          resolved.add(reference);
        }
        if (unique.length != 1 || !unique.contains(referenceKey)) {
          _invalid(usePath, 'la referencia no corresponde a la fila fuente');
        }
        uses.add(
          TraditionalUse(
            activity: activity,
            source: source,
            references: resolved,
          ),
        );
      }
      plants.add(
        Plant(
          usdaPlantId: id,
          editorialCommonName: _string(
            item['editorialCommonName'],
            '$path.editorialCommonName',
          ),
          sourceScientificName: scientificName,
          origin: origin,
          description: description,
          identitySource: identity,
          parts: parts,
          traditionalUses: uses,
          propertiesNotEvaluated: true,
        ),
      );
    }
    final usedReferences = plants
        .expand((plant) => plant.traditionalUses)
        .expand((use) => use.references)
        .map((reference) => reference.id)
        .toSet();
    if (usedReferences.length != references.length ||
        references.keys.any((id) => !usedReferences.contains(id))) {
      _invalid('referencias', 'contiene referencias huérfanas');
    }
    return PlantCatalog(plants: plants, provenance: provenance);
  }
}

PlantCatalogProvenance _provenance(Map<String, dynamic> value) {
  final inspected = _string(value['inspectedOn'], 'procedencia.inspectedOn');
  final match = RegExp(r'^(\d{4})-(\d{2})-(\d{2})$').firstMatch(inspected);
  if (match == null) {
    _invalid('procedencia.inspectedOn', 'debe ser una fecha válida YYYY-MM-DD');
  }
  final year = int.parse(match.group(1)!);
  final month = int.parse(match.group(2)!);
  final day = int.parse(match.group(3)!);
  final date = DateTime.utc(year, month, day);
  if (date.year != year || date.month != month || date.day != day) {
    _invalid('procedencia.inspectedOn', 'debe ser una fecha válida YYYY-MM-DD');
  }
  final sourceUrl = _httpUrl(value['sourceUrl'], 'procedencia.sourceUrl');
  final downloadUrl = _httpUrl(value['downloadUrl'], 'procedencia.downloadUrl');
  final md5 = _string(value['md5'], 'procedencia.md5');
  if (!RegExp(r'^[0-9a-fA-F]{32}$').hasMatch(md5)) {
    _invalid('procedencia.md5', 'debe ser MD5 hexadecimal');
  }
  return PlantCatalogProvenance(
    sourceName: _string(value['sourceName'], 'procedencia.sourceName'),
    license: _string(value['license'], 'procedencia.license'),
    version: _string(value['version'], 'procedencia.version'),
    sourceUrl: sourceUrl,
    datasetId: _string(value['datasetId'], 'procedencia.datasetId'),
    downloadUrl: downloadUrl,
    fileId: _string(value['fileId'], 'procedencia.fileId'),
    fileName: _string(value['fileName'], 'procedencia.fileName'),
    fileSizeBytes: _positiveInt(
      value['fileSizeBytes'],
      'procedencia.fileSizeBytes',
    ),
    md5: md5,
    inspectedOn: date,
    recommendedCitation: _string(
      value['recommendedCitation'],
      'procedencia.recommendedCitation',
    ),
  );
}

SourceRecord _source(Object? value, String path) {
  final source = _object(value, path);
  final selectors = _object(source['selectors'], '$path.selectors');
  try {
    return SourceRecord(
      table: _string(source['table'], '$path.table'),
      selectors: selectors,
    );
  } on ArgumentError {
    _invalid(path, 'contiene selectores no válidos');
  }
}

Map<String, dynamic> _object(Object? value, String path) {
  if (value is! Map) {
    _invalid(path, 'debe ser un objeto');
  }
  for (final key in value.keys) {
    if (key is! String) _invalid(path, 'contiene una clave inválida');
  }
  return Map<String, dynamic>.from(value);
}

List<dynamic> _array(Object? value, String path) {
  if (value is! List) {
    _invalid(path, 'debe ser una lista');
  }
  return value;
}

String _string(Object? value, String path) {
  if (value is! String || value.trim().isEmpty) {
    _invalid(path, 'debe ser texto no vacío');
  }
  return value;
}

String? _nullableString(Object? value, String path) =>
    value == null ? null : _string(value, path);

int _positiveInt(Object? value, String path) {
  if (value is! int || value <= 0) {
    _invalid(path, 'debe ser un entero positivo');
  }
  return value;
}

String _httpUrl(Object? value, String path) {
  final text = _string(value, path);
  final uri = Uri.tryParse(text);
  if (uri == null ||
      !uri.hasAuthority ||
      uri.host.isEmpty ||
      (uri.scheme != 'http' && uri.scheme != 'https')) {
    _invalid(path, 'debe ser una URL HTTP o HTTPS');
  }
  return text;
}

Never _invalid(String path, String reason) => throw PlantCatalogLoadException(
  'Catálogo local inválido en $path: $reason.',
);
