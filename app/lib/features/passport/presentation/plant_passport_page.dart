import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/catalog_client_exception.dart';
import '../../catalog/domain/plant.dart';
import '../application/plant_detail_provider.dart';

const _green = Color(0xFF236335);
const _ink = Color(0xFF172A1F);
const _background = Color(0xFFF9FAF7);

/// Route-facing entry point. It resolves the API id (slug) of the route
/// against the catalog API; the content itself is [PlantPassportPage].
class PlantPassportRoutePage extends ConsumerWidget {
  const PlantPassportRoutePage({
    required this.plantId,
    required this.onBack,
    required this.onHome,
    super.key,
  });

  final String plantId;
  final VoidCallback onBack;
  final VoidCallback onHome;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final plant = ref.watch(plantDetailProvider(plantId));
    return plant.when(
      loading: () => _PassportStatusPage(
        title: 'Cargando planta...',
        onBack: onBack,
        onHome: onHome,
      ),
      error: (error, _) => _PassportStatusPage(
        title: 'No se pudo cargar la planta',
        message: error is CatalogClientException ? error.message : null,
        onBack: onBack,
        onHome: onHome,
        action: OutlinedButton(
          onPressed: () => ref.invalidate(plantDetailProvider(plantId)),
          child: const Text('Reintentar'),
        ),
      ),
      data: (value) {
        if (value == null) {
          return _PassportStatusPage(
            title: 'Planta no encontrada',
            onBack: onBack,
            onHome: onHome,
          );
        }
        return PlantPassportPage(plant: value, onBack: onBack, onHome: onHome);
      },
      skipLoadingOnRefresh: false,
    );
  }
}

class _PassportStatusPage extends StatelessWidget {
  const _PassportStatusPage({
    required this.title,
    required this.onBack,
    required this.onHome,
    this.message,
    this.action,
  });
  final String title;
  final String? message;
  final VoidCallback onBack;
  final VoidCallback onHome;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: _background,
    body: SafeArea(
      child: Column(
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: SizedBox(
              width: 48,
              height: 48,
              child: IconButton(
                tooltip: 'Volver a Explorar',
                onPressed: onBack,
                icon: const Icon(Icons.chevron_left, color: _green),
              ),
            ),
          ),
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        title,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      if (message != null) ...[
                        const SizedBox(height: 8),
                        Text(message!, textAlign: TextAlign.center),
                      ],
                      if (action != null) ...[
                        const SizedBox(height: 16),
                        action!,
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
    bottomNavigationBar: SafeArea(
      top: false,
      child: _PassportBottomBar(onHome: onHome),
    ),
  );
}

class _PassportBottomBar extends StatelessWidget {
  const _PassportBottomBar({required this.onHome});
  final VoidCallback onHome;
  @override
  Widget build(BuildContext context) => Material(
    color: Theme.of(context).colorScheme.surface,
    child: LayoutBuilder(
      builder: (context, constraints) {
        final scaler = MediaQuery.textScalerOf(context);
        final fontSize = Theme.of(context).textTheme.labelSmall?.fontSize ?? 12;
        final largeText = scaler.scale(fontSize) / fontSize >= 1.5;
        final items = [
          _navItem('Inicio', Icons.home, selected: true, onPressed: onHome),
          _navItem('Favoritos', Icons.favorite_border),
          _navItem('Historial', Icons.history),
          _navItem('Perfil', Icons.person_outline),
        ];
        if (!largeText) {
          return Row(
            children: [for (final item in items) Expanded(child: item)],
          );
        }
        return Wrap(
          children: [
            for (final item in items)
              SizedBox(width: constraints.maxWidth / 2, child: item),
          ],
        );
      },
    ),
  );
}

Widget _navItem(
  String label,
  IconData icon, {
  bool selected = false,
  VoidCallback? onPressed,
}) => Semantics(
  label: selected ? label : '$label no disponible',
  button: true,
  selected: selected,
  enabled: onPressed != null,
  onTap: onPressed,
  child: ExcludeSemantics(
    child: ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 56),
      child: InkWell(
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 20, color: selected ? _green : Colors.grey),
              Text(
                label,
                textAlign: TextAlign.center,
                style: TextStyle(color: selected ? _green : Colors.grey),
              ),
            ],
          ),
        ),
      ),
    ),
  ),
);

/// Passport content for an already-resolved plant.
///
/// Content for a catalog-resolved plant; route IDs are handled by
/// [PlantPassportRoutePage].
class PlantPassportPage extends StatefulWidget {
  const PlantPassportPage({
    required this.plant,
    required this.onBack,
    required this.onHome,
    super.key,
  });

  final Plant plant;
  final VoidCallback onBack;
  final VoidCallback onHome;

  @override
  State<PlantPassportPage> createState() => _PlantPassportPageState();
}

class _PlantPassportPageState extends State<PlantPassportPage> {
  int _tab = 0;

  @override
  void didUpdateWidget(covariant PlantPassportPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.plant.id != widget.plant.id) _tab = 0;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: _background,
    body: SafeArea(
      bottom: false,
      child: CustomScrollView(
        key: PageStorageKey('passport-${widget.plant.id}-$_tab'),
        slivers: [
          SliverToBoxAdapter(child: _header()),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
            sliver: SliverList.list(
              children: [
                _tabs(),
                const SizedBox(height: 16),
                if (_tab == 0)
                  _general()
                else if (_tab == 1)
                  _properties()
                else
                  _uses(),
              ],
            ),
          ),
        ],
      ),
    ),
    bottomNavigationBar: SafeArea(
      top: false,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: const _DisabledAction(
              label: 'Ver formulaciones relacionadas',
            ),
          ),
          _PassportBottomBar(onHome: widget.onHome),
        ],
      ),
    ),
  );

  Widget _header() => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
    child: Row(
      children: [
        SizedBox(
          width: 48,
          height: 48,
          child: IconButton(
            tooltip: 'Volver a Explorar',
            onPressed: widget.onBack,
            icon: const Icon(Icons.chevron_left),
            color: _green,
          ),
        ),
        const ExcludeSemantics(
          child: Icon(Icons.local_florist, color: _green, size: 34),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.plant.primaryName,
                style: Theme.of(context).textTheme.titleLarge
                    ?.copyWith(color: _ink),
              ),
              if (widget.plant.secondaryName != null)
                Text(
                  widget.plant.secondaryName!,
                  style: Theme.of(context).textTheme.bodyMedium
                      ?.copyWith(color: _ink),
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

  Widget _tabs() => Wrap(
    spacing: 8,
    runSpacing: 4,
    children: [
      for (var i = 0; i < 3; i++)
        ChoiceChip(
          label: Text(['General', 'Propiedades', 'Usos'][i]),
          selected: _tab == i,
          onSelected: (_) => setState(() => _tab = i),
          materialTapTargetSize: MaterialTapTargetSize.padded,
        ),
    ],
  );

  Widget _general() {
    final plant = widget.plant;
    final commonNames = plant.commonNames;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _field('Familia', plant.family ?? 'No disponible en fuente'),
        if (commonNames.isEmpty)
          _field('Nombres comunes', 'No hay nombres comunes registrados')
        else
          _fieldLines('Nombres comunes', [
            for (final name in commonNames) '${name.text} (${name.language})',
          ]),
        _field(
          'Partes registradas en fuente',
          plant.parts.isEmpty
              ? 'No hay partes registradas en fuente'
              : plant.parts.join(', '),
        ),
        _field('Tipo de aceite', 'No aplicable: ficha de planta'),
        if (plant.uses.isNotEmpty) ...[
          const SizedBox(height: 8),
          _sectionTitle('Referencias bibliográficas'),
          for (final ref in _references()) _field(ref.id, ref.citation),
        ],
      ],
    );
  }

  Widget _properties() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _sectionTitle('Propiedades'),
      const SizedBox(height: 8),
      const Text('sin propiedades medicinales evaluadas en este catálogo'),
    ],
  );

  Widget _uses() {
    final uses = widget.plant.uses;
    if (uses.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionTitle('Usos tradicionales'),
          const SizedBox(height: 8),
          const Text(
            'No hay usos tradicionales con referencia verificable disponibles',
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle('Registros tradicionales'),
        const SizedBox(height: 8),
        const Text(
          'No es una recomendación de uso ni evidencia de eficacia clínica',
        ),
        const SizedBox(height: 12),
        for (final use in uses) ...[
          _field('Registro tradicional', use.activity),
          _field('Referencia: ${use.reference.id}', use.reference.citation),
          const Divider(height: 20),
        ],
      ],
    );
  }

  List<UseReference> _references() {
    final refs = <String, UseReference>{};
    for (final use in widget.plant.uses) {
      refs[use.reference.id] = use.reference;
    }
    return refs.values.toList();
  }

  Widget _fieldLines(String label, List<String> values) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge
              ?.copyWith(color: _green),
        ),
        const SizedBox(height: 3),
        for (final value in values)
          Text(
            value,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: _ink),
          ),
      ],
    ),
  );

  Widget _field(String label, String value) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge
              ?.copyWith(color: _green),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: _ink),
        ),
      ],
    ),
  );

  Widget _sectionTitle(String text) => Text(
    text,
    style: Theme.of(context).textTheme.titleMedium?.copyWith(color: _ink),
  );
}

class _DisabledAction extends StatelessWidget {
  const _DisabledAction({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) => Semantics(
    label: '$label no disponible',
    button: true,
    enabled: false,
    child: ExcludeSemantics(
      child: SizedBox(
        width: double.infinity,
        child: OutlinedButton(onPressed: null, child: Text(label)),
      ),
    ),
  );
}
