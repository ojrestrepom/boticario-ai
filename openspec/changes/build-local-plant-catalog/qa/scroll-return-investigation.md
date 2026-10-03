# Investigación de retorno de scroll 4.3

Fecha: 2026-10-03 UTC. Estado: **diagnóstico host confirmado; Android pendiente
de repetición en AVD. No aprobado todavía.**

## Hecho observado y límite de la evidencia anterior

La pasada Samsung de `android-smoke-4.3.md` falló con P04 `offset`
`108.79999999999995 -> 0.0` tras el chevron de P05, pero conservó ruta,
consulta `A` y filtro `Plantas`. Ese log no registró `viewInsets`, dimensión de
viewport, `maxScrollExtent` ni identidad de controladores. Por tanto no permite
atribuir retrospectivamente el cero a recreación/pérdida de estado ni confirmar
el IME como causa.

## Instrumentación y corrección del harness

`app/integration_test/catalog_smoke.dart` ahora emite, solo desde test, snapshots
antes del tap P04, tras navegar P05, antes de cada retorno y tras volver: inset,
viewport, extensión máxima, offset, e identidad de `ScrollController` y
`TextEditingController`. No cambia producto, rutas ni datos.

El smoke Android cierra el teclado únicamente antes de capturar el offset de la
sesión P04 (unfocus y `SystemChannels.textInput.invokeMethod<void>('TextInput.hide')`,
seguido de hasta 60 frames de 16 ms), exige
`viewInsets.bottom == 0`, hace visible Menta y mantiene la igualdad exacta de
offset en ambos retornos. No hay delay arbitrario ni tolerancia añadida. También
comprueba `handlePopRoute` desde la última P04 hasta Home.

### Compatibilidad del cierre nativo

Se revisó el SDK Flutter 3.47.6 local: `TestTextInput.hide()` solamente cambia
una bandera interna y exige `isRegistered`; a su vez
`IntegrationTestWidgetsFlutterBinding.registerTestTextInput` devuelve `false`.
Por ello el smoke no llama esa API de test ni registra un stub. Usa el canal
real `SystemChannels.textInput`; la documentación local del canal indica que
`TextInput.hide` puede invocarse en cualquier momento. El binding host acepta el
mismo mensaje por su canal fake, mientras que Android lo entrega al IME nativo.

## Regresión host con IME simulado

La segunda prueba de `catalog_smoke_contract_test.dart` usa app/router/datos
reales, un viewport de 360x1000 dp y un inset de IME de 400 dp. Demuestra el
caso que el log Samsung no podía distinguir:

| Snapshot | inset | viewport | max extent | offset |
|---|---:|---:|---:|---:|
| P04 antes de tap con IME | 400 | 600 | 220 | 220 |
| P05 tras cerrar IME | 0 | 932 | 0 | 0 |
| P04 tras chevron | 0 | 932 | 0 | 0 |

Las identidades de ambos controladores son iguales antes/después y consulta y
filtro siguen siendo los esperados. La prueba exige exactamente el clamp
`min(offsetAnterior, maxExtentNuevo)`, no omite la comprobación. La prueba normal
con viewport estable exige restauración exacta y pasó con `68 -> 68`.

Esto confirma que un cambio de viewport puede explicar legalmente el patrón
observado. **No confirma que fuera la causa en Samsung**, pues sus métricas no
se tomaron. La corrección deja una condición más fuerte y observable para la
repetición Android, sin declarar que el defecto de producto esté resuelto.

## Evidencia y siguiente ejecución Android autorizada

- Host: `qa/evidence/scroll-return-host.log`, comando desde `app/`:
  `PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test test/app/catalog_smoke_contract_test.dart`.
  Resultado: 2/2 pasan.
- Hashes de los archivos de diagnóstico: `qa/evidence/scroll-return-source-manifest.log`.
- No se ejecutó Android, ADB, build ni instalación en esta investigación; no se
  tocó el Samsung ni la configuración de SDK/AVD.

Cuando el orquestador anuncie un serial AVD autorizado, ejecutar el smoke Android
y conservar sus snapshots. Se podrá clasificar así:

1. Insets cero y viewport/extensión estables con offset distinto, o controlador
   distinto: defecto real de preservación; detenerse y solicitar autorización
   para cambiar producto.
2. El cierre de teclado no llega a inset cero: fallo explícito de estabilización
   del harness/plataforma, no aprobación; investigar sin ocultarlo.
3. Insets cero, misma extensión y offset exacto en ambos retornos: el AVD
   demuestra el contrato con viewport estable. No confirma retrospectivamente
   la causa del Samsung; aún requiere revisión del resto del smoke Android.

La pasada Samsung original permanece sin sobrescribir y sigue marcada FALLÓ.
