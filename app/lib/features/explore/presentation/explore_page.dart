import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/plant_catalog_repository.dart';
import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_search.dart';

const _green = Color(0xFF236335);
const _ink = Color(0xFF172A1F);
const _background = Color(0xFFF9FAF7);
const _border = Color(0xFFD6DDD4);

/// Local catalog browser. Navigation is provided by the app shell so this
/// widget can be tested and reused without introducing a route of its own.
class ExplorePage extends ConsumerStatefulWidget {
  const ExplorePage({
    required this.onBack,
    required this.onHome,
    required this.onPlantSelected,
    super.key,
  });

  final VoidCallback onBack;
  final VoidCallback onHome;
  final ValueChanged<int> onPlantSelected;

  @override
  ConsumerState<ExplorePage> createState() => _ExplorePageState();
}

class _ExplorePageState extends ConsumerState<ExplorePage> {
  final _queryController = TextEditingController();
  final _scrollController = ScrollController();
  PlantFilter _filter = PlantFilter.all;

  @override
  void dispose() {
    _queryController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final catalog = ref.watch(plantCatalogProvider);
    return Scaffold(
      backgroundColor: _background,
      body: SafeArea(
        bottom: false,
        child: CustomScrollView(
          controller: _scrollController,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          slivers: [
            SliverToBoxAdapter(child: _header()),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              sliver: SliverList.list(
                children: [
                  _searchField(),
                  const SizedBox(height: 12),
                  _filters(),
                  const SizedBox(height: 12),
                  catalog.when(
                    loading: () => const _Message(
                      key: ValueKey('catalog-loading'),
                      icon: Icons.hourglass_empty,
                      text: 'Cargando catálogo...',
                    ),
                    error: (error, stack) => _errorState(),
                    data: (value) => _results(value),
                    skipLoadingOnRefresh: false,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(top: false, child: _bottomBar()),
    );
  }

  Widget _header() => Padding(
    padding: const EdgeInsets.fromLTRB(4, 4, 4, 4),
    child: Row(
      children: [
        IconButton(
          tooltip: 'Volver a Inicio',
          onPressed: widget.onBack,
          icon: const Icon(Icons.chevron_left),
          color: _green,
        ),
        Expanded(
          child: Text(
            'Explorar',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(color: _ink),
          ),
        ),
        const SizedBox(width: 48),
      ],
    ),
  );

  Widget _searchField() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      ExcludeSemantics(
        child: Text(
          'Buscar planta o aceite',
          style: Theme.of(context).textTheme.labelLarge,
        ),
      ),
      const SizedBox(height: 4),
      Semantics(
        label: 'Buscar planta o aceite',
        child: TextField(
          controller: _queryController,
          onChanged: (_) => setState(() {}),
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            hint: const ExcludeSemantics(
              child: Text('Buscar planta o aceite...'),
            ),
            hintMaxLines: 4,
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _queryController.text.isEmpty
                ? null
                : IconButton(
                    tooltip: 'Borrar búsqueda',
                    onPressed: () {
                      _queryController.clear();
                      setState(() {});
                    },
                    icon: const Icon(Icons.clear),
                  ),
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      ),
    ],
  );

  Widget _filters() => Wrap(
    spacing: 8,
    runSpacing: 4,
    children: [
      for (final entry in const [
        (PlantFilter.all, 'Todas'),
        (PlantFilter.plants, 'Plantas'),
        (PlantFilter.oils, 'Aceites'),
      ])
        ChoiceChip(
          label: Text(entry.$2),
          selected: _filter == entry.$1,
          onSelected: (_) => setState(() => _filter = entry.$1),
          materialTapTargetSize: MaterialTapTargetSize.padded,
        ),
    ],
  );

  Widget _results(PlantCatalog catalog) {
    final plants = searchPlants(
      catalog.plants,
      query: _queryController.text,
      filter: _filter,
    );
    if (plants.isEmpty) {
      return _Message(
        key: ValueKey(
          _filter == PlantFilter.oils ? 'empty-oils' : 'empty-search',
        ),
        icon: Icons.search_off,
        text: _filter == PlantFilter.oils
            ? 'No hay aceites disponibles en este catálogo'
            : 'No se encontraron plantas',
      );
    }
    return Column(children: [for (final plant in plants) _plantRow(plant)]);
  }

  Widget _plantRow(Plant plant) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: _border),
      ),
      child: Semantics(
        button: true,
        label: '${plant.editorialCommonName}, ${plant.sourceScientificName}',
        onTap: () => widget.onPlantSelected(plant.usdaPlantId),
        excludeSemantics: true,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => widget.onPlantSelected(plant.usdaPlantId),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const ExcludeSemantics(
                  child: Icon(Icons.local_florist, color: _green, size: 32),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        plant.editorialCommonName,
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(color: _ink),
                      ),
                      Text(
                        plant.sourceScientificName,
                        style: Theme.of(context).textTheme.bodyMedium
                            ?.copyWith(color: _ink),
                      ),
                    ],
                  ),
                ),
                const ExcludeSemantics(
                  child: Icon(Icons.chevron_right, color: _green),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );

  Widget _errorState() => Column(
    children: [
      const _Message(
        icon: Icons.error_outline,
        text: 'No se pudo cargar el catálogo local.',
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: () => ref.invalidate(plantCatalogProvider),
        child: const Text('Reintentar'),
      ),
    ],
  );

  Widget _bottomBar() => Material(
    color: _background,
    child: DecoratedBox(
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: _border)),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final scaler = MediaQuery.textScalerOf(context);
          final fontSize =
              Theme.of(context).textTheme.labelSmall?.fontSize ?? 12;
          final largeText = scaler.scale(fontSize) / fontSize >= 1.5;
          final tabs = [
            _tab('Inicio', Icons.home, onTap: widget.onHome, selected: true),
            _tab('Favoritos', Icons.favorite_border),
            _tab('Historial', Icons.history),
            _tab('Perfil', Icons.person_outline),
          ];
          if (!largeText) {
            return Row(
              children: [for (final tab in tabs) Expanded(child: tab)],
            );
          }
          return Wrap(
            children: [
              for (final tab in tabs)
                SizedBox(width: constraints.maxWidth / 2, child: tab),
            ],
          );
        },
      ),
    ),
  );

  Widget _tab(
    String label,
    IconData icon, {
    VoidCallback? onTap,
    bool selected = false,
  }) {
    final color = selected ? _green : _ink;
    return Semantics(
      button: true,
      enabled: onTap != null,
      selected: selected,
      label: onTap == null ? '$label no disponible' : label,
      onTap: onTap,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ExcludeSemantics(child: Icon(icon, color: color)),
                Text(
                  label,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelSmall
                      ?.copyWith(color: color),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.text, super.key});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 8),
    child: Column(
      children: [
        ExcludeSemantics(child: Icon(icon, color: _green, size: 32)),
        const SizedBox(height: 8),
        Text(text, textAlign: TextAlign.center),
      ],
    ),
  );
}
