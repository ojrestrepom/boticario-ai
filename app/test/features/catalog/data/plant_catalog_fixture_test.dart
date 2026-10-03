import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  final file = File('assets/data/plant_catalog.json');

  test('offline snapshot manifest and five curated identities are intact', () {
    final root = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
    expect(root['schemaVersion'], 1);
    final manifest = root['provenance'] as Map<String, dynamic>;
    expect(manifest['sourceName'], contains('USDA Dr. Duke'));
    expect(manifest['license'], 'CC0');
    expect(manifest['version'], '1');
    expect(manifest['datasetId'], '24660351');
    expect(manifest['fileId'], '43363335');
    expect(manifest['fileName'], 'Duke-Source-CSV.zip');
    expect(manifest['fileSizeBytes'], 6033990);
    expect(manifest['md5'], '45ae44a0544586b8ac22a232beaac344');
    expect(manifest['inspectedOn'], '2026-10-01');
    expect(manifest['recommendedCitation'], contains('Duke, James A. (2016)'));

    final plants = root['plants'] as List<dynamic>;
    expect(
      plants
          .map(
            (item) => [
              item['usdaPlantId'],
              item['editorialCommonName'],
              item['sourceScientificName'],
            ],
          )
          .toList(),
      [
        [544, 'Lavanda', 'Lavandula angustifolia'],
        [401, 'Eucalipto', 'Eucalyptus globulus'],
        [873, 'Romero', 'Rosmarinus officinalis'],
        [605, 'Manzanilla', 'Matricaria recutita'],
        [619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'],
      ],
    );
    for (final value in plants) {
      final plant = value as Map<String, dynamic>;
      expect(plant['kind'], 'plant');
      expect(plant['origin'], isNull);
      expect(plant['description'], isNull);
      expect(plant['propertiesNotEvaluated'], isTrue);
      expect((plant['identitySource'] as Map)['table'], 'FNFTAX');
      expect(
        (plant['identitySource'] as Map)['selectors']['FNFNUM'],
        plant['usdaPlantId'],
      );
    }
  });

  test('parts and uses have source selectors and no orphan bibliography', () {
    final root = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
    final refs = <String, Map<String, dynamic>>{
      for (final value in root['references'] as List<dynamic>)
        (value as Map<String, dynamic>)['id'] as String: value,
    };
    expect(refs, isNotEmpty);
    for (final reference in refs.values) {
      expect(reference['citation'], isNotEmpty);
      expect((reference['source'] as Map)['table'], 'REFERENCES');
    }
    for (final value in root['plants'] as List<dynamic>) {
      final plant = value as Map<String, dynamic>;
      for (final part in plant['parts'] as List<dynamic>) {
        final sources = (part as Map)['sources'] as List<dynamic>;
        expect(sources.map((source) => source['table']), [
          'FARMACY_NEW',
          'PARTS',
        ]);
        expect(sources.first['selectors']['FNFNUM'], plant['usdaPlantId']);
        expect(sources.first['selectors']['PPCO'], part['sourceCode']);
        expect(sources.last['selectors']['PPCO'], part['sourceCode']);
      }
      for (final use in plant['traditionalUses'] as List<dynamic>) {
        final source = (use as Map)['source'] as Map;
        expect(source['table'], 'ETHNOBOT');
        expect(
          source['selectors'].keys,
          containsAll([
            'GENUS',
            'SPECIES',
            'TAXON',
            'ACTIVITY',
            'REFERENCE',
            'ETHNO',
          ]),
        );
        expect(use['referenceIds'], isNotEmpty);
        for (final id in use['referenceIds'] as List<dynamic>) {
          expect(refs, contains(id));
        }
      }
    }
  });
}
