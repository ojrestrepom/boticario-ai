import 'dart:convert';
import 'dart:io';

import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final fixture = jsonDecode(
    File('assets/data/plant_catalog.json').readAsStringSync(),
  ) as Map<String, dynamic>;

  Map<String, dynamic> changed(void Function(Map<String, dynamic>) edit) {
    final copy = jsonDecode(jsonEncode(fixture)) as Map<String, dynamic>;
    edit(copy);
    return copy;
  }

  test('loads the packaged asset through the default bundle loader', () async {
    final catalog = await PlantCatalogAssetDataSource().load();
    expect(catalog.plants.map((plant) => plant.usdaPlantId), [
      544,
      401,
      873,
      605,
      619,
    ]);
    expect(catalog.plants.map((plant) => plant.editorialCommonName), [
      'Lavanda',
      'Eucalipto',
      'Romero',
      'Manzanilla',
      'Menta',
    ]);
    expect(
      catalog.plants.fold<int>(0, (n, p) => n + p.traditionalUses.length),
      121,
    );
    expect(catalog.provenance.md5, '45ae44a0544586b8ac22a232beaac344');
    expect(
      catalog.plants.last.sourceScientificName,
      contains('subsp. nothosubsp.'),
    );
    final first = catalog.plants.first;
    expect(first.parts.first.sources.first.selectors, {
      'FNFNUM': 544,
      'PPCO': first.parts.first.sourceCode,
    });
    final use = first.traditionalUses.first;
    expect(use.references.single.id, 'Steinmetz');
    expect(
      use.references.single.source.selectors['LONGREF'],
      use.references.single.citation,
    );
  });

  test(
    'loader injection returns parsed catalog and uses the asset path',
    () async {
      String? requestedPath;
      final catalog = await PlantCatalogAssetDataSource(
        loadAsset: (path) async {
          requestedPath = path;
          return jsonEncode(fixture);
        },
      ).load();
      expect(requestedPath, plantCatalogAssetPath);
      expect(catalog.plants, hasLength(5));
    },
  );

  test('reports safe errors for missing assets and malformed JSON', () async {
    final missing = PlantCatalogAssetDataSource(
      loadAsset: (_) async => throw StateError('private path'),
    );
    await expectLater(
      missing.load(),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse('{'),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    try {
      await missing.load();
    } on PlantCatalogLoadException catch (error) {
      expect(error.message, contains('Inténtalo de nuevo'));
      expect(error.message, isNot(contains('private path')));
    }
  });

  test('rejects wrong root/version and malformed required values', () {
    expect(
      () => PlantCatalogAssetDataSource.parse('[]'),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(changed((v) => v['schemaVersion'] = '1')),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(changed((v) => v['schemaVersion'] = 2)),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(
          changed(
            (v) => (v['provenance'] as Map)['inspectedOn'] = '2026-02-30',
          ),
        ),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(
          changed((v) => (v['plants'] as List)[0]['usdaPlantId'] = '544'),
        ),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(
          changed((v) => (v['provenance'] as Map)['fileSizeBytes'] = 0),
        ),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
  });

  test('rejects duplicate plant/reference IDs and orphan references', () {
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(
          changed((v) => (v['plants'] as List)[1]['usdaPlantId'] = 544),
        ),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    final duplicateReference = changed((v) {
      final references = v['references'] as List;
      final duplicate = jsonDecode(jsonEncode(references.first));
      references.add(duplicate);
    });
    expect(
      () => PlantCatalogAssetDataSource.parse(jsonEncode(duplicateReference)),
      throwsA(
        isA<PlantCatalogLoadException>().having(
          (error) => error.message,
          'message',
          contains('ID bibliográfico duplicado'),
        ),
      ),
    );
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(changed((v) => (v['references'] as List).removeLast())),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
    final orphanReference = changed((v) {
      final references = v['references'] as List;
      final orphan = jsonDecode(jsonEncode(references.first));
      orphan['id'] = 'UnusedReference';
      orphan['source']['selectors']['REFERENCE'] = 'UnusedReference';
      references.add(orphan);
    });
    expect(
      () => PlantCatalogAssetDataSource.parse(jsonEncode(orphanReference)),
      throwsA(
        isA<PlantCatalogLoadException>().having(
          (error) => error.message,
          'message',
          contains('referencias huérfanas'),
        ),
      ),
    );
  });

  test(
    'rejects missing identity, invalid kind, property flag, and use fields',
    () {
      final invalidMutations = <void Function(Map<String, dynamic>)>[
        (v) => (v['plants'] as List)[0].remove('identitySource'),
        (v) => (v['plants'] as List)[0]['kind'] = 'oil',
        (v) => (v['plants'] as List)[0]['propertiesNotEvaluated'] = false,
        (v) =>
            ((v['plants'] as List)[0]['traditionalUses']
                    as List)[0]['referenceIds'] =
                <String>[],
        (v) =>
            ((v['plants'] as List)[0]['traditionalUses']
                    as List)[0]['source']['selectors']['REFERENCE'] =
                '',
        (v) => ((v['plants'] as List)[0]['traditionalUses'] as List)[0].remove(
          'activity',
        ),
        (v) =>
            ((v['plants'] as List)[0]['traditionalUses']
                    as List)[0]['source']['selectors']['GENUS'] =
                'NotLavandula',
        (v) =>
            ((v['plants'] as List)[0]['traditionalUses']
                    as List)[0]['source']['selectors']['SPECIES'] =
                'notangustifolia',
        (v) =>
            ((v['plants'] as List)[0]['traditionalUses']
                    as List)[0]['source']['table'] =
                'FNFTAX',
      ];
      for (final mutate in invalidMutations) {
        expect(
          () => PlantCatalogAssetDataSource.parse(jsonEncode(changed(mutate))),
          throwsA(isA<PlantCatalogLoadException>()),
        );
      }
    },
  );

  test('rejects HTTP URLs without a host', () {
    expect(
      () => PlantCatalogAssetDataSource.parse(
        jsonEncode(
          changed((v) => (v['provenance'] as Map)['sourceUrl'] = 'https://'),
        ),
      ),
      throwsA(isA<PlantCatalogLoadException>()),
    );
  });

  test('non-finite selector numbers become a typed parse error', () {
    final json = jsonEncode(fixture)
        .replaceFirst('"FNFNUM":544', '"FNFNUM":544,"EXTRA":1e999');
    expect(
      () => PlantCatalogAssetDataSource.parse(json),
      throwsA(isA<PlantCatalogLoadException>()),
    );
  });

  test(
    'rejects invalid use identity/reference, taxon, and part association',
    () {
      expect(
        () => PlantCatalogAssetDataSource.parse(
          jsonEncode(
            changed(
              (v) =>
                  ((v['plants'] as List)[0]['traditionalUses']
                          as List)[0]['source']['selectors']
                      .remove('TAXON'),
            ),
          ),
        ),
        throwsA(isA<PlantCatalogLoadException>()),
      );
      expect(
        () => PlantCatalogAssetDataSource.parse(
          jsonEncode(
            changed(
              (v) =>
                  ((v['plants'] as List)[0]['traditionalUses']
                      as List)[0]['referenceIds'] = [
                    'missing',
                  ],
            ),
          ),
        ),
        throwsA(isA<PlantCatalogLoadException>()),
      );
      expect(
        () => PlantCatalogAssetDataSource.parse(
          jsonEncode(
            changed(
              (v) =>
                  ((v['plants'] as List)[0]['traditionalUses']
                          as List)[0]['source']['selectors']['TAXON'] =
                      'Lavandula',
            ),
          ),
        ),
        throwsA(isA<PlantCatalogLoadException>()),
      );
      expect(
        () => PlantCatalogAssetDataSource.parse(
          jsonEncode(
            changed(
              (v) =>
                  ((v['plants'] as List)[0]['parts']
                          as List)[0]['sources'][0]['selectors']['FNFNUM'] =
                      401,
            ),
          ),
        ),
        throwsA(isA<PlantCatalogLoadException>()),
      );
      expect(
        () => PlantCatalogAssetDataSource.parse(
          jsonEncode(changed((v) => (v['plants'] as List)[0]['origin'] = 42)),
        ),
        throwsA(isA<PlantCatalogLoadException>()),
      );
    },
  );

  test('accepts null optional editorial fields', () {
    final catalog = PlantCatalogAssetDataSource.parse(jsonEncode(fixture));
    expect(
      catalog.plants.every(
        (plant) => plant.origin == null && plant.description == null,
      ),
      isTrue,
    );
  });
}
