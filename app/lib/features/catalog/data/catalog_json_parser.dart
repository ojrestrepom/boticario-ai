import 'dart:convert';

import '../domain/catalog_plant.dart';
import '../domain/plant_summary.dart';
import 'catalog_client_exception.dart';

/// Strict parsers for the `/v1` responses described in `backend/openapi.json`.
/// Required fields must be present with the right type; unknown fields are
/// ignored and nothing is filled in with invented data.
PlantPage parsePlantPage(String body) {
  final json = _decodeObject(body, 'el listado');
  final items = _list(json, 'items', 'listado');
  return PlantPage(
    items: [
      for (var i = 0; i < items.length; i++)
        _summary(_asObject(items[i], 'items[$i]')),
    ],
    total: _int(json, 'total', 'listado'),
    limit: _int(json, 'limit', 'listado'),
    offset: _int(json, 'offset', 'listado'),
  );
}

Plant parsePlant(String body) {
  final json = _decodeObject(body, 'el detalle');
  const where = 'detalle';
  final names = _list(json, 'names', where);
  final parts = _list(json, 'parts', where);
  final uses = _list(json, 'uses', where);
  return Plant(
    id: _string(json, 'id', where),
    scientificName: _string(json, 'scientificName', where),
    family: _nullableString(json, 'family', where),
    names: [
      for (var i = 0; i < names.length; i++)
        _name(_asObject(names[i], 'names[$i]'), 'names[$i]'),
    ],
    parts: [
      for (var i = 0; i < parts.length; i++)
        _string(_asObject(parts[i], 'parts[$i]'), 'label', 'parts[$i]'),
    ],
    uses: [
      for (var i = 0; i < uses.length; i++)
        _use(_asObject(uses[i], 'uses[$i]'), 'uses[$i]'),
    ],
  );
}

PlantSummary _summary(Map<String, Object?> json) {
  final where = 'items';
  final names = _list(json, 'commonNames', where);
  return PlantSummary(
    id: _string(json, 'id', where),
    scientificName: _string(json, 'scientificName', where),
    commonNames: [
      for (var i = 0; i < names.length; i++)
        CommonName(
          text: _string(
            _asObject(names[i], 'commonNames[$i]'),
            'text',
            'commonNames[$i]',
          ),
          language: _string(
            _asObject(names[i], 'commonNames[$i]'),
            'language',
            'commonNames[$i]',
          ),
        ),
    ],
    family: _nullableString(json, 'family', where),
  );
}

PlantName _name(Map<String, Object?> json, String where) {
  final kind = _string(json, 'kind', where);
  return PlantName(
    text: _string(json, 'text', where),
    kind: switch (kind) {
      'scientific' => PlantNameKind.scientific,
      'common' => PlantNameKind.common,
      _ => throw _invalid('$where.kind tiene un valor desconocido: "$kind"'),
    },
    language: _string(json, 'language', where),
  );
}

PlantUse _use(Map<String, Object?> json, String where) {
  final reference = _asObject(json['reference'], '$where.reference');
  return PlantUse(
    activity: _string(json, 'activity', where),
    language: _string(json, 'language', where),
    reference: UseReference(
      id: _string(reference, 'id', '$where.reference'),
      citation: _string(reference, 'citation', '$where.reference'),
    ),
  );
}

CatalogClientException _invalid(String detail) => CatalogClientException(
  CatalogClientErrorKind.invalidResponse,
  'La respuesta del servidor no es válida: $detail.',
);

Map<String, Object?> _decodeObject(String body, String what) {
  final Object? decoded;
  try {
    decoded = jsonDecode(body);
  } on FormatException catch (error) {
    throw CatalogClientException(
      CatalogClientErrorKind.invalidResponse,
      'La respuesta del servidor no es válida: $what no es JSON.',
      cause: error,
    );
  }
  return _asObject(decoded, what);
}

Map<String, Object?> _asObject(Object? value, String where) {
  if (value is Map<String, Object?>) return value;
  throw _invalid('se esperaba un objeto en $where');
}

List<Object?> _list(Map<String, Object?> json, String key, String where) {
  final value = json[key];
  if (value is List<Object?>) return value;
  throw _invalid(
    value == null && !json.containsKey(key)
        ? 'falta el campo "$key" en $where'
        : 'el campo "$key" de $where debe ser una lista',
  );
}

String _string(Map<String, Object?> json, String key, String where) {
  final value = json[key];
  if (value is String) return value;
  throw _invalid(
    json.containsKey(key)
        ? 'el campo "$key" de $where debe ser texto'
        : 'falta el campo "$key" en $where',
  );
}

/// `family` is optional in the contract: absent and `null` both mean none.
String? _nullableString(Map<String, Object?> json, String key, String where) {
  final value = json[key];
  if (value == null || value is String) return value as String?;
  throw _invalid('el campo "$key" de $where debe ser texto o nulo');
}

int _int(Map<String, Object?> json, String key, String where) {
  final value = json[key];
  if (value is int) return value;
  throw _invalid(
    json.containsKey(key)
        ? 'el campo "$key" de $where debe ser un entero'
        : 'falta el campo "$key" en $where',
  );
}
