# Lot #212 — La photographie porte le monde de 1400
Jalon : J2 · Machine : vps · Taille prévue : 270 lignes

## But
La photographie du monde (`monde.json`, `--snapshot-json`) porte, pour chaque cellule, sa puissance, sa maison tenante, sa densité et ses villes de 1400, et à la racine la terre choisie par le joueur avec sa fiche. Une vue ou Unity peut dessiner la carte de 1400 et la fiche du jalon 2 en ne lisant qu'elle. Ce qui manque y est écrit `null`, jamais omis ni deviné.

## Règle du monde
Aucune règle nouvelle : la photographie **lit** des vues qui existent déjà et ne décide aucun nombre (`CAP.md`, « Une vue ne décide jamais un nombre »). Elle découle de quatre sections de `jeu/sim/MODELE.md` : « Les puissances de 1400, vue dérivée », « Les maisons de 1400, vue dérivée », « Les seigneuries de départ, vue dérivée » et « Les intentions du joueur », ainsi que de l'attribution des villes de `sim/villes.py` que l'amorçage utilise déjà. **Base : master après #211** (`211d84e`). Si la branche part d'avant, le codeur la rebase d'abord sur `origin/master`.

**Décision du propriétaire (réponse A, issue #212).** Deux tests existants sont réécrits, et aucun ne devient moins exigeant :
- `sim/tests/test_monde.py` : `_ROOT_KEYS` et `_CELL_KEYS` restent des ensembles **fermés**, on y **ajoute** seulement les nouvelles clés ;
- `forge/tests/test_forge.py::test_depart_et_photographie_inchangee` (#211) devient `test_depart_et_photographie_ne_differe_que_par_la_terre`. Les deux photographies, avec et sans `--depart`, doivent être égales **en tout, sauf** `terre_choisie`.

Aucun autre test existant ne change.

**Par cellule**, quatre clés toujours présentes :
- `puissance` : `{"id", "nom"}` de la puissance que rend `puissances_depuis_monde(world)` ; `null` si la cellule est non couverte ;
- `maison` : `{"id", "nom"}` de la maison que rend `maisons_depuis_monde(world)` ; `null` si la cellule est non couverte, ou si elle est tenue par une république, une Église ou un ordre. `puissance` dit lequel des deux cas s'applique ;
- `densite_hab_par_km2` : `population / area_km2`, arrondie comme tout flottant de la photographie (`_round_tree`). Elle est calculée par une fonction unique, `densite_de_cellule(cell)`, de `sim/snapshot_export.py` ;
- `villes` : liste des `{"nom", "population"}` des villes de `charger_villes()` placées dans la cellule par `attribuer_villes`, triée par `nom` ; `[]` si la cellule n'a aucune ville documentée.

Les clés `owner` et `province_id` restent interdites dans une cellule : `test_rouge_sentinelle_et_cle_spatiale` le garde.

**À la racine**, deux clés toujours présentes :
- `villes_hors_carte` : noms triés des villes que `attribuer_villes` n'a placées dans aucune cellule. Aujourd'hui, c'est Venise ; le code ne l'écrit nulle part, il le dérive. Une ville absente de la carte se déclare.
- `terre_choisie` : `null` si `world.maison_du_joueur is None`. Sinon, la fiche que rend `fiche_de_seigneurie(world.maison_du_joueur, world)` au moment de la photographie :
  `{"id", "nom", "religion", "maison"` (nom de la maison de la seigneurie), `"siege": {"nom", "lat", "lon"}`, `"source"`, `"cell_id"`, `"habitants"`, `"production_kg_par_tick"`, `"suzerain": {"id", "nom"}`, `"maison_du_suzerain": {"id", "nom"} | null`, `"cellules_du_suzerain"`, `"habitants_du_suzerain"`, `"voisins": [{"cell_id", "puissance": {"id", "nom"} | null, "habitants"}]}`.
  Les voisins sont dans l'ordre de la fiche.

**Comment on la construit.** On reconstruit le document de carte en mémoire, `{**world.carte_meta, "cellules": [world.carte[c] for c in sorted(world.carte)]}`, pour `attribuer_villes`. Les tables (`charger_table`, `charger_maisons`) se chargent une seule fois par photographie et passent aux fonctions qui les acceptent.

Les nouvelles vues se calculent **après** l'appel existant à `agregat_depuis_monde`. Ainsi, une position inconnue reste refusée par le chemin d'aujourd'hui (`test_snapshot_refuse_cellule_sans_position_ou_sans_province`). Toute `PuissanceInvalide`, `SeigneurieInconnue` ou `ValueError` de ces vues devient une `SnapshotExportError` qui en reprend le message : la photographie refuse, elle ne complète rien.

Le monde n'est jamais modifié : `world.to_dict()` est identique avant et après la photographie. **Le tick ne lit rien de tout cela.**

**Version — correction après CI rouge.** `SNAPSHOT_SCHEMA_VERSION` reste
`"v0a-5"` dans `sim/constants.py`, avec les six nouvelles clés décrites ici.
Le tableau la compare à la constante, mais
`sim/tests/test_aridite.py::test_sonde_voit_la_couche_pluie` fige déjà
`"v0a-5"`. L'affirmation initiale « aucun test ne fige la valeur » était
fausse. La consigne de correction « Corrige la cause, jamais le test »
prime sur le passage initialement demandé à `"v0a-6"` : on conserve le
contrat existant, sans modifier ce test ni contourner sa comparaison.

**La chronique.** `vues/chronique/capture.py` découpe la photographie en décor (les champs fixes) et en images (les champs que le tick fait bouger). Elle **mesure** ces champs : `test_les_champs_mobiles_sont_mesures_et_pas_declares` rougit si un champ bouge sans être dans `CHAMPS_MOBILES`. La densité suit la population, donc elle bouge. Le codeur ajoute `"densite_hab_par_km2"` à `CHAMPS_MOBILES`. Dans `_image_du_monde`, il ajoute une branche qui l'obtient par `densite_de_cellule`, arrondie par `_round_tree`. Puissance, maison et villes ne bougent pas : elles vont dans le décor. La chronique rejoue un monde sans choix, donc sa `terre_choisie` reste `null` (voir Hors périmètre).

**Le modèle.** Dans « Les intentions du joueur », la phrase « la photographie `monde.json` reste identique avec ou sans choix » devient : « la photographie porte `terre_choisie`, `null` sans choix ; c'est sa seule différence ». Une section courte « ## La photographie de 1400, vue dérivée » vient juste après. Elle donne les six clés, leur source, les cas `null` et la phrase « le tick ne la lit pas ».

**Niveaux.** Rien de nouveau, tout est hérité :
- niveau 1 : puissances, maisons, villes et terres, avec leurs sources ;
- niveau 2 : étendue des puissances et des maisons, seigneurie réduite à la cellule de son siège, population amorcée ;
- niveau 3, pas simulé : frontières réelles, suzeraineté, villes hors carte (déclarées, pas placées).

### Ce que le codeur écrit
1. **`jeu/sim/snapshot_export.py`** : `densite_de_cellule`, les quatre clés de cellule, `villes_hors_carte`, `terre_choisie` (une fonction privée qui sérialise la `Fiche`), la conversion des refus. La docstring du module dit « schéma v0a-5 ». Aucun littéral numérique hors {0, 1, −1} (`test_no_hardcoded.py`).
2. **`jeu/sim/constants.py`** : `SNAPSHOT_SCHEMA_VERSION = "v0a-5"`.
3. **`jeu/vues/chronique/capture.py`** : `"densite_hab_par_km2"` dans `CHAMPS_MOBILES`, et sa branche dans `_image_du_monde`.
4. **`jeu/sim/MODELE.md`** : la phrase corrigée et la section décrite plus haut.
5. **`jeu/sim/README.md`** : la phrase sur `--snapshot-json` nomme puissance, maison, densité, villes et terre choisie.
6. **`jeu/sim/tests/test_monde.py`** : les clés ajoutées aux deux ensembles, et les nouveaux tests en ajout.
7. **`jeu/forge/tests/test_forge.py`** : le test de #211 réécrit comme décidé.

Les tests sont compacts : une fonction d'aide pour la photographie de graine 0, réutilisée.

## Périmètre
jeu/sim/snapshot_export.py
jeu/sim/constants.py
jeu/vues/chronique/capture.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_monde.py
jeu/forge/tests/test_forge.py
docs/briefs/212-la-photographie-porte-le-monde-de-1400.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`, sauf mention contraire. Aucun identifiant, nom de ville ou compte n'est écrit en dur dans un test : tout se dérive des vues (`puissances_depuis_monde`, `maisons_depuis_monde`, `attribuer_villes`, `charger_seigneuries`, `fiche_de_seigneurie`). Chaque test imprime ses compteurs, et un échantillon vide échoue. Chaque contre-épreuve est prouvée rouge avant d'être gardée.

**SC1 — le schéma s'élargit et reste fermé.** Commande : `python3 -m pytest sim/tests/test_monde.py -q -s -k "schema or sentinelle or photographie_1400"`.
- `test_schema_ferme_et_couches` est vert, avec `_ROOT_KEYS` élargi de `terre_choisie` et `villes_hors_carte`, et `_CELL_KEYS` élargi de `puissance`, `maison`, `densite_hab_par_km2` et `villes`. **Chaque** cellule (pas seulement la première) a exactement `_CELL_KEYS`. `doc["schema_version"] == "v0a-5"` passe par la constante.
- Contre-épreuve en mémoire, comme pour `bourg` : une cellule privée de `villes`, ou augmentée d'une clé `owner`, ne vérifie plus `set(cellule) == _CELL_KEYS`.

**SC2 — puissance et maison sont celles des vues, et l'absence s'écrit.** Commande : `python3 -m pytest sim/tests/test_monde.py -q -s -k photographie_1400_puissance`.
- Pour chaque cellule de `World.charger(0)`, `puissance["id"]` (ou `null`) est égal à `puissances_depuis_monde(monde)[cid]`, et `maison["id"]` (ou `null`) à `maisons_depuis_monde(monde)[cid]`. Les noms sont ceux des tables.
- Les comptes sont dérivés et imprimés : `couvertes`, `non_couvertes` (> 0), `avec_maison` et `sans_maison_par_nature` (> 0). Leur somme vaut `cell_count`.
- Toute cellule non couverte a `maison: null`.
- Contre-épreuve : un `monkeypatch` de `sim.snapshot_export.puissances_depuis_monde` qui rend `None` partout fait échouer la comparaison.

**SC3 — la densité suit la population.** Commande : `python3 -m pytest sim/tests/test_monde.py -q -s -k photographie_1400_densite`.
- Pour chaque cellule, à t0 puis après 3 ticks, `densite_hab_par_km2 == _round_tree(population / area_km2)`. On lit la population et la surface dans la même photographie.
- Au moins deux densités distinctes.
- Contre-épreuve : une cellule du monde à laquelle on ajoute un habitant change sa densité dans la photographie suivante.

**SC4 — chaque ville est placée une fois, ou se déclare hors carte.** Commande : `python3 -m pytest sim/tests/test_monde.py -q -s -k photographie_1400_villes`.
- L'ensemble des noms des listes `villes` de toutes les cellules, plus `villes_hors_carte`, est égal aux noms de `charger_villes()`, sans doublon.
- Chaque ville est dans la cellule `attribuer_villes(...).placees[nom]`, avec sa population.
- `villes_hors_carte == sorted(attribution.hors_carte)`.
- Contre-épreuve : retirer une ville de sa cellule dans une copie fait échouer l'égalité des ensembles.

**SC5 — la terre choisie et sa fiche.** Commande : `python3 -m pytest sim/tests/test_monde.py -q -s -k photographie_1400_terre`.
- Sans choix, `terre_choisie is None`.
- Après `deposer_intention` (Duché de Bar, trouvé par `nom`) et un `tick` : `terre_choisie["id"]` est l'`id` de Bar. `cell_id`, `habitants`, `suzerain`, `cellules_du_suzerain`, `habitants_du_suzerain` et les `cell_id` des voisins sont égaux à ceux de `fiche_de_seigneurie(bar, monde)`.
- Un monde jumeau sans choix, avec le même tick et la même graine, donne une photographie égale **une fois `terre_choisie` retirée des deux**. `monde.to_dict()` est identique avant et après la photographie.
- Contre-épreuves :
  - la Morée donne un autre `cell_id` ;
  - `monde.maison_du_joueur = max(id) + 1`, posé à la main, fait lever `SnapshotExportError`, dont le message contient « seigneurie inconnue ».

**SC6 — le test de #211, réécrit.** Commande : `python3 -m pytest forge/tests/test_forge.py -q -s -k depart`.
- `test_depart_et_photographie_ne_differe_que_par_la_terre` : `monde.json` avec `--depart <id de Bar>` a `terre_choisie["id"] == bar`, et sans `--depart`, `terre_choisie is None`. Les deux documents, privés de `terre_choisie`, sont égaux. Les assertions sur `resume.json` restent celles de #211.
- Contre-épreuve dans le même test : une copie du document « avec » dont une population de cellule change d'un habitant n'est plus égale au document « sans » privé de `terre_choisie`.
- Les autres tests `depart` du fichier restent verts sans modification.

**SC7 — la chronique découpe toujours la photographie au bit près.** Commande : `python3 -m pytest vues/chronique/tests/test_chronique.py -q`. Elle reste verte **sans modification du fichier de test** : la recomposition est exacte au tick 30, et les champs mobiles mesurés valent `CHAMPS_MOBILES`, qui contient `densite_hab_par_km2`.
- Contre-épreuve : avec `densite_hab_par_km2` ôtée de `CHAMPS_MOBILES`, `test_les_champs_mobiles_sont_mesures_et_pas_declares` rougit.

**SC8 — rien d'autre ne bouge.** Commande : `python3 -m pytest jeu -q`, depuis la racine. Elle reste verte, en particulier `test_no_hardcoded.py`, `test_seigneuries.py::test_pure`, `vues/tableau` et `ville/tests/test_epreuve_jalon1.py`.
- Depuis la racine, `git diff origin/master -- jeu/sim/tests jeu/vues jeu/forge/tests | grep -E '^-[^-]'` ne rend que des lignes de l'ancien `test_depart_et_photographie_inchangee` de `test_forge.py`. Tout le reste est ajout.
- `grep -c "^## La photographie de 1400" jeu/sim/MODELE.md` rend 1, et `grep -c "reste identique avec ou sans choix" jeu/sim/MODELE.md` rend 0.
- Contre-épreuve : sur la base, le premier `grep` rend 0 et le second rend 1.

## Hors périmètre
- L'écran du jalon 2 : la carte de 1400 dessinée par une vue ou par Unity, la fiche affichée, la capture du journal. Elles liront cette photographie dans un autre lot.
- La preuve du jalon 2, avec sa table de référence (Flandre, Île-de-France, delta du Nil plus denses que la médiane, désert plus vide ; Paris, Londres, Constantinople… à la bonne puissance).
- La raison d'une cellule non couverte (`lacune_par_cellule`), les ancres, la suzeraineté et les frontières tracées.
- `/monde`, `/lieu` et `/plan` du service, ainsi que `python3 -m sim`, qui n'a toujours pas de `--depart` : sa photographie a `terre_choisie: null`.
- La chronique rejouée par `forge` ne rejoue pas le choix : son décor garde `terre_choisie: null`. Rejouer les intentions viendra dans un autre lot.
- `puissances.py`, `maisons.py`, `villes.py`, `seigneuries.py`, `intentions.py`, `engine.py`, `world.py`, les tables de `data/`, l'amorçage, le tick, `vues/tableau`, `vues/relief`, `jeu/ville/`, `3d/`, `docs/COHERENCE.md`, et tout test existant hors des deux réécritures décidées.
