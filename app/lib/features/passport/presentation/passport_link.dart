import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'passport_style.dart';
import 'passport_texts.dart';

/// A URL shown as selectable text, with a label before it and, for `https`
/// URLs, a button that opens it in the system browser.
///
/// The URL stays visible so it can be copied when it cannot be opened. The
/// app never loads or shows the target page itself.
class PassportLink extends StatelessWidget {
  const PassportLink({required this.label, required this.url, super.key});

  final String label;
  final String url;

  /// Whether [url] may be opened: only well-formed `https` URLs with a host.
  static bool canOpen(String url) {
    final uri = Uri.tryParse(url.trim());
    return uri != null && uri.scheme == 'https' && uri.host.isNotEmpty;
  }

  /// [url] for reading: percent-encoding decoded, or the original text when
  /// it cannot be decoded. Only the display changes; the link that opens is
  /// always the original URL.
  static String readable(String url) {
    try {
      return Uri.decodeFull(url);
    } on Object {
      return url;
    }
  }

  Future<void> _open(BuildContext context) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    var opened = false;
    try {
      opened = await launchUrl(
        Uri.parse(url.trim()),
        mode: LaunchMode.externalApplication,
      );
    } on Object {
      opened = false;
    }
    if (!opened) {
      messenger?.showSnackBar(
        const SnackBar(content: Text(PassportTexts.linkNotOpened)),
      );
    }
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium
                  ?.copyWith(color: passportGreen),
            ),
            if (canOpen(url))
              Tooltip(
                message: PassportTexts.openLinkTooltip(label),
                child: TextButton.icon(
                  style: TextButton.styleFrom(
                    foregroundColor: passportGreen,
                    minimumSize: const Size(48, 48),
                  ),
                  onPressed: () => _open(context),
                  icon: const Icon(Icons.open_in_new, size: 18),
                  label: const Text(PassportTexts.openLink),
                ),
              ),
          ],
        ),
        SelectableText(
          readable(url),
          style: Theme.of(context).textTheme.bodyMedium
              ?.copyWith(color: passportInk),
        ),
      ],
    ),
  );
}
