import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'catalog_api_config.dart';
import 'catalog_repository.dart';

/// Tests override this with a `MockClient`; no test opens a real connection.
final httpClientProvider = Provider<http.Client>((ref) {
  final client = http.Client();
  ref.onDispose(client.close);
  return client;
});

final apiBaseUrlProvider = Provider<String>(
  (ref) => normalizeApiBaseUrl(apiBaseUrlFromEnvironment),
);

/// Tests override this with a fictitious token.
final apiTokenProvider = Provider<String>((ref) => apiTokenFromEnvironment);

final catalogRepositoryProvider = Provider<CatalogRepository>(
  (ref) => HttpCatalogRepository(
    client: ref.watch(httpClientProvider),
    baseUrl: ref.watch(apiBaseUrlProvider),
    apiToken: ref.watch(apiTokenProvider),
  ),
);
