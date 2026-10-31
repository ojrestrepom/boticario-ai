# QA local de activity-glossary

Informe de la QA local del cambio `activity-glossary` (rama `passport-uses-glossary`, commits `5805eae` a `fa3ea6c`), hecha el 2026-10-29 antes del despliegue. Cubre la parte local de la tarea 8.1 (API con Postman), la tarea 8.2 en el emulador contra la API local y la corrida en el emulador del smoke de la tarea 7.6.

## Resumen

- No se encontró ningún defecto del producto (API, base, semilla ni app). Todos los escenarios de los deltas que se pudieron probar localmente pasan.
- Hay un defecto de prueba (D1, severidad media): el smoke `integration_test/app_test.dart` pasa aunque la app no muestre ninguna explicación y no comprueba que una planta sin términos no muestre la etiqueta, que es lo que pide la tarea 7.6. Se reprodujo contra una API sin glosario.
- Hay observaciones de contenido (verbos de efecto en definiciones aprobadas, `Anticonceptivo`, `Emenagogo`, `Vulnerario`) y de accesibilidad (área táctil del enlace) en la sección de observaciones.
- Contra la API desplegada no se probó nada: no se ha desplegado. Quedan pendientes la primera corrida de la tarea 8.1 contra Cloud Run y la tarea 8.2 con el APK apuntando a Cloud Run.

## Entorno

- API local: binario `catalog-api` de `--release` compilado con `--target-dir` en la carpeta auxiliar de la sesión, puerto 18080, con un token aleatorio solo en la variable de entorno `API_TOKENS` del proceso. En este informe el token es `<token-app>`.
- Base: `catalog-ingest build --out` escribió el `catalog.db` en la carpeta auxiliar (no se tocó `data/build/catalog.db`). Dos construcciones dieron el mismo hash `da58f6145435…` (los primeros 12 caracteres) y archivos idénticos byte a byte, que además coinciden con el `data/build/catalog.db` que ya existía.
- Emulador: `boticario_catalog_api36` (Android 36, 1080x1920), APK de depuración con `--dart-define=API_BASE_URL=http://10.0.2.2:18080` y `--dart-define=API_TOKEN=<token-app>`. No se usó el teléfono físico `R5CR70M9GEE` para ninguna prueba.
- Herramientas: Postman CLI 1.74.0 (ya instalado), Python 3 con `sqlite3` y `urllib` de la biblioteca estándar, `adb` y `uiautomator`. No se instaló nada ni se agregaron dependencias al proyecto.

## Casos y resultados

La colección propia es `postman/activity-glossary.postman_collection.json` (17 peticiones, 109 aserciones). El oráculo es `scripts/oracle.py` (31 comprobaciones). Los números de escenario son los de `openspec/changes/activity-glossary/specs/`.

| ID | Qué cubre | Técnica | Resultado | Evidencia |
| --- | --- | --- | --- | --- |
| A0 | Colección general `backend/postman/` contra la API local (incluye las dos peticiones nuevas del glosario): 24 peticiones, 101 aserciones | Regresión | Pasa, 0 fallos | `evidence/api/postman-general.txt` |
| G1 | `catalog-api`: grupo con término. Lavanda: Diurético y Carminativo literales de Wikcionario con texto exacto, Estimulante adaptado de Wikipedia, `glossary` siempre presente con los 5 campos, orden de campos del grupo sin cambios, créditos de Wikcionario y Wikipedia una vez cada uno | Partición de equivalencia | Pasa | `evidence/api/postman-glossary.txt` |
| G2 | Texto adaptado: Sedante (acónito) | Partición | Pasa | idem |
| G3 | Wikipedia literal: Expectorante (abeto) con `adapted` falso | Partición | Pasa | idem |
| G4 | Planta con solo explicaciones de Wikipedia (`actaea-dahurica`): sin crédito de Wikcionario y Wikipedia una vez | Tabla de decisión | Pasa | idem |
| G5 | Fórmula «Uso tradicional, sin eficacia demostrada: cáncer» con `glossary` nulo y `activity` íntegra | Negativo | Pasa | idem |
| G6 | Términos excluidos (Hemostático y Depurativo) con `glossary` nulo | Negativo | Pasa | idem |
| G7 | Calificador: `Antídoto (Laportea)` hereda `Antídoto` (Wikipedia literal) y conserva el calificador en `activity` | Partición | Pasa | idem |
| G8 | Solo grupos pendientes (`cedrus-deodara`): no se sirven los grupos ni la explicación ni el crédito de Wikcionario | Tabla de decisión | Pasa | idem |
| G9 | Grupo pendiente de Wikipedia (`maclura-pomifera`): no se sirve | Tabla de decisión | Pasa | idem |
| G10 | Planta sin ningún término: todo nulo y sin crédito de Wikcionario | Negativo | Pasa | idem |
| G11 | El alias `rosmarinus-officinalis` resuelve y trae `glossary` | Partición | Pasa | idem |
| C1 a C2 | Contrato anterior: forma del listado, `uses` (`activity`, `language`, `reference`) y las claves de la raíz del detalle en su orden | Regresión | Pasa | idem |
| C3 | `/openapi.json` en vivo describe `UseGlossaryDto` (5 campos obligatorios), `glossary` como objeto o nulo y obligatorio, y es idéntico a `backend/openapi.json` | Contrato | Pasa | idem |
| C4 | 401 sin token en el detalle (`application/problem+json`, `WWW-Authenticate: Bearer`, sin datos) | Autenticación | Pasa | idem |
| C5 a C6 | `/v1/goals` y `/v1/goals/{id}/plants` sin cambios y sin `glossary` | Regresión | Pasa | idem |
| O1 | Oráculo SQL: 53 términos; texto, URL, fuente y modo iguales a la tabla de revisión aprobada (53 filas con «sí (usuario, 2026-10-29)»); 37 de Wikcionario, 5 de Wikipedia literal y 11 de Wikipedia adaptado; Emenagogo, Anticonceptivo y los 6 verbos aprobados presentes; claves en forma base; todas las URL `https` con `oldid` | Oráculo | Pasa | `evidence/api/oracle-output.txt` |
| O2 | `glossary.json` y `activity_glossary` iguales; `glossaryCount` 53 en el manifiesto | Oráculo | Pasa | idem |
| O3 | 5.172 grupos visibles con explicación en 1.207 plantas; 5.278 enlazados, 106 pendientes; 2.354 plantas; `foreign_key_check` vacío; `schema_version` 3 | Oráculo | Pasa | idem |
| O4 | Ninguna fórmula de enfermedad grave enlazada (hay 1.309 grupos con la fórmula) y enlace igual a una reimplementación independiente de la regla de la forma base, sin enlaces de más ni de menos en todos los grupos | Oráculo | Pasa | idem |
| O5 | Recorrido de las 2.354 plantas por la API: grupos servidos iguales a los no pendientes de la base, forma de cada grupo sin cambios, `glossary` igual a la fila de la base o nulo, 5.172 grupos y 1.207 plantas, créditos de Wikcionario en 1.133 plantas (exactamente las que sirven una explicación suya), Wikipedia presente cuando hay explicación de Wikipedia y nunca repetida | Oráculo | Pasa | idem |
| O6 | Muestra aleatoria reproducible de 30 grupos (semilla 20261029) comparada entre API, base, `glossary.json` y tabla aprobada | Oráculo | Pasa | idem, líneas `muestra:` |
| O7 | Las 53 definiciones sin dosis ni posología (cifras, «dosis», «posología», «gotas», «cucharadas», «mg», «ml») | Revisión | Pasa | idem |
| R1 | Revisión de contenido de las 53 definiciones: sin dosis; los textos adaptados coinciden con la tabla aprobada (O1); verbos vigilados solo en los 6 aprobados (ver observaciones sobre otros verbos de efecto) | Revisión | Pasa con observaciones | sección de observaciones |
| E1 | Smoke `integration_test/app_test.dart` en el emulador contra la API local | Integración | Pasa (1 prueba) con el defecto de prueba D1 | `evidence/emulator/smoke-integration-test.txt` |
| E2 | Lavanda en `Usos`: 8 explicaciones (Carminativo, Estimulante, Colagogo, Diurético, Estomacal, Nervino, Sudorífico, Vermífugo) iguales a las de la API; `Espasmo` sin etiqueta ni hueco; etiqueta gris, formato `<Término>: «…» (Fuente)`, «adaptado de Wikipedia» en Estimulante, Colagogo y Vermífugo | Exploratoria con charter | Pasa | capturas 01, 02 y 06 |
| E3 | Enlace de la fuente: «Wikcionario» abre `es.wiktionary.org/w/index.php?title=carminativo&oldid=5967250` y «Wikipedia» (adaptado) abre `es.wikipedia.org/w/index.php?title=Estimulante&oldid=174885171`, en Chrome, sin mostrar la URL como texto; nombre accesible «Wikcionario. Abre la fuente de la explicación» | Exploratoria | Pasa | `evidence/emulator/link-wikcionario-browser.png`, `evidence/emulator/link-wikipedia-adaptado-browser.png` |
| E4 | Citas plegadas: «Ver 2 citas de Carminativo» despliega las dos citas en su sitio y «Ocultar citas» las pliega, con la explicación visible encima | Exploratoria | Pasa | `evidence/emulator/citas-desplegadas-carminativo.png` |
| E5 | `Fuentes` de Lavanda: Wikcionario en español y Wikipedia en español, cada uno una vez, con licencia CC BY-SA 4.0 enlazada y atribución como texto secundario, sin URL visible; la atribución de Wikcionario dice que se retiró el marcado y las notas, que se recortó a la primera oración y que el historial lista a los autores | Exploratoria | Pasa | captura 03 |
| E6 | 200 % de texto (`font_scale` 2.0): etiqueta, explicación y enlace completos y sin truncar ni desbordar, en Carminativo (Wikcionario) y Estimulante (adaptado); título, explicación y línea de datos leídos como un solo bloque de accesibilidad | Exploratoria | Pasa | capturas 04 y 05 |
| E7 | Cardo bendito (Emenagogo y Anticonceptivo con Wikcionario; `Fiebre` sin etiqueta; la fórmula «…: cáncer» sin explicación y mostrada tal cual) | Exploratoria | Pasa | capturas 07 y 08 |
| E8 | Abeto común: `Expectorante` con el texto literal de Wikipedia y «(Wikipedia)» sin «adaptado de»; `Catarro` y `Contusión` sin etiqueta | Exploratoria | Pasa | captura 09 |
| E9 | Yerba mansa (sin ningún término del glosario): ninguna etiqueta «Significado del término» en `Usos`, fórmula mostrada tal cual y `Fuentes` sin Wikcionario (con Wikipedia, que acredita su descripción) | Negativo | Pasa | captura 10 |

## Defectos

### D1. El smoke no verifica lo que pide la tarea 7.6 (severidad media, defecto de prueba)

- **Escenario afectado:** tarea 7.6, que pide que en una planta con `Diurético` o `Tónico` `Usos` muestre «Significado del término» bajo el título, que una planta sin términos del glosario no lo muestre y que `Fuentes` liste Wikcionario.
- **Qué pasa:** en `app/integration_test/catalog_smoke.dart`, `_expectGlossary` solo exige `lines > 0 == seen > 0` (si no hay etiqueta ni línea, también pasa) y devuelve si vio alguna; la comprobación de `Fuentes` está dentro de `if (hasGlossary)`. El smoke solo recorre la lavanda y no abre ninguna planta sin términos, así que no hay ninguna comprobación negativa.
- **Reproducción:**
  - Se copió la base a la carpeta auxiliar y se vació (`update plant_use_group set glossary_key = null; delete from activity_glossary;`).
  - Se levantó una segunda API con esa base en el puerto 18081.
  - Se corrió `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:18081 --dart-define=API_TOKEN=<token-app>`.
- **Obtenido:** `All tests passed!` con una API que no sirve ninguna explicación ni crédito de Wikcionario.
- **Esperado:** el smoke falla si la lavanda no muestra la etiqueta, y comprueba que una planta sin términos (por ejemplo `anemopsis-californica`, Yerba mansa) no la muestra y que `Fuentes` de la lavanda lista Wikcionario.
- **Evidencia:** `evidence/emulator/smoke-contra-api-sin-glosario.txt` y, para el caso con glosario, `evidence/emulator/smoke-integration-test.txt`. Las comprobaciones que el smoke no hace sí se hicieron a mano en este informe (E2, E5, E9).

No hay defectos de severidad crítica, alta ni baja.

## Observaciones

- **Verbos de efecto en definiciones aprobadas.** Además de los 6 verbos aprobados (Antiséptico, Bactericida, Vulnerario, Antidiarreico, Fungicida, Parasiticida), otras 8 definiciones llevan verbos de efecto (Antidiarreico también por «combate», que su aprobación no nombra) que el validador no vigila y que el diseño (D10) deja a la revisión humana:
  - Anodino: «mitiga el dolor».
  - Estomacal: «fortalece al estómago, y favorece la digestión».
  - Tónico: «favorece el tono».
  - Cordial: «fortalecer el corazón».
  - Febrífugo: «combatir la fiebre».
  - Antidiarreico: «previene o combate la diarrea».
  - Emenagogo: «favoreciendo la menstruación».
  - Estíptico (Wikipedia literal): «pueden producir una acción cicatrizante, antiinflamatoria y antihemorrágica».
  - Todas están en la tabla que aprobó el usuario; se informan para que se confirme que esa aprobación cubrió también esos verbos.
- **Vulnerario** es la única definición que habla de «la planta»: «Se dice de la planta o sustancia que tiene propiedades beneficiosas para curar heridas o llagas». Se lee como una afirmación sobre la planta que se está viendo, a pesar de la etiqueta. El verbo «curar» está aprobado, la referencia a «la planta» no se mencionó en la aprobación.
- **Anticonceptivo y Emenagogo** (salud reproductiva) aparecen en plantas con toxicidad conocida, como `taxus-baccata` (tejo), que tiene los dos grupos. La etiqueta y el aviso fijo de `Usos` atenúan la lectura, pero conviene que el usuario confirme que quiere esa combinación. Los dos términos se incluyeron por su decisión expresa.
- **Atribución de Wikipedia.** El texto del crédito de Wikipedia menciona el glosario de actividades en todas las plantas que lo tienen, también en las 754 plantas cuyo crédito de Wikipedia viene solo de la descripción y que no tienen ninguna explicación de Wikipedia. Se comprobó en la API para Lavanda y Actaea, y se infiere para las demás porque la atribución sale de la fila de la fuente. Es una imprecisión menor de texto, no afecta la licencia.
- **Área táctil del enlace.** El enlace de la fuente mide unos 72 px de alto a 100 % (unos 27 dp, según `uiautomator`) y unos 114 px al 200 % (unos 43 dp). Es del mismo tamaño que los enlaces de `Fuentes` (unos 78 px). El delta pide un área «suficiente»; está por debajo de los 48 dp de Material al 100 %.
- **Viewport al 200 %.** Con 200 % de texto, la franja de contenido que queda entre la cabecera de la planta y el botón fijo «Ver formulaciones relacionadas» es de unos 100 px mientras se ven las pestañas, y hay que desplazarse para leer. Es previo a este cambio y no lo causa el glosario.
- **OpenAPI.** El documento ordena las propiedades de `UseGroupDto` alfabéticamente (`glossary` queda entre `countries` y `references`); el orden real de la respuesta JSON no cambia (`glossary` es la última clave). No es un defecto.
- **Procedimiento.** Una vez se corrió `adb shell pm list packages` contra el teléfono físico por equivocación (solo lectura, no devolvió nada de la app y no se instaló ni cambió nada). El resto de comandos usó `-s emulator-5554` o `-d emulator-5554`.

## No ejecutado

- La primera corrida de la tarea 8.1 contra Cloud Run y la tarea 8.2 con el APK apuntando a Cloud Run, porque el cambio no está desplegado.
- Un término excluido (Hemostático o Depurativo) y una planta con `Antídoto (…)` recorridos a mano en el emulador: se verificaron en la API (G6, G7) y en el oráculo, no en la app. En la app se recorrió una fórmula de enfermedad grave (cardo bendito y yerba mansa).
- Lavanda y Romero con 200 % en `Fuentes`: el 200 % se probó en `Usos`.
- La app contra un backend anterior sin `glossary`: solo se probó que el smoke pasa contra una API que sirve `glossary: null` en todo (D1), no la lectura tolerante campo por campo, que cubren las pruebas de la tarea 7.1.
- TalkBack: la accesibilidad se revisó por el árbol de `uiautomator` (nodo único con título, etiqueta, explicación y datos; enlace con nombre accesible), no con el lector de pantalla.
- La suite de pruebas del producto (`cargo test`, `flutter test`, `flutter analyze`): quedan en las tareas 6.5 y 7.8.

## Capturas para el usuario

Están en `openspec/changes/activity-glossary/qa/evidence/review/`.

- `01-usos-lavanda-carminativo-estimulante-adaptado.png`: dos explicaciones, Carminativo (Wikcionario) y Estimulante «adaptado de Wikipedia».
- `02-usos-lavanda-sudorifico-vermifugo.png`: Sudorífico (Wikcionario) y Vermífugo adaptado.
- `06-usos-lavanda-diuretico-espasmo-sin-termino.png`: Diurético, Espasmo sin etiqueta y Estomacal.
- `09-usos-abeto-expectorante-wikipedia-literal.png`: Wikipedia literal, sin «adaptado de».
- `07-usos-cardo-bendito-emenagogo-sin-termino-fiebre.png`: Emenagogo y Emético con explicación, Fiebre sin ella.
- `08-usos-cardo-bendito-formula-sin-explicacion.png`: la fórmula «Uso tradicional, sin eficacia demostrada: cáncer» sin explicación y Aperitivo con ella.
- `10-usos-yerba-mansa-sin-ningun-termino.png`: planta sin ningún término del glosario.
- `03-fuentes-wikcionario-wikipedia.png`: `Fuentes` de Lavanda con Wikcionario y Wikipedia.
- `04-usos-200pct-lavanda-carminativo.png` y `05-usos-200pct-adaptado-estimulante.png`: 200 % de texto, sin truncar.

## Tareas

- 8.1 (parte local): cumplida. Falta la corrida contra Cloud Run después del despliegue. El informe de la tarea 8.1 nombra `qa/activity-glossary-api-results.md`, que no se creó: los resultados de la API están en este informe.
- 8.2: cumplida contra la API local con las plantas indicadas arriba; falta repetirla con el APK apuntando a la API desplegada.
- 7.6: la corrida en el emulador pasa, pero el smoke no verifica lo que la tarea describe (D1); recomiendo no marcarla hasta reforzarlo.

## Cómo re-ejecutar

Desde la raíz del repositorio. Todos los comandos usan variables de entorno para el token.

```bash
mise exec -- cargo build --release --locked --manifest-path backend/Cargo.toml --target-dir <carpeta-auxiliar> -p catalog-ingest -p catalog-api
<carpeta-auxiliar>/release/catalog-ingest build --out <carpeta-auxiliar>/catalog.db
API_TOKENS=$(openssl rand -hex 32) PORT=18080 CATALOG_DB=<carpeta-auxiliar>/catalog.db <carpeta-auxiliar>/release/catalog-api &
postman collection run openspec/changes/activity-glossary/qa/postman/activity-glossary.postman_collection.json -e openspec/changes/activity-glossary/qa/postman/local-18080.postman_environment.json --env-var "token=<token-app>"
TOKEN=<token-app> python3 -I openspec/changes/activity-glossary/qa/scripts/oracle.py <carpeta-auxiliar>/catalog.db http://localhost:18080 "$PWD" salida.json
(cd app && flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:18080 --dart-define=API_TOKEN=<token-app>)
```

`scripts/build_postman_collection.py` regenera la colección y `scripts/ui.py` es el ayudante de `adb` del recorrido a mano. Las plantas de la colección dependen de la semilla actual (por ejemplo `cedrus-deodara` y `maclura-pomifera` por tener grupos pendientes), así que si la semilla cambia hay que revisarlas.

## Limpieza y barrido de tokens

- Se detuvieron las dos APIs, el daemon de Gradle (`./gradlew --stop`) y el emulador; la app quedó desinstalada, `font_scale` en 1.0 y se borraron solo `app-debug.apk` y `app-debug.apk.sha1`. No se usó Docker ni `rm -rf`, y no hay procesos en segundo plano.
- Barrido `grep -rEn '[0-9a-f]{32,}' openspec/changes/activity-glossary/qa/`: cero resultados (ver el resultado en el mensaje de entrega).
- Los logs de la API y de la compilación se quedaron en la carpeta auxiliar de la sesión, fuera del repositorio. No se guardó ningún `logcat`. El token del smoke se sustituyó por `<token-app>` en la salida guardada.

## Validación en Cloud Run y emulador (2026-10-31)

Validación de las tareas 8.1 (API con Postman contra Cloud Run) y 8.2 (interfaz en el emulador con un APK que apunta a Cloud Run), con los ajustes de revisión del usuario: etiqueta «Significado general del término», línea «Aviso sobre usos» con diálogo, «Sucedáneo del café», sin línea «Lugares» e icono de libro de citas a la derecha del título. Rama `uses-citations-icon` (`d9a5e4c`), con el backend y la semilla de `main` (`24a4477`) desplegados en Cloud Run.

### Resumen

- La API desplegada pasa todos los casos (8.1): colección del glosario con 22 peticiones y 147 aserciones, colección general con 24 peticiones y 101 aserciones, y un barrido de las 2.354 plantas contra `data/seed/glossary.json`, todo sin fallos.
- La interfaz pasó todos los casos de 8.2 salvo uno, que se corrigió y reverificó (D2, cerrado tras `b5450c1`; antes era un defecto del producto de severidad media): el icono de libro se ve igual plegado que desplegado, así que el estado no se expresa en el icono (los píxeles de ambos estados son idénticos en el APK release). El estado sí se expresa en el tooltip, en la etiqueta accesible y en las citas visibles debajo.
- Observaciones: la atribución de Wikipedia menciona el glosario también en plantas sin explicación de Wikipedia (confirmada en Cloud Run), y no se pudo oír TalkBack (se verificó el árbol de accesibilidad).
- No se marcan casillas en `tasks.md`.

### Entorno

- API: `https://boticario-api-d3xv5q3iaa-pv.a.run.app`, con el token de la app leído a una variable de entorno de la shell y pasado a Postman CLI como variable; en los informes aparece `<token-app>` (el barrido de `[0-9a-f]{32,}` sobre `qa/` no da resultados).
- APK: `app/build/app/outputs/flutter-apk/app-release.apk` (release, ya compilado, no se compiló otro; contiene la URL de Cloud Run y ninguna de `localhost` ni `10.0.2.2`, comprobado con `strings` sobre `libapp.so`). Instalado con `adb -s emulator-5554 install -r`; no se usó el teléfono físico `R5CR70M9GEE` (solo apareció en `adb devices`, que es de lectura).
- Emulador `boticario_catalog_api36`, 1080x1920 a 480 dpi (360x640 dp; 1 dp = 3 px, 48 dp = 144 px). `font_scale` 1.0 y 2.0. Lo arranqué yo y lo apagué al terminar; la app quedó desinstalada y `font_scale` en 1.0.
- Herramientas: Postman CLI 1.74.0, Python 3 de la biblioteca estándar, `adb`, `uiautomator` y `sips` (macOS) para recortar capturas. No se instaló nada ni se tocó el proyecto. No se usó Gradle.

### Casos de 8.1 (Postman contra Cloud Run)

La colección `postman/activity-glossary.postman_collection.json` se regeneró con `scripts/build_postman_collection.py` y suma cinco peticiones (G12 a G15 y C7) a las 17 anteriores; el entorno nuevo es `postman/cloud-run.postman_environment.json` (sin token). Se corrió también la colección general `backend/postman/boticario-api.postman_collection.json` con el mismo entorno.

| ID | Qué cubre | Resultado | Evidencia |
| --- | --- | --- | --- |
| G1 | Lavanda: `Diurético` y `Carminativo` literales de Wikcionario con su `glossary.text` y `glossary.url` (con `oldid`), `Estimulante` adaptado de Wikipedia, los cinco campos `term`, `text`, `sourceName`, `url`, `adapted`, créditos de Wikcionario y de Wikipedia una vez cada uno | Pasa | `evidence/api/cloudrun-postman-glossary.txt` |
| G2 a G3 | Sedante adaptado (acónito) y Expectorante literal de Wikipedia (abeto) | Pasa | idem |
| G4 | Planta con solo explicaciones de Wikipedia: sin crédito de Wikcionario y Wikipedia una vez | Pasa | idem |
| G5 | Fórmula de enfermedad grave («…: cáncer») con `glossary` nulo y `activity` íntegra | Pasa | idem |
| G6 | Términos excluidos `Hemostático` y `Depurativo` (milenrama) con `glossary` nulo | Pasa | idem |
| G7 | `Antídoto (Laportea)` hereda la definición de `Antídoto` y conserva el calificador | Pasa | idem |
| G8 a G9 | Grupos pendientes de revisión: no se sirven ni su explicación ni el crédito | Pasa | idem |
| G10 | Planta sin ningún término: todo nulo y sin crédito de Wikcionario | Pasa | idem |
| G11 | El alias `rosmarinus-officinalis` resuelve y trae `glossary` | Pasa | idem |
| G12 | *Senna occidentalis*: el grupo con `activitySource` `Coffee` se llama `Sucedáneo del café`, con `glossary` nulo, y no existe ningún grupo ni uso `Café`; `Fiebre` nulo; `Purgante` adaptado; fórmulas de malaria y lepra nulas | Pasa | idem |
| G13 | Cardo (`cynara-cardunculus`), una sola explicación: `Diurético` de Wikcionario | Pasa | idem |
| G14 | Romero: 10 explicaciones, `Tónico` literal, los dos créditos una vez | Pasa | idem |
| G15 | Texto de atribución de Wikcionario (definiciones tomadas, primera oración, historial de autores) y de Wikipedia (menciona el glosario), con CC BY-SA 4.0 y `licenseUrl` | Pasa | idem |
| C1 a C2 | Forma del listado y del detalle (`uses`, orden de las claves de la raíz) sin cambios | Pasa | idem |
| C3 | `/openapi.json` desplegado describe `UseGlossaryDto` y `glossary` obligatorio | Pasa | idem |
| C4 y C7 | 401 sin token y con token inválido (`application/problem+json`, sin datos) | Pasa | idem |
| C5 a C6 | `/v1/goals` y `/v1/goals/{id}/plants` sin cambios y sin `glossary` | Pasa | idem |
| A0 | Colección general de `backend/postman/` contra Cloud Run: 24 peticiones, 101 aserciones | Pasa, 0 fallos | `evidence/api/cloudrun-postman-general.txt` |
| S1 a S8 | Barrido de las 2.354 plantas de Cloud Run (`scripts/cloudrun_sweep.py`) contra `data/seed/glossary.json` por la regla de la forma base: texto, URL, fuente y `adapted` iguales; ningún grupo servido con término sin `glossary`; ninguna fórmula con `glossary`; forma de cada grupo; créditos (Wikcionario si y solo si hay explicación de Wikcionario, Wikipedia una vez, CC BY-SA 4.0 con `licenseUrl`); 5.172 grupos con explicación en 1.207 plantas y 1.133 con crédito de Wikcionario (las mismas cifras de la base local); los 36 grupos `Coffee` se llaman `Sucedáneo del café` y ninguno `Café` | Pasa | `evidence/api/cloudrun-sweep-output.txt` y `evidence/api/cloudrun-sweep-results.json` |

El barrido no usa una base local (`data/build/catalog.db` no existe en esta copia): compara la API desplegada con el archivo de la semilla, que es de donde sale la base de la imagen.

### Casos de 8.2 (emulador con el APK contra Cloud Run)

Plantas: Lavanda (varias explicaciones), Romero (varias), Cardo (una sola, con una fórmula de enfermedad grave), Yerba mansa (ninguna, con la fórmula «…: cáncer»), *Senna occidentalis* (`Sucedáneo del café`, `Fiebre` y fórmulas de malaria y lepra), Milenrama (términos excluidos `Hemostático` y `Depurativo`) y *Alocasia macrorrhizos* (`Antídoto (…)`). Las capturas están en `evidence/cloudrun/`.

| ID | Qué cubre | Resultado | Evidencia |
| --- | --- | --- | --- |
| U1 | Lavanda en `Usos` al 100 %: línea «Aviso sobre usos» al inicio, grupos con título y a su derecha, en la misma fila, el icono de libro; bajo cada término con explicación, la etiqueta gris «Significado general del término» y `Término: «definición» (Wikcionario)` con la fuente enlazada; `Estimulante` dice «(adaptado de Wikipedia)»; `Espasmo`, `Perfume` y `Repelente de insectos` sin etiqueta ni hueco | Pasa | `01-lavanda-usos-100.png`, `02-lavanda-usos-100-scrolled.png` y `a11y-arbol-usos-lavanda.txt` |
| U2 | Romero: las 10 explicaciones del API (Carminativo, Estimulante, Estomacal, Nervino, Rubefaciente, Cardiotónico, Colagogo, Diurético, Emenagogo, Tónico) con etiqueta; el resto de grupos y la fórmula sin ella | Pasa | `18-romero-usos.png` |
| U3 | Una sola explicación (Cardo): solo `Diurético` lleva etiqueta; `Laxante suave` y la fórmula «…: diabetes» no | Pasa | `13-cardo-una-explicacion-y-formula.png` |
| U4 | Ninguna explicación (Yerba mansa): ninguna etiqueta, grupos con título e icono, fórmula mostrada tal cual | Pasa | `14-yerba-mansa-sin-explicaciones.png` |
| U5 | Enfermedad grave: «Uso tradicional, sin eficacia demostrada: cáncer, diabetes, malaria y lepra» se muestra con su texto exacto, sin explicación | Pasa | capturas 13 y 14 y `evidence/cloudrun/a11y-otras-plantas.txt` |
| U6 | Término excluido: `Hemostático` y `Depurativo` (milenrama) sin etiqueta | Pasa | `16-milenrama-hemostatico-excluido.png` |
| U7 | `Antídoto (Laportea)` conserva el calificador en el título y la línea empieza con «Antídoto:» (Wikipedia, literal, sin «adaptado de») | Pasa | `17-alocasia-antidoto-calificador.png` |
| U8 | «Sucedáneo del café» en *Senna occidentalis* (4 citas, sin explicación) y ningún «Café» | Pasa | `15-senna-sucedaneo-del-cafe.png` |
| U9 | Sin «Lugares»: ningún nodo con «Lugares» en el árbol de Lavanda, Romero, Cardo, Yerba mansa, *Senna* ni *Alocasia*, ni los países (Turquía, China, …) | Pasa | `a11y-arbol-usos-lavanda.txt` (0 coincidencias) y las capturas |
| U10 | Diálogo «Aviso sobre usos» al 100 %: título, texto completo igual al del spec (con la oración sobre las explicaciones de términos) y botón «Entendido»; se cierra con «Entendido», con Atrás y tocando fuera, sin cambiar la pestaña ni el estado de las citas; el texto del aviso no se ve en la pestaña | Pasa | `08-aviso-dialogo-100.png` |
| U11 | Diálogo al 200 %: título y texto completos (desplazable hasta la oración final), «Entendido» alcanzable de 405x144 px | Pasa | `11-aviso-dialogo-200.png` y `12-aviso-dialogo-200-final-scroll.png` |
| U12 | Línea «Aviso sobre usos»: un solo botón de 455x144 px (152x48 dp) con la etiqueta «Aviso sobre usos» | Pasa | árbol de accesibilidad |
| U13 | Icono de libro, posición: a la derecha del título, en la misma fila y centrado con su primera línea; mide 20 dp (unos 58 px) y su área táctil 144x144 px (48x48 dp), también al 200 % | Pasa | capturas 02 y 09; árbol con `(888, 677, 1032, 821)` |
| U14 | Área táctil con `input tap` en coordenadas medidas: 4 px fuera por la izquierda (884, 750), por arriba (960, 674) y por abajo (960, 826) no hacen nada; 2 px dentro de la esquina superior izquierda (890, 680) despliega, y 2 px dentro de la inferior derecha (1030, 818) pliega | Pasa | `evidence/cloudrun/toque-area-48dp.txt` |
| U15 | Plegar y desplegar: las citas empiezan plegadas; al tocar se muestran las dos citas de Carminativo debajo de la explicación, sin mover el icono ni afectar a los demás grupos; al volver a tocar se pliegan | Pasa | `03-carminativo-citas-desplegadas.png` |
| U16 | Tooltip: «Ver 2 citas» al mantener pulsado plegado y «Ocultar citas» desplegado | Pasa | `04-tooltip-ver-2-citas-longpress.png` y `05-tooltip-ocultar-citas-longpress.png` |
| U17 | Estado de plegado al cambiar de pestaña: se desplegó Carminativo, se fue a `Fuentes` y se volvió a `Usos`: sigue desplegado y los demás plegados | Pasa | árbol de accesibilidad |
| U18 | Cambio de icono de cerrado a abierto | Falla con `d9a5e4c` (D2); **pasa tras `b5450c1`** (ver la reverificación) | recortes de las capturas 03 y 05 (fallo) y `21-d2-reverif-iconos-plegado-y-desplegado.png` (corrección) |
| U19 | Lectura de accesibilidad del control: nodo botón clicable con la etiqueta «Ver 2 citas de Carminativo» plegado y «Ocultar citas de Carminativo» desplegado, con el nombre de la actividad; «Ver 1 cita de …» en singular | Pasa | árbol de accesibilidad |
| U20 | Lectura del glosario en el árbol: título, etiqueta y las explicaciones forman un solo nodo de lectura («Carminativo \| Significado general del término \| Estimulante \| …») y el enlace es un nodo clicable aparte, «Wikcionario. Abre la fuente de la explicación» o «Wikipedia. Abre la fuente de la explicación», sin la URL como texto | Pasa | árbol de accesibilidad |
| U21 | Enlace: al tocar «Wikcionario» se abre Chrome en `es.wiktionary.org/w/index.php?title=carminativo&oldid=5967250` | Pasa | `19-enlace-wikcionario-navegador.png` |
| U22 | 200 % de texto en Lavanda: la etiqueta, las explicaciones (también la adaptada, larga) y el enlace se leen completos, sin truncar ni desbordar; el título y el icono siguen en una fila y el área táctil sigue en 144x144 px | Pasa | `09-lavanda-usos-200-a.png` y `10-lavanda-usos-200-b.png` |
| U23 | `Fuentes` de Lavanda: Wikcionario en español y Wikipedia en español, una vez cada uno, con «Licencia: CC BY-SA 4.0» enlazada y su atribución | Pasa | `06-lavanda-fuentes.png` y `07-lavanda-fuentes-wikcionario-wikipedia.png` |
| U24 | `Fuentes` de Yerba mansa: sin Wikcionario y con Wikipedia (por la descripción) | Pasa (con la observación 1) | `20-yerba-mansa-fuentes-sin-wikcionario.png` |

### Defectos

#### D2. El icono de libro no cambia de cerrado a abierto (severidad media; cerrado tras `b5450c1`, ver la reverificación)

- **Requisito afectado:** `plant-passport`, «Usos como registros tradicionales trazables» (`Icons.menu_book_outlined` plegado y `Icons.menu_book` desplegado, «el icono pasa a libro abierto»), escenario «Desplegar y plegar citas», y «Accesibilidad del pasaporte» («el estado SHALL expresarse también en el icono (libro cerrado o abierto), no solo en el color»).
- **Pasos:**
  - Instalar el APK release y abrir Explorar, Lavanda y la pestaña `Usos`.
  - Recortar con `sips` el icono de Carminativo (plegado), tocarlo para desplegar y recortar de nuevo el mismo icono (desplegado).
  - Comparar los dos recortes.
- **Esperado:** el icono plegado (`menu_book_outlined`) y el desplegado (`menu_book`) se distinguen a simple vista.
- **Obtenido:** los dos estados dibujan el mismo libro relleno. Los recortes de 100x140 px del icono desplegado (Carminativo) y del plegado (Estimulante) en la misma captura (`03-carminativo-citas-desplegadas.png`) tienen el mismo `md5`, y la captura con el tooltip «Ocultar citas» (`05-tooltip-ocultar-citas-longpress.png`) muestra el mismo icono que la de «Ver 2 citas» (`04-tooltip-ver-2-citas-longpress.png`). El estado sí cambia en el tooltip, en la etiqueta accesible («Ocultar citas de Carminativo») y por las citas que aparecen debajo.
- **Reproducible:** sí, las dos veces que se probó. El código usa `Icons.menu_book_outlined` y `Icons.menu_book` (`app/lib/features/passport/presentation/passport_uses_tab.dart`) y las pruebas de widgets buscan los iconos por tipo, por lo que no ven que se dibujan igual.
- **Evidencia:** `evidence/cloudrun/03-carminativo-citas-desplegadas.png`, `04-tooltip-ver-2-citas-longpress.png`, `05-tooltip-ocultar-citas-longpress.png`.
- **Nota:** no se determinó si la causa es que esos dos glifos de la fuente `MaterialIcons` (puntos de código `e3dd` y `f1c2`) se ven igual a 20 dp o un problema de la compilación release; el resultado visible es el mismo. Una pareja de iconos que se distinga (por ejemplo, un libro cerrado y uno abierto) lo resolvería.

### Reverificación de D2 con `b5450c1` (2026-10-31)

Se instaló el APK release nuevo (`app-release.apk` compilado a las 20:47, que apunta a Cloud Run y no contiene `localhost` ni `10.0.2.2`) en el emulador `boticario_catalog_api36`, siempre con `-s emulator-5554`; el código usa `Icons.book_outlined` plegado y `Icons.menu_book` desplegado.

- **Resultado: D2 cerrado, U18 pasa.**
- **U18:** en una misma captura (`evidence/cloudrun/21-d2-reverif-iconos-plegado-y-desplegado.png`), con Carminativo desplegado y Estimulante plegado, los recortes de 100x140 px de los dos iconos tienen `md5` distintos y se distinguen a simple vista: plegado es un libro cerrado con marcador y desplegado es un libro abierto con renglones. Antes de la corrección eran idénticos.
- **Regresión del icono, 100 %:**
  - Posición a la derecha del título y en su misma fila, tamaño de 20 dp y área de 144x144 px (48x48 dp): igual que antes.
  - Toques: 4 px fuera por la izquierda, por arriba y por abajo no hacen nada, y 2 px dentro de las esquinas sí despliegan y pliegan (`evidence/cloudrun/toque-area-48dp-reverif.txt`).
  - Tooltips por pulsación larga: «Ver 2 citas» con el libro cerrado y «Ocultar citas» con el libro abierto (`23-d2-reverif-tooltip-ver-citas.png` y `24-d2-reverif-tooltip-ocultar-citas.png`).
  - Árbol de accesibilidad: nodo clicable «Ver 2 citas de Carminativo» y «Ocultar citas de Carminativo», sin «Lugares».
- **200 % de texto:** el icono sigue a la derecha del título, con área de 144x144 px, el libro plegado y el desplegado siguen distinguiéndose (recortes con `md5` distintos de `25-d2-reverif-200-plegado.png` y `26-d2-reverif-200-desplegado.png`) y el árbol cambia entre «Ver 2 citas de Carminativo» y «Ocultar citas de Carminativo» (`a11y-reverif-d2-200.txt`).
- Siguen sin verificarse con TalkBack con voz el estado plegado o expandido (observación 2).

### Observaciones

1. **Atribución de Wikipedia.** El crédito de Wikipedia dice «En el glosario de actividades, el texto es la primera oración de un artículo o una paráfrasis…» también en plantas sin ninguna explicación de Wikipedia, como Yerba mansa (su crédito viene de la descripción). Ya estaba observado en la QA local; ahora se confirma en Cloud Run y en la app. Es una imprecisión de texto, sin efecto sobre la licencia.
2. **TalkBack.** TalkBack está instalado en el emulador; lo activé, no logré obtener su voz ni por `logcat` y lo desactivé (`enabled_accessibility_services` vuelto a su valor original, nulo). La lectura se verificó con el árbol de `uiautomator`, que no expone el estado «expandido» del botón. Quedan sin comprobar con el lector de pantalla real: el anuncio del estado plegado o expandido y el orden de lectura.
3. **Visor reducido al 200 %.** La franja de contenido bajo la cabecera de la planta mide unos 200 px y la barra de navegación ocupa dos filas, de modo que hay que desplazar la página; es previo a este cambio y ya estaba observado.
4. **Primer arranque de Chrome.** Al abrir el enlace, Chrome mostró sus pantallas de bienvenida (se pasaron con «Use without an account» y «No thanks»); no es del producto.
5. **Texto de la tarea 8.1.** Nombra `qa/activity-glossary-api-results.md`; los resultados de la API están en este informe.

### No verificado

- TalkBack con voz (observación 2) y el estado «expandido» del control en la semántica (lo cubren las pruebas de widgets de la rama, que no se corrieron aquí).
- El enlace de «Wikipedia» y los textos al 200 % en `Fuentes` y en Romero: el enlace de Wikipedia se comprobó en la QA local y el 200 % solo en Lavanda (`Usos` y diálogo).
- Contraste de color de la etiqueta gris y del enlace (no se midió).
- Una planta de Wikipedia literal en el emulador (se cubre con Antídoto y con la API; el abeto con `Expectorante` se vio en la QA local).
- La suite de pruebas del producto (`cargo test`, `flutter test`), que quedan en las tareas 6.5 y 7.8.

### Tareas

- 8.1: cumplida contra Cloud Run (la API local se había cumplido en la QA anterior). Sin defectos del producto.
- 8.2: cumplida con el APK contra Cloud Run. D2 se corrigió en `b5450c1` y quedó cerrado en la reverificación. La casilla de `tasks.md` no se marca aquí.

### Cómo re-ejecutar

Desde la raíz del repositorio, con el token solo en una variable de entorno de la shell (sin escribirlo en archivos).

```bash
TOKEN="$(gcloud secrets versions access 1 --secret=boticario-api-tokens --project boticario-ai | awk -F, '{print $1}' | tr -d '[:space:]')"
postman collection run openspec/changes/activity-glossary/qa/postman/activity-glossary.postman_collection.json -e openspec/changes/activity-glossary/qa/postman/cloud-run.postman_environment.json --env-var "token=$TOKEN"
(cd backend/postman && postman collection run boticario-api.postman_collection.json -e ../../openspec/changes/activity-glossary/qa/postman/cloud-run.postman_environment.json --env-var "token=$TOKEN")
TOKEN="$TOKEN" python3 -I openspec/changes/activity-glossary/qa/scripts/cloudrun_sweep.py https://boticario-api-d3xv5q3iaa-pv.a.run.app "$PWD" salida.json
```

Para el emulador: `adb -s emulator-5554 install -r app/build/app/outputs/flutter-apk/app-release.apk` y los ayudantes `scripts/ui.py` y `scripts/ui_cr.py` (`home`, `open "<búsqueda>" "<patrón>"`, `full`, `scrolltap`). El buscador de Explorar filtra al teclear; el patrón de la planta debe coincidir con el botón de resultado y no con el campo de búsqueda (si ambos dicen lo mismo, tocar por coordenadas).

## Verificación del icono de definición (2026-10-31)

Verificación del ajuste del usuario de `b046704`: en `Usos`, la explicación del término empieza oculta y un icono de información (`Icons.info_outline` plegado, `Icons.info` desplegado, 20 dp, área de 48 dp) la controla, a la izquierda del libro de citas y en la fila del título. Esta sección sustituye, para la explicación, a los casos U1 a U9 y U20 a U22 de la sección anterior, que se hicieron cuando la explicación se veía siempre (el contenido, el formato y el enlace no cambian; solo cómo se muestran).

### Resumen

- Pasan todos los casos; no se encontró ningún defecto del producto. Hay una observación de contenido (sobre `Repelente (serpientes)`).
- Entorno: APK release que compiló el orquestador (21:03), que apunta a Cloud Run (la cadena `run.app` está en `libapp.so` y no hay `localhost` ni `10.0.2.2`), instalado en `emulator-5554` (`boticario_catalog_api36`, 360x640 dp). Emulador apagado, app desinstalada y `font_scale` en 1.0 al terminar. No se usó el teléfono físico. Evidencia en `evidence/cloudrun/`, numerada de la 30 a la 41.

### Casos

| ID | Qué cubre | Resultado | Evidencia |
| --- | --- | --- | --- |
| I1 | Lavanda: icono de información solo en los usos con explicación (Carminativo, Estimulante, Colagogo, Diurético, Estomacal, Nervino, Sudorífico, Vermífugo), a la izquierda del libro y en la misma fila del título; `Espasmo`, `Perfume` y `Repelente de insectos` solo tienen el libro, sin hueco; la explicación está oculta al abrir `Usos` | Pasa | `30-ico-lavanda-inicial-oculta.png`, `31-ico-lavanda-espasmo-sin-icono-info.png` y `a11y-ico-lavanda-inicial.txt` |
| I2 | Mostrar y ocultar: al tocar el icono aparecen la etiqueta «Significado general del término» y la línea `Carminativo: «…» (Wikcionario)` bajo el título; al volver a tocar desaparecen | Pasa | `ico-combinaciones-carminativo.txt` y `32-ico-info-desplegado-citas-plegadas.png` |
| I3 | Independencia en las cuatro combinaciones (ninguno, solo explicación, ambos, solo citas) y vuelta al inicio: cada toque cambia solo su control; con ambos abiertos la explicación va antes de las citas | Pasa | `ico-combinaciones-carminativo.txt`, `33-ico-info-y-citas-desplegados.png` y `34-ico-solo-citas-desplegadas.png` |
| I4 | Iconos: en una misma captura, el de información plegado y desplegado y el de libro plegado y desplegado se distinguen a simple vista (círculo con una «i» sin relleno frente a círculo relleno; libro cerrado con marcador frente a libro abierto) y los recortes de 100x120 px tienen `md5` distintos entre estados, también contra la captura del estado inicial | Pasa | `33-ico-info-y-citas-desplegados.png` y `30-ico-lavanda-inicial-oculta.png` |
| I5 | Área de 48 dp (144 px, separación de 12 px entre los dos iconos), con `input tap` en coordenadas medidas: 4 px fuera por los cuatro lados de cada icono y en la separación (x=882) no hacen nada; 2 px dentro de los bordes izquierdo y derecho de cada icono sí cambian solo su estado, sin pisar al vecino | Pasa | `ico-area-48dp.txt` |
| I6 | Tooltips por pulsación larga: «Ver significado» con el icono plegado y «Ocultar significado» con el desplegado | Pasa | `35-ico-tooltip-ver-significado.png` y `36-ico-tooltip-ocultar-significado.png` |
| I7 | Árbol de accesibilidad: botones clicables «Ver significado de Carminativo» y «Ocultar significado de Carminativo» (con el término, no la actividad completa, como pide el spec) junto a «Ver 2 citas de Carminativo» y «Ocultar citas de Carminativo»; el nodo de lectura del grupo lista el título, la etiqueta y la cita en ese orden | Pasa | `ico-combinaciones-carminativo.txt`, `a11y-ico-lavanda-inicial.txt` y `a11y-ico-200.txt` |
| I8 | Estado al cambiar de pestaña: Carminativo con la explicación abierta y las citas plegadas, y Estimulante con ambas abiertas; tras ir a `Fuentes` y volver a `Usos` no cambia nada | Pasa | `ico-estado-cambio-pestana.txt` |
| I9 | Yerba mansa: ningún icono de información en `Catarro`, `Llaga` ni la fórmula «…: cáncer», solo el libro | Pasa | `ico-yerba-mansa-sin-info.txt` y `38-ico-yerba-mansa-sin-iconos-info.png` |
| I10 | 200 % de texto con un título largo (Fresno blanco, `Repelente (serpientes)`): el título se parte en dos líneas, los dos iconos quedan a la derecha sin desbordar y con áreas de 144x144 px; la fórmula larga también se parte y solo lleva el libro; con ambos abiertos la etiqueta, la explicación completa, el enlace y la cita se leen sin truncar | Pasa | `39-ico-200-titulo-largo-plegado.png`, `40-ico-200-titulo-largo-ambos-desplegados.png`, `41-ico-200-explicacion-y-cita-completas.png` y `a11y-ico-200.txt` |
| I11 | Enlace de la fuente tras desplegar la explicación: «Wikcionario. Abre la fuente de la explicación» abre Chrome en `es.wiktionary.org/w/index.php?title=carminativo&oldid=5967250` y al volver la explicación sigue desplegada | Pasa | `37-ico-enlace-wikcionario-desplegado.png` |

### Defectos

Ninguno.

### Observaciones

1. **Contenido de `Repelente (serpientes)`.** El grupo hereda la definición de `Repelente` («Substancia líquida o pastosa que se frota en la piel para ahuyentar insectos picadores, principalmente mosquitos.», Wikcionario) por la regla de la forma base, pero la actividad habla de serpientes. Es el comportamiento especificado para los calificadores (como `Antídoto (…)`) y la etiqueta «Significado general del término» lo atenúa, pero aquí la definición y el calificador se contradicen; se informa para que el usuario decida.
2. **Etiqueta con el término.** La etiqueta accesible usa el término («Ver significado de Repelente»), no la actividad completa («Repelente (serpientes)»), como pide el spec; dos grupos del mismo término en una planta se anunciarían igual (por ejemplo `Antídoto (Laportea)` y `Antídoto (urticaria)` en *Alocasia*).
3. Siguen sin verificarse con TalkBack con voz el anuncio del estado expandido de los dos controles (observación 2 de la sección anterior) ni el contraste de color.
