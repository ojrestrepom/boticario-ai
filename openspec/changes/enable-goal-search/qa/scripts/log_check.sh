#!/bin/sh
# 6.2: comprueba que el log de la API (RUST_LOG=debug) no contiene el token en las rutas de objetivos.
# Entorno: QA_TOKEN, QA_BASE (servicio con RUST_LOG=debug), QA_CONTAINER (nombre del contenedor). Escribe evidence/api/API-23.txt (argumento 1).
set -u
out="$1"; : > "$out"
for p in "/v1/goals" "/v1/goals/mejorar-el-sueno/plants?limit=2" "/v1/goals/otros-objetivos/plants?subarea=digestion&limit=1" "/v1/goals/no-existe/plants"; do
  curl -s -o /dev/null -H "Authorization: Bearer $QA_TOKEN" "$QA_BASE$p"
  curl -s -o /dev/null -H "Authorization: Bearer ${QA_TOKEN}x" "$QA_BASE$p"
  curl -s -o /dev/null "$QA_BASE$p"
  curl -s -o /dev/null -X POST -H "Authorization: Bearer $QA_TOKEN" "$QA_BASE$p"
done
docker logs "$QA_CONTAINER" > /tmp/qa-log-check.$$ 2>&1
n=$(wc -l < /tmp/qa-log-check.$$)
if grep -q "$QA_TOKEN" /tmp/qa-log-check.$$; then echo "FALLA el token aparece en el log" >> "$out"; else echo "PASA el token no aparece en las $n lineas del log (RUST_LOG=debug, 16 peticiones a las dos rutas con token valido, incorrecto, sin token y POST)" >> "$out"; fi
if grep -qi "bearer" /tmp/qa-log-check.$$; then echo "OBS el log contiene la palabra Bearer" >> "$out"; else echo "PASA el log no contiene la palabra Bearer ni cabeceras Authorization" >> "$out"; fi
echo "--- ultimas 8 lineas del log (token sustituido)" >> "$out"
tail -8 /tmp/qa-log-check.$$ | sed "s/$QA_TOKEN/<token-app>/g" >> "$out"
rm -f /tmp/qa-log-check.$$
cat "$out" | cut -c1-300
