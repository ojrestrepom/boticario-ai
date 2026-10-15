import 'dart:async';
import 'dart:io';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/catalog/data/catalog_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import '../../../support/fake_catalog_api.dart';

Matcher _clientError(CatalogClientErrorKind kind) => throwsA(
  isA<CatalogClientException>()
      .having((e) => e.kind, 'kind', kind)
      .having((e) => e.message, 'message', isNotEmpty),
);

void main() {
  late List<http.Request> requests;

  HttpCatalogRepository repo(
    http.Response Function(http.Request) handler, {
    String baseUrl = 'http://host:8080',
    Duration timeout = const Duration(seconds: 10),
  }) {
    requests = [];
    return HttpCatalogRepository(
      client: MockClient((request) async {
        requests.add(request);
        return handler(request);
      }),
      baseUrl: baseUrl,
      timeout: timeout,
    );
  }

  http.Response emptyPage(http.Request _) => http.Response(
    '{"items":[],"total":0,"limit":50,"offset":0}',
    200,
    headers: {'content-type': 'application/json'},
  );

  group('listPlants requests', () {
    test('sends exact URL and Accept header', () async {
      final r = repo(emptyPage);
      await r.listPlants(query: 'lavandula', limit: 50, offset: 100);
      expect(
        requests.single.url.toString(),
        'http://host:8080/v1/plants?q=lavandula&limit=50&offset=100',
      );
      expect(requests.single.method, 'GET');
      expect(requests.single.headers, {'Accept': 'application/json'});
    });

    test('encodes spaces, accents and reserved characters in q', () async {
      final r = repo(emptyPage);
      await r.listPlants(query: 'té & café/ñ?=#');
      expect(requests.single.url.queryParameters['q'], 'té & café/ñ?=#');
      expect(requests.single.url.query, isNot(contains(' ')));
      expect(requests.single.url.query, isNot(contains('&café')));
      expect(requests.single.url.query, contains('%26'));
      expect(requests.single.url.query, contains('%C3%A9'));
      expect(requests.single.url.fragment, isEmpty);
    });

    test('omits q for empty or whitespace-only queries', () async {
      final r = repo(emptyPage);
      await r.listPlants();
      await r.listPlants(query: '   ');
      expect(
        requests[0].url.toString(),
        'http://host:8080/v1/plants?limit=50&offset=0',
      );
      expect(requests[1].url.queryParameters.containsKey('q'), isFalse);
    });

    test('trims and limits q to 200 characters', () async {
      final r = repo(emptyPage);
      await r.listPlants(query: '  ${'a' * 250}  ');
      expect(requests.single.url.queryParameters['q'], 'a' * 200);
    });

    test('cuts q by code points without splitting a surrogate pair', () async {
      final r = repo(emptyPage);
      await r.listPlants(query: '${'a' * 199}😀${'b' * 20}');
      final sent = requests.single.url.queryParameters['q']!;
      expect(sent, '${'a' * 199}😀');
      expect(sent.runes.length, 200);
      expect(requests.single.url.query, contains('%F0%9F%98%80'));
    });

    test('does not produce // with a trailing slash in the base URL', () async {
      final r = repo(emptyPage, baseUrl: 'http://host:8080/');
      await r.listPlants();
      await r.getPlant('x').catchError((_) => null);
      expect(
        requests[0].url.toString(),
        startsWith('http://host:8080/v1/plants?'),
      );
      expect(requests[1].url.toString(), 'http://host:8080/v1/plants/x');
    });
  });

  group('getPlant', () {
    test('requests the id path with Accept and parses the detail', () async {
      final r = repo(
        (_) => http.Response.bytes(
          File('test/fixtures/api/plant_lavandula-angustifolia.json')
              .readAsBytesSync(),
          200,
          headers: {'content-type': 'application/json'},
        ),
      );
      final plant = await r.getPlant('lavandula-angustifolia');
      expect(
        requests.single.url.toString(),
        'http://host:8080/v1/plants/lavandula-angustifolia',
      );
      expect(requests.single.headers['Accept'], 'application/json');
      expect(plant!.uses, hasLength(10));
      // UTF-8 is decoded even when the content type has no charset.
      expect(
        plant.names.map((n) => n.text),
        everyElement(isNot(contains('Ã'))),
      );
    });

    test('encodes reserved characters in the id segment', () async {
      final r = repo((_) => http.Response('', 404));
      await r.getPlant('a/b c?d#e');
      expect(requests.single.url.path, '/v1/plants/a%2Fb%20c%3Fd%23e');
      expect(requests.single.url.hasQuery, isFalse);
    });

    test('returns null on 404', () async {
      final r = repo((_) => http.Response('{"status":404}', 404));
      expect(await r.getPlant('nope'), isNull);
    });
  });

  group('errors', () {
    test('400 is a bad request error', () {
      final r = repo(
        (_) => http.Response(
          '{"status":400}',
          400,
          headers: {'content-type': 'application/problem+json'},
        ),
      );
      expect(r.listPlants(), _clientError(CatalogClientErrorKind.badRequest));
    });

    test('5xx is a server error', () {
      final r = repo((_) => http.Response('boom', 503));
      expect(r.listPlants(), _clientError(CatalogClientErrorKind.server));
      expect(r.getPlant('x'), _clientError(CatalogClientErrorKind.server));
    });

    test('unexpected status and 404 on the list are invalid responses', () {
      final r = repo((_) => http.Response('', 404));
      expect(
        r.listPlants(),
        _clientError(CatalogClientErrorKind.invalidResponse),
      );
    });

    test('invalid body on success is an invalid response', () {
      final r = repo((_) => http.Response('<html>', 200));
      expect(
        r.listPlants(),
        _clientError(CatalogClientErrorKind.invalidResponse),
      );
      expect(
        r.getPlant('x'),
        _clientError(CatalogClientErrorKind.invalidResponse),
      );
    });

    test('connection failures become network errors', () async {
      final socket = HttpCatalogRepository(
        client: MockClient((_) async => throw const SocketException('down')),
        baseUrl: 'http://host:8080',
      );
      await expectLater(
        socket.listPlants(),
        _clientError(CatalogClientErrorKind.network),
      );
      final client = HttpCatalogRepository(
        client: MockClient((_) async => throw http.ClientException('down')),
        baseUrl: 'http://host:8080',
      );
      await expectLater(
        client.getPlant('x'),
        _clientError(CatalogClientErrorKind.network),
      );
    });

    test('a request that never answers times out', () async {
      final r = HttpCatalogRepository(
        client: MockClient((_) => Completer<http.Response>().future),
        baseUrl: 'http://host:8080',
        timeout: const Duration(milliseconds: 20),
      );
      await expectLater(
        r.listPlants(),
        _clientError(CatalogClientErrorKind.timeout),
      );
    });

    test('the default timeout is 10 seconds', () {
      final r = HttpCatalogRepository(
        client: MockClient((_) async => http.Response('', 200)),
        baseUrl: 'http://host:8080',
      );
      expect(r.timeout, const Duration(seconds: 10));
    });

    test('a retry succeeds once the backend answers', () async {
      final api = FakeCatalogApi(failure: FakeApiFailure.connection);
      final r = HttpCatalogRepository(client: api.client, baseUrl: 'http://h');
      await expectLater(
        r.listPlants(),
        _clientError(CatalogClientErrorKind.network),
      );
      api.failure = FakeApiFailure.none;
      expect((await r.listPlants()).items, isNotEmpty);
    });
  });

  group('providers and fake API', () {
    test('catalogRepositoryProvider uses the injected client', () async {
      final api = FakeCatalogApi();
      final container = ProviderContainer(
        overrides: [
          httpClientProvider.overrideWithValue(api.client),
          apiBaseUrlProvider.overrideWithValue('http://fake:1/'),
        ],
      );
      addTearDown(container.dispose);
      final repository = container.read(catalogRepositoryProvider);
      final page = await repository.listPlants(query: 'lavandula');
      expect(page.items, isNotEmpty);
      expect(api.requests.single.url.host, 'fake');
      expect(await repository.getPlant('no-existe'), isNull);
      expect(
        (await repository.getPlant('rosmarinus-officinalis'))!.uses.length,
        greaterThan(50),
      );
      final empty = await repository.listPlants(query: 'zzz', offset: 5);
      expect(empty.items, isEmpty);
      expect(empty.offset, 5);
    });

    test('default base URL provider yields the emulator address', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      expect(container.read(apiBaseUrlProvider), 'http://10.0.2.2:8080');
    });

    test('fake API failure modes map to client errors', () async {
      final api = FakeCatalogApi(failure: FakeApiFailure.serverError);
      final r = HttpCatalogRepository(
        client: api.client,
        baseUrl: 'http://h',
        timeout: const Duration(milliseconds: 20),
      );
      await expectLater(
        r.listPlants(),
        _clientError(CatalogClientErrorKind.server),
      );
      api.failure = FakeApiFailure.timeout;
      await expectLater(
        r.listPlants(),
        _clientError(CatalogClientErrorKind.timeout),
      );
    });
  });
}
