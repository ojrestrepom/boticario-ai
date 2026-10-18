import 'package:flutter/material.dart';

/// Semilla verde del `ColorScheme` del prototipo.
const Color _boticarioSeedColor = Colors.green;

/// Tema real de la app: Material 3 con `ColorScheme` base verde.
///
/// API sin estado y estable, reutilizable por la app y por los harness de
/// widget tests.
ThemeData buildBoticarioTheme() {
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: _boticarioSeedColor),
  );
}
