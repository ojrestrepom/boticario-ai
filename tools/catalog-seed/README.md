# Herramientas de la semilla del catálogo

Estas herramientas, en Python, preparan offline la semilla del catálogo de plantas: descargan y verifican las fuentes de datos y, en los grupos de tareas siguientes, resuelven nombres, consolidan y validan los paquetes. Son solo para el desarrollador: no van en la imagen de Docker (`tools/` está excluido de `.dockerignore`) y el backend en ejecución no las usa. Véase `openspec/changes/consolidate-catalog-seed/`.

## Entorno

Se necesita Python 3.9 o superior y, por ahora, solo la biblioteca estándar. No hace falta instalar nada. Si más adelante se añaden dependencias, se declaran en `tools/catalog-seed/requirements.txt` y se instalan en un entorno virtual local, ignorado por Git:

```sh
python3 -m venv tools/catalog-seed/.venv
tools/catalog-seed/.venv/bin/pip install -r tools/catalog-seed/requirements.txt
```

## Estructura

- `cli.py`: punto de entrada de línea de comandos.
- `catalog_seed/`: paquete importable (`sources.py` valida `sources.json` y las listas de fuentes; `download.py` descarga y verifica; `cli.py` define los comandos).
- `sources.json`: registro de fuentes.
- `tests/`: pruebas con `unittest`, sin red.

## Comandos

Se ejecutan desde la raíz del repositorio:

```sh
python3 -I tools/catalog-seed/cli.py download
python3 -I tools/catalog-seed/cli.py download --source usda
python3 -I tools/catalog-seed/cli.py download --offline
python3 -I tools/catalog-seed/cli.py download --force
```

- `download` descarga cada fuente con `enabled: true` a `data/.cache/<id>/<filename>`, comprueba tamaño y checksum y la deja en la caché solo si coinciden. Una fuente con `enabled: false` no se descarga ni se verifica.
- Si el archivo ya está en la caché e íntegro, no vuelve a descargarlo ni usa la red. Si está alterado, falla indicando la fuente; `--force` lo descarga de nuevo.
- `--offline` solo verifica la caché y nunca abre la red. Si el insumo falta o está alterado, termina con error e indica el paso de descarga necesario.
- `--source <id>` limita el comando a una fuente y se puede repetir.
- `--sources <ruta>` y `--cache-dir <ruta>` cambian el archivo de fuentes y la caché (útil en pruebas).

El código de los pasos posteriores debe obtener los insumos con `catalog_seed.download.require_verified`, que nunca usa datos sin verificar.

## Formato de `sources.json`

Un objeto con la lista `sources`. Cada fuente tiene estos campos, todos obligatorios:

- `id`: identificador de la fuente; debe estar en la lista de admitidas.
- `version`: versión o snapshot fijo (con su fecha cuando la fuente cambia con el tiempo).
- `url`: dirección del insumo.
- `filename`: nombre del archivo en la caché, sin rutas.
- `license`: licencia de los datos.
- `attribution`: atribución exigida por la licencia.
- `size`: tamaño esperado en bytes.
- `checksum`: objeto con `algorithm` (`md5` o `sha256`) y `value` en hexadecimal.
- `enabled`: `true` o `false`; una fuente desactivada no se descarga y permite retirarla por configuración.

Ejemplo (la fuente USDA, la única declarada hasta ahora):

```json
{
  "id": "usda",
  "version": "Ag Data Commons 24660351, v1 (Duke-Source-CSV.zip, file ID 43363335)",
  "url": "https://ndownloader.figshare.com/files/43363335",
  "filename": "Duke-Source-CSV.zip",
  "license": "CC0",
  "attribution": "Duke, James A. (2016). Dr. Duke's Phytochemical and Ethnobotanical Databases. Ag Data Commons. https://doi.org/10.15482/USDA.ADC/1239279",
  "size": 6033990,
  "checksum": {"algorithm": "md5", "value": "45ae44a0544586b8ac22a232beaac344"},
  "enabled": true
}
```

## Fuentes admitidas y descartadas

El verificador (`catalog_seed/sources.py`) rechaza cualquier fuente que no esté en la lista de admitidas.

- Admitidas: `usda`, `wcvp`, `wfo`, `ema_json`, `ema_pdf`, `tppt`, `efsa`, `wikidata`, `wikipedia_es` y `commons`.
- Descartadas (mensaje específico): AromaDb, EssOilDB, sCentInDB, FDA PPDB, Comisión E, OMS/WHO, NHPID, iNaturalist y DrugBank.

## Pruebas

Desde la raíz del repositorio, sin red:

```sh
python3 -I -m unittest discover -s tools/catalog-seed/tests -v
```

Con `-I` Python no añade directorios a `sys.path`, así que `tests/support.py` calcula la ruta de `tools/catalog-seed/` y la agrega antes de importar el paquete; cada archivo de pruebas importa `support` primero.

## Archivos locales

`data/.cache/` (descargas verificadas) y `data/work/` (productos intermedios) están ignorados por Git y excluidos del contexto de Docker, igual que `tools/`. El entorno virtual `tools/catalog-seed/.venv` también está ignorado.
