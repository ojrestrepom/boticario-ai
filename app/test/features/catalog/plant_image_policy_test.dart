import 'package:boticario_ai/features/catalog/data/plant_image_policy.dart';
import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Imagen de un host permitido', () {
    for (final url in [
      'https://upload.wikimedia.org/wikipedia/commons/a/ab/Lavandula.jpg',
      'https://commons.wikimedia.org/wiki/Special:FilePath/Lavandula.jpg',
      'https://UPLOAD.wikimedia.org/x.jpg',
    ]) {
      test('acepta $url', () {
        expect(PlantImagePolicy.isAllowed(url), isTrue);
        expect(PlantImagePolicy.providerFor(url), isA<NetworkImage>());
      });
    }

    test('la petición solo lleva un User-Agent genérico', () {
      final provider = PlantImagePolicy.providerFor(
        'https://upload.wikimedia.org/x.jpg',
      ) as NetworkImage;
      final headers = provider.headers!;
      expect(headers.keys.map((k) => k.toLowerCase()), ['user-agent']);
      final agent = headers['User-Agent']!;
      expect(agent, startsWith('BoticarioAI/'));
      expect(agent, isNot(contains('@')));
    });
  });

  group('Imagen de un host no permitido', () {
    for (final url in [
      'http://upload.wikimedia.org/x.jpg',
      'https://example.com/x.jpg',
      'https://upload.wikimedia.org.evil.com/x.jpg',
      'https://evil.com/upload.wikimedia.org/x.jpg',
      'https://evil.com@upload.wikimedia.org/x.jpg',
      'https://es.wikipedia.org/x.jpg',
      'ftp://upload.wikimedia.org/x.jpg',
      'upload.wikimedia.org/x.jpg',
      'https://',
      'https://[bad',
      '',
    ]) {
      test('rechaza "$url"', () {
        expect(PlantImagePolicy.isAllowed(url), isFalse);
        expect(PlantImagePolicy.providerFor(url), isNull);
      });
    }

    test('rechaza null', () {
      expect(PlantImagePolicy.isAllowed(null), isFalse);
    });
  });
}
