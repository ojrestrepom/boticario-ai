import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:boticario_ai/features/plant_recognition/data/plant_image_preprocessor.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_predictions.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_species_metadata.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

void main() {
  final processor = PlantImagePreprocessor();
  final indicesJson = File('assets/metadata/class_idx_to_species_id.json')
      .readAsStringSync();
  final namesJson = File('assets/metadata/plantnet300K_species_id_2_name.json')
      .readAsStringSync();
  final metadata = PlantSpeciesMetadata.parse(indicesJson, namesJson);

  test('RGB normalization, float32 and NCHW planes preserve spatial order', () {
    final image = img.Image(width: 224, height: 224);
    img.fill(image, color: img.ColorRgb8(255, 0, 128));
    image.setPixelRgb(1, 0, 0, 255, 64);
    final tensor = processor.prepare(img.encodePng(image));
    expect(tensor, isA<Float32List>());
    expect(tensor.length, 150528);
    for (var c = 0; c < 3; c++) {
      for (var x = 0; x < 2; x++) {
        final value = x == 0 ? [255, 0, 128][c] : [0, 255, 64][c];
        expect(
          tensor[c * 224 * 224 + x],
          closeTo(
            (value / 255 - PlantImagePreprocessor.mean[c]) /
                PlantImagePreprocessor.std[c],
            1e-6,
          ),
        );
      }
    }
  });

  test('non-square input is resized to a finite 224 square tensor', () {
    final image = img.Image(width: 37, height: 19);
    img.fill(image, color: img.ColorRgb8(30, 80, 140));
    final tensor = processor.prepare(img.encodePng(image));
    expect(tensor.length, 150528);
    expect(tensor.every((value) => value.isFinite), isTrue);
    expect(tensor.first, closeTo((30 / 255 - 0.4425) / 0.2353, 1e-6));
  });

  test('EXIF rotation and mirroring match physically oriented pixels', () {
    for (var orientation = 2; orientation <= 8; orientation++) {
      final image = img.Image(width: 9, height: 5);
      for (final pixel in image) {
        pixel.setRgb(pixel.x * 25, pixel.y * 45, 100);
      }
      final untagged = img.decodeJpg(img.encodeJpg(image, quality: 100))!;
      untagged.exif.imageIfd.orientation = orientation;
      final oriented = img.bakeOrientation(untagged);
      image.exif.imageIfd.orientation = orientation;
      final encoded = img.encodeJpg(image, quality: 100);
      final decoded = img.decodeJpg(encoded)!;
      // image 4.12 applies JPEG EXIF during decoding and removes the tag.
      expect(decoded.exif.imageIfd.orientation, isNull);
      expect(decoded.width, oriented.width);
      expect(decoded.height, oriented.height);
      expect(
        processor.prepare(encoded),
        processor.prepare(img.encodePng(oriented)),
      );
    }
  });

  test('invalid encoded image is rejected', () {
    expect(
      () => processor.prepare(Uint8List.fromList([1, 2, 3])),
      throwsFormatException,
    );
  });

  test('real metadata covers all indices and reference scientific names', () {
    expect(metadata.classes.length, 1081);
    const references = {
      4: 'Cirsium vulgare',
      144: 'Chaerophyllum temulum',
      187: 'Sedum rupestre',
      529: 'Adenostyles alpina',
    };
    for (final entry in references.entries) {
      expect(metadata.classes[entry.key].classIndex, entry.key);
      expect(
        metadata.classes[entry.key].scientificName,
        startsWith(entry.value),
      );
    }
    expect(() => metadata.classes.clear(), throwsUnsupportedError);
  });

  test(
    'metadata rejects missing indices, unknown IDs, blank names and duplicates',
    () {
      final indices = jsonDecode(indicesJson) as Map<String, dynamic>;
      final names = jsonDecode(namesJson) as Map<String, dynamic>;
      for (final malformed in [
        {...indices}..remove('0'),
        {...indices, '0': 'unknown'},
        {...indices, '0': indices['1']},
        {...indices, '0': null},
      ]) {
        expect(
          () => PlantSpeciesMetadata.parse(jsonEncode(malformed), namesJson),
          throwsFormatException,
        );
      }
      names['${indices['0']}'] = ' ';
      expect(
        () => PlantSpeciesMetadata.parse(indicesJson, jsonEncode(names)),
        throwsFormatException,
      );
    },
  );

  test(
    'stable softmax uses all classes, preserves order and breaks ties by index',
    () {
      final logits = List<double>.filled(1081, 10000);
      final uniform = plantTopFive(logits, metadata);
      expect(uniform.map((p) => p.species.classIndex), [0, 1, 2, 3, 4]);
      expect(uniform.first.score, closeTo(1 / 1081, 1e-12));
      expect(uniform.fold<double>(0, (sum, p) => sum + p.score), lessThan(1));
      logits[529] = 10002;
      final ranked = plantTopFive(logits, metadata);
      expect(ranked.first.species.classIndex, 529);
      expect(
        ranked.every((p) => p.score.isFinite && p.score >= 0 && p.score <= 1),
        isTrue,
      );
      final shifted = plantTopFive(
        logits.map((v) => v - 20000).toList(),
        metadata,
      );
      expect(ranked.map((p) => p.score), shifted.map((p) => p.score));
      expect(() => plantTopFive([0], metadata), throwsArgumentError);
      logits[0] = double.nan;
      expect(() => plantTopFive(logits, metadata), throwsArgumentError);
    },
  );
}
