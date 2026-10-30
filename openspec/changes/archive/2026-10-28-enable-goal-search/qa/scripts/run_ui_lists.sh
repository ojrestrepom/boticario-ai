#!/bin/sh
# 6.3 y 6.4: reinicia la app (cache de imagenes limpia) y recorre cada lista indicada con ui_goal_lists.py.
# Uso: run_ui_lists.sh "<objetivo>[:<subarea>] ..."    Entorno: QA_TOKEN, QA_PYLIB, QA_DWELL (segundos entre pasos, por defecto 1.5)
ADB=~/Library/Android/sdk/platform-tools/adb; DEV=emulator-5556
for l in $1; do
  g=${l%%:*}; s=""; [ "$g" != "$l" ] && s=${l#*:}
  $ADB -s $DEV shell am force-stop com.example.boticario_ai; sleep 1
  $ADB -s $DEV shell am start -n com.example.boticario_ai/.MainActivity >/dev/null; sleep 5
  python3 "$(dirname "$0")/ui_goal_lists.py" $g $s
done
