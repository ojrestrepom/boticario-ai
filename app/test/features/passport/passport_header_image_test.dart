import 'dart:convert';
import 'dart:typed_data';

import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_header.dart';
import 'package:boticario_ai/features/passport/presentation/passport_link.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_url_launcher.dart';
import 'passport_test_support.dart';

/// A 1x1 transparent PNG: stands in for a downloaded photo.
final Uint8List _png = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
  '60e6kgAAAABJRU5ErkJggg==',
);

ImageProvider? _loads(String? url) => MemoryImage(_png);

class _Failing extends ImageProvider<_Failing> {
  @override
  Future<_Failing> obtainKey(ImageConfiguration configuration) =>
      Future.value(this);

  @override
  ImageStreamCompleter loadImage(_Failing key, ImageDecoderCallback decode) =>
      OneFrameImageStreamCompleter(Future.error(Exception('sin conexión')));
}

ImageProvider? _fails(String? url) => _Failing();

Plant _withoutImage(Plant p) => Plant(
  id: p.id,
  scientificName: p.scientificName,
  family: p.family,
  names: p.names,
  parts: p.parts,
  uses: p.uses,
  displayName: p.displayName,
  credits: p.credits,
);

/// Lets the in-memory image decode (real async work) and shows its frame.
Future<void> _settleImage(WidgetTester tester) async {
  await tester.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 200)),
  );
  await tester.pump();
}

Finder _inHeader(String text) =>
    find.descendant(of: find.byType(PassportHeader), matching: find.text(text));

void main() {
  late FakeUrlLauncher launcher;

  setUp(() {
    launcher = FakeUrlLauncher();
    UrlLauncherPlatform.instance = launcher;
  });

  testWidgets('Imagen con licencia CC BY-SA', (tester) async {
    final plant = consolidatedPlant('agrimonia-eupatoria');
    final image = plant.image!;
    expect(image.license, 'CC BY-SA 4.0');
    await showPassport(tester, plant, imageProviderFor: _loads);
    await _settleImage(tester);
    expect(find.byType(Image), findsOneWidget);
    expect(_inHeader('Autor: ${image.author}'), findsOneWidget);
    expect(_inHeader('Licencia: CC BY-SA 4.0'), findsOneWidget);
    expect(_inHeader(PassportTexts.imageFilePageLabel), findsOneWidget);
    expect(_inHeader(PassportLink.readable(image.pageUrl)), findsWidgets);
  });

  testWidgets('Imagen sin atribución obligatoria', (tester) async {
    final plant = consolidatedPlant('capsella-bursa-pastoris');
    final image = plant.image!;
    expect(image.attributionRequired, isFalse);
    await showPassport(tester, plant, imageProviderFor: _loads);
    await _settleImage(tester);
    expect(_inHeader('Autor: ${image.author}'), findsOneWidget);
    expect(_inHeader('Licencia: ${image.license}'), findsOneWidget);
    expect(_inHeader(PassportLink.readable(image.pageUrl)), findsWidgets);
  });

  testWidgets('Imagen descrita para tecnología de asistencia', (tester) async {
    final handle = tester.ensureSemantics();
    final plant = consolidatedPlant('agrimonia-eupatoria');
    await showPassport(tester, plant, imageProviderFor: _loads);
    await _settleImage(tester);
    expect(
      find.bySemanticsLabel(PassportTexts.imageDescription(plant.primaryName)),
      findsOneWidget,
    );
    handle.dispose();
  });

  testWidgets('Mientras carga se ve el arte local, sin pie', (tester) async {
    final plant = consolidatedPlant('agrimonia-eupatoria');
    await showPassport(tester, plant, imageProviderFor: (_) => _NeverLoads());
    expect(find.byIcon(Icons.local_florist), findsWidgets);
    expect(find.text(PassportTexts.imageFilePageLabel), findsNothing);
  });

  testWidgets('Sin imagen', (tester) async {
    final plant = _withoutImage(consolidatedPlant('agrimonia-eupatoria'));
    var asked = false;
    await showPassport(
      tester,
      plant,
      imageProviderFor: (url) {
        asked = true;
        return _loads(url);
      },
    );
    await tester.pump();
    expect(asked, isFalse);
    expect(find.byType(Image), findsNothing);
    expect(find.byIcon(Icons.local_florist), findsOneWidget);
    expect(find.text(PassportTexts.imageFilePageLabel), findsNothing);
  });

  testWidgets('Imagen de un host no permitido se muestra como sin imagen', (
    tester,
  ) async {
    // The default provider is the policy's: a URL it rejects gives no image.
    final base = consolidatedPlant('agrimonia-eupatoria');
    final plant = Plant(
      id: base.id,
      scientificName: base.scientificName,
      family: base.family,
      names: base.names,
      parts: base.parts,
      uses: base.uses,
      image: PlantImage(
        url: 'https://example.com/x.jpg',
        pageUrl: base.image!.pageUrl,
        author: 'A',
        license: 'CC BY 4.0',
        licenseUrl: null,
        attributionRequired: true,
      ),
    );
    await showPassport(tester, plant);
    await tester.pump();
    expect(find.byType(Image), findsNothing);
  });

  testWidgets('Falla la descarga de la imagen', (tester) async {
    final plant = consolidatedPlant('agrimonia-eupatoria');
    await showPassport(tester, plant, imageProviderFor: _fails);
    await tester.pump();
    await tester.pump();
    expect(tester.takeException(), isNull);
    expect(find.byIcon(Icons.local_florist), findsWidgets);
    expect(find.text(PassportTexts.imageFilePageLabel), findsNothing);
    expect(find.text('No se pudo cargar la planta'), findsNothing);
    // The rest of the sheet is complete.
    expect(find.text('Nombre común'), findsOneWidget);
  });

  testWidgets('Abrir la página del archivo', (tester) async {
    final plant = consolidatedPlant('agrimonia-eupatoria');
    await showPassport(tester, plant, imageProviderFor: _loads);
    await _settleImage(tester);
    await tester.tap(
      find.byTooltip(
        PassportTexts.openLinkTooltip(PassportTexts.imageFilePageLabel),
      ),
    );
    await tester.pump();
    expect(launcher.launched, [plant.image!.pageUrl]);
    expect(launcher.modes, [PreferredLaunchMode.externalApplication]);
    // The URL stays visible and the page itself is not shown.
    expect(
      find.text(PassportLink.readable(plant.image!.pageUrl)),
      findsWidgets,
    );
  });
}

class _NeverLoads extends ImageProvider<_NeverLoads> {
  @override
  Future<_NeverLoads> obtainKey(ImageConfiguration configuration) =>
      Future.value(this);

  @override
  ImageStreamCompleter loadImage(
    _NeverLoads key,
    ImageDecoderCallback decode,
  ) => OneFrameImageStreamCompleter(
    Future<ImageInfo>.delayed(const Duration(days: 1)),
  );
}
