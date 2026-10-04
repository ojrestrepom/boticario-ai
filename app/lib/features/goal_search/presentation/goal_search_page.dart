import 'package:flutter/material.dart';

const _green = Color(0xFF236335);
const _ink = Color(0xFF172A1F);
const _background = Color(0xFFF9FAF7);
const _border = Color(0xFFD6DDD4);

/// Presentational P06 screen. Goal rows are intentionally not interactive.
class GoalSearchPage extends StatelessWidget {
  const GoalSearchPage({required this.onBack, required this.onHome, super.key});

  final VoidCallback onBack;
  final VoidCallback onHome;

  static const _goals = <(String, IconData)>[
    ('Relajación / Estrés', Icons.spa_outlined),
    ('Mejorar el sueño', Icons.nightlight_outlined),
    ('Cuidado de la piel', Icons.face_retouching_natural_outlined),
    ('Alivio respiratorio', Icons.air),
    ('Concentración', Icons.center_focus_strong_outlined),
    ('Otros objetivos', Icons.more_horiz),
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: _background,
    body: SafeArea(
      bottom: false,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(child: _header(context)),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            sliver: SliverList.list(
              children: [
                Text(
                  'Selecciona un objetivo principal',
                  style: Theme.of(context).textTheme.bodyLarge
                      ?.copyWith(color: _ink),
                ),
                const SizedBox(height: 16),
                for (final (label, icon) in _goals) ...[
                  _goalRow(context, label, icon),
                  const SizedBox(height: 10),
                ],
              ],
            ),
          ),
        ],
      ),
    ),
    bottomNavigationBar: SafeArea(top: false, child: _bottomBar(context)),
  );

  Widget _header(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 4, 4, 4),
    child: Row(
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          child: Semantics(
            label: 'Volver a Inicio',
            button: true,
            onTap: onBack,
            excludeSemantics: true,
            child: IconButton(
              tooltip: 'Volver a Inicio',
              onPressed: onBack,
              icon: const Icon(Icons.chevron_left),
              color: _green,
            ),
          ),
        ),
        Expanded(
          child: Text(
            '¿Qué deseas lograr?',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(color: _ink),
          ),
        ),
        const SizedBox(width: 48),
      ],
    ),
  );

  Widget _goalRow(BuildContext context, String label, IconData icon) =>
      DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _border),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
          child: Row(
            children: [
              ExcludeSemantics(child: Icon(icon, color: _green, size: 28)),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(context).textTheme.titleMedium
                      ?.copyWith(color: _ink),
                ),
              ),
              const ExcludeSemantics(
                child: Icon(Icons.chevron_right, color: _green),
              ),
            ],
          ),
        ),
      );

  Widget _bottomBar(BuildContext context) {
    final fontSize = Theme.of(context).textTheme.labelSmall?.fontSize ?? 12;
    final largeText =
        MediaQuery.textScalerOf(context).scale(fontSize) / fontSize >= 1.5;
    final tabs = <Widget>[
      _tab(context, 'Inicio', Icons.home, onTap: onHome, selected: true),
      _tab(context, 'Favoritos', Icons.favorite_border),
      _tab(context, 'Historial', Icons.history),
      _tab(context, 'Perfil', Icons.person_outline),
    ];
    return Material(
      color: _background,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: _border)),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) => largeText
              ? Wrap(
                  children: [
                    for (final tab in tabs)
                      SizedBox(width: constraints.maxWidth / 2, child: tab),
                  ],
                )
              : Row(children: [for (final tab in tabs) Expanded(child: tab)]),
        ),
      ),
    );
  }

  Widget _tab(
    BuildContext context,
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
          constraints: const BoxConstraints(minHeight: 56, minWidth: 48),
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
