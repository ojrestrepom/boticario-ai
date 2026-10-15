import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../domain/catalog_plant.dart';
import '../domain/plant_summary.dart';
import 'catalog_api_config.dart';
import 'catalog_client_exception.dart';
import 'catalog_json_parser.dart';

/// Read-only access to the catalog API (`GET /v1/plants` and
/// `GET /v1/plants/{id}`).
abstract class CatalogRepository {
  Future<PlantPage> listPlants({
    String query = '',
    int limit = 50,
    int offset = 0,
  });

  /// Returns `null` when the API answers 404 (plant not found).
  Future<Plant?> getPlant(String id);
}

class HttpCatalogRepository implements CatalogRepository {
  HttpCatalogRepository({
    required this._client,
    required String baseUrl,
    this.timeout = const Duration(seconds: 10),
  }) : _base = Uri.parse(normalizeApiBaseUrl(baseUrl));

  static const int maxQueryLength = 200;

  final http.Client _client;
  final Uri _base;
  final Duration timeout;

  static const _headers = {'Accept': 'application/json'};

  @override
  Future<PlantPage> listPlants({
    String query = '',
    int limit = 50,
    int offset = 0,
  }) async {
    var q = query.trim();
    // Cut by code points (as the API counts), never splitting a surrogate pair.
    if (q.runes.length > maxQueryLength) {
      q = String.fromCharCodes(q.runes.take(maxQueryLength));
    }
    final uri = _uri(
      ['v1', 'plants'],
      {if (q.isNotEmpty) 'q': q, 'limit': '$limit', 'offset': '$offset'},
    );
    final response = await _get(uri);
    _throwForStatus(response);
    return parsePlantPage(_body(response));
  }

  @override
  Future<Plant?> getPlant(String id) async {
    final response = await _get(_uri(['v1', 'plants', id], null));
    if (response.statusCode == 404) return null;
    _throwForStatus(response);
    return parsePlant(_body(response));
  }

  Uri _uri(List<String> segments, Map<String, String>? query) => _base.replace(
    pathSegments: [
      ..._base.pathSegments.where((segment) => segment.isNotEmpty),
      ...segments,
    ],
    queryParameters: query,
  );

  Future<http.Response> _get(Uri uri) async {
    try {
      return await _client.get(uri, headers: _headers).timeout(timeout);
    } on TimeoutException catch (error) {
      throw CatalogClientException(
        CatalogClientErrorKind.timeout,
        'El servidor tardó demasiado en responder. Inténtalo de nuevo.',
        cause: error,
      );
    } on SocketException catch (error) {
      throw _network(error);
    } on http.ClientException catch (error) {
      throw _network(error);
    }
  }

  CatalogClientException _network(Object error) => CatalogClientException(
    CatalogClientErrorKind.network,
    'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.',
    cause: error,
  );

  void _throwForStatus(http.Response response) {
    final status = response.statusCode;
    if (status >= 200 && status < 300) return;
    if (status >= 500) {
      throw CatalogClientException(
        CatalogClientErrorKind.server,
        'El servidor tuvo un problema (HTTP $status). Inténtalo de nuevo.',
      );
    }
    if (status == 400) {
      throw const CatalogClientException(
        CatalogClientErrorKind.badRequest,
        'El servidor rechazó la solicitud. Inténtalo de nuevo.',
      );
    }
    throw CatalogClientException(
      CatalogClientErrorKind.invalidResponse,
      'El servidor respondió de forma inesperada (HTTP $status).',
    );
  }

  String _body(http.Response response) {
    try {
      return utf8.decode(response.bodyBytes);
    } on FormatException catch (error) {
      throw CatalogClientException(
        CatalogClientErrorKind.invalidResponse,
        'La respuesta del servidor no es válida: texto mal codificado.',
        cause: error,
      );
    }
  }
}
