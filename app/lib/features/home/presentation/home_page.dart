import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'home_action.dart';

/// Color de acento provisional D5 (no es token de marca final).
const Color _homeAccent = Color(0xFF236335);

/// Color de texto provisional D5 (no es token de marca final).
const Color _homeText = Color(0xFF172A1F);

/// Fondo provisional D5 (no es token de marca final).
const Color _homeBackground = Color(0xFFF9FAF7);

/// Fondo de tarjeta provisional D5 (no es token de marca final).
const Color _homeCardBackground = Color(0xFFF3F5F2);

/// Borde provisional D5 (no es token de marca final).
const Color _homeBorder = Color(0xFFD6DDD4);

/// Fondo crema provisional del banner D5 (no es token de marca final).
const Color _bannerBackground = Color(0xFFFBF2D4);

/// Emite una sola vez el mensaje de [action] si el modo de depuración lo permite.
///
/// Único punto de emisión: el cálculo puro decide el mensaje y aquí solo se llama
/// `debugPrint` cuando no es nulo. No se invoca desde `build`, así que no hay
/// logs por render, rebuild ni recarga en caliente.
void _emitHomeAction(HomeAction action) {
  final message = homeActionMessage(action, isDebugMode: kDebugMode);
  if (message != null) {
    debugPrint(message);
  }
}

/// Pantalla Inicio (P03): estructura visual de partida de la ruta `/`.
///
/// Sin estado ni providers: cada control emite su acción de depuración.
/// Explorar, Buscar por objetivo e Identificar planta delegan su navegación
/// a callbacks requeridos. Compone cabecera, banner, cuadrícula 2x2, CTA
/// y barra inferior con `Inicio` siempre seleccionado.
class HomePage extends StatelessWidget {
  const HomePage({
    super.key,
    required this.onExplore,
    required this.onSearchByGoal,
    required this.onIdentifyPlant,
  });

  final VoidCallback onExplore;
  final VoidCallback onSearchByGoal;
  final VoidCallback onIdentifyPlant;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _homeBackground,
      body: SafeArea(
        // El inset inferior lo cubre la barra inferior, no el cuerpo.
        bottom: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _HomeHeader(
                onMenuPressed: () => _emitHomeAction(HomeAction.headerMenu),
                onProfilePressed: () =>
                    _emitHomeAction(HomeAction.headerProfile),
              ),
              const SizedBox(height: 12),
              const _BotanicalBanner(),
              const SizedBox(height: 12),
              ..._buildFeatureGrid(context),
              const SizedBox(height: 12),
              _AskBoticarioCta(
                onPressed: () => _emitHomeAction(HomeAction.askTheBoticario),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const SafeArea(
        // La barra inferior aporta su propio inset; el cuerpo ya cubre el resto.
        top: false,
        child: _HomeBottomBar(),
      ),
    );
  }

  /// Cuadrícula de las 4 tarjetas: 2 columnas al 100% y 1 columna cuando la
  /// escala de texto alcanza el umbral de una columna.
  List<Widget> _buildFeatureGrid(BuildContext context) {
    final cards = <Widget>[
      _FeatureCard(
        action: HomeAction.explorePlantsAndOils,
        icon: Icons.eco,
        label: 'Explorar plantas y aceites',
        onPressed: () {
          _emitHomeAction(HomeAction.explorePlantsAndOils);
          onExplore();
        },
      ),
      _FeatureCard(
        action: HomeAction.searchByGoal,
        icon: Icons.track_changes,
        label: 'Buscar por objetivo',
        onPressed: () {
          _emitHomeAction(HomeAction.searchByGoal);
          onSearchByGoal();
        },
      ),
      _FeatureCard(
        action: HomeAction.identifyWithCamera,
        icon: Icons.photo_camera,
        label: 'Identificar con cámara',
        onPressed: () {
          _emitHomeAction(HomeAction.identifyWithCamera);
          onIdentifyPlant();
        },
      ),
      _FeatureCard(
        action: HomeAction.formulateBlends,
        icon: Icons.science,
        label: 'Formular mezclas',
        onPressed: () => _emitHomeAction(HomeAction.formulateBlends),
      ),
    ];

    if (_useSingleColumn(context)) {
      return [
        for (var i = 0; i < cards.length; i++) ...[
          if (i > 0) const SizedBox(height: 12),
          cards[i],
        ],
      ];
    }

    return [
      _FeatureCardPair(left: cards[0], right: cards[1]),
      const SizedBox(height: 12),
      _FeatureCardPair(left: cards[2], right: cards[3]),
    ];
  }
}

/// Umbral de escala de texto a partir del cual la cuadrícula pasa a 1 columna.
const double _singleColumnThreshold = 1.5;

/// Indica si la cuadrícula debe usar una sola columna por escala de texto.
///
/// Usa `TextScaler.scale(fontSize) / fontSize` (API vigente) sobre el tamaño de
/// `bodyMedium`, sin fijar `MediaQuery` ni asumir un factor constante.
bool _useSingleColumn(BuildContext context) {
  final double fontSize =
      Theme.of(context).textTheme.bodyMedium?.fontSize ?? 14;
  final TextScaler textScaler = MediaQuery.textScalerOf(context);
  return textScaler.scale(fontSize) / fontSize >= _singleColumnThreshold;
}

/// Par de tarjetas de la cuadrícula a 2 columnas, con alturas igualadas.
class _FeatureCardPair extends StatelessWidget {
  const _FeatureCardPair({required this.left, required this.right});

  final Widget left;
  final Widget right;

  @override
  Widget build(BuildContext context) {
    // `IntrinsicHeight` acota la altura para igualar el par; solo hay 4 tarjetas
    // y no se anida `LayoutBuilder` dentro, evitando constraints infinitas.
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(child: left),
          const SizedBox(width: 12),
          Expanded(child: right),
        ],
      ),
    );
  }
}

/// Tarjeta de acceso con icono arriba, label vivo centrado y callback.
class _FeatureCard extends StatelessWidget {
  const _FeatureCard({
    required this.action,
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final HomeAction action;
  final IconData icon;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final TextStyle? labelStyle = Theme.of(context).textTheme.bodyMedium
        ?.copyWith(color: _homeText);

    return Semantics(
      button: true,
      label: label,
      excludeSemantics: true,
      onTap: onPressed,
      child: Material(
        color: _homeCardBackground,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: _homeBorder),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: ValueKey(action),
          onTap: onPressed,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Icono decorativo: la lectura la aporta el label de la tarjeta.
                  ExcludeSemantics(
                    child: Icon(icon, size: 32, color: _homeAccent),
                  ),
                  const SizedBox(height: 12),
                  Text(label, textAlign: TextAlign.center, style: labelStyle),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// CTA de ancho completo que pregunta al Boticario; fondo claro y borde.
class _AskBoticarioCta extends StatelessWidget {
  const _AskBoticarioCta({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      key: const ValueKey(HomeAction.askTheBoticario),
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: _homeText,
        minimumSize: const Size.fromHeight(48),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        side: const BorderSide(color: _homeBorder),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: Theme.of(context).textTheme.labelLarge,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Icono de chat decorativo: el label lo aporta el texto del botón.
          const ExcludeSemantics(
            child: Icon(Icons.chat_bubble_outline, size: 24),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text('Preguntar al Boticario', textAlign: TextAlign.center),
          ),
        ],
      ),
    );
  }
}

/// Cabecera de Inicio: menú a la izquierda, marca `Boticario AI` con hojas
/// decorativas al centro y perfil a la derecha.
class _HomeHeader extends StatelessWidget {
  const _HomeHeader({
    required this.onMenuPressed,
    required this.onProfilePressed,
  });

  final VoidCallback onMenuPressed;
  final VoidCallback onProfilePressed;

  @override
  Widget build(BuildContext context) {
    final TextStyle? brandStyle = Theme.of(context).textTheme.titleLarge
        ?.copyWith(color: _homeText);

    return Row(
      children: [
        IconButton(
          key: const ValueKey(HomeAction.headerMenu),
          onPressed: onMenuPressed,
          iconSize: 32,
          color: _homeAccent,
          icon: const Icon(Icons.menu, semanticLabel: 'Menú'),
        ),
        Expanded(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Hoja decorativa del logo: no declara acción ni lectura propia.
              const ExcludeSemantics(
                child: Icon(Icons.eco, size: 32, color: _homeAccent),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  'Boticario AI',
                  textAlign: TextAlign.center,
                  style: brandStyle,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          key: const ValueKey(HomeAction.headerProfile),
          onPressed: onProfilePressed,
          iconSize: 32,
          color: _homeAccent,
          icon: const Icon(Icons.person, semanticLabel: 'Perfil de cabecera'),
        ),
      ],
    );
  }
}

/// Banner botánico decorativo con su frase viva, sin acción asociada.
class _BotanicalBanner extends StatelessWidget {
  const _BotanicalBanner();

  @override
  Widget build(BuildContext context) {
    final TextStyle? phraseStyle = Theme.of(context).textTheme.titleMedium
        ?.copyWith(color: _homeText, fontStyle: FontStyle.italic);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _bannerBackground,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          // Motivos decorativos locales: no se exponen a accesibilidad.
          const ExcludeSemantics(
            child: Icon(Icons.local_florist, size: 32, color: _homeAccent),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              'Pequeñas esencias, grandes posibilidades',
              textAlign: TextAlign.center,
              style: phraseStyle,
            ),
          ),
          const SizedBox(width: 12),
          const ExcludeSemantics(
            child: Icon(Icons.eco, size: 32, color: _homeAccent),
          ),
        ],
      ),
    );
  }
}

/// Barra inferior inmóvil: `Inicio` siempre seleccionado, sin navegación.
class _HomeBottomBar extends StatelessWidget {
  const _HomeBottomBar();

  @override
  Widget build(BuildContext context) {
    return Material(
      color: _homeBackground,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: _homeBorder)),
        ),
        child: Row(
          children: [
            Expanded(
              child: _HomeTab(
                action: HomeAction.tabHome,
                icon: Icons.home,
                label: 'Inicio',
                selected: true,
                onPressed: () => _emitHomeAction(HomeAction.tabHome),
              ),
            ),
            Expanded(
              child: _HomeTab(
                action: HomeAction.tabFavorites,
                icon: Icons.favorite_border,
                label: 'Favoritos',
                selected: false,
                onPressed: () => _emitHomeAction(HomeAction.tabFavorites),
              ),
            ),
            Expanded(
              child: _HomeTab(
                action: HomeAction.tabHistory,
                icon: Icons.history,
                label: 'Historial',
                selected: false,
                onPressed: () => _emitHomeAction(HomeAction.tabHistory),
              ),
            ),
            Expanded(
              child: _HomeTab(
                action: HomeAction.tabProfile,
                icon: Icons.person_outline,
                label: 'Perfil',
                selected: false,
                onPressed: () => _emitHomeAction(HomeAction.tabProfile),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Destino de la barra inferior: tappable, con label siempre visible.
class _HomeTab extends StatelessWidget {
  const _HomeTab({
    required this.action,
    required this.icon,
    required this.label,
    required this.selected,
    required this.onPressed,
  });

  final HomeAction action;
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final Color color = selected ? _homeAccent : _homeText;
    final TextStyle? labelStyle = Theme.of(context).textTheme.labelSmall
        ?.copyWith(color: color);

    return Semantics(
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      onTap: onPressed,
      child: InkWell(
        key: ValueKey(action),
        onTap: onPressed,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Icono decorativo: el label del destino ya se anuncia.
                ExcludeSemantics(child: Icon(icon, size: 32, color: color)),
                const SizedBox(height: 4),
                Text(label, textAlign: TextAlign.center, style: labelStyle),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
