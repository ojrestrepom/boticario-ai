import 'dart:async';

import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_results_page.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_search_page.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_subareas_page.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../support/fake_catalog_api.dart';

GoRouter _router(WidgetTester tester) =>
    GoRouter.of(tester.element(find.byType(HomePage)));

Future<FakeCatalogApi> _mount(
  WidgetTester tester, {
  List<Map<String, Object?>>? goals,
}) async {
  final api = FakeCatalogApi(requiredToken: testApiToken, goals: goals);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        httpClientProvider.overrideWithValue(api.client),
        apiTokenProvider.overrideWithValue(testApiToken),
      ],
      child: const BoticarioApp(),
    ),
  );
  await tester.pumpAndSettle();
  return api;
}

Future<void> _openP06(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey(HomeAction.searchByGoal)));
  await tester.pumpAndSettle();
}

Future<void> _tapText(WidgetTester tester, String text) async {
  final finder = find.text(text);
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> _back(WidgetTester tester, {required bool system}) async {
  if (system) {
    await tester.binding.handlePopRoute();
  } else {
    // The app back button is the first IconButton of the visible screen.
    await tester.tap(find.byType(IconButton).hitTestable().first);
  }
  await tester.pumpAndSettle();
}

void main() {
  for (final system in [false, true]) {
    testWidgets('full stack Inicio, P06, subareas, P07, passport and back '
        '(${system ? 'system' : 'app'} back)', (tester) async {
      await _mount(tester);
      final router = _router(tester);
      await _openP06(tester);
      expect(router.state.uri.path, '/goals');
      expect(find.byType(GoalSearchPage), findsOneWidget);

      await _tapText(tester, 'Otros objetivos');
      expect(router.state.uri.path, '/goals/otros-objetivos/subareas');
      expect(find.byType(GoalSubareasPage), findsOneWidget);

      await _tapText(tester, 'Digestión');
      expect(router.state.uri.path, '/goals/otros-objetivos/plants');
      expect(router.state.uri.queryParameters, {'subarea': 'digestion'});
      final results = tester.widget<GoalResultsPage>(
        find.byType(GoalResultsPage),
      );
      expect(results.goalId, 'otros-objetivos');
      expect(results.subareaId, 'digestion');

      unawaited(
        router.push('/goals/otros-objetivos/plants/lavandula-angustifolia'),
      );
      await tester.pumpAndSettle();
      expect(find.byType(PlantPassportPage), findsOneWidget);
      // The passport does not claim to come from Explorar.
      expect(find.byTooltip('Volver a Explorar'), findsNothing);
      expect(find.byTooltip('Volver'), findsOneWidget);

      await _back(tester, system: system);
      expect(find.byType(GoalResultsPage), findsOneWidget);
      expect(router.state.uri.path, '/goals/otros-objetivos/plants');
      expect(router.state.uri.queryParameters, {'subarea': 'digestion'});

      await _back(tester, system: system);
      expect(find.byType(GoalSubareasPage), findsOneWidget);
      expect(router.state.uri.path, '/goals/otros-objetivos/subareas');

      await _back(tester, system: system);
      expect(find.byType(GoalSearchPage), findsOneWidget);
      expect(router.state.uri.path, '/goals');
      // Nothing stays selected after coming back.
      expect(find.text('Mejorar el sueño'), findsOneWidget);

      await _back(tester, system: system);
      expect(find.byType(HomePage), findsOneWidget);
      expect(router.state.uri.path, '/');
      expect(router.canPop(), isFalse);
    });
  }

  testWidgets('a goal without subareas opens P07 straight from P06', (
    tester,
  ) async {
    await _mount(tester);
    final router = _router(tester);
    await _openP06(tester);
    await _tapText(tester, 'Mejorar el sueño');
    expect(router.state.uri.path, '/goals/mejorar-el-sueno/plants');
    expect(router.state.uri.queryParameters, isEmpty);
    expect(
      tester.widget<GoalResultsPage>(find.byType(GoalResultsPage)).subareaId,
      isNull,
    );
    expect(find.byType(GoalSubareasPage), findsNothing);
  });

  testWidgets('Inicio clears the stack from every screen of the flow', (
    tester,
  ) async {
    await _mount(tester);
    final router = _router(tester);

    Future<void> homeFrom(Type page) async {
      await tester.tap(
        find
            .descendant(of: find.byType(page), matching: find.text('Inicio'))
            .first,
      );
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/');
      expect(router.canPop(), isFalse);
      expect(find.byType(HomePage), findsOneWidget);
    }

    await _openP06(tester);
    await homeFrom(GoalSearchPage);

    await _openP06(tester);
    await _tapText(tester, 'Otros objetivos');
    await homeFrom(GoalSubareasPage);

    await _openP06(tester);
    await _tapText(tester, 'Otros objetivos');
    await _tapText(tester, 'Boca y garganta');
    await homeFrom(GoalResultsPage);

    await _openP06(tester);
    await _tapText(tester, 'Mejorar el sueño');
    unawaited(
      router.push('/goals/mejorar-el-sueno/plants/lavandula-angustifolia'),
    );
    await tester.pumpAndSettle();
    await homeFrom(PlantPassportPage);
  });

  testWidgets('ids with reserved characters are encoded and decoded', (
    tester,
  ) async {
    await _mount(
      tester,
      goals: [
        {
          'id': 'a/b c?d',
          'name': 'Raro',
          'plantCount': 1,
          'subareas': <Object?>[],
        },
        {
          'id': 'con-subareas',
          'name': 'Con subáreas',
          'plantCount': 1,
          'subareas': [
            {'id': 'x&y=z/ñ', 'name': 'Subárea rara', 'plantCount': 1},
          ],
        },
      ],
    );
    final router = _router(tester);
    await _openP06(tester);

    await _tapText(tester, 'Raro');
    expect(router.state.uri.path, '/goals/a%2Fb%20c%3Fd/plants');
    expect(
      tester.widget<GoalResultsPage>(find.byType(GoalResultsPage)).goalId,
      'a/b c?d',
    );
    await _back(tester, system: true);

    await _tapText(tester, 'Con subáreas');
    expect(router.state.uri.path, '/goals/con-subareas/subareas');
    await _tapText(tester, 'Subárea rara');
    expect(router.state.uri.queryParameters, {'subarea': 'x&y=z/ñ'});
    expect(
      tester.widget<GoalResultsPage>(find.byType(GoalResultsPage)).subareaId,
      'x&y=z/ñ',
    );

    unawaited(router.push('/goals/a%2Fb%20c%3Fd/plants/rara%2Fplanta'));
    await tester.pumpAndSettle();
    expect(find.byType(PlantPassportRoutePage), findsOneWidget);
    expect(
      tester
          .widget<PlantPassportRoutePage>(find.byType(PlantPassportRoutePage))
          .plantId,
      'rara/planta',
    );
  });
}
