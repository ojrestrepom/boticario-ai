# Spec Delta

## MODIFIED Requirements

### Requirement: Permisos y transporte en Android
El manifest principal de Android SHALL declarar el permiso `INTERNET`. Los manifests de `debug` y `profile` SHALL habilitar el tráfico HTTP en claro para la pila de red de Android. El manifest principal y los recursos de `release` SHALL NOT habilitarlo. La documentación SHALL indicar que el cliente Dart (`dart:io`) no está sujeto a esa restricción, por lo que el build `release` debe recibir una `API_BASE_URL` HTTPS.

#### Scenario: Permiso en todos los builds
- **WHEN** se revisa el manifest principal
- **THEN** declara `INTERNET`, de modo que un build `release` tiene acceso a la red

#### Scenario: HTTP en claro en desarrollo
- **WHEN** se revisan los manifests de `debug` y `profile`
- **THEN** declaran `android:usesCleartextTraffic="true"`, de modo que la app llega al backend local por HTTP

#### Scenario: Release sin HTTP en claro
- **WHEN** se revisan el manifest principal y los recursos de `release`
- **THEN** no habilitan HTTP en claro ni definen una configuración de seguridad de red que lo permita

#### Scenario: Release con dirección HTTP
- **WHEN** se compila un build `release` con `API_BASE_URL=http://…`
- **THEN** el cliente Dart sí usa HTTP en claro, por lo que la documentación exige pasar la URL HTTPS del backend desplegado en `release`
