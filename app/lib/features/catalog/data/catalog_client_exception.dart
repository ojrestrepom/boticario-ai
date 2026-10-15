enum CatalogClientErrorKind {
  network,
  timeout,
  server,
  badRequest,
  invalidResponse,
}

/// Any failure talking to the catalog API. [message] is Spanish text that is
/// safe to show in the UI; every kind is retryable by the user.
class CatalogClientException implements Exception {
  const CatalogClientException(this.kind, this.message, {this.cause});

  final CatalogClientErrorKind kind;
  final String message;
  final Object? cause;

  @override
  String toString() => 'CatalogClientException(${kind.name}): $message';
}
