import 'package:flutter/material.dart';

import '../application/goal_catalog_controller.dart';

const goalGreen = Color(0xFF236335);
const goalInk = Color(0xFF172A1F);
const goalBackground = Color(0xFFF9FAF7);
const goalBorder = Color(0xFFD6DDD4);

/// Icon of a goal row by API identifier; unknown ids get [genericGoalIcon].
const goalIcons = <String, IconData>{
  'relajacion-estres': Icons.spa_outlined,
  'mejorar-el-sueno': Icons.nightlight_outlined,
  'cuidado-de-la-piel': Icons.face_retouching_natural_outlined,
  'alivio-respiratorio': Icons.air,
  'cansancio-y-fatiga': Icons.bolt_outlined,
  'otros-objetivos': Icons.more_horiz,
};

const genericGoalIcon = Icons.eco_outlined;

IconData goalIconFor(String id) => goalIcons[id] ?? genericGoalIcon;

/// Screen frame shared by P06 and the subareas screen: header with back
/// button, optional subtitle, the content and the shared bottom bar.
class GoalListShell extends StatelessWidget {
  const GoalListShell({
    required this.title,
    required this.backLabel,
    required this.onBack,
    required this.onHome,
    required this.children,
    this.subtitle,
    super.key,
  });

  final String title;
  final String? subtitle;
  final String backLabel;
  final VoidCallback onBack;
  final VoidCallback onHome;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: goalBackground,
    body: SafeArea(
      bottom: false,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: GoalHeaderBar(
              title: title,
              backLabel: backLabel,
              onBack: onBack,
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            sliver: SliverList.list(
              children: [
                if (subtitle != null) ...[
                  Text(
                    subtitle!,
                    style: Theme.of(context).textTheme.bodyLarge
                        ?.copyWith(color: goalInk),
                  ),
                  const SizedBox(height: 16),
                ],
                ...children,
              ],
            ),
          ),
        ],
      ),
    ),
    bottomNavigationBar: SafeArea(
      top: false,
      child: GoalBottomBar(onHome: onHome),
    ),
  );
}

/// Header of the goal screens: back button and centered title.
class GoalHeaderBar extends StatelessWidget {
  const GoalHeaderBar({
    required this.title,
    required this.backLabel,
    required this.onBack,
    super.key,
  });

  final String title;
  final String backLabel;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 4, 4, 4),
    child: Row(
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          child: Semantics(
            label: backLabel,
            button: true,
            onTap: onBack,
            excludeSemantics: true,
            child: IconButton(
              tooltip: backLabel,
              onPressed: onBack,
              icon: const Icon(Icons.chevron_left),
              color: goalGreen,
            ),
          ),
        ),
        Expanded(
          child: Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(color: goalInk),
          ),
        ),
        const SizedBox(width: 48),
      ],
    ),
  );
}

/// Shared bottom bar with Inicio selected; the other three have no action.
class GoalBottomBar extends StatelessWidget {
  const GoalBottomBar({required this.onHome, super.key});

  final VoidCallback onHome;

  @override
  Widget build(BuildContext context) {
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
      color: goalBackground,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: goalBorder)),
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
    final color = selected ? goalGreen : goalInk;
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

/// One row of P06 or of the subareas screen: a button named after [label]
/// with a decorative icon and chevron. It keeps no selection.
class GoalRow extends StatelessWidget {
  const GoalRow({
    required this.label,
    required this.icon,
    required this.onTap,
    super.key,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: goalBorder),
      ),
      child: Semantics(
        button: true,
        label: label,
        onTap: onTap,
        excludeSemantics: true,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
              child: Row(
                children: [
                  Icon(icon, color: goalGreen, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      label,
                      style: Theme.of(context).textTheme.titleMedium
                          ?.copyWith(color: goalInk),
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: goalGreen),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

/// Loading, error or empty content of a goal list.
class GoalMessage extends StatelessWidget {
  const GoalMessage({
    required this.icon,
    required this.text,
    this.onRetry,
    super.key,
  });

  final IconData icon;
  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      const SizedBox(height: 24),
      ExcludeSemantics(child: Icon(icon, size: 40, color: goalGreen)),
      const SizedBox(height: 8),
      Text(
        text,
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: goalInk),
      ),
      if (onRetry != null) ...[
        const SizedBox(height: 8),
        OutlinedButton(onPressed: onRetry, child: const Text('Reintentar')),
      ],
    ],
  );
}

/// Loading indicator with an accessible label.
class GoalLoading extends StatelessWidget {
  const GoalLoading({required this.label, super.key});

  final String label;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 24),
    child: Center(
      child: Semantics(
        label: label,
        child: const SizedBox.square(
          dimension: 40,
          child: CircularProgressIndicator(),
        ),
      ),
    ),
  );
}

/// Shows the status of the goal catalog (loading or error) or `null` when it
/// is ready.
Widget? goalCatalogStatus(GoalCatalogState state, VoidCallback onRetry) {
  switch (state.phase) {
    case GoalCatalogPhase.loading:
      return const GoalLoading(
        key: ValueKey('goals-loading'),
        label: 'Cargando objetivos',
      );
    case GoalCatalogPhase.error:
      return GoalMessage(
        key: const ValueKey('goals-error'),
        icon: Icons.error_outline,
        text: state.errorMessage ?? 'No se pudo cargar el catálogo.',
        onRetry: onRetry,
      );
    case GoalCatalogPhase.ready:
      return null;
  }
}
