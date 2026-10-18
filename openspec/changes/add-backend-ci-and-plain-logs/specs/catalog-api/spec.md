## ADDED Requirements

### Requirement: Logs sin secuencias ANSI fuera de una terminal
Los eventos de log de la API (los de `tracing`), que se escriben por la salida estándar, SHALL NOT incluir secuencias de escape ANSI cuando esa salida no es una terminal, de modo que los colectores de logs (como Cloud Logging) y los archivos reciban texto plano. SHALL NOT incluirlas tampoco cuando la variable de entorno `NO_COLOR` tiene un valor no vacío, aunque la salida sea una terminal. Con la salida en una terminal y `NO_COLOR` sin definir o vacía, SHALL conservar los colores. El nivel de logs SHALL seguir controlándose con `RUST_LOG`, con `info` por defecto.

#### Scenario: Salida redirigida
- **WHEN** la API se ejecuta con la salida estándar redirigida a una tubería o a un archivo y escribe la línea de arranque
- **THEN** la salida no contiene ningún carácter de escape `ESC` (0x1B) y la línea incluye el nivel y el mensaje «escuchando»

#### Scenario: Contenedor en Cloud Run
- **WHEN** el servicio desplegado atiende una petición y se leen sus logs en Cloud Logging
- **THEN** las entradas de la API no contienen secuencias ANSI

#### Scenario: NO_COLOR en una terminal
- **WHEN** la salida estándar es una terminal y `NO_COLOR` vale `1`
- **THEN** los logs no contienen secuencias ANSI

#### Scenario: Terminal con colores
- **WHEN** la salida estándar es una terminal y `NO_COLOR` no está definida o está vacía
- **THEN** los logs conservan los colores por nivel

#### Scenario: Nivel por entorno
- **WHEN** la API se ejecuta con `RUST_LOG=warn` y la salida redirigida
- **THEN** la línea INFO de arranque no aparece y sigue sin haber secuencias ANSI
