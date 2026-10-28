// Fake catalog API for tests without network.
//
// Usage:
//
//   final api = FakeCatalogApi();
//   final container = ProviderContainer(
//     overrides: [httpClientProvider.overrideWithValue(api.client)],
//   );
//   // widget tests: ProviderScope(overrides: [...same...], child: ...)
//
// Routing (fixtures live in `test/fixtures/api/`, captured from the real API):
//   GET /v1/plants?...            -> `list_lavandula.json` when `q` is absent or
//                                    contains "lavandula"; otherwise an empty
//                                    page that echoes `limit` and `offset`.
//   GET /v1/plants/{id}           -> `plant_{id}.json` for the ids in
//                                    [FakeCatalogApi.plantIds]; any other id gets
//                                    404 `application/problem+json`.
//   GET /v1/goals                 -> [FakeCatalogApi.goals] (synthetic: the six
//                                    goals of the seed with ids, names, order
//                                    and subareas; real fixtures are task 3.3).
//   GET /v1/goals/{id}/plants     -> a synthetic one-plant page for a goal of
//                                    [FakeCatalogApi.goals] (`subarea` must
//                                    belong to it, else 400); other ids 404.
//   anything else                 -> 404 (the app must not call other routes).
//
// Failures: set [FakeCatalogApi.failure] (and back to [FakeApiFailure.none] to
// let a retry succeed). `timeout` never answers, so the request ends only when
// the repository's 10 s timeout fires: use `tester.pump(Duration(seconds: 11))`
// or `fakeAsync` and `elapse`.
//
// With `requiredToken` the fake answers 401 unless the exact Bearer header is
// sent; `FakeApiFailure.unauthorized` always answers 401.
//
// [FakeCatalogApi.requests] records every request so tests can assert that
// only the two allowed endpoints are used, with `Accept: application/json`.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

enum FakeApiFailure { none, serverError, timeout, connection, unauthorized }

/// Fictitious API token for tests. It is not a secret and no backend accepts it.
const testApiToken = 'test-token-not-a-secret-000000000000';

const _jsonHeaders = {'content-type': 'application/json; charset=utf-8'};
const _problemHeaders = {
  'content-type': 'application/problem+json; charset=utf-8',
};

/// Reads a fixture from `test/fixtures/api/` (tests run from `app/`).
String apiFixture(String name) =>
    File('test/fixtures/api/$name').readAsStringSync();

class FakeCatalogApi {
  FakeCatalogApi({
    this.failure = FakeApiFailure.none,
    this.requiredToken,
    this.listFixture = 'list_lavandula.json',
    this.detailFixtures = const {},
    List<Map<String, Object?>>? goals,
  }) : goals = goals ?? syntheticGoals() {
    client = MockClient(_handle);
  }

  /// Fixture served by the list when `q` is absent or contains "lavandula".
  final String listFixture;

  /// Detail fixtures by plant id, taking precedence over `plant_{id}.json`.
  /// Used to serve real responses of the consolidated backend
  /// (`consolidated_*.json`).
  final Map<String, String> detailFixtures;

  /// Ids that have a detail fixture.
  static const plantIds = [
    'lavandula-angustifolia',
    'rosmarinus-officinalis',
    'abies-spectabilis',
    'abies-sachalinensis',
    'chondrus-crispus',
  ];

  /// Body of `GET /v1/goals`; tests may replace it before the request.
  List<Map<String, Object?>> goals;

  FakeApiFailure failure;

  /// When set, any request without exactly `Authorization: Bearer <token>`
  /// gets 401, like the real API.
  final String? requiredToken;
  late final http.Client client;
  final List<http.BaseRequest> requests = [];

  Future<http.Response> _handle(http.Request request) async {
    requests.add(request);
    final token = requiredToken;
    if (token != null && request.headers['Authorization'] != 'Bearer $token') {
      return _unauthorized();
    }
    switch (failure) {
      case FakeApiFailure.none:
        break;
      case FakeApiFailure.serverError:
        return http.Response(
          '{"type":"about:blank","title":"Internal Server Error","status":500}',
          500,
          headers: _problemHeaders,
        );
      case FakeApiFailure.unauthorized:
        return _unauthorized();
      case FakeApiFailure.timeout:
        return Completer<http.Response>().future;
      case FakeApiFailure.connection:
        throw const SocketException('Connection refused');
    }
    final segments = request.url.pathSegments;
    if (request.method == 'GET' &&
        segments.length == 2 &&
        segments[0] == 'v1' &&
        segments[1] == 'plants') {
      return _list(request.url.queryParameters);
    }
    if (request.method == 'GET' &&
        segments.length == 2 &&
        segments[0] == 'v1' &&
        segments[1] == 'goals') {
      return http.Response(jsonEncode(goals), 200, headers: _jsonHeaders);
    }
    if (request.method == 'GET' &&
        segments.length == 4 &&
        segments[0] == 'v1' &&
        segments[1] == 'goals' &&
        segments[3] == 'plants') {
      final page = _goalPage(segments[2], request.url.queryParameters);
      if (page != null) return page;
    }
    if (request.method == 'GET' &&
        segments.length == 3 &&
        segments[0] == 'v1' &&
        segments[1] == 'plants') {
      final id = segments[2];
      final override = detailFixtures[id];
      if (override != null) {
        return http.Response.bytes(
          utf8.encode(apiFixture(override)),
          200,
          headers: _jsonHeaders,
        );
      }
      if (plantIds.contains(id)) {
        return http.Response.bytes(
          utf8.encode(apiFixture('plant_$id.json')),
          200,
          headers: _jsonHeaders,
        );
      }
    }
    return http.Response.bytes(
      utf8.encode(apiFixture('notfound.json')),
      404,
      headers: _problemHeaders,
    );
  }

  http.Response _unauthorized() => http.Response(
    '{"type":"about:blank","title":"Unauthorized","status":401}',
    401,
    headers: _problemHeaders,
  );

  http.Response? _goalPage(String goalId, Map<String, String> query) {
    final goal = goals.where((g) => g['id'] == goalId).firstOrNull;
    if (goal == null) return null;
    final subareaId = query['subarea'];
    Map<String, Object?>? subarea;
    if (subareaId != null) {
      subarea = (goal['subareas']! as List<Object?>)
          .cast<Map<String, Object?>>()
          .where((s) => s['id'] == subareaId)
          .firstOrNull;
      if (subarea == null) {
        return http.Response(
          '{"type":"about:blank","title":"Bad Request","status":400}',
          400,
          headers: _problemHeaders,
        );
      }
    }
    return http.Response(
      jsonEncode({
        'goal': {'id': goal['id'], 'name': goal['name']},
        'subarea': subarea == null
            ? null
            : {'id': subarea['id'], 'name': subarea['name']},
        'items': [
          {
            'id': 'lavandula-angustifolia',
            'displayName': 'Lavanda',
            'scientificName': 'Lavandula angustifolia',
            'commonNames': [
              {'text': 'Lavanda', 'language': 'es'},
            ],
            'family': 'Lamiaceae',
            'areas': ['Estrés mental y trastornos del ánimo'],
            'safetyLevel': 'bajo',
            'hasSafety': true,
            'image': null,
          },
        ],
        'total': 1,
        'limit': int.tryParse(query['limit'] ?? '') ?? 20,
        'offset': int.tryParse(query['offset'] ?? '') ?? 0,
      }),
      200,
      headers: _jsonHeaders,
    );
  }

  http.Response _list(Map<String, String> query) {
    final q = query['q'];
    if (q == null || q.toLowerCase().contains('lavandula')) {
      return http.Response.bytes(
        utf8.encode(apiFixture(listFixture)),
        200,
        headers: _jsonHeaders,
      );
    }
    return http.Response(
      jsonEncode({
        'items': <Object?>[],
        'total': 0,
        'limit': int.tryParse(query['limit'] ?? '') ?? 50,
        'offset': int.tryParse(query['offset'] ?? '') ?? 0,
      }),
      200,
      headers: _jsonHeaders,
    );
  }
}

/// Synthetic `GET /v1/goals` body: ids, names and order of the seed, with the
/// six subareas under `otros-objetivos`. The counts are made up.
List<Map<String, Object?>> syntheticGoals() => [
  _goal('relajacion-estres', 'Relajación / Estrés', 17),
  _goal('mejorar-el-sueno', 'Mejorar el sueño', 8),
  _goal('cuidado-de-la-piel', 'Cuidado de la piel', 32),
  _goal('alivio-respiratorio', 'Alivio respiratorio', 52),
  _goal('cansancio-y-fatiga', 'Cansancio y fatiga', 8),
  _goal('otros-objetivos', 'Otros objetivos', 135, [
    _goal('digestion', 'Digestión', 68),
    _goal('vias-urinarias-y-genitales', 'Vías urinarias y genitales', 42),
    _goal('dolor-e-inflamacion', 'Dolor e inflamación', 22),
    _goal('boca-y-garganta', 'Boca y garganta', 20),
    _goal('circulacion', 'Circulación', 17),
    _goal('molestias-oculares', 'Molestias oculares', 1),
  ]),
];

Map<String, Object?> _goal(
  String id,
  String name,
  int plantCount, [
  List<Map<String, Object?>>? subareas,
]) => {
  'id': id,
  'name': name,
  'plantCount': plantCount,
  'subareas': subareas ?? <Object?>[],
};
