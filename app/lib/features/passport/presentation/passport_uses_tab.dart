import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import 'passport_style.dart';

/// `Usos` tab content.
class PassportUsesTab extends StatelessWidget {
  const PassportUsesTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    final uses = plant.uses;
    if (uses.isEmpty) {
      return const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PassportSectionTitle('Usos tradicionales'),
          SizedBox(height: 8),
          Text(
            'No hay usos tradicionales con referencia verificable disponibles',
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PassportSectionTitle('Registros tradicionales'),
        const SizedBox(height: 8),
        const Text(
          'No es una recomendación de uso ni evidencia de eficacia clínica',
        ),
        const SizedBox(height: 12),
        for (final use in uses) ...[
          PassportField('Registro tradicional', use.activity),
          PassportField(
            'Referencia: ${use.reference.id}',
            use.reference.citation,
          ),
          const Divider(height: 20),
        ],
      ],
    );
  }
}
