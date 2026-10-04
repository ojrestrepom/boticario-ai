# Saneamiento de evidencia QA para publicación

Fecha: 2026-10-03. Antes de publicar se redactaron **24 segmentos de
autenticación** de URL del Dart VM Service en los logs de depuración locales de
QA. Se conservaron host, puerto, timestamps, eventos y demás resultados; cada
segmento sustituido aparece como `[REDACTED_VM_SERVICE_AUTH]`.

Archivos afectados:

- `evidence/android-manual-cold-pid-4245.log` (1)
- `evidence/android-manual-commands.log` (12)
- `evidence/android-manual-final-pid-11099.log` (1)
- `evidence/android-manual-flow100-pid-4245.log` (1)
- `evidence/android-manual-flow200-pid-6767.log` (1)
- `evidence/android-manual-home-actions-pid-4245.log` (1)
- `evidence/android-manual-home200-pid-6298.log` (1)
- `evidence/android-manual-offline-all-cold-pid-10539.log` (1)
- `evidence/android-manual-offline-five-valid-cold-pid-11099.log` (1)
- `evidence/android-manual-offline-five-valid-flow-pid-11099.log` (1)
- `evidence/android-manual-offline-valid-cold-pid-9511.log` (1)
- `evidence/android-manual-offline-valid-flow-pid-9511.log` (1)
- `evidence/android-manual-synthetic-query-pid-4245.log` (1)

Los hashes históricos de manifiestos y ejecuciones describen los bytes que
existían cuando se generaron; no se recalcularon ni se presentan como hashes de
los logs saneados. Para identificar esta versión publicable, los SHA-256 actuales
de los 13 archivos saneados son:

```text
26eb916edab8b3964d3da32e15c69991de907729ebf469301dd52acaa80c321b  evidence/android-manual-cold-pid-4245.log
d2ea41306cde18b6339abee52e89fa934ff4cc93717f3b0a1b55a4e6cf6f0aab  evidence/android-manual-commands.log
d64196ce623290fd760f6f48120a260d6c59f5588c2af1be2d6b0c0468b445ec  evidence/android-manual-final-pid-11099.log
d2d550b414a6b8a77399f0d0cce4f4777a1419dd9ff2e4c63634e6d8fa8f76b4  evidence/android-manual-flow100-pid-4245.log
a5f0f04a47bd9917e1c3a877a49bb45fd6880330a25b7516094acb591a224811  evidence/android-manual-flow200-pid-6767.log
a682b7221891c045514d4c15dc0502b60f5bac27eac0e51e48a69d59fc5e40ec  evidence/android-manual-home-actions-pid-4245.log
27fe23b207f70e0004260b680f1900ebb28018e57cfa8064a1ba92db13af4c86  evidence/android-manual-home200-pid-6298.log
05763294a95543dc0194bc3d333a594422aa32734cf452773587ba50249729b1  evidence/android-manual-offline-all-cold-pid-10539.log
ee0b770c5bbd0613859ca4386ea32b89aaf0e14f5569f86ffbf5682d45f184ba  evidence/android-manual-offline-five-valid-cold-pid-11099.log
c69d2b240856a1c4f59ecd3d30dac1889a98a5be3747d4be7abe63b904c60153  evidence/android-manual-offline-five-valid-flow-pid-11099.log
c708d2f9ea47aa23e00af9904d0c6bebc091adfd6497d8974c559564562438c4  evidence/android-manual-offline-valid-cold-pid-9511.log
3ab321dbf766d44b10f84f2d6f42cd7bdf0da5e11bb85c23e2ab4c339f4eabaa  evidence/android-manual-offline-valid-flow-pid-9511.log
2c4fc2e031b1b079affebd6370ce632a6030f240665eaec11089b49ce66cfafb  evidence/android-manual-synthetic-query-pid-4245.log
```

La evidencia original no se conserva en copias dentro del repositorio. Este
saneamiento elimina los patrones de autenticación Dart VM Service encontrados;
no constituye una garantía de que cualquier otro tipo de secreto esté ausente.

## Comprobación final del índice

En la revisión previa al commit, la comprobación staged predeterminada reportó
10.174 avisos limitados a `qa/evidence`: 10.170 por espacios finales y cuatro
por líneas vacías finales. Corresponden al formato de los logs históricos; se
preservaron sus bytes y saltos de línea fuera de las redacciones necesarias, sin
normalización masiva ni reglas persistentes de Git. No se reportaron avisos en
archivos de producto. El chequeo staged sin ese directorio y el chequeo de
evidencia con las dos excepciones de whitespace fueron ejecutados por el
orquestador, ambos con exit 0:

```sh
git diff --cached --check -- . ':!openspec/changes/build-local-plant-catalog/qa/evidence'
git -c core.whitespace=-blank-at-eol,-blank-at-eof diff --cached --check -- openspec/changes/build-local-plant-catalog/qa/evidence
```

Esto no afirma que `git diff --cached --check` sin exclusiones esté limpio.
Las verificaciones host registradas antes pasaron 137/137 pruebas, análisis y
formato; no se repitieron para esta actualización documental. El pin Flutter
3.47.6 y `app/pubspec.lock` conservaron sus hashes previos.
