import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/passport/application/plant_detail_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

void main() {
  late FakeCatalogApi api;
  late ProviderContainer container;

  setUp(() {
    api = FakeCatalogApi(requiredToken: testApiToken);
    container = ProviderContainer(
      overrides: [
        httpClientProvider.overrideWithValue(api.client),
        apiTokenProvider.overrideWithValue(testApiToken),
      ],
    );
    addTearDown(container.dispose);
  });

  test('resolves the plant by its slug id', () async {
    final plant = await container.read(
      plantDetailProvider('lavandula-angustifolia').future,
    );
    expect(plant, isNotNull);
    expect(plant!.id, 'lavandula-angustifolia');
    expect(plant.primaryName, 'English Lavender');
    expect(api.requests.single.url.path, '/v1/plants/lavandula-angustifolia');
  });

  test('is null when the API answers 404', () async {
    final plant = await container.read(plantDetailProvider('nope').future);
    expect(plant, isNull);
  });

  test('exposes the client error at once, without automatic retry', () async {
    api.failure = FakeApiFailure.serverError;
    final subscription = container.listen(
      plantDetailProvider('lavandula-angustifolia'),
      (_, _) {},
    );
    addTearDown(subscription.close);
    await expectLater(
      container.read(plantDetailProvider('lavandula-angustifolia').future),
      throwsA(isA<CatalogClientException>()),
    );
    await Future<void>.delayed(const Duration(milliseconds: 50));
    expect(api.requests, hasLength(1));
  });

  test('401 is an unauthorized error, not null like a 404', () async {
    api.failure = FakeApiFailure.unauthorized;
    await expectLater(
      container.read(plantDetailProvider('lavandula-angustifolia').future),
      throwsA(
        isA<CatalogClientException>().having(
          (e) => e.kind,
          'kind',
          CatalogClientErrorKind.unauthorized,
        ),
      ),
    );
  });

  test('invalidating the provider repeats the request', () async {
    api.failure = FakeApiFailure.connection;
    final subscription = container.listen(
      plantDetailProvider('chondrus-crispus'),
      (_, _) {},
    );
    addTearDown(subscription.close);
    await expectLater(
      container.read(plantDetailProvider('chondrus-crispus').future),
      throwsA(isA<CatalogClientException>()),
    );
    api.failure = FakeApiFailure.none;
    container.invalidate(plantDetailProvider('chondrus-crispus'));
    final plant = await container.read(
      plantDetailProvider('chondrus-crispus').future,
    );
    expect(plant!.family, isNull);
    expect(api.requests, hasLength(2));
  });
}
