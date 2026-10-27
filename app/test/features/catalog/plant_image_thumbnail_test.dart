import 'package:boticario_ai/features/catalog/data/plant_image_policy.dart';
import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';

const _base = 'https://upload.wikimedia.org/wikipedia/commons';

void main() {
  group('Miniatura de 500 px', () {
    test('JPG', () {
      expect(
        PlantImagePolicy.thumbnailUrl('$_base/a/ab/Lavandula.jpg'),
        '$_base/thumb/a/ab/Lavandula.jpg/500px-Lavandula.jpg',
      );
    });

    test('conserva la codificación por porcentaje del nombre', () {
      expect(
        PlantImagePolicy.thumbnailUrl(
          '$_base/3/3f/Lavandula_angustifolia_-_K%C3%B6hler.jpg',
        ),
        '$_base/thumb/3/3f/Lavandula_angustifolia_-_K%C3%B6hler.jpg/'
        '500px-Lavandula_angustifolia_-_K%C3%B6hler.jpg',
      );
      expect(
        PlantImagePolicy.thumbnailUrl(
          '$_base/8/8a/Mentha_%C3%97_piperita_%281%29.JPG',
        ),
        '$_base/thumb/8/8a/Mentha_%C3%97_piperita_%281%29.JPG/'
        '500px-Mentha_%C3%97_piperita_%281%29.JPG',
      );
    });

    test('PNG', () {
      expect(
        PlantImagePolicy.thumbnailUrl('$_base/c/cf/Ackee.png'),
        '$_base/thumb/c/cf/Ackee.png/500px-Ackee.png',
      );
    });

    test('SVG se sirve como PNG', () {
      expect(
        PlantImagePolicy.thumbnailUrl('$_base/1/12/Plant.svg'),
        '$_base/thumb/1/12/Plant.svg/500px-Plant.svg.png',
      );
    });

    test('formatos sin miniatura soportada devuelven null', () {
      for (final f in ['x.tif', 'x.tiff', 'x.pdf', 'x.ogv', 'x', 'x.']) {
        expect(
          PlantImagePolicy.thumbnailUrl('$_base/a/ab/$f'),
          isNull,
          reason: f,
        );
      }
    });

    test('rutas que no encajan devuelven null', () {
      for (final url in [
        'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/X.jpg/500px-X.jpg',
        'https://upload.wikimedia.org/wikipedia/commons/a/X.jpg',
        'https://upload.wikimedia.org/wikipedia/commons/a/xy/X.jpg',
        'https://upload.wikimedia.org/wikipedia/en/a/ab/X.jpg',
        'https://upload.wikimedia.org/x.jpg',
        '$_base/a/ab/X.jpg?download',
        '$_base/a/ab/',
      ]) {
        expect(PlantImagePolicy.thumbnailUrl(url), isNull, reason: url);
        expect(PlantImagePolicy.thumbnailProviderFor(url), isNull);
      }
    });

    test('host no permitido, http o nulo devuelven null', () {
      for (final url in [
        'https://commons.wikimedia.org/wikipedia/commons/a/ab/X.jpg',
        'https://example.com/wikipedia/commons/a/ab/X.jpg',
        'http://upload.wikimedia.org/wikipedia/commons/a/ab/X.jpg',
        null,
      ]) {
        expect(PlantImagePolicy.thumbnailUrl(url), isNull);
      }
    });

    test('el proveedor lleva solo el User-Agent genérico', () {
      final provider =
          PlantImagePolicy.thumbnailProviderFor('$_base/a/ab/X.jpg')!
              as NetworkImage;
      expect(provider.url, '$_base/thumb/a/ab/X.jpg/500px-X.jpg');
      expect(provider.headers, {'User-Agent': 'BoticarioAI/0.1.0'});
    });
  });
}
