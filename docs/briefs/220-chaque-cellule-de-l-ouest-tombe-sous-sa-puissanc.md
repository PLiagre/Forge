# Lot #220 — Chaque cellule de l'Ouest tombe sous sa puissance, ou se déclare non couverte
Jalon : J2 · Machine : vps · Taille prévue : 220 lignes

## But
Le monde sait dire, pour chaque cellule, de quelle puissance de 1400 elle relève
(la cellule de Paris : le royaume de France ; celle de Londres : le royaume
d'Angleterre) ou qu'aucune puissance de la table ne la couvre (Le Caire,
Constantinople). C'est le pas qui fait passer la table du lot #219 de points à
des frontières, celles qu'il faudra pour « des points connus appartiennent à la
bonne puissance » (CAP.md, jalon 2) et pour la carte des royaumes de 1400.

## Règle du monde
Une cellule relève de la puissance qui tient **l'ancre la plus proche** de son
centroïde. C'est la règle unique de `sim/aggregation.py`
(`derive_appartenance`, départage des égalités par le plus petit identifiant
d'ancre), appliquée aux ancres de `data/puissances-1400.json` comme elle
s'applique aux centres de province. Au-delà d'une **portée** unique, une
cellule n'est à personne dans la table : elle ressort **non couverte**
(`None`), elle est comptée, et rien ne la rattache à une puissance par défaut.
Sans portée, le désert d'Égypte relèverait de Vienne : la portée est ce qui
empêche la vue de deviner.

Cela découle de `jeu/sim/MODELE.md`, section « La province dérivée et ses
centres » (« Règle de départage des égalités », « Refus de deviner », « Ce que
l'agrégation ne fait pas — et le motif que toute vue recopie »), et suit le
motif de « La pluie de 1400, vue dérivée » : vue pure, hors de `sim.model`,
rien posé sur `Cell`, `cell_id` seule clé, recalculée à chaque consultation ;
**le tick ne la lit pas**.

**Niveaux de fidélité.**

- **Niveau 1** (déjà porté par le lot #219, inchangé) : les puissances, leurs
  ancres et leurs sources.
- **Niveau 2** (plausible, jamais sourcé ; une anomalie n'est pas un défaut) :
  la frontière « ancre la plus proche » et la **portée**, déclarées comme
  telles dans le fichier. Mesuré le 29 septembre 2026 sur la carte figée
  (596 cellules), dans le plan de la projection déclarée
  (`x = lon × cos(47,5°)`, `y = −lat`) : les cellules de Paris et de Londres
  sont à 0,39 et 0,40 de leur ancre, Constantinople à 11,9, Le Caire à 20,1.
  La portée retenue est **4,0 degrés projetés** (≈ 440 km) : 248 cellules
  couvertes, 348 non couvertes ; Rome (6,2) et Copenhague (5,7), dont les
  puissances ne sont pas dans la table, restent dehors. Budapest (2,5) tombe
  sous le Saint-Empire : anomalie de niveau 2, acceptée et non corrigée.
- **Niveau 3, pas simulé** : les frontières réelles, les enclaves, les
  suzerainetés, les terres contestées.

**Ce que le fichier gagne** (`jeu/data/puissances-1400.json`, au niveau
racine, rien d'autre ne change) :

- `"projection"` : `{"type": "equirectangular", "mid_latitude": 47.5,
  "comment": "x = lon * cos(mid_latitude), y = -lat"}`, le même bloc que
  `pluie-releves-1400.json` et `nil-cours-1400.json` ;
- `"portee"` : `{"degres_projetes": 4.0, "niveau": 2, "note": "<une phrase :
  plausible, jamais sourcée ; au-delà, la cellule est déclarée non
  couverte>"}`.

**Ce que `jeu/sim/puissances.py` gagne** (sous ce qui existe, sans rien en
retirer ; aucun littéral numérique hors {0, 1, −1} dans un corps de fonction,
`test_no_hardcoded` y veille) :

- `charger_latitude_moyenne_puissances(path=None) -> float` : lit
  `projection.mid_latitude` ; refuse (`PuissanceInvalide`, qui nomme le champ)
  un bloc absent ou une valeur qui n'est pas un nombre fini ;
- `charger_portee(path=None) -> float` : lit `portee.degres_projetes` ; refuse
  (`PuissanceInvalide`, message qui contient `portee`) un bloc absent, une
  valeur absente, textuelle, booléenne, non finie, nulle ou négative, et un
  `niveau` différent de `2` ;
- `puissance_par_cellule(positions, table, portee, latitude_moyenne) -> dict` :
  pure ; rend `cell_id → id de puissance` ou `None`. Elle appelle
  `derive_appartenance(positions, table.ancres, latitude_moyenne)` (une
  `Ancre` a `id`, `lat`, `lon`), puis, pour chaque cellule, compare le carré de
  la distance projetée (`facteur_de_projection`, `projeter` de
  `aggregation.py`) à son ancre retenue avec `portee²` : couverte si
  `carré ≤ portee²`, sinon `None`. Une `portee` égale à `math.inf` est
  acceptée par cette fonction (c'est la contre-épreuve), jamais par le
  fichier ; une portée nulle ou négative y lève `PuissanceInvalide` ;
- `puissances_depuis_monde(world, positions=None, table=None, portee=None,
  latitude_moyenne=None) -> dict` : adaptateur en lecture seule ; restreint
  les positions par `positions_du_monde` (une cellule sans position lève
  `PositionCelluleInconnue` qui la nomme) ; les entrées absentes sont lues des
  fichiers ;
- `puissance_de_cellule(cell_id, vue, table)` : rend la `Puissance`, ou
  `None` si la cellule est non couverte ou absente de la vue ;
- `cellules_non_couvertes(vue) -> tuple` : les `cell_id` à `None`, triés.

Aucune nouvelle dataclass n'est nécessaire ; s'il en faut une, elle hérite de
`_NoBadSpatialField` et n'a pas de champ `province…`.

## Périmètre
jeu/data/puissances-1400.json
jeu/sim/puissances.py
jeu/sim/tests/test_puissances.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent par `python3 -m pytest jeu/sim/tests/test_puissances.py -q -k
<nom>` depuis la racine ; chaque test imprime ses compteurs, et un échantillon
vide échoue. Les nouveaux cas s'**ajoutent** au fichier : aucun test du lot
#219 n'est modifié. Aucun `cell_id` n'est écrit dans le test : les cellules de
référence se dérivent de points nommés dans le test (niveau 1, pas lus de la
table) — Paris 48,86° N 2,35° E ; Londres 51,51° N 0,13° W ; Le Caire
30,04° N 31,24° E ; Constantinople 41,01° N 28,98° E — en cherchant le
centroïde le plus proche par `derive_appartenance` (le point cherche sa
cellule, comme dans `test_fleuve.py`) avec la projection du fichier. Les quatre
cellules de référence sont distinctes, sinon le test échoue.

**SC1 — la portée et la projection se lisent et se refusent** (`-k portee`).
Sur la vraie table : `charger_portee()` rend un nombre fini strictement
positif, `charger_latitude_moyenne_puissances()` égale la `mid_latitude` de
`province-centres-1400.json` (lue, pas écrite). Contre-épreuve, dans le même
test : la vraie table réécrite dans un fichier temporaire avec **une**
altération à la fois — `portee` retirée, `degres_projetes` retiré, en chaîne,
en booléen, à `NaN`, à `0`, à `-1`, `niveau` à `1`, `projection` retirée —
lève `PuissanceInvalide` à chaque cas (compteur `refus_observés` = nombre de
cas) ; et `charger_table` lit toujours cette même table altérée sans erreur
tant que seules `portee` ou `projection` sont touchées (le lot n'a pas
durci #219 en silence).

**SC2 — Paris, Londres, Le Caire, Constantinople** (`-k geographie`). Sur
`puissances_depuis_monde(World.charger(0))` : la cellule de Paris relève de la
puissance nommée `France`, celle de Londres de `Angleterre` (identifiées par
leur `nom` dans la table, pas par un `id` écrit dans le test) ; celles du
Caire et de Constantinople rendent `None` et figurent dans
`cellules_non_couvertes`. Contre-épreuve, dans le même test : la même table où
les ancres de la France et de l'Angleterre échangent leur champ `puissance`
(`dataclasses.replace`) fait relever Paris de l'Angleterre et Londres de la
France — le test exige que l'assertion de départ y soit fausse pour les deux ;
et `portee = math.inf` fait relever Le Caire d'une puissance (non `None`) et
vide `cellules_non_couvertes`.

**SC3 — chaque cellule est comptée une fois** (`-k compte`). Sur le monde
d'épreuve : les clés de la vue sont exactement `set(world.cells)` ;
`couvertes + non_couvertes == len(world.cells)` (dénominateur lu du monde),
les deux strictement positifs ; toute valeur non `None` est l'`id` d'une
puissance de la table ; toute puissance de la table couvre au moins une
cellule (sinon le test nomme la puissance). Contre-épreuve : avec une portée
plus petite que la plus petite distance mesurée entre une cellule et son
ancre (dérivée dans le test, divisée par deux), `couvertes` vaut 0 et le test
l'exige.

**SC4 — l'égalité se départage par le plus petit identifiant d'ancre**
(`-k egalite`). Une cellule synthétique à égale distance exacte de deux
ancres synthétiques d'identifiants 3 (puissance A) et 7 (puissance B),
symétriques en longitude, relève de A, que les ancres soient données dans
l'ordre 3, 7 ou 7, 3 ; le test vérifie que les deux carrés de distance sont
exactement égaux. Et une cellule exactement à la portée de son ancre est
couverte (`≤`), une cellule juste au-delà ne l'est pas.

**SC5 — une vue pure que le tick ne lit pas** (`-k pure`). Deux appels de
`puissances_depuis_monde` rendent la même vue ;
`json.dumps(world.to_dict(), sort_keys=True)` est identique avant et après ;
aucune `Cell` n'a gagné d'attribut ; des positions privées de la plus petite
cellule du monde lèvent `PositionCelluleInconnue` qui nomme ce `cell_id`. Puis,
depuis la racine :
`grep -rlE "sim\.puissances|from sim import puissances" jeu/sim --include=*.py | grep -v -e "sim/puissances.py" -e "sim/tests/"`
ne rend rien. Contre-épreuve : la même commande sans le second filtre rend
`jeu/sim/tests/test_puissances.py`.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert, sans
qu'aucun test existant ne soit modifié : les cas du lot #219 dans
`test_puissances.py`, `test_no_hardcoded.py` (qui inspecte `puissances.py`),
`test_province.py`, `test_pluie.py`, `test_fleuve.py` restent tels quels.
Contre-épreuve : un littéral `4` glissé dans un corps de fonction de
`puissances.py` rend `test_no_hardcoded` rouge.

**SC7 — le modèle le dit.** `grep -n "^## Les puissances de 1400, vue
dérivée" jeu/sim/MODELE.md` rend une ligne ; la section, placée après « Le
cours du Nil, vue dérivée », dit la provenance
(`data/puissances-1400.json`), les niveaux 1 et 2, la règle du plus proche et
son départage, la portée et sa valeur mesurée, « non couverte », et contient
« le tick ne la lit pas ». `grep -n "puissance" jeu/sim/MODELE.md` rend aussi
une ligne dans « En une page » (le paragraphe qui dit que la province et la
pluie ne se stockent pas). Sans la section, la première commande ne rend
rien.

## Hors périmètre
- Le tick, l'amorçage, `World.lire_carte` et la carte ne lisent pas la vue :
  aucune puissance n'entre dans le monde simulé dans ce lot.
- De nouvelles puissances ou de nouvelles ancres (Italie, Scandinavie, Europe
  de l'Est, Byzance, Mamelouks) : c'est ce qui couvrira un jour Le Caire et
  Constantinople, par la table, pas par la portée.
- Les frontières réelles, les enclaves, les suzerainetés, les maisons, les
  villes comme cellules (lot #209) : pas dans ce lot.
- Toute portée par puissance, toute pondération d'ancre, toute frontière
  lissée.
- `jeu/data/world-1400.json`, `jeu/data/province-centres-1400.json`,
  `sim/aggregation.py`, `sim/model.py`, `sim/world.py`, `sim/engine.py`,
  `sim/constants.py` : aucun ne change.
- L'affichage : aucune vue (tableau, chronique, relief, Unity) ne montre les
  puissances dans ce lot ; la carte des royaumes est un lot suivant.
