import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import 'passport_style.dart';

/// `Propiedades` tab content.
class PassportPropertiesTab extends StatelessWidget {
  const PassportPropertiesTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) => const Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      PassportSectionTitle('Propiedades'),
      SizedBox(height: 8),
      Text('sin propiedades medicinales evaluadas en este catálogo'),
    ],
  );
}
