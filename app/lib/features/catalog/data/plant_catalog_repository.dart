import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/plant.dart';
import 'plant_catalog_asset_data_source.dart';

/// Reads the local catalog. The ordered catalog remains the domain model's
/// responsibility; this class deliberately adds no second cache.
class PlantCatalogRepository {
  PlantCatalogRepository({required this.dataSource});

  final PlantCatalogAssetDataSource dataSource;

  Future<PlantCatalog> load() => dataSource.load();

  Future<Plant?> findById(int usdaPlantId) async =>
      (await load()).findById(usdaPlantId);
}

final plantCatalogAssetDataSourceProvider =
    Provider<PlantCatalogAssetDataSource>(
      (ref) => PlantCatalogAssetDataSource(),
    );

final plantCatalogRepositoryProvider = Provider<PlantCatalogRepository>(
  (ref) => PlantCatalogRepository(
    dataSource: ref.watch(plantCatalogAssetDataSourceProvider),
  ),
);

/// Shared async state for catalog consumers. Failures are exposed immediately;
/// screens can explicitly invalidate this provider to retry a failed load.
final plantCatalogProvider = FutureProvider<PlantCatalog>(
  (ref) => ref.watch(plantCatalogRepositoryProvider).load(),
  // Catalog reads are local and user-triggered retry is explicit in the UI.
  retry: (_, _) => null,
);
