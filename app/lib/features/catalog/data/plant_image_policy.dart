import 'package:flutter/painting.dart';

/// Policy for loading plant images straight from Wikimedia (design D9).
///
/// Only HTTPS URLs on [allowedHosts] are loaded, and requests carry no
/// credentials: no `Authorization`, no cookies, only a generic `User-Agent`.
abstract final class PlantImagePolicy {
  static const allowedHosts = {'commons.wikimedia.org', 'upload.wikimedia.org'};

  /// App name and version only. No email, no personal data.
  static const userAgent = 'BoticarioAI/0.1.0';

  /// The only headers a request may carry.
  static const headers = {'User-Agent': userAgent};

  /// Returns the parsed URI when [url] may be loaded, or `null`.
  static Uri? allowedUri(String? url) {
    if (url == null) return null;
    final Uri uri;
    try {
      uri = Uri.parse(url.trim());
    } on FormatException {
      return null;
    }
    if (uri.scheme != 'https') return null;
    if (uri.userInfo.isNotEmpty) return null;
    if (!allowedHosts.contains(uri.host.toLowerCase())) return null;
    return uri;
  }

  static bool isAllowed(String? url) => allowedUri(url) != null;

  /// Image provider for [url], or `null` when the policy rejects it.
  /// Callers show the local art when this returns `null` or loading fails.
  static ImageProvider? providerFor(String? url) {
    final uri = allowedUri(url);
    if (uri == null) return null;
    return NetworkImage(uri.toString(), headers: headers);
  }
}
