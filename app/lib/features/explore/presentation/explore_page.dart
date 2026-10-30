import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/domain/plant_summary.dart';
import '../application/explore_controller.dart';

const _green = Color(0xFF236335);
const _ink = Color(0xFF172A1F);
const _background = Color(0xFFF9FAF7);
const _border = Color(0xFFD6DDD4);

/// How many rows before the end of the loaded list the next page is asked for.
const _prefetchDistance = 5;

/// Catalog browser backed by the catalog API. Navigation is provided by the
/// app shell so this widget can be tested and reused without introducing a
/// route of its own.
class ExplorePage extends ConsumerStatefulWidget {
  const ExplorePage({
    required this.onBack,
    required this.onHome,
    required this.onPlantSelected,
    super.key,
  });

  final VoidCallback onBack;
  final VoidCallback onHome;

  /// Receives the API id (slug) of the selected plant.
  final ValueChanged<String> onPlantSelected;

  @override
  ConsumerState<ExplorePage> createState() => _ExplorePageState();
}

class _ExplorePageState extends ConsumerState<ExplorePage> {
  late final TextEditingController _queryController;
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // Query, filter and loaded pages live in the controller, so they come
    // back with the page; the scroll offset lives in this State, which stays
    // mounted under the passport route.
    _queryController = TextEditingController(
      text: ref.read(exploreControllerProvider).query,
    );
  }

  @override
  void dispose() {
    _queryController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  ExploreController get _controller =>
      ref.read(exploreControllerProvider.notifier);

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(exploreControllerProvider);
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
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              sliver: SliverList.list(
                children: [
                  _searchField(),
                  const SizedBox(height: 12),
                  _filters(state),
                  const SizedBox(height: 12),
                ],
              ),
            ),
            ..._results(state),
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
          onChanged: (text) {
            setState(() {});
            _controller.setQuery(text);
          },
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
                      _controller.setQuery('');
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

  Widget _filters(ExploreState state) => Wrap(
    spacing: 8,
    runSpacing: 4,
    children: [
      for (final entry in const [
        (ExploreFilter.all, 'Todas'),
        (ExploreFilter.plants, 'Plantas'),
        (ExploreFilter.oils, 'Aceites'),
      ])
        ChoiceChip(
          label: Text(entry.$2),
          selected: state.filter == entry.$1,
          onSelected: (_) => _controller.setFilter(entry.$1),
          materialTapTargetSize: MaterialTapTargetSize.padded,
        ),
    ],
  );

  List<Widget> _results(ExploreState state) {
    Widget box(Widget child) => SliverPadding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      sliver: SliverToBoxAdapter(child: child),
    );
    if (state.showsOils) {
      return [
        box(
          const _Message(
            key: ValueKey('empty-oils'),
            icon: Icons.search_off,
            text: 'No hay aceites disponibles en este catálogo',
          ),
        ),
      ];
    }
    switch (state.phase) {
      case ExplorePhase.loading:
        return [
          box(
            const _Message(
              key: ValueKey('catalog-loading'),
              icon: Icons.hourglass_empty,
              text: 'Cargando catálogo...',
            ),
          ),
        ];
      case ExplorePhase.error:
        return [box(_errorState(state.errorMessage))];
      case ExplorePhase.ready:
        break;
    }
    if (state.items.isEmpty) {
      return [
        box(
          const _Message(
            key: ValueKey('empty-search'),
            icon: Icons.search_off,
            text: 'No se encontraron plantas',
          ),
        ),
      ];
    }
    final count = state.items.length;
    return [
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        sliver: SliverList.builder(
          itemCount: count + 1,
          itemBuilder: (context, index) {
            if (index == count) return _footer(state);
            if (index >= count - _prefetchDistance) _requestMoreAfterFrame();
            return _plantRow(state.items[index]);
          },
        ),
      ),
    ];
  }

  /// The list builder runs during layout, where provider state must not
  /// change; the request waits for the end of the frame. The controller
  /// ignores repeated calls while a page is loading or has failed.
  void _requestMoreAfterFrame() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _controller.loadMore();
    });
  }

  Widget _footer(ExploreState state) {
    if (state.footerError != null) {
      return Padding(
        key: const ValueKey('explore-footer-error'),
        padding: const EdgeInsets.only(top: 8),
        child: Column(
          children: [
            Text(state.footerError!, textAlign: TextAlign.center),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _controller.retryMore,
              child: const Text('Reintentar'),
            ),
          ],
        ),
      );
    }
    if (state.hasMore) {
      return Padding(
        key: const ValueKey('explore-footer-loading'),
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Center(
          child: Semantics(
            label: 'Cargando más resultados',
            child: const SizedBox.square(
              dimension: 32,
              child: CircularProgressIndicator(),
            ),
          ),
        ),
      );
    }
    return const Padding(
      key: ValueKey('explore-footer-end'),
      padding: EdgeInsets.symmetric(vertical: 16),
      child: Text('No hay más resultados', textAlign: TextAlign.center),
    );
  }

  Widget _plantRow(PlantSummary plant) {
    final secondary = plant.secondaryName;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: _border),
        ),
        child: Semantics(
          button: true,
          label: secondary == null
              ? plant.primaryName
              : '${plant.primaryName}, $secondary',
          onTap: () => widget.onPlantSelected(plant.id),
          excludeSemantics: true,
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => widget.onPlantSelected(plant.id),
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
                          plant.primaryName,
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(color: _ink),
                        ),
                        if (secondary != null)
                          Text(
                            secondary,
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
  }

  Widget _errorState(String? message) => Column(
    key: const ValueKey('catalog-error'),
    children: [
      _Message(
        icon: Icons.error_outline,
        text: message ?? 'No se pudo cargar el catálogo.',
      ),
      const SizedBox(height: 8),
      OutlinedButton(
        onPressed: _controller.retry,
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
