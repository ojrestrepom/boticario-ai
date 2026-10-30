# Diseño

## Arquitectura

PlantRecognitionPage es un StatelessWidget en features/plant_recognition/presentation. Recibe onBack y onHome; el router gestionado por Riverpod proporciona pop y go('/'). HomePage recibe onIdentifyPlant y conserva la emisión única del mensaje bajo kDebugMode antes de ejecutar el callback en cualquier modo. /identify es hija de / para permitir retorno seguro también desde acceso directo.

## Presentación

Se conservan Material 3, la paleta provisional verde, bordes redondeados, márgenes de 16 dp y la barra inferior con Inicio seleccionado. La pantalla contiene texto vivo, iconografía local, un espacio reservado y dos botones realmente deshabilitados. El contenido tiene scroll, SafeArea y una barra adaptable a texto al 200%. La barra pertenece al módulo para evitar dependencia de objetivos y refactorizaciones ajenas.

## Límites

No se adquieren imágenes, solicitan permisos, simulan resultados, persisten datos ni realizan peticiones. No se añaden paquetes ni providers sin estado que gestionar.

## Verificación

Pruebas de widget con el tema real y router real cubren entrada, log, acceso directo y los tres retornos. El cliente falso verifica ausencia de HTTP. Se comprueban estados deshabilitados, inercia de pestañas y layout a 100% y 200% en 360x640 con insets. El smoke compartido incorpora el recorrido local antes de los recorridos existentes.
