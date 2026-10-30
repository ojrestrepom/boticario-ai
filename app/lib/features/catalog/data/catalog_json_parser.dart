import 'dart:convert';

import '../domain/goal.dart';
import '../domain/plant.dart';
import '../domain/plant_consolidated.dart';
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

List<Goal> parseGoals(String body) {
  final decoded = _decodeAny(body, 'el catálogo de objetivos');
  if (decoded is! List<Object?>) {
    throw _invalid('se esperaba una lista en el catálogo de objetivos');
  }
  return [
    for (var i = 0; i < decoded.length; i++)
      _goalEntry(_asObject(decoded[i], 'goals[$i]'), 'goals[$i]'),
  ];
}

Goal _goalEntry(Map<String, Object?> json, String where) {
  final subareas = _list(json, 'subareas', where);
  return Goal(
    id: _string(json, 'id', where),
    name: _string(json, 'name', where),
    plantCount: _int(json, 'plantCount', where),
    subareas: [
      for (var i = 0; i < subareas.length; i++)
        _subarea(
          _asObject(subareas[i], '$where.subareas[$i]'),
          '$where.subareas[$i]',
        ),
    ],
  );
}

GoalSubarea _subarea(Map<String, Object?> json, String where) => GoalSubarea(
  id: _string(json, 'id', where),
  name: _string(json, 'name', where),
  plantCount: _int(json, 'plantCount', where),
);

GoalPlantPage parseGoalPlantPage(String body) {
  final json = _decodeObject(body, 'las plantas del objetivo');
  const where = 'plantas del objetivo';
  final items = _list(json, 'items', where);
  if (!json.containsKey('subarea')) {
    throw _invalid('falta el campo "subarea" en $where');
  }
  return GoalPlantPage(
    goal: _goalRef(_asObject(json['goal'], 'goal'), 'goal'),
    subarea: _optionalObject(
      json,
      'subarea',
      where,
      (o) => _goalRef(o, 'subarea'),
    ),
    items: [
      for (var i = 0; i < items.length; i++)
        _goalPlant(_asObject(items[i], 'items[$i]'), 'items[$i]'),
    ],
    total: _int(json, 'total', where),
    limit: _int(json, 'limit', where),
    offset: _int(json, 'offset', where),
  );
}

GoalRef _goalRef(Map<String, Object?> json, String where) =>
    GoalRef(id: _string(json, 'id', where), name: _string(json, 'name', where));

GoalPlant _goalPlant(Map<String, Object?> json, String where) {
  final names = _list(json, 'commonNames', where);
  final areas = _list(json, 'areas', where);
  if (!json.containsKey('safetyLevel')) {
    throw _invalid('falta el campo "safetyLevel" en $where');
  }
  final level = _nullableString(json, 'safetyLevel', where);
  final safetyLevel = switch (level) {
    null => null,
    'alto' => SafetyLevel.high,
    'medio' => SafetyLevel.medium,
    'bajo' => SafetyLevel.low,
    _ => throw _invalid(
      '$where.safetyLevel tiene un valor desconocido: "$level"',
    ),
  };
  return GoalPlant(
    id: _string(json, 'id', where),
    scientificName: _string(json, 'scientificName', where),
    commonNames: [
      for (var i = 0; i < names.length; i++)
        CommonName(
          text: _string(
            _asObject(names[i], '$where.commonNames[$i]'),
            'text',
            '$where.commonNames[$i]',
          ),
          language: _string(
            names[i] as Map<String, Object?>,
            'language',
            '$where.commonNames[$i]',
          ),
        ),
    ],
    family: _nullableString(json, 'family', where),
    displayName: _nullableString(json, 'displayName', where),
    areas: [
      for (var i = 0; i < areas.length; i++)
        areas[i] is String
            ? areas[i] as String
            : throw _invalid('areas[$i] de $where debe ser texto'),
    ],
    safetyLevel: safetyLevel,
    // Absent (older backend): a level implies precautions, no level does not.
    hasSafety: json['hasSafety'] == null
        ? safetyLevel != null
        : _bool(json, 'hasSafety', where),
    image: _optionalObject(json, 'image', where, _image),
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
    displayName: _nullableString(json, 'displayName', where),
    synonyms: [
      for (final (i, value) in _optionalList(json, 'synonyms', where).indexed)
        value is String
            ? value
            : throw _invalid('synonyms[$i] de $where debe ser texto'),
    ],
    description: _nullableString(json, 'description', where),
    origin: _nullableString(json, 'origin', where),
    oil: _optionalObject(json, 'oil', where, (o) {
      return PlantOil(type: _string(o, 'type', 'oil'));
    }),
    // Absent (older backend) derives the groups from `uses`; present, even
    // empty, is the API's own answer.
    useGroups: json.containsKey('useGroups') && json['useGroups'] != null
        ? [
            for (final (i, v) in _list(json, 'useGroups', where).indexed)
              _useGroup(_asObject(v, 'useGroups[$i]'), 'useGroups[$i]'),
          ]
        : null,
    goals: [
      for (final (i, v) in _optionalList(json, 'goals', where).indexed)
        _goal(_asObject(v, 'goals[$i]'), 'goals[$i]'),
    ],
    safety: _optionalObject(json, 'safety', where, _safety),
    image: _optionalObject(json, 'image', where, _image),
    credits: [
      for (final (i, v) in _optionalList(json, 'credits', where).indexed)
        _credit(_asObject(v, 'credits[$i]'), 'credits[$i]'),
    ],
  );
}

UseGroup _useGroup(Map<String, Object?> json, String where) => UseGroup(
  activity: _string(json, 'activity', where),
  activitySource: _nullableString(json, 'activitySource', where),
  count: _int(json, 'count', where),
  countries: _stringList(json, 'countries', where),
  references: _references(json, where),
);

PlantGoal _goal(Map<String, Object?> json, String where) => PlantGoal(
  id: _string(json, 'id', where),
  name: _string(json, 'name', where),
  subarea: _nullableString(json, 'subarea', where),
  area: _string(json, 'area', where),
  evidence: _string(json, 'evidence', where),
  references: _references(json, where),
);

PlantSafety _safety(Map<String, Object?> json) {
  const where = 'safety';
  final level = _nullableString(json, 'level', where);
  return PlantSafety(
    level: switch (level) {
      null => null,
      'alto' => SafetyLevel.high,
      'medio' => SafetyLevel.medium,
      'bajo' => SafetyLevel.low,
      _ => throw _invalid('$where.level tiene un valor desconocido: "$level"'),
    },
    text: _string(json, 'text', where),
    references: _references(json, where),
  );
}

PlantImage _image(Map<String, Object?> json) {
  const where = 'image';
  return PlantImage(
    url: _string(json, 'url', where),
    pageUrl: _string(json, 'pageUrl', where),
    author: _nullableString(json, 'author', where),
    license: _string(json, 'license', where),
    licenseUrl: _nullableString(json, 'licenseUrl', where),
    attributionRequired: _bool(json, 'attributionRequired', where),
  );
}

PlantCredit _credit(Map<String, Object?> json, String where) => PlantCredit(
  name: _string(json, 'name', where),
  license: _string(json, 'license', where),
  licenseUrl: _nullableString(json, 'licenseUrl', where),
  attribution: _string(json, 'attribution', where),
  url: _nullableString(json, 'url', where),
);

/// `references` of a group, goal or safety: absent means none. A reference
/// without `resolved` counts as resolved only when it has an `id`.
List<CitedReference> _references(Map<String, Object?> json, String where) {
  return [
    for (final (i, v) in _optionalList(json, 'references', where).indexed)
      _reference(
        _asObject(v, '$where.references[$i]'),
        '$where.references[$i]',
      ),
  ];
}

CitedReference _reference(Map<String, Object?> json, String where) {
  final id = _nullableString(json, 'id', where);
  return CitedReference(
    id: id,
    citation: _string(json, 'citation', where),
    resolved: json['resolved'] == null && !json.containsKey('resolved')
        ? id != null
        : _bool(json, 'resolved', where),
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
    displayName: _nullableString(json, 'displayName', where),
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

Map<String, Object?> _decodeObject(String body, String what) =>
    _asObject(_decodeAny(body, what), what);

Object? _decodeAny(String body, String what) {
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
  return decoded;
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

bool _bool(Map<String, Object?> json, String key, String where) {
  final value = json[key];
  if (value is bool) return value;
  throw _invalid(
    json.containsKey(key)
        ? 'el campo "$key" de $where debe ser verdadero o falso'
        : 'falta el campo "$key" en $where',
  );
}

/// A list that older backends omit: absent and `null` mean empty.
List<Object?> _optionalList(
  Map<String, Object?> json,
  String key,
  String where,
) {
  final value = json[key];
  if (value == null) return const [];
  if (value is List<Object?>) return value;
  throw _invalid('el campo "$key" de $where debe ser una lista');
}

List<String> _stringList(Map<String, Object?> json, String key, String where) {
  return [
    for (final (i, v) in _optionalList(json, key, where).indexed)
      v is String ? v : throw _invalid('$key[$i] de $where debe ser texto'),
  ];
}

/// An object that older backends omit: absent and `null` mean none.
T? _optionalObject<T>(
  Map<String, Object?> json,
  String key,
  String where,
  T Function(Map<String, Object?>) build,
) {
  final value = json[key];
  if (value == null) return null;
  if (value is Map<String, Object?>) return build(value);
  throw _invalid('el campo "$key" de $where debe ser un objeto o nulo');
}
