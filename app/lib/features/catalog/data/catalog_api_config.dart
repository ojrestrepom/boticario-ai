/// Base address of the catalog API, set at build time with
/// `--dart-define=API_BASE_URL=http://192.168.1.20:8080`. The default reaches
/// a backend running on the host machine from the Android emulator.
const String apiBaseUrlFromEnvironment = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: defaultApiBaseUrl,
);

const String defaultApiBaseUrl = 'http://10.0.2.2:8080';

/// Validates [value] as an `http` or `https` address with a host and strips
/// trailing slashes so paths can be appended without `//`.
///
/// Pure so tests can cover the default, overridden and trailing-slash cases,
/// which `String.fromEnvironment` cannot vary at run time.
String normalizeApiBaseUrl(String value) {
  final trimmed = value.trim();
  final uri = Uri.tryParse(trimmed);
  if (uri == null ||
      (uri.scheme != 'http' && uri.scheme != 'https') ||
      uri.host.isEmpty) {
    throw FormatException(
      'API_BASE_URL debe ser una dirección http o https con host: "$value".',
    );
  }
  return trimmed.replaceFirst(RegExp(r'/+$'), '');
}
