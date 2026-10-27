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

  /// Width in pixels of the thumbnail the header asks for (design D9).
  /// Wikimedia only serves standard widths: 500 and 960 work, 640 does not.
  static const thumbnailWidth = 500;

  static const _rasterExtensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'};

  /// Thumbnail URL for an `image.url` of the form
  /// `https://upload.wikimedia.org/wikipedia/commons/<a>/<ab>/<file>`, which
  /// becomes `.../commons/thumb/<a>/<ab>/<file>/500px-<file>`.
  ///
  /// The file name keeps the percent-encoding it has in [url]. SVG files are
  /// served as PNG (`500px-<file>.png`). Other formats (TIFF, PDF...) and any
  /// path that does not fit return `null`, and so does a URL the policy
  /// rejects; callers then show the local art, never the original file.
  static String? thumbnailUrl(String? url) {
    final uri = allowedUri(url);
    if (uri == null || uri.host.toLowerCase() != 'upload.wikimedia.org') {
      return null;
    }
    if (uri.hasQuery || uri.hasFragment) return null;
    final parts = uri.path.split('/');
    // ['', 'wikipedia', 'commons', a, ab, file]
    if (parts.length != 6 ||
        parts[0].isNotEmpty ||
        parts[1] != 'wikipedia' ||
        parts[2] != 'commons') {
      return null;
    }
    final a = parts[3];
    final ab = parts[4];
    final file = parts[5];
    if (a.length != 1 || ab.length != 2 || !ab.startsWith(a) || file.isEmpty) {
      return null;
    }
    final dot = file.lastIndexOf('.');
    if (dot < 0 || dot == file.length - 1) return null;
    final ext = file.substring(dot + 1).toLowerCase();
    final String thumbName;
    if (ext == 'svg') {
      thumbName = '${thumbnailWidth}px-$file.png';
    } else if (_rasterExtensions.contains(ext)) {
      thumbName = '${thumbnailWidth}px-$file';
    } else {
      return null;
    }
    return 'https://upload.wikimedia.org/wikipedia/commons/thumb/$a/$ab/'
        '$file/$thumbName';
  }

  /// Image provider for the 500 px thumbnail of [url], or `null` when there is
  /// none. Callers show the local art then or when loading fails.
  static ImageProvider? thumbnailProviderFor(String? url) {
    final thumb = thumbnailUrl(url);
    if (thumb == null) return null;
    return NetworkImage(thumb, headers: headers);
  }

  /// Image provider for [url], or `null` when the policy rejects it.
  /// Callers show the local art when this returns `null` or loading fails.
  static ImageProvider? providerFor(String? url) {
    final uri = allowedUri(url);
    if (uri == null) return null;
    return NetworkImage(uri.toString(), headers: headers);
  }
}
