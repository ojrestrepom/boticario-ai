import 'package:flutter/material.dart';

import 'passport_style.dart';

/// A URL shown as selectable text, with a label before it.
///
/// Links are not opened yet: the `url_launcher` decision is pending (task
/// 7.2). When the user chooses it, this is the only widget that needs to
/// learn to open the URL (wrap [url] in a tappable area of at least 48 dp).
class PassportLink extends StatelessWidget {
  const PassportLink({required this.label, required this.url, super.key});

  final String label;
  final String url;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelMedium
              ?.copyWith(color: passportGreen),
        ),
        SelectableText(
          url,
          style: Theme.of(context).textTheme.bodyMedium
              ?.copyWith(color: passportInk),
        ),
      ],
    ),
  );
}
