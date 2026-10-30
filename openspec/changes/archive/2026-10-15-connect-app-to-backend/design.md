# Design

## Context

Véanse `proposal.md` y las specs delta para los requisitos observables. Estado de partida:

- La app lee `app/assets/data/plant_catalog.json` (único asset) con `PlantCatalogAssetDataSource`, un parseo manual estricto que lanza `PlantCatalogLoadException`. `plantCatalogProvider` es un `FutureProvider<PlantCatalog>` sin reintento automático y `Plant` usa `usdaPlantId` entero.
- La búsqueda de Explorar es en memoria (`plant_search.dart`) y el Pasaporte recibe un `Plant` y un `PlantCatalogProvenance` y muestra origen, descripción, procedencia y bibliografía.
- El manifest principal de Android no declara `INTERNET` (solo `debug` y `profile`), no hay `network_security_config` ni lectura de `dart-define`.
- El smoke (`integration_test/catalog_smoke.dart`) envuelve `app.main()` en un guard que deniega todo HTTP y espera cinco filas fijas.
- El backend sirve `GET /v1/plants` (`items`, `total`, `limit`, `offset`; `limit` 1..100, por defecto 20; `q` hasta 200 caracteres, sin caracteres de control) y `GET /v1/plants/{id}`, con errores `application/problem+json`. Ninguna planta tiene nombre común en `es`: 1.577 de 2.376 tienen nombres comunes (`en` y `und`) y 799 no tienen ninguno.

## Goals / Non-Goals

**Goals:**

- Que Explorar y el Pasaporte muestren el catálogo real del backend sin inventar datos ni perder la accesibilidad ya especificada.
- Un cliente pequeño, testeable sin red y tolerante a cambios aditivos de `/v1`.
- Que la falta de conectividad se vea como un error reintentable y no afecte a Inicio ni a Buscar por objetivo.
- Conservar la guía de regresión del backend contra la curación manual de las cinco plantas.

**Non-Goals:**

- Nombres comunes en español, caché o modo offline, despliegue del backend y HTTPS.
- Favoritos, historial, perfil y resultados de Buscar por objetivo.
- CI del backend y cualquier cambio del contrato de la API.

## Decisions

### 1. `package:http` con cliente inyectado y parseo manual

El cliente usa `package:http` (dependencia nueva, versión fijada en `pubspec.lock`). Un provider de Riverpod entrega el `http.Client` y los tests lo sustituyen por `MockClient` de `package:http/testing.dart`. El parseo es manual, sin codegen: exige los campos requeridos y sus tipos según `backend/openapi.json`, ignora campos desconocidos y lanza un error legible ante JSON inválido o campos faltantes, sin completar datos.

Por qué: la superficie son dos endpoints de solo lectura, así que una librería pequeña y un parseo explícito bastan, igual que el lector del asset, y no añaden generación de código al flujo. Ignorar campos desconocidos permite cambios aditivos en `/v1`.

Alternativas descartadas: `dio` (interceptores, cancelación y adaptadores que no se necesitan; más superficie) y `json_serializable`/`freezed` (codegen y `build_runner` para unos pocos modelos).

### 2. Dirección del backend por `--dart-define`

`const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8080')`: el emulador Android llega al Docker del Mac por `10.0.2.2`. Para un dispositivo físico se pasa `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080`. Se tolera una barra final. Solo se usan `GET /v1/plants` y `GET /v1/plants/{id}` (id codificado en la URL) con `Accept: application/json`, sin autenticación, sin cabeceras ni datos de usuario y sin hablar con otro host.

Por qué: la dirección se fija en compilación, sin pantalla de ajustes ni persistencia, y el valor por defecto cubre el caso habitual.

Alternativa descartada: un archivo de configuración (en `assets/` o `.env`) que habría que versionar, ignorar o cargar en tiempo de ejecución, y que reintroduciría un asset.

### 3. HTTP en claro solo en `debug` y `profile`

El permiso `INTERNET` pasa al manifest principal (un build `release` no tendría red, porque hoy solo `debug` y `profile` lo declaran). `android:usesCleartextTraffic="true"` se declara únicamente en los manifests de `debug` y `profile`. `release` queda sin HTTP en claro: todavía no hay backend desplegado y, cuando lo haya, será HTTPS.

Alternativas descartadas: `network_security_config` con dominios permitidos (el emulador usa `10.0.2.2` y un dispositivo físico una IP variable, así que no hay lista cerrada útil) y `cleartext` en `release` (abre HTTP en claro en binarios distribuibles sin necesidad).

### 4. Nombre para mostrar

El nombre principal es el primer nombre común (en el idioma que venga) y el científico es el secundario. Si no hay nombre común, el científico es el principal y no hay secundario. La regla vive en el dominio y la usan Explorar y el Pasaporte. No se traduce ni se inventa: los nombres en español serán consolidación futura del backend (una fuente `es`), no trabajo de la app.

Por qué: el 33 % de las plantas no tiene nombre común y ninguna lo tiene en español, así que la regla debe degradar a lo único siempre disponible.

### 5. Modelos y repositorio

En `lib/features/catalog/domain/` se definen `PlantSummary` (`id`, `scientificName`, `commonNames`, `family`), `PlantPage` (`items`, `total`, `limit`, `offset`) y `Plant` (`id`, `scientificName`, `family`, `names` con `kind` e idioma, `parts`, `uses` con `reference`). Se eliminan `PlantCatalog`, `PlantCatalogProvenance`, `SourceRecord`, `TraditionalUse`, `PlantReference`, `PlantKind` y el asset. La interfaz `CatalogRepository { Future<PlantPage> listPlants({query, limit, offset}); Future<Plant?> getPlant(id) }` devuelve `null` en 404 y tiene una implementación HTTP. Una excepción propia representa los errores de cliente.

Por qué: la interfaz aísla la UI del transporte y permite tests de widget con repositorio o con `MockClient`. El `null` en 404 mantiene «no encontrada» fuera del camino de errores.

### 6. Errores: legibles, reintentables y 404 distinguido

Cada petición tiene un tiempo máximo de 10 s. Fallo de conexión, timeout, 5xx, cuerpo inválido y 400 producen la excepción de cliente, con mensaje legible y acción de reintento en la UI. El 404 del detalle no es error: es «planta no encontrada». Sin conectividad, Explorar y el Pasaporte muestran error con «Reintentar»; Inicio y Buscar por objetivo siguen funcionando porque no usan red.

### 7. Paginación con scroll infinito

Páginas de 50 (`limit=50`), carga automática al acercarse al final, pie de lista con indicador de carga y, si falla, error reintentable en el pie que conserva los elementos ya cargados. El fin de lista se determina por `total`.

Por qué: es la forma natural de recorrer 2.376 plantas con la barra de desplazamiento ya especificada y no añade controles.

Alternativa descartada: botón «Cargar más», que añade un control, obliga a 48 dp de área de toque y etiqueta, y rompe el flujo de lectura.

### 8. Búsqueda remota con debounce y descarte de respuestas atrasadas

La búsqueda se delega a la API con `q`. La app solo recorta espacios exteriores y limita la consulta a 200 caracteres (más allá, o con caracteres de control, la API respondería 400). Un debounce de unos 300 ms evita una petición por pulsación y cada consulta lleva una generación: la respuesta de una consulta anterior nunca pisa la vigente. Consulta vacía lista todo. `plant_search.dart` y su normalización desaparecen, porque la API ya normaliza mayúsculas, acentos y espacios.

Los filtros `Todas`/`Plantas`/`Aceites` siguen siendo locales. Para `Aceites` se elige lo más simple: el estado vacío específico se muestra sin pedir nada a la red, ya que no hay aceites en el catálogo. `Todas` y `Plantas` usan la misma lista.

### 9. Estado de Explorar en un `Notifier` de Riverpod 3

Un `Notifier` (con estado asíncrono) mantiene consulta, filtro, páginas cargadas, `total`, indicadores de carga y error del pie, y la generación para descartar respuestas atrasadas. Vive mientras dure la sesión, de modo que volver desde el Pasaporte conserva consulta, filtro y posición de lista (el requisito ya existe en `explore-screen`). El controlador de scroll y el campo de búsqueda restauran su valor desde ese estado.

Alternativa descartada: estado local en el `State` del widget, que se pierde al desmontar la ruta y obligaría a recargar las páginas al volver.

### 10. Pasaporte con un provider por id

`PlantPassportRoutePage` recibe el id como texto (slug, p. ej. `lavandula-angustifolia`) y lo resuelve con un provider de familia por id sobre `getPlant`. Estados: carga, error reintentable (invalida el provider), no encontrada (404, con regreso seguro) y datos. El router conserva `/explore/:plantId` sin `int.tryParse`.

`General` muestra familia (o `No disponible en fuente` si es `null`), nombres comunes con su idioma, partes registradas (como dato de fuente, no recomendación) y `Tipo de aceite: no aplicable`. Origen y descripción desaparecen, porque el contrato no los tiene. `Propiedades` no cambia. `Usos` muestra cada uso con su actividad, `Registro tradicional`, la aclaración no recomendatoria y la cita de su referencia, o un vacío explícito. Se conserva la bibliografía deduplicada de `General` si ya existe. Los usos largos (Romero tiene unos 60) se muestran en una lista desplazable, sin truncar.

### 11. La procedencia sale de la app

No hay crédito en pantalla: la fuente activa es CC0 y no lo exige. La atribución queda en `README.md` y `docs/`. Si un dataset futuro exigiera créditos visibles, se resolverá con un dato neutro de créditos del backend en un cambio propio (el mismo criterio que `remove-api-provenance`).

### 12. El asset se mueve al backend como fixture

`app/assets/data/plant_catalog.json` se mueve a `backend/catalog-ingest/tests/fixtures/` y `asset_crosscheck.rs` (marcado `#[ignore]`) lo lee de ahí, porque sigue guardando que la derivación del backend coincide con la curación manual de las cinco plantas. `backend/README.md` se actualiza. Un `git mv` conserva el historial. Se quita la sección `assets` de `pubspec.yaml`.

Alternativa descartada: borrarlo sin más, que dejaría sin guardia la derivación del backend.

### 13. Guard HTTP del smoke y tests con fixtures

El smoke (`integration_test/catalog_smoke.dart`) requiere el backend en marcha (`docker compose up`) y el emulador. El guard `HttpOverrides.runZoned` deja de denegar todo: permite solo el host de la URL base y deniega el resto. El flujo busca una planta real (por ejemplo `lavandula` y espera «English Lavender» y «Lavandula angustifolia»). `test/app/catalog_smoke_contract_test.dart` ejecuta el mismo flujo en widget test con un `MockClient` que sirve fixtures. Las fixtures JSON pequeñas (una planta con nombres comunes, una sin ninguno, una con `family` `null`, una con usos y una sin usos) viven en `app/test/fixtures/api/` y las comparten los widget tests.

Por qué: el guard sigue protegiendo contra tráfico a hosts inesperados, y el test de contrato cubre en CI lo que el smoke cubre en el emulador.

### 14. Specs y fin de la excepción de compatibilidad

`plant-catalog` se elimina entera: sus cuatro requisitos pasan a `## REMOVED Requirements` con `**Reason**` y `**Migration**`. El catálogo vive en el backend (`catalog-ingest` y `catalog-api`), los límites de contenido de la app siguen en `plant-passport` y la disponibilidad y los errores pasan a `catalog-client`. Se añade `catalog-client` y se modifican `explore-screen`, `plant-passport` y `flutter-app-bootstrap`.

`catalog-api` no lleva delta, pero con este cambio la API tiene su primer consumidor: la excepción de «Compatibilidad dentro de `/v1`» (cambios incompatibles mientras no haya consumidores) deja de aplicar y, desde aquí, `/v1` solo admite cambios aditivos. El parseo que ignora campos desconocidos es la contrapartida del cliente.

### 15. Barra inferior del Pasaporte adaptada al texto grande (desvío por DEF-01 de QA)

QA encontró un defecto preexistente (anterior a este cambio) contra la spec vigente de `plant-passport`: con el texto del sistema al 200 % en 360x640 dp, la barra inferior del Pasaporte partía «Favorit/os» e «Histori/al» en dos líneas. El usuario decidió corregirlo dentro de este cambio, dentro de la tarea 7.5. La solución replica la adaptación 2x2 de Explorar (`Wrap` con cada elemento a la mitad del ancho cuando la escala del texto es ≥ 1.5, `Row` con `Expanded` si no) sin unificar las dos barras, que queda como posible limpieza futura.

## Risks / Trade-offs

- [Emulador frente a dispositivo físico: `10.0.2.2` solo sirve en el emulador] → documentar `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080` y la misma red.
- [HTTP en claro en `debug` y `profile`] → acotado a esos manifests; `release` sin HTTP en claro y HTTPS cuando haya backend desplegado.
- [Sin nombres en español: la mayoría de las filas muestra nombres en inglés o solo el científico] → decisión aceptada; la consolidación con una fuente `es` es trabajo futuro del backend.
- [La app y el smoke necesitan el backend en marcha] → documentarlo; sin backend, Explorar y el Pasaporte muestran error reintentable y Inicio y Buscar por objetivo siguen funcionando.
- [`q` de más de 200 caracteres o con caracteres de control daría 400] → la app recorta y limita la consulta a 200 caracteres y trata cualquier 400 como error legible y reintentable.
- [La CI no cubre el smoke (necesita emulador y backend)] → el test de contrato con `MockClient` cubre el mismo flujo sin red; el smoke se ejecuta a mano y se reporta como no ejecutado si falta dispositivo o backend.
- [Listas largas de usos (Romero tiene unos 60)] → lista desplazable sin truncar y comprobación con texto al 200 %.
- [Respuestas atrasadas al escribir rápido] → generación por consulta que descarta las respuestas obsoletas, con test dedicado.
- [Cambios futuros del contrato rompen a la app] → desde este cambio `/v1` solo admite cambios aditivos y el parseo ignora campos desconocidos.

## Migration Plan

Orden de las tareas: (1) cliente de catálogo con sus tests sin tocar las pantallas; (2) Explorar; (3) Pasaporte y router; (4) retirada del asset, de la procedencia y de la búsqueda local, y movimiento del fixture al backend (se hace después de las pantallas para que cada paso compile y pase los tests); (5) smoke y test de contrato; (6) documentación, doc comment y `openapi.json`; (7) verificación global y QA.

Desde el paso 4 el asset deja de existir en la app: la app necesita el backend en marcha. No hay datos que migrar. Reversión: revertir los commits del cambio; el fixture vuelve a `app/assets/data/` con `git mv`.
