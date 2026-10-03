import 'dart:io';

import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final json = File('assets/data/plant_catalog.json').readAsStringSync();

  test(
    'loads the default packaged asset in source order and looks up IDs',
    () async {
      final repository = PlantCatalogRepository(
        dataSource: PlantCatalogAssetDataSource(),
      );
      final catalog = await repository.load();

      expect(catalog.plants.map((plant) => plant.usdaPlantId), [
        544,
        401,
        873,
        605,
        619,
      ]);
      expect(catalog.plants.map((plant) => plant.editorialCommonName), [
        'Lavanda',
        'Eucalipto',
        'Romero',
        'Manzanilla',
        'Menta',
      ]);
      expect((await repository.findById(873))?.editorialCommonName, 'Romero');
      expect(await repository.findById(-1), isNull);
    },
  );

  test('repository provider uses an injected source', () async {
    var calls = 0;
    final container = ProviderContainer(
      overrides: [
        plantCatalogAssetDataSourceProvider.overrideWithValue(
          PlantCatalogAssetDataSource(
            loadAsset: (_) async {
              calls++;
              return json;
            },
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    final catalog = await container.read(plantCatalogProvider.future);
    expect(catalog.plants, hasLength(5));
    expect(calls, 1);
  });

  test(
    'provider reports typed failures and retries only after invalidation',
    () async {
      var calls = 0;
      final container = ProviderContainer(
        overrides: [
          plantCatalogAssetDataSourceProvider.overrideWithValue(
            PlantCatalogAssetDataSource(
              loadAsset: (_) async {
                calls++;
                if (calls == 1) throw StateError('hidden detail');
                return json;
              },
            ),
          ),
        ],
      );
      addTearDown(container.dispose);

      await expectLater(
        container.read(plantCatalogProvider.future),
        throwsA(isA<PlantCatalogLoadException>()),
      );
      expect(calls, 1, reason: 'failed local reads must not autoretry');
      container.invalidate(plantCatalogProvider);
      final recovered = await container.read(plantCatalogProvider.future);
      expect(recovered.plants, hasLength(5));
      expect(calls, 2);
    },
  );

  test(
    'repository can be overridden without invoking the default loader',
    () async {
      final catalog = PlantCatalogAssetDataSource.parse(json);
      final repository = _StubRepository(catalog);
      final container = ProviderContainer(
        overrides: [
          plantCatalogRepositoryProvider.overrideWithValue(repository),
        ],
      );
      addTearDown(container.dispose);

      expect(await container.read(plantCatalogProvider.future), same(catalog));
      expect(repository.loads, 1);
    },
  );
}

class _StubRepository extends PlantCatalogRepository {
  _StubRepository(this.catalog)
    : super(
        dataSource: PlantCatalogAssetDataSource(loadAsset: (_) async => ''),
      );

  final PlantCatalog catalog;
  int loads = 0;

  @override
  Future<PlantCatalog> load() async {
    loads++;
    return catalog;
  }
}
