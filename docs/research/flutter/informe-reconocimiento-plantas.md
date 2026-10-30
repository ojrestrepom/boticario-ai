# Informe de preparación del módulo de reconocimiento de plantas

Fecha: 19 de octubre de 2026. Alcance: revisión del código Flutter, documentación vigente, artículo adjunto de Pl@ntNet-300K y fuentes técnicas oficiales. Este informe propone trabajo futuro; no implementa el módulo ni modifica las specs vigentes.

## 1. Dictamen

Es viable añadir reconocimiento de plantas sobre la estructura actual sin rehacer la aplicación. Ya existen navegación con GoRouter, inyección y estado con Riverpod, catálogo local, pasaporte y pruebas. Falta toda la cadena de reconocimiento: adquisición de imagen, preprocesamiento, ejecución del modelo, interpretación de clases, gestión de incertidumbre y enlace taxonómico al catálogo.

La primera entrega recomendada es un experimento de identificación por fotografía, ejecutado localmente en Android, con varios candidatos y acceso al pasaporte únicamente cuando exista una correspondencia revisada. La recomendación de ejecución local es una propuesta coherente con el catálogo sin conexión actual, no una decisión previamente aprobada. No se necesita inicialmente backend, login ni entrenamiento desde cero.

Los dos obstáculos principales son comprobar si las especies de interés están entre las 1.081 clases y convertir un checkpoint de investigación a un artefacto móvil verificable. El tamaño del `.tar` no permite decidir cuál modelo es mejor para el producto.

## 2. Qué existe y qué falta

| Componente | Evidencia del proyecto | Trabajo necesario |
|---|---|---|
| Entrada desde Inicio | `app/lib/features/home/presentation/home_page.dart`: la tarjeta de cámara solo llama a `_emitHomeAction` | Añadir callback `onIdentifyPlant` y conectarlo con una ruta nueva |
| Navegación | `app/lib/app/router.dart`: `/`, `/goals`, `/explore`, `/explore/:plantId` | Proponer `/identify`, con captura y resultado como estados de una pantalla, y definir sus retornos |
| Organización | `app/lib/features/`, Riverpod y separación de catálogo en dominio/datos | Crear una feature independiente de reconocimiento |
| Dependencias | `app/pubspec.yaml`: Flutter, Riverpod y GoRouter; asset del catálogo | Añadir adquisición de imagen e integración del runtime elegido después de la prueba de compatibilidad |
| Catálogo | `app/assets/data/plant_catalog.json`: cinco plantas con IDs USDA | Incorporar tabla de correspondencia taxonómica separada; comprobar cobertura real |
| Pasaporte | `PlantPassportRoutePage` convierte un ID de ruta a entero y consulta el catálogo local | Abrirlo con `usdaPlantId`, nunca con el índice de salida del modelo |
| Android | Manifest principal sin declaración explícita de cámara; SDKs delegados a Flutter | Ajustar configuración y permisos según captura externa o preview integrada y mínimos del runtime |
| Calidad | `app/test/`, `app/integration_test/` y CI de Flutter | Añadir pruebas del módulo, paridad de inferencia y verificación en dispositivos reales |
| Modelos | No se encontraron `.tar`, `.onnx` o `.tflite` en la carpeta revisada | Obtener artefactos y etiquetas, verificar integridad, exportar y versionar |

El catálogo contiene `Lavandula angustifolia` (544), `Eucalyptus globulus` (401), `Rosmarinus officinalis` (873), `Matricaria recutita` (605) y `Mentha x piperita subsp. nothosubsp. piperita` (619). Estos nombres son literales de USDA y sus equivalencias con otras nomenclaturas no están certificadas por el proyecto. Véase [procedencia del catálogo](../../data/usda-catalog.md).

## 3. Qué aportan el artículo y los pesos

El PDF adjunto describe un benchmark de clasificación de especies, no un módulo Flutter listo para instalar. En sus secciones 3 y 4 documenta 306.146 fotografías de 1.081 especies y 303 géneros, con particiones de 243.916 imágenes de entrenamiento, 31.118 de validación y 31.112 de prueba. Se seleccionó una fracción de los géneros de la base original; no representa todas las especies de Pl@ntNet ni garantiza cobertura de plantas medicinales o flora colombiana.

El 80 % de las especies concentra solo el 11 % de las imágenes. La sección 4.3 y la tabla 1 muestran la importancia de evaluar por especie: para ResNet50, el promedio de exactitud de las clases con 0–10 imágenes de entrenamiento es 0,09 y el de clases con más de 2.000 es 0,93. Estos datos pertenecen al experimento del artículo; no son predicciones de rendimiento de Boticario AI. La exactitud macro top-1 de los modelos estudiados no supera el 40 % según el texto del artículo.

Consecuencias para producto: mostrar varios candidatos, admitir resultados no concluyentes y medir rendimiento por especie. Una imagen de una parte de la planta puede carecer de rasgos suficientes para diferenciar especies. El modelo tampoco identifica propiedades medicinales, seguridad de consumo, dosis, aceites ni enfermedades por el hecho de reconocer una especie.

El repositorio oficial distingue los índices de clase de los identificadores botánicos mediante archivos de metadatos. Hay que preservar ese orden al interpretar cualquier salida. Fuente: [repositorio de Pl@ntNet-300K](https://github.com/plantnet/PlantNet-300K).

Según el código oficial, los checkpoints guardan parámetros del modelo, optimizador y época; la carga usa `d['model']`. La extensión `.tar` no implica un paquete utilizable en Dart. Debe reconstruirse la arquitectura con 1.081 salidas y cargar sus parámetros. Para inferencia no se necesita el optimizador. Esto también explica por qué el tamaño descargado puede diferir del artefacto final. Fuente: [`utils.py`](https://raw.githubusercontent.com/plantnet/PlantNet-300K/main/utils.py).

## 4. Modelos que conviene evaluar primero

Los tamaños de esta tabla proceden de la lista suministrada por el usuario; no son tamaños medidos después de exportación ni benchmarks de Android.

| Candidato | Tamaño `.tar` informado | Papel propuesto |
|---|---:|---|
| MobileNetV3 Small | 21,2 MB | Primer candidato para inferencia local por su arquitectura orientada a móviles |
| MobileNetV2 | 29,2 MB | Alternativa inicial para comparar calidad, conversión y velocidad |
| EfficientNet B0 | 43,5 MB | Tercer candidato si las primeras alternativas no alcanzan calidad suficiente |
| ResNet18 | 93,9 MB | Referencia técnica de carga y comparación; no asumir que tendrá la mayor exactitud |
| MobileNetV3 Large | 44,9 MB | Ampliación de la comparación si Small resulta insuficiente |

ShuffleNet y SqueezeNet pueden entrar si el presupuesto de tamaño es muy restrictivo. No priorizaría VGG11, ViT Base, Wide ResNet ni las variantes grandes de Inception, DenseNet o ResNet para la primera prueba móvil: aumentan el trabajo y los recursos a evaluar sin una ventaja demostrada para las especies objetivo. No es necesario descargar los 27 archivos.

La selección debe comparar la misma colección de imágenes, preprocesamiento y dispositivo: top-1, top-3/top-5, promedio por especie, falsos resultados aceptados, tamaño final, memoria máxima, tiempo de carga y latencias p50/p95 incluyendo procesamiento de imagen. No se declara un ganador antes de medir.

## 5. Dónde ejecutar la inferencia

| Estrategia | Ventajas | Costos y trabajo adicional |
|---|---|---|
| Local Android, recomendada para el experimento | Identificación sin red después de instalar el modelo; fotos procesadas en el teléfono | Exportación, integración nativa, tamaño instalado y desempeño variable por dispositivo |
| Backend Python con PyTorch | Facilita ejecutar el checkpoint original y actualizar el modelo | API, alojamiento, disponibilidad, transferencia de fotos, límites de uso y gestión de retención |
| API externa de identificación | Reduce el mantenimiento propio de modelos | Evaluar cobertura, condiciones, costo y dependencia del proveedor; no equivale a usar estos checkpoints |

Para la prueba local hay dos rutas razonables: PyTorch → LiteRT (`.tflite`) o PyTorch → ONNX → ONNX Runtime para Android. La primera dispone de conversión oficial desde PyTorch; la segunda permite usar un runtime Android documentado. Ambas requieren comprobar operadores y paridad. La existencia de soporte Android no implica soporte Dart directo: verificar un binding Flutter mantenido o implementar un puente Kotlin con platform channels. Fuentes: [conversión PyTorch a LiteRT](https://developers.google.com/edge/litert/conversion/pytorch/overview) y [despliegue móvil de ONNX Runtime](https://onnxruntime.ai/docs/tutorials/mobile/).

Usar un solo runtime en la app final. Empezar con precisión flotante y cuantizar únicamente después de contar con una referencia correcta. INT8 necesita imágenes representativas y evaluación de pérdida de calidad, en particular en especies poco representadas. El resultado de exportación, las dependencias nativas y el tamaño de la app se deben medir, no deducir del peso original.

## 6. Preparación del artefacto de inferencia

1. Obtener un checkpoint de la fuente oficial y los archivos `class_idx_to_species_id.json` y `plantnet300K_species_id_2_name.json`. Registrar URL, hash SHA-256 y fecha. Usar `plantnet300K_metadata.json` para preparar evaluación, procedencia de imágenes y licencias.
2. Congelar versiones de Python, PyTorch, torchvision y, cuando aplique, timm y herramientas de conversión. El código de 2021 puede necesitar adaptación a APIs actuales.
3. Reconstruir la arquitectura correcta, verificar 1.081 salidas y cargar el estado sin faltantes. Ejecutar en modo evaluación y sin gradientes; no cargar el optimizador para inferencia.
4. Reproducir el procesamiento de referencia antes de optimizarlo. El artículo describe resize a 256 y recorte central 224 × 224 en prueba. El código distingue normalización ImageNet y otra para entrenamiento sin preentrenamiento; comprobar cuál corresponde al peso descargado. Validar también RGB, orientación, escala y disposición de tensores.
5. Exportar y comparar resultados frente a PyTorch sobre imágenes fijas. Documentar forma, tipo y disposición de entrada/salida, tolerancias numéricas y coincidencia de candidatos.
6. Cuantizar si es necesario y repetir la evaluación; no aceptar solo que el conversor termine sin errores.
7. Distribuir el artefacto con manifest: versión, arquitectura, número de clases, hash del modelo y etiquetas, procesamiento, runtime, métricas y procedencia/licencias. Empaquetarlo como asset es la opción inicial más sencilla; una descarga posterior exige integridad, estados de disponibilidad y política de actualización.

No aplicar softmax dos veces ni interpretar logits como porcentajes. Una puntuación softmax alta no certifica una identificación correcta ni detecta por sí sola especies desconocidas.

## 7. Correspondencia con los pasaportes: requisito prioritario

La resolución debe seguir esta cadena:

```text
índice de clase → speciesId de Pl@ntNet → nombre científico de origen
                                      → correspondencia curada → usdaPlantId opcional
```

Crear, por ejemplo, `app/assets/data/plantnet_catalog_mapping.json`, independiente del asset USDA. Cada entrada debe conservar identificador Pl@ntNet, nombre fuente, ID USDA opcional, tipo de correspondencia, fuente taxonómica y estado de revisión. Un nombre parecido o común no basta para enlazar un pasaporte. Los casos del romero, manzanilla y menta requieren revisar sinonimia y rango taxonómico, conservando el texto original de USDA.

Primero producir una matriz de cobertura de las cinco plantas: presente, ausente o pendiente de resolver. No se ha podido certificar esa cobertura porque los metadatos del enlace Seafile no fueron accesibles con el lector web. Si una especie no pertenece a las 1.081 clases, ningún umbral ni cambio de etiquetas permitirá reconocerla con ese clasificador; habría que ampliar entrenamiento o usar otro modelo/proveedor.

Mostrar “Especie candidata sin ficha disponible” para una clase reconocida sin correspondencia local. No inventar una ficha, reemplazarla por una planta cercana ni restringir la salida a las cinco fichas para forzar un resultado. Diferenciar ausencia de pasaporte, baja confianza y especie fuera de cobertura: esta última no puede determinarse de forma infalible solo con el softmax.

## 8. Organización propuesta del módulo

```text
app/lib/features/recognition/
  domain/
    recognition_candidate.dart
    recognition_result.dart
    plant_recognizer.dart
  data/
    local_plant_recognizer.dart
    recognition_model_manifest.dart
    plantnet_label_data_source.dart
    plant_catalog_matcher.dart
    plant_image_source.dart
  presentation/
    recognition_controller.dart
    identify_plant_page.dart
app/assets/models/                 artefacto exportado y manifest
app/assets/data/                   etiquetas y correspondencias curadas
tools/plant_recognition/           carga, exportación, paridad y evaluación
```

`PlantRecognizer` debe exponer una operación de identificación independiente de widgets y devolver candidatos con índice, especie y puntuación, además de versión del modelo y estado del resultado. `PlantCatalogMatcher` resuelve IDs USDA opcionales. Riverpod proporciona las implementaciones y el controlador; las pruebas sustituyen adquisición e inferencia por dobles.

Mantener inferencia y procesamiento costoso fuera del hilo de interfaz, con el mecanismo apropiado al binding elegido. Definir carga única del runtime, liberación, exclusión de inferencias simultáneas y descarte de respuestas cuando la pantalla ya se cerró o se capturó otra imagen.

## 9. Flujo y experiencia necesarios

Para un primer incremento, usar fotografía única con cámara externa y selección de galería permite validar el modelo con menos complejidad visual. `image_picker` cubre ambas fuentes. Si se requiere el encuadre integrado de P09, `camera` ofrece preview y captura, pero exige gestionar permisos y ciclo de vida. Elegir una estrategia explícita antes de añadir paquetes. Fuentes: [`image_picker`](https://pub.dev/packages/image_picker) y [`camera`](https://pub.dev/packages/camera?trk=public_profile_project-title).

Estados mínimos: preparando modelo, listo para capturar, adquiriendo imagen, analizando, candidatos, resultado no concluyente, error recuperable y modelo no disponible. La cancelación voluntaria debe volver al estado anterior sin tratarse como error. Contemplar permiso denegado, cámara ausente, imagen inválida, rotación, cierre del proceso durante captura y retorno de segundo plano.

Presentar hasta tres candidatos inicialmente y permitir otra fotografía; evaluar internamente también top-5. “Ver pasaporte” solo aparece habilitado cuando el candidato seleccionado tiene correspondencia curada. Abrir `/explore/<usdaPlantId>` mediante navegación apilada y verificar que Atrás regresa al resultado; Inicio debe volver a `/`.

El mockup P09 incluye “Confianza: 92 %”; su documentación aclara que es ilustrativo. Conviene usar “Resultado probable” y, si se muestran números, explicar su naturaleza y validar calibración. Definir el umbral de abstención con validación y datos de uso, incluyendo imágenes sin plantas y especies no cubiertas. Un umbral de puntuación es una heurística de rechazo, no una garantía de detección de desconocidos.

Procesar fotos de forma temporal, evitar su inclusión en logs y establecer cuándo se borran. Si más adelante se envían a un servidor, definir comunicación al usuario, eliminación de metadatos innecesarios, límites de archivo, retención y tratamiento de errores. Historial y favoritos pueden quedar para otro incremento porque todavía no existe persistencia de usuario.

## 10. Documentación y contratos que deberán evolucionar

La spec `home-screen` exige actualmente que la tarjeta de cámara sea inerte y prohíbe cámara y permisos en ese flujo. `flutter-app-bootstrap` también limita rutas. Son contratos de la versión actual: al implementar reconocimiento habrá que actualizarlos mediante un nuevo cambio de OpenSpec y ajustar los tests de inercia, en lugar de considerar que el botón ya está preparado funcionalmente.

El cambio debería incluir propuesta, diseño, tareas y spec nueva `plant-recognition`, además de deltas de `home-screen` y `flutter-app-bootstrap`. Revisar deltas de `plant-passport` cuando se concrete el retorno al reconocimiento y de `plant-catalog` si cambia su contrato. Actualizar README, documentación de procesamiento y modelo, cobertura taxonómica y plan de QA. No reescribir cambios archivados.

La licencia CC0 del catálogo USDA no cubre automáticamente imágenes ni pesos de Pl@ntNet. El código oficial declara BSD-2-Clause; el artículo indica licencias por imagen en metadatos. Documentar por separado términos aplicables al código, checkpoint, dataset y fotos reutilizadas antes de distribuirlos. La accesibilidad de una descarga no demuestra por sí sola permiso de redistribución de pesos.

## 11. Secuencia de implementación y criterios de salida

| Fase | Entregable | Criterio para avanzar |
|---|---|---|
| 0. Cobertura y requisitos | Matriz de las cinco plantas, términos de uso, Android mínimo objetivo y presupuestos de tamaño/latencia | Saber qué especies pueden reconocerse y cómo se mostrará la ausencia de cobertura o ficha |
| 1. Prueba de modelo | MobileNetV3 Small y ResNet18 cargados; comparación con MobileNetV2 si hace falta; un candidato exportado | Inferencia reproducible, etiquetas correctas y paridad documentada |
| 2. Contratos y UI | Cambio OpenSpec, ruta, controlador y pantalla con reconocedor simulado | Flujo completo de captura simulada, candidatos, abstención y retorno al pasaporte |
| 3. Android real | Adquisición de imagen e inferencia local conectadas | Identificación sin red, orientación correcta y UI fluida en teléfono objetivo |
| 4. Evaluación | Reporte por especie y dispositivo; umbrales y, si procede, cuantización | Cumplir objetivos acordados de calidad y recursos sin ocultar errores de especies raras |
| 5. Preparación de entrega | Modelo, hashes, licencias, documentación y smoke actualizado | Instalación reproducible, manejo de fallos y regresiones del catálogo cubiertas |

No es responsable estimar fechas cerradas antes de resolver cobertura y exportación. El esfuerzo principal no será dibujar P09, sino preparar y validar el artefacto, enlazar taxonomía y probar en dispositivos.

Pruebas requeridas: orden y unicidad de las 1.081 etiquetas; mapeos curados; procesamiento de imágenes verticales, horizontales y con orientación; paridad de PyTorch y runtime; candidatos sin ficha; resultado no concluyente; cancelación y permisos; navegación y descarte de resultados tardíos. Mantener las pruebas existentes de catálogo y pasaporte. Evaluar fotos externas al benchmark, con referencia botánica revisada, distintas partes de plantas y negativos. Ajustar umbrales con validación, conservando un test independiente; si se entrena, evitar que fotos del mismo espécimen u observación se filtren entre particiones.

La CI actual cubre formato, análisis y tests Flutter, pero no crea un emulador ni valida inferencia nativa. Añadir un proceso reproducible de exportación/paridad y un smoke Android del reconocimiento. El rendimiento y los permisos necesitan validación en dispositivo, aunque los widgets pasen.

## 12. Alcance y límites de esta revisión

Se revisaron código y configuración de la app, dependencias, datos locales, tests, CI, README, mockups, plan Flutter, specs vigentes y el texto del PDF adjunto, con atención a sus secciones 3, 4 y 7. Se distinguieron la descripción del artículo, el estado real del código y las propuestas de este informe.

El lector web no pudo acceder al listado Seafile de pesos ni a la carpeta de metadatos enlazada por el repositorio oficial. Por ello no se descargaron ni ejecutaron checkpoints, no se verificó la cobertura exacta de las cinco plantas y no se midieron conversión, precisión o desempeño móvil. La carpeta entregada tampoco contiene metadatos Git para obtener un diff con `git status`.

Se intentaron ejecutar `flutter analyze` y `flutter test test/` desde `app/`; ambos permanecieron sin producir salida y se interrumpieron. Por tanto, esta revisión no certifica que el análisis ni las suites pasen en el entorno actual. Se verificó la existencia de los destinos de los enlaces locales del informe. No se modificó el código funcional.

## 13. Fuentes

- Artículo adjunto: Garcin et al., *Pl@ntNet-300K: a plant image dataset with high label ambiguity and a long-tailed distribution*, NeurIPS Datasets and Benchmarks 2021; [versión publicada](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/file/7e7757b1e12abcb736ab9a754ffb617a-Paper-round2.pdf).
- [Código y documentación oficiales](https://github.com/plantnet/PlantNet-300K), [carga y procesamiento](https://raw.githubusercontent.com/plantnet/PlantNet-300K/main/utils.py) y [dataset versión 1.1](https://zenodo.org/records/5645731). Fijar la versión usada: Zenodo señala que existe una versión posterior; no se asume que corresponda a los pesos de 2021.
- [Pesos indicados por el usuario](https://seafile.plantnet.org/d/01ab6658dad6447c95ae/?p=%2F&mode=list) y [metadatos enlazados por los autores](https://seafile.plantnet.org/d/bed81bc15e8944969cf6/), accesibilidad pendiente.
- Fuentes del proyecto: [README](../../../README.md), [mockup P09](../../mockups/pantallas.md#p09-identificar-con-cámara), [guía USDA](../../data/usda-catalog.md) y specs vigentes en `openspec/specs/`.
