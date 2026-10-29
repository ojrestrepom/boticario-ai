# Tasks

## 1. Enlace en línea

- [ ] 1.1 Crear `PassportInlineLink` (texto subrayado y verde; `InkWell` de 48 dp de alto y de ancho; abre con `launchUrl` en modo externo; pulsación larga copia la URL y avisa «Enlace copiado»; falla con «No se pudo abrir el enlace»; sin `url` o no `https` se muestra texto plano sin semántica de enlace) y retirar `PassportLink`, incluido `readable`. Verificación: pruebas de widget nuevas en `passport_link_test.dart` (abrir, fallo, copia con el portapapeles simulado, URL `http`, URL nula, sin URL visible) en verde y `flutter analyze` sin hallazgos.
- [ ] 1.2 Actualizar `PassportTexts`: añadir `linkCopied`, el nombre de origen `Wikimedia Commons`, el enlace del archivo y el prefijo del pie; retirar `openLink`, `openLinkTooltip`, `licenseUrlPrefix`, `pageUrlPrefix` e `imageFilePageLabel`, y mantener `all` al día. Verificación: la prueba del escaneo de lenguaje de eficacia pasa y `grep` no encuentra los textos retirados en `app/lib`.
- [ ] 1.3 Semántica del enlace: `link: true`, etiqueta con el texto visible, aviso con el destino y la pulsación larga, sin lectura doble. Verificación: prueba con `SemanticsController` y con `labeledTapTargetGuideline` y `androidTapTargetGuideline`.

## 2. Pie de la foto con enlaces

- [ ] 2.1 Reemplazar las tres líneas del pie por «Foto: [autor] · [licencia]» en un `Wrap`: autor a `pageUrl`, licencia a `licenseUrl` si existe, y «Wikimedia Commons» enlazado a `pageUrl` cuando no hay autor (propuesta A de D4, sujeta a la pregunta Q1). Verificación: pruebas en `passport_header_image_test.dart` para autor y licencia enlazados, licencia sin URL, autor desconocido, imagen que no carga (sin pie) y ninguna URL visible.
- [ ] 2.2 Ajustar `passport_tall_header_test.dart` al pie nuevo y comprobar que sigue sin truncarse a 360x640 al 200 %. Verificación: esa prueba en verde.

## 3. Pestaña Fuentes

- [ ] 3.1 Convertir `PassportSourcesSection` en el contenido de la pestaña (sin `Divider` ni título): texto de licencias mixtas, entradas de crédito (nombre enlazado a `url`, «Licencia: [nombre]» enlazada a `licenseUrl`, atribución en `bodySmall` gris) y entrada de la imagen (autor o «No disponible en fuente», licencia enlazada, «Archivo en Wikimedia Commons»), con el vacío explícito. Verificación: `passport_sources_section_test.dart` reescrito con créditos con y sin enlaces, la atribución más pequeña y gris con contraste de 4,5:1, imagen con y sin autor, planta sin créditos ni imagen y sin URL visible.
- [ ] 3.2 Añadir el cuarto chip `Fuentes` en `plant_passport_page.dart` y retirar la sección del final de las otras tres pestañas. Verificación: pruebas en `plant_passport_page_test.dart`: cuatro pestañas con `General` inicial, el contenido de `Fuentes` solo con su pestaña, ninguna de las otras tres muestra créditos, y los ajustes de las pruebas que recorrían tres pestañas.
- [ ] 3.3 Comprobar el arreglo DEF-01 con cuatro pestañas: extender las pruebas de posición de scroll y de pestañas que vuelven a la vista a `Fuentes` a 360x640 al 100 % y 200 % (incluido el `Wrap` en tres filas y el paso de una pestaña larga a una corta). Verificación: esas pruebas en verde; si `ensureVisible` falla con el `Wrap` más alto, se corrige en `_selectTab` y se documenta en el diseño.

## 4. Accesibilidad

- [ ] 4.1 Extender `passport_accessibility_test.dart`: la pestaña `Fuentes` y el pie de la foto a 360x640 al 100 % y 200 % sin desbordes ni truncado; enlaces con semántica de enlace, destino y áreas de 48 dp; las cuatro pestañas con área de 48 dp y etiquetas; los enlaces se distinguen del texto sin depender del color (subrayado); sustituir la prueba «Abrir en el navegador expone semántica de botón». Verificación: `flutter test test/features/passport/passport_accessibility_test.dart` en verde.

## 5. Smoke

- [ ] 5.1 Ajustar `app/integration_test/catalog_smoke.dart`: recorrer las cuatro pestañas, comprobar que `Fuentes` solo se ve en su pestaña, que no aparece una URL como texto y que el pie de la foto tiene los enlaces. Verificación: el smoke pasa en el emulador (misma invocación que los cambios anteriores) y se anota la salida.

## 6. Documentación

- [ ] 6.1 Actualizar `docs/data/fuentes-y-licencias.md` («Qué licencias ve el usuario»): `Fuentes` es una pestaña, el pie lleva enlaces sobre el autor y la licencia, no hay URL visibles, solo se abren las `https`, la pulsación larga copia, y retirar la frase pendiente sobre `url_launcher`. Verificación: lectura contra la spec delta y `python3 -I openspec/changes/archive/2026-10-16-deploy-backend-cloud-run/qa/scripts/check-md-lines.py` sin hallazgos.
- [ ] 6.2 Actualizar `README.md`: las líneas del pasaporte (cuatro pestañas, sin la sección bajo cada una) y de `Fuentes` (enlaces sobre el nombre, sin URL visible ni botón). Verificación: el mismo verificador de Markdown y `grep` sin «Abrir en el navegador» ni «bajo cada una la sección `Fuentes`».

## 7. Verificación global

- [ ] 7.1 Ejecutar en `app/`: `flutter analyze`, `dart format --set-exit-if-changed .` y `flutter test` completo; recompilar el APK con `flutter build apk` y el `API_BASE_URL` del emulador. Verificación: todo en verde y el APK generado; se anotan los conteos de pruebas.
- [ ] 7.2 Ejecutar `openspec validate passport-sources-tab --strict` y el verificador de Markdown sobre los artefactos del cambio. Verificación: ambos sin hallazgos.

## 8. QA corta en el emulador

- [ ] 8.1 Con el APK en el emulador (sin el teléfono físico), recorrer: una planta con créditos con y sin enlaces, una con imagen sin autor, y una sin créditos ni imagen si existe; las cuatro pestañas al 100 % y 200 %; abrir un enlace, copiar con pulsación larga y provocar el aviso de fallo (por ejemplo sin navegador o en modo avión). Verificación: capturas en `qa/evidence/` del cambio y un informe breve `qa/passport-sources-tab-results.md` con los casos, resultados y defectos.
