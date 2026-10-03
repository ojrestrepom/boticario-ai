import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/plant_catalog_repository.dart';
import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_catalog_provenance.dart';

const _green = Color(0xFF236335);
const _ink = Color(0xFF172A1F);
const _background = Color(0xFFF9FAF7);

/// Route-facing entry point. ID parsing and lookup belong to P05, not router.
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
    final catalog = ref.watch(plantCatalogProvider);
    final id = int.tryParse(plantId);
    return catalog.when(
      loading: () => _PassportStatusPage(
        title: 'Cargando catálogo...',
        onBack: onBack,
        onHome: onHome,
      ),
      error: (_, _) => _PassportStatusPage(
        title: 'No se pudo cargar el catálogo',
        onBack: onBack,
        onHome: onHome,
        action: TextButton(
          onPressed: () => ref.invalidate(plantCatalogProvider),
          child: const Text('Reintentar'),
        ),
      ),
      data: (value) {
        final plant = id == null || id < 0 ? null : value.findById(id);
        if (plant == null) {
          return _PassportStatusPage(
            title: 'Planta no encontrada',
            onBack: onBack,
            onHome: onHome,
          );
        }
        return PlantPassportPage(
          plant: plant,
          provenance: value.provenance,
          onBack: onBack,
          onHome: onHome,
        );
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
    this.action,
  });
  final String title;
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
                      ?action,
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
    child: Row(
      children: [
        _navItem('Inicio', Icons.home, selected: true, onPressed: onHome),
        _navItem('Favoritos', Icons.favorite_border),
        _navItem('Historial', Icons.history),
        _navItem('Perfil', Icons.person_outline),
      ],
    ),
  );
}

Widget _navItem(
  String label,
  IconData icon, {
  bool selected = false,
  VoidCallback? onPressed,
}) => Expanded(
  child: Semantics(
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
  ),
);

/// Passport content for an already-resolved plant.
///
/// Content for a catalog-resolved plant; route IDs are handled by
/// [PlantPassportRoutePage].
class PlantPassportPage extends StatefulWidget {
  const PlantPassportPage({
    required this.plant,
    required this.provenance,
    required this.onBack,
    required this.onHome,
    super.key,
  });

  final Plant plant;
  final PlantCatalogProvenance provenance;
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
    if (oldWidget.plant.usdaPlantId != widget.plant.usdaPlantId) _tab = 0;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: _background,
    body: SafeArea(
      bottom: false,
      child: CustomScrollView(
        key: PageStorageKey('passport-${widget.plant.usdaPlantId}-$_tab'),
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
                widget.plant.editorialCommonName,
                style: Theme.of(context).textTheme.titleLarge
                    ?.copyWith(color: _ink),
              ),
              Text(
                widget.plant.sourceScientificName,
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

  Widget _general() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _field('Nombre común editorial', widget.plant.editorialCommonName),
      _field('Nombre científico de fuente', widget.plant.sourceScientificName),
      _field('Origen', widget.plant.origin ?? 'No disponible en fuente'),
      _field(
        'Descripción',
        widget.plant.description ?? 'No disponible en fuente',
      ),
      _field(
        'Partes registradas en fuente',
        widget.plant.parts.isEmpty
            ? 'No hay partes registradas en fuente'
            : widget.plant.parts
                  .map((p) => '${p.name} (${p.sourceCode})')
                  .join(', '),
      ),
      _field('Tipo de aceite', 'No aplicable: ficha de planta'),
      const SizedBox(height: 8),
      _sectionTitle('Procedencia'),
      _field('Fuente', widget.provenance.sourceName),
      _field('Licencia', widget.provenance.license),
      _field('Versión', widget.provenance.version),
      _field('Dataset', widget.provenance.datasetId),
      _field(
        'Archivo',
        '${widget.provenance.fileName} (ID ${widget.provenance.fileId})',
      ),
      _field('URL de fuente', widget.provenance.sourceUrl),
      _field(
        'Fecha de inspección (no cobertura temporal)',
        _date(widget.provenance.inspectedOn),
      ),
      _field(
        'Cita recomendada de la fuente',
        widget.provenance.recommendedCitation,
      ),
      if (widget.plant.traditionalUses.isNotEmpty) ...[
        const SizedBox(height: 8),
        _sectionTitle('Referencias bibliográficas'),
        for (final ref in _references()) _field(ref.id, ref.citation),
      ],
    ],
  );

  Widget _properties() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _sectionTitle('Propiedades'),
      const SizedBox(height: 8),
      const Text('sin propiedades medicinales evaluadas en este catálogo'),
    ],
  );

  Widget _uses() {
    final uses = widget.plant.traditionalUses;
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
          for (final ref in use.references)
            _field('Fuente: ${ref.id}', ref.citation),
          const Divider(height: 20),
        ],
      ],
    );
  }

  List<PlantReference> _references() {
    final refs = <String, PlantReference>{};
    for (final use in widget.plant.traditionalUses) {
      for (final ref in use.references) {
        refs[ref.id] = ref;
      }
    }
    return refs.values.toList();
  }

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
  String _date(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
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
