import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import 'passport_style.dart';

/// Passport header: back button, plant icon, names and the favorite stub.
class PassportHeader extends StatelessWidget {
  const PassportHeader({required this.plant, required this.onBack, super.key});

  final Plant plant;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
    child: Row(
      children: [
        SizedBox(
          width: 48,
          height: 48,
          child: IconButton(
            tooltip: 'Volver a Explorar',
            onPressed: onBack,
            icon: const Icon(Icons.chevron_left),
            color: passportGreen,
          ),
        ),
        const ExcludeSemantics(
          child: Icon(Icons.local_florist, color: passportGreen, size: 34),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                plant.primaryName,
                style: Theme.of(context).textTheme.titleLarge
                    ?.copyWith(color: passportInk),
              ),
              if (plant.secondaryName != null)
                Text(
                  plant.secondaryName!,
                  style: Theme.of(context).textTheme.bodyMedium
                      ?.copyWith(color: passportInk),
                ),
            ],
          ),
        ),
        Semantics(
          label: 'Favorito no disponible',
          button: true,
          enabled: false,
          child: const SizedBox(
            width: 48,
            height: 48,
            child: Icon(Icons.favorite_border, color: Colors.grey),
          ),
        ),
      ],
    ),
  );
}
