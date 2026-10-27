import 'package:flutter/material.dart';

const passportGreen = Color(0xFF236335);
const passportInk = Color(0xFF172A1F);
const passportBackground = Color(0xFFF9FAF7);

/// Label and value pair shared by the passport tabs.
class PassportField extends StatelessWidget {
  const PassportField(this.label, this.value, {super.key});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => PassportFieldLines(label, [value]);
}

/// Label followed by one text line per value.
class PassportFieldLines extends StatelessWidget {
  const PassportFieldLines(this.label, this.values, {super.key});
  final String label;
  final List<String> values;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge
              ?.copyWith(color: passportGreen),
        ),
        const SizedBox(height: 3),
        for (final value in values)
          Text(
            value,
            style: Theme.of(context).textTheme.bodyLarge
                ?.copyWith(color: passportInk),
          ),
      ],
    ),
  );
}

class PassportSectionTitle extends StatelessWidget {
  const PassportSectionTitle(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: Theme.of(context).textTheme.titleMedium
        ?.copyWith(color: passportInk),
  );
}
