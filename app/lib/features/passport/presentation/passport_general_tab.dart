import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import 'passport_style.dart';

/// `General` tab content.
class PassportGeneralTab extends StatelessWidget {
  const PassportGeneralTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    final commonNames = plant.commonNames;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PassportField('Familia', plant.family ?? 'No disponible en fuente'),
        if (commonNames.isEmpty)
          const PassportField(
            'Nombres comunes',
            'No hay nombres comunes registrados',
          )
        else
          PassportFieldLines('Nombres comunes', [
            for (final name in commonNames) '${name.text} (${name.language})',
          ]),
        PassportField(
          'Partes registradas en fuente',
          plant.parts.isEmpty
              ? 'No hay partes registradas en fuente'
              : plant.parts.join(', '),
        ),
        const PassportField('Tipo de aceite', 'No aplicable: ficha de planta'),
        if (plant.uses.isNotEmpty) ...[
          const SizedBox(height: 8),
          const PassportSectionTitle('Referencias bibliográficas'),
          for (final ref in _references()) PassportField(ref.id, ref.citation),
        ],
      ],
    );
  }

  List<UseReference> _references() {
    final refs = <String, UseReference>{};
    for (final use in plant.uses) {
      refs[use.reference.id] = use.reference;
    }
    return refs.values.toList();
  }
}
