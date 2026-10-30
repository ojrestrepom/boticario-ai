# Spec Delta

## MODIFIED Requirements

### Requirement: Fuentes con versión fija, checksum y licencia
Cada fuente que alimenta la semilla SHALL declararse con identificador, versión o snapshot, URL, licencia, URL de la licencia (opcional: una URL https, o `null` si la fuente no tiene una licencia con una URL única, como la licencia por archivo de Commons o los términos propios de la EMA y TPPT), atribución exigida y checksum del insumo. El manifiesto SHALL copiar la URL de la licencia de cada fuente que la declara. Las descargas SHALL ser un paso explícito, SHALL verificarse contra su checksum y SHALL cachearse en `data/.cache/`, ignorada por Git. Una fuente que cambia con el tiempo SHALL fijarse en un snapshot con su fecha. Las fuentes admitidas son USDA Dr. Duke, WCVP, WFO (solo respaldo), EMA (herbal medicines y PDF de seguridad), TPPT de Agroscope, EFSA Compendium of Botanicals, Wikidata, Wikipedia en español y Wikimedia Commons.

#### Scenario: Insumo íntegro
- **WHEN** un insumo cacheado coincide con el checksum declarado
- **THEN** el paso siguiente lo usa sin acceder a la red

#### Scenario: Insumo alterado o ausente
- **WHEN** un insumo cacheado no coincide con su checksum o no ha sido descargado
- **THEN** el paso falla indicando la fuente y el paso de descarga necesario, y no usa datos sin verificar

#### Scenario: Snapshot de una fuente cambiante
- **WHEN** se descarga el JSON de la EMA, que se actualiza dos veces al día
- **THEN** el manifiesto registra el `meta.timestamp` del snapshot y su checksum, y las ejecuciones posteriores usan ese snapshot hasta que se decida actualizarlo

#### Scenario: Retirar una fuente
- **WHEN** una fuente, por ejemplo Wikipedia, se desactiva en la configuración de las herramientas y se calcula el plan de regeneración
- **THEN** solo figuran como pendientes las plantas cuyo paquete usaba esa fuente, ningún registro regenerado contiene refs de ella, `description` queda `null` o se resume de otras fuentes del paquete, el validador no da errores y el manifiesto deja de listar la fuente

#### Scenario: Fuente fuera de la lista
- **WHEN** se intenta añadir una fuente descartada, como DrugBank o iNaturalist
- **THEN** el manifiesto y el validador de fuentes la rechazan por no estar en la lista de fuentes admitidas

#### Scenario: URL de licencia de una fuente
- **WHEN** `sources.json` declara para `wikipedia_es` la licencia CC BY-SA 4.0 y `licenseUrl` igual a `https://creativecommons.org/licenses/by-sa/4.0/`
- **THEN** el manifiesto sellado incluye ese `licenseUrl` en la fuente `wikipedia_es`, y los registros de las plantas y el `seedHash` no cambian

#### Scenario: Fuente sin URL de licencia
- **WHEN** una fuente, como Commons, declara `licenseUrl` igual a `null`, o no lo declara
- **THEN** la fuente se acepta y el manifiesto la lista con `licenseUrl` nulo o sin el campo, respectivamente

#### Scenario: URL de licencia inválida
- **WHEN** `licenseUrl` no es `null` ni una cadena que empiece por `https://`
- **THEN** la validación de fuentes falla indicando la fuente y el campo
