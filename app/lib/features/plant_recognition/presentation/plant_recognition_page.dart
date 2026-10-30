import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../application/plant_image_controller.dart';
import '../data/plant_image_source.dart';

const _green = Color(0xFF236335);
const _ink = Color(0xFF172A1F);
const _background = Color(0xFFF9FAF7);
const _border = Color(0xFFD6DDD4);

/// Local image acquisition only; no inference or backend requests.
class PlantRecognitionPage extends ConsumerStatefulWidget {
  const PlantRecognitionPage({
    required this.onBack,
    required this.onHome,
    super.key,
  });

  final VoidCallback onBack;
  final VoidCallback onHome;

  @override
  ConsumerState<PlantRecognitionPage> createState() =>
      _PlantRecognitionPageState();
}

class _PlantRecognitionPageState extends ConsumerState<PlantRecognitionPage> {
  late final PlantImageController _controller;
  late final int _sessionId;

  @override
  void initState() {
    super.initState();
    _controller = ref.read(plantImageControllerProvider.notifier);
    _sessionId = _controller.beginSession();
  }

  @override
  void dispose() {
    // Provider notifications must happen outside the widget disposal phase.
    scheduleMicrotask(() => _controller.endSession(_sessionId));
    super.dispose();
  }

  void _leave(VoidCallback navigate) {
    _controller.endSession(_sessionId);
    navigate();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(plantImageControllerProvider);
    return Scaffold(
      backgroundColor: _background,
      body: SafeArea(
        bottom: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  IconButton(
                    tooltip: 'Volver a Inicio',
                    onPressed: () => _leave(widget.onBack),
                    color: _green,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Expanded(
                    child: Text(
                      'Identificar planta',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge
                          ?.copyWith(color: _ink),
                    ),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                constraints: const BoxConstraints(minHeight: 200),
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFFF3F5F2),
                  border: Border.all(color: _border),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: state.image != null
                    ? Image.memory(
                        state.image!,
                        fit: BoxFit.contain,
                        height: 240,
                        cacheWidth: 1600,
                        semanticLabel: 'Imagen seleccionada de la planta',
                        errorBuilder: (context, error, stack) => const Text(
                          'No se pudo mostrar la imagen. Selecciona otra imagen.',
                        ),
                      )
                    : const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          ExcludeSemantics(
                            child: Icon(
                              Icons.image_outlined,
                              size: 64,
                              color: _green,
                            ),
                          ),
                          SizedBox(height: 12),
                          Text(
                            'Aquí se mostrará la imagen',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
              ),
              const SizedBox(height: 16),
              if (state.error != null) ...[
                Semantics(
                  liveRegion: true,
                  child: Text(state.error!, textAlign: TextAlign.center),
                ),
                const SizedBox(height: 12),
              ],
              if (state.busy) ...[
                Semantics(
                  liveRegion: true,
                  child: const Text(
                    'Esperando la selección de imagen…',
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 12),
              ],
              OutlinedButton(
                onPressed: state.busy
                    ? null
                    : () => _controller.pick(PlantImageOrigin.camera),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text(
                  'Tomar fotografía',
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: state.busy
                    ? null
                    : () => _controller.pick(PlantImageOrigin.gallery),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text(
                  'Seleccionar de galería',
                  textAlign: TextAlign.center,
                ),
              ),
              if (state.image != null) ...[
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: _controller.discard,
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(48),
                  ),
                  child: const Text(
                    'Descartar imagen',
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: DecoratedBox(
          decoration: const BoxDecoration(
            border: Border(top: BorderSide(color: _border)),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final fontSize =
                  Theme.of(context).textTheme.labelSmall?.fontSize ?? 12;
              final largeText =
                  MediaQuery.textScalerOf(context).scale(fontSize) / fontSize >=
                  1.5;
              final tabs = [
                _tab(
                  context,
                  'Inicio',
                  Icons.home,
                  () => _leave(widget.onHome),
                ),
                _tab(context, 'Favoritos', Icons.favorite_border, null),
                _tab(context, 'Historial', Icons.history, null),
                _tab(context, 'Perfil', Icons.person_outline, null),
              ];
              return largeText
                  ? Wrap(
                      children: [
                        for (final tab in tabs)
                          SizedBox(width: constraints.maxWidth / 2, child: tab),
                      ],
                    )
                  : Row(
                      children: [for (final tab in tabs) Expanded(child: tab)],
                    );
            },
          ),
        ),
      ),
    );
  }

  Widget _tab(
    BuildContext context,
    String label,
    IconData icon,
    VoidCallback? onTap,
  ) => Semantics(
    button: true,
    enabled: onTap != null,
    selected: onTap != null,
    label: onTap == null ? '$label no disponible' : label,
    onTap: onTap,
    excludeSemantics: true,
    child: InkWell(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 56, minWidth: 48),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: onTap == null ? _ink : _green),
              Text(
                label,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.labelSmall
                    ?.copyWith(color: onTap == null ? _ink : _green),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
