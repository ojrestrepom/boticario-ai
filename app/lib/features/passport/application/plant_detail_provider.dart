import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/catalog_providers.dart';
import '../../catalog/domain/plant.dart';

/// Plant detail by API id (slug). Resolves to `null` when the API answers 404.
/// Errors are exposed at once: retrying is the user's decision (the passport
/// invalidates this provider), so Riverpod's automatic retry is disabled.
final plantDetailProvider = FutureProvider.autoDispose.family<Plant?, String>(
  (ref, id) => ref.watch(catalogRepositoryProvider).getPlant(id),
  retry: (_, _) => null,
);
