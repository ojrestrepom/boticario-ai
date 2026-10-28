import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/plant_image_policy.dart';
import '../../catalog/domain/goal.dart';
import '../../catalog/domain/plant_consolidated.dart';
import '../../catalog/presentation/plant_photo.dart';
import '../application/goal_results_controller.dart';
import 'goal_list_shell.dart';
import 'goal_results_texts.dart';

/// How many cards before the end of the loaded list the next page is asked
/// for.
const _prefetchDistance = 5;

const _photoHeight = 112.0;

/// P07 («Recomendaciones»): the plants the catalog associates with a goal or
/// subarea, in API order, loaded in pages as the user scrolls.
///
/// Navigation is provided by the app shell. The loaded pages live in
/// [goalResultsControllerProvider] and the scroll offset in this State; both
/// survive while the passport is open on top of this page.
class GoalResultsPage extends ConsumerStatefulWidget {
  const GoalResultsPage({
    required this.goalId,
    required this.onBack,
    required this.onHome,
    required this.onPlantSelected,
    this.subareaId,
    this.backLabel = 'Volver',
    this.imageProviderFor = PlantImagePolicy.thumbnailProviderFor,
    super.key,
  });

  final String goalId;
  final String? subareaId;
  final VoidCallback onBack;
  final VoidCallback onHome;

  /// Receives the API id (slug) of the tapped plant.
  final ValueChanged<String> onPlantSelected;
  final String backLabel;

  /// Provider of the 500 px thumbnail for an `image.url`, or `null`. Tests
  /// replace it; the default never loads the original file.
  final ImageProvider? Function(String? url) imageProviderFor;

  @override
  ConsumerState<GoalResultsPage> createState() => _GoalResultsPageState();
}

class _GoalResultsPageState extends ConsumerState<GoalResultsPage> {
  final _scrollController = ScrollController();

  GoalResultsQuery get _query =>
      (goalId: widget.goalId, subareaId: widget.subareaId);

  GoalResultsController get _controller =>
      ref.read(goalResultsControllerProvider(_query).notifier);

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(goalResultsControllerProvider(_query));
    final name = state.targetName;
    return Scaffold(
      backgroundColor: goalBackground,
      body: SafeArea(
        bottom: false,
        child: CustomScrollView(
          controller: _scrollController,
          slivers: [
            SliverToBoxAdapter(
              child: GoalHeaderBar(
                title: GoalResultsTexts.title,
                backLabel: widget.backLabel,
                onBack: widget.onBack,
              ),
            ),
            if (name != null)
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                sliver: SliverToBoxAdapter(
                  child: Text(
                    GoalResultsTexts.subtitle(name),
                    style: Theme.of(context).textTheme.bodyLarge
                        ?.copyWith(color: goalInk),
                  ),
                ),
              ),
            ..._content(state),
            const SliverPadding(
              padding: EdgeInsets.fromLTRB(16, 8, 16, 16),
              sliver: SliverToBoxAdapter(child: _Notice()),
            ),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: GoalBottomBar(onHome: widget.onHome),
      ),
    );
  }

  List<Widget> _content(GoalResultsState state) {
    Widget box(Widget child) => SliverPadding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      sliver: SliverToBoxAdapter(child: child),
    );
    switch (state.phase) {
      case GoalResultsPhase.loading:
        return [
          box(
            const GoalLoading(
              key: ValueKey('results-loading'),
              label: GoalResultsTexts.loading,
            ),
          ),
        ];
      case GoalResultsPhase.error:
        return [
          box(
            GoalMessage(
              key: const ValueKey('results-error'),
              icon: Icons.error_outline,
              text: state.errorMessage ?? 'No se pudo cargar el catálogo.',
              onRetry: _controller.retry,
            ),
          ),
        ];
      case GoalResultsPhase.notFound:
        return [
          box(
            const GoalMessage(
              key: ValueKey('results-not-found'),
              icon: Icons.search_off,
              text: GoalResultsTexts.notFound,
            ),
          ),
        ];
      case GoalResultsPhase.ready:
        break;
    }
    if (state.items.isEmpty) {
      return [
        box(
          const GoalMessage(
            key: ValueKey('results-empty'),
            icon: Icons.search_off,
            text: GoalResultsTexts.empty,
          ),
        ),
      ];
    }
    final count = state.items.length;
    return [
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
        sliver: SliverList.builder(
          itemCount: count + 1,
          itemBuilder: (context, index) {
            if (index == count) return _footer(state);
            if (index >= count - _prefetchDistance) _requestMoreAfterFrame();
            final plant = state.items[index];
            return _PlantCard(
              key: ValueKey('plant-card-${plant.id}'),
              plant: plant,
              imageProviderFor: widget.imageProviderFor,
              onTap: () => widget.onPlantSelected(plant.id),
            );
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

  Widget _footer(GoalResultsState state) {
    if (state.footerError != null) {
      return GoalMessage(
        key: const ValueKey('results-footer-error'),
        icon: Icons.error_outline,
        text: state.footerError!,
        onRetry: _controller.retryMore,
      );
    }
    if (state.hasMore) {
      return const GoalLoading(
        key: ValueKey('results-footer-loading'),
        label: GoalResultsTexts.loadingMore,
      );
    }
    return const Padding(
      key: ValueKey('results-footer-end'),
      padding: EdgeInsets.symmetric(vertical: 16),
      child: Text(GoalResultsTexts.endOfList, textAlign: TextAlign.center),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice();

  @override
  Widget build(BuildContext context) => Row(
    key: const ValueKey('results-notice'),
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const ExcludeSemantics(child: Icon(Icons.info_outline, color: goalGreen)),
      const SizedBox(width: 8),
      Expanded(
        child: Text(
          GoalResultsTexts.notice,
          style: Theme.of(context).textTheme.bodyMedium
              ?.copyWith(color: goalInk),
        ),
      ),
    ],
  );
}

/// One plant: photo with its credit (only once loaded), names, the EMA line
/// and the precaution mark. The whole card is one button whose accessible
/// name is made of those texts.
class _PlantCard extends StatelessWidget {
  const _PlantCard({
    required this.plant,
    required this.imageProviderFor,
    required this.onTap,
    super.key,
  });

  final GoalPlant plant;
  final ImageProvider? Function(String? url) imageProviderFor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final secondary = plant.secondaryName;
    final mark = _markText(plant);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: goalBorder),
        ),
        child: MergeSemantics(
          child: Semantics(
            button: true,
            onTap: onTap,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: onTap,
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 48),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _photo(context),
                      Text(
                        plant.primaryName,
                        style: theme.titleMedium?.copyWith(color: goalInk),
                      ),
                      if (secondary != null)
                        Text(
                          secondary,
                          style: theme.bodyMedium?.copyWith(color: goalInk),
                        ),
                      const SizedBox(height: 4),
                      Text(
                        GoalResultsTexts.emaLine(plant.areas),
                        style: theme.bodyMedium?.copyWith(color: goalInk),
                      ),
                      if (mark != null) ...[
                        const SizedBox(height: 6),
                        _Mark(text: mark, warning: _isCaution(plant)),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _photo(BuildContext context) {
    const art = PlantArtPlaceholder(height: _photoHeight, iconSize: 48);
    final image = plant.image;
    final provider = image == null ? null : imageProviderFor(image.url);
    final Widget content;
    if (image == null || provider == null) {
      content = art;
    } else {
      content = PlantPhotoImage(
        provider: provider,
        height: _photoHeight,
        placeholder: art,
        failed: art,
        loaded: (context, photo) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(borderRadius: BorderRadius.circular(12), child: photo),
            const SizedBox(height: 4),
            Text(
              GoalResultsTexts.photoCredit(image.author, image.license),
              style: Theme.of(context).textTheme.bodySmall
                  ?.copyWith(color: goalInk),
            ),
          ],
        ),
      );
    }
    return Padding(padding: const EdgeInsets.only(bottom: 8), child: content);
  }
}

bool _isCaution(GoalPlant plant) =>
    plant.safetyLevel == SafetyLevel.high ||
    plant.safetyLevel == SafetyLevel.medium;

/// Text of the mark, or `null` when the card shows none: `Precaución` only
/// for `alto` and `medio`; the no-data text only without any safety data;
/// nothing for `bajo` or for precautions without a level.
String? _markText(GoalPlant plant) {
  if (_isCaution(plant)) return GoalResultsTexts.caution;
  if (!plant.hasSafety) return GoalResultsTexts.noSafetyData;
  return null;
}

class _Mark extends StatelessWidget {
  const _Mark({required this.text, required this.warning});

  final String text;
  final bool warning;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      ExcludeSemantics(
        child: Icon(
          warning ? Icons.warning_amber_rounded : Icons.help_outline,
          size: 20,
          color: warning ? const Color(0xFF8A4B00) : goalInk,
        ),
      ),
      const SizedBox(width: 6),
      Expanded(
        child: Text(
          text,
          style: Theme.of(context).textTheme.labelLarge
              ?.copyWith(color: warning ? const Color(0xFF8A4B00) : goalInk),
        ),
      ),
    ],
  );
}
