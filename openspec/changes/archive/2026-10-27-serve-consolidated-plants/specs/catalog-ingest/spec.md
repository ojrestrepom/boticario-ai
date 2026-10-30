# Spec Delta

## MODIFIED Requirements

### Requirement: Procedencia de cada dato
Todo dato del catálogo (nombre, parte, uso, referencia, objetivo, seguridad, imagen y campo de valor único) SHALL llevar el dataset del que proviene según los refs de la semilla. Las fuentes SHALL registrar su identificador, nombre, versión, licencia, URL de la licencia (nula si la fuente no tiene una), atribución, cita, URL y checksum del insumo, tomados del manifiesto, de modo que cada dato sea trazable hasta su dataset.

#### Scenario: Trazabilidad de un uso
- **WHEN** se consulta un uso de una planta en la base construida
- **THEN** es posible determinar su fuente, la licencia y la cita de esa fuente y la referencia bibliográfica del uso

#### Scenario: Trazabilidad de un objetivo
- **WHEN** se consulta un objetivo de una planta en la base construida
- **THEN** es posible determinar el dataset de la EMA que lo respalda y su licencia

#### Scenario: Dato sin fuente
- **WHEN** se intenta construir la base con un dato que no tiene fuente asociada
- **THEN** la construcción falla y no produce una base utilizable

#### Scenario: URL de licencia de una fuente
- **WHEN** el manifiesto declara `licenseUrl` para una fuente, como `https://creativecommons.org/licenses/by-sa/4.0/` para Wikipedia
- **THEN** la construcción lo guarda en `source.license_url` de esa fuente, y las fuentes sin `licenseUrl` o con `licenseUrl` nulo quedan con `license_url` nulo

#### Scenario: URL de licencia inválida en el manifiesto
- **WHEN** el manifiesto trae un `licenseUrl` que no es una URL https
- **THEN** la lectura de la semilla falla nombrando la fuente y no se escribe ninguna base
