# Lot #319 — Les maisons de l'IA et leurs capitales
Jalon : J5 · Machine : vps · Taille prévue : 280 lignes

## But
Le monde sait nommer chaque maison que joue l'IA — les 30 grandes maisons de la table des puissances et les seigneuries de départ que le joueur n'a pas prises — et dire dans quelle cellule est sa capitale, ou déclarer qu'elle est hors carte.

## Règle du monde
Découle de « Les maisons de 1400, vue dérivée » et « Les seigneuries de départ, vue dérivée » de `jeu/sim/MODELE.md`, et de « Les intentions du joueur » (`maison_du_joueur`). C'est une **vue pure** : rien ne change dans le tick.

**La donnée (niveau 1).** Un nouveau fichier `jeu/data/capitales-1400.json`, daté `1400-01-01`, déclare **une capitale par grande maison**, une ligne JSON par capitale : `maison` (id de la table des puissances), `nom`, `lat`, `lon` (EPSG:4326), `source` publique qui atteste que la ville est le siège de cette maison au 1er janvier 1400, et, seulement si le point tombe hors de tout polygone, `hors_carte` : la raison, en texte. La table des puissances ne change pas.

Les capitales à déclarer, mesurées sur la carte figée le 04/10/2026 (point projeté par `projeter_epsg3035`, puis polygone) :

| maison | capitale | cellule |
|---|---|---|
| 1 Lancastre | Londres | 10237 |
| 2 Stuart | Perth (Édimbourg ne devient capitale qu'au milieu du XVe siècle) | 10206 |
| 3 Valois | Paris | 10322 |
| 4 Aviz | Lisbonne | 10231 |
| 5 Trastamare | Tolède (cour itinérante, déclaré au niveau 2) | 10204 |
| 6 Barcelone | Barcelone | 10313 |
| 7 Évreux | Pampelune | 10192 |
| 8 Nasrides | Grenade | 10209 |
| 9 Luxembourg | Prague | 10284 |
| 10 Visconti | Milan | 10466 |
| 11 Anjou-Durazzo | Naples (Gaète est dans la même cellule) | 10283 |
| 12 Savoie | Chambéry | 10433 |
| 13 Poméranie | Roskilde (capitale danoise jusqu'en 1443 ; Copenhague est hors des polygones) | 9892 |
| 14 Jagellon | Cracovie | 10327 |
| 15 Paléologue | Constantinople | 10374 |
| 16 Osman | Edirne | 10366 |
| 17 Lazarević | Kruševac | 10329 |
| 18 Kotromanić | Bobovac | 10300 |
| 19 Basarab | Târgoviște | 10362 |
| 20 Mușat | Suceava | 10371 |
| 21 Djötchides | Saraï, sur la basse Volga | **hors carte, déclarée** |
| 22 Barquq | Le Caire (le point est dans le polygone 8992, sans ancre au Caire) | 8992 |
| 23 Hafsides | Tunis | 10143 |
| 24 Zayyanides | Tlemcen | 9788 |
| 25 Mérinides | Fès | 9831 |
| 26 Lusignan | Nicosie | 10059 |
| 27 Valois-Bourgogne | Dijon | 10420 |
| 28 Montfort | Nantes | 10191 |
| 29 Wittelsbach | Heidelberg (la branche palatine, tête de la maison dans sa source ; Munich reste une ancre, pas la capitale) | 10452 |
| 30 Habsbourg | Vienne | 10294 |

Mesure à retenir : les **29 capitales placées tombent chacune dans une cellule que `maisons_depuis_monde` donne à leur propre maison**. C'est l'invariant de cohérence que le lot prouve.

**Le placement.** La cellule d'une capitale se trouve comme celle d'un siège de seigneurie : `point_dans_geometrie` de `sim/villes.py`, polygones parcourus dans l'ordre des `cell_id`, le plus petit gagne sur une frontière ; le centroïde le plus proche ne sert jamais. Une capitale **hors carte se déclare, jamais ne se devine** : un point hors de tout polygone sans `hors_carte` est refusé ; un `hors_carte` déclaré pour un point qui tombe dans une cellule est refusé aussi. Une capitale hors carte n'a pas de cellule (`None`) et porte sa raison.

**Le chargement refuse**, en nommant la maison et le champ (`PuissanceInvalide`, comme les tables voisines) : une liste absente ou vide, une date autre que `1400-01-01`, une maison inconnue, booléenne ou non entière, une maison en double, une maison de la table sans capitale, un `nom` ou une `source` vides, une coordonnée non finie ou booléenne, un `hors_carte` présent mais vide.

**La vue.** `maisons_de_l_ia(monde, …)` dans un nouveau module `jeu/sim/capitales.py` rend un tuple gelé, recalculé à chaque appel :
- d'abord les 30 grandes maisons, par id : sorte `grande maison`, id, nom de la maison, nom de la capitale, `cell_id` (ou `None`), raison hors carte (ou `None`), source ;
- puis les seigneuries de départ **sauf celle de `monde.maison_du_joueur`**, par id : sorte `seigneurie`, id de la seigneurie, nom de sa maison (`Bar`, `Paléologue`…), nom de son siège, `cell_id` donné par `cellule_du_siege`, source de la seigneurie.

Sans choix, 35 maisons ; avec un choix, 34. La Morée est tenue par une branche Paléologue distincte de l'empereur : quand le joueur prend la Morée, la grande maison Paléologue (Constantinople) reste à l'IA ; elles sont deux maisons de l'IA quand il ne la prend pas. Les dataclasses héritent de `_NoBadSpatialField`, ne posent rien sur `Cell`, ne sont pas dans `sim.model` ; `engine.py`, `world.py` et `model.py` ne lisent pas `capitales`. **Le tick ne lit pas cette vue.**

**Niveaux.** Niveau 1 : la ville capitale de chaque maison et sa source, les sièges des seigneuries (déjà sourcés). Niveau 2 : une maison réduite à une seule capitale (cour itinérante de Castille, branches de Wittelsbach), la cellule qu'en donne le polygone. Niveau 3, pas simulé : ce que l'IA décide, ses gestes, le lien entre deux branches d'une même dynastie, les républiques, l'Église et les ordres (sans maison, ils ne sont pas dans cette vue), les capitales qui changent.

`jeu/sim/MODELE.md` reçoit une section « ## Les maisons de l'IA et leurs capitales, vue dérivée », placée après « Les seigneuries de départ, vue dérivée », qui dit tout ce qui précède (donnée, placement, refus, vue, comptes 30 / 29 placées / 1 hors carte / 35 ou 34, niveaux), et une ligne à « Référence de code ». Elle corrige aussi la phrase de « Les puissances de 1400 » sur Le Caire : son point est dans le polygone 8992, même si aucune ancre n'y est.

## Périmètre
jeu/data/capitales-1400.json
jeu/sim/capitales.py
jeu/sim/tests/test_maisons.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`. Les cas s'ajoutent à `sim/tests/test_maisons.py` (le fichier qui porte l'invariant des maisons ; pas de nouveau fichier de test, cf. `sim/tests/README.md`), dans des tests dont le nom contient `capitale`.

- **SC1 — la table se lit, une capitale par maison.** `python3 -m pytest sim/tests/test_maisons.py -q -k capitale` : la vraie table charge 30 capitales, dont l'ensemble des `maison` est exactement celui des ids de `charger_maisons()`. Contre-épreuve : chaque refus listé ci-dessus, écrit dans une copie de la table sous `tmp_path`, lève `PuissanceInvalide` dont le message nomme la maison et le champ ; une table où l'on retire la ligne de Lusignan est refusée en nommant la maison 26.
- **SC2 — chaque capitale dans sa cellule, par polygone.** Même commande : Londres → 10237, Constantinople → 10374, Le Caire → 8992, Roskilde → 9892 ; exactement **29** capitales placées et **1** hors carte, Saraï (Djötchides), avec sa raison ; pour chacune des 29, `maisons_depuis_monde(monde)[cell_id]` vaut sa propre maison. Contre-épreuves : (a) Saraï sans `hors_carte` est refusée (« hors carte » et « maison 21 » dans le message) ; (b) Paris déclarée `hors_carte` est refusée en nommant la cellule 10322 ; (c) une copie où la capitale de Lancastre prend les coordonnées de Paris fait compter une capitale incohérente (cellule tenue par Valois) et l'assertion de cohérence échoue ; (d) sur une carte synthétique de deux carrés qui se touchent, un point sur la frontière va au plus petit `cell_id`, et un point dans le grand carré mais plus proche du centroïde du petit va au grand.
- **SC3 — l'IA joue tout ce que le joueur n'a pas pris.** Même commande : sur `World.charger(0)` sans choix, `maisons_de_l_ia` rend 35 maisons, 30 grandes puis 5 seigneuries, ordonnées par id. Pour chacune des 5 seigneuries, un monde où `deposer_intention(monde, {"type": "choisir_depart", "seigneurie": id})` est appliqué par un tick rend 34 maisons, sans cette seigneurie et avec les 4 autres ; avec la Morée choisie, la grande maison Paléologue (Constantinople, 10374) est toujours là. Contre-épreuve : le même monde avec Bar choisi, passé à une vue qui ignore `maison_du_joueur` (paramètre ou copie du monde remis à `None`), rend 35 et l'assertion « Bar absent » échoue.
- **SC4 — une vue pure, que le tick ne lit pas.** Même commande : deux appels rendent la même valeur ; `monde.to_dict()`, `vars()` de chaque cellule et les tables chargées sont identiques avant et après ; `grep -c capitales` vaut 0 dans `sim/engine.py`, `sim/world.py`, `sim/model.py`, et plus de 0 dans `sim/capitales.py` (contre-épreuve du grep). Une position de cellule absente fait lever une erreur qui nomme la cellule, comme `maisons_depuis_monde`.
- **SC5 — MODELE.md change dans le même lot.** `grep -c "^## Les maisons de l'IA et leurs capitales, vue dérivée" sim/MODELE.md` rend 1 (contre-épreuve : 0 sur `master`), et `grep -c "capitales-1400.json" sim/MODELE.md` rend au moins 1.
- **SC6 — rien d'autre ne bouge.** `python3 -m pytest sim -q` puis `python3 -m pytest . -q` (depuis `jeu/`) passent en entier, sans modifier aucun test existant : `test_no_hardcoded.py` (aucun nombre magique dans `sim/capitales.py` : les comptes vivent dans les tests), `test_write_coverage.py`, `test_determinisme.py`, `test_puissances.py`, `test_seigneuries.py`. Contre-épreuve : `git diff --stat master -- jeu/data/puissances-1400.json jeu/data/seigneuries-1400.json jeu/sim/engine.py jeu/sim/world.py jeu/sim/model.py` est vide.

## Hors périmètre
- Les décisions et les gestes de l'IA, et le contrôle « l'IA n'a que le chemin des intentions » : lots suivants du jalon J5.
- La photographie, le service (`/monde`, `/lieu`), le journal, la carte, Unity : la vue n'est exposée nulle part dans ce lot.
- Les républiques, l'Église et les ordres (Venise, Papauté, Hospitaliers…) : sans maison, ils ne sont pas des maisons de l'IA ici.
- Les vassaux sans ancre, d'autres seigneuries que les cinq de départ, les personnes, la succession, une capitale qui change de ville.
- Toute modification de `data/puissances-1400.json`, `data/seigneuries-1400.json`, de leurs modules, du tick ou de `Cell`.
