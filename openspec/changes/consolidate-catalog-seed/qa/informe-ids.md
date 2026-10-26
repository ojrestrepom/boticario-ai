# Informe 10.1: IDs de la base anterior frente a la nueva

Generado por `scripts/compare_bases.py` y `scripts/make_id_report.py` desde `evidence/ids/id-map.tsv`. La base anterior es la que construye `catalog-ingest download` y `build` en `main` (2.376 plantas, hash de contenido `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, ZIP de USDA de la caché); la nueva es `data/build/catalog.db` (2.354 plantas, hash `4be91c438ced8f41a07bc4873cc7562c869b5c16af44570d934f851bb7d5a639`).

## Resumen

| Medida | Anterior | Nueva |
| --- | --- | --- |
| Plantas | 2376 | 2354 |
| Plantas sin ningún uso | 1196 (50.3 %) | 923 (39.2 %) |
| Usos servidos por la API | 18931 | 24286 |
| Alias en `plant_alias` | 0 (no existía) | 650 |

| Destino de los 2.376 IDs anteriores | IDs |
| --- | --- |
| Mismo ID (sin cambio) | 1690 |
| Mismo ID y absorbe a otros IDs anteriores | 57 |
| Pasan a alias de otro ID (renombrados, 1 a 1) | 527 |
| Pasan a alias de un ID que absorbe a varios (fusionados) | 101 |
| Ausentes (justificado) | 1 |
| IDs que cambian (alias más ausentes) | 629 |

- Los 2.376 IDs anteriores tienen destino: 2375 son el mismo ID o un alias y 1 es ausencia justificada (`malachra-alaceaefolia`). Los IDs que cambian son 629, algo más que el «unos 500 a 600» estimado.
- 76 plantas nuevas reciben más de un ID anterior (fusiones por sinonimia). Todas las absorbidas quedan como alias de la planta que las absorbe; ningún alias coincide con el ID de otra planta.
- 61 plantas nuevas no vienen de ningún ID anterior (especies de la EMA fuera de USDA y miembros separados por la regla de colisiones); están en `evidence/ids/new-only.txt`. Hay además 22 alias que no corresponden a un ID anterior (`evidence/ids/extra-alias.txt`).
- Plantas que tenían usos y ya no los tienen: 26 (véase DEF-03 del informe de resultados y `evidence/ids/lost-uses-reasons.tsv`). Plantas que no tenían usos y ahora sí: 304.

## Tabla A: IDs que cambian (alias o ausencia)

| ID anterior | Nombre anterior | Destino | Nombre nuevo | Usos antes → ahora | Motivo |
| --- | --- | --- | --- | --- | --- |
| `acacia-catechu` | Acacia catechu | alias de `senegalia-catechu` | Senegalia catechu | 17 → 31 | sinónimo homotípico del aceptado de WCVP |
| `acacia-farnesiana` | Acacia farnesiana | alias de `vachellia-farnesiana` | Vachellia farnesiana | 27 → 27 | sinónimo homotípico del aceptado de WCVP |
| `acacia-lenticularis` | Acacia lenticularis | alias de `senegalia-lenticularis` | Senegalia lenticularis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `acacia-leucophloea` | Acacia leucophloea | alias de `vachellia-leucophloea` | Vachellia leucophloea | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `acacia-modesta` | Acacia modesta | alias de `senegalia-modesta` | Senegalia modesta | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `acacia-nilotica` | Acacia nilotica | alias de `vachellia-nilotica` | Vachellia nilotica | 2 → 5 | sinónimo homotípico del aceptado de WCVP |
| `acacia-senegal` | Acacia senegal | alias de `senegalia-senegal` | Senegalia senegal | 5 → 6 | sinónimo homotípico del aceptado de WCVP |
| `acacia-tortilis` | Acacia tortilis | alias de `vachellia-tortilis` | Vachellia tortilis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `acanthopanax-gracilistylis` | Acanthopanax gracilistylis | alias de `eleutherococcus-nodiflorus` | Eleutherococcus nodiflorus | 0 → 15 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `achillea-moschata` | Achillea moschata | alias de `achillea-erba-rotta-subsp-moschata` | Achillea erba-rotta subsp. moschata | 4 → 4 | sinónimo homotípico del aceptado de WCVP |
| `acinos-alpinus-var-meridionalis` | Acinos alpinus var. meridionalis | alias de `clinopodium-alpinum` | Clinopodium alpinum | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `acinos-suaveolens` | Acinos suaveolens | alias de `clinopodium-suaveolens` | Clinopodium suaveolens | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `acinos-thymoides` | Acinos thymoides | alias de `clinopodium-acinos` | Clinopodium acinos | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `aerva-lanata` | Aerva lanata | alias de `ouret-lanata` | Ouret lanata | 0 → 7 | sinónimo homotípico del aceptado de WCVP |
| `ailanthus-grandis` | Ailanthus grandis | alias de `ailanthus-integrifolia-subsp-calycina` | Ailanthus integrifolia subsp. calycina | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `ajuga-bracteosa` | Ajuga bracteosa | alias de `ajuga-integrifolia` | Ajuga integrifolia | 2 → 11 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: ajuga-remota (reviewFlag fusion-heterotipica) |
| `ajuga-remota` | Ajuga remota | alias de `ajuga-integrifolia` | Ajuga integrifolia | 0 → 11 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: ajuga-bracteosa (reviewFlag fusion-heterotipica) |
| `akania-luceus` | Akania luceus | alias de `akania-bidwillii` | Akania bidwillii | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `alangium-lamarckii` | Alangium lamarckii | alias de `alangium-salviifolium` | Alangium salviifolium | 3 → 20 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `aleurites-fordii` | Aleurites fordii | alias de `vernicia-fordii` | Vernicia fordii | 12 → 9 | sinónimo homotípico del aceptado de WCVP |
| `aleurites-moluccana` | Aleurites moluccana | alias de `aleurites-moluccanus` | Aleurites moluccanus | 9 → 23 | variante ortográfica del nombre de WCVP |
| `aleurites-montana` | Aleurites montana | alias de `vernicia-montana` | Vernicia montana | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `allium-sativum-var-sativum` | Allium sativum var. sativum | alias de `allium-sativum` | Allium sativum | 0 → 82 | infraespecífico o autónimo absorbido por la especie aceptada |
| `alnus-crispa` | Alnus crispa | alias de `alnus-alnobetula-subsp-crispa` | Alnus alnobetula subsp. crispa | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `alnus-rugosa` | Alnus rugosa | alias de `alnus-incana-subsp-rugosa` | Alnus incana subsp. rugosa | 5 → 5 | sinónimo homotípico del aceptado de WCVP |
| `alocasia-macrorrhiza` | Alocasia macrorrhiza | alias de `alocasia-macrorrhizos` | Alocasia macrorrhizos | 4 → 22 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `alyxia-levinei` | Alyxia levinei | alias de `alyxia-sinensis` | Alyxia sinensis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `ambrosia-cumanenesis` | Ambrosia cumanenesis | alias de `ambrosia-peruviana` | Ambrosia peruviana | 0 → 21 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `ammi-visnaga` | Ammi visnaga | alias de `visnaga-daucoides` | Visnaga daucoides | 23 → 24 | sinónimo homotípico del aceptado de WCVP |
| `amomum-compactum` | Amomum compactum | alias de `wurfbainia-compacta` | Wurfbainia compacta | 3 → 9 | sinónimo homotípico del aceptado de WCVP |
| `amomum-xanthioides` | Amomum xanthioides | alias de `wurfbainia-villosa-var-xanthioides` | Wurfbainia villosa var. xanthioides | 6 → 7 | sinónimo homotípico del aceptado de WCVP |
| `amoora-canarana` | Amoora canarana | alias de `aglaia-lawii-subsp-lawii` | Aglaia lawii subsp. lawii | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `amorphophallus-campanulatus` | Amorphophallus campanulatus | alias de `amorphophallus-paeoniifolius` | Amorphophallus paeoniifolius | 1 → 20 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `amphicarpaea-edgworthii` | Amphicarpaea edgworthii | alias de `amphicarpaea-edgeworthii` | Amphicarpaea edgeworthii | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `andira-araroba` | Andira araroba | alias de `vataireopsis-araroba` | Vataireopsis araroba | 8 → 7 | sinónimo homotípico del aceptado de WCVP |
| `andropogon-virginicus` | Andropogon virginicus | alias de `anatherum-virginicum` | Anatherum virginicum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `anemone-narcissiflora` | Anemone narcissiflora | alias de `anemonastrum-narcissiflorum` | Anemonastrum narcissiflorum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `anemone-pulsatilla` | Anemone pulsatilla | alias de `pulsatilla-vulgaris` | Pulsatilla vulgaris | 7 → 7 | sinónimo homotípico del aceptado de WCVP |
| `aniba-rosaeodora` | Aniba rosaeodora | alias de `aniba-rosodora` | Aniba rosodora | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `anisochilus-carnosus` | Anisochilus carnosus | alias de `coleus-strobilifer` | Coleus strobilifer | 0 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `annona-diversifolia` | Annona diversifolia | alias de `annona-macroprophyllata` | Annona macroprophyllata | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `anogeissus-latifolia` | Anogeissus latifolia | alias de `terminalia-anogeissiana` | Terminalia anogeissiana | 0 → 10 | sinónimo homotípico del aceptado de WCVP |
| `aquilaria-agallocha` | Aquilaria agallocha | alias de `aquilaria-malaccensis` | Aquilaria malaccensis | 23 → 21 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `arecastrum-romanzoffianum` | Arecastrum romanzoffianum | alias de `syagrus-romanzoffiana` | Syagrus romanzoffiana | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `argyreia-speciosa` | Argyreia speciosa | alias de `argyreia-nervosa` | Argyreia nervosa | 2 → 19 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: argyreia-nervosa (reviewFlag fusion-heterotipica) |
| `artocarpus-integrifolia` | Artocarpus integrifolia | alias de `artocarpus-integer` | Artocarpus integer | 1 → 5 | sinónimo homotípico del aceptado de WCVP |
| `asiasarum-heterotropoides` | Asiasarum heterotropoides | alias de `asarum-heterotropoides` | Asarum heterotropoides | 0 → 10 | sinónimo homotípico del aceptado de WCVP |
| `asiasarum-sieboldii` | Asiasarum sieboldii | alias de `asarum-sieboldii` | Asarum sieboldii | 5 → 35 | sinónimo homotípico del aceptado de WCVP |
| `asparagus-lucidus` | Asparagus lucidus | alias de `asparagus-cochinchinensis` | Asparagus cochinchinensis | 14 → 21 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `aspidixia-angulata` | Aspidixia angulata | alias de `viscum-angulatum` | Viscum angulatum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `atractylodes-ovata` | Atractylodes ovata | alias de `atractylodes-lancea` | Atractylodes lancea | 0 → 28 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: atractylodes-lancea (reviewFlag fusion-heterotipica) |
| `balanites-aegyptiacus` | Balanites aegyptiacus | alias de `balanites-aegyptiaca` | Balanites aegyptiaca | 0 → 22 | variante ortográfica del nombre de WCVP |
| `barosma-betulina` | Barosma betulina | alias de `agathosma-betulina` | Agathosma betulina | 11 → 11 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: agathosma-betulina |
| `belamcanda-chinensis` | Belamcanda chinensis | alias de `iris-domestica` | Iris domestica | 45 → 36 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `beta-vulgaris-subsp-subsp-vulgaris` | Beta vulgaris subsp. subsp. vulgaris | alias de `beta-vulgaris` | Beta vulgaris | 0 → 19 | infraespecífico o autónimo absorbido por la especie aceptada |
| `betula-alba` | Betula alba | alias de `betula-pubescens-var-pubescens` | Betula pubescens var. pubescens | 20 → 21 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `betula-caerulea` | Betula caerulea | alias de `betula-x-caerulea` | Betula × caerulea | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: betula-caerulea-grandis (reviewFlag fusion-heterotipica) |
| `betula-caerulea-grandis` | Betula caerulea-grandis | alias de `betula-x-caerulea` | Betula × caerulea | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: betula-caerulea (reviewFlag fusion-heterotipica) |
| `betula-dahurica` | Betula dahurica | alias de `betula-davurica` | Betula davurica | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `betula-platyphylla` | Betula platyphylla | alias de `betula-pendula-subsp-mandshurica` | Betula pendula subsp. mandshurica | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `bonnetia-dinizii` | Bonnetia dinizii | alias de `bonnetia-paniculata` | Bonnetia paniculata | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-juncea` | Brassica juncea | alias de `x-brassarda-juncea` | × Brassarda juncea | 12 → 24 | sinónimo homotípico del aceptado de WCVP |
| `brassica-napus-var-napobrassica-var-napobrassica` | Brassica napus var. napobrassica var. napobrassica | alias de `brassica-napus-var-napobrassica` | Brassica napus var. napobrassica | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-napus-var-napus` | Brassica napus var. napus | alias de `brassica-napus` | Brassica napus | 0 → 7 | infraespecífico o autónimo absorbido por la especie aceptada |
| `brassica-nigra` | Brassica nigra | alias de `mutarda-nigra` | Mutarda nigra | 34 → 31 | sinónimo homotípico del aceptado de WCVP |
| `brassica-oleracea-var-botrytis-l-var-botrytis` | Brassica oleracea var. botrytis l. var. botrytis | alias de `brassica-cretica-subsp-cretica` | Brassica cretica subsp. cretica | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-oleracea-var-capitata-l-var-capitata` | Brassica oleracea var. capitata l. var. capitata | alias de `brassica-oleracea-var-capitata` | Brassica oleracea var. capitata | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-oleracea-var-gemmifera-var-gemmifera` | Brassica oleracea var. gemmifera var. gemmifera | alias de `brassica-oleracea-var-gemmifera` | Brassica oleracea var. gemmifera | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-oleracea-var-sabellica-l-var-acephala` | Brassica oleracea var. sabellica l. var. acephala | alias de `brassica-oleracea-var-acephala` | Brassica oleracea var. acephala | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-oleracea-var-viridis-l` | Brassica oleracea var. viridis l. | alias de `brassica-oleracea-var-viridis` | Brassica oleracea var. viridis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `brassica-rapa-subsp-subsp-chinensis` | Brassica rapa subsp. subsp. chinensis | alias de `brassica-chinensis` | Brassica chinensis | 0 → 8 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: brassica-chinensis |
| `brassica-rapa-var-rapa` | Brassica rapa var. rapa | alias de `brassica-rapa` | Brassica rapa | 0 → 31 | infraespecífico o autónimo absorbido por la especie aceptada; se fusiona con otros: brassica-rapa |
| `brugmansia-amesianum` | Brugmansia amesianum | alias de `brugmansia-x-candida` | Brugmansia × candida | 4 → 11 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: datura-candida (reviewFlag fusion-heterotipica) |
| `bruguiera-gymnorrhiza` | Bruguiera gymnorrhiza | alias de `bruguiera-gymnorhiza` | Bruguiera gymnorhiza | 0 → 1 | variante ortográfica del nombre de WCVP |
| `brunfelsia-uniflorus` | Brunfelsia uniflorus | alias de `brunfelsia-uniflora` | Brunfelsia uniflora | 0 → 10 | variante ortográfica del nombre de WCVP |
| `bursera-delpechiana` | Bursera delpechiana | alias de `bursera-linanoe` | Bursera linanoe | 1 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `caesalpinia-decapetala` | Caesalpinia decapetala | alias de `biancaea-decapetala` | Biancaea decapetala | 0 → 10 | sinónimo homotípico del aceptado de WCVP |
| `calamintha-nepeta` | Calamintha nepeta | alias de `clinopodium-nepeta` | Clinopodium nepeta | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `calamintha-nepeta-subsp-glandulosa` | Calamintha nepeta subsp. glandulosa | alias de `clinopodium-nepeta-subsp-spruneri` | Clinopodium nepeta subsp. spruneri | 0 → 13 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `calathea-allouia` | Calathea allouia | alias de `goeppertia-allouia` | Goeppertia allouia | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `calathea-macrosepala` | Calathea macrosepala | alias de `goeppertia-macrosepala` | Goeppertia macrosepala | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `calea-zacatechichi` | Calea zacatechichi | alias de `calea-ternifolia` | Calea ternifolia | 7 → 8 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `callistemon-lanceolatus` | Callistemon lanceolatus | alias de `melaleuca-citrina` | Melaleuca citrina | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `canavalia-virosa` | Canavalia virosa | alias de `canavalia-cathartica` | Canavalia cathartica | 0 → 4 | sinónimo homotípico del aceptado de WCVP |
| `caraipa-densiflora` | Caraipa densiflora | alias de `caraipa-densifolia` | Caraipa densifolia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: caraipa-densifolia |
| `carica-pentagona` | Carica pentagona | alias de `vasconcellea-x-pentagona` | Vasconcellea × pentagona | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `carya-illinoensis` | Carya illinoensis | alias de `carya-illinoinensis` | Carya illinoinensis | 2 → 4 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `cassia-angustifolia` | Cassia angustifolia | alias de `senna-alexandrina-var-alexandrina` | Senna alexandrina var. alexandrina | 5 → 10 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cassia-marilandica` | Cassia marilandica | alias de `senna-marilandica` | Senna marilandica | 4 → 8 | sinónimo homotípico del aceptado de WCVP |
| `cassia-obtusifolia` | Cassia obtusifolia | alias de `senna-obtusifolia` | Senna obtusifolia | 5 → 13 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: senna-obtusifolia |
| `cassia-siamea` | Cassia siamea | alias de `senna-siamea` | Senna siamea | 0 → 2 | sinónimo homotípico del aceptado de WCVP |
| `cassia-tora` | Cassia tora | alias de `senna-tora` | Senna tora | 30 → 37 | sinónimo homotípico del aceptado de WCVP |
| `castanea-mollisima` | Castanea mollisima | alias de `castanea-mollissima` | Castanea mollissima | 0 → 6 | variante ortográfica del nombre de WCVP |
| `cedrus-deodora` | Cedrus deodora | alias de `cedrus-deodara` | Cedrus deodara | 1 → 1 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `celosia-cristata` | Celosia cristata | alias de `celosia-argentea` | Celosia argentea | 24 → 50 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `centrosema-schiedianum` | Centrosema schiedianum | alias de `centrosema-pubescens` | Centrosema pubescens | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cephaelis-ipecacuanha` | Cephaelis ipecacuanha | alias de `carapichea-ipecacuanha` | Carapichea ipecacuanha | 18 → 28 | sinónimo homotípico del aceptado de WCVP |
| `cephalotaxus-drupacea` | Cephalotaxus drupacea | alias de `cephalotaxus-harringtonia` | Cephalotaxus harringtonia | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: cephalotaxus-harringtonii,cephalotaxus-wilsoniana (reviewFlag fusion-heterotipica) |
| `cephalotaxus-harringtonii` | Cephalotaxus harringtonii | alias de `cephalotaxus-harringtonia` | Cephalotaxus harringtonia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: cephalotaxus-drupacea,cephalotaxus-wilsoniana (reviewFlag fusion-heterotipica) |
| `cephalotaxus-wilsoniana` | Cephalotaxus wilsoniana | alias de `cephalotaxus-harringtonia` | Cephalotaxus harringtonia | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: cephalotaxus-drupacea,cephalotaxus-harringtonii (reviewFlag fusion-heterotipica) |
| `cereus-grandiflorus` | Cereus grandiflorus | alias de `selenicereus-grandiflorus` | Selenicereus grandiflorus | 6 → 13 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: selenicereus-grandiflorus |
| `chaenomeles-lagenaria` | Chaenomeles lagenaria | alias de `chaenomeles-japonica` | Chaenomeles japonica | 8 → 19 | sinónimo homotípico del aceptado de WCVP |
| `chamaecytisus-smyrnaeus` | Chamaecytisus smyrnaeus | alias de `chamaecytisus-eriocarpus-subsp-eriocarpus` | Chamaecytisus eriocarpus subsp. eriocarpus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `chamaespartium-sagittale` | Chamaespartium sagittale | alias de `genista-sagittalis` | Genista sagittalis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `chamaespartium-tridentatum` | Chamaespartium tridentatum | alias de `genista-tridentata` | Genista tridentata | 0 → 3 | sinónimo homotípico del aceptado de WCVP |
| `chamaesyce-hypericifolia` | Chamaesyce hypericifolia | alias de `euphorbia-hypericifolia` | Euphorbia hypericifolia | 7 → 20 | sinónimo homotípico del aceptado de WCVP |
| `chenopodium-ambrosioides` | Chenopodium ambrosioides | alias de `dysphania-ambrosioides` | Dysphania ambrosioides | 65 → 59 | sinónimo homotípico del aceptado de WCVP |
| `chronanthus-biflorus` | Chronanthus biflorus | alias de `cytisus-fontanesii` | Cytisus fontanesii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `chrysanthemum-balsamita` | Chrysanthemum balsamita | alias de `tanacetum-balsamita-var-balsamitoides` | Tanacetum balsamita var. balsamitoides | 11 → 0 | sinónimo homotípico del aceptado de WCVP |
| `chrysanthemum-cinerariifolium` | Chrysanthemum cinerariifolium | alias de `tanacetum-cinerariifolium` | Tanacetum cinerariifolium | 1 → 14 | sinónimo homotípico del aceptado de WCVP |
| `chrysanthemum-coronarium` | Chrysanthemum coronarium | alias de `glebionis-coronaria` | Glebionis coronaria | 5 → 5 | sinónimo homotípico del aceptado de WCVP |
| `chrysanthemum-parthenium` | Chrysanthemum parthenium | alias de `tanacetum-parthenium` | Tanacetum parthenium | 34 → 31 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: tanacetum-parthenium |
| `cimicifuga-dahurica` | Cimicifuga dahurica | alias de `actaea-dahurica` | Actaea dahurica | 5 → 5 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: actaea-dahurica |
| `cimicifuga-foetida` | Cimicifuga foetida | alias de `actaea-cimicifuga` | Actaea cimicifuga | 16 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: actaea-cimicifuga |
| `cimicifuga-japonica` | Cimicifuga japonica | alias de `actaea-japonica` | Actaea japonica | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `cimicifuga-racemosa` | Cimicifuga racemosa | alias de `actaea-racemosa` | Actaea racemosa | 22 → 28 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: actaea-racemosa |
| `cimicifuga-simplex` | Cimicifuga simplex | alias de `actaea-simplex` | Actaea simplex | 7 → 7 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: actaea-simplex |
| `cinchona-succirubra` | Cinchona succirubra | alias de `cinchona-pubescens` | Cinchona pubescens | 11 → 15 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: cinchona-pubescens (reviewFlag fusion-heterotipica) |
| `cinnamomum-burmannii` | Cinnamomum burmannii | alias de `cinnamomum-burmanni` | Cinnamomum burmanni | 7 → 14 | variante ortográfica del nombre de WCVP |
| `cinnamomum-camphora` | Cinnamomum camphora | alias de `camphora-officinarum` | Camphora officinarum | 42 → 31 | sinónimo homotípico del aceptado de WCVP |
| `cinnamomum-glaucescens` | Cinnamomum glaucescens | alias de `camphora-glaucescens` | Camphora glaucescens | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `cinnamomum-impressicostatum` | Cinnamomum impressicostatum | alias de `cinnamomum-vimineum` | Cinnamomum vimineum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cinnamomum-porrectum` | Cinnamomum porrectum | alias de `camphora-parthenoxylon` | Camphora parthenoxylon | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cinnamomum-pubescens` | Cinnamomum pubescens | alias de `cinnamomum-scortechinii` | Cinnamomum scortechinii | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cinnamomum-zeylanicum` | Cinnamomum zeylanicum | alias de `cinnamomum-verum` | Cinnamomum verum | 7 → 26 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: cinnamomum-verum (reviewFlag fusion-heterotipica) |
| `cistus-ladaniferus` | Cistus ladaniferus | alias de `cistus-ladanifer` | Cistus ladanifer | 10 → 13 | variante ortográfica del nombre de WCVP |
| `citharexylum-subserratum` | Citharexylum subserratum | alias de `citharexylum-spinosum` | Citharexylum spinosum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-aurantiifolia` | Citrus aurantiifolia | alias de `citrus-x-aurantiifolia` | Citrus × aurantiifolia | 40 → 59 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `citrus-aurantium` | Citrus aurantium | alias de `citrus-x-aurantium` | Citrus × aurantium | 67 → 46 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: citrus-aurantium-f-kabusu |
| `citrus-aurantium-f-kabusu` | Citrus aurantium f. kabusu | alias de `citrus-x-aurantium` | Citrus × aurantium | 0 → 46 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: citrus-aurantium |
| `citrus-ichangensis` | Citrus ichangensis | alias de `citrus-cavaleriei` | Citrus cavaleriei | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-junos` | Citrus junos | alias de `citrus-x-junos` | Citrus × junos | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `citrus-limetta` | Citrus limetta | alias de `citrus-x-limetta` | Citrus × limetta | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-limon` | Citrus limon | alias de `citrus-x-limon` | Citrus × limon | 21 → 22 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `citrus-meyerii` | Citrus meyerii | alias de `citrus-x-meyeri` | Citrus × meyeri | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-mitis` | Citrus mitis | alias de `citrus-x-microcarpa` | Citrus × microcarpa | 0 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-paradisi` | Citrus paradisi | alias de `citrus-x-paradisi` | Citrus × paradisi | 2 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-sinensis` | Citrus sinensis | alias de `citrus-x-sinensis` | Citrus × sinensis | 49 → 38 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-sphaerocarpa` | Citrus sphaerocarpa | alias de `citrus-x-sphaerocarpa` | Citrus × sphaerocarpa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-sudachi` | Citrus sudachi | alias de `citrus-x-sudachi` | Citrus × sudachi | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `citrus-unshiu` | Citrus unshiu | alias de `citrus-x-aurantium-f-deliciosa` | Citrus × aurantium f. deliciosa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `claoxylon-polot` | Claoxylon polot | alias de `claoxylon-indicum` | Claoxylon indicum | 0 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cleistocalyx-fullageri` | Cleistocalyx fullageri | alias de `syzygium-fullagarii` | Syzygium fullagarii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `clerodendrum-inerme` | Clerodendrum inerme | alias de `volkameria-inermis` | Volkameria inermis | 4 → 21 | sinónimo homotípico del aceptado de WCVP |
| `cnicus-benedictus` | Cnicus benedictus | alias de `centaurea-benedicta` | Centaurea benedicta | 35 → 35 | sinónimo homotípico del aceptado de WCVP |
| `cnidium-officinale` | Cnidium officinale | alias de `conioselinum-officinale` | Conioselinum officinale | 4 → 4 | sinónimo homotípico del aceptado de WCVP |
| `cnidoscolus-chayamansa` | Cnidoscolus chayamansa | alias de `cnidoscolus-aconitifolius-subsp-aconitifolius` | Cnidoscolus aconitifolius subsp. aconitifolius | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `coccoloba-excoriata` | Coccoloba excoriata | alias de `coccoloba-tenuifolia` | Coccoloba tenuifolia | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `coleus-blumei` | Coleus blumei | alias de `coleus-scutellarioides` | Coleus scutellarioides | 0 → 24 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `coleus-forskohlii` | Coleus forskohlii | alias de `coleus-barbatus-var-barbatus` | Coleus barbatus var. barbatus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `coleus-ignarius` | Coleus ignarius | alias de `coleus-igniarius` | Coleus igniarius | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `cologana-broussonetii` | Cologana broussonetii | alias de `cologania-broussonetii` | Cologania broussonetii | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `colubrina-granulosa` | Colubrina granulosa | alias de `frangula-granulosa` | Frangula granulosa | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `commiphora-mukul` | Commiphora mukul | alias de `commiphora-wightii` | Commiphora wightii | 11 → 24 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: commiphora-wightii (reviewFlag fusion-heterotipica) |
| `consolida-ajacis` | Consolida ajacis | alias de `delphinium-ajacis` | Delphinium ajacis | 0 → 6 | sinónimo homotípico del aceptado de WCVP |
| `conyza-canadensis` | Conyza canadensis | alias de `erigeron-canadensis` | Erigeron canadensis | 0 → 34 | sinónimo homotípico del aceptado de WCVP |
| `coriaria-thymifolia` | Coriaria thymifolia | alias de `coriaria-ruscifolia-subsp-microphylla` | Coriaria ruscifolia subsp. microphylla | 6 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `coridothymus-capitatus` | Coridothymus capitatus | alias de `thymbra-capitata` | Thymbra capitata | 0 → 1 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: thymus-capitatus |
| `costus-speciosus` | Costus speciosus | alias de `hellenia-speciosa` | Hellenia speciosa | 1 → 22 | sinónimo homotípico del aceptado de WCVP |
| `coutarea-latiflora` | Coutarea latiflora | alias de `hintonia-latiflora` | Hintonia latiflora | 3 → 12 | sinónimo homotípico del aceptado de WCVP |
| `crataegus-oxyacantha` | Crataegus oxyacantha | alias de `crataegus-rhipidophylla-var-rhipidophylla` | Crataegus rhipidophylla var. rhipidophylla | 12 → 16 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cryptostegia-grandifolia` | Cryptostegia grandifolia | alias de `cryptostegia-grandiflora` | Cryptostegia grandiflora | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `cucumis-melo-subsp-ssp-melo-var-cantalupensis` | Cucumis melo subsp. ssp melo var.cantalupensis | alias de `cucumis-melo` | Cucumis melo | 0 → 32 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cuphea-epilobifolia` | Cuphea epilobifolia | alias de `cuphea-epilobiifolia` | Cuphea epilobiifolia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `cuphea-infundibulum` | Cuphea infundibulum | alias de `cuphea-appendiculata-var-appendiculata` | Cuphea appendiculata var. appendiculata | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `curcuma-xanthorrhiza` | Curcuma xanthorrhiza | alias de `curcuma-zanthorrhiza` | Curcuma zanthorrhiza | 0 → 9 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `cymbopogon-martinii` | Cymbopogon martinii | alias de `cymbopogon-martini` | Cymbopogon martini | 1 → 14 | variante ortográfica del nombre de WCVP |
| `cymbopogon-parkeri` | Cymbopogon parkeri | alias de `cymbopogon-commutatus` | Cymbopogon commutatus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cynanchum-atratum` | Cynanchum atratum | alias de `vincetoxicum-atratum` | Vincetoxicum atratum | 4 → 27 | sinónimo homotípico del aceptado de WCVP |
| `cynara-scolymus` | Cynara scolymus | alias de `cynara-cardunculus-subsp-cardunculus` | Cynara cardunculus subsp. cardunculus | 15 → 15 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: cynara-cardunculus-subsp-cardunculus |
| `cyphomandra-betacea` | Cyphomandra betacea | alias de `solanum-betaceum` | Solanum betaceum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `cypripedium-pubescens` | Cypripedium pubescens | alias de `cypripedium-parviflorum-var-pubescens` | Cypripedium parviflorum var. pubescens | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `cyrtosperma-chamissonis` | Cyrtosperma chamissonis | alias de `cyrtosperma-merkusii` | Cyrtosperma merkusii | 0 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cytisus-ardoini` | Cytisus ardoini | alias de `cytisus-ardoinoi` | Cytisus ardoinoi | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `cytisus-ingramii` | Cytisus ingramii | alias de `cytisus-commutatus` | Cytisus commutatus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cytisus-patens` | Cytisus patens | alias de `cytisus-striatus-subsp-striatus` | Cytisus striatus subsp. striatus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `cytisus-tribracteolatus` | Cytisus tribracteolatus | alias de `genista-tribracteolata` | Genista tribracteolata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `daemonorops-draco` | Daemonorops draco | alias de `calamus-draco` | Calamus draco | 11 → 24 | sinónimo homotípico del aceptado de WCVP |
| `dalbergia-paniculata` | Dalbergia paniculata | alias de `dalbergia-lanceolaria-subsp-paniculata` | Dalbergia lanceolaria subsp. paniculata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `datura-candida` | Datura candida | alias de `brugmansia-x-candida` | Brugmansia × candida | 11 → 11 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: brugmansia-amesianum (reviewFlag fusion-heterotipica) |
| `dendroseris-neriifolia` | Dendroseris neriifolia | alias de `sonchus-neriifolius` | Sonchus neriifolius | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `desmodium-gangeticum` | Desmodium gangeticum | alias de `pleurolobus-gangeticus` | Pleurolobus gangeticus | 7 → 20 | sinónimo homotípico del aceptado de WCVP |
| `dichrostachys-glomerata` | Dichrostachys glomerata | alias de `dichrostachys-cinerea-subsp-africana` | Dichrostachys cinerea subsp. africana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `dicliptera-roxburghiana` | Dicliptera roxburghiana | alias de `dicliptera-chinensis` | Dicliptera chinensis | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `dictamnus-angustifolius` | Dictamnus angustifolius | alias de `dictamnus-albus` | Dictamnus albus | 0 → 22 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: dictamnus-albus,dictamnus-caucasicus (reviewFlag fusion-heterotipica) |
| `dictamnus-caucasicus` | Dictamnus caucasicus | alias de `dictamnus-albus` | Dictamnus albus | 0 → 22 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: dictamnus-albus,dictamnus-angustifolius (reviewFlag fusion-heterotipica) |
| `dillenia-anhamanica` | Dillenia anhamanica | alias de `dillenia-andamanica` | Dillenia andamanica | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `dioclea-glycinoides` | Dioclea glycinoides | alias de `camptosema-rubicundum` | Camptosema rubicundum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `diospyros-digyna` | Diospyros digyna | alias de `diospyros-nigra` | Diospyros nigra | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `diospyros-discolour` | Diospyros discolour | alias de `diospyros-blancoi` | Diospyros blancoi | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `diospyros-ismailii` | Diospyros ismailii | alias de `diospyros-insidiosa` | Diospyros insidiosa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `diospyros-oblongifolia` | Diospyros oblongifolia | alias de `diospyros-srilankana` | Diospyros srilankana | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `diospyros-perigrina` | Diospyros perigrina | alias de `diospyros-peregrina` | Diospyros peregrina | 0 → 25 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `diospyros-siamensis` | Diospyros siamensis | alias de `diospyros-malabarica` | Diospyros malabarica | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `diospyros-tomentosa` | Diospyros tomentosa | alias de `diospyros-chloroxylon` | Diospyros chloroxylon | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `discaria-longispina` | Discaria longispina | alias de `discaria-americana` | Discaria americana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `dolichos-biflorus` | Dolichos biflorus | alias de `macrotyloma-biflorum-var-biflorum` | Macrotyloma biflorum var. biflorum | 1 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `dracocephalum-parviflora` | Dracocephalum parviflora | alias de `dracocephalum-parviflorum` | Dracocephalum parviflorum | 0 → 0 | variante ortográfica del nombre de WCVP |
| `dracocephalum-thymiflora` | Dracocephalum thymiflora | alias de `dracocephalum-thymiflorum` | Dracocephalum thymiflorum | 0 → 0 | variante ortográfica del nombre de WCVP; se fusiona con otros: moldavica-thymiflora |
| `drynaria-fortunei` | Drynaria fortunei | alias de `drynaria-roosii` | Drynaria roosii | 17 → 21 | sinónimo homotípico del aceptado de WCVP |
| `duchesnea-indica` | Duchesnea indica | alias de `potentilla-indica` | Potentilla indica | 14 → 22 | sinónimo homotípico del aceptado de WCVP |
| `duranta-repens` | Duranta repens | alias de `duranta-erecta` | Duranta erecta | 5 → 5 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `echinospartium-horridum` | Echinospartium horridum | alias de `echinospartum-horridum` | Echinospartum horridum | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `elaeagnus-umbellatus` | Elaeagnus umbellatus | alias de `elaeagnus-umbellata` | Elaeagnus umbellata | 0 → 5 | variante ortográfica del nombre de WCVP |
| `elsholtzia-cristata` | Elsholtzia cristata | alias de `elsholtzia-ciliata` | Elsholtzia ciliata | 13 → 15 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: elsholtzia-ciliata,elsholtzia-patrini (reviewFlag fusion-heterotipica) |
| `elsholtzia-eriostachya-var-pusilla` | Elsholtzia eriostachya var. pusilla | alias de `elsholtzia-eriostachya` | Elsholtzia eriostachya | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `elsholtzia-incisa` | Elsholtzia incisa | alias de `elsholtzia-stachyodes` | Elsholtzia stachyodes | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `elsholtzia-patrini` | Elsholtzia patrini | alias de `elsholtzia-ciliata` | Elsholtzia ciliata | 0 → 15 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: elsholtzia-ciliata,elsholtzia-cristata (reviewFlag fusion-heterotipica) |
| `elsholtzia-polystachya` | Elsholtzia polystachya | alias de `elsholtzia-fruticosa` | Elsholtzia fruticosa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `elytrigia-repens` | Elytrigia repens | alias de `elymus-repens` | Elymus repens | 0 → 26 | sinónimo homotípico del aceptado de WCVP |
| `emilia-flammea` | Emilia flammea | alias de `emilia-coccinea` | Emilia coccinea | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `eryngium-creticus` | Eryngium creticus | alias de `eryngium-creticum` | Eryngium creticum | 0 → 4 | variante ortográfica del nombre de WCVP |
| `eryngium-floridanum` | Eryngium floridanum | alias de `eryngium-aquaticum-var-floridanum` | Eryngium aquaticum var. floridanum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `erythroxylum-argentatum` | Erythroxylum argentatum | alias de `erythroxylum-argentinum` | Erythroxylum argentinum | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `erythroxylum-brownianum` | Erythroxylum brownianum | alias de `erythroxylum-delagoense` | Erythroxylum delagoense | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `erythroxylum-coca-var-coca` | Erythroxylum coca var. coca | alias de `erythroxylum-coca` | Erythroxylum coca | 0 → 29 | infraespecífico o autónimo absorbido por la especie aceptada |
| `erythroxylum-cumanense` | Erythroxylum cumanense | alias de `erythroxylum-havanense` | Erythroxylum havanense | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: erythroxylum-ovatum (reviewFlag fusion-heterotipica) |
| `erythroxylum-macrocnemum` | Erythroxylum macrocnemum | alias de `erythroxylum-macrophyllum-var-macrocnemium` | Erythroxylum macrophyllum var. macrocnemium | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `erythroxylum-montanum` | Erythroxylum montanum | alias de `erythroxylum-ecarinatum` | Erythroxylum ecarinatum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `erythroxylum-novogranatense-var-novogranatense` | Erythroxylum novogranatense var. novogranatense | alias de `erythroxylum-novogranatense` | Erythroxylum novogranatense | 0 → 0 | infraespecífico o autónimo absorbido por la especie aceptada |
| `erythroxylum-ovatum` | Erythroxylum ovatum | alias de `erythroxylum-havanense` | Erythroxylum havanense | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: erythroxylum-cumanense (reviewFlag fusion-heterotipica) |
| `erythroxylum-recurrens` | Erythroxylum recurrens | alias de `erythroxylum-gracilipes` | Erythroxylum gracilipes | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: erythroxylum-gracilipes (reviewFlag fusion-heterotipica) |
| `erythroxylum-shatoni` | Erythroxylum shatoni | alias de `erythroxylum-shatona` | Erythroxylum shatona | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `eschscholzia-californica-subsp-californica` | Eschscholzia californica subsp. californica | alias de `eschscholzia-californica` | Eschscholzia californica | 0 → 6 | infraespecífico o autónimo absorbido por la especie aceptada |
| `eucalyptus-calophylla` | Eucalyptus calophylla | alias de `corymbia-calophylla` | Corymbia calophylla | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `eucalyptus-citriodora` | Eucalyptus citriodora | alias de `corymbia-citriodora` | Corymbia citriodora | 0 → 5 | sinónimo homotípico del aceptado de WCVP |
| `eucalyptus-cornea` | Eucalyptus cornea | alias de `eucalyptus-carnea` | Eucalyptus carnea | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `eucalyptus-corynocalyx` | Eucalyptus corynocalyx | alias de `eucalyptus-cladocalyx` | Eucalyptus cladocalyx | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: eucalyptus-cladocalyx |
| `eucalyptus-erythrandra` | Eucalyptus erythrandra | alias de `eucalyptus-x-erythrandra` | Eucalyptus × erythrandra | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `eucalyptus-fasiculosa` | Eucalyptus fasiculosa | alias de `eucalyptus-fasciculosa` | Eucalyptus fasciculosa | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `eucalyptus-hemiphloia` | Eucalyptus hemiphloia | alias de `eucalyptus-moluccana` | Eucalyptus moluccana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: eucalyptus-moluccana (reviewFlag fusion-heterotipica) |
| `eucalyptus-macrorrhuncha` | Eucalyptus macrorrhuncha | alias de `eucalyptus-macrorhyncha` | Eucalyptus macrorhyncha | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `eucalyptus-maculata` | Eucalyptus maculata | alias de `corymbia-maculata` | Corymbia maculata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `eucalyptus-maideni` | Eucalyptus maideni | alias de `eucalyptus-maidenii` | Eucalyptus maidenii | 0 → 0 | variante ortográfica del nombre de WCVP |
| `eucalyptus-oviformis` | Eucalyptus oviformis | alias de `eucalyptus-x-oviformis` | Eucalyptus × oviformis | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `eucalyptus-rostratus` | Eucalyptus rostratus | alias de `eucalyptus-camaldulensis-subsp-camaldulensis` | Eucalyptus camaldulensis subsp. camaldulensis | 0 → 10 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `eugenia-floribunda` | Eugenia floribunda | alias de `myrciaria-floribunda` | Myrciaria floribunda | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `eugenia-fruticosa` | Eugenia fruticosa | alias de `syzygium-cumini` | Syzygium cumini | 0 → 18 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: eugenia-jambolana,syzygium-cumini (reviewFlag fusion-heterotipica) |
| `eugenia-jambolana` | Eugenia jambolana | alias de `syzygium-cumini` | Syzygium cumini | 3 → 18 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: eugenia-fruticosa,syzygium-cumini (reviewFlag fusion-heterotipica) |
| `eugenia-wallichii` | Eugenia wallichii | alias de `syzygium-praecox` | Syzygium praecox | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `euodia-rutaecarpa` | Euodia rutaecarpa | alias de `tetradium-ruticarpum` | Tetradium ruticarpum | 0 → 5 | sinónimo homotípico del aceptado de WCVP |
| `eupatorium-odoratum` | Eupatorium odoratum | alias de `chromolaena-odorata` | Chromolaena odorata | 31 → 0 | sinónimo homotípico del aceptado de WCVP |
| `eupatorium-triplinerve` | Eupatorium triplinerve | alias de `ayapana-triplinervis` | Ayapana triplinervis | 6 → 26 | sinónimo homotípico del aceptado de WCVP |
| `euphorbia-broteri` | Euphorbia broteri | alias de `euphorbia-oxyphylla` | Euphorbia oxyphylla | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `euphorbia-hermentiana` | Euphorbia hermentiana | alias de `euphorbia-trigona` | Euphorbia trigona | 1 → 6 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `fagonia-cretica` | Fagonia cretica | alias de `zygophyllum-creticum` | Zygophyllum creticum | 3 → 3 | sinónimo homotípico del aceptado de WCVP |
| `fagonia-indica` | Fagonia indica | alias de `zygophyllum-indicum` | Zygophyllum indicum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `fagus-taurica` | Fagus taurica | alias de `fagus-x-taurica` | Fagus × taurica | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `fallopia-japonica` | Fallopia japonica | alias de `reynoutria-japonica` | Reynoutria japonica | 0 → 21 | sinónimo homotípico del aceptado de WCVP |
| `ferula-sumbul` | Ferula sumbul | alias de `ferula-moschata` | Ferula moschata | 10 → 15 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `ficus-thunbergii` | Ficus thunbergii | alias de `ficus-sarmentosa-var-thunbergii` | Ficus sarmentosa var. thunbergii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `formosia-benthamiana` | Formosia benthamiana | alias de `anodendron-benthamianum` | Anodendron benthamianum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `fraxinus-rhynchophylla` | Fraxinus rhynchophylla | alias de `fraxinus-chinensis-subsp-rhynchophylla` | Fraxinus chinensis subsp. rhynchophylla | 8 → 12 | sinónimo homotípico del aceptado de WCVP |
| `galipea-officinalis` | Galipea officinalis | alias de `angostura-trifoliata` | Angostura trifoliata | 0 → 14 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `garcinia-cambogia` | Garcinia cambogia | alias de `garcinia-gummi-gutta` | Garcinia gummi-gutta | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `geissospermum-vellosii` | Geissospermum vellosii | alias de `geissospermum-laeve` | Geissospermum laeve | 2 → 4 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: geissospermum-laeve |
| `genista-patula` | Genista patula | alias de `genista-tinctoria-subsp-tinctoria` | Genista tinctoria subsp. tinctoria | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `genista-rumelica` | Genista rumelica | alias de `genista-lydia` | Genista lydia | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: genista-lydia (reviewFlag fusion-heterotipica) |
| `givotia-rottleriformis` | Givotia rottleriformis | alias de `givotia-moluccana` | Givotia moluccana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `glycine-wightii` | Glycine wightii | alias de `neonotonia-wightii` | Neonotonia wightii | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: neonotonia-wightii |
| `gnaphalium-viscosum` | Gnaphalium viscosum | alias de `pseudognaphalium-viscosum` | Pseudognaphalium viscosum | 6 → 6 | sinónimo homotípico del aceptado de WCVP |
| `gochnatia-blanchetiana` | Gochnatia blanchetiana | alias de `moquiniastrum-blanchetianum` | Moquiniastrum blanchetianum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `grewia-tiliaefolia` | Grewia tiliaefolia | alias de `grewia-tiliifolia` | Grewia tiliifolia | 0 → 5 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `guarea-rusbyi` | Guarea rusbyi | alias de `guarea-guidonia` | Guarea guidonia | 2 → 8 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `guatteria-scadens` | Guatteria scadens | alias de `guatteria-scandens` | Guatteria scandens | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `guazuma-tomentosa` | Guazuma tomentosa | alias de `guazuma-ulmifolia` | Guazuma ulmifolia | 7 → 42 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: guazuma-ulmifolia (reviewFlag fusion-heterotipica) |
| `helianthemum-glomeratum` | Helianthemum glomeratum | alias de `crocanthemum-glomeratum` | Crocanthemum glomeratum | 2 → 6 | sinónimo homotípico del aceptado de WCVP |
| `helichrysum-angustifolium` | Helichrysum angustifolium | alias de `helichrysum-litoreum` | Helichrysum litoreum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `helichrysum-bilobum` | Helichrysum bilobum | alias de `ozothamnus-bilobus` | Ozothamnus bilobus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `helictores-isora` | Helictores isora | alias de `helicteres-isora` | Helicteres isora | 0 → 24 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `heliotropium-indicus` | Heliotropium indicus | alias de `heliotropium-indicum` | Heliotropium indicum | 0 → 36 | variante ortográfica del nombre de WCVP |
| `herpestis-monniera` | Herpestis monniera | alias de `bacopa-monnieri` | Bacopa monnieri | 0 → 28 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: bacopa-monnieri |
| `hibiscus-cannabinus` | Hibiscus cannabinus | alias de `sabdariffa-cannabina` | Sabdariffa cannabina | 7 → 11 | sinónimo homotípico del aceptado de WCVP |
| `hibiscus-rosa-sinensis` | Hibiscus rosa-sinensis | alias de `hibiscus-x-rosa-sinensis` | Hibiscus × rosa-sinensis | 34 → 37 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `hibiscus-sabdariffa` | Hibiscus sabdariffa | alias de `sabdariffa-gossypiifolia` | Sabdariffa gossypiifolia | 26 → 39 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `hierochloe-odorata` | Hierochloe odorata | alias de `anthoxanthum-nitens` | Anthoxanthum nitens | 6 → 9 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `hippuris-vulgare` | Hippuris vulgare | alias de `hippuris-vulgaris` | Hippuris vulgaris | 0 → 0 | variante ortográfica del nombre de WCVP |
| `holacantha-emoryi` | Holacantha emoryi | alias de `castela-emoryi` | Castela emoryi | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `hybanthus-enneasperma` | Hybanthus enneasperma | alias de `afrohybanthus-enneaspermus` | Afrohybanthus enneaspermus | 0 → 10 | sinónimo homotípico del aceptado de WCVP |
| `hydnocarpus-anthelminticus` | Hydnocarpus anthelminticus | alias de `hydnocarpus-castaneus` | Hydnocarpus castaneus | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `hydnocarpus-venenata` | Hydnocarpus venenata | alias de `hydnocarpus-venenatus` | Hydnocarpus venenatus | 0 → 0 | variante ortográfica del nombre de WCVP |
| `hydnocarpus-wightiana` | Hydnocarpus wightiana | alias de `hydnocarpus-pentandrus` | Hydnocarpus pentandrus | 1 → 12 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `hylocereus-guatemalensis` | Hylocereus guatemalensis | alias de `selenicereus-guatemalensis` | Selenicereus guatemalensis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `hylocereus-undatus` | Hylocereus undatus | alias de `selenicereus-undatus` | Selenicereus undatus | 3 → 3 | sinónimo homotípico del aceptado de WCVP |
| `hypericum-elatum` | Hypericum elatum | alias de `hypericum-x-inodorum` | Hypericum × inodorum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `hyptis-albida` | Hyptis albida | alias de `condea-albida` | Condea albida | 5 → 5 | sinónimo homotípico del aceptado de WCVP |
| `hyptis-emoryi` | Hyptis emoryi | alias de `condea-emoryi` | Condea emoryi | 1 → 6 | sinónimo homotípico del aceptado de WCVP |
| `hyptis-spicata` | Hyptis spicata | alias de `cantinoa-mutabilis` | Cantinoa mutabilis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `hyptis-suaveolens` | Hyptis suaveolens | alias de `mesosphaerum-suaveolens` | Mesosphaerum suaveolens | 27 → 48 | sinónimo homotípico del aceptado de WCVP |
| `hyptis-verticillata` | Hyptis verticillata | alias de `condea-verticillata` | Condea verticillata | 6 → 10 | sinónimo homotípico del aceptado de WCVP |
| `hyssopus-ferganensis` | Hyssopus ferganensis | alias de `dracocephalum-seravschanicum` | Dracocephalum seravschanicum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: hyssopus-seravshanicus (reviewFlag fusion-heterotipica) |
| `hyssopus-officinalis` | Hyssopus officinalis | alias de `dracocephalum-officinale` | Dracocephalum officinale | 26 → 28 | sinónimo homotípico del aceptado de WCVP |
| `hyssopus-seravshanicus` | Hyssopus seravshanicus | alias de `dracocephalum-seravschanicum` | Dracocephalum seravschanicum | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: hyssopus-ferganensis (reviewFlag fusion-heterotipica) |
| `inga-feuillei` | Inga feuillei | alias de `inga-feuilleei` | Inga feuilleei | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `inocarpus-edulis` | Inocarpus edulis | alias de `inocarpus-fagifer` | Inocarpus fagifer | 3 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `isanthus-brachiatus` | Isanthus brachiatus | alias de `trichostema-dichotomum` | Trichostema dichotomum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: trichostemma-dichotomum (reviewFlag fusion-heterotipica) |
| `jatropha-gossypifolia` | Jatropha gossypifolia | alias de `jatropha-gossypiifolia` | Jatropha gossypiifolia | 37 → 61 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `jessenia-bataua` | Jessenia bataua | alias de `oenocarpus-bataua` | Oenocarpus bataua | 0 → 7 | sinónimo homotípico del aceptado de WCVP |
| `juniperus-macropoda` | Juniperus macropoda | alias de `juniperus-seravschanica` | Juniperus seravschanica | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `jussiaea-repens` | Jussiaea repens | alias de `ludwigia-adscendens-subsp-adscendens` | Ludwigia adscendens subsp. adscendens | 7 → 8 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `jussiaea-suffruticosa` | Jussiaea suffruticosa | alias de `ludwigia-octovalvis-subsp-octovalvis` | Ludwigia octovalvis subsp. octovalvis | 0 → 9 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `justicia-pectoralis` | Justicia pectoralis | alias de `dianthera-pectoralis` | Dianthera pectoralis | 22 → 32 | sinónimo homotípico del aceptado de WCVP |
| `justicia-procumbens` | Justicia procumbens | alias de `rostellularia-procumbens` | Rostellularia procumbens | 16 → 0 | sinónimo homotípico del aceptado de WCVP |
| `kalanchoe-daegrimontiana` | Kalanchoe daegrimontiana | alias de `kalanchoe-daigremontiana` | Kalanchoe daigremontiana | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `kalanchoe-spathulata` | Kalanchoe spathulata | alias de `kalanchoe-integra` | Kalanchoe integra | 0 → 4 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `krameria-triandra` | Krameria triandra | alias de `krameria-lappacea` | Krameria lappacea | 11 → 27 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lachnanthes-tinctoria` | Lachnanthes tinctoria | alias de `lachnanthes-caroliana` | Lachnanthes caroliana | 9 → 8 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lactuca-sativa-subsp-var-capitata` | Lactuca sativa subsp. var. capitata | alias de `lactuca-sativa-var-capitata` | Lactuca sativa var. capitata | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lactuca-scariola` | Lactuca scariola | alias de `lactuca-serriola` | Lactuca serriola | 15 → 15 | sinónimo homotípico del aceptado de WCVP |
| `lavandula-x-hybrida` | Lavandula x hybrida | alias de `lavandula-x-heterophylla` | Lavandula × heterophylla | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `ledum-palustre` | Ledum palustre | alias de `rhododendron-tomentosum` | Rhododendron tomentosum | 15 → 13 | sinónimo homotípico del aceptado de WCVP |
| `lemaireocereus-griseus` | Lemaireocereus griseus | alias de `stenocereus-griseus` | Stenocereus griseus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lemaireocereus-hystrix` | Lemaireocereus hystrix | alias de `stenocereus-heptagonus` | Stenocereus heptagonus | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lemaireocereus-quevedonis` | Lemaireocereus quevedonis | alias de `stenocereus-quevedonis` | Stenocereus quevedonis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lemaireocereus-stellatus` | Lemaireocereus stellatus | alias de `stenocereus-stellatus` | Stenocereus stellatus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lemaireocereus-thurberi` | Lemaireocereus thurberi | alias de `stenocereus-thurberi` | Stenocereus thurberi | 0 → 2 | sinónimo homotípico del aceptado de WCVP |
| `lembotropis-emerifolia` | Lembotropis emerifolia | alias de `cytisus-emeriflorus` | Cytisus emeriflorus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lens-culinaris` | Lens culinaris | alias de `vicia-lens` | Vicia lens | 2 → 4 | sinónimo homotípico del aceptado de WCVP |
| `leonotis-dysophylla` | Leonotis dysophylla | alias de `leonotis-ocymifolia-var-raineriana` | Leonotis ocymifolia var. raineriana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `leonotis-nepetaefolia` | Leonotis nepetaefolia | alias de `leonotis-nepetifolia` | Leonotis nepetifolia | 7 → 32 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `leonurus-heterophyllus` | Leonurus heterophyllus | alias de `paraleonurus-japonicus` | Paraleonurus japonicus | 11 → 18 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lepechinia-chamaedryoides` | Lepechinia chamaedryoides | alias de `lepechinia-chilensis` | Lepechinia chilensis | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lepechinia-schiediana` | Lepechinia schiediana | alias de `lepechinia-schiedeana` | Lepechinia schiedeana | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `lepechinia-urbanii` | Lepechinia urbanii | alias de `lepechinia-urbani` | Lepechinia urbani | 3 → 3 | variante ortográfica del nombre de WCVP |
| `leptospermum-ericoides` | Leptospermum ericoides | alias de `kunzea-ericoides` | Kunzea ericoides | 12 → 12 | sinónimo homotípico del aceptado de WCVP |
| `lespedeza-davidii` | Lespedeza davidii | alias de `lespedeza-davidi` | Lespedeza davidi | 0 → 0 | variante ortográfica del nombre de WCVP |
| `licania-platypus` | Licania platypus | alias de `moquilea-platypus` | Moquilea platypus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `licania-rigida` | Licania rigida | alias de `microdesmia-rigida` | Microdesmia rigida | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lippia-graveolens` | Lippia graveolens | alias de `lippia-origanoides` | Lippia origanoides | 4 → 14 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lithocarpus-attenuata` | Lithocarpus attenuata | alias de `lithocarpus-attenuatus` | Lithocarpus attenuatus | 0 → 0 | variante ortográfica del nombre de WCVP |
| `lithocarpus-cornea` | Lithocarpus cornea | alias de `lithocarpus-corneus` | Lithocarpus corneus | 0 → 0 | variante ortográfica del nombre de WCVP |
| `lithocarpus-polystachya` | Lithocarpus polystachya | alias de `lithocarpus-polystachyus` | Lithocarpus polystachyus | 0 → 0 | variante ortográfica del nombre de WCVP |
| `litsea-glaucescens-var-glaucescens` | Litsea glaucescens var. glaucescens | alias de `litsea-glaucescens` | Litsea glaucescens | 0 → 5 | infraespecífico o autónimo absorbido por la especie aceptada |
| `ludwigia-parviflora` | Ludwigia parviflora | alias de `ludwigia-perennis` | Ludwigia perennis | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: ludwigia-perennis (reviewFlag fusion-heterotipica) |
| `luisia-indivisa` | Luisia indivisa | alias de `luisia-brachystachys` | Luisia brachystachys | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lycopersicon-esculentum` | Lycopersicon esculentum | alias de `solanum-lycopersicum` | Solanum lycopersicum | 23 → 27 | sinónimo homotípico del aceptado de WCVP |
| `lycopodium-carolinianum` | Lycopodium carolinianum | alias de `lycopodiella-caroliniana` | Lycopodiella caroliniana | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: lycopodiella-caroliniana |
| `lycopodium-cernuum` | Lycopodium cernuum | alias de `lycopodiella-cernua` | Lycopodiella cernua | 10 → 19 | sinónimo homotípico del aceptado de WCVP |
| `lycopodium-erythraeum` | Lycopodium erythraeum | alias de `huperzia-crassa-var-crassa` | Huperzia crassa var. crassa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `lycopodium-gnidioides` | Lycopodium gnidioides | alias de `huperzia-gnidioides` | Huperzia gnidioides | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lycopodium-inundatum` | Lycopodium inundatum | alias de `lycopodiella-inundata` | Lycopodiella inundata | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: lycopodiella-inundata |
| `lycopodium-lucidulum` | Lycopodium lucidulum | alias de `huperzia-lucidula` | Huperzia lucidula | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lycopodium-selago` | Lycopodium selago | alias de `huperzia-selago` | Huperzia selago | 1 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lycopodium-serratum` | Lycopodium serratum | alias de `huperzia-serrata` | Huperzia serrata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lycopus-europeus` | Lycopus europeus | alias de `lycopus-europaeus` | Lycopus europaeus | 0 → 5 | variante ortográfica del nombre de WCVP |
| `lygos-monosperma` | Lygos monosperma | alias de `retama-monosperma` | Retama monosperma | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `lygos-raetum` | Lygos raetum | alias de `retama-raetam` | Retama raetam | 0 → 2 | sinónimo homotípico del aceptado de WCVP |
| `macfadyena-uncata` | Macfadyena uncata | alias de `dolichandra-uncata` | Dolichandra uncata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `machaerocereus-gummosus` | Machaerocereus gummosus | alias de `stenocereus-gummosus` | Stenocereus gummosus | 2 → 2 | sinónimo homotípico del aceptado de WCVP |
| `macroptylium-atropurpureum` | Macroptylium atropurpureum | alias de `macroptilium-atropurpureum` | Macroptilium atropurpureum | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `macroptylium-bracteatum` | Macroptylium bracteatum | alias de `macroptilium-bracteatum` | Macroptilium bracteatum | 0 → 1 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `macroptylium-lathyroides` | Macroptylium lathyroides | alias de `macroptilium-lathyroides` | Macroptilium lathyroides | 0 → 3 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `macroptylium-martii` | Macroptylium martii | alias de `macroptilium-martii` | Macroptilium martii | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `macrotyloma-uniflora` | Macrotyloma uniflora | alias de `macrotyloma-uniflorum` | Macrotyloma uniflorum | 0 → 0 | variante ortográfica del nombre de WCVP |
| `madhuca-nerifolia` | Madhuca nerifolia | alias de `madhuca-neriifolia` | Madhuca neriifolia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `magnolia-fargesii` | Magnolia fargesii | alias de `magnolia-biondii` | Magnolia biondii | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `mahonia-aquifolium` | Mahonia aquifolium | alias de `berberis-aquifolium` | Berberis aquifolium | 3 → 12 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: berberis-aquifolium |
| `mahonia-bealei` | Mahonia bealei | alias de `berberis-bealei` | Berberis bealei | 10 → 11 | sinónimo homotípico del aceptado de WCVP |
| `mahonia-fargesii` | Mahonia fargesii | alias de `berberis-sheridaniana` | Berberis sheridaniana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `mahonia-fortunei` | Mahonia fortunei | alias de `berberis-fortunei` | Berberis fortunei | 1 → 1 | sinónimo homotípico del aceptado de WCVP |
| `mahonia-gracilipes` | Mahonia gracilipes | alias de `berberis-gracilipes` | Berberis gracilipes | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `mahonia-japonica` | Mahonia japonica | alias de `berberis-japonica` | Berberis japonica | 13 → 13 | sinónimo homotípico del aceptado de WCVP |
| `mahonia-nervosa` | Mahonia nervosa | alias de `berberis-nervosa` | Berberis nervosa | 0 → 4 | sinónimo homotípico del aceptado de WCVP |
| `mahonia-philipinensis` | Mahonia philipinensis | alias de `berberis-philippinensis` | Berberis philippinensis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `mahonia-repens` | Mahonia repens | alias de `berberis-repens` | Berberis repens | 4 → 12 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: berberis-repens |
| `mahonia-siamensis` | Mahonia siamensis | alias de `berberis-napaulensis-var-napaulensis` | Berberis napaulensis var. napaulensis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `malachra-alaceaefolia` | Malachra alaceaefolia | ausente |  | 0 → 0 | Sin datos en ninguna fuente y sin resolución en WCVP/WFO; fuera de la semilla (tools/catalog-seed/README.md, estado final) |
| `marsdenia-reichenbachii` | Marsdenia reichenbachii | alias de `ruehssia-cundurango-subsp-cundurango` | Ruehssia cundurango subsp. cundurango | 1 → 6 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `matricaria-recutita` | Matricaria recutita | alias de `matricaria-chamomilla` | Matricaria chamomilla | 0 → 40 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `matteuccia-pennsylvanica` | Matteuccia pennsylvanica | alias de `onoclea-pensylvanica` | Onoclea pensylvanica | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `maytenus-canariensis` | Maytenus canariensis | alias de `gymnosporia-cassinoides` | Gymnosporia cassinoides | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `maytenus-octogona` | Maytenus octogona | alias de `maytenus-orbicularis` | Maytenus orbicularis | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `maytenus-senegalensis` | Maytenus senegalensis | alias de `gymnosporia-senegalensis` | Gymnosporia senegalensis | 25 → 24 | sinónimo homotípico del aceptado de WCVP |
| `medicago-sativa-subsp-sativa` | Medicago sativa subsp. sativa | alias de `medicago-sativa` | Medicago sativa | 0 → 12 | infraespecífico o autónimo absorbido por la especie aceptada |
| `melaleuca-leucadendron` | Melaleuca leucadendron | alias de `melaleuca-leucadendra` | Melaleuca leucadendra | 19 → 33 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: melaleuca-leucadendra |
| `meleleuca-howeana` | Meleleuca howeana | alias de `melaleuca-howeana` | Melaleuca howeana | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `melicoccus-bijugatas` | Melicoccus bijugatas | alias de `melicoccus-bijugatus` | Melicoccus bijugatus | 0 → 1 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `melilotus-alba` | Melilotus alba | alias de `melilotus-albus` | Melilotus albus | 1 → 4 | variante ortográfica del nombre de WCVP |
| `melilotus-indica` | Melilotus indica | alias de `melilotus-indicus` | Melilotus indicus | 2 → 3 | variante ortográfica del nombre de WCVP |
| `mentha-arvensis-var-piperascens` | Mentha arvensis var. piperascens | alias de `mentha-canadensis` | Mentha canadensis | 0 → 5 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `mentha-rotundifolia` | Mentha rotundifolia | alias de `mentha-x-rotundifolia` | Mentha × rotundifolia | 2 → 6 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: mentha-x-rotundifolia |
| `mentha-x-piperita-subsp-nothosubsp-piperita` | Mentha x piperita subsp. nothosubsp. piperita | alias de `mentha-x-piperita` | Mentha × piperita | 0 → 31 | infraespecífico o autónimo absorbido por la especie aceptada |
| `mesua-myrtifolia` | Mesua myrtifolia | alias de `kayea-myrtifolia` | Kayea myrtifolia | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `michelia-alba` | Michelia alba | alias de `magnolia-x-alba` | Magnolia × alba | 0 → 4 | sinónimo homotípico del aceptado de WCVP |
| `michelia-champaca` | Michelia champaca | alias de `magnolia-champaca` | Magnolia champaca | 13 → 31 | sinónimo homotípico del aceptado de WCVP |
| `micromeria-congesta` | Micromeria congesta | alias de `clinopodium-congestum` | Clinopodium congestum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `micromeria-fruticosa` | Micromeria fruticosa | alias de `clinopodium-serpyllifolium-subsp-fruticosum` | Clinopodium serpyllifolium subsp. fruticosum | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `micromeria-fruticosa-subsp-barbata` | Micromeria fruticosa subsp. barbata | alias de `clinopodium-barbatum` | Clinopodium barbatum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `micromeria-thymifolia` | Micromeria thymifolia | alias de `clinopodium-album` | Clinopodium album | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `micromeria-varia-subsp-thymoides` | Micromeria varia subsp. thymoides | alias de `micromeria-maderensis` | Micromeria maderensis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `mimosa-hostilis` | Mimosa hostilis | alias de `mimosa-tenuiflora` | Mimosa tenuiflora | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `mimusops-littoralis` | Mimusops littoralis | alias de `manilkara-littoralis` | Manilkara littoralis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `mitracarpus-scaber` | Mitracarpus scaber | alias de `mitracarpus-hirtus` | Mitracarpus hirtus | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `moldavica-parviflora` | Moldavica parviflora | alias de `physostegia-parviflora` | Physostegia parviflora | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `moldavica-thymiflora` | Moldavica thymiflora | alias de `dracocephalum-thymiflorum` | Dracocephalum thymiflorum | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: dracocephalum-thymiflora |
| `mucuna-deeringiana` | Mucuna deeringiana | alias de `mucuna-pruriens-var-utilis` | Mucuna pruriens var. utilis | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: stizolobium-deeringianum |
| `mucuna-pruriens-subsp-utilis` | Mucuna pruriens subsp. utilis | alias de `mucuna-pruriens` | Mucuna pruriens | 0 → 39 | infraespecífico o autónimo absorbido por la especie aceptada; se fusiona con otros: mucuna-pruriens |
| `murraya-koenigii` | Murraya koenigii | alias de `bergera-koenigii` | Bergera koenigii | 1 → 11 | sinónimo homotípico del aceptado de WCVP |
| `myrciaria-cauliflora` | Myrciaria cauliflora | alias de `plinia-cauliflora` | Plinia cauliflora | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `nardostachys-chinensis` | Nardostachys chinensis | alias de `nardostachys-jatamansi` | Nardostachys jatamansi | 0 → 42 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: nardostachys-jatamansi (reviewFlag fusion-heterotipica) |
| `nepeta-cilicia` | Nepeta cilicia | alias de `nepeta-cilicica` | Nepeta cilicica | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `neuracanthus-sphaerostachys` | Neuracanthus sphaerostachys | alias de `neuracanthus-sphaerostachyus` | Neuracanthus sphaerostachyus | 0 → 2 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `newcastelia-viscida` | Newcastelia viscida | alias de `apatelantha-viscida` | Apatelantha viscida | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `notopterygium-incisum` | Notopterygium incisum | alias de `hansenia-weberbaueriana` | Hansenia weberbaueriana | 0 → 6 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `nymphoides-peltatum` | Nymphoides peltatum | alias de `nymphoides-peltata` | Nymphoides peltata | 0 → 15 | variante ortográfica del nombre de WCVP |
| `ocimum-canum` | Ocimum canum | alias de `ocimum-americanum` | Ocimum americanum | 6 → 35 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: ocimum-americanum (reviewFlag fusion-heterotipica) |
| `ocimum-sanctum` | Ocimum sanctum | alias de `ocimum-tenuiflorum` | Ocimum tenuiflorum | 8 → 31 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: ocimum-tenuiflorum (reviewFlag fusion-heterotipica) |
| `ocimum-suave` | Ocimum suave | alias de `ocimum-gratissimum-subsp-gratissimum` | Ocimum gratissimum subsp. gratissimum | 0 → 9 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `olea-europaea-subsp-europaea` | Olea europaea subsp. europaea | alias de `olea-europaea` | Olea europaea | 0 → 23 | infraespecífico o autónimo absorbido por la especie aceptada |
| `origanum-vulgare-var-gracile` | Origanum vulgare var. gracile | alias de `origanum-vulgare` | Origanum vulgare | 0 → 27 | infraespecífico o autónimo absorbido por la especie aceptada; se fusiona con otros: origanum-vulgare |
| `origanum-vulgare-var-viride` | Origanum vulgare var. viride | alias de `origanum-vulgare-subsp-viridulum` | Origanum vulgare subsp. viridulum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `pachira-macrocarpa` | Pachira macrocarpa | alias de `pachira-aquatica` | Pachira aquatica | 4 → 6 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: pachira-aquatica (reviewFlag fusion-heterotipica) |
| `paeonia-japonica` | Paeonia japonica | alias de `paeonia-obovata-subsp-japonica` | Paeonia obovata subsp. japonica | 4 → 4 | sinónimo homotípico del aceptado de WCVP |
| `paeonia-moutan` | Paeonia moutan | alias de `paeonia-x-suffruticosa` | Paeonia × suffruticosa | 15 → 25 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: paeonia-suffruticosa (reviewFlag fusion-heterotipica) |
| `paeonia-suffruticosa` | Paeonia suffruticosa | alias de `paeonia-x-suffruticosa` | Paeonia × suffruticosa | 8 → 25 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: paeonia-moutan (reviewFlag fusion-heterotipica) |
| `panicum-maximum` | Panicum maximum | alias de `megathyrsus-maximus` | Megathyrsus maximus | 3 → 4 | sinónimo homotípico del aceptado de WCVP |
| `passiflora-mollissima` | Passiflora mollissima | alias de `passiflora-tripartita-var-mollissima` | Passiflora tripartita var. mollissima | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `paullinia-yoko` | Paullinia yoko | alias de `paullinia-yoco` | Paullinia yoco | 0 → 2 | variante ortográfica del nombre de WCVP |
| `pausinystalia-johimbe` | Pausinystalia johimbe | alias de `corynanthe-johimbe` | Corynanthe johimbe | 2 → 3 | sinónimo homotípico del aceptado de WCVP |
| `pavonia-odorata` | Pavonia odorata | alias de `pavonia-zeylonica` | Pavonia zeylonica | 1 → 10 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `pelargonium-citrosum` | Pelargonium citrosum | alias de `pelargonium-graveolens` | Pelargonium graveolens | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: pelargonium-graveolens (reviewFlag fusion-heterotipica) |
| `pelargonium-roseum` | Pelargonium roseum | alias de `pelargonium-radens` | Pelargonium radens | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `peperomia-pelucida` | Peperomia pelucida | alias de `peperomia-pellucida` | Peperomia pellucida | 0 → 29 | variante ortográfica del nombre de WCVP |
| `peucedanum-decursivum` | Peucedanum decursivum | alias de `angelica-decursiva` | Angelica decursiva | 23 → 29 | sinónimo homotípico del aceptado de WCVP |
| `pfaffia-paniculata` | Pfaffia paniculata | alias de `hebanthe-erianthos` | Hebanthe erianthos | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `phaseolus-aborigineus` | Phaseolus aborigineus | alias de `phaseolus-vulgaris` | Phaseolus vulgaris | 0 → 22 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: phaseolus-vulgaris-subsp-var-vulgaris (reviewFlag fusion-heterotipica) |
| `phaseolus-vulgaris-subsp-var-vulgaris` | Phaseolus vulgaris subsp. var. vulgaris | alias de `phaseolus-vulgaris` | Phaseolus vulgaris | 0 → 22 | infraespecífico o autónimo absorbido por la especie aceptada; se fusiona con otros: phaseolus-aborigineus (reviewFlag fusion-heterotipica) |
| `phlogacanthus-thyrsiflorus` | Phlogacanthus thyrsiflorus | alias de `phlogacanthus-thyrsiformis` | Phlogacanthus thyrsiformis | 0 → 9 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `phoradendron-serotinum` | Phoradendron serotinum | alias de `phoradendron-leucarpum` | Phoradendron leucarpum | 1 → 6 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `phyllanthus-discoideus` | Phyllanthus discoideus | alias de `margaritaria-discoidea` | Margaritaria discoidea | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `physalis-alkekingi` | Physalis alkekingi | alias de `alkekengi-officinarum` | Alkekengi officinarum | 0 → 27 | sinónimo homotípico del aceptado de WCVP |
| `picea-glauca` | Picea glauca | alias de `picea-laxa` | Picea laxa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `pinus-insularis` | Pinus insularis | alias de `pinus-kesiya-var-langbianensis` | Pinus kesiya var. langbianensis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `pinus-walliciana` | Pinus walliciana | alias de `pinus-wallichiana` | Pinus wallichiana | 0 → 1 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `piper-angustifolium` | Piper angustifolium | alias de `piper-aduncum-var-aduncum` | Piper aduncum var. aduncum | 24 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `piper-betel` | Piper betel | alias de `piper-betle` | Piper betle | 50 → 49 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `piptanthus-nanus` | Piptanthus nanus | alias de `ammopiptanthus-nanus` | Ammopiptanthus nanus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `piscidia-erythrina` | Piscidia erythrina | alias de `piscidia-piscipula` | Piscidia piscipula | 12 → 46 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: piscidia-piscipula |
| `pisum-sativum` | Pisum sativum | alias de `lathyrus-oleraceus` | Lathyrus oleraceus | 11 → 15 | sinónimo homotípico del aceptado de WCVP |
| `plantago-psyllium` | Plantago psyllium | alias de `plantago-arenaria` | Plantago arenaria | 9 → 9 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `platanus-accrifolia` | Platanus accrifolia | alias de `platanus-x-hispanica` | Platanus × hispanica | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: platanus-acerifolia |
| `platanus-acerifolia` | Platanus acerifolia | alias de `platanus-x-hispanica` | Platanus × hispanica | 2 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: platanus-accrifolia |
| `platanus-vulgaris` | Platanus vulgaris | alias de `platanus-orientalis` | Platanus orientalis | 0 → 8 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: platanus-orientalis |
| `platycodon-grandiflorum` | Platycodon grandiflorum | alias de `platycodon-grandiflorus` | Platycodon grandiflorus | 25 → 31 | variante ortográfica del nombre de WCVP |
| `plectranthus-amboinicus` | Plectranthus amboinicus | alias de `coleus-amboinicus` | Coleus amboinicus | 0 → 32 | sinónimo homotípico del aceptado de WCVP |
| `plectranthus-barbatus` | Plectranthus barbatus | alias de `coleus-barbatus` | Coleus barbatus | 0 → 0 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: coleus-barbatus |
| `plectranthus-coleoides` | Plectranthus coleoides | alias de `coleus-paniculatus` | Coleus paniculatus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `plectranthus-incanus` | Plectranthus incanus | alias de `equilabium-molle` | Equilabium molle | 0 → 5 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `plectranthus-rugosus` | Plectranthus rugosus | alias de `isodon-rugosus` | Isodon rugosus | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `plectranthus-trichocarpus` | Plectranthus trichocarpus | alias de `isodon-trichocarpus` | Isodon trichocarpus | 2 → 2 | sinónimo homotípico del aceptado de WCVP |
| `plumeria-acutifolia` | Plumeria acutifolia | alias de `plumeria-rubra` | Plumeria rubra | 22 → 39 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `podocarpus-koordersii` | Podocarpus koordersii | alias de `podocarpus-rumphii` | Podocarpus rumphii | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `polygala-penaea` | Polygala penaea | alias de `badiera-penaea` | Badiera penaea | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `polygala-senega` | Polygala senega | alias de `senega-officinalis` | Senega officinalis | 11 → 18 | sinónimo homotípico del aceptado de WCVP |
| `polygonum-hydropiper` | Polygonum hydropiper | alias de `persicaria-hydropiper` | Persicaria hydropiper | 24 → 24 | sinónimo homotípico del aceptado de WCVP |
| `polygonum-hydropiperoides` | Polygonum hydropiperoides | alias de `persicaria-hydropiperoides` | Persicaria hydropiperoides | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `polygonum-multiflorum` | Polygonum multiflorum | alias de `pleuropterus-multiflorus` | Pleuropterus multiflorus | 36 → 29 | sinónimo homotípico del aceptado de WCVP |
| `polymnia-edulis` | Polymnia edulis | alias de `smallanthus-sonchifolius` | Smallanthus sonchifolius | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `polypodium-aureum` | Polypodium aureum | alias de `phlebodium-aureum` | Phlebodium aureum | 9 → 10 | sinónimo homotípico del aceptado de WCVP |
| `polystichum-polyblepharum` | Polystichum polyblepharum | alias de `polystichum-luctuosum` | Polystichum luctuosum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `populus-tacamahacca` | Populus tacamahacca | alias de `populus-balsamifera` | Populus balsamifera | 0 → 20 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: populus-balsamifera (reviewFlag fusion-heterotipica) |
| `porteresia-coarctata` | Porteresia coarctata | alias de `oryza-coarctata` | Oryza coarctata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `pourouma-cecropiaefolia` | Pourouma cecropiaefolia | alias de `pourouma-cecropiifolia` | Pourouma cecropiifolia | 0 → 2 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `pouteria-campechiana` | Pouteria campechiana | alias de `lucuma-campechiana` | Lucuma campechiana | 0 → 8 | sinónimo homotípico del aceptado de WCVP |
| `premna-integrifolia` | Premna integrifolia | alias de `premna-serratifolia` | Premna serratifolia | 1 → 25 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `prosopis-glandulosa` | Prosopis glandulosa | alias de `neltuma-glandulosa` | Neltuma glandulosa | 0 → 12 | sinónimo homotípico del aceptado de WCVP |
| `prosopis-juliflora` | Prosopis juliflora | alias de `neltuma-juliflora` | Neltuma juliflora | 25 → 25 | sinónimo homotípico del aceptado de WCVP |
| `prunus-aequinoctialis` | Prunus aequinoctialis | alias de `prunus-itosakura` | Prunus itosakura | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `prunus-dulcis` | Prunus dulcis | alias de `prunus-amygdalus` | Prunus amygdalus | 17 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `prunus-salicifolia` | Prunus salicifolia | alias de `prunus-serotina-var-salicifolia` | Prunus serotina var. salicifolia | 0 → 14 | sinónimo homotípico del aceptado de WCVP |
| `prunus-serotina-subsp-serotina` | Prunus serotina subsp. serotina | alias de `prunus-serotina` | Prunus serotina | 0 → 28 | infraespecífico o autónimo absorbido por la especie aceptada |
| `prunus-verecunda` | Prunus verecunda | alias de `prunus-leveilleana` | Prunus leveilleana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `pseudelephantopus-spicatus-juss-gleason` | Pseudelephantopus spicatus (juss.) gleason | alias de `pseudelephantopus-spicatus` | Pseudelephantopus spicatus | 0 → 22 | infraespecífico o autónimo absorbido por la especie aceptada |
| `psidium-cattleianum` | Psidium cattleianum | alias de `psidium-cattleyanum` | Psidium cattleyanum | 0 → 0 | variante ortográfica del nombre de WCVP |
| `psoralea-corylifolia` | Psoralea corylifolia | alias de `cullen-corylifolium` | Cullen corylifolium | 32 → 35 | sinónimo homotípico del aceptado de WCVP |
| `psoralea-esculenta` | Psoralea esculenta | alias de `pediomelum-esculentum` | Pediomelum esculentum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `pterospermum-lanceaefolium` | Pterospermum lanceaefolium | alias de `pterospermum-lanceifolium` | Pterospermum lanceifolium | 0 → 1 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `pueraria-montana-subsp-var-lobata` | Pueraria montana subsp. var. lobata | alias de `pueraria-montana-var-lobata` | Pueraria montana var. lobata | 0 → 37 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: pueraria-pseudohirsuta (reviewFlag fusion-heterotipica) |
| `pueraria-phaseoloides` | Pueraria phaseoloides | alias de `neustanthus-phaseoloides` | Neustanthus phaseoloides | 0 → 2 | sinónimo homotípico del aceptado de WCVP |
| `pueraria-pseudohirsuta` | Pueraria pseudohirsuta | alias de `pueraria-montana-var-lobata` | Pueraria montana var. lobata | 8 → 37 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: pueraria-montana-subsp-var-lobata (reviewFlag fusion-heterotipica) |
| `pulicaria-salviaefolia` | Pulicaria salviaefolia | alias de `pulicaria-salviifolia` | Pulicaria salviifolia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `putoria-calabrica` | Putoria calabrica | alias de `plocama-calabrica` | Plocama calabrica | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `pycnanthemum-pilosum` | Pycnanthemum pilosum | alias de `pycnanthemum-verticillatum-var-pilosum` | Pycnanthemum verticillatum var. pilosum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `pygeum-acuminatum` | Pygeum acuminatum | alias de `prunus-ceylanica` | Prunus ceylanica | 0 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `quararibea-cordata` | Quararibea cordata | alias de `matisia-cordata` | Matisia cordata | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `quercus-bambusaefolia` | Quercus bambusaefolia | alias de `quercus-bambusifolia` | Quercus bambusifolia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `quercus-championi` | Quercus championi | alias de `quercus-championii` | Quercus championii | 0 → 0 | variante ortográfica del nombre de WCVP |
| `quercus-myrsinaefolia` | Quercus myrsinaefolia | alias de `quercus-myrsinifolia` | Quercus myrsinifolia | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `quisqualis-indica` | Quisqualis indica | alias de `combretum-indicum` | Combretum indicum | 16 → 34 | sinónimo homotípico del aceptado de WCVP |
| `rabdosia-adenantha` | Rabdosia adenantha | alias de `isodon-adenanthus` | Isodon adenanthus | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `raphanus-sativus` | Raphanus sativus | alias de `raphanus-raphanistrum-subsp-sativus` | Raphanus raphanistrum subsp. sativus | 48 → 38 | sinónimo homotípico del aceptado de WCVP |
| `ravensara-aromatica` | Ravensara aromatica | alias de `cryptocarya-agathophylla` | Cryptocarya agathophylla | 2 → 2 | sinónimo homotípico del aceptado de WCVP |
| `rhamnus-purshiana` | Rhamnus purshiana | alias de `frangula-purshiana` | Frangula purshiana | 6 → 16 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: frangula-purshiana |
| `rheedia-gardneriana` | Rheedia gardneriana | alias de `garcinia-gardneriana` | Garcinia gardneriana | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `rhododendron-ledebourii` | Rhododendron ledebourii | alias de `rhododendron-dauricum` | Rhododendron dauricum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: rhododendron-dauricum (reviewFlag fusion-heterotipica) |
| `rhododendron-schotense` | Rhododendron schotense | alias de `rhododendron-sichotense` | Rhododendron sichotense | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `rhoeo-spathacea` | Rhoeo spathacea | alias de `tradescantia-spathacea` | Tradescantia spathacea | 4 → 5 | sinónimo homotípico del aceptado de WCVP |
| `rhus-alata` | Rhus alata | alias de `hippobromus-pauciflorus` | Hippobromus pauciflorus | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `rhus-copallina` | Rhus copallina | alias de `rhus-copallinum` | Rhus copallinum | 4 → 4 | variante ortográfica del nombre de WCVP |
| `rhus-toxicodendron` | Rhus toxicodendron | alias de `toxicodendron-pubescens` | Toxicodendron pubescens | 1 → 1 | sinónimo homotípico del aceptado de WCVP |
| `rhynchosia-cabibaea` | Rhynchosia cabibaea | alias de `rhynchosia-caribaea` | Rhynchosia caribaea | 0 → 2 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `rivea-corymbosa` | Rivea corymbosa | alias de `ipomoea-corymbosa` | Ipomoea corymbosa | 7 → 21 | sinónimo homotípico del aceptado de WCVP |
| `rollinia-mucosa` | Rollinia mucosa | alias de `annona-mucosa` | Annona mucosa | 1 → 1 | sinónimo homotípico del aceptado de WCVP |
| `rosa-centifolia` | Rosa centifolia | alias de `rosa-x-centifolia` | Rosa × centifolia | 8 → 14 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `rosa-damascena` | Rosa damascena | alias de `rosa-x-damascena` | Rosa × damascena | 10 → 10 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `rosmarinus-eriocalyx` | Rosmarinus eriocalyx | alias de `salvia-jordanii` | Salvia jordanii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `rosmarinus-officinalis` | Rosmarinus officinalis | alias de `salvia-rosmarinus` | Salvia rosmarinus | 59 → 33 | sinónimo homotípico del aceptado de WCVP |
| `rosmarinus-tomentosus` | Rosmarinus tomentosus | alias de `salvia-granatensis` | Salvia granatensis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `rosmarinus-x-lavandulaceus` | Rosmarinus x lavandulaceus | alias de `salvia-x-lavandulacea` | Salvia × lavandulacea | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `rosmarinus-x-mendizabalii` | Rosmarinus x mendizabalii | alias de `salvia-x-mendizabalii` | Salvia × mendizabalii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `roylea-elegans` | Roylea elegans | alias de `roylea-cinerea` | Roylea cinerea | 0 → 4 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `salvia-africana-lutea` | Salvia africana-lutea | alias de `salvia-aurea` | Salvia aurea | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `salvia-chinopeplica` | Salvia chinopeplica | alias de `salvia-chionopeplica` | Salvia chionopeplica | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `salvia-gilliesii` | Salvia gilliesii | alias de `salvia-cuspidata-subsp-gilliesii` | Salvia cuspidata subsp. gilliesii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `salvia-triloba` | Salvia triloba | alias de `salvia-fruticosa` | Salvia fruticosa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP (reviewFlag fusion-heterotipica) |
| `sambucus-simpsonii` | Sambucus simpsonii | alias de `sambucus-canadensis` | Sambucus canadensis | 3 → 41 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: sambucus-canadensis (reviewFlag fusion-heterotipica) |
| `sansevieria-trifasciata` | Sansevieria trifasciata | alias de `dracaena-trifasciata` | Dracaena trifasciata | 2 → 11 | sinónimo homotípico del aceptado de WCVP |
| `sarcostemma-acidum` | Sarcostemma acidum | alias de `cynanchum-viminale-subsp-viminale` | Cynanchum viminale subsp. viminale | 0 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `sarracenia-rubra-subsp-subsp-jonesii` | Sarracenia rubra subsp. subsp. jonesii | alias de `sarracenia-jonesii` | Sarracenia jonesii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `sarracenia-rubra-subsp-subsp-wherryi` | Sarracenia rubra subsp. subsp. wherryi | alias de `sarracenia-alabamensis-subsp-wherryi` | Sarracenia alabamensis subsp. wherryi | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `satureja-douglasii` | Satureja douglasii | alias de `clinopodium-douglasii` | Clinopodium douglasii | 0 → 3 | sinónimo homotípico del aceptado de WCVP |
| `satureja-glabella` | Satureja glabella | alias de `clinopodium-glabellum` | Clinopodium glabellum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `satureja-grandiflora` | Satureja grandiflora | alias de `clinopodium-grandiflorum` | Clinopodium grandiflorum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `satureja-obovata` | Satureja obovata | alias de `satureja-cuneifolia` | Satureja cuneifolia | 1 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: satureja-cuneifolia (reviewFlag fusion-heterotipica) |
| `satureja-odora` | Satureja odora | alias de `clinopodium-odorum` | Clinopodium odorum | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `satureja-parvifolia` | Satureja parvifolia | alias de `clinopodium-gilliesii` | Clinopodium gilliesii | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `satureja-vulgaris` | Satureja vulgaris | alias de `clinopodium-vulgare` | Clinopodium vulgare | 2 → 4 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: clinopodium-vulgare |
| `saussurea-lappa` | Saussurea lappa | alias de `dolomiaea-costus` | Dolomiaea costus | 33 → 28 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `schefflera-octophylla` | Schefflera octophylla | alias de `heptapleurum-heptaphyllum` | Heptapleurum heptaphyllum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `schefflera-venulosa` | Schefflera venulosa | alias de `heptapleurum-venulosum` | Heptapleurum venulosum | 0 → 1 | sinónimo homotípico del aceptado de WCVP |
| `schinus-terebinthifolius` | Schinus terebinthifolius | alias de `schinus-terebinthifolia` | Schinus terebinthifolia | 4 → 20 | variante ortográfica del nombre de WCVP |
| `schizonepeta-tenuifolia` | Schizonepeta tenuifolia | alias de `nepeta-tenuifolia` | Nepeta tenuifolia | 0 → 12 | sinónimo homotípico del aceptado de WCVP |
| `scirpus-fluviatilis` | Scirpus fluviatilis | alias de `bolboschoenus-fluviatilis` | Bolboschoenus fluviatilis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `sclerocarya-caffra` | Sclerocarya caffra | alias de `sclerocarya-birrea-subsp-afra` | Sclerocarya birrea subsp. afra | 1 → 4 | sinónimo homotípico del aceptado de WCVP |
| `scrophularia-umbrosa` | Scrophularia umbrosa | alias de `scrophularia-oblongifolia` | Scrophularia oblongifolia | 0 → 9 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `scutellaria-churchilliana` | Scutellaria churchilliana | alias de `scutellaria-x-churchilliana` | Scutellaria × churchilliana | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `scutellaria-epilobifolia` | Scutellaria epilobifolia | alias de `scutellaria-galericulata` | Scutellaria galericulata | 0 → 19 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: scutellaria-galericulata (reviewFlag fusion-heterotipica) |
| `scutellaria-polydon` | Scutellaria polydon | alias de `scutellaria-caucasica` | Scutellaria caucasica | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `sechium-edule` | Sechium edule | alias de `sicyos-edulis` | Sicyos edulis | 8 → 9 | sinónimo homotípico del aceptado de WCVP |
| `senecio-aureus` | Senecio aureus | alias de `packera-aurea` | Packera aurea | 17 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-affinis` | Shorea affinis | alias de `doona-affinis` | Doona affinis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-congestiflora` | Shorea congestiflora | alias de `doona-congestiflora` | Doona congestiflora | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-dyerii` | Shorea dyerii | alias de `shorea-dyeri` | Shorea dyeri | 0 → 0 | variante ortográfica del nombre de WCVP |
| `shorea-magistophylla` | Shorea magistophylla | alias de `doona-macrophylla` | Doona macrophylla | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-ovalifolia` | Shorea ovalifolia | alias de `doona-ovalifolia` | Doona ovalifolia | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-stipularvis` | Shorea stipularvis | alias de `anthoshorea-stipularis` | Anthoshorea stipularis | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-trapezifolia` | Shorea trapezifolia | alias de `doona-trapezifolia` | Doona trapezifolia | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `shorea-zeylanica` | Shorea zeylanica | alias de `doona-zeylanica` | Doona zeylanica | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `sideritis-athoa` | Sideritis athoa | alias de `sideritis-perfoliata-subsp-athoa` | Sideritis perfoliata subsp. athoa | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `sideritis-mugronensis` | Sideritis mugronensis | alias de `sideritis-tragoriganum-subsp-tragoriganum` | Sideritis tragoriganum subsp. tragoriganum | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `sideritis-tomentosa` | Sideritis tomentosa | alias de `sideritis-hirsuta` | Sideritis hirsuta | 0 → 1 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `siegesbeckia-orientalis` | Siegesbeckia orientalis | alias de `sigesbeckia-orientalis` | Sigesbeckia orientalis | 50 → 32 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `simaba-cedron` | Simaba cedron | alias de `homalolepis-cedron` | Homalolepis cedron | 12 → 18 | sinónimo homotípico del aceptado de WCVP |
| `simaba-cuspidata` | Simaba cuspidata | alias de `simaba-guianensis-subsp-guianensis` | Simaba guianensis subsp. guianensis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `simaba-morettii` | Simaba morettii | alias de `homalolepis-morettii` | Homalolepis morettii | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `simaba-multiflora` | Simaba multiflora | alias de `simaba-orinocensis` | Simaba orinocensis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `smilax-regelii` | Smilax regelii | alias de `smilax-ornata` | Smilax ornata | 9 → 12 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `solanum-quitoensis` | Solanum quitoensis | alias de `solanum-quitoense` | Solanum quitoense | 0 → 1 | variante ortográfica del nombre de WCVP |
| `sophora-angustifolia` | Sophora angustifolia | alias de `sophora-flavescens-var-flavescens` | Sophora flavescens var. flavescens | 10 → 10 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `sophora-japonica` | Sophora japonica | alias de `styphnolobium-japonicum` | Styphnolobium japonicum | 35 → 23 | sinónimo homotípico del aceptado de WCVP |
| `sophora-secundiflora` | Sophora secundiflora | alias de `dermatophyllum-secundiflorum` | Dermatophyllum secundiflorum | 8 → 8 | sinónimo homotípico del aceptado de WCVP |
| `sophora-subprostrata` | Sophora subprostrata | alias de `sophora-tonkinensis-var-tonkinensis` | Sophora tonkinensis var. tonkinensis | 1 → 11 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `sorbus-aucubaria` | Sorbus aucubaria | alias de `sorbus-aucuparia` | Sorbus aucuparia | 0 → 13 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `spermacoce-assurgens` | Spermacoce assurgens | alias de `spermacoce-remota` | Spermacoce remota | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `stachys-officinalis` | Stachys officinalis | alias de `betonica-officinalis` | Betonica officinalis | 11 → 11 | sinónimo homotípico del aceptado de WCVP |
| `stachys-sieboldii` | Stachys sieboldii | alias de `stachys-affinis` | Stachys affinis | 1 → 3 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `stephania-glabra` | Stephania glabra | alias de `stephania-rotunda` | Stephania rotunda | 0 → 19 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `stephania-tetrandra` | Stephania tetrandra | alias de `botryodiscia-tetrandra` | Botryodiscia tetrandra | 0 → 6 | sinónimo homotípico del aceptado de WCVP |
| `stizolobium-deeringianum` | Stizolobium deeringianum | alias de `mucuna-pruriens-var-utilis` | Mucuna pruriens var. utilis | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: mucuna-deeringiana |
| `strophostyles-helvula` | Strophostyles helvula | alias de `strophostyles-helvola` | Strophostyles helvola | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `sweetia-panamensis` | Sweetia panamensis | alias de `leptolobium-panamense` | Leptolobium panamense | 2 → 5 | sinónimo homotípico del aceptado de WCVP |
| `swertia-chirata` | Swertia chirata | alias de `swertia-chirayita` | Swertia chirayita | 9 → 29 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `syncarpia-laurifolia` | Syncarpia laurifolia | alias de `syncarpia-glomulifera-subsp-glomulifera` | Syncarpia glomulifera subsp. glomulifera | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `syzgium-claviflorum` | Syzgium claviflorum | alias de `syzygium-claviflorum` | Syzygium claviflorum | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: syzygium-claviflorum |
| `tabebuia-avellanedae` | Tabebuia avellanedae | alias de `handroanthus-impetiginosus` | Handroanthus impetiginosus | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: tabebuia-impetiginosa,tabebuia-palmeri (reviewFlag fusion-heterotipica) |
| `tabebuia-heptaphylla` | Tabebuia heptaphylla | alias de `handroanthus-heptaphyllus` | Handroanthus heptaphyllus | 0 → 3 | sinónimo homotípico del aceptado de WCVP |
| `tabebuia-impetiginosa` | Tabebuia impetiginosa | alias de `handroanthus-impetiginosus` | Handroanthus impetiginosus | 0 → 2 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: tabebuia-avellanedae,tabebuia-palmeri (reviewFlag fusion-heterotipica) |
| `tabebuia-palmeri` | Tabebuia palmeri | alias de `handroanthus-impetiginosus` | Handroanthus impetiginosus | 0 → 2 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: tabebuia-avellanedae,tabebuia-impetiginosa (reviewFlag fusion-heterotipica) |
| `tacca-aspera` | Tacca aspera | alias de `tacca-integrifolia` | Tacca integrifolia | 0 → 6 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `tagetes-florida` | Tagetes florida | alias de `tagetes-lucida` | Tagetes lucida | 5 → 22 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: tagetes-lucida (reviewFlag fusion-heterotipica) |
| `talguenea-quinquenervis` | Talguenea quinquenervis | alias de `trevoa-quinquenervia` | Trevoa quinquenervia | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `taxus-sumatrana` | Taxus sumatrana | alias de `taxus-wallichiana` | Taxus wallichiana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: taxus-wallichiana,taxus-yunnanensis (reviewFlag fusion-heterotipica) |
| `taxus-x-media-cv-hicksii` | Taxus x media cv. hicksii | alias de `taxus-x-media` | Taxus × media | 0 → 0 | infraespecífico o autónimo absorbido por la especie aceptada |
| `taxus-yunnanensis` | Taxus yunnanensis | alias de `taxus-wallichiana` | Taxus wallichiana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: taxus-sumatrana,taxus-wallichiana (reviewFlag fusion-heterotipica) |
| `tetragonia-tetragonioides` | Tetragonia tetragonioides | alias de `tetragonia-tetragonoides` | Tetragonia tetragonoides | 0 → 3 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `tetrapanax-papyrifera` | Tetrapanax papyrifera | alias de `tetrapanax-papyrifer` | Tetrapanax papyrifer | 5 → 21 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `teucrium-divaricatum-var-canescens` | Teucrium divaricatum var. canescens | alias de `teucrium-divaricatum` | Teucrium divaricatum | 0 → 0 | infraespecífico o autónimo absorbido por la especie aceptada |
| `teucrium-oxylepis-subsp-marianum` | Teucrium oxylepis subsp. marianum | alias de `teucrium-oxylepis` | Teucrium oxylepis | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: teucrium-oxylepis-subsp-oxylepis (reviewFlag fusion-heterotipica) |
| `teucrium-oxylepis-subsp-oxylepis` | Teucrium oxylepis subsp. oxylepis | alias de `teucrium-oxylepis` | Teucrium oxylepis | 0 → 0 | infraespecífico o autónimo absorbido por la especie aceptada; se fusiona con otros: teucrium-oxylepis-subsp-marianum (reviewFlag fusion-heterotipica) |
| `teucrium-polium-var-valentinum` | Teucrium polium var. valentinum | alias de `teucrium-polium` | Teucrium polium | 0 → 8 | infraespecífico o autónimo absorbido por la especie aceptada; se fusiona con otros: teucrium-polium |
| `teyleria-koordersii` | Teyleria koordersii | alias de `teyleria-tetragona` | Teyleria tetragona | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `thevetia-neriifolia` | Thevetia neriifolia | alias de `cascabela-thevetia` | Cascabela thevetia | 13 → 31 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: thevetia-peruviana (reviewFlag fusion-heterotipica) |
| `thevetia-peruviana` | Thevetia peruviana | alias de `cascabela-thevetia` | Cascabela thevetia | 14 → 31 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: thevetia-neriifolia (reviewFlag fusion-heterotipica) |
| `thymus-broussonettii` | Thymus broussonettii | alias de `thymus-broussonetii` | Thymus broussonetii | 0 → 0 | variante ortográfica del nombre de WCVP |
| `thymus-capitatus` | Thymus capitatus | alias de `thymbra-capitata` | Thymbra capitata | 2 → 1 | sinónimo homotípico del aceptado de WCVP; se fusiona con otros: coridothymus-capitatus |
| `tovomita-brasiliensis` | Tovomita brasiliensis | alias de `tovomita-fructipendula` | Tovomita fructipendula | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `tovomita-excelsa` | Tovomita excelsa | alias de `tovomita-longifolia` | Tovomita longifolia | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `tovomita-pyrifolia` | Tovomita pyrifolia | alias de `tovomita-macrophylla` | Tovomita macrophylla | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `triadenum-japonicum` | Triadenum japonicum | alias de `hypericum-fauriei` | Hypericum fauriei | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `trichosanthes-anguina` | Trichosanthes anguina | alias de `trichosanthes-cucumerina-subsp-cucumerina` | Trichosanthes cucumerina subsp. cucumerina | 2 → 10 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `trichostemma-dichotomum` | Trichostemma dichotomum | alias de `trichostema-dichotomum` | Trichostema dichotomum | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: isanthus-brachiatus (reviewFlag fusion-heterotipica) |
| `trifolium-brachycalycinum` | Trifolium brachycalycinum | alias de `trifolium-subterraneum-subsp-oxaloides` | Trifolium subterraneum subsp. oxaloides | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `tripterygium-wilfordiim` | Tripterygium wilfordiim | alias de `tripterygium-wilfordii` | Tripterygium wilfordii | 0 → 8 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `tylophora-indica` | Tylophora indica | alias de `vincetoxicum-indicum` | Vincetoxicum indicum | 0 → 14 | sinónimo homotípico del aceptado de WCVP |
| `ulmus-fulva` | Ulmus fulva | alias de `ulmus-rubra` | Ulmus rubra | 13 → 23 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: ulmus-rubra (reviewFlag fusion-heterotipica) |
| `urginea-indica` | Urginea indica | alias de `drimia-indica` | Drimia indica | 7 → 19 | sinónimo homotípico del aceptado de WCVP |
| `urginea-maritima` | Urginea maritima | alias de `drimia-maritima` | Drimia maritima | 37 → 37 | sinónimo homotípico del aceptado de WCVP |
| `vaccinium-vitis-idaea-var-minus` | Vaccinium vitis-idaea var. minus | alias de `vaccinium-vitis-idaea` | Vaccinium vitis-idaea | 0 → 16 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `valerianella-locusta` | Valerianella locusta | alias de `valeriana-locusta` | Valeriana locusta | 0 → 4 | sinónimo homotípico del aceptado de WCVP |
| `valerianella-radicata` | Valerianella radicata | alias de `valeriana-woodsiana` | Valeriana woodsiana | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `vanilla-tahitensis` | Vanilla tahitensis | alias de `vanilla-x-tahitensis` | Vanilla × tahitensis | 0 → 0 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `vernonia-cinerea` | Vernonia cinerea | alias de `cyanthillium-cinereum` | Cyanthillium cinereum | 2 → 24 | sinónimo homotípico del aceptado de WCVP |
| `vetiveria-zizanioides` | Vetiveria zizanioides | alias de `chrysopogon-zizanioides` | Chrysopogon zizanioides | 29 → 34 | sinónimo homotípico del aceptado de WCVP |
| `viburnum-opulus-subsp-var-opulus` | Viburnum opulus subsp. var. opulus | alias de `viburnum-opulus` | Viburnum opulus | 0 → 19 | infraespecífico o autónimo absorbido por la especie aceptada |
| `vigna-unguiculata-subsp-unguiculata` | Vigna unguiculata subsp. unguiculata | alias de `vigna-unguiculata` | Vigna unguiculata | 0 → 20 | infraespecífico o autónimo absorbido por la especie aceptada |
| `waltheria-americana` | Waltheria americana | alias de `waltheria-indica` | Waltheria indica | 13 → 34 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `wasabia-japonica` | Wasabia japonica | alias de `eutrema-japonicum` | Eutrema japonicum | 1 → 6 | sinónimo homotípico del aceptado de WCVP |
| `wedelia-trilobata` | Wedelia trilobata | alias de `sphagneticola-trilobata` | Sphagneticola trilobata | 5 → 10 | sinónimo homotípico del aceptado de WCVP |
| `woodfordia-floribunda` | Woodfordia floribunda | alias de `woodfordia-fruticosa` | Woodfordia fruticosa | 5 → 25 | sinónimo homotípico del aceptado de WCVP |
| `wormia-burbidgei` | Wormia burbidgei | alias de `dillenia-suffruticosa` | Dillenia suffruticosa | 0 → 0 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `wormia-triquetra` | Wormia triquetra | alias de `dillenia-triquetra` | Dillenia triquetra | 0 → 0 | sinónimo homotípico del aceptado de WCVP |
| `zanthoxylum-alatum` | Zanthoxylum alatum | alias de `zanthoxylum-armatum-var-armatum` | Zanthoxylum armatum var. armatum | 1 → 17 | sinónimo heterotípico resuelto al aceptado de WCVP |
| `ziziphus-joazeiro` | Ziziphus joazeiro | alias de `sarcomphalus-joazeiro` | Sarcomphalus joazeiro | 0 → 2 | sinónimo homotípico del aceptado de WCVP |
| `zizyphus-jujuba` | Zizyphus jujuba | alias de `ziziphus-jujuba` | Ziziphus jujuba | 0 → 37 | nombre de USDA que WCVP trata con otro nombre aceptado; se fusiona con otros: zizyphus-vulgaris-var-spinosus (reviewFlag fusion-heterotipica) |
| `zizyphus-mauritiana` | Zizyphus mauritiana | alias de `ziziphus-mauritiana` | Ziziphus mauritiana | 0 → 20 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `zizyphus-nummularia` | Zizyphus nummularia | alias de `ziziphus-nummularia` | Ziziphus nummularia | 0 → 7 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `zizyphus-rugosa` | Zizyphus rugosa | alias de `ziziphus-rugosa` | Ziziphus rugosa | 0 → 13 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `zizyphus-spina-christi` | Zizyphus spina-christi | alias de `ziziphus-spina-christi` | Ziziphus spina-christi | 0 → 13 | nombre de USDA que WCVP trata con otro nombre aceptado |
| `zizyphus-vulgaris-var-spinosus` | Zizyphus vulgaris var. spinosus | alias de `ziziphus-jujuba` | Ziziphus jujuba | 0 → 37 | sinónimo heterotípico resuelto al aceptado de WCVP; se fusiona con otros: zizyphus-jujuba (reviewFlag fusion-heterotipica) |

## Tabla B: IDs que se conservan y absorben a otros

| ID | Nombre | Usos antes → ahora | IDs anteriores que absorbe |
| --- | --- | --- | --- |
| `actaea-cimicifuga` | Actaea cimicifuga | 0 → 0 | cimicifuga-foetida |
| `actaea-dahurica` | Actaea dahurica | 0 → 5 | cimicifuga-dahurica |
| `actaea-racemosa` | Actaea racemosa | 11 → 28 | cimicifuga-racemosa |
| `actaea-simplex` | Actaea simplex | 0 → 7 | cimicifuga-simplex |
| `agathosma-betulina` | Agathosma betulina | 0 → 11 | barosma-betulina |
| `argyreia-nervosa` | Argyreia nervosa | 2 → 19 | argyreia-speciosa |
| `atractylodes-lancea` | Atractylodes lancea | 4 → 28 | atractylodes-ovata |
| `bacopa-monnieri` | Bacopa monnieri | 0 → 28 | herpestis-monniera |
| `berberis-aquifolium` | Berberis aquifolium | 0 → 12 | mahonia-aquifolium |
| `berberis-repens` | Berberis repens | 7 → 12 | mahonia-repens |
| `brassica-chinensis` | Brassica chinensis | 8 → 8 | brassica-rapa-subsp-subsp-chinensis |
| `brassica-rapa` | Brassica rapa | 29 → 31 | brassica-rapa-var-rapa |
| `caraipa-densifolia` | Caraipa densifolia | 0 → 0 | caraipa-densiflora |
| `cinchona-pubescens` | Cinchona pubescens | 0 → 15 | cinchona-succirubra |
| `cinnamomum-verum` | Cinnamomum verum | 23 → 26 | cinnamomum-zeylanicum |
| `clinopodium-vulgare` | Clinopodium vulgare | 0 → 4 | satureja-vulgaris |
| `coleus-barbatus` | Coleus barbatus | 0 → 0 | plectranthus-barbatus |
| `commiphora-wightii` | Commiphora wightii | 0 → 24 | commiphora-mukul |
| `cynara-cardunculus-subsp-cardunculus` | Cynara cardunculus subsp. cardunculus | 0 → 15 | cynara-scolymus |
| `dictamnus-albus` | Dictamnus albus | 23 → 22 | dictamnus-angustifolius, dictamnus-caucasicus |
| `elsholtzia-ciliata` | Elsholtzia ciliata | 0 → 15 | elsholtzia-cristata, elsholtzia-patrini |
| `erythroxylum-gracilipes` | Erythroxylum gracilipes | 0 → 0 | erythroxylum-recurrens |
| `eucalyptus-cladocalyx` | Eucalyptus cladocalyx | 1 → 0 | eucalyptus-corynocalyx |
| `eucalyptus-moluccana` | Eucalyptus moluccana | 0 → 0 | eucalyptus-hemiphloia |
| `frangula-purshiana` | Frangula purshiana | 0 → 16 | rhamnus-purshiana |
| `geissospermum-laeve` | Geissospermum laeve | 2 → 4 | geissospermum-vellosii |
| `genista-lydia` | Genista lydia | 0 → 0 | genista-rumelica |
| `guazuma-ulmifolia` | Guazuma ulmifolia | 32 → 42 | guazuma-tomentosa |
| `ludwigia-perennis` | Ludwigia perennis | 0 → 2 | ludwigia-parviflora |
| `lycopodiella-caroliniana` | Lycopodiella caroliniana | 0 → 0 | lycopodium-carolinianum |
| `lycopodiella-inundata` | Lycopodiella inundata | 0 → 0 | lycopodium-inundatum |
| `melaleuca-leucadendra` | Melaleuca leucadendra | 0 → 33 | melaleuca-leucadendron |
| `mentha-x-rotundifolia` | Mentha × rotundifolia | 0 → 6 | mentha-rotundifolia |
| `mucuna-pruriens` | Mucuna pruriens | 24 → 39 | mucuna-pruriens-subsp-utilis |
| `nardostachys-jatamansi` | Nardostachys jatamansi | 32 → 42 | nardostachys-chinensis |
| `neonotonia-wightii` | Neonotonia wightii | 0 → 0 | glycine-wightii |
| `ocimum-americanum` | Ocimum americanum | 9 → 35 | ocimum-canum |
| `ocimum-tenuiflorum` | Ocimum tenuiflorum | 0 → 31 | ocimum-sanctum |
| `origanum-vulgare` | Origanum vulgare | 40 → 27 | origanum-vulgare-var-gracile |
| `pachira-aquatica` | Pachira aquatica | 0 → 6 | pachira-macrocarpa |
| `pelargonium-graveolens` | Pelargonium graveolens | 0 → 0 | pelargonium-citrosum |
| `piscidia-piscipula` | Piscidia piscipula | 26 → 46 | piscidia-erythrina |
| `platanus-orientalis` | Platanus orientalis | 8 → 8 | platanus-vulgaris |
| `populus-balsamifera` | Populus balsamifera | 24 → 20 | populus-tacamahacca |
| `rhododendron-dauricum` | Rhododendron dauricum | 0 → 0 | rhododendron-ledebourii |
| `sambucus-canadensis` | Sambucus canadensis | 36 → 41 | sambucus-simpsonii |
| `satureja-cuneifolia` | Satureja cuneifolia | 0 → 0 | satureja-obovata |
| `scutellaria-galericulata` | Scutellaria galericulata | 9 → 19 | scutellaria-epilobifolia |
| `selenicereus-grandiflorus` | Selenicereus grandiflorus | 3 → 13 | cereus-grandiflorus |
| `senna-obtusifolia` | Senna obtusifolia | 0 → 13 | cassia-obtusifolia |
| `syzygium-claviflorum` | Syzygium claviflorum | 0 → 0 | syzgium-claviflorum |
| `syzygium-cumini` | Syzygium cumini | 3 → 18 | eugenia-fruticosa, eugenia-jambolana |
| `tagetes-lucida` | Tagetes lucida | 4 → 22 | tagetes-florida |
| `tanacetum-parthenium` | Tanacetum parthenium | 0 → 31 | chrysanthemum-parthenium |
| `taxus-wallichiana` | Taxus wallichiana | 0 → 0 | taxus-sumatrana, taxus-yunnanensis |
| `teucrium-polium` | Teucrium polium | 7 → 8 | teucrium-polium-var-valentinum |
| `ulmus-rubra` | Ulmus rubra | 11 → 23 | ulmus-fulva |

## Tabla C: IDs que se conservan sin cambio

El destino es el mismo ID. El nombre científico es el mismo salvo el signo híbrido (`x` pasa a `×`).

| ID | Nombre nuevo | Usos antes → ahora |
| --- | --- | --- |
| `abelmoschus-esculentus` | Abelmoschus esculentus | 42 → 37 |
| `abelmoschus-manihot` | Abelmoschus manihot | 9 → 15 |
| `abelmoschus-moschatus` | Abelmoschus moschatus | 29 → 39 |
| `abies-alba` | Abies alba | 22 → 22 |
| `abies-balsamea` | Abies balsamea | 12 → 13 |
| `abies-sachalinensis` | Abies sachalinensis | 0 → 0 |
| `abies-spectabilis` | Abies spectabilis | 2 → 7 |
| `abrus-precatorius` | Abrus precatorius | 80 → 54 |
| `abutilon-theophrasti` | Abutilon theophrasti | 0 → 5 |
| `acacia-confusa` | Acacia confusa | 0 → 0 |
| `acacia-decurrens` | Acacia decurrens | 0 → 0 |
| `acacia-melanoxylon` | Acacia melanoxylon | 0 → 0 |
| `acalypha-indica` | Acalypha indica | 3 → 8 |
| `acanthospermum-hispidum` | Acanthospermum hispidum | 2 → 2 |
| `acanthus-ilicifolius` | Acanthus ilicifolius | 4 → 8 |
| `achillea-millefolium` | Achillea millefolium | 68 → 48 |
| `achyranthes-aspera` | Achyranthes aspera | 9 → 25 |
| `achyranthes-bidentata` | Achyranthes bidentata | 19 → 28 |
| `acinos-sp` | Acinos sp | 0 → 0 |
| `acokanthera-schimperi` | Acokanthera schimperi | 1 → 1 |
| `aconitum-carmichaelii` | Aconitum carmichaelii | 0 → 14 |
| `aconitum-napellus` | Aconitum napellus | 20 → 18 |
| `acorus-calamus` | Acorus calamus | 90 → 64 |
| `acrocomia-totai` | Acrocomia totai | 0 → 1 |
| `acrotrema-arnottianum` | Acrotrema arnottianum | 0 → 0 |
| `acrotrema-uniflorum` | Acrotrema uniflorum | 0 → 0 |
| `actaea-pachypoda` | Actaea pachypoda | 1 → 0 |
| `actaea-rubra` | Actaea rubra | 1 → 5 |
| `actaea-spicata` | Actaea spicata | 24 → 23 |
| `actinidia-chinensis` | Actinidia chinensis | 13 → 14 |
| `actinidia-polygama` | Actinidia polygama | 1 → 1 |
| `adansonia-digitata` | Adansonia digitata | 12 → 22 |
| `adenocarpus-complicatus` | Adenocarpus complicatus | 0 → 0 |
| `adenocarpus-decorticans` | Adenocarpus decorticans | 0 → 0 |
| `adenocarpus-foliolosus` | Adenocarpus foliolosus | 0 → 0 |
| `adiantum-capillus-veneris` | Adiantum capillus-veneris | 51 → 39 |
| `adiantum-pedatum` | Adiantum pedatum | 13 → 17 |
| `adonis-vernalis` | Adonis vernalis | 10 → 9 |
| `aegle-marmelos` | Aegle marmelos | 10 → 34 |
| `aeolanthus-myriantha` | Aeolanthus myriantha | 0 → 0 |
| `aesculus-hippocastanum` | Aesculus hippocastanum | 34 → 30 |
| `aethusa-cynapium` | Aethusa cynapium | 13 → 11 |
| `aframomum-melegueta` | Aframomum melegueta | 13 → 33 |
| `agastache-foeniculum` | Agastache foeniculum | 0 → 2 |
| `agastache-nepetoides` | Agastache nepetoides | 0 → 0 |
| `agastache-pallidiflora` | Agastache pallidiflora | 0 → 0 |
| `agastache-rugosa` | Agastache rugosa | 7 → 22 |
| `agastache-urticifolia` | Agastache urticifolia | 0 → 0 |
| `agave-americana` | Agave americana | 16 → 19 |
| `agave-sisalana` | Agave sisalana | 9 → 11 |
| `ageratum-conyzoides` | Ageratum conyzoides | 30 → 32 |
| `aglaia-edulis` | Aglaia edulis | 0 → 0 |
| `aglaia-elaeagnoidea` | Aglaia elaeagnoidea | 0 → 0 |
| `aglaia-leptantha` | Aglaia leptantha | 0 → 0 |
| `aglaia-odorata` | Aglaia odorata | 3 → 8 |
| `aglaonema-commutatum` | Aglaonema commutatum | 0 → 0 |
| `agrimonia-eupatoria` | Agrimonia eupatoria | 35 → 33 |
| `agrostemma-githago` | Agrostemma githago | 10 → 7 |
| `agrostistachys-hookeri` | Agrostistachys hookeri | 0 → 0 |
| `ailanthus-altissima` | Ailanthus altissima | 38 → 27 |
| `ajuga-chamaepitys` | Ajuga chamaepitys | 15 → 15 |
| `ajuga-iva` | Ajuga iva | 2 → 2 |
| `ajuga-reptans` | Ajuga reptans | 19 → 19 |
| `akebia-quinata` | Akebia quinata | 14 → 14 |
| `albizia-julibrissin` | Albizia julibrissin | 15 → 15 |
| `albizia-lebbeck` | Albizia lebbeck | 8 → 12 |
| `albizia-procera` | Albizia procera | 0 → 1 |
| `alchornea-floribunda` | Alchornea floribunda | 0 → 0 |
| `aletris-farinosa` | Aletris farinosa | 19 → 22 |
| `alisma-plantago-aquatica` | Alisma plantago-aquatica | 13 → 19 |
| `alliaria-petiolata` | Alliaria petiolata | 8 → 10 |
| `allium-ampeloprasum` | Allium ampeloprasum | 11 → 18 |
| `allium-cepa` | Allium cepa | 74 → 49 |
| `allium-schoenoprasum` | Allium schoenoprasum | 13 → 13 |
| `alnus-glutinosa` | Alnus glutinosa | 11 → 11 |
| `alnus-maximowiczii` | Alnus maximowiczii | 0 → 0 |
| `alnus-nepalensis` | Alnus nepalensis | 0 → 0 |
| `alnus-rubra` | Alnus rubra | 13 → 26 |
| `aloe-descoingsii` | Aloe descoingsii | 0 → 0 |
| `aloe-globuligemma` | Aloe globuligemma | 0 → 0 |
| `aloe-krapohliana` | Aloe krapohliana | 0 → 0 |
| `aloe-ortholopha` | Aloe ortholopha | 0 → 0 |
| `aloe-spp` | Aloe spp. | 0 → 0 |
| `aloe-vera` | Aloe vera | 10 → 62 |
| `aloe-viguieri` | Aloe viguieri | 0 → 0 |
| `aloysia-citrodora` | Aloysia citrodora | 0 → 23 |
| `alphitonia-excelsa` | Alphitonia excelsa | 0 → 0 |
| `alphitonia-macrocarpa` | Alphitonia macrocarpa | 0 → 0 |
| `alphitonia-petriei` | Alphitonia petriei | 0 → 0 |
| `alphitonia-whitei` | Alphitonia whitei | 0 → 0 |
| `alpinia-galanga` | Alpinia galanga | 4 → 12 |
| `alpinia-officinarum` | Alpinia officinarum | 35 → 32 |
| `alstonia-scholaris` | Alstonia scholaris | 14 → 26 |
| `althaea-officinalis` | Althaea officinalis | 21 → 25 |
| `alyxia-buxifolia` | Alyxia buxifolia | 0 → 0 |
| `amanoa-oblongifolia` | Amanoa oblongifolia | 0 → 0 |
| `amaranthus-sp` | Amaranthus sp. | 0 → 0 |
| `amaranthus-spinosus` | Amaranthus spinosus | 20 → 25 |
| `ambrosia-acanthicarpa` | Ambrosia acanthicarpa | 0 → 0 |
| `ambrosia-artemisiifolia` | Ambrosia artemisiifolia | 1 → 8 |
| `ambrosia-hispida` | Ambrosia hispida | 5 → 15 |
| `ambrosia-magdalenae` | Ambrosia magdalenae | 0 → 0 |
| `ammannia-baccifera` | Ammannia baccifera | 4 → 9 |
| `ammi-majus` | Ammi majus | 14 → 13 |
| `amorphophallus-konjac` | Amorphophallus konjac | 1 → 7 |
| `ampelozizyphus-amazonicus` | Ampelozizyphus amazonicus | 3 → 3 |
| `amphicarpaea-bracteata` | Amphicarpaea bracteata | 0 → 0 |
| `amsonia-grandiflora` | Amsonia grandiflora | 0 → 0 |
| `anabasis-aphylla` | Anabasis aphylla | 0 → 0 |
| `anacardium-occidentale` | Anacardium occidentale | 56 → 52 |
| `anadenanthera-colubrina` | Anadenanthera colubrina | 0 → 4 |
| `anadenanthera-peregrina` | Anadenanthera peregrina | 0 → 11 |
| `anamirta-cocculus` | Anamirta cocculus | 5 → 8 |
| `ananas-comosus` | Ananas comosus | 29 → 42 |
| `anaphalis-margaritacea` | Anaphalis margaritacea | 1 → 4 |
| `anastatica-hierochuntica` | Anastatica hierochuntica | 0 → 0 |
| `andira-inermis` | Andira inermis | 15 → 23 |
| `andrographis-paniculata` | Andrographis paniculata | 24 → 29 |
| `anemarrhena-asphodeloides` | Anemarrhena asphodeloides | 13 → 25 |
| `anemone-coronaria` | Anemone coronaria | 1 → 1 |
| `anemopsis-californica` | Anemopsis californica | 3 → 3 |
| `anethum-graveolens` | Anethum graveolens | 32 → 34 |
| `angelica-archangelica` | Angelica archangelica | 18 → 21 |
| `angelica-dahurica` | Angelica dahurica | 3 → 13 |
| `angelica-laxiflora` | Angelica laxiflora | 0 → 0 |
| `angelica-sinensis` | Angelica sinensis | 7 → 14 |
| `anisodus-tanguticus` | Anisodus tanguticus | 0 → 0 |
| `anisomeles-indica` | Anisomeles indica | 3 → 7 |
| `anisomeles-malabarica` | Anisomeles malabarica | 5 → 8 |
| `annona-cherimola` | Annona cherimola | 8 → 13 |
| `annona-glabra` | Annona glabra | 6 → 13 |
| `annona-montana` | Annona montana | 0 → 6 |
| `annona-muricata` | Annona muricata | 35 → 42 |
| `annona-reticulata` | Annona reticulata | 13 → 29 |
| `annona-squamosa` | Annona squamosa | 20 → 29 |
| `anredera-baselloides` | Anredera baselloides | 0 → 1 |
| `anthriscus-cerefolium` | Anthriscus cerefolium | 15 → 15 |
| `apios-americana` | Apios americana | 1 → 1 |
| `apium-graveolens` | Apium graveolens | 53 → 36 |
| `apocynum-androsaemifolium` | Apocynum androsaemifolium | 18 → 17 |
| `apocynum-cannabinum` | Apocynum cannabinum | 28 → 31 |
| `aquilegia-vulgaris` | Aquilegia vulgaris | 17 → 14 |
| `arachis-hypogaea` | Arachis hypogaea | 12 → 16 |
| `aralia-cordata` | Aralia cordata | 6 → 6 |
| `aralia-spinosa` | Aralia spinosa | 12 → 11 |
| `araucaria-bidwillii` | Araucaria bidwillii | 0 → 0 |
| `arbutus-menziesii` | Arbutus menziesii | 0 → 5 |
| `arbutus-unedo` | Arbutus unedo | 7 → 8 |
| `arctium-lappa` | Arctium lappa | 89 → 57 |
| `arctostaphylos-uva-ursi` | Arctostaphylos uva-ursi | 18 → 23 |
| `ardisia-japonica` | Ardisia japonica | 12 → 13 |
| `areca-catechu` | Areca catechu | 39 → 41 |
| `argemone-mexicana` | Argemone mexicana | 37 → 40 |
| `argyrocytisus-battandieri` | Argyrocytisus battandieri | 0 → 0 |
| `arisaema-consanguineum` | Arisaema consanguineum | 12 → 14 |
| `arisaema-triphyllum` | Arisaema triphyllum | 22 → 27 |
| `arisarum-vulgare` | Arisarum vulgare | 3 → 3 |
| `aristolochia-debilis` | Aristolochia debilis | 11 → 21 |
| `aristolochia-serpentaria` | Aristolochia serpentaria | 26 → 25 |
| `armoracia-rusticana` | Armoracia rusticana | 10 → 17 |
| `arnica-montana` | Arnica montana | 17 → 15 |
| `arracacia-xanthorrhiza` | Arracacia xanthorrhiza | 7 → 8 |
| `artemisia-abrotanum` | Artemisia abrotanum | 13 → 13 |
| `artemisia-absinthium` | Artemisia absinthium | 28 → 28 |
| `artemisia-annua` | Artemisia annua | 17 → 17 |
| `artemisia-capillaris` | Artemisia capillaris | 26 → 30 |
| `artemisia-cina` | Artemisia cina | 4 → 4 |
| `artemisia-dracunculus` | Artemisia dracunculus | 15 → 15 |
| `artemisia-herba-alba` | Artemisia herba-alba | 3 → 6 |
| `artemisia-indica` | Artemisia indica | 0 → 0 |
| `artemisia-maritima` | Artemisia maritima | 7 → 8 |
| `artemisia-pallens` | Artemisia pallens | 0 → 0 |
| `artemisia-salsoloides` | Artemisia salsoloides | 0 → 0 |
| `artemisia-vulgaris` | Artemisia vulgaris | 60 → 43 |
| `artocarpus-altilis` | Artocarpus altilis | 14 → 25 |
| `artocarpus-heterophyllus` | Artocarpus heterophyllus | 6 → 16 |
| `arum-italicum` | Arum italicum | 14 → 13 |
| `arum-maculatum` | Arum maculatum | 24 → 20 |
| `arundo-donax` | Arundo donax | 12 → 12 |
| `asarum-canadense` | Asarum canadense | 20 → 23 |
| `asclepias-syriaca` | Asclepias syriaca | 17 → 28 |
| `asimina-triloba` | Asimina triloba | 2 → 2 |
| `aspalathus-linearis` | Aspalathus linearis | 0 → 0 |
| `asparagus-officinalis` | Asparagus officinalis | 45 → 38 |
| `aspidosperma-quebracho-blanco` | Aspidosperma quebracho-blanco | 5 → 6 |
| `asplenium-platyneuron` | Asplenium platyneuron | 0 → 0 |
| `astragalus-gummifer` | Astragalus gummifer | 0 → 2 |
| `astragalus-membranaceus` | Astragalus membranaceus | 5 → 17 |
| `astrocaryum-vulgare` | Astrocaryum vulgare | 1 → 1 |
| `atractylis-carduus` | Atractylis carduus | 0 → 0 |
| `atropa-bella-donna` | Atropa bella-donna | 1 → 29 |
| `aucuba-japonica` | Aucuba japonica | 2 → 2 |
| `avena-sativa` | Avena sativa | 11 → 10 |
| `averrhoa-bilimbi` | Averrhoa bilimbi | 3 → 16 |
| `averrhoa-carambola` | Averrhoa carambola | 4 → 11 |
| `avicennia-alba` | Avicennia alba | 0 → 0 |
| `avicennia-marina` | Avicennia marina | 0 → 0 |
| `avicennia-officinalis` | Avicennia officinalis | 4 → 4 |
| `avicennia-tomentosa` | Avicennia tomentosa | 0 → 0 |
| `azadirachta-indica` | Azadirachta indica | 22 → 38 |
| `bactris-gasipaes` | Bactris gasipaes | 0 → 3 |
| `balanops-australiana` | Balanops australiana | 0 → 0 |
| `ballota-nigra` | Ballota nigra | 29 → 29 |
| `banisteriopsis-caapi` | Banisteriopsis caapi | 1 → 4 |
| `baptisia-hirsuta` | Baptisia hirsuta | 0 → 0 |
| `baptisia-sp` | Baptisia sp | 0 → 0 |
| `baptisia-sphaerocarpa` | Baptisia sphaerocarpa | 0 → 0 |
| `baptisia-tinctoria` | Baptisia tinctoria | 16 → 21 |
| `basella-alba` | Basella alba | 8 → 23 |
| `bauhinia-vahlii` | Bauhinia vahlii | 0 → 5 |
| `benincasa-hispida` | Benincasa hispida | 29 → 27 |
| `berberis-vulgaris` | Berberis vulgaris | 17 → 19 |
| `bertholletia-excelsa` | Bertholletia excelsa | 1 → 1 |
| `betula-alleghaniensis` | Betula alleghaniensis | 0 → 1 |
| `betula-cordifolia` | Betula cordifolia | 0 → 0 |
| `betula-ermanii` | Betula ermanii | 2 → 2 |
| `betula-lenta` | Betula lenta | 9 → 18 |
| `betula-maximowicziana` | Betula maximowicziana | 0 → 0 |
| `betula-papyrifera` | Betula papyrifera | 4 → 8 |
| `betula-pendula` | Betula pendula | 0 → 0 |
| `betula-populifolia` | Betula populifolia | 0 → 1 |
| `betula-sp` | Betula sp. | 0 → 0 |
| `betula-utilis` | Betula utilis | 0 → 3 |
| `bidens-pilosa` | Bidens pilosa | 35 → 34 |
| `bischofia-javanica` | Bischofia javanica | 3 → 14 |
| `bixa-orellana` | Bixa orellana | 41 → 42 |
| `blechnum-orientale` | Blechnum orientale | 2 → 5 |
| `bletilla-striata` | Bletilla striata | 21 → 25 |
| `blighia-sapida` | Blighia sapida | 23 → 20 |
| `bocconia-arborea` | Bocconia arborea | 13 → 13 |
| `bocconia-frutescens` | Bocconia frutescens | 40 → 36 |
| `boehmeria-excelsa` | Boehmeria excelsa | 0 → 0 |
| `boehmeria-nivea` | Boehmeria nivea | 21 → 26 |
| `borago-officinalis` | Borago officinalis | 22 → 24 |
| `boronia-megastigma` | Boronia megastigma | 0 → 0 |
| `boswellia-sacra` | Boswellia sacra | 0 → 21 |
| `boswellia-serrata` | Boswellia serrata | 7 → 14 |
| `bowdichia-nitida` | Bowdichia nitida | 0 → 0 |
| `bowdichia-virgilioides` | Bowdichia virgilioides | 5 → 5 |
| `bowiea-volubilis` | Bowiea volubilis | 6 → 4 |
| `brassica-oleracea-var-gongylodes` | Brassica oleracea var. gongylodes | 0 → 0 |
| `brassica-oleracea-var-italica` | Brassica oleracea var. italica | 0 → 0 |
| `brassica-pekinensis` | Brassica pekinensis | 0 → 0 |
| `bromelia-pinguin` | Bromelia pinguin | 1 → 4 |
| `brosimum-alicastrum` | Brosimum alicastrum | 9 → 10 |
| `broussonetia-papyrifera` | Broussonetia papyrifera | 13 → 20 |
| `bryonia-alba` | Bryonia alba | 12 → 11 |
| `bupleurum-chinense` | Bupleurum chinense | 11 → 11 |
| `bupleurum-salicifolium` | Bupleurum salicifolium | 0 → 0 |
| `bursera-simaruba` | Bursera simaruba | 41 → 38 |
| `buxus-microphylla` | Buxus microphylla | 0 → 0 |
| `buxus-sempervirens` | Buxus sempervirens | 31 → 27 |
| `buxus-wallichiana` | Buxus wallichiana | 0 → 0 |
| `byrsonima-crassifolia` | Byrsonima crassifolia | 26 → 30 |
| `byrsonima-sericea` | Byrsonima sericea | 0 → 0 |
| `caesalpinia-pulcherrima` | Caesalpinia pulcherrima | 38 → 39 |
| `cajanus-cajan` | Cajanus cajan | 27 → 32 |
| `cajanus-scarabaeoides` | Cajanus scarabaeoides | 0 → 11 |
| `caladium-bicolor` | Caladium bicolor | 2 → 10 |
| `caladium-bulbosum` | Caladium bulbosum | 0 → 0 |
| `calendula-officinalis` | Calendula officinalis | 39 → 30 |
| `calicotome-spinosa` | Calicotome spinosa | 0 → 0 |
| `calicotome-villosa` | Calicotome villosa | 0 → 1 |
| `callicarpa-americana` | Callicarpa americana | 1 → 1 |
| `callicarpa-arborea` | Callicarpa arborea | 1 → 1 |
| `callitriche-stagnalis` | Callitriche stagnalis | 0 → 0 |
| `calophyllum-apetalum` | Calophyllum apetalum | 0 → 0 |
| `calophyllum-bracteatum` | Calophyllum bracteatum | 0 → 0 |
| `calophyllum-lankaensis` | Calophyllum lankaensis | 0 → 0 |
| `calophyllum-macrocarpum` | Calophyllum macrocarpum | 0 → 0 |
| `calophyllum-tomentosum` | Calophyllum tomentosum | 0 → 0 |
| `calopogonium-caeruleum` | Calopogonium caeruleum | 0 → 1 |
| `calotropis-sp` | Calotropis sp. | 0 → 0 |
| `camellia-japonica` | Camellia japonica | 8 → 15 |
| `camellia-sinensis` | Camellia sinensis | 44 → 30 |
| `camptosema-sp` | Camptosema sp | 0 → 0 |
| `camptotheca-acuminata` | Camptotheca acuminata | 0 → 1 |
| `cananga-odorata` | Cananga odorata | 6 → 23 |
| `canarium-indicum` | Canarium indicum | 0 → 0 |
| `canavalia-bonariensis` | Canavalia bonariensis | 0 → 0 |
| `canavalia-ensiformis` | Canavalia ensiformis | 8 → 10 |
| `canavalia-eurycarpa` | Canavalia eurycarpa | 0 → 0 |
| `canavalia-galeata` | Canavalia galeata | 0 → 3 |
| `canavalia-gladiata` | Canavalia gladiata | 2 → 4 |
| `canavalia-rosea` | Canavalia rosea | 0 → 4 |
| `canavalia-sericea` | Canavalia sericea | 0 → 0 |
| `canna-indica` | Canna indica | 10 → 24 |
| `cannabis-sativa` | Cannabis sativa | 70 → 42 |
| `capparis-spinosa` | Capparis spinosa | 10 → 11 |
| `capparis-tomentosa` | Capparis tomentosa | 2 → 1 |
| `capsella-bursa-pastoris` | Capsella bursa-pastoris | 45 → 31 |
| `capsicum-annuum` | Capsicum annuum | 16 → 24 |
| `capsicum-frutescens` | Capsicum frutescens | 28 → 47 |
| `caraipa-grandifolia` | Caraipa grandifolia | 0 → 0 |
| `carapa-guianensis` | Carapa guianensis | 13 → 25 |
| `careya-arborea` | Careya arborea | 1 → 21 |
| `carica-papaya` | Carica papaya | 50 → 50 |
| `carlina-corymbosa` | Carlina corymbosa | 0 → 0 |
| `carthamus-tinctorius` | Carthamus tinctorius | 52 → 36 |
| `carum-carvi` | Carum carvi | 20 → 25 |
| `carya-glabra` | Carya glabra | 0 → 0 |
| `carya-ovata` | Carya ovata | 0 → 1 |
| `casearia-arborea` | Casearia arborea | 0 → 0 |
| `casimiroa-edulis` | Casimiroa edulis | 22 → 25 |
| `cassia-grandis` | Cassia grandis | 9 → 11 |
| `cassinia-laevis` | Cassinia laevis | 0 → 0 |
| `cassinia-uncata` | Cassinia uncata | 0 → 0 |
| `castanea-dentata` | Castanea dentata | 7 → 7 |
| `castanea-sativa` | Castanea sativa | 26 → 21 |
| `castanopsis-concinna` | Castanopsis concinna | 0 → 0 |
| `castanopsis-eyrei` | Castanopsis eyrei | 0 → 0 |
| `castanopsis-lamontii` | Castanopsis lamontii | 0 → 0 |
| `castanospermum-australe` | Castanospermum australe | 0 → 0 |
| `catalpa-bignonioides` | Catalpa bignonioides | 7 → 7 |
| `catalpa-longissima` | Catalpa longissima | 3 → 3 |
| `catalpa-ovata` | Catalpa ovata | 3 → 4 |
| `catha-edulis` | Catha edulis | 2 → 22 |
| `catharanthus-lanceus` | Catharanthus lanceus | 0 → 0 |
| `catharanthus-longifolius` | Catharanthus longifolius | 0 → 0 |
| `catharanthus-roseus` | Catharanthus roseus | 35 → 42 |
| `caulophyllum-thalictroides` | Caulophyllum thalictroides | 9 → 10 |
| `ceanothus-americanus` | Ceanothus americanus | 23 → 26 |
| `ceanothus-velutinus` | Ceanothus velutinus | 3 → 3 |
| `cedrela-odorata` | Cedrela odorata | 7 → 18 |
| `cedrus-libani` | Cedrus libani | 2 → 5 |
| `ceiba-pentandra` | Ceiba pentandra | 22 → 38 |
| `cenchrus-biflorus` | Cenchrus biflorus | 0 → 0 |
| `centaurea-calcitrapa` | Centaurea calcitrapa | 11 → 11 |
| `centaurea-cyanus` | Centaurea cyanus | 14 → 15 |
| `centaurium-erythraea` | Centaurium erythraea | 0 → 4 |
| `centella-asiatica` | Centella asiatica | 19 → 38 |
| `centrosema-pascuorum` | Centrosema pascuorum | 0 → 0 |
| `centrosema-plumieri` | Centrosema plumieri | 1 → 3 |
| `centrosema-sagittatum` | Centrosema sagittatum | 0 → 0 |
| `cephalotaxus-fortunei` | Cephalotaxus fortunei | 0 → 0 |
| `cephalotaxus-hainanensis` | Cephalotaxus hainanensis | 0 → 0 |
| `cephalotaxus-mannii` | Cephalotaxus mannii | 0 → 0 |
| `cephalotaxus-spp` | Cephalotaxus spp | 0 → 0 |
| `ceratonia-siliqua` | Ceratonia siliqua | 7 → 11 |
| `ceriops-decandra` | Ceriops decandra | 0 → 0 |
| `chaenomeles-speciosa` | Chaenomeles speciosa | 1 → 1 |
| `chamaecrista-greggii` | Chamaecrista greggii | 0 → 0 |
| `chamaecytisus-albus` | Chamaecytisus albus | 0 → 0 |
| `chamaecytisus-eriocarpus` | Chamaecytisus eriocarpus | 0 → 0 |
| `chamaecytisus-hirsutus` | Chamaecytisus hirsutus | 0 → 0 |
| `chamaecytisus-ratisbonensis` | Chamaecytisus ratisbonensis | 0 → 0 |
| `chamaecytisus-supinus` | Chamaecytisus supinus | 0 → 0 |
| `chamaelirium-luteum` | Chamaelirium luteum | 14 → 24 |
| `chamaemelum-nobile` | Chamaemelum nobile | 13 → 33 |
| `chamissoa-altissima` | Chamissoa altissima | 4 → 5 |
| `chelidonium-majus` | Chelidonium majus | 25 → 22 |
| `chenopodium-album` | Chenopodium album | 19 → 21 |
| `chenopodium-quinoa` | Chenopodium quinoa | 0 → 1 |
| `chimaphila-umbellata` | Chimaphila umbellata | 20 → 23 |
| `chiococca-alba` | Chiococca alba | 22 → 24 |
| `chondrodendron-tomentosum` | Chondrodendron tomentosum | 10 → 7 |
| `chondrus-crispus` | Chondrus crispus | 0 → 0 |
| `chrysanthemum-x-morifolium` | Chrysanthemum × morifolium | 0 → 29 |
| `chrysobalanus-icaco` | Chrysobalanus icaco | 17 → 20 |
| `chrysophyllum-cainito` | Chrysophyllum cainito | 12 → 13 |
| `cicer-arietinum` | Cicer arietinum | 11 → 15 |
| `cichorium-endivia` | Cichorium endivia | 7 → 7 |
| `cichorium-intybus` | Cichorium intybus | 37 → 40 |
| `cicuta-maculata` | Cicuta maculata | 2 → 2 |
| `cinchona-calisaya` | Cinchona calisaya | 9 → 16 |
| `cinchona-officinalis` | Cinchona officinalis | 11 → 25 |
| `cinchona-spp` | Cinchona spp | 0 → 0 |
| `cinnamomum-aromaticum` | Cinnamomum aromaticum | 7 → 7 |
| `cinnamomum-iners` | Cinnamomum iners | 9 → 13 |
| `cinnamomum-javanicum` | Cinnamomum javanicum | 0 → 2 |
| `cinnamomum-mollissimum` | Cinnamomum mollissimum | 0 → 0 |
| `cinnamomum-sieboldii` | Cinnamomum sieboldii | 4 → 4 |
| `cinnamomum-sulphuratum` | Cinnamomum sulphuratum | 0 → 0 |
| `cissampelos-pareira` | Cissampelos pareira | 42 → 52 |
| `cissus-verticillata` | Cissus verticillata | 0 → 0 |
| `cistanche-salsa` | Cistanche salsa | 0 → 4 |
| `cistus-laurifolius` | Cistus laurifolius | 0 → 0 |
| `citrullus-colocynthis` | Citrullus colocynthis | 21 → 23 |
| `citrullus-lanatus` | Citrullus lanatus | 23 → 26 |
| `citrus-medica` | Citrus medica | 15 → 22 |
| `citrus-reticulata` | Citrus reticulata | 34 → 23 |
| `citrus-spp` | Citrus spp | 0 → 0 |
| `clematis-vitalba` | Clematis vitalba | 12 → 11 |
| `cleonia-lusitanica` | Cleonia lusitanica | 0 → 0 |
| `clinacanthus-nutans` | Clinacanthus nutans | 0 → 1 |
| `clinopodium-umbrosum` | Clinopodium umbrosum | 0 → 0 |
| `clitoria-falcata` | Clitoria falcata | 0 → 0 |
| `clitoria-ternatea` | Clitoria ternatea | 12 → 33 |
| `clusia-arboricida` | Clusia arboricida | 0 → 0 |
| `clusia-sp` | Clusia sp. | 0 → 0 |
| `coccinia-grandis` | Coccinia grandis | 0 → 7 |
| `cocos-nucifera` | Cocos nucifera | 67 → 63 |
| `coffea-arabica` | Coffea arabica | 26 → 38 |
| `coix-lacryma-jobi` | Coix lacryma-jobi | 49 → 40 |
| `cola-acuminata` | Cola acuminata | 13 → 14 |
| `colchicum-autumnale` | Colchicum autumnale | 15 → 13 |
| `collinsonia-canadensis` | Collinsonia canadensis | 17 → 19 |
| `colocasia-esculenta` | Colocasia esculenta | 13 → 26 |
| `colubrina-arborescens` | Colubrina arborescens | 1 → 11 |
| `colubrina-texensis` | Colubrina texensis | 0 → 2 |
| `combretum-imberbe` | Combretum imberbe | 1 → 1 |
| `commelina-benghalensis` | Commelina benghalensis | 3 → 8 |
| `commelina-communis` | Commelina communis | 19 → 23 |
| `commiphora-myrrha` | Commiphora myrrha | 18 → 25 |
| `comptonia-peregrina` | Comptonia peregrina | 7 → 16 |
| `conium-chaerophylloides` | Conium chaerophylloides | 1 → 1 |
| `conium-maculatum` | Conium maculatum | 27 → 19 |
| `convallaria-majalis` | Convallaria majalis | 11 → 9 |
| `copaifera-spp` | Copaifera spp | 0 → 0 |
| `coptis-chinensis` | Coptis chinensis | 13 → 20 |
| `coptis-japonica` | Coptis japonica | 7 → 7 |
| `coptis-spp` | Coptis spp | 0 → 0 |
| `corchorus-olitorius` | Corchorus olitorius | 6 → 6 |
| `coriandrum-sativum` | Coriandrum sativum | 51 → 43 |
| `coriaria-myrtifolia` | Coriaria myrtifolia | 3 → 2 |
| `cornus-capitata` | Cornus capitata | 0 → 0 |
| `cornus-florida` | Cornus florida | 16 → 20 |
| `cornus-macrophylla` | Cornus macrophylla | 3 → 3 |
| `cornus-mas` | Cornus mas | 0 → 0 |
| `cornus-officinalis` | Cornus officinalis | 26 → 27 |
| `corydalis-spp` | Corydalis spp | 0 → 0 |
| `corylus-americana` | Corylus americana | 1 → 3 |
| `corylus-avellana` | Corylus avellana | 5 → 5 |
| `cotylelobium-scabriusculum` | Cotylelobium scabriusculum | 0 → 0 |
| `crataegus-cuneata` | Crataegus cuneata | 10 → 12 |
| `crataegus-laevigata` | Crataegus laevigata | 0 → 0 |
| `crataegus-monogyna` | Crataegus monogyna | 1 → 1 |
| `crataegus-pentagyna` | Crataegus pentagyna | 0 → 0 |
| `crataegus-rhipidophylla` | Crataegus rhipidophylla | 0 → 0 |
| `crataegus-sp` | Crataegus sp. | 0 → 0 |
| `crateva-religiosa` | Crateva religiosa | 8 → 12 |
| `crateva-tapia` | Crateva tapia | 12 → 16 |
| `crescentia-alata` | Crescentia alata | 15 → 15 |
| `crocus-sativus` | Crocus sativus | 42 → 37 |
| `crotalaria-juncea` | Crotalaria juncea | 5 → 4 |
| `crotalaria-retusa` | Crotalaria retusa | 1 → 4 |
| `crotalaria-semperflorens` | Crotalaria semperflorens | 0 → 0 |
| `croton-eluteria` | Croton eluteria | 6 → 8 |
| `croton-lechleri` | Croton lechleri | 0 → 0 |
| `croton-linearis` | Croton linearis | 1 → 3 |
| `croton-macrostachys` | Croton macrostachys | 1 → 1 |
| `croton-megalocarpus` | Croton megalocarpus | 0 → 0 |
| `croton-tiglium` | Croton tiglium | 32 → 30 |
| `cryptotaenia-japonica` | Cryptotaenia japonica | 0 → 0 |
| `cucumis-sativus` | Cucumis sativus | 18 → 25 |
| `cucurbita-foetidissima` | Cucurbita foetidissima | 2 → 2 |
| `cucurbita-maxima` | Cucurbita maxima | 16 → 18 |
| `cucurbita-pepo` | Cucurbita pepo | 23 → 25 |
| `cucurbita-spp` | Cucurbita spp | 0 → 0 |
| `cuminum-cyminum` | Cuminum cyminum | 17 → 20 |
| `cunila-origanoides` | Cunila origanoides | 2 → 2 |
| `cuphea-carthagenensis` | Cuphea carthagenensis | 0 → 0 |
| `curatella-americana` | Curatella americana | 6 → 7 |
| `curcuma-longa` | Curcuma longa | 21 → 65 |
| `curcuma-zedoaria` | Curcuma zedoaria | 15 → 27 |
| `cuscuta-europaea` | Cuscuta europaea | 14 → 14 |
| `cuscuta-reflexa` | Cuscuta reflexa | 1 → 7 |
| `cyamopsis-tetragonoloba` | Cyamopsis tetragonoloba | 0 → 10 |
| `cycas-revoluta` | Cycas revoluta | 7 → 10 |
| `cyclanthera-pedata` | Cyclanthera pedata | 0 → 0 |
| `cydonia-oblonga` | Cydonia oblonga | 30 → 26 |
| `cymbopogon-citratus` | Cymbopogon citratus | 43 → 46 |
| `cymbopogon-flexuosus` | Cymbopogon flexuosus | 2 → 3 |
| `cymbopogon-nardus` | Cymbopogon nardus | 19 → 24 |
| `cymbopogon-winterianus` | Cymbopogon winterianus | 0 → 0 |
| `cyperus-articulatus` | Cyperus articulatus | 1 → 5 |
| `cyperus-rotundus` | Cyperus rotundus | 58 → 45 |
| `cytisus-multiflorus` | Cytisus multiflorus | 0 → 0 |
| `cytisus-scoparius` | Cytisus scoparius | 15 → 25 |
| `cytisus-sp` | Cytisus sp | 0 → 0 |
| `cytisus-striatus` | Cytisus striatus | 0 → 0 |
| `dalbergia-nitidula` | Dalbergia nitidula | 1 → 0 |
| `dalbergia-sericea` | Dalbergia sericea | 0 → 0 |
| `daphne-genkwa` | Daphne genkwa | 27 → 22 |
| `daphne-mezereum` | Daphne mezereum | 16 → 11 |
| `datura-innoxia` | Datura innoxia | 3 → 28 |
| `datura-metel` | Datura metel | 23 → 47 |
| `datura-stramonium` | Datura stramonium | 79 → 58 |
| `daucus-carota` | Daucus carota | 36 → 33 |
| `davilla-rugosa` | Davilla rugosa | 3 → 3 |
| `davilla-sp` | Davilla sp. | 0 → 0 |
| `dendrobium-nobile` | Dendrobium nobile | 17 → 17 |
| `derris-trifoliata` | Derris trifoliata | 0 → 10 |
| `desmodium-pulchellum` | Desmodium pulchellum | 0 → 4 |
| `dianthus-barbatus` | Dianthus barbatus | 0 → 0 |
| `dianthus-caryophyllus` | Dianthus caryophyllus | 6 → 6 |
| `dianthus-chinensis` | Dianthus chinensis | 2 → 13 |
| `dianthus-sp` | Dianthus sp. | 0 → 0 |
| `dianthus-superbus` | Dianthus superbus | 21 → 20 |
| `dicoma-tomentosa` | Dicoma tomentosa | 2 → 4 |
| `dictamnus-hispanicus` | Dictamnus hispanicus | 1 → 0 |
| `dieffenbachia-seguine` | Dieffenbachia seguine | 4 → 10 |
| `digitalis-lanata` | Digitalis lanata | 7 → 14 |
| `digitalis-purpurea` | Digitalis purpurea | 22 → 26 |
| `dillenia-aurea` | Dillenia aurea | 2 → 3 |
| `dillenia-bracteata` | Dillenia bracteata | 0 → 0 |
| `dillenia-indica` | Dillenia indica | 1 → 9 |
| `dillenia-pentagyna` | Dillenia pentagyna | 0 → 7 |
| `dillenia-retusa` | Dillenia retusa | 0 → 0 |
| `dillenia-scabrella` | Dillenia scabrella | 0 → 1 |
| `dionaea-muscipula` | Dionaea muscipula | 0 → 0 |
| `dioscorea-alata` | Dioscorea alata | 1 → 8 |
| `dioscorea-bulbifera` | Dioscorea bulbifera | 15 → 18 |
| `dioscorea-composita` | Dioscorea composita | 0 → 1 |
| `dioscorea-pentaphylla` | Dioscorea pentaphylla | 0 → 4 |
| `dioscorea-sp` | Dioscorea sp. | 0 → 0 |
| `dioscorea-villosa` | Dioscorea villosa | 19 → 25 |
| `diospyros-abyssinica` | Diospyros abyssinica | 0 → 0 |
| `diospyros-argentea` | Diospyros argentea | 0 → 2 |
| `diospyros-buxifolia` | Diospyros buxifolia | 0 → 0 |
| `diospyros-canaliculata` | Diospyros canaliculata | 0 → 0 |
| `diospyros-celebica` | Diospyros celebica | 0 → 0 |
| `diospyros-chevalieri` | Diospyros chevalieri | 0 → 0 |
| `diospyros-cinnabarina` | Diospyros cinnabarina | 0 → 0 |
| `diospyros-consolatae` | Diospyros consolatae | 0 → 0 |
| `diospyros-crassiflora` | Diospyros crassiflora | 0 → 0 |
| `diospyros-dendo` | Diospyros dendo | 0 → 0 |
| `diospyros-derra` | Diospyros derra | 0 → 0 |
| `diospyros-ebenum` | Diospyros ebenum | 5 → 9 |
| `diospyros-elliptifolia` | Diospyros elliptifolia | 0 → 0 |
| `diospyros-eriantha` | Diospyros eriantha | 0 → 0 |
| `diospyros-ferrea` | Diospyros ferrea | 0 → 3 |
| `diospyros-fragrans` | Diospyros fragrans | 0 → 0 |
| `diospyros-gabunensis` | Diospyros gabunensis | 0 → 0 |
| `diospyros-gracilescens` | Diospyros gracilescens | 0 → 0 |
| `diospyros-greenwayi` | Diospyros greenwayi | 0 → 0 |
| `diospyros-hirsuta` | Diospyros hirsuta | 0 → 0 |
| `diospyros-hoyleana` | Diospyros hoyleana | 0 → 0 |
| `diospyros-iturensis` | Diospyros iturensis | 0 → 0 |
| `diospyros-japonica` | Diospyros japonica | 0 → 0 |
| `diospyros-kaki` | Diospyros kaki | 22 → 23 |
| `diospyros-kamerunensis` | Diospyros kamerunensis | 0 → 0 |
| `diospyros-leucomelas` | Diospyros leucomelas | 0 → 0 |
| `diospyros-longiflora` | Diospyros longiflora | 0 → 0 |
| `diospyros-lotus` | Diospyros lotus | 0 → 0 |
| `diospyros-mafiensis` | Diospyros mafiensis | 0 → 0 |
| `diospyros-maingayi` | Diospyros maingayi | 0 → 0 |
| `diospyros-malanonilau` | Diospyros malanonilau | 0 → 0 |
| `diospyros-mannii` | Diospyros mannii | 0 → 0 |
| `diospyros-maritima` | Diospyros maritima | 1 → 1 |
| `diospyros-melanoxylon` | Diospyros melanoxylon | 0 → 17 |
| `diospyros-mespiliformis` | Diospyros mespiliformis | 0 → 0 |
| `diospyros-mollis` | Diospyros mollis | 0 → 0 |
| `diospyros-monbuttensis` | Diospyros monbuttensis | 0 → 0 |
| `diospyros-montana` | Diospyros montana | 1 → 11 |
| `diospyros-moonii` | Diospyros moonii | 0 → 0 |
| `diospyros-morrisiana` | Diospyros morrisiana | 0 → 0 |
| `diospyros-natalensis` | Diospyros natalensis | 0 → 0 |
| `diospyros-quaesita` | Diospyros quaesita | 0 → 0 |
| `diospyros-rotundifolia` | Diospyros rotundifolia | 0 → 0 |
| `diospyros-sanza-minika` | Diospyros sanza-minika | 0 → 0 |
| `diospyros-siamang` | Diospyros siamang | 0 → 0 |
| `diospyros-siderophylla` | Diospyros siderophylla | 0 → 0 |
| `diospyros-singaporensis` | Diospyros singaporensis | 0 → 0 |
| `diospyros-spinescens` | Diospyros spinescens | 0 → 0 |
| `diospyros-sumatrana` | Diospyros sumatrana | 0 → 0 |
| `diospyros-sylvatica` | Diospyros sylvatica | 0 → 0 |
| `diospyros-thwaitesii` | Diospyros thwaitesii | 0 → 0 |
| `diospyros-undulata` | Diospyros undulata | 0 → 0 |
| `diospyros-verrucosa` | Diospyros verrucosa | 0 → 0 |
| `diospyros-virginiana` | Diospyros virginiana | 21 → 23 |
| `diospyros-walkeri` | Diospyros walkeri | 0 → 0 |
| `diospyros-wallichii` | Diospyros wallichii | 0 → 2 |
| `diospyros-zenkeri` | Diospyros zenkeri | 0 → 0 |
| `dipogon-lignosus` | Dipogon lignosus | 0 → 0 |
| `dipsacus-fullonum` | Dipsacus fullonum | 2 → 3 |
| `dipterocarpus-glandulosus` | Dipterocarpus glandulosus | 0 → 0 |
| `dipterocarpus-hispidus` | Dipterocarpus hispidus | 0 → 0 |
| `dipterocarpus-insignis` | Dipterocarpus insignis | 0 → 0 |
| `dipterocarpus-zeylanicus` | Dipterocarpus zeylanicus | 0 → 0 |
| `dipteryx-odorata` | Dipteryx odorata | 13 → 18 |
| `dodonaea-viscosa` | Dodonaea viscosa | 21 → 40 |
| `dracocephalum-moldavica` | Dracocephalum moldavica | 1 → 6 |
| `drimys-winteri` | Drimys winteri | 19 → 19 |
| `dryopteris-filix-mas` | Dryopteris filix-mas | 9 → 17 |
| `dryopteris-marginalis` | Dryopteris marginalis | 2 → 2 |
| `duboisia-leichhardtii` | Duboisia leichhardtii | 1 → 0 |
| `duboisia-myoporoides` | Duboisia myoporoides | 8 → 7 |
| `dunbaria-villosa` | Dunbaria villosa | 0 → 0 |
| `durio-zibethinus` | Durio zibethinus | 1 → 6 |
| `echinacea-angustifolia` | Echinacea angustifolia | 13 → 13 |
| `echinacea-pallida` | Echinacea pallida | 3 → 3 |
| `echinacea-purpurea` | Echinacea purpurea | 5 → 6 |
| `echinacea-spp` | Echinacea spp | 0 → 0 |
| `echinops-echinatus` | Echinops echinatus | 0 → 6 |
| `echinops-niveus` | Echinops niveus | 0 → 0 |
| `ehretia-laevis` | Ehretia laevis | 0 → 2 |
| `elaeaegnus-oldhami` | Elaeaegnus oldhami | 0 → 0 |
| `elaeagnus-angustifolia` | Elaeagnus angustifolia | 0 → 1 |
| `elaeagnus-commutata` | Elaeagnus commutata | 0 → 0 |
| `elaeagnus-pungens` | Elaeagnus pungens | 7 → 7 |
| `elaeis-guineensis` | Elaeis guineensis | 3 → 10 |
| `elaeis-oleifera` | Elaeis oleifera | 0 → 8 |
| `eleocharis-dulcis` | Eleocharis dulcis | 0 → 2 |
| `elettaria-cardamomum` | Elettaria cardamomum | 43 → 34 |
| `eleutherococcus-senticosus` | Eleutherococcus senticosus | 0 → 0 |
| `elsholtzia-blanda` | Elsholtzia blanda | 0 → 3 |
| `elsholtzia-densa` | Elsholtzia densa | 0 → 0 |
| `elsholtzia-nipponica` | Elsholtzia nipponica | 0 → 0 |
| `elsholtzia-pilosa` | Elsholtzia pilosa | 0 → 0 |
| `enterolobium-cyclocarpum` | Enterolobium cyclocarpum | 14 → 16 |
| `eperua-falcata` | Eperua falcata | 0 → 0 |
| `eperua-purpurea` | Eperua purpurea | 0 → 0 |
| `ephedra-gerardiana` | Ephedra gerardiana | 3 → 8 |
| `ephedra-nevadensis` | Ephedra nevadensis | 3 → 5 |
| `ephedra-sinica` | Ephedra sinica | 8 → 24 |
| `ephedra-spp` | Ephedra spp | 0 → 0 |
| `epilobium-rosmarinifolium` | Epilobium rosmarinifolium | 0 → 0 |
| `equisetum-arvense` | Equisetum arvense | 34 → 30 |
| `equisetum-hyemale` | Equisetum hyemale | 17 → 28 |
| `eremurus-chinensis` | Eremurus chinensis | 0 → 0 |
| `erica-arborea` | Erica arborea | 0 → 0 |
| `erinacea-anthyllis` | Erinacea anthyllis | 0 → 0 |
| `eriobotrya-japonica` | Eriobotrya japonica | 18 → 25 |
| `eriocaulon-sp` | Eriocaulon sp | 8 → 0 |
| `eriodictyon-californicum` | Eriodictyon californicum | 0 → 14 |
| `eriosema-glomeratum` | Eriosema glomeratum | 1 → 1 |
| `eriosema-nutans` | Eriosema nutans | 0 → 0 |
| `eriosema-psoraleoides` | Eriosema psoraleoides | 0 → 1 |
| `eruca-sativa` | Eruca sativa | 6 → 7 |
| `eryngium-foetidum` | Eryngium foetidum | 35 → 44 |
| `erythrina-berteroana` | Erythrina berteroana | 3 → 5 |
| `erythrina-crista-galli` | Erythrina crista-galli | 1 → 4 |
| `erythrina-fusca` | Erythrina fusca | 1 → 3 |
| `erythrina-senegalensis` | Erythrina senegalensis | 1 → 1 |
| `erythrina-sp` | Erythrina sp | 8 → 0 |
| `erythrophleum-suaveolens` | Erythrophleum suaveolens | 29 → 27 |
| `erythrospermum-zeylanicum` | Erythrospermum zeylanicum | 0 → 0 |
| `erythroxylum-amazonicum` | Erythroxylum amazonicum | 0 → 0 |
| `erythroxylum-areolatum` | Erythroxylum areolatum | 0 → 0 |
| `erythroxylum-australe` | Erythroxylum australe | 0 → 0 |
| `erythroxylum-campestre` | Erythroxylum campestre | 0 → 0 |
| `erythroxylum-cataractarum` | Erythroxylum cataractarum | 0 → 0 |
| `erythroxylum-citrifolium` | Erythroxylum citrifolium | 1 → 1 |
| `erythroxylum-coca-var-ipadu` | Erythroxylum coca var. ipadu | 0 → 0 |
| `erythroxylum-deciduum` | Erythroxylum deciduum | 0 → 0 |
| `erythroxylum-ellipticum` | Erythroxylum ellipticum | 0 → 0 |
| `erythroxylum-fimbriatum` | Erythroxylum fimbriatum | 0 → 0 |
| `erythroxylum-glaucum` | Erythroxylum glaucum | 0 → 0 |
| `erythroxylum-hypericifolium` | Erythroxylum hypericifolium | 0 → 0 |
| `erythroxylum-impressum` | Erythroxylum impressum | 0 → 0 |
| `erythroxylum-incrassatum` | Erythroxylum incrassatum | 0 → 0 |
| `erythroxylum-laurifolium` | Erythroxylum laurifolium | 0 → 0 |
| `erythroxylum-lucidum` | Erythroxylum lucidum | 0 → 0 |
| `erythroxylum-macrophyllum` | Erythroxylum macrophyllum | 0 → 0 |
| `erythroxylum-mamacoca` | Erythroxylum mamacoca | 0 → 0 |
| `erythroxylum-monogynum` | Erythroxylum monogynum | 0 → 0 |
| `erythroxylum-mucronatum` | Erythroxylum mucronatum | 0 → 0 |
| `erythroxylum-novogranatense-var-truxillense` | Erythroxylum novogranatense var. truxillense | 0 → 0 |
| `erythroxylum-panamense` | Erythroxylum panamense | 0 → 0 |
| `erythroxylum-pelleterianum` | Erythroxylum pelleterianum | 0 → 0 |
| `erythroxylum-pulchrum` | Erythroxylum pulchrum | 0 → 0 |
| `erythroxylum-retusum` | Erythroxylum retusum | 0 → 0 |
| `erythroxylum-rotundifolium` | Erythroxylum rotundifolium | 0 → 1 |
| `erythroxylum-sp` | Erythroxylum sp. | 0 → 0 |
| `erythroxylum-steyermarkii` | Erythroxylum steyermarkii | 0 → 0 |
| `erythroxylum-ulei` | Erythroxylum ulei | 0 → 0 |
| `erythroxylum-vacciniifolium` | Erythroxylum vacciniifolium | 0 → 0 |
| `erythroxylum-zambesiacum` | Erythroxylum zambesiacum | 0 → 0 |
| `eucalyptus-albens` | Eucalyptus albens | 0 → 0 |
| `eucalyptus-angulosa` | Eucalyptus angulosa | 0 → 0 |
| `eucalyptus-astringens` | Eucalyptus astringens | 0 → 0 |
| `eucalyptus-behriana` | Eucalyptus behriana | 0 → 0 |
| `eucalyptus-blakelyi` | Eucalyptus blakelyi | 0 → 0 |
| `eucalyptus-bosistoana` | Eucalyptus bosistoana | 0 → 0 |
| `eucalyptus-botryoides` | Eucalyptus botryoides | 0 → 0 |
| `eucalyptus-brassiana` | Eucalyptus brassiana | 0 → 0 |
| `eucalyptus-bridgesiana` | Eucalyptus bridgesiana | 0 → 0 |
| `eucalyptus-camaldulensis` | Eucalyptus camaldulensis | 9 → 15 |
| `eucalyptus-ceratocorys` | Eucalyptus ceratocorys | 0 → 0 |
| `eucalyptus-cuprea` | Eucalyptus cuprea | 0 → 0 |
| `eucalyptus-dealbata` | Eucalyptus dealbata | 0 → 0 |
| `eucalyptus-desquamata` | Eucalyptus desquamata | 0 → 0 |
| `eucalyptus-diversicolor` | Eucalyptus diversicolor | 0 → 0 |
| `eucalyptus-dives` | Eucalyptus dives | 0 → 0 |
| `eucalyptus-dolichorhyncha` | Eucalyptus dolichorhyncha | 0 → 0 |
| `eucalyptus-forrestiana` | Eucalyptus forrestiana | 0 → 0 |
| `eucalyptus-globulus` | Eucalyptus globulus | 49 → 32 |
| `eucalyptus-grandis` | Eucalyptus grandis | 0 → 0 |
| `eucalyptus-incrassata` | Eucalyptus incrassata | 2 → 2 |
| `eucalyptus-intertexta` | Eucalyptus intertexta | 0 → 0 |
| `eucalyptus-lansdowneana` | Eucalyptus lansdowneana | 0 → 0 |
| `eucalyptus-largisparsa` | Eucalyptus largisparsa | 0 → 0 |
| `eucalyptus-leucoxylon` | Eucalyptus leucoxylon | 0 → 0 |
| `eucalyptus-melanophloia` | Eucalyptus melanophloia | 0 → 0 |
| `eucalyptus-melliodora` | Eucalyptus melliodora | 0 → 0 |
| `eucalyptus-nova-anglica` | Eucalyptus nova-anglica | 0 → 0 |
| `eucalyptus-occidentalis` | Eucalyptus occidentalis | 0 → 0 |
| `eucalyptus-ochrophloia` | Eucalyptus ochrophloia | 0 → 0 |
| `eucalyptus-odorata` | Eucalyptus odorata | 0 → 0 |
| `eucalyptus-paniculata` | Eucalyptus paniculata | 0 → 0 |
| `eucalyptus-polyanthemos` | Eucalyptus polyanthemos | 0 → 0 |
| `eucalyptus-populnea` | Eucalyptus populnea | 0 → 0 |
| `eucalyptus-porosa` | Eucalyptus porosa | 0 → 0 |
| `eucalyptus-punctata` | Eucalyptus punctata | 0 → 0 |
| `eucalyptus-robusta` | Eucalyptus robusta | 13 → 13 |
| `eucalyptus-saligna` | Eucalyptus saligna | 0 → 0 |
| `eucalyptus-siderophloia` | Eucalyptus siderophloia | 0 → 0 |
| `eucalyptus-sideroxylon` | Eucalyptus sideroxylon | 0 → 0 |
| `eucalyptus-sp` | Eucalyptus sp | 4 → 0 |
| `eucalyptus-sparsa` | Eucalyptus sparsa | 0 → 0 |
| `eucalyptus-stoatei` | Eucalyptus stoatei | 0 → 0 |
| `eucalyptus-tereticornis` | Eucalyptus tereticornis | 0 → 0 |
| `eucalyptus-tetraptera` | Eucalyptus tetraptera | 0 → 0 |
| `eucalyptus-viminalis` | Eucalyptus viminalis | 0 → 0 |
| `eucalyptus-viridis` | Eucalyptus viridis | 0 → 0 |
| `eucalyptus-wandoo` | Eucalyptus wandoo | 0 → 0 |
| `euclea-crispa` | Euclea crispa | 4 → 4 |
| `euclea-divinorum` | Euclea divinorum | 0 → 0 |
| `euclea-natalensis` | Euclea natalensis | 1 → 1 |
| `eucommia-ulmoides` | Eucommia ulmoides | 20 → 27 |
| `eugenia-brasiliensis` | Eugenia brasiliensis | 0 → 0 |
| `eugenia-uniflora` | Eugenia uniflora | 1 → 2 |
| `euonymus-atropurpureus` | Euonymus atropurpureus | 14 → 19 |
| `euonymus-echinatus` | Euonymus echinatus | 0 → 0 |
| `eupatorium-perfoliatum` | Eupatorium perfoliatum | 26 → 28 |
| `euphorbia-hirta` | Euphorbia hirta | 33 → 42 |
| `euphorbia-lathyris` | Euphorbia lathyris | 20 → 20 |
| `euphorbia-paralias` | Euphorbia paralias | 1 → 1 |
| `euphorbia-pulcherrima` | Euphorbia pulcherrima | 12 → 12 |
| `euphorbia-tirucalli` | Euphorbia tirucalli | 3 → 22 |
| `euphrasia-officinalis` | Euphrasia officinalis | 6 → 10 |
| `euptelea-polyandra` | Euptelea polyandra | 0 → 0 |
| `eurya-acuminata` | Eurya acuminata | 2 → 2 |
| `eurya-japonica` | Eurya japonica | 0 → 5 |
| `fagopyrum-esculentum` | Fagopyrum esculentum | 18 → 22 |
| `feijoa-sellowiana` | Feijoa sellowiana | 0 → 0 |
| `ferula-alliacea` | Ferula alliacea | 6 → 6 |
| `ferula-assa-foetida` | Ferula assa-foetida | 27 → 27 |
| `ferula-gummosa` | Ferula gummosa | 5 → 16 |
| `ferula-jaeschkeana` | Ferula jaeschkeana | 1 → 2 |
| `ficus-carica` | Ficus carica | 35 → 28 |
| `filipendula-ulmaria` | Filipendula ulmaria | 12 → 12 |
| `firmiana-simplex` | Firmiana simplex | 0 → 12 |
| `flemingia-strobilifera` | Flemingia strobilifera | 0 → 9 |
| `flindersia-pimenteliana` | Flindersia pimenteliana | 0 → 0 |
| `foeniculum-vulgare` | Foeniculum vulgare | 79 → 58 |
| `forsythia-suspensa` | Forsythia suspensa | 52 → 35 |
| `forsythia-viridissima` | Forsythia viridissima | 3 → 3 |
| `fragaria-spp` | Fragaria spp | 0 → 0 |
| `fragaria-vesca` | Fragaria vesca | 27 → 25 |
| `frangula-alnus` | Frangula alnus | 10 → 11 |
| `fraxinus-americana` | Fraxinus americana | 11 → 22 |
| `fraxinus-ornus` | Fraxinus ornus | 10 → 12 |
| `fritillaria-thunbergii` | Fritillaria thunbergii | 6 → 14 |
| `fucus-vesiculosus` | Fucus vesiculosus | 4 → 4 |
| `galactia-jussiaeana` | Galactia jussiaeana | 0 → 0 |
| `galanthus-nivalis` | Galanthus nivalis | 5 → 4 |
| `galega-officinalis` | Galega officinalis | 12 → 12 |
| `galeopsis-segetum` | Galeopsis segetum | 0 → 3 |
| `galeopsis-tetrahit` | Galeopsis tetrahit | 8 → 12 |
| `galium-odoratum` | Galium odoratum | 3 → 10 |
| `ganoderma-lucidum` | Ganoderma lucidum | 0 → 0 |
| `garcinia-atroviridis` | Garcinia atroviridis | 0 → 3 |
| `garcinia-hanburyi` | Garcinia hanburyi | 5 → 4 |
| `garcinia-indica` | Garcinia indica | 0 → 4 |
| `garcinia-mangostana` | Garcinia mangostana | 3 → 17 |
| `garcinia-xanthochymus` | Garcinia xanthochymus | 0 → 0 |
| `gardenia-jasminoides` | Gardenia jasminoides | 20 → 37 |
| `gastrodia-elata` | Gastrodia elata | 32 → 28 |
| `gaultheria-fragrantissima` | Gaultheria fragrantissima | 2 → 17 |
| `gaultheria-procumbens` | Gaultheria procumbens | 14 → 17 |
| `gelsemium-sempervirens` | Gelsemium sempervirens | 43 → 31 |
| `genipa-americana` | Genipa americana | 21 → 28 |
| `genista-clavata` | Genista clavata | 0 → 0 |
| `genista-germanica` | Genista germanica | 0 → 0 |
| `genista-hispanica` | Genista hispanica | 0 → 0 |
| `genista-ovata` | Genista ovata | 0 → 0 |
| `genista-sp` | Genista sp | 1 → 0 |
| `genista-tinctoria` | Genista tinctoria | 11 → 11 |
| `gentiana-acaulis` | Gentiana acaulis | 0 → 0 |
| `gentiana-lutea` | Gentiana lutea | 9 → 10 |
| `gentiana-scabra` | Gentiana scabra | 38 → 31 |
| `geranium-maculatum` | Geranium maculatum | 18 → 24 |
| `geranium-thunbergii` | Geranium thunbergii | 2 → 2 |
| `ginkgo-biloba` | Ginkgo biloba | 40 → 33 |
| `glaucium-flavum` | Glaucium flavum | 7 → 7 |
| `glechoma-hederacea` | Glechoma hederacea | 31 → 25 |
| `glechoma-hirsuta` | Glechoma hirsuta | 0 → 0 |
| `gleditsia-triacanthos` | Gleditsia triacanthos | 6 → 7 |
| `glehnia-littoralis` | Glehnia littoralis | 7 → 17 |
| `gliricidia-sepium` | Gliricidia sepium | 22 → 33 |
| `gloriosa-superba` | Gloriosa superba | 18 → 27 |
| `glycine-max` | Glycine max | 75 → 22 |
| `glycyrrhiza-glabra` | Glycyrrhiza glabra | 41 → 30 |
| `glycyrrhiza-squamulosa` | Glycyrrhiza squamulosa | 0 → 0 |
| `glycyrrhiza-uralensis` | Glycyrrhiza uralensis | 21 → 27 |
| `gmelina-arborea` | Gmelina arborea | 2 → 25 |
| `gossypium-sp` | Gossypium sp | 10 → 0 |
| `gratifolia-officianalis` | Gratifolia officianalis | 0 → 0 |
| `grewia-asiatica` | Grewia asiatica | 6 → 13 |
| `grewia-bicolor` | Grewia bicolor | 0 → 0 |
| `grewia-flavescens` | Grewia flavescens | 0 → 0 |
| `grewia-tenax` | Grewia tenax | 0 → 3 |
| `grindelia-squarrosa` | Grindelia squarrosa | 20 → 23 |
| `guaiacum-sp` | Guaiacum sp. | 0 → 0 |
| `guatteria-discolor` | Guatteria discolor | 0 → 0 |
| `gymnema-sylvestre` | Gymnema sylvestre | 2 → 19 |
| `gymnostachyum-latifolium` | Gymnostachyum latifolium | 0 → 0 |
| `gynostemma-pentaphyllum` | Gynostemma pentaphyllum | 0 → 0 |
| `gypsophila-struthium` | Gypsophila struthium | 7 → 7 |
| `haematoxylum-campechianum` | Haematoxylum campechianum | 28 → 40 |
| `hamamelis-virginiana` | Hamamelis virginiana | 33 → 33 |
| `hamelia-patens` | Hamelia patens | 4 → 14 |
| `haplophyton-cimicidum` | Haplophyton cimicidum | 2 → 2 |
| `hardenbergia-violacea` | Hardenbergia violacea | 0 → 0 |
| `harpagophytum-procumbens` | Harpagophytum procumbens | 6 → 6 |
| `hedeoma-drummondii` | Hedeoma drummondii | 0 → 0 |
| `hedeoma-hispida` | Hedeoma hispida | 0 → 0 |
| `hedeoma-pulegioides` | Hedeoma pulegioides | 10 → 13 |
| `hedeoma-reverchonii` | Hedeoma reverchonii | 0 → 0 |
| `hedera-helix` | Hedera helix | 28 → 25 |
| `hedychium-flavum` | Hedychium flavum | 0 → 0 |
| `hedyotis-lawsoniae` | Hedyotis lawsoniae | 0 → 0 |
| `heimia-salicifolia` | Heimia salicifolia | 20 → 32 |
| `helianthus-annuus` | Helianthus annuus | 45 → 40 |
| `helianthus-tuberosus` | Helianthus tuberosus | 13 → 13 |
| `heliotropium-europaeum` | Heliotropium europaeum | 8 → 7 |
| `helleborus-niger` | Helleborus niger | 14 → 13 |
| `hemidesmus-indicus` | Hemidesmus indicus | 4 → 26 |
| `hemsleya-amabilis` | Hemsleya amabilis | 0 → 0 |
| `heracleum-laciniatum` | Heracleum laciniatum | 0 → 0 |
| `heracleum-sphondylium` | Heracleum sphondylium | 3 → 3 |
| `hesperis-matronalis` | Hesperis matronalis | 7 → 9 |
| `hibiscus-mutabilis` | Hibiscus mutabilis | 17 → 22 |
| `hibiscus-syriacus` | Hibiscus syriacus | 12 → 22 |
| `hippeastrum-vittatum` | Hippeastrum vittatum | 0 → 0 |
| `hippomane-mancinella` | Hippomane mancinella | 28 → 27 |
| `hippophae-rhamnoides` | Hippophae rhamnoides | 5 → 8 |
| `hoffmannia-strigillosa` | Hoffmannia strigillosa | 0 → 0 |
| `holarrhena-pubescens` | Holarrhena pubescens | 0 → 33 |
| `hopea-brevipetiolaris` | Hopea brevipetiolaris | 0 → 0 |
| `hopea-cordifolia` | Hopea cordifolia | 0 → 0 |
| `hopea-jucunda` | Hopea jucunda | 0 → 0 |
| `hordeum-vulgare` | Hordeum vulgare | 28 → 28 |
| `hoslundia-opposita` | Hoslundia opposita | 33 → 20 |
| `houttuynia-cordata` | Houttuynia cordata | 37 → 40 |
| `humulus-lupulus` | Humulus lupulus | 32 → 32 |
| `huperzia-spp` | Huperzia spp | 0 → 0 |
| `hura-crepitans` | Hura crepitans | 13 → 25 |
| `hyacinthus-orientalis` | Hyacinthus orientalis | 1 → 0 |
| `hydnocarpus-kurzii` | Hydnocarpus kurzii | 12 → 24 |
| `hydrangea-arborescens` | Hydrangea arborescens | 17 → 19 |
| `hydrangea-paniculata` | Hydrangea paniculata | 3 → 3 |
| `hydrastis-canadensis` | Hydrastis canadensis | 28 → 24 |
| `hygrophila-auriculata` | Hygrophila auriculata | 0 → 24 |
| `hymenaea-courbaril` | Hymenaea courbaril | 35 → 32 |
| `hymenaea-verrucosa` | Hymenaea verrucosa | 0 → 5 |
| `hyoscyamus-niger` | Hyoscyamus niger | 46 → 44 |
| `hypericum-androsaemum` | Hypericum androsaemum | 3 → 4 |
| `hypericum-patulum` | Hypericum patulum | 1 → 4 |
| `hypericum-perforatum` | Hypericum perforatum | 24 → 24 |
| `hyptis-capitata` | Hyptis capitata | 11 → 21 |
| `hyptis-dilatata` | Hyptis dilatata | 0 → 0 |
| `hyssopus-officinalis-subsp-aristatus` | Hyssopus officinalis subsp. aristatus | 0 → 0 |
| `iberis-amara` | Iberis amara | 5 → 10 |
| `ilex-paraguariensis` | Ilex paraguariensis | 8 → 13 |
| `ilex-verticillata` | Ilex verticillata | 8 → 8 |
| `illicium-verum` | Illicium verum | 17 → 32 |
| `impatiens-balsamina` | Impatiens balsamina | 17 → 22 |
| `indigofera-tinctoria` | Indigofera tinctoria | 46 → 26 |
| `inga-edulis` | Inga edulis | 0 → 0 |
| `inga-punctata` | Inga punctata | 0 → 0 |
| `inonotus-obliquus` | Inonotus obliquus | 0 → 0 |
| `inula-helenium` | Inula helenium | 39 → 35 |
| `ipomoea-aquatica` | Ipomoea aquatica | 2 → 18 |
| `ipomoea-batatas` | Ipomoea batatas | 18 → 22 |
| `ipomoea-purga` | Ipomoea purga | 6 → 6 |
| `ipomoea-violacea` | Ipomoea violacea | 0 → 2 |
| `iris-missouriensis` | Iris missouriensis | 0 → 0 |
| `iris-versicolor` | Iris versicolor | 12 → 17 |
| `iris-x-germanica` | Iris × germanica | 0 → 22 |
| `isatis-tinctoria` | Isatis tinctoria | 3 → 9 |
| `isertia-hypoleuca` | Isertia hypoleuca | 0 → 0 |
| `isodon-grandifolius` | Isodon grandifolius | 0 → 0 |
| `jacaranda-caucana` | Jacaranda caucana | 0 → 0 |
| `jasminum-officinale` | Jasminum officinale | 22 → 22 |
| `jasminum-sambac` | Jasminum sambac | 22 → 27 |
| `jateorhiza-palmata` | Jateorhiza palmata | 6 → 17 |
| `jatropha-curcas` | Jatropha curcas | 88 → 61 |
| `juglans-cinerea` | Juglans cinerea | 12 → 14 |
| `juglans-nigra` | Juglans nigra | 8 → 10 |
| `juglans-regia` | Juglans regia | 65 → 39 |
| `juncus-effusus` | Juncus effusus | 20 → 20 |
| `juncus-roemerianus` | Juncus roemerianus | 0 → 0 |
| `juniperus-communis` | Juniperus communis | 47 → 44 |
| `juniperus-horizontalis` | Juniperus horizontalis | 1 → 2 |
| `juniperus-oxycedrus` | Juniperus oxycedrus | 22 → 23 |
| `juniperus-sabina` | Juniperus sabina | 22 → 15 |
| `juniperus-virginiana` | Juniperus virginiana | 14 → 13 |
| `justicia-adhatoda` | Justicia adhatoda | 6 → 16 |
| `justicia-gendarussa` | Justicia gendarussa | 23 → 38 |
| `kaempferia-galanga` | Kaempferia galanga | 21 → 35 |
| `kalanchoe-gastonis-bonnieri` | Kalanchoe gastonis-bonnieri | 0 → 0 |
| `kalanchoe-pinnata` | Kalanchoe pinnata | 2 → 41 |
| `kalmia-latifolia` | Kalmia latifolia | 26 → 22 |
| `kayea-stylosa` | Kayea stylosa | 0 → 0 |
| `kennedia-coccinea` | Kennedia coccinea | 0 → 0 |
| `kennedia-nigricans` | Kennedia nigricans | 0 → 0 |
| `kennedia-procurrens` | Kennedia procurrens | 0 → 0 |
| `kennedia-rubicunda` | Kennedia rubicunda | 0 → 0 |
| `kleinhovia-hospita` | Kleinhovia hospita | 1 → 11 |
| `krameria-spp` | Krameria spp | 0 → 0 |
| `lablab-purpureus` | Lablab purpureus | 16 → 19 |
| `laburnum-alpinum` | Laburnum alpinum | 0 → 0 |
| `laburnum-anagyroides` | Laburnum anagyroides | 2 → 6 |
| `lactuca-sativa` | Lactuca sativa | 31 → 23 |
| `lactuca-virosa` | Lactuca virosa | 20 → 19 |
| `lagenaria-siceraria` | Lagenaria siceraria | 29 → 32 |
| `lagerstroemia-indica` | Lagerstroemia indica | 16 → 22 |
| `lagochilus-inebrians` | Lagochilus inebrians | 0 → 0 |
| `lamium-sp` | Lamium sp | 0 → 0 |
| `lantana-camara` | Lantana camara | 55 → 50 |
| `larix-laricina` | Larix laricina | 8 → 13 |
| `larrea-tridentata` | Larrea tridentata | 13 → 27 |
| `lasianthus-chinensis` | Lasianthus chinensis | 0 → 0 |
| `latua-pubiflora` | Latua pubiflora | 0 → 0 |
| `laurus-nobilis` | Laurus nobilis | 18 → 18 |
| `lavandula-angustifolia` | Lavandula angustifolia | 10 → 13 |
| `lavandula-latifolia` | Lavandula latifolia | 14 → 13 |
| `lavandula-sp` | Lavandula sp | 0 → 0 |
| `lavandula-spica` | Lavandula spica | 2 → 2 |
| `lavandula-x-intermedia` | Lavandula × intermedia | 0 → 0 |
| `lawsonia-inermis` | Lawsonia inermis | 35 → 33 |
| `lentinus-edodes` | Lentinus edodes | 0 → 0 |
| `leonotis-leonurus` | Leonotis leonurus | 4 → 10 |
| `leonurus-cardiaca` | Leonurus cardiaca | 25 → 32 |
| `lepechinia-calycina` | Lepechinia calycina | 0 → 0 |
| `lepechinia-caulescens` | Lepechinia caulescens | 0 → 0 |
| `lepechinia-glomerata` | Lepechinia glomerata | 0 → 0 |
| `lepechinia-hastata` | Lepechinia hastata | 0 → 0 |
| `lepechinia-meyenii` | Lepechinia meyenii | 0 → 1 |
| `lepidium-meyenii` | Lepidium meyenii | 0 → 0 |
| `lepidium-sativum` | Lepidium sativum | 14 → 26 |
| `leptospermum-polygalifolium` | Leptospermum polygalifolium | 0 → 0 |
| `leptospermum-scoparium` | Leptospermum scoparium | 0 → 0 |
| `lespedeza-cyrtobotrya` | Lespedeza cyrtobotrya | 0 → 0 |
| `levisticum-officinale` | Levisticum officinale | 18 → 17 |
| `ligustrum-japonicum` | Ligustrum japonicum | 3 → 5 |
| `ligustrum-lucidum` | Ligustrum lucidum | 16 → 23 |
| `ligustrum-vulgare` | Ligustrum vulgare | 6 → 6 |
| `limnophila-rugosa` | Limnophila rugosa | 0 → 5 |
| `limonia-acidissima` | Limonia acidissima | 0 → 16 |
| `lindera-benzoin` | Lindera benzoin | 8 → 14 |
| `linum-usitatissimum` | Linum usitatissimum | 28 → 28 |
| `lippia-alba` | Lippia alba | 15 → 44 |
| `lippia-dulcis` | Lippia dulcis | 20 → 26 |
| `lippia-javanica` | Lippia javanica | 0 → 0 |
| `liquidambar-orientalis` | Liquidambar orientalis | 24 → 24 |
| `liquidambar-styraciflua` | Liquidambar styraciflua | 50 → 45 |
| `lithocarpus-elizabethae` | Lithocarpus elizabethae | 0 → 0 |
| `lithocarpus-haipinii` | Lithocarpus haipinii | 0 → 0 |
| `lobelia-inflata` | Lobelia inflata | 19 → 28 |
| `lobelia-tupa` | Lobelia tupa | 0 → 0 |
| `lolium-temulentum` | Lolium temulentum | 11 → 8 |
| `lonicera-japonica` | Lonicera japonica | 34 → 35 |
| `lophatherum-gracile` | Lophatherum gracile | 15 → 27 |
| `lophophora-williamsii` | Lophophora williamsii | 10 → 24 |
| `ludwigia-adscendens` | Ludwigia adscendens | 0 → 3 |
| `ludwigia-epilobioides` | Ludwigia epilobioides | 0 → 0 |
| `luffa-aegyptiaca` | Luffa aegyptiaca | 45 → 24 |
| `lumnitzera-racemosa` | Lumnitzera racemosa | 0 → 2 |
| `lupinus-albus` | Lupinus albus | 9 → 12 |
| `lupinus-angustifolius` | Lupinus angustifolius | 2 → 2 |
| `lupinus-luteus` | Lupinus luteus | 0 → 0 |
| `lupinus-mutabilis` | Lupinus mutabilis | 0 → 0 |
| `lupinus-perennis` | Lupinus perennis | 0 → 0 |
| `lupinus-polyphyllus` | Lupinus polyphyllus | 0 → 1 |
| `lycium-barbarum` | Lycium barbarum | 5 → 14 |
| `lycium-chilense` | Lycium chilense | 0 → 0 |
| `lycium-chinense` | Lycium chinense | 32 → 28 |
| `lycopodium-annotinum` | Lycopodium annotinum | 0 → 0 |
| `lycopodium-clavatum` | Lycopodium clavatum | 16 → 23 |
| `lycopodium-complanatum` | Lycopodium complanatum | 0 → 1 |
| `lycopodium-fawcettii` | Lycopodium fawcettii | 0 → 0 |
| `lycopodium-lucidum` | Lycopodium lucidum | 0 → 0 |
| `lycopus-americanus` | Lycopus americanus | 0 → 0 |
| `lycopus-lucidus` | Lycopus lucidus | 11 → 16 |
| `lycopus-uniflorus` | Lycopus uniflorus | 0 → 0 |
| `lycopus-virginicus` | Lycopus virginicus | 15 → 16 |
| `lycoris-radiata` | Lycoris radiata | 17 → 23 |
| `lycoris-squamigera` | Lycoris squamigera | 3 → 3 |
| `lygodium-japonicum` | Lygodium japonicum | 17 → 20 |
| `lythrum-salicaria` | Lythrum salicaria | 8 → 10 |
| `maackia-amurensis` | Maackia amurensis | 0 → 0 |
| `macadamia-spp` | Macadamia spp | 0 → 0 |
| `macleaya-cordata` | Macleaya cordata | 17 → 19 |
| `maclura-pomifera` | Maclura pomifera | 3 → 2 |
| `macrotyloma-axillare` | Macrotyloma axillare | 0 → 0 |
| `madhuca-microphylla` | Madhuca microphylla | 0 → 0 |
| `magnolia-denudata` | Magnolia denudata | 2 → 11 |
| `magnolia-kobus` | Magnolia kobus | 3 → 3 |
| `magnolia-obovata` | Magnolia obovata | 10 → 16 |
| `magnolia-officinalis` | Magnolia officinalis | 33 → 26 |
| `malachra-capitata` | Malachra capitata | 0 → 5 |
| `malpighia-glabra` | Malpighia glabra | 9 → 15 |
| `malus-domestica` | Malus domestica | 0 → 0 |
| `malva-neglecta` | Malva neglecta | 10 → 11 |
| `malva-parviflora` | Malva parviflora | 12 → 18 |
| `malva-sylvestris` | Malva sylvestris | 17 → 21 |
| `mammea-americana` | Mammea americana | 33 → 39 |
| `mandragora-officinarum` | Mandragora officinarum | 5 → 14 |
| `mangifera-indica` | Mangifera indica | 71 → 61 |
| `manihot-esculenta` | Manihot esculenta | 31 → 29 |
| `manilkara-zapota` | Manilkara zapota | 19 → 38 |
| `maranta-arundinacea` | Maranta arundinacea | 13 → 24 |
| `marrubium-vulgare` | Marrubium vulgare | 49 → 33 |
| `mauritia-flexuosa` | Mauritia flexuosa | 4 → 5 |
| `maytenus-aquifolium` | Maytenus aquifolium | 0 → 0 |
| `maytenus-boaria` | Maytenus boaria | 1 → 1 |
| `melaleuca-alternifolia` | Melaleuca alternifolia | 1 → 1 |
| `melaleuca-bracteata` | Melaleuca bracteata | 1 → 1 |
| `melaleuca-cajuputi` | Melaleuca cajuputi | 0 → 0 |
| `melaleuca-linariifolia` | Melaleuca linariifolia | 1 → 1 |
| `melaleuca-sp` | Melaleuca sp | 0 → 0 |
| `melaleuca-viridiflora` | Melaleuca viridiflora | 4 → 4 |
| `melampyrum-arvense` | Melampyrum arvense | 0 → 0 |
| `melanoxylon-brauna` | Melanoxylon brauna | 0 → 0 |
| `melia-azedarach` | Melia azedarach | 88 → 63 |
| `melilotus-officinalis` | Melilotus officinalis | 18 → 25 |
| `melissa-officinalis` | Melissa officinalis | 31 → 27 |
| `melochia-tomentosa` | Melochia tomentosa | 2 → 4 |
| `menispermum-canadense` | Menispermum canadense | 20 → 21 |
| `mentha-aquatica` | Mentha aquatica | 8 → 22 |
| `mentha-japonica` | Mentha japonica | 0 → 0 |
| `mentha-longifolia` | Mentha longifolia | 16 → 16 |
| `mentha-pulegium` | Mentha pulegium | 17 → 17 |
| `mentha-requienii` | Mentha requienii | 0 → 0 |
| `mentha-sp` | Mentha sp | 2 → 0 |
| `mentha-spicata` | Mentha spicata | 14 → 21 |
| `menyanthes-trifoliata` | Menyanthes trifoliata | 39 → 42 |
| `mercurialis-annua` | Mercurialis annua | 11 → 9 |
| `mesua-ferrea` | Mesua ferrea | 5 → 19 |
| `metrosideros-excelsa` | Metrosideros excelsa | 2 → 3 |
| `metrosideros-nervulosa` | Metrosideros nervulosa | 0 → 0 |
| `metrosideros-sclerocarpa` | Metrosideros sclerocarpa | 0 → 0 |
| `micromeria-benthamii` | Micromeria benthamii | 0 → 0 |
| `micromeria-croatica` | Micromeria croatica | 0 → 0 |
| `micromeria-dalmatica` | Micromeria dalmatica | 0 → 0 |
| `micromeria-juliana` | Micromeria juliana | 0 → 0 |
| `micromeria-myrtifolia` | Micromeria myrtifolia | 0 → 0 |
| `micromeria-teneriffae` | Micromeria teneriffae | 0 → 0 |
| `micromyrtus-striata` | Micromyrtus striata | 0 → 0 |
| `mimosa-pudica` | Mimosa pudica | 23 → 34 |
| `mimulus-glabratus` | Mimulus glabratus | 0 → 0 |
| `minthostachys-mollis` | Minthostachys mollis | 0 → 0 |
| `mirabilis-expansa` | Mirabilis expansa | 0 → 0 |
| `mirabilis-jalapa` | Mirabilis jalapa | 34 → 34 |
| `mitchella-repens` | Mitchella repens | 15 → 17 |
| `mitragyna-speciosa` | Mitragyna speciosa | 3 → 10 |
| `mitrephora-heyneana` | Mitrephora heyneana | 0 → 0 |
| `moghania-macrophylla` | Moghania macrophylla | 0 → 8 |
| `momordica-charantia` | Momordica charantia | 55 → 57 |
| `monarda-citriodora` | Monarda citriodora | 0 → 1 |
| `monarda-clinopodia` | Monarda clinopodia | 0 → 0 |
| `monarda-didyma` | Monarda didyma | 10 → 12 |
| `monarda-fistulosa` | Monarda fistulosa | 16 → 21 |
| `monarda-lindheimeri` | Monarda lindheimeri | 0 → 0 |
| `monarda-media` | Monarda media | 0 → 0 |
| `monarda-punctata` | Monarda punctata | 15 → 15 |
| `monarda-russeliana` | Monarda russeliana | 0 → 0 |
| `montanoa-tomentosa` | Montanoa tomentosa | 22 → 20 |
| `montrichardia-arborescens` | Montrichardia arborescens | 5 → 12 |
| `morinda-citrifolia` | Morinda citrifolia | 9 → 36 |
| `morinda-sp` | Morinda sp | 0 → 0 |
| `moringa-oleifera` | Moringa oleifera | 31 → 40 |
| `morus-alba` | Morus alba | 69 → 33 |
| `morus-serrata` | Morus serrata | 0 → 0 |
| `muntingia-calabura` | Muntingia calabura | 2 → 8 |
| `murraya-sp` | Murraya sp | 0 → 0 |
| `musa-x-paradisiaca` | Musa × paradisiaca | 0 → 59 |
| `myrciaria-dubia` | Myrciaria dubia | 0 → 0 |
| `myrica-cerifera` | Myrica cerifera | 28 → 32 |
| `myristica-fragrans` | Myristica fragrans | 30 → 43 |
| `myroxylon-balsamum` | Myroxylon balsamum | 19 → 49 |
| `myrrhis-odorata` | Myrrhis odorata | 21 → 22 |
| `myrtus-communis` | Myrtus communis | 31 → 24 |
| `nandina-domestica` | Nandina domestica | 23 → 21 |
| `narcissus-tazetta` | Narcissus tazetta | 20 → 21 |
| `nasturtium-officinale` | Nasturtium officinale | 52 → 40 |
| `nelumbo-nucifera` | Nelumbo nucifera | 66 → 46 |
| `nepeta-cataria` | Nepeta cataria | 34 → 28 |
| `nepeta-racemosa` | Nepeta racemosa | 0 → 0 |
| `nerium-oleander` | Nerium oleander | 43 → 46 |
| `neurolaena-lobata` | Neurolaena lobata | 10 → 29 |
| `nicotiana-glauca` | Nicotiana glauca | 5 → 8 |
| `nicotiana-rustica` | Nicotiana rustica | 9 → 11 |
| `nicotiana-tabacum` | Nicotiana tabacum | 59 → 46 |
| `nigella-sativa` | Nigella sativa | 24 → 23 |
| `nuytsia-floribunda` | Nuytsia floribunda | 0 → 0 |
| `nyssa-sylvatica` | Nyssa sylvatica | 1 → 1 |
| `ocimum-basilicum` | Ocimum basilicum | 55 → 36 |
| `ocimum-gratissimum` | Ocimum gratissimum | 46 → 34 |
| `ocimum-kilimandscharicum` | Ocimum kilimandscharicum | 1 → 3 |
| `ocimum-sp` | Ocimum sp | 5 → 0 |
| `ocotea-glaziovii` | Ocotea glaziovii | 0 → 0 |
| `oenanthe-aquatica` | Oenanthe aquatica | 8 → 8 |
| `oenanthe-crocata` | Oenanthe crocata | 6 → 5 |
| `oenanthe-javanica` | Oenanthe javanica | 0 → 0 |
| `oenothera-biennis` | Oenothera biennis | 6 → 8 |
| `ononis-spinosa` | Ononis spinosa | 8 → 8 |
| `ophiopogon-japonicus` | Ophiopogon japonicus | 12 → 28 |
| `opopanax-chironium` | Opopanax chironium | 3 → 6 |
| `opuntia-ficus-indica` | Opuntia ficus-indica | 7 → 19 |
| `origanum-compactum` | Origanum compactum | 0 → 0 |
| `origanum-creticum` | Origanum creticum | 4 → 0 |
| `origanum-majorana` | Origanum majorana | 18 → 24 |
| `origanum-minutiflorum` | Origanum minutiflorum | 0 → 0 |
| `origanum-onites` | Origanum onites | 1 → 1 |
| `origanum-sipyleum` | Origanum sipyleum | 0 → 0 |
| `origanum-syriacum` | Origanum syriacum | 0 → 0 |
| `origanum-vulgare-subsp-hirtum` | Origanum vulgare subsp. hirtum | 0 → 0 |
| `origanum-vulgare-var-hirtum` | Origanum vulgare var. hirtum | 0 → 0 |
| `ormosia-excelsa` | Ormosia excelsa | 0 → 0 |
| `ornithogalum-umbellatum` | Ornithogalum umbellatum | 3 → 1 |
| `orthosphenia-mexicana` | Orthosphenia mexicana | 0 → 0 |
| `oryza-sativa` | Oryza sativa | 46 → 28 |
| `oxalis-tuberosa` | Oxalis tuberosa | 0 → 0 |
| `pachyrhizus-erosus` | Pachyrhizus erosus | 11 → 16 |
| `paeonia-lactiflora` | Paeonia lactiflora | 4 → 27 |
| `paeonia-officinalis` | Paeonia officinalis | 16 → 16 |
| `palaquium-grande` | Palaquium grande | 0 → 0 |
| `panax-ginseng` | Panax ginseng | 40 → 35 |
| `panax-japonicus` | Panax japonicus | 0 → 7 |
| `panax-notoginseng` | Panax notoginseng | 0 → 0 |
| `panax-pseudoginseng` | Panax pseudoginseng | 0 → 26 |
| `panax-quinquefolius` | Panax quinquefolius | 22 → 27 |
| `pancratium-maritimum` | Pancratium maritimum | 3 → 3 |
| `papaver-bracteatum` | Papaver bracteatum | 0 → 0 |
| `papaver-somniferum` | Papaver somniferum | 61 → 51 |
| `paris-polyphylla` | Paris polyphylla | 19 → 25 |
| `paris-quadrifolia` | Paris quadrifolia | 17 → 15 |
| `parthenium-hysterophorus` | Parthenium hysterophorus | 29 → 28 |
| `parthenium-integrifolium` | Parthenium integrifolium | 1 → 1 |
| `parthenocissus-quinquefolia` | Parthenocissus quinquefolia | 22 → 21 |
| `passiflora-edulis` | Passiflora edulis | 1 → 1 |
| `passiflora-foetida` | Passiflora foetida | 9 → 25 |
| `passiflora-incarnata` | Passiflora incarnata | 23 → 31 |
| `passiflora-ligularis` | Passiflora ligularis | 0 → 0 |
| `passiflora-quadrangularis` | Passiflora quadrangularis | 25 → 26 |
| `passiflora-suberosa` | Passiflora suberosa | 0 → 0 |
| `pastinaca-sativa` | Pastinaca sativa | 7 → 7 |
| `paullinia-cupana` | Paullinia cupana | 11 → 12 |
| `pavonia-spinifex` | Pavonia spinifex | 19 → 19 |
| `pedicularis-longiflora` | Pedicularis longiflora | 0 → 0 |
| `pedicularis-palustris` | Pedicularis palustris | 0 → 0 |
| `peganum-harmala` | Peganum harmala | 31 → 37 |
| `peperomia-galioides` | Peperomia galioides | 0 → 2 |
| `peperomia-pereskiifolia` | Peperomia pereskiifolia | 0 → 0 |
| `pereskia-aculeata` | Pereskia aculeata | 0 → 0 |
| `pericopsis-laxiflora` | Pericopsis laxiflora | 0 → 0 |
| `perideridia-gairdneri` | Perideridia gairdneri | 0 → 2 |
| `perilla-frutescens` | Perilla frutescens | 22 → 27 |
| `persea-americana` | Persea americana | 81 → 58 |
| `persea-schiedeana` | Persea schiedeana | 0 → 1 |
| `petasites-hybridus` | Petasites hybridus | 1 → 1 |
| `petasites-japonicus` | Petasites japonicus | 6 → 6 |
| `petiveria-alliacea` | Petiveria alliacea | 73 → 72 |
| `petroselinum-crispum` | Petroselinum crispum | 24 → 24 |
| `peucedanum-ostruthium` | Peucedanum ostruthium | 7 → 18 |
| `peumus-boldus` | Peumus boldus | 17 → 17 |
| `phaseolus-acutifolius` | Phaseolus acutifolius | 0 → 0 |
| `phaseolus-coccineus` | Phaseolus coccineus | 0 → 0 |
| `phaseolus-lunatus` | Phaseolus lunatus | 7 → 4 |
| `phaseolus-spp` | Phaseolus spp | 0 → 0 |
| `phellodendron-amurense` | Phellodendron amurense | 38 → 24 |
| `phillyrea-latifolia` | Phillyrea latifolia | 4 → 4 |
| `phoenix-dactylifera` | Phoenix dactylifera | 38 → 27 |
| `phoradendron-juniperinum` | Phoradendron juniperinum | 3 → 3 |
| `phragmites-australis` | Phragmites australis | 23 → 26 |
| `phyllanthus-acidus` | Phyllanthus acidus | 3 → 9 |
| `phyllanthus-amarus` | Phyllanthus amarus | 7 → 9 |
| `phyllanthus-emblica` | Phyllanthus emblica | 4 → 23 |
| `phyllanthus-flexuosus` | Phyllanthus flexuosus | 0 → 0 |
| `phyllanthus-niruri` | Phyllanthus niruri | 32 → 36 |
| `phyllanthus-reticulatus` | Phyllanthus reticulatus | 4 → 24 |
| `physalis-angulata` | Physalis angulata | 32 → 34 |
| `physalis-ixocarpa` | Physalis ixocarpa | 1 → 1 |
| `physalis-peruviana` | Physalis peruviana | 1 → 1 |
| `physostigma-venenosum` | Physostigma venenosum | 5 → 17 |
| `phytelephas-aequatorialis` | Phytelephas aequatorialis | 0 → 0 |
| `phytelephas-macrocarpa` | Phytelephas macrocarpa | 0 → 1 |
| `phytolacca-americana` | Phytolacca americana | 25 → 26 |
| `picea-mariana` | Picea mariana | 6 → 6 |
| `picramnia-sellowii` | Picramnia sellowii | 0 → 0 |
| `picrasma-excelsa` | Picrasma excelsa | 11 → 17 |
| `picrasma-quassioides` | Picrasma quassioides | 2 → 9 |
| `picrorhiza-kurrooa` | Picrorhiza kurrooa | 0 → 17 |
| `pilocarpus-jaborandi` | Pilocarpus jaborandi | 7 → 13 |
| `pilocarpus-microphyllus` | Pilocarpus microphyllus | 18 → 18 |
| `pilocarpus-pennatifolius` | Pilocarpus pennatifolius | 0 → 1 |
| `pilocarpus-racemosus` | Pilocarpus racemosus | 0 → 0 |
| `pimenta-dioica` | Pimenta dioica | 11 → 13 |
| `pimenta-racemosa` | Pimenta racemosa | 27 → 24 |
| `pimpinella-anisum` | Pimpinella anisum | 26 → 29 |
| `pinellia-ternata` | Pinellia ternata | 24 → 27 |
| `pinus-cembroides` | Pinus cembroides | 0 → 0 |
| `pinus-echinata` | Pinus echinata | 0 → 0 |
| `pinus-edulis` | Pinus edulis | 13 → 17 |
| `pinus-elliottii` | Pinus elliottii | 0 → 0 |
| `pinus-gerardiana` | Pinus gerardiana | 0 → 5 |
| `pinus-kesiya` | Pinus kesiya | 0 → 0 |
| `pinus-mugo` | Pinus mugo | 5 → 12 |
| `pinus-palustris` | Pinus palustris | 28 → 23 |
| `pinus-pinea` | Pinus pinea | 1 → 1 |
| `pinus-roxburghii` | Pinus roxburghii | 4 → 23 |
| `pinus-strobus` | Pinus strobus | 14 → 15 |
| `pinus-sylvestris` | Pinus sylvestris | 3 → 16 |
| `piper-auritum` | Piper auritum | 3 → 21 |
| `piper-cubeba` | Piper cubeba | 29 → 48 |
| `piper-methysticum` | Piper methysticum | 15 → 29 |
| `piper-nigrum` | Piper nigrum | 50 → 41 |
| `piptanthus-nepalensis` | Piptanthus nepalensis | 0 → 0 |
| `pistacia-lentiscus` | Pistacia lentiscus | 42 → 24 |
| `pistacia-major` | Pistacia major | 0 → 0 |
| `pistacia-vera` | Pistacia vera | 16 → 16 |
| `plantago-asiatica` | Plantago asiatica | 15 → 31 |
| `plantago-major` | Plantago major | 98 → 59 |
| `plantago-ovata` | Plantago ovata | 6 → 10 |
| `platanus-occidentalis` | Platanus occidentalis | 3 → 6 |
| `platonia-insignis` | Platonia insignis | 0 → 0 |
| `plectranthus-urticifolius` | Plectranthus urticifolius | 0 → 0 |
| `pluchea-carolinensis` | Pluchea carolinensis | 4 → 15 |
| `plumeria-obtusa` | Plumeria obtusa | 11 → 11 |
| `podocarpus-spicatus` | Podocarpus spicatus | 0 → 0 |
| `podophyllum-hexandrum` | Podophyllum hexandrum | 2 → 21 |
| `podophyllum-peltatum` | Podophyllum peltatum | 18 → 23 |
| `podophyllum-pleianthum` | Podophyllum pleianthum | 0 → 2 |
| `pogostemon-cablin` | Pogostemon cablin | 12 → 22 |
| `polianthes-tuberosa` | Polianthes tuberosa | 4 → 15 |
| `polygala-tenuifolia` | Polygala tenuifolia | 13 → 14 |
| `polygonatum-multiflorum` | Polygonatum multiflorum | 14 → 19 |
| `polygonum-aviculare` | Polygonum aviculare | 44 → 31 |
| `polygonum-plebeium` | Polygonum plebeium | 0 → 5 |
| `polypodium-vulgare` | Polypodium vulgare | 19 → 23 |
| `pongamia-pinnata` | Pongamia pinnata | 7 → 28 |
| `populus-nigra` | Populus nigra | 14 → 14 |
| `porophyllum-ruderale` | Porophyllum ruderale | 3 → 6 |
| `portulaca-oleracea` | Portulaca oleracea | 86 → 55 |
| `pothomorphe-sp` | Pothomorphe sp. | 0 → 0 |
| `pouteria-caimito` | Pouteria caimito | 0 → 0 |
| `pouteria-torta` | Pouteria torta | 0 → 0 |
| `pouteria-viridis` | Pouteria viridis | 0 → 0 |
| `prunella-vulgaris` | Prunella vulgaris | 38 → 31 |
| `prunus-africana` | Prunus africana | 0 → 0 |
| `prunus-armeniaca` | Prunus armeniaca | 47 → 35 |
| `prunus-avium` | Prunus avium | 3 → 3 |
| `prunus-cerasus` | Prunus cerasus | 15 → 16 |
| `prunus-domestica` | Prunus domestica | 20 → 19 |
| `prunus-laurocerasus` | Prunus laurocerasus | 16 → 16 |
| `prunus-mahaleb` | Prunus mahaleb | 9 → 8 |
| `prunus-maximowiczii` | Prunus maximowiczii | 0 → 0 |
| `prunus-nipponica` | Prunus nipponica | 0 → 0 |
| `prunus-pensylvanica` | Prunus pensylvanica | 0 → 0 |
| `prunus-persica` | Prunus persica | 38 → 35 |
| `prunus-spinosa` | Prunus spinosa | 13 → 13 |
| `prunus-spp` | Prunus spp | 0 → 0 |
| `pseudeminia-comosa` | Pseudeminia comosa | 0 → 0 |
| `pseudoeriosema-borianii` | Pseudoeriosema borianii | 0 → 0 |
| `pseudovigna-argentea` | Pseudovigna argentea | 0 → 0 |
| `psidium-guajava` | Psidium guajava | 49 → 54 |
| `psophocarpus-tetragonolobus` | Psophocarpus tetragonolobus | 0 → 8 |
| `psychotria-adenophylla` | Psychotria adenophylla | 0 → 0 |
| `pteridium-aquilinum` | Pteridium aquilinum | 15 → 23 |
| `pterocarpus-angolensis` | Pterocarpus angolensis | 1 → 1 |
| `pterocarpus-marsupium` | Pterocarpus marsupium | 4 → 23 |
| `pterocarpus-santalinus` | Pterocarpus santalinus | 8 → 23 |
| `pterospermum-acerifolium` | Pterospermum acerifolium | 0 → 14 |
| `pterospermum-suberifolium` | Pterospermum suberifolium | 0 → 4 |
| `pterospermum-xylocarpum` | Pterospermum xylocarpum | 0 → 2 |
| `ptychopetalum-olacoides` | Ptychopetalum olacoides | 5 → 5 |
| `pueraria-montana` | Pueraria montana | 0 → 0 |
| `pulsatilla-chinensis` | Pulsatilla chinensis | 3 → 8 |
| `punica-granatum` | Punica granatum | 62 → 56 |
| `pycnanthemum-albescens` | Pycnanthemum albescens | 2 → 2 |
| `pycnanthemum-beadlei` | Pycnanthemum beadlei | 0 → 0 |
| `pycnanthemum-californicum` | Pycnanthemum californicum | 0 → 0 |
| `pycnanthemum-clinopodioides` | Pycnanthemum clinopodioides | 0 → 0 |
| `pycnanthemum-curvipes` | Pycnanthemum curvipes | 0 → 0 |
| `pycnanthemum-flexuosum` | Pycnanthemum flexuosum | 0 → 0 |
| `pycnanthemum-incanum` | Pycnanthemum incanum | 1 → 1 |
| `pycnanthemum-loomisii` | Pycnanthemum loomisii | 0 → 0 |
| `pycnanthemum-montanum` | Pycnanthemum montanum | 0 → 0 |
| `pycnanthemum-muticum` | Pycnanthemum muticum | 0 → 0 |
| `pycnanthemum-nudum` | Pycnanthemum nudum | 0 → 0 |
| `pycnanthemum-pycnanthemoides` | Pycnanthemum pycnanthemoides | 0 → 0 |
| `pycnanthemum-setosum` | Pycnanthemum setosum | 0 → 0 |
| `pycnanthemum-tenuifolium` | Pycnanthemum tenuifolium | 0 → 0 |
| `pycnanthemum-torreyi` | Pycnanthemum torreyi | 0 → 0 |
| `pycnanthemum-verticillatum` | Pycnanthemum verticillatum | 0 → 0 |
| `pycnanthemum-virginianum` | Pycnanthemum virginianum | 2 → 4 |
| `pyropolyporus-fomentarius` | Pyropolyporus fomentarius | 0 → 0 |
| `pyrus-communis` | Pyrus communis | 12 → 11 |
| `quassia-amara` | Quassia amara | 33 → 41 |
| `quercus-alba` | Quercus alba | 15 → 17 |
| `quercus-infectoria` | Quercus infectoria | 3 → 4 |
| `quercus-phellos` | Quercus phellos | 0 → 0 |
| `quercus-robur` | Quercus robur | 16 → 16 |
| `quercus-rubra` | Quercus rubra | 2 → 2 |
| `quercus-stellata` | Quercus stellata | 1 → 1 |
| `quercus-suber` | Quercus suber | 0 → 0 |
| `quercus-velutina` | Quercus velutina | 9 → 9 |
| `quillaja-saponaria` | Quillaja saponaria | 11 → 17 |
| `ranunculus-bulbosus` | Ranunculus bulbosus | 3 → 3 |
| `rauvolfia-serpentina` | Rauvolfia serpentina | 17 → 18 |
| `rauvolfia-tetraphylla` | Rauvolfia tetraphylla | 3 → 19 |
| `rauvolfia-vomitoria` | Rauvolfia vomitoria | 34 → 26 |
| `rehmannia-glutinosa` | Rehmannia glutinosa | 48 → 32 |
| `rhamnus-cathartica` | Rhamnus cathartica | 7 → 7 |
| `rheum-officinale` | Rheum officinale | 39 → 35 |
| `rheum-palmatum` | Rheum palmatum | 6 → 6 |
| `rheum-rhabarbarum` | Rheum rhabarbarum | 5 → 8 |
| `rhizophora-mangle` | Rhizophora mangle | 31 → 38 |
| `rhizophora-mucronata` | Rhizophora mucronata | 0 → 6 |
| `rhododendron-anthopogon` | Rhododendron anthopogon | 0 → 1 |
| `rhododendron-arboreum` | Rhododendron arboreum | 0 → 5 |
| `rhododendron-falconeri` | Rhododendron falconeri | 0 → 1 |
| `rhododendron-ferrugineum` | Rhododendron ferrugineum | 14 → 11 |
| `rhododendron-grande` | Rhododendron grande | 0 → 0 |
| `rhododendron-molle` | Rhododendron molle | 10 → 14 |
| `rhododendron-ponticum` | Rhododendron ponticum | 4 → 7 |
| `rhodomyrtus-tomentosa` | Rhodomyrtus tomentosa | 5 → 10 |
| `rhodymenia-palmata` | Rhodymenia palmata | 0 → 0 |
| `rhus-coriaria` | Rhus coriaria | 15 → 14 |
| `rhus-glabra` | Rhus glabra | 35 → 32 |
| `rhus-typhina` | Rhus typhina | 4 → 8 |
| `rhynchosia-acuminatifolia` | Rhynchosia acuminatifolia | 0 → 0 |
| `rhynchosia-densiflora` | Rhynchosia densiflora | 0 → 0 |
| `rhynchosia-hirsuta` | Rhynchosia hirsuta | 1 → 1 |
| `rhynchosia-minima` | Rhynchosia minima | 0 → 0 |
| `rhynchosia-phaseoloides` | Rhynchosia phaseoloides | 2 → 2 |
| `rhynchosia-pyramidalis` | Rhynchosia pyramidalis | 3 → 2 |
| `rhynchosia-volubilis` | Rhynchosia volubilis | 6 → 6 |
| `ribes-nigrum` | Ribes nigrum | 11 → 14 |
| `ribes-rubrum` | Ribes rubrum | 9 → 9 |
| `ribes-uva-crispa` | Ribes uva-crispa | 6 → 6 |
| `ricinus-communis` | Ricinus communis | 119 → 69 |
| `robinia-pseudoacacia` | Robinia pseudoacacia | 14 → 12 |
| `rorippa-islandica` | Rorippa islandica | 0 → 8 |
| `rosa-canina` | Rosa canina | 20 → 21 |
| `rosa-davurica` | Rosa davurica | 0 → 0 |
| `rosa-gallica` | Rosa gallica | 10 → 10 |
| `rosa-laevigata` | Rosa laevigata | 22 → 27 |
| `rosa-multiflora` | Rosa multiflora | 14 → 20 |
| `rosa-rubiginosa` | Rosa rubiginosa | 0 → 3 |
| `rosa-spp` | Rosa spp | 0 → 0 |
| `rosa-woodsii` | Rosa woodsii | 1 → 1 |
| `rotala-floribunda` | Rotala floribunda | 0 → 0 |
| `rubia-cordifolia` | Rubia cordifolia | 36 → 30 |
| `rubus-chamaemorus` | Rubus chamaemorus | 1 → 1 |
| `rubus-chingii` | Rubus chingii | 0 → 0 |
| `rubus-fruticosus` | Rubus fruticosus | 14 → 16 |
| `rubus-idaeus` | Rubus idaeus | 21 → 27 |
| `rubus-parviflorus` | Rubus parviflorus | 0 → 6 |
| `rubus-phoenicolasius` | Rubus phoenicolasius | 0 → 0 |
| `rubus-sp` | Rubus sp. | 0 → 0 |
| `rubus-spectabilis` | Rubus spectabilis | 0 → 5 |
| `ruellia-tuberosa` | Ruellia tuberosa | 14 → 23 |
| `rumex-acetosa` | Rumex acetosa | 18 → 17 |
| `rumex-acetosella` | Rumex acetosella | 13 → 12 |
| `rumex-crispus` | Rumex crispus | 32 → 28 |
| `rumex-hymenosepalus` | Rumex hymenosepalus | 11 → 10 |
| `ruscus-aculeatus` | Ruscus aculeatus | 24 → 25 |
| `ruta-graveolens` | Ruta graveolens | 54 → 35 |
| `rzedowskia-tolantonguensis` | Rzedowskia tolantonguensis | 0 → 0 |
| `saccharum-officinarum` | Saccharum officinarum | 0 → 0 |
| `salacia-cordata` | Salacia cordata | 0 → 0 |
| `salix-alba` | Salix alba | 17 → 18 |
| `salix-sp` | Salix sp. | 0 → 0 |
| `salvia-apiana` | Salvia apiana | 0 → 0 |
| `salvia-beckeri` | Salvia beckeri | 0 → 0 |
| `salvia-canariensis` | Salvia canariensis | 0 → 0 |
| `salvia-columbariae` | Salvia columbariae | 1 → 1 |
| `salvia-divinorum` | Salvia divinorum | 2 → 3 |
| `salvia-dorisiana` | Salvia dorisiana | 0 → 0 |
| `salvia-farinacea` | Salvia farinacea | 0 → 0 |
| `salvia-longistyla` | Salvia longistyla | 0 → 0 |
| `salvia-mellifera` | Salvia mellifera | 0 → 0 |
| `salvia-mexicana` | Salvia mexicana | 1 → 1 |
| `salvia-miltiorrhiza` | Salvia miltiorrhiza | 34 → 24 |
| `salvia-munzii` | Salvia munzii | 0 → 0 |
| `salvia-nicolsoniana` | Salvia nicolsoniana | 0 → 0 |
| `salvia-officinalis` | Salvia officinalis | 38 → 25 |
| `salvia-sclarea` | Salvia sclarea | 12 → 12 |
| `salvia-sp` | Salvia sp. | 0 → 0 |
| `salvia-splendens` | Salvia splendens | 0 → 0 |
| `salvia-tomentosa` | Salvia tomentosa | 0 → 1 |
| `salvia-willeana` | Salvia willeana | 0 → 0 |
| `sambucus-nigra` | Sambucus nigra | 34 → 29 |
| `sambucus-racemosa` | Sambucus racemosa | 24 → 22 |
| `sanguinaria-canadensis` | Sanguinaria canadensis | 30 → 30 |
| `sanguisorba-minor` | Sanguisorba minor | 4 → 6 |
| `sanguisorba-officinalis` | Sanguisorba officinalis | 28 → 33 |
| `santalum-acuminatum` | Santalum acuminatum | 0 → 0 |
| `santalum-album` | Santalum album | 32 → 29 |
| `santolina-chamaecyparissus` | Santolina chamaecyparissus | 13 → 13 |
| `sarracenia-alata` | Sarracenia alata | 0 → 0 |
| `sarracenia-flava` | Sarracenia flava | 5 → 5 |
| `sarracenia-leucophylla` | Sarracenia leucophylla | 0 → 0 |
| `sarracenia-minor` | Sarracenia minor | 0 → 0 |
| `sarracenia-oreophila` | Sarracenia oreophila | 0 → 0 |
| `sarracenia-psittacina` | Sarracenia psittacina | 0 → 0 |
| `sarracenia-purpurea` | Sarracenia purpurea | 7 → 7 |
| `sarracenia-rubra` | Sarracenia rubra | 0 → 0 |
| `sarracenia-sp` | Sarracenia sp. | 0 → 0 |
| `sassafras-albidum` | Sassafras albidum | 32 → 34 |
| `satureja-cilicica` | Satureja cilicica | 0 → 0 |
| `satureja-hortensis` | Satureja hortensis | 15 → 15 |
| `satureja-montana` | Satureja montana | 3 → 20 |
| `satureja-subspicata-subsp-liburnica` | Satureja subspicata subsp. liburnica | 0 → 0 |
| `satureja-thymbra` | Satureja thymbra | 1 → 1 |
| `sauvagesia-erecta` | Sauvagesia erecta | 1 → 1 |
| `schefflera-species` | Schefflera species | 0 → 0 |
| `schinus-molle` | Schinus molle | 42 → 29 |
| `schisandra-chinensis` | Schisandra chinensis | 3 → 14 |
| `schleichera-oleosa` | Schleichera oleosa | 0 → 23 |
| `schoenocaulon-officinale` | Schoenocaulon officinale | 12 → 9 |
| `schrebera-swietenioides` | Schrebera swietenioides | 0 → 7 |
| `scirpus-tuberosus` | Scirpus tuberosus | 5 → 5 |
| `scoparia-dulcis` | Scoparia dulcis | 59 → 52 |
| `scopolia-carniolica` | Scopolia carniolica | 10 → 9 |
| `scrophularia-buergeriana` | Scrophularia buergeriana | 2 → 2 |
| `scrophularia-scorodonia` | Scrophularia scorodonia | 0 → 0 |
| `scutellaria-baicalensis` | Scutellaria baicalensis | 40 → 38 |
| `scutellaria-discolor` | Scutellaria discolor | 0 → 3 |
| `scutellaria-lateriflora` | Scutellaria lateriflora | 16 → 17 |
| `scutellaria-parvula` | Scutellaria parvula | 0 → 0 |
| `scutellaria-sp` | Scutellaria sp | 0 → 0 |
| `secale-cereale` | Secale cereale | 4 → 5 |
| `selaginella-delicatula` | Selaginella delicatula | 0 → 0 |
| `senecio-alpinus` | Senecio alpinus | 0 → 0 |
| `senna-alata` | Senna alata | 0 → 69 |
| `senna-alexandrina` | Senna alexandrina | 0 → 4 |
| `senna-lindheimeriana` | Senna lindheimeriana | 0 → 0 |
| `senna-occidentalis` | Senna occidentalis | 0 → 84 |
| `serenoa-repens` | Serenoa repens | 5 → 19 |
| `sesamum-indicum` | Sesamum indicum | 68 → 46 |
| `shorea-oblongifolia` | Shorea oblongifolia | 0 → 0 |
| `sicana-odorifera` | Sicana odorifera | 1 → 1 |
| `sida-rhombifolia` | Sida rhombifolia | 11 → 28 |
| `sideritis-germanicolpitana` | Sideritis germanicolpitana | 0 → 0 |
| `sideritis-pauli` | Sideritis pauli | 0 → 0 |
| `sideritis-scardica` | Sideritis scardica | 0 → 0 |
| `sideritis-sp` | Sideritis sp | 0 → 0 |
| `silybum-marianum` | Silybum marianum | 23 → 23 |
| `simaba-obovata` | Simaba obovata | 0 → 0 |
| `simarouba-amara` | Simarouba amara | 0 → 1 |
| `simarouba-glauca` | Simarouba glauca | 23 → 30 |
| `simmondsia-chinensis` | Simmondsia chinensis | 11 → 19 |
| `sinapis-alba` | Sinapis alba | 24 → 24 |
| `sinomenium-acutum` | Sinomenium acutum | 8 → 8 |
| `skimmia-arborescens` | Skimmia arborescens | 0 → 0 |
| `skimmia-japonica` | Skimmia japonica | 6 → 5 |
| `smilax-china` | Smilax china | 45 → 38 |
| `smilax-officinalis` | Smilax officinalis | 1 → 1 |
| `smilax-spp` | Smilax spp | 0 → 0 |
| `solanum-aviculare` | Solanum aviculare | 0 → 4 |
| `solanum-carolinense` | Solanum carolinense | 17 → 18 |
| `solanum-dulcamara` | Solanum dulcamara | 37 → 23 |
| `solanum-laciniatum` | Solanum laciniatum | 0 → 0 |
| `solanum-mammosum` | Solanum mammosum | 22 → 24 |
| `solanum-melongena` | Solanum melongena | 42 → 26 |
| `solanum-nigrum` | Solanum nigrum | 86 → 43 |
| `solanum-sessiliflorum` | Solanum sessiliflorum | 0 → 1 |
| `solanum-torvum` | Solanum torvum | 18 → 23 |
| `solanum-tuberosum` | Solanum tuberosum | 13 → 13 |
| `solidago-gigantea` | Solidago gigantea | 0 → 0 |
| `solidago-virgaurea` | Solidago virgaurea | 11 → 27 |
| `sonchus-oleraceus` | Sonchus oleraceus | 37 → 25 |
| `sophora-flavescens` | Sophora flavescens | 21 → 30 |
| `sophora-pachycarpa` | Sophora pachycarpa | 0 → 0 |
| `sorbus-americana` | Sorbus americana | 6 → 7 |
| `sorocea-bonplandii` | Sorocea bonplandii | 0 → 0 |
| `spartium-junceum` | Spartium junceum | 11 → 9 |
| `sphenostylis-angustifolia` | Sphenostylis angustifolia | 0 → 0 |
| `sphenostylis-stenocarpa` | Sphenostylis stenocarpa | 0 → 0 |
| `spigelia-marilandica` | Spigelia marilandica | 10 → 10 |
| `spinacia-oleracea` | Spinacia oleracea | 18 → 18 |
| `spirulina-pratensis` | Spirulina pratensis | 0 → 0 |
| `spirulina-spp` | Spirulina spp. | 0 → 0 |
| `spondianthus-preussii` | Spondianthus preussii | 1 → 1 |
| `spondias-dulcis` | Spondias dulcis | 7 → 17 |
| `spondias-mombin` | Spondias mombin | 34 → 51 |
| `spondias-pinnata` | Spondias pinnata | 1 → 23 |
| `spondias-purpurea` | Spondias purpurea | 17 → 18 |
| `spondias-tuberosa` | Spondias tuberosa | 0 → 0 |
| `stachys-betonicifolia` | Stachys betonicifolia | 0 → 0 |
| `stachys-germanica` | Stachys germanica | 0 → 0 |
| `stachys-sp` | Stachys sp | 0 → 0 |
| `stachytarpheta-cayennensis` | Stachytarpheta cayennensis | 11 → 20 |
| `stachytarpheta-jamaicensis` | Stachytarpheta jamaicensis | 42 → 53 |
| `stauracanthus-boivinii` | Stauracanthus boivinii | 0 → 0 |
| `stauracanthus-genistoides` | Stauracanthus genistoides | 0 → 0 |
| `stellaria-media` | Stellaria media | 13 → 13 |
| `stemodia-maritima` | Stemodia maritima | 0 → 9 |
| `stemonoporus-affinis` | Stemonoporus affinis | 0 → 0 |
| `stemonoporus-canaliculatus` | Stemonoporus canaliculatus | 0 → 0 |
| `stemonoporus-cordifolius` | Stemonoporus cordifolius | 0 → 0 |
| `stemonoporus-oblongifolius` | Stemonoporus oblongifolius | 0 → 0 |
| `stemonoporus-petiolaris` | Stemonoporus petiolaris | 0 → 0 |
| `stemonoporus-reticulatus` | Stemonoporus reticulatus | 0 → 0 |
| `stephania-japonica` | Stephania japonica | 2 → 15 |
| `sterculia-urens` | Sterculia urens | 0 → 7 |
| `stevia-rebaudiana` | Stevia rebaudiana | 1 → 3 |
| `stillingia-sylvatica` | Stillingia sylvatica | 33 → 32 |
| `streblus-asper` | Streblus asper | 5 → 25 |
| `strobilanthes-cusia` | Strobilanthes cusia | 0 → 18 |
| `strongylodon-macrobotrys` | Strongylodon macrobotrys | 0 → 0 |
| `strophanthus-divaricatus` | Strophanthus divaricatus | 0 → 0 |
| `strophanthus-gratus` | Strophanthus gratus | 1 → 0 |
| `strophanthus-hispidus` | Strophanthus hispidus | 1 → 3 |
| `strophanthus-kombe` | Strophanthus kombe | 4 → 4 |
| `strychnos-nux-vomica` | Strychnos nux-vomica | 26 → 28 |
| `styrax-benzoin` | Styrax benzoin | 21 → 28 |
| `styrax-tonkinensis` | Styrax tonkinensis | 0 → 11 |
| `suaeda-maritima` | Suaeda maritima | 0 → 1 |
| `symphoricarpos-orbiculatus` | Symphoricarpos orbiculatus | 0 → 1 |
| `symphytum-officinale` | Symphytum officinale | 21 → 23 |
| `symplocarpus-foetidus` | Symplocarpus foetidus | 23 → 25 |
| `symplocos-racemosa` | Symplocos racemosa | 6 → 20 |
| `syncarpia-glomulifera` | Syncarpia glomulifera | 0 → 0 |
| `synedrella-nodiflora` | Synedrella nodiflora | 11 → 20 |
| `syringa-vulgaris` | Syringa vulgaris | 7 → 7 |
| `syzygium-aromaticum` | Syzygium aromaticum | 57 → 44 |
| `syzygium-jambos` | Syzygium jambos | 3 → 11 |
| `syzygium-malaccense` | Syzygium malaccense | 0 → 21 |
| `tabernanthe-iboga` | Tabernanthe iboga | 6 → 13 |
| `tagetes-erecta` | Tagetes erecta | 25 → 32 |
| `tagetes-filifolia` | Tagetes filifolia | 0 → 10 |
| `tagetes-minuta` | Tagetes minuta | 10 → 28 |
| `tagetes-patula` | Tagetes patula | 9 → 23 |
| `tagetes-sp` | Tagetes sp. | 0 → 0 |
| `tamarindus-indica` | Tamarindus indica | 28 → 59 |
| `tanacetum-vulgare` | Tanacetum vulgare | 34 → 34 |
| `taraxacum-mongolicum` | Taraxacum mongolicum | 15 → 22 |
| `taraxacum-officinale` | Taraxacum officinale | 56 → 43 |
| `taxus-baccata` | Taxus baccata | 15 → 16 |
| `taxus-cuspidata` | Taxus cuspidata | 3 → 2 |
| `taxus-sp` | Taxus sp | 2 → 0 |
| `tecoma-stans` | Tecoma stans | 28 → 32 |
| `tectona-grandis` | Tectona grandis | 0 → 18 |
| `teline-sp` | Teline sp | 0 → 0 |
| `telosma-cordata` | Telosma cordata | 0 → 0 |
| `tephrosia-candida` | Tephrosia candida | 0 → 4 |
| `tephrosia-purpurea` | Tephrosia purpurea | 16 → 31 |
| `tephrosia-virginiana` | Tephrosia virginiana | 18 → 18 |
| `tephrosia-vogelii` | Tephrosia vogelii | 3 → 14 |
| `terminalia-alata` | Terminalia alata | 0 → 5 |
| `terminalia-arjuna` | Terminalia arjuna | 3 → 21 |
| `terminalia-bellirica` | Terminalia bellirica | 1 → 25 |
| `terminalia-catappa` | Terminalia catappa | 24 → 38 |
| `terminalia-chebula` | Terminalia chebula | 44 → 37 |
| `terminalia-ivorensis` | Terminalia ivorensis | 3 → 3 |
| `terminalia-pallida` | Terminalia pallida | 0 → 0 |
| `ternstroemia-gymnanthera` | Ternstroemia gymnanthera | 0 → 2 |
| `ternstromia-merriliana` | Ternstromia merriliana | 0 → 0 |
| `tetracera-akara` | Tetracera akara | 0 → 0 |
| `tetracera-indica` | Tetracera indica | 0 → 7 |
| `tetracera-sarmentosa` | Tetracera sarmentosa | 2 → 2 |
| `tetracera-scandens` | Tetracera scandens | 0 → 12 |
| `tetraclinis-articulata` | Tetraclinis articulata | 9 → 11 |
| `teucrium-arduini` | Teucrium arduini | 0 → 0 |
| `teucrium-asiaticum` | Teucrium asiaticum | 0 → 0 |
| `teucrium-botrys` | Teucrium botrys | 1 → 1 |
| `teucrium-chamaedrys` | Teucrium chamaedrys | 20 → 20 |
| `teucrium-cyprium` | Teucrium cyprium | 0 → 0 |
| `teucrium-gnaphalodes` | Teucrium gnaphalodes | 0 → 0 |
| `teucrium-kotschyanum` | Teucrium kotschyanum | 0 → 0 |
| `teucrium-marum` | Teucrium marum | 11 → 11 |
| `teucrium-micropodioides` | Teucrium micropodioides | 0 → 0 |
| `teucrium-montanum` | Teucrium montanum | 0 → 0 |
| `teucrium-pseudoscorodonia` | Teucrium pseudoscorodonia | 0 → 0 |
| `teucrium-salviastrum` | Teucrium salviastrum | 0 → 0 |
| `teucrium-scordium` | Teucrium scordium | 15 → 15 |
| `teucrium-scorodonia` | Teucrium scorodonia | 14 → 16 |
| `teucrium-sp` | Teucrium sp | 1 → 0 |
| `theobroma-angustifolium` | Theobroma angustifolium | 0 → 0 |
| `theobroma-bicolor` | Theobroma bicolor | 1 → 1 |
| `theobroma-cacao` | Theobroma cacao | 14 → 26 |
| `theobroma-speciosum` | Theobroma speciosum | 0 → 3 |
| `thermopsis-fabacea` | Thermopsis fabacea | 3 → 3 |
| `thermopsis-montana` | Thermopsis montana | 0 → 0 |
| `thermopsis-sp` | Thermopsis sp | 0 → 0 |
| `thespesia-populnea` | Thespesia populnea | 13 → 30 |
| `thonningia-sanguinea` | Thonningia sanguinea | 9 → 9 |
| `thuja-occidentalis` | Thuja occidentalis | 34 → 37 |
| `thymelaea-hirsuta` | Thymelaea hirsuta | 1 → 1 |
| `thymus-cilicicus` | Thymus cilicicus | 0 → 0 |
| `thymus-funkii` | Thymus funkii | 0 → 0 |
| `thymus-longicaulis` | Thymus longicaulis | 0 → 0 |
| `thymus-mastichina` | Thymus mastichina | 2 → 2 |
| `thymus-orospedanus` | Thymus orospedanus | 0 → 0 |
| `thymus-piperella` | Thymus piperella | 0 → 0 |
| `thymus-riatarum` | Thymus riatarum | 0 → 0 |
| `thymus-saturejoides` | Thymus saturejoides | 0 → 0 |
| `thymus-serpyllum` | Thymus serpyllum | 18 → 19 |
| `thymus-vulgaris` | Thymus vulgaris | 36 → 30 |
| `thymus-x-citriodorus` | Thymus × citriodorus | 0 → 0 |
| `thymus-zygis` | Thymus zygis | 1 → 1 |
| `thymus-zygis-subsp-sylvestris` | Thymus zygis subsp. sylvestris | 0 → 0 |
| `tilia-sp` | Tilia sp. | 0 → 0 |
| `tovomita-mangle` | Tovomita mangle | 0 → 0 |
| `trachyspermum-ammi` | Trachyspermum ammi | 6 → 22 |
| `tragopogon-porrifolius` | Tragopogon porrifolius | 3 → 3 |
| `tribulus-terrestris` | Tribulus terrestris | 42 → 31 |
| `trichilia-hirta` | Trichilia hirta | 17 → 15 |
| `tricholepis-glaberrima` | Tricholepis glaberrima | 0 → 15 |
| `trichosanthes-kirilowii` | Trichosanthes kirilowii | 27 → 28 |
| `tridax-procumbens` | Tridax procumbens | 3 → 14 |
| `trifolium-alexandrinum` | Trifolium alexandrinum | 0 → 0 |
| `trifolium-hybridum` | Trifolium hybridum | 0 → 0 |
| `trifolium-pratense` | Trifolium pratense | 26 → 29 |
| `trifolium-repens` | Trifolium repens | 12 → 14 |
| `trifolium-sp` | Trifolium sp | 0 → 0 |
| `trifolium-subterraneum` | Trifolium subterraneum | 0 → 0 |
| `trigonella-foenum-graecum` | Trigonella foenum-graecum | 45 → 33 |
| `trilisa-odoratissima` | Trilisa odoratissima | 7 → 8 |
| `triticum-aestivum` | Triticum aestivum | 46 → 24 |
| `tropaeolum-majus` | Tropaeolum majus | 18 → 28 |
| `tropaeolum-tuberosum` | Tropaeolum tuberosum | 0 → 0 |
| `tsuga-canadensis` | Tsuga canadensis | 9 → 15 |
| `tulipa-gesneriana` | Tulipa gesneriana | 0 → 0 |
| `turnera-diffusa` | Turnera diffusa | 39 → 35 |
| `tussilago-farfara` | Tussilago farfara | 26 → 31 |
| `ulex-europaeus` | Ulex europaeus | 2 → 3 |
| `ulex-micranthus` | Ulex micranthus | 0 → 0 |
| `ulex-sp` | Ulex sp | 0 → 0 |
| `ullucus-tuberosus` | Ullucus tuberosus | 1 → 1 |
| `umbellularia-californica` | Umbellularia californica | 5 → 5 |
| `uncaria-catechu` | Uncaria catechu | 0 → 0 |
| `uncaria-guianensis` | Uncaria guianensis | 1 → 1 |
| `uncaria-tomentosa` | Uncaria tomentosa | 0 → 0 |
| `urtica-dioica` | Urtica dioica | 43 → 33 |
| `uvaria-sp` | Uvaria sp. | 0 → 0 |
| `vaccinium-corymbosum` | Vaccinium corymbosum | 0 → 0 |
| `vaccinium-macrocarpon` | Vaccinium macrocarpon | 1 → 2 |
| `vaccinium-myrtillus` | Vaccinium myrtillus | 15 → 15 |
| `valeriana-jatamansi` | Valeriana jatamansi | 9 → 26 |
| `valeriana-officinalis` | Valeriana officinalis | 37 → 31 |
| `vancouveria-hexandra` | Vancouveria hexandra | 0 → 0 |
| `vandasina-retusa` | Vandasina retusa | 0 → 0 |
| `vanilla-planifolia` | Vanilla planifolia | 14 → 19 |
| `vatica-affinis` | Vatica affinis | 0 → 0 |
| `vauquelinia-corymbosa` | Vauquelinia corymbosa | 0 → 0 |
| `vellozia-declinans` | Vellozia declinans | 0 → 0 |
| `veratrum-album` | Veratrum album | 22 → 21 |
| `veratrum-viride` | Veratrum viride | 27 → 26 |
| `verbascum-thapsus` | Verbascum thapsus | 42 → 39 |
| `verbena-hastata` | Verbena hastata | 9 → 10 |
| `verbena-officinalis` | Verbena officinalis | 60 → 31 |
| `veronica-officinalis` | Veronica officinalis | 27 → 23 |
| `viburnum-cassinoides` | Viburnum cassinoides | 1 → 1 |
| `viburnum-prunifolium` | Viburnum prunifolium | 11 → 15 |
| `vicia-faba` | Vicia faba | 13 → 12 |
| `vigna-aconitifolia` | Vigna aconitifolia | 0 → 0 |
| `vigna-angularis` | Vigna angularis | 0 → 18 |
| `vigna-mungo` | Vigna mungo | 19 → 25 |
| `vigna-radiata` | Vigna radiata | 21 → 20 |
| `vigna-subterranea` | Vigna subterranea | 0 → 0 |
| `vigna-umbellata` | Vigna umbellata | 0 → 1 |
| `vigna-unguiculata-subsp-sesquipedalis` | Vigna unguiculata subsp. sesquipedalis | 0 → 2 |
| `vinca-minor` | Vinca minor | 13 → 27 |
| `viola-odorata` | Viola odorata | 29 → 27 |
| `viola-tricolor` | Viola tricolor | 23 → 24 |
| `virola-calophylla` | Virola calophylla | 2 → 2 |
| `virola-surinamensis` | Virola surinamensis | 1 → 1 |
| `viscum-album` | Viscum album | 20 → 19 |
| `viscum-articulatum` | Viscum articulatum | 0 → 9 |
| `vismia-cayennensis` | Vismia cayennensis | 0 → 0 |
| `vismia-micrantha` | Vismia micrantha | 0 → 0 |
| `vitellaria-paradoxa` | Vitellaria paradoxa | 0 → 0 |
| `vitex-agnus-castus` | Vitex agnus-castus | 25 → 21 |
| `vitis-vinifera` | Vitis vinifera | 28 → 26 |
| `warburgia-ugandensis` | Warburgia ugandensis | 0 → 0 |
| `wisteria-floribunda` | Wisteria floribunda | 2 → 1 |
| `withania-somnifera` | Withania somnifera | 28 → 26 |
| `xanthorhiza-simplicissima` | Xanthorhiza simplicissima | 9 → 10 |
| `xanthosoma-sagittifolium` | Xanthosoma sagittifolium | 8 → 14 |
| `xylopia-aethiopica` | Xylopia aethiopica | 21 → 20 |
| `yucca-baccata` | Yucca baccata | 0 → 1 |
| `yucca-brevifolia` | Yucca brevifolia | 2 → 2 |
| `yucca-schidigera` | Yucca schidigera | 0 → 0 |
| `zanthoxylum-americanum` | Zanthoxylum americanum | 14 → 23 |
| `zanthoxylum-clava-herculis` | Zanthoxylum clava-herculis | 23 → 23 |
| `zataria-multiflora` | Zataria multiflora | 0 → 6 |
| `zea-mays` | Zea mays | 60 → 47 |
| `zingiber-officinale` | Zingiber officinale | 100 → 70 |
| `zizyphus-oenoplia` | Zizyphus oenoplia | 0 → 0 |
| `zizyphus-trinervia` | Zizyphus trinervia | 0 → 0 |
| `zizyphus-xylopyra` | Zizyphus xylopyra | 0 → 0 |
