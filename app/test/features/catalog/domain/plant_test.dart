import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_catalog_provenance.dart';
import 'package:flutter_test/flutter_test.dart';

PlantCatalog _catalog() => PlantCatalog(
  provenance: PlantCatalogProvenance(
    sourceName: 'Synthetic fixture',
    license: 'CC0',
    version: 'fixture-v1',
    sourceUrl: 'https://example.org/synthetic-dataset',
    datasetId: 'dataset-fixture',
    downloadUrl: 'https://example.org/synthetic-file.zip',
    fileId: 'file-fixture',
    fileName: 'fixture.zip',
    fileSizeBytes: 1,
    md5: 'synthetic',
    inspectedOn: DateTime.utc(2026, 10, 1),
    recommendedCitation: 'Synthetic citation',
  ),
  plants:
      [
        (544, 'Lavanda', 'Lavandula angustifolia'),
        (401, 'Eucalipto', 'Eucalyptus globulus'),
        (873, 'Romero', 'Rosmarinus officinalis'),
        (605, 'Manzanilla', 'Matricaria recutita'),
        (619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
      ].map(
        (row) => Plant(
          usdaPlantId: row.$1,
          editorialCommonName: row.$2,
          sourceScientificName: row.$3,
        ),
      ),
);

void main() {
  test('retains the five required identities, names, and order', () {
    final catalog = _catalog();
    expect(
      catalog.plants
          .map(
            (plant) => (
              plant.usdaPlantId,
              plant.editorialCommonName,
              plant.sourceScientificName,
            ),
          )
          .toList(),
      [
        (544, 'Lavanda', 'Lavandula angustifolia'),
        (401, 'Eucalipto', 'Eucalyptus globulus'),
        (873, 'Romero', 'Rosmarinus officinalis'),
        (605, 'Manzanilla', 'Matricaria recutita'),
        (619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
      ],
    );
  });

  test('unknown IDs return null and duplicate IDs are rejected', () {
    final catalog = _catalog();
    expect(catalog.findById(999), isNull);
    expect(catalog.findById(544)?.editorialCommonName, 'Lavanda');
    final plant = catalog.plants.first;
    expect(
      () =>
          PlantCatalog(provenance: catalog.provenance, plants: [plant, plant]),
      throwsArgumentError,
    );
  });

  test('missing content stays null and plants are not inferred oils', () {
    final plant = _catalog().plants.first;
    expect(plant.origin, isNull);
    expect(plant.description, isNull);
    expect(plant.kind, PlantKind.plant);
    expect(PlantKind.values, [PlantKind.plant]);
    expect(plant.propertiesNotEvaluated, isTrue);
    expect(plant.parts, isEmpty);
    expect(plant.traditionalUses, isEmpty);
  });

  test(
    'catalog, parts, uses, references, and nested selectors are immutable',
    () {
      final selectorsNested = <String, Object?>{
        'ids': <Object?>[1, 2],
      };
      final selectors = <String, Object?>{
        'FNFNUM': 544,
        'nested': selectorsNested,
      };
      final source = SourceRecord(table: 'FNFTAX', selectors: selectors);
      final references = <PlantReference>[
        PlantReference(
          id: 'ref-fixture',
          citation: 'Synthetic citation',
          source: SourceRecord(
            table: 'REFERENCES',
            selectors: {'ID': 'ref-fixture', 'REFERENCE': 'Synthetic citation'},
          ),
        ),
      ];
      final uses = <TraditionalUse>[
        TraditionalUse(
          activity: 'Synthetic activity',
          source: source,
          references: references,
        ),
      ];
      final partSources = <SourceRecord>[
        SourceRecord(
          table: 'FARMACY_NEW',
          selectors: {'FNFNUM': 12, 'PPCO': 'P'},
        ),
        SourceRecord(table: 'PARTS', selectors: {'PPCO': 'P'}),
      ];
      final parts = <PlantPart>[
        PlantPart(
          name: 'Synthetic part',
          sourceCode: 'P',
          sources: partSources,
        ),
      ];
      final plant = Plant(
        usdaPlantId: 12,
        editorialCommonName: 'Synthetic plant',
        sourceScientificName: 'Synthetic species',
        identitySource: source,
        parts: parts,
        traditionalUses: uses,
      );
      final originalPlants = <Plant>[plant];
      final catalog = PlantCatalog(
        plants: originalPlants,
        provenance: _catalog().provenance,
      );

      selectors['FNFNUM'] = 0;
      (selectorsNested['ids']! as List<Object?>).add(3);
      references.clear();
      uses.clear();
      partSources.clear();
      parts.clear();
      originalPlants.clear();

      expect(catalog.plants, [plant]);
      expect(plant.parts, hasLength(1));
      expect(plant.parts.single.sources, hasLength(2));
      expect(plant.parts.single.sources.map((record) => record.table), [
        'FARMACY_NEW',
        'PARTS',
      ]);
      expect(plant.traditionalUses, hasLength(1));
      expect(plant.traditionalUses.single.references, hasLength(1));
      expect(plant.traditionalUses.single.references.single.source.selectors, {
        'ID': 'ref-fixture',
        'REFERENCE': 'Synthetic citation',
      });
      expect(source.selectors['FNFNUM'], 544);
      expect(source.selectors['nested'], {
        'ids': [1, 2],
      });
      expect(() => catalog.plants.clear(), throwsUnsupportedError);
      expect(() => plant.parts.clear(), throwsUnsupportedError);
      expect(
        () => plant.traditionalUses.single.references.clear(),
        throwsUnsupportedError,
      );
      expect(
        () =>
            ((source.selectors['nested']! as Map<String, Object?>)['ids']!
                    as List<Object?>)
                .add(9),
        throwsUnsupportedError,
      );
      expect(
        () => (source.selectors['nested']! as Map<String, Object?>).clear(),
        throwsUnsupportedError,
      );
    },
  );

  test(
    'inspection date and recommended citation are separate provenance data',
    () {
      final provenance = _catalog().provenance;
      expect(provenance.inspectedOn, DateTime.utc(2026, 10, 1));
      expect(provenance.recommendedCitation, 'Synthetic citation');
      expect(provenance.version, 'fixture-v1');
      expect(provenance.sourceUrl, 'https://example.org/synthetic-dataset');
      expect(provenance.datasetId, 'dataset-fixture');
      expect(provenance.downloadUrl, 'https://example.org/synthetic-file.zip');
      expect(provenance.fileId, 'file-fixture');
    },
  );

  test('selectors reject non-JSON values and non-string map keys', () {
    expect(
      () =>
          SourceRecord(table: 'fixture', selectors: {'value': StringBuffer()}),
      throwsArgumentError,
    );
    expect(
      () => SourceRecord(
        table: 'fixture',
        selectors: {
          'nested': {1: 'not a JSON object'},
        },
      ),
      throwsArgumentError,
    );
    expect(
      () => SourceRecord(table: 'fixture', selectors: {'value': double.nan}),
      throwsArgumentError,
    );
  });
}
