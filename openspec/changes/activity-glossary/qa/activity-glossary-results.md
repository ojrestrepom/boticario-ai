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
