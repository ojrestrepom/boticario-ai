import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import 'passport_style.dart';
import 'passport_texts.dart';

/// Text that links to a URL, without showing the URL (design D2).
///
/// When [url] is a well-formed `https` URL the text is underlined and green,
/// a tap opens it in the system browser and a long press copies it to the
/// clipboard. Otherwise (no URL, or not `https`) it is plain text with no link
/// semantics. The app never loads or shows the target page itself.
///
/// [prefix] ("Licencia: ") sits inside the touch target but outside the
/// underline. [destination] describes where the link goes for screen readers
/// ("el texto de la licencia"); the URL itself is never read.
class PassportInlineLink extends StatelessWidget {
  const PassportInlineLink({
    required this.text,
    required this.url,
    required this.destination,
    this.prefix = '',
    this.style,
    super.key,
  });

  final String text;
  final String? url;
  final String destination;
  final String prefix;

  /// Base style of the text; the context text style when null.
  final TextStyle? style;

  /// Whether [url] may be opened: only well-formed `https` URLs with a host.
  static bool canOpen(String? url) {
    if (url == null) return false;
    final uri = Uri.tryParse(url.trim());
    return uri != null && uri.scheme == 'https' && uri.host.isNotEmpty;
  }

  Future<void> _open(BuildContext context) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    var opened = false;
    try {
      opened = await launchUrl(
        Uri.parse(url!.trim()),
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

  Future<void> _copy(BuildContext context) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    try {
      await Clipboard.setData(ClipboardData(text: url!.trim()));
      messenger?.showSnackBar(
        const SnackBar(content: Text(PassportTexts.linkCopied)),
      );
    } on Object {
      // Copying is a shortcut, not the only way out: stay silent on failure.
    }
  }

  @override
  Widget build(BuildContext context) {
    final base = DefaultTextStyle.of(context).style.merge(style);
    if (!canOpen(url)) {
      return Text.rich(TextSpan(text: '$prefix$text', style: base));
    }
    final linkStyle = base.copyWith(
      color: passportGreen,
      decoration: TextDecoration.underline,
      decorationColor: passportGreen,
    );
    return Semantics(
      link: true,
      label: '$prefix$text',
      hint: PassportTexts.linkHint(destination),
      onTap: () => _open(context),
      onLongPress: () => _copy(context),
      excludeSemantics: true,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 48, minWidth: 48),
        child: InkWell(
          onTap: () => _open(context),
          onLongPress: () => _copy(context),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Align(
              alignment: Alignment.centerLeft,
              widthFactor: 1,
              child: Text.rich(
                TextSpan(
                  style: base,
                  children: [
                    if (prefix.isNotEmpty) TextSpan(text: prefix),
                    TextSpan(text: text, style: linkStyle),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
