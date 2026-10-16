# Spec Delta

## MODIFIED Requirements

### Requirement: Flujo de desarrollo reproducible y documentado
El repositorio SHALL contener la app Android en `app/`, abrible en Android Studio, con prerequisitos, versión exacta de SDK, dependencias fijadas y comandos documentados; la configuración local del SDK SHALL permanecer sin versionar. La documentación SHALL cubrir cómo arrancar el backend con Docker y la dirección con la que lo alcanzan el emulador y un dispositivo físico, y SHALL cubrir cómo compilar el build `release` y ejecutar el smoke contra el backend desplegado con `--dart-define=API_BASE_URL=https://…`.

#### Scenario: Apertura en Android Studio
- **WHEN** un desarrollador abre la raíz `app/` en Android Studio con los prerequisitos documentados
- **THEN** el proyecto se reconoce como proyecto Flutter con target Android

#### Scenario: SDK y dependencias fijadas
- **WHEN** se revisa el repositorio
- **THEN** la versión exacta de SDK usada en local y en CI y las dependencias están fijadas

#### Scenario: Configuración local sin versionar
- **WHEN** se revisa el control de versiones
- **THEN** la configuración local del SDK no está versionada

#### Scenario: Setup y comandos documentados
- **WHEN** un desarrollador consulta la documentación
- **THEN** encuentra los pasos de setup, la selección de dispositivo Android y los comandos de prueba

#### Scenario: SDK ausente
- **WHEN** un desarrollador no dispone del SDK requerido y consulta el quickstart
- **THEN** encuentra la preparación manual del SDK y la revisión y aceptación interactiva de licencias

#### Scenario: Backend y dirección documentados
- **WHEN** un desarrollador consulta el quick start
- **THEN** encuentra que debe arrancar el backend con Docker antes de ejecutar la app, que el emulador lo alcanza en `http://10.0.2.2:8080` y que un dispositivo físico necesita `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080`

#### Scenario: Release contra el backend desplegado
- **WHEN** un desarrollador consulta la documentación para compilar el build `release` o ejecutar el smoke contra el backend desplegado
- **THEN** encuentra los comandos con `--dart-define=API_BASE_URL=https://<url-de-cloud-run>`, que el build `release` exige HTTPS y que, sin esa definición, la dirección por defecto sigue siendo la del emulador
