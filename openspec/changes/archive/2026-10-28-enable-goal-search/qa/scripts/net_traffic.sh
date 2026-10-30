#!/bin/sh
# 6.4/UI-16: mide los bytes recibidos por el emulador (suma de wlan0 y eth0 de /proc/net/dev) mientras la app carga la lista de un objetivo,
# para comprobar por tamano que las miniaturas son de 500 px y no los originales. Uso: net_traffic.sh <objetivo> <n de miniaturas esperadas>
ADB=~/Library/Android/sdk/platform-tools/adb; DEV=emulator-5556
rx() { $ADB -s $DEV shell cat /proc/net/dev | awk "/wlan0|eth0/ {s += \$2} END {print s}"; }
$ADB -s $DEV shell am force-stop com.example.boticario_ai; sleep 2
idle0=$(rx); sleep 10; idle1=$(rx); echo "reposo: $((idle1 - idle0)) bytes en 10 s"
b0=$(rx)
sh "$(dirname "$0")/run_ui_lists.sh" "$1" > /tmp/qa-net-run.$$ 2>&1
b1=$(rx)
echo "lista $1: $((b1 - b0)) bytes recibidos en total, para $2 miniaturas esperadas; media $(( (b1 - b0) / $2 )) bytes por miniatura (incluye JSON y reposo)"
grep -E '"api_total"|foto con credito' /tmp/qa-net-run.$$
rm -f /tmp/qa-net-run.$$
