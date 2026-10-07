# Lot #402 — Le service sert la carte et les terres de départ
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Le service local sert, par deux routes, le fond de la carte du joueur (le contour simplifié de chaque cellule, son relief, sa puissance, sa maison de 1400 et ses villes) et les terres de départ avec leur fiche du tick courant, sans que Unity ait à recopier la carte.

## Le joueur
Lot de fond. Il prépare l'écran du jalon 3, « la carte du joueur, dans Unity », et ses deux premiers gestes : ouvrir sa carte (#403) et y choisir sa terre (#404). Après lui, le contour de chaque cellule et la fiche de chaque terre de départ (habitants, production, suzerain, voisins) arrivent dans Unity par le même chemin que le reste du monde, sans copie de la carte dans Unity : la fiche que le joueur lira avant de choisir sa terre est celle du monde au tick où il la lit, pas un chiffre figé. Le joueur ne voit rien de neuf dans ce lot ; #403 le rend visible.

## Règle du monde
Sans objet pour le monde : rien n'est simulé de neuf, aucun nombre du monde ne change. C'est une vue, qui lit ce que décrivent dans `jeu/sim/MODELE.md` « Les seigneuries de départ, vue dérivée » et « La photographie de 1400, vue dérivée ». Ce lot ajoute une section à `MODELE.md` (voir plus bas).

### Ce que le code fait

**Nouveau module `jeu/sim/carte_servie.py`.** Il n'utilise que la bibliothèque standard et `sim`. Ses constantes sont déclarées au niveau du module : `TOLERANCE_CONTOUR_M = 1000` et `SOMMETS_MIN_ANNEAU = 4` (le point de fermeture compte). Aucun littéral autre que 0, 1 et -1 n'apparaît dans une fonction (`test_no_hardcoded.py`).

- `simplifier_anneau(anneau, tolerance)` applique Douglas-Peucker à un anneau fermé, dans cet ordre :
  - retirer le point de fermeture ;
  - couper l'anneau au sommet le plus éloigné du premier (à égalité, le premier par indice) ;
  - simplifier chaque moitié à `tolerance` mètres, avec une pile itérative et la distance perpendiculaire à la corde ; on garde le sommet le plus éloigné s'il dépasse la tolérance (à égalité, le premier par indice) ;
  - recoller les deux moitiés, refermer, et arrondir chaque coordonnée au mètre (`round`).

  Le premier sommet d'origine reste le premier sommet servi. Les sommets servis sont une sous-suite des sommets d'origine.
- `point_temoin(cellule_carte)` rend le centroïde de la carte (`x_m`, `y_m`) s'il tombe dans le contour d'origine (`point_dans_geometrie` de `sim/villes.py`). Sinon, il prend l'horizontale du centroïde, la coupe par tous les anneaux du contour d'origine selon la règle pair-impair, et rend le milieu du plus large intervalle intérieur. S'il n'y a aucune intersection, il lève `ValueError` en nommant la cellule : le code refuse de deviner.
- `contour_servi(cellule_carte)` rend toujours un `MultiPolygon` : un `Polygon` est enveloppé. Chaque anneau passe par `simplifier_anneau(…, TOLERANCE_CONTOUR_M)`. Une garde vérifie le résultat, sur les coordonnées arrondies : si un anneau a moins de `SOMMETS_MIN_ANNEAU` points, ou si le point témoin n'est plus dans le contour, la cellule sert son contour d'origine arrondi au mètre. Si même ce contour-là perd le témoin, la fonction lève `ValueError` en nommant la cellule. Ainsi aucune cellule et aucun îlot ne se perd.
- `document_carte(world)` construit `{"crs": "EPSG:3035", "tolerance_m": TOLERANCE_CONTOUR_M, "version": <version de la carte>, "cell_count", "cells", "villes_hors_carte"}`. `cells` est trié par `cell_id`, et chaque cellule porte **exactement** `cell_id`, `contour`, `relief` (celui de la carte), `puissance`, `maison` et `villes`.
  - `puissance` et `maison` (`{id, nom}` ou `null`) viennent de `puissances_depuis_monde` et `maisons_depuis_monde`, comme dans la photographie.
  - `villes` reprend `{nom, population}` de la photographie, plus `x_m` et `y_m` de `charger_villes`. Elles sont placées par `attribuer_villes` et triées par nom ; `villes_hors_carte` les déclare comme la photographie.
  - Le document n'a ni `tick`, ni population de cellule, ni stock : seule la géométrie de 1400 y est figée.
  - `document_carte` rend aussi la vue des puissances qu'il a calculée, pour `/departs`.

**`jeu/sim/seigneuries.py`.** `fiche_de_seigneurie` gagne un paramètre nommé `vue=None`. Sans lui, la fonction recalcule `puissances_depuis_monde` comme aujourd'hui, et les tests existants restent inchangés. Avec lui, elle prend cette vue. On a mesuré 0,75 s par fiche sans vue, contre 36 ms pour les cinq fiches avec une vue figée. La vue ne dérive que des contours et des ancres de 1400 : aucun nombre du monde n'y est mis en cache.

**`jeu/sim/service.py`.**

- Ce qui est figé (les octets de `/carte`, la vue des puissances, et les tables des seigneuries, puissances et maisons) se calcule **une fois pour toute la partie**, à la première requête `GET /carte` ou `GET /departs`. Le calcul passe par un verrou propre, avec double vérification. Il ne se fait pas au démarrage, pour que chaque lancement de service des tests ne paie pas 1,6 s de plus.
- `GET /carte` rend ces octets (`_serialiser`).
- `GET /departs` prend `verrou_tick`, comme `/intention`, et calcule `{"tick", "date", "departs"}` :
  - `departs` contient, triées par `id`, les `_round_tree(_fiche_document(fiche_de_seigneurie(id, world, seigneuries, table, maisons, vue=vue)))` ;
  - c'est exactement la forme de `terre_choisie` dans la photographie (on a mesuré l'égalité) ;
  - `tick` et `date` sont ceux du monde, verrou tenu.
- Une erreur (`ValueError`, `SnapshotExportError`, `PuissanceInvalide`, `SeigneurieInconnue`) renvoie 500 avec `{"erreur": …}`, sans arrêter le service.
- `/departs` n'est pas calculé à chaque tick : à 36 ms par tick, il pèserait sur la cadence de l'horloge.

**`jeu/sim/MODELE.md`.** Ajouter une section « ## La carte et les terres servies, vue dérivée », juste après « La photographie de 1400, vue dérivée ». Elle dit :
- les deux routes et leurs champs ;
- `TOLERANCE_CONTOUR_M` et la garde ;
- le point témoin et pourquoi il existe ;
- que `/carte` est figée et que `/departs` est recalculé à chaque requête ;
- les niveaux de fidélité. **Niveau 1** : le trait des contours de la carte figée, les puissances, les maisons et les villes avec leurs sources. **Niveau 2** : la simplification à 1 km, une approximation de dessin, et l'étendue des puissances. **Niveau 3** : les frontières réelles, comme dans la photographie.

### Mesures du chef, le 07/10, carte `world-1400-v1`
- 596 cellules (544 `Polygon`, 52 `MultiPolygon`) et 51 314 sommets. À 1 km, il reste 19 789 sommets servis (environ 330 ko de JSON), en 0,1 à 0,2 s.
- **12 cellules ont un centroïde de carte hors de leur propre contour d'origine** : ce sont des contours concaves, dont 1211, 1232, 1242, 1316, 1324, 1404, 1429, 1444, 1479 et 1506. Pour ces cellules, la phrase de l'issue « le centroïde tombe dans son contour simplifié » ne peut pas tenir, même sans simplification. L'épreuve exige donc le centroïde partout où il est dans le contour d'origine (584 cellules), et le point témoin pour les 12 autres. La liste est **dérivée** des données, jamais écrite en dur. Cela ne rend pas la preuve moins exigeante, puisque le contrôle littéral est géométriquement impossible pour ces 12 cellules. Le contrôle reste le même : la simplification n'a perdu aucune cellule.
- 18 cellules tombent dans la garde et servent leur contour d'origine : un anneau s'effondre sous 4 points, comme 1412 et 1492 (environ 1,5 km² chacune), ou des îlots de `MultiPolygon` (9880, 9903, …). Sans la garde, au moins une cellule perd son témoin.
- Une fiche coûte 0,75 s sans vue figée, presque entièrement dans `puissances_depuis_monde`. `maisons_depuis_monde` coûte 0,73 s. La photographie complète coûte 15 s : l'épreuve n'en construit qu'une.
- Les habitants de chacune des cinq terres changent à chaque tick de 1 à 5 (seed 0). La contre-épreuve « pas de cache » a donc toujours un témoin.

## Périmètre
jeu/sim/carte_servie.py
jeu/sim/service.py
jeu/sim/seigneuries.py
jeu/sim/MODELE.md
jeu/sim/tests/test_carte_servie.py

## Conditions de succès
Tous les tests sont dans le nouveau fichier `jeu/sim/tests/test_carte_servie.py`. Il réutilise `lancer_service` et `requete_service` de `test_monde.py`, comme `test_determinisme.py`. Une seule photographie est construite, dans une fixture de module : seed 0, 3 ticks, `maison_du_joueur` = Duché de Bar, sur une copie du monde rejoué.

- **SC1 — chaque cellule est servie une fois, et `/carte` est figée.** `python3 -m pytest jeu/sim/tests/test_carte_servie.py -q -k carte_une_fois`.
  - Le test lance le service et appelle `GET /carte`. La liste des `cell_id` servis doit égaler la liste triée des `cell_id` de `World.lire_carte()`, sans doublon, avec `cell_count == len(cells) > 0`.
  - Chaque cellule porte exactement les six clés. `relief` égale celui de la carte. `puissance`, `maison` et `villes` (réduites à `{nom, population}`) égalent celles de la cellule dans la photographie, et `villes_hors_carte` égale celle de la photographie.
  - Après `POST /tick?n=1`, les octets de `/carte` sont identiques, et `tick` n'y figure pas.
  - Contre-épreuve : la fonction de contrôle reçoit le document privé d'une cellule, puis le document avec une cellule en double. Elle lève `AssertionError` dans les deux cas.
- **SC2 — le contour simplifié garde sa cellule, à un kilomètre près.** `python3 -m pytest jeu/sim/tests/test_carte_servie.py -q -k contour`.
  - Pour chaque cellule servie, le contour est un `MultiPolygon` dont chaque anneau est fermé et a au moins `SOMMETS_MIN_ANNEAU` points.
  - Chaque anneau servi est une sous-suite des sommets d'origine arrondis au mètre. Chaque sommet d'origine retiré est à au plus `TOLERANCE_CONTOUR_M + 1` m de la corde qui le remplace.
  - Le total des sommets servis est inférieur au total d'origine.
  - Le point témoin est dans le contour servi pour **toutes** les cellules. Le test vérifie et affiche que le témoin égale le centroïde de la carte pour exactement les cellules dont le centroïde est dans le contour d'origine. Ce nombre est dérivé et doit être strictement positif.
  - Contre-épreuves : (a) le contour d'une cellule remplacé par celui d'une voisine (`land-land`) perd le témoin ; (b) `simplifier_anneau` appliqué à 1 000 m **sans la garde** fait perdre son témoin, ou effondrer un anneau, à au moins une cellule ; (c) un contour simplifié à `5 × TOLERANCE_CONTOUR_M` échoue au contrôle de distance d'au moins une cellule.
- **SC3 — `/departs` égale les fiches de la photographie au même tick, sans cache.** `python3 -m pytest jeu/sim/tests/test_carte_servie.py -q -k departs`.
  - Le test lance le service (seed 0), envoie `POST /tick?n=3`, puis `GET /departs`. Il attend `tick == 3`, et des `id` égaux à la liste triée de `charger_seigneuries()` (non vide).
  - Chaque fiche égale `_round_tree(_fiche_document(fiche_de_seigneurie(id, monde)))` sur un monde rejoué en processus : `World.charger(0)`, puis 3 ticks avec `random.Random(0)`, **sans** `vue`.
  - La fiche du Duché de Bar égale `terre_choisie` de la photographie de la fixture.
  - Contre-épreuve : après `POST /tick?n=1`, `/departs` ne correspond plus aux fiches du tick 3 pour au moins une terre. Aucun nombre du monde n'est donc gardé en cache.
- **SC4 — rien d'existant ne casse.** `python3 -m pytest jeu -q` reste vert : aucun test existant n'est modifié, ni `test_service_depend_uniquement_de_la_bibliotheque_standard_et_de_sim`, ni `test_no_hardcoded.py`, ni `test_write_coverage.py`. Contre-épreuve : un littéral `1000` écrit dans une fonction de `carte_servie.py` fait rougir `test_no_hardcoded.py`, ce qui est vérifié à la main avant de nommer la constante.

## Hors périmètre
- Lire `/carte` ou `/departs` dans Unity, et dessiner la carte : #403 (pc). Choisir sa terre sur la carte : #404.
- Les seigneurs et lieux sur la carte, les flux, et la place d'un lieu dans sa cellule : #393, #400 et #401.
- Des frontières qui bougent (conquête, jalon 7). Si la puissance d'une cellule devient un jour un nombre du monde, ce figé devra être revu ; ce lot ne l'anticipe pas.
- La sixième terre de départ (le Zab) : `/departs` sert ce que porte `seigneuries-1400.json`, sans rien y ajouter.
- Une simplification qui garde la topologie (frontières communes identiques entre voisines) : les contours voisins de la carte ne partagent presque aucun sommet (1 063 sur 51 314). Chaque anneau se simplifie seul, et des jours de moins d'un kilomètre peuvent apparaître entre deux cellules.
- Toute modification de `data/world-1400.json`, de la photographie, du tick, de `/monde`, `/lieu` ou `/plan`, et la compression HTTP.
