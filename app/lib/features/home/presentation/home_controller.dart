import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Estado demo del contador de la pantalla inicial.
///
/// Inicia en 0 en cada instancia nueva y vive en memoria: no hay persistencia.
class HomeController extends Notifier<int> {
  @override
  int build() => 0;

  /// Suma exactamente 1 al contador actual.
  void increment() {
    state = state + 1;
  }
}

/// Provider síncrono del contador, sin codegen ni `StateProvider` legacy.
final homeControllerProvider = NotifierProvider<HomeController, int>(
  HomeController.new,
);
