import 'package:boticario_ai/features/catalog/data/catalog_api_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('the default address reaches the host from the Android emulator', () {
    expect(defaultApiBaseUrl, 'http://10.0.2.2:8080');
    expect(
      normalizeApiBaseUrl(apiBaseUrlFromEnvironment),
      'http://10.0.2.2:8080',
    );
  });

  test('accepts an overridden address', () {
    expect(
      normalizeApiBaseUrl('http://192.168.1.20:8080'),
      'http://192.168.1.20:8080',
    );
    expect(
      normalizeApiBaseUrl('https://api.example.org'),
      'https://api.example.org',
    );
  });

  test('strips trailing slashes', () {
    expect(normalizeApiBaseUrl('http://host:8080/'), 'http://host:8080');
    expect(normalizeApiBaseUrl('http://host:8080//'), 'http://host:8080');
  });

  test('rejects addresses that are not http(s) with a host', () {
    for (final bad in ['', 'host:8080', 'ftp://host', 'http://', '/v1']) {
      expect(() => normalizeApiBaseUrl(bad), throwsFormatException);
    }
  });
}
