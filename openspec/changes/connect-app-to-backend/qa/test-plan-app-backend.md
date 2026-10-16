# Plan de pruebas: app conectada al backend (connect-app-to-backend, tareas 7.4 y 7.5)

Commit probado: `4ff10be`. Alcance: la app Flutter Android consume `GET /v1/plants` y `GET /v1/plants/{id}`. Criterios de aceptación: los deltas de `openspec/changes/connect-app-to-backend/specs/` (`catalog-client`, `explore-screen`, `plant-passport`, `flutter-app-bootstrap`, `plant-catalog` eliminada) y los requisitos vigentes de `explore-screen`, `plant-passport`, `home-screen` y `goal-search-screen`.

## Estrategia

- Caja negra sobre el emulador `emulator-5554` (AVD `boticario_catalog_api36`, 360x640 dp, Android 16) con el APK debug normal y el backend en Docker.
- Técnicas: particiones de equivalencia (planta con y sin nombre común, `family` nula, con y sin usos, muchos usos), valores límite (consulta de 200 caracteres, fin de lista, página 50), transición de estados (cargando, datos, error, vacío, no encontrada) y casos negativos (backend detenido, 400, 5xx, JSON inválido, campo ausente, timeout).
- Los casos de red se observan con un proxy de registro (`scripts/logproxy.py`, escucha en 127.0.0.1:8080 y reenvía al contenedor publicado en 18080) porque la API no registra peticiones en `docker compose logs`. Los casos con el backend detenido usan la topología directa (`docker compose stop` / `start` en 8080, sin proxy).
- La pirámide se respeta: los tests unitarios y de widget del proyecto ya cubren debounce exacto, parseo y MockClient; aquí se ejecutan flujos de usuario y contrato real.
- Inyección de fallos con reglas del proxy (retraso, estado, cuerpo, corte de conexión).
- Accesibilidad: texto al 200 % (`font_scale` 2.0), tamaño de controles (>= 48 dp) y overflow en logcat. TalkBack no se ejecuta.

## Casos

Entorno común: backend en marcha salvo indicación; app debug instalada; `font_scale` 1.0 salvo indicación. «R-» indica el escenario o requisito de spec cubierto.

| ID | Cubre | Técnica | Pasos | Esperado |
|---|---|---|---|---|
| TC-01 | R-bootstrap «Smoke Android» | E2E real | `flutter test integration_test/app_test.dart -d emulator-5554` con backend | Pasa |
| TC-01b | R-bootstrap «Smoke Android sin dispositivo o backend» | Negativo | Mismo comando con `docker compose stop` | Falla (no exitoso) |
| TC-03 | R-catalog-client «Pruebas sin red», R-bootstrap «Verificaciones» | Regresión | `flutter test test/` con el backend detenido | Todo pasa |
| TC-04 | R-catalog-client «Permisos y transporte en Android» | Inspección | `grep` de los tres manifests y manifests fusionados debug y release | main con INTERNET sin cleartext; debug y profile con cleartext; release sin cleartext |
| D-01 | R-bootstrap «Flujo de desarrollo documentado» | Inspección | Revisar `README.md`, enlaces y regla de párrafos de una línea | Backend primero, 10.0.2.2, `--dart-define`, smoke con backend; sin «cinco plantas»; enlaces resuelven |
| E-01 | R-explore «Vista inicial», «Scroll infinito» | Valor límite | Abrir Explorar y desplazar más de 50 filas | 50 por página, orden alfabético por científico, páginas siguientes añadidas sin reiniciar |
| E-01b | R-explore «Abrir y volver de una ficha» | Estado | Con más de 50 filas cargadas abrir una fila y volver | Misma posición |
| E-02 | R-explore «Búsqueda», R-client «Nombre para mostrar» | Equivalencia | Buscar `lavandula` | 7 filas, primera «English Lavender» / «Lavandula angustifolia», `Lavandula spica` solo científico, pie «No hay más resultados» |
| E-03a/b/c | R-explore «Búsqueda por cualquiera de los nombres», R-client «Consulta con caracteres especiales» | Equivalencia | Buscar `  LAVANDULA  `, `mentha   SPICATA` y `àrnica` | Mismos resultados que la forma normalizada; `q` recortada y codificada |
| E-04a | R-explore «Resultado sin coincidencias» | Negativo | Buscar `zzzqqq` | «No se encontraron plantas» |
| E-05a | R-explore «Filtro de aceites sin catálogo» | Estado | Seleccionar `Aceites` con consulta activa | «No hay aceites disponibles en este catálogo» y ninguna petición |
| E-05b | R-explore «Filtro y consulta combinados», «Borrar conserva filtro» | Combinación | `Plantas` + `lavandula`, pasar por `Aceites`, borrar consulta | 7 filas; filtro permanece |
| E-06 / E-06b | R-client «Consulta larga», «Consulta con caracteres especiales» | Valor límite | Teclear 250 caracteres; teclear `a&b=c#d/e?f+g` | `q` <= 200 caracteres, sin 400; reservados codificados |
| E-07 | R-explore «Debounce de la consulta» | Temporal | Teclear `mentha` con 6 teclas en ~50 ms | Una sola petición con la consulta final |
| E-08 | R-explore «Respuesta atrasada descartada» | Temporal | Retener 5 s `q=lav` y escribir `mentha` | La lista es la de `mentha` cuando llega la respuesta atrasada |
| E-09 | R-explore «Carga del catálogo» | Estado | Retener 5 s la primera página | «Cargando catálogo...» |
| E-10a/b | R-explore «Scroll infinito», «Error al cargar más» | Estado | Retener la página 2; fallar la página 2 y reintentar | Spinner en el pie; error reintentable en el pie conservando lo cargado; reintentar pide solo esa página |
| E-11 | R-client «Tiempo agotado» | Valor límite | Retener 16 s el detalle | Error legible con Reintentar sin esperar 16 s (límite 10 s) |
| E-12a/b | R-client «Planta sin nombre común», «Idioma del nombre común» | Equivalencia | Buscar `abies` y `artemisia annua` | `Abies spectabilis` solo científico; «Annual Mugwort (GRIN)» (`und`) tal cual |
| P-01 a P-06 | R-passport «Identidad», «General», «Usos» | Equivalencia | Abrir `/explore/{id}` de `lavandula-angustifolia`, `abies-spectabilis`, `chondrus-crispus`, `abies-sachalinensis`, `rosmarinus-officinalis`, `artemisia-annua` y recorrer pestañas | Datos de la API sin procedencia; `family` nula = «No disponible en fuente»; sin usos = vacío explícito; 10 y 59 usos con cita; Propiedades sin evaluación |
| P-05b | R-passport «Muchos usos» | Valor límite | Desplazar Usos de Romero hasta el final | Último uso (`Wen`) alcanzable |
| P-07 | R-passport «Identidad inexistente», R-client «Planta no encontrada» | Negativo | Abrir `/explore/no-existe` y un id con reservados | «Planta no encontrada», regreso seguro, id codificado |
| N-01a/b/c | R-explore «Abrir y volver de una ficha», «Volver desde Pasaporte» | Estado | Consulta `ros` + `Plantas`, desplazar, abrir, volver con chevron y con Atrás | Consulta, filtro y posición conservados |
| N-02 | R-explore estado al volver a Inicio | Estado | Inicio, entrar a Explorar de nuevo | Campo vacío, `Todas`, primera página |
| N-03 | R-explore «Volver desde Explorar a Inicio» | Navegación | Chevron y Atrás de Android | Inicio |
| N-04a/b/c | R-explore «Barra inferior» | Navegación | Tocar Favoritos, Historial, Perfil, corazón y formulaciones; `Inicio` | Deshabilitados sin efecto; `Inicio` lleva a Home |
| H-01 | R-bootstrap «Solicitudes limitadas», R-client «Sin otros hosts» | Observación | Muestrear `/proc/net/tcp*` del UID de la app durante un recorrido | Solo 10.0.2.2:8080 saliente |
| H-02 | R-bootstrap «Ausencia de solicitudes de negocio» | Negativo | Interactuar con Inicio y P06 | 0 peticiones |
| H-03 | R-client «Consumo de la API v1» | Contrato | Analizar todas las peticiones del proxy | Solo GET `/v1/plants` y `/v1/plants/{id}`, `limit=50`, `Accept: application/json`, sin credenciales |
| A-01 / A-02 | R-explore «Accesibilidad de Explorar», R-passport «Accesibilidad del pasaporte» | Accesibilidad | `font_scale` 2.0 en Explorar y Pasaporte; controles >= 48 dp; logcat sin overflow | Texto legible sin truncar, todo alcanzable |
| S-01 a S-06b | R-client «Sin conexión», «Reintento»; R-explore «Error local reintentable», «Error al cargar más»; R-passport «Error de red reintentable»; R-bootstrap «Funcionamiento sin conectividad» | Estado | `docker compose stop`: Explorar, Reintentar, Inicio y P06, `start` y Reintentar, pasaporte, error del pie | Error con Reintentar sin cierre; Inicio y P06 funcionan; Reintentar recupera |
| a200-S-* | Igual que S-* | Accesibilidad | Repetir S-* con `font_scale` 2.0 | Igual; Reintentar alcanzable con scroll vertical |
| F-01 a F-07 | R-client «Error del servidor», «Parámetro inválido», «JSON inválido», «Campo ausente», «Campos desconocidos», «Familia nula» | Fallos inyectados | Proxy devuelve 503, 400, JSON truncado, sin `items`, detalle 500, sin `scientificName`, y campos extra con `family` nula | Error legible con Reintentar sin cierre; los campos extra se ignoran |

## No planificado en este entorno

Dispositivo físico con `API_BASE_URL`, ejecución de un build release, TalkBack, prueba de caja negra del guard HTTP del smoke y caracteres de control en `q` (no se pueden teclear) se reportan como NO EJECUTADO en `app-backend-results.md`.

## Re-ejecución

Scripts en `scripts/` (`aq.py` es la biblioteca adb/uiautomator; `s_*.py` los escenarios; `logproxy.py` el proxy). Requisitos: Python 3, adb, Docker. Topología con proxy: `PORT=18080 docker compose up -d` y `python3 scripts/logproxy.py evidence/proxy-all.jsonl RULES.json`. Topología directa: `docker compose up -d`. Los resultados crudos de cada ejecución están en `results.jsonl`.
