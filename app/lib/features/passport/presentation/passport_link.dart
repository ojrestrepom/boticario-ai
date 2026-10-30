import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import 'passport_style.dart';
import 'passport_texts.dart';

/// One piece of a [PassportLinkedText]: plain text, or a link when [url] is a
/// well-formed `https` URL (design D2).
@immutable
class PassportLinkPart {
  const PassportLinkPart(this.text, {this.url, this.destination = ''});

  final String text;
  final String? url;

  /// Where the link goes, for screen readers ("el texto de la licencia").
  final String destination;

  bool get isLink => PassportLinkedText.canOpen(url);
}

/// A tap recognizer that also reports a long press.
///
/// It stays a [TapGestureRecognizer] so the text keeps the link semantics
/// Flutter derives from it. A long press suppresses the tap that follows it.
class _LinkRecognizer extends TapGestureRecognizer {
  _LinkRecognizer({required VoidCallback onOpen, required this.onLongPress}) {
    onTap = onOpen;
  }

  final VoidCallback onLongPress;
  Timer? _timer;
  bool _longPressed = false;

  @override
  void handleTapDown({required PointerDownEvent down}) {
    super.handleTapDown(down: down);
    _longPressed = false;
    _timer?.cancel();
    _timer = Timer(kLongPressTimeout - kPressTimeout, () {
      _longPressed = true;
      onLongPress();
    });
  }

  @override
  void handleTapUp({
    required PointerDownEvent down,
    required PointerUpEvent up,
  }) {
    _timer?.cancel();
    if (_longPressed) {
      _longPressed = false;
      return;
    }
    super.handleTapUp(down: down, up: up);
  }

  @override
  void handleTapCancel({
    required PointerDownEvent down,
    PointerCancelEvent? cancel,
    required String reason,
  }) {
    _timer?.cancel();
    _longPressed = false;
    super.handleTapCancel(down: down, cancel: cancel, reason: reason);
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

/// Running text whose [parts] may be links, without showing any URL.
///
/// A link part is underlined and green; a tap opens it in the system browser
/// and a long press copies the URL to the clipboard. Other parts, and parts
/// whose URL is missing or not `https`, are plain text with no link semantics.
/// Links sit inside the sentence, so they follow the inline-link exception of
/// WCAG 2.5.8 and do not need a 48 dp target (design D5). The app never loads
/// or shows the target page itself.
class PassportLinkedText extends StatefulWidget {
  const PassportLinkedText({required this.parts, this.style, super.key});

  final List<PassportLinkPart> parts;

  /// Base style of the text; the context text style when null.
  final TextStyle? style;

  /// Whether [url] may be opened: only well-formed `https` URLs with a host.
  static bool canOpen(String? url) {
    if (url == null) return false;
    final uri = Uri.tryParse(url.trim());
    return uri != null && uri.scheme == 'https' && uri.host.isNotEmpty;
  }

  @override
  State<PassportLinkedText> createState() => _PassportLinkedTextState();
}

class _PassportLinkedTextState extends State<PassportLinkedText> {
  var _recognizers = <GestureRecognizer?>[];

  @override
  void initState() {
    super.initState();
    _recognizers = _build();
  }

  @override
  void didUpdateWidget(covariant PassportLinkedText oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!listEquals(
      [for (final p in oldWidget.parts) (p.text, p.url)],
      [for (final p in widget.parts) (p.text, p.url)],
    )) {
      _disposeRecognizers();
      _recognizers = _build();
    }
  }

  @override
  void dispose() {
    _disposeRecognizers();
    super.dispose();
  }

  void _disposeRecognizers() {
    for (final recognizer in _recognizers) {
      recognizer?.dispose();
    }
  }

  List<GestureRecognizer?> _build() => [
    for (final part in widget.parts)
      if (part.isLink)
        _LinkRecognizer(
          onOpen: () => _open(part.url!),
          onLongPress: () => _copy(part.url!),
        )
      else
        null,
  ];

  Future<void> _open(String url) async {
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

  Future<void> _copy(String url) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    try {
      await Clipboard.setData(ClipboardData(text: url.trim()));
      messenger?.showSnackBar(
        const SnackBar(content: Text(PassportTexts.linkCopied)),
      );
    } on Object {
      // Copying is a shortcut, not the only way out: stay silent on failure.
    }
  }

  @override
  Widget build(BuildContext context) {
    final base = DefaultTextStyle.of(context).style.merge(widget.style);
    final linkStyle = base.copyWith(
      color: passportGreen,
      decoration: TextDecoration.underline,
      decorationColor: passportGreen,
    );
    return Text.rich(
      TextSpan(
        style: base,
        children: [
          for (var i = 0; i < widget.parts.length; i++)
            if (widget.parts[i].isLink)
              TextSpan(
                text: widget.parts[i].text,
                style: linkStyle,
                recognizer: _recognizers[i],
                // The destination is announced, never the URL.
                semanticsLabel: PassportTexts.linkSemantics(
                  widget.parts[i].text,
                  widget.parts[i].destination,
                ),
              )
            else
              TextSpan(text: widget.parts[i].text),
        ],
      ),
    );
  }
}
