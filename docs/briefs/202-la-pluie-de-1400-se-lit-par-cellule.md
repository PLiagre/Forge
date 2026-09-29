# Lot #202 — La pluie de 1400 se lit par cellule
Jalon : J2 · Machine : vps · Taille prévue : 285 lignes

## But
Le monde sait dire, pour chacune de ses cellules, combien il y pleut en une
année, d'après une table de relevés réels qui cite sa source ligne par ligne :
c'est la première donnée d'aridité du monde de 1400, celle dont l'amorçage
aura besoin pour vider le désert (CAP.md, jalon 2 : « le moteur apprend
l'aridité »).

## Règle du monde
Il pleut sur une terre selon le climat de l'endroit. Un pluviomètre représente
la région qui l'entoure : **une cellule reçoit la pluie annuelle du relevé le
plus proche d'elle**, et de nul autre. Pas d'interpolation, pas de moyenne
pondérée, pas de correction par le relief : le plus proche, c'est tout.

Cela découle de `jeu/sim/MODELE.md`, section « La province dérivée et ses
centres », et de sa sous-section « Ce que l'agrégation ne fait pas — et le
motif que toute vue recopie » : la pluie est une **vue dérivée**, recalculée à
chaque consultation, hors de `sim.model`, pure, qui refuse de deviner, qui
départage ses égalités par le plus petit identifiant, et que le tick ne lit
pas. `cell_id` reste la seule clé spatiale : aucun `releve_id` ni aucune pluie
n'est stocké sur `Cell`.

**Niveaux de fidélité.**

- Les relevés (point, millimètres par an) sont de **niveau 1** : justes dans
  les grandes lignes — l'ordre de grandeur, et le contraste entre la façade
  atlantique et le désert. Chaque ligne cite sa source publique.
- **Le climat actuel tient lieu de celui de 1400**, et le fichier le déclare
  en toutes lettres : la pluie de 1400 n'a pas été mesurée ; les normales
  climatiques du XXᵉ siècle (ou de 1991–2020) en sont une approximation. Cette
  déclaration est une absence de donnée dite, pas une affirmation historique.
- L'attribution d'un relevé à une cellule est de **niveau 2** : une cellule de
  15 000 km² à cheval sur une montagne reçoit une seule valeur, et une
  anomalie locale n'est pas un défaut.

**Ce que la pluie ne dit pas, à déclarer dans `MODELE.md`** : la pluie n'est
pas l'eau. Par la pluie, le delta du Nil est presque aussi sec que le désert
occidental ; ce qui le rend fertile — la crue du fleuve — n'est dans aucune
table du dépôt. Aucun lot ne doit lire cette vue comme si elle suffisait à
faire la densité du delta.

### Ce que le codeur écrit

**1. `jeu/data/pluie-releves-1400.json`** — un document, un relevé par ligne :

```json
{
  "description": "Relevés de pluie annuelle, un point par ligne, une source par ligne.",
  "climat_de_1400": "Approximation déclarée : …",
  "unite": "mm/an",
  "fidelite": "Niveau 1 dans les grandes lignes …",
  "projection": { "type": "equirectangular", "mid_latitude": 47.5,
                  "comment": "x = lon * cos(mid_latitude), y = -lat" },
  "releves": [
    { "id": 1, "nom": "Bergen", "lat": 60.38, "lon": 5.33, "mm_par_an": 0, "source": "…" }
  ]
}
```

(les valeurs ci-dessus sont des gabarits, pas des données.)

- **entre 35 et 45 relevés**, identifiants entiers croissants depuis 1 ; `lat`
  et `lon` en degrés décimaux WGS84, ceux de la station ; `mm_par_an` le cumul
  annuel moyen ;
- **`source`** nomme l'organisme, la station et la période des normales, par
  exemple « Met Norway, Bergen-Florida, normales 1991–2020, via Wikipédia
  (Bergen, tableau climatique) ». Une valeur qu'on ne peut pas rattacher à une
  source nommée ne s'écrit pas : un relevé de moins vaut mieux qu'un relevé
  deviné ;
- **au moins un relevé** dans chacune de ces régions, pour que le contraste
  tienne : façade atlantique de l'Irlande, Grande-Bretagne (ouest et est),
  Norvège occidentale, Scandinavie méridionale, Flandre ou Pays-Bas, France
  (Atlantique, Bassin parisien, Méditerranée), Péninsule ibérique (Galice,
  Meseta, Andalousie ou Levant), Alpes, Allemagne, Pologne ou pays baltes,
  plaine hongroise ou Autriche, Italie du Nord et du Sud, Balkans, Grèce,
  Anatolie occidentale, Crimée ou Ukraine, Maroc (côte et versant
  présaharien), Algérie (côte et présaharien), Tunisie, Libye (Tripolitaine,
  Cyrénaïque), Égypte (côte et Le Caire), Levant méridional ou Sinaï ;
- **tout relevé sert au moins une cellule** (voir SC2) : un relevé qu'aucune
  cellule n'a pour plus proche est une donnée morte, il se retire. La carte
  couvre les centroïdes de 30,4° N à 61,5° N et de 10° W à 34,8° E : une
  station hors de cette étendue risque de ne servir personne.

**2. `jeu/sim/pluie.py`** — le module de la vue, sur le modèle de
`sim/aggregation.py`, qu'il **importe sans le modifier** :

- `ReleveDePluieInvalide(ValueError)` ;
- `ReleveDePluie`, dataclass figée héritant de `_NoBadSpatialField` : `id`,
  `nom`, `lat`, `lon`, `mm_par_an`, `source` ;
- `PluieDeCellule`, dataclass figée héritant de `_NoBadSpatialField` :
  `cell_id`, `releve_id`, `mm_par_an` ;
- `charger_releves(path=None)` lit le fichier et **refuse** par
  `ReleveDePluieInvalide`, en nommant le relevé (son `id`) et le champ
  fautif : une table vide ; une déclaration `climat_de_1400` absente ou
  vide ; une `unite` autre que `"mm/an"` ; un `id` non entier (booléen
  compris) ou dupliqué ; un `nom` ou une `source` absents ou faits de blancs ;
  une `lat`, une `lon` ou un `mm_par_an` non numériques, booléens ou non
  finis ; un `mm_par_an` négatif. **`0` est accepté** : un désert sans pluie
  mesurée est une mesure ;
- `charger_latitude_moyenne_pluie(path=None)` lit `projection.mid_latitude`
  de ce fichier, jamais de celui des provinces ;
- `pluie_par_cellule(positions, releves, latitude_moyenne)`, pure : refuse
  une liste de relevés vide par `ReleveDePluieInvalide`, puis **appelle
  `derive_appartenance` de `sim/aggregation.py`** (les relevés ont `id`,
  `lat`, `lon`) — il n'y a qu'une définition du « plus proche » et de son
  départage dans `sim/` ; rend un tuple de `PluieDeCellule` trié par
  `cell_id` ;
- `pluie_depuis_monde(world, positions=None, releves=None,
  latitude_moyenne=None)` : restreint les positions par `positions_du_monde`
  (qui lève `PositionCelluleInconnue` en nommant la cellule) et rend la vue ;
- `pluie_de_cellule(cell_id, pluies)` : les millimètres, ou `None` pour une
  cellule absente de la vue — `None` n'est pas zéro ;
- `releves_sans_cellule(pluies, releves)` : les `id` des relevés qu'aucune
  cellule n'a retenus, triés — un fait mesuré.

Aucun littéral numérique autre que 0, 1, −1 dans un corps de fonction
(`sim/tests/test_no_hardcoded.py` inspecte tout module neuf de `sim/`). Les
clés du document sont des noms de module, comme dans `aggregation.py`.

**3. `jeu/sim/MODELE.md`** — une section « ## La pluie de 1400, vue dérivée »,
placée après « La province dérivée et ses centres » : provenance et
déclaration d'approximation, niveaux, règle du plus proche et du départage,
refus, le Nil déclaré, et « le tick ne la lit pas ». Dans « En une page », le
paragraphe de la province dit que la pluie, elle non plus, n'est ni stockée ni
consommée par le tick. Aucun nombre mesuré n'y est recopié (règle du fichier :
un compteur se cite par son nom).

## Périmètre
jeu/data/pluie-releves-1400.json
jeu/sim/pluie.py
jeu/sim/tests/test_pluie.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent par `python3 -m pytest jeu/sim/tests/test_pluie.py -q -k <nom>`
depuis la racine ; chaque test imprime ses compteurs, et un échantillon vide
échoue.

**SC1 — la table se lit et se refuse** (`-k table`). Sur la vraie table :
`releves_lus` entre 35 et 45, chacun avec une source non vide, `climat_de_1400`
non vide, `unite == "mm/an"`. Contre-épreuve, dans le même fichier de test : la
vraie table réécrite dans un fichier temporaire avec **une** altération à la
fois — source retirée, source en blancs, `mm_par_an` négatif, en chaîne, en
booléen, en `NaN`, `id` dupliqué, `releves` vide, `climat_de_1400` retiré,
`unite` changée — lève `ReleveDePluieInvalide` à chaque cas, et le message
nomme l'`id` du relevé altéré quand l'altération porte sur une ligne. Un
`mm_par_an` mis à `0` est **accepté**.

**SC2 — chaque cellule a sa pluie, chaque relevé sert** (`-k couverture`). Sur
`World.charger(0)` : `cellules_avec_pluie == len(world.cells)` (dénominateur
lu du monde, jamais écrit), `cellules_sans_pluie == 0`, et
`releves_sans_cellule == 0`. Contre-épreuves : la table augmentée d'un relevé
qui recopie le premier en **échangeant `lat` et `lon`** (nouvel `id` = plus
grand + 1) donne `releves_sans_cellule == 1` ; des positions privées de la
plus petite cellule du monde lèvent `PositionCelluleInconnue`, et le message
contient ce `cell_id`.

**SC3 — l'égalité se départage par le plus petit id** (`-k egalite`). Une
cellule synthétique à égale distance exacte de deux relevés d'`id` 3 et 7
(positions symétriques en longitude) reçoit le relevé 3, que les relevés
soient passés dans l'ordre `[3, 7]` ou `[7, 3]`. Contre-épreuve : le test
vérifie que les deux carrés de distance sont exactement égaux — un cas qui ne
serait pas une vraie égalité ne prouverait rien.

**SC4 — le désert est sec, l'Atlantique mouillé** (`-k geographie`). Le test
nomme quatre points de référence (niveau 1, écrits dans le test, pas lus de la
table) : le désert occidental égyptien (30,9° N, 28,5° E), l'isthme de Suez
(30,45° N, 32,5° E), Bergen (60,39° N, 5,32° E) et Galway (53,27° N,
9,05° W). Pour chacun, la cellule dont le centroïde est le plus proche (même
projection) ; exigé : la pluie de chacune des deux cellules sèches est
strictement sous la **médiane des pluies du monde**, elle-même strictement
sous la pluie de chacune des deux cellules mouillées. La médiane se dérive de
la vue. Contre-épreuve : la même vérification, sur la table dont les
millimètres sont **inversés par rang** (le plus sec reçoit la valeur du plus
mouillé, et ainsi de suite), doit rendre faux — le test l'exige.

**SC5 — une vue pure que le tick ne lit pas** (`-k pure`). Deux appels de
`pluie_depuis_monde` rendent la même vue, et `json.dumps(world.to_dict(),
sort_keys=True)` est identique avant et après. Aucun module de `sim/` hors
`pluie.py` et hors tests n'importe `sim.pluie` ni ne nomme ses fonctions
publiques (lecture de l'arbre syntaxique, dénominateur dérivé du répertoire,
`modules_parcourus > 0`). Contre-épreuve : le même détecteur, appliqué à la
source synthétique `from sim.pluie import pluie_depuis_monde`, la signale.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert, sans
qu'aucun test existant ne soit modifié : `test_no_hardcoded.py` inspecte
`pluie.py`, `test_province.py` et `test_write_coverage.py` restent tels quels.
Contre-épreuve : un littéral `1000` glissé dans un corps de fonction de
`pluie.py` rend `test_no_hardcoded` rouge.

**SC7 — le modèle le dit.** `grep -n "^## La pluie de 1400, vue dérivée"
jeu/sim/MODELE.md` rend une ligne, et la section contient les mots
« approximation », « Nil » et « le tick ne la lit pas » ; sans la section, la
commande ne rend rien.

## Hors périmètre
- Le tick ne lit pas la pluie : ni l'amorçage, ni la population de départ, ni
  la production, ni le rendement ne changent. Brancher la pluie sur le monde
  est un lot suivant, et il le fera par une cause (l'eau manque aux champs),
  jamais par un « si sec alors −x % ».
- Le Nil, les fleuves, l'irrigation, les oasis : déclarés absents, pas
  simulés.
- La répartition de la pluie dans l'année (mois, saisons), la variabilité
  d'une année à l'autre, le changement du climat de 1400 à 1900.
- Toute interpolation entre relevés, toute correction par le relief ou
  l'altitude.
- `jeu/data/world-1400.json`, `jeu/data/province-centres-1400.json`,
  `sim/aggregation.py`, `sim/constants.py`, `sim/engine.py` et
  `sim/snapshot_export.py` : aucun ne change.
- L'affichage : aucune vue (tableau, chronique, relief, Unity) ne montre la
  pluie dans ce lot.
