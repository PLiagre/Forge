# Lot #210 — Les seigneuries de départ et leur fiche
Jalon : J2 · Machine : vps · Taille prévue : 290 lignes

## But
Le monde connaît cinq petites seigneuries réelles du 1er janvier 1400 (deux catholiques, deux orthodoxes, une musulmane), et sait dire pour chacune, dans une fiche calculée, ce qui décide le choix de la terre de départ du jalon J2 : ses habitants, ce qu'elle produit, son suzerain et son poids, ses voisins ; une seigneurie inconnue est refusée.

## Règle du monde
Elle prolonge, dans `jeu/sim/MODELE.md`, « Les puissances de 1400, vue dérivée », « Les maisons de 1400, vue dérivée » (#207, #208) et les populations amorcées par « Population initiale par cellule » avec les villes (#209). **Base : master après #208** (`71679c5`) ; si la branche part d'avant, le codeur la rebase d'abord sur `origin/master`.

**Rien ne change dans le monde.** La table des puissances, ses maisons, l'amorçage, la carte et le tick restent identiques. La fiche est une **vue pure**, recalculée, hors de `sim.model` : elle ne pose rien sur `Cell`, n'ajoute aucune clé spatiale (le siège donne un `cell_id`, rien d'autre), et le tick ne la lit pas.

**Une seigneurie** a un `id`, un `nom`, une `religion` (une de `RELIGIONS` de `sim/puissances.py`), une `maison` (son nom, en texte), un `suzerain` (l'`id` d'une puissance de `puissances-1400.json`), un `siege` (nom, `lat`, `lon` en EPSG:4326 et `x_m`, `y_m` en EPSG:3035, la projection de la carte) et une `source` publique qui atteste le seigneur, sa maison et son suzerain au 1er janvier 1400. Le suzerain est la **puissance** : son poids se mesure sur ses cellules, et la fiche nomme aussi la maison qui la tient (#208). Le lien lui-même — hommage, part prélevée — reste au jalon 3.

**Le siège donne la cellule** par appartenance au polygone, comme les villes : `point_dans_geometrie` de `sim/villes.py` sur les cellules de la carte triées par `cell_id` (sur une frontière, le plus petit gagne). Jamais par le centroïde le plus proche. Un siège hors de toute cellule est **refusé**, en nommant la seigneurie : une terre de départ hors carte ne se joue pas.

**La fiche**, pour un monde chargé :
- `cell_id` du siège et `habitants` = `population` de cette cellule ;
- `production_kg_par_tick` = `population_soutenable_de(cellule, monde.carte) × constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK` : la nourriture que l'unique formule du moteur produit par tick au rendement moyen et sur la saison moyenne (aucune formule recopiée, `engine.py` ne change pas) ;
- le `suzerain` (la `Puissance`), sa `maison` (la `Maison` de `par_puissance`, ou `None` pour une république, une Église, un ordre), son poids : `cellules_du_suzerain` (cellules que `puissances_depuis_monde` lui donne) et `habitants_du_suzerain` (somme de leurs `population`) ;
- les `voisins` : les cellules reliées au siège par une arête `kind == "land-land"` de `monde.adjacency`, sans doublon, triées par `cell_id`, chacune avec sa puissance (ou `None`) et ses habitants.

Un `id` inconnu (absent, booléen, non entier) lève `SeigneurieInconnue` (sous-classe de `LookupError`) en le nommant, avant tout calcul.

**Niveaux.** Niveau 1 (sources publiques) : le seigneur, sa maison, son suzerain au 1er janvier 1400, le point du siège. Niveau 2 (plausible ; une anomalie n'est pas un défaut) : la seigneurie réduite à la cellule de son siège (le détail sous la cellule attend le jalon 3) ; ses habitants et sa production sont ceux de la cellule entière amorcée ; l'étendue du suzerain suit ses ancres. Niveau 3, pas simulé : la suzeraineté qui prélève, les personnes, les autres seigneuries.

### Ce que le codeur écrit

**1. `jeu/data/seigneuries-1400.json`** (nouveau). Racine : `date` `"1400-01-01"`, `projection` `"EPSG:3035"`, `reference` `"EPSG:4326"`, `conversion` (Lambert azimutale équivalente ellipsoïdale GRS80, φ0 = 52° N, λ0 = 10° E, x0 = 4 321 000 m, y0 = 3 210 000 m, arrondie au centimètre ; elle retrouve les centroïdes de la carte à 6 cm près), `fidelite`, `seigneuries`. Le `siege` tient sur une ligne. Les cinq lignes, vérifiées par le chef sur la carte figée :

| id | nom | religion | maison | suzerain | siège | lat ; lon | x_m ; y_m | cellule (mesurée) |
|---|---|---|---|---|---|---|---|---|
| 1 | `Duché de Bar` | catholique | `Bar` (Robert Ier, duc 1352–1411 ; Barrois mouvant) | France | Bar-le-Duc | 48,772 ; 5,160 | 3965409.11 ; 2862646.57 | 10430 |
| 2 | `Comté de Wurtemberg` | catholique | `Wurtemberg` (Eberhard III, comte 1392–1417) | Saint-Empire | Stuttgart | 48,776 ; 9,183 | 4260932.34 ; 2851742.83 | 10465 |
| 3 | `Despotat de Morée` | orthodoxe | `Paléologue` (Théodore Ier, despote 1383–1407) | Byzance | Mistra | 37,074 ; 22,367 | 5424441.58 ; 1644956.82 | 10340 |
| 4 | `Terre des Branković` | orthodoxe | `Branković` (Đurađ, vassal ottoman après 1396) | Ottomans | Vučitrn | 42,823 ; 20,969 | 5217097.38 ; 2256208.68 | 10334 |
| 5 | `Uç d'Evrenos` | musulmane | `Evrenosoğulları` (Gazi Evrenos Bey, à Yenice-i Vardar) | Ottomans | Giannitsa | 40,792 ; 22,408 | 5367717.15 ; 2051967.94 | 10337 |

Le `suzerain` s'écrit par l'`id` de la puissance (France 3, Saint-Empire 9, Byzance 25, Ottomans 26 sur la base). Chaque `source` est un article public (encyclopédie, atlas) que le codeur vérifie ; une graphie autre peut être prise, il le dit dans la PR. Une **attribution** (seigneur, maison, suzerain au 1er janvier 1400) qu'il ne peut pas sourcer, il ne la remplace pas : il s'arrête et le dit dans la PR. La vente projetée de la Morée aux Hospitaliers (1400–1404) est postérieure au 1er janvier : la ligne tient si la source le confirme.

**2. `jeu/sim/seigneuries.py`** (nouveau ; aucun littéral numérique hors {0, 1, −1} dans un corps de fonction : `test_no_hardcoded` l'inspecte). Il peut importer de `sim.puissances` `_refuser_id`, `_texte`, `_nombre`, `PuissanceInvalide`, `RELIGIONS`, `charger_table`, `puissances_depuis_monde`, de `sim.maisons` `charger_maisons`, et de `sim.villes` `point_dans_geometrie`. Il ne modifie aucun de ces modules.
- `Seigneurie`, `Voisin`, `Fiche` : dataclasses gelées sur `_NoBadSpatialField`.
- `charger_seigneuries(path=None, table=None) -> tuple` (triées par `id`) lève `PuissanceInvalide` en nommant « seigneurie <id>, champ <champ> » : liste vide ou absente, `date` ou `projection` autres, `id` dupliqué ou booléen, `nom` dupliqué, texte vide (`nom`, `maison`, `source`, nom du siège), `religion` hors `RELIGIONS`, `suzerain` qui n'est pas une puissance de `table`, coordonnée non finie.
- `cellule_du_siege(seigneurie, carte) -> int` (carte : `monde.carte`) ; hors carte : `PuissanceInvalide` « seigneurie <id>, champ siege : hors carte ».
- `fiche_de_seigneurie(identifiant, monde, seigneuries=None, table=None, maisons=None) -> Fiche`, et `SeigneurieInconnue`.

**3. `jeu/sim/tests/test_seigneuries.py`** (nouveau). Il peut importer `_cellule_la_plus_proche` de `sim.tests.test_puissances`. Aucun test existant n'est touché.

**4. `jeu/sim/MODELE.md`** : une section « ## Les seigneuries de départ, vue dérivée », juste après celle des maisons : la règle ci-dessus, les cinq seigneuries, la fiche et ses formules, les trois niveaux, et que le tick ne la lit pas. Ne pas réécrire la section des maisons.

## Périmètre
jeu/data/seigneuries-1400.json
jeu/sim/seigneuries.py
jeu/sim/tests/test_seigneuries.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par `python3 -m pytest jeu/sim/tests/test_seigneuries.py -q -s -k <nom>`, sur `World.charger(0)`. Chaque test imprime ses compteurs ; un échantillon vide échoue. Aucun `cell_id` ni `id` écrit dans un test : seigneuries et puissances se trouvent par leur `nom`. Les nombres mesurés ci-dessous sont des repères pour le compte rendu, jamais des attendus codés en dur (sauf les cinq lignes et les quatre suzerains du tableau). Prouver chaque contre-épreuve rouge avant de la garder ; les altérations restent en mémoire ou dans `tmp_path`.

**SC1 — la table se lit** (`-k lecture`). `seigneuries_lues == 5`, noms uniques, et l'ensemble des religions lues est exactement `RELIGIONS` (une fonction `religions_manquantes` le dit). Contre-épreuve (`tmp_path`) : l'Uç d'Evrenos réécrit `catholique` donne `religions_manquantes == {"musulmane"}` et le test rougit.

**SC2 — les refus tiennent** (`-k refus`). Un test paramétré, une altération à la fois dans `tmp_path` : `seigneuries` vide ; `id` dupliqué ; `id` booléen ; `religion` `"arienne"` ; `suzerain` inconnu (max + 1) ; `source` vide ; `maison` absente ; `lat` non fini ; `date` `"1453-05-29"`. Chacune lève `PuissanceInvalide` en nommant la seigneurie et le champ (`refus_observés == len(cas) > 0`). Plus un siège déplacé en `x_m = y_m = 0` : `cellule_du_siege` le refuse « hors carte ». Contre-épreuve : la vraie table se charge.

**SC3 — chaque siège dans la terre de son suzerain** (`-k sieges`). Les cinq cellules de siège sont distinctes ; chacune est aussi celle que `_cellule_la_plus_proche` donne pour `lat`, `lon` (ce qui garde `x_m`, `y_m` d'accord avec le point) ; sa puissance dans `puissances_depuis_monde` est le suzerain déclaré (`hors_suzerain == 0`). Contre-épreuves en mémoire (`dataclasses.replace`) : Bar donné au Saint-Empire fait `hors_suzerain == 1` ; Bar avec les `x_m`, `y_m` de Stuttgart fait rougir l'accord avec le point et la distinction.

**SC4 — la fiche dit ce qui décide** (`-k fiche`). Pour chaque seigneurie, la fiche est égale à un recalcul indépendant dans le test : `habitants`, `production_kg_par_tick > 0` et égale à la formule, `cellules_du_suzerain` et `habitants_du_suzerain` depuis la vue des puissances, voisins = arêtes `land-land`, maison du suzerain : France → `Valois`, Saint-Empire → `Luxembourg`, Byzance → `Paléologue`, Ottomans → `Osman`. Le test imprime les cinq fiches et exige : la Terre des Branković et l'Uç d'Evrenos sont voisines ; les Ottomans pèsent plus de cellules que Byzance (mesuré 49 contre 23) ; la Morée a moins de voisins que Bar (mesuré 2 et 6). Contre-épreuves en mémoire : la population de la cellule de Bar augmentée de 1 000 se retrouve dans `habitants` ; celle d'une cellule de la France hors du siège augmentée de 1 000 se retrouve dans `habitants_du_suzerain` de Bar, et pas dans celui du Wurtemberg.

**SC5 — une seigneurie inconnue est refusée** (`-k inconnue`). `fiche_de_seigneurie` lève `SeigneurieInconnue` nommant l'identifiant pour max + 1, `True` et `"Bar"` ; `monde.to_dict()` est inchangé après chaque refus. Contre-épreuve : l'`id` du Duché de Bar rend sa fiche.

**SC6 — une vue pure, que le tick ne lit pas** (`-k pure`). Deux appels rendent la même fiche ; `monde.to_dict()` est inchangé ; `grep -c "seigneur" jeu/sim/engine.py jeu/sim/world.py jeu/sim/model.py` rend 0 pour chacun. Contre-épreuve : la même commande sur `jeu/sim/seigneuries.py` rend plus de 0.

**SC7 — rien d'autre ne bouge.** `git diff --name-only origin/master -- jeu/sim jeu/data` rend exactement `jeu/data/seigneuries-1400.json`, `jeu/sim/MODELE.md`, `jeu/sim/seigneuries.py`, `jeu/sim/tests/test_seigneuries.py`. `python3 -m pytest jeu -q` est vert, `test_no_hardcoded.py` compris. Contre-épreuve : un littéral `5` glissé dans une fonction de `seigneuries.py` fait rougir `test_no_hardcoded.py`.

**SC8 — le modèle le dit.** `awk '/^## Les seigneuries de départ, vue dérivée/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep -c -e Morée -e Evrenos -e Branković` rend au moins 3. Contre-épreuve : sur la base, avant le lot, elle rend 0.

## Hors périmètre
- Toute puissance, ancre, maison ou lacune ajoutée, retirée ou déplacée ; `puissances-1400.json`, `puissances.py`, `maisons.py`, `villes.py` et leurs tests ne changent pas.
- L'amorçage, `World.charger`, le tick, la carte figée, les villes : aucune population n'est posée pour une seigneurie.
- Le choix du joueur lui-même (intention, partie), la carte de 1400 à l'écran, le service, Unity et toute vue d'affichage.
- Les lieux sous la cellule, le prélèvement et l'hommage (jalon 3) ; les personnes (jalon 6) ; d'autres seigneuries que les cinq.
