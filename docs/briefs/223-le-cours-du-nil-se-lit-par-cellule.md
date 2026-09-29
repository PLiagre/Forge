# Lot #223 — Le cours du Nil se lit par cellule
Jalon : J2 · Machine : vps · Taille prévue : 280 lignes

## But
Le monde sait dire quelles cellules le Nil traverse, du Caire aux embouchures
de Rosette et de Damiette, d'après une table de points réels qui cite sa
source ligne par ligne. C'est la donnée qui manque pour réparer le delta
(CAP.md, jalon 2 : « les régions denses de 1400 […] delta du Nil sont plus
denses que la médiane ») : depuis que le moteur a appris l'aridité, le delta
se vide comme le désert, parce que la pluie n'est pas l'eau.

## Règle du monde
Un fleuve passe par des lieux précis. Un point du cours appartient à la
cellule dont le centroïde est le plus proche de lui, et à nulle autre ; **une
cellule est traversée par le Nil si au moins un point du cours lui
appartient**. Pas de tracé interpolé entre deux points, pas de largeur, pas de
bassin versant : le point, sa cellule, c'est tout.

Le sens est l'inverse de celui de la pluie : pour la pluie, chaque cellule
cherche son relevé le plus proche ; ici, **chaque point cherche sa cellule**.
Les points sont les positions, les centroïdes des cellules sont les centres,
et c'est **la même fonction** `derive_appartenance` de `sim/aggregation.py`
qui tranche : il n'y a qu'une définition du « plus proche » et de son
départage dans `sim/`. À distance exactement égale, le plus petit `cell_id`
gagne.

Cela découle de trois sections de `jeu/sim/MODELE.md` :

- « La province dérivée et ses centres », sous-section « Ce que l'agrégation
  ne fait pas — et le motif que toute vue recopie » : le cours est une **vue
  dérivée**, hors de `sim.model`, pure, qui refuse de deviner, départage par
  le plus petit identifiant, et que le tick ne lit pas. `cell_id` reste la
  seule clé spatiale : rien n'est posé sur `Cell` ;
- « La pluie de 1400, vue dérivée » : elle déclare que « la pluie n'est pas
  l'eau » et que seul le futur mécanisme du fleuve pourra rendre au delta sa
  fertilité. Ce lot en pose la première pierre, la géographie, sans rien
  brancher ;
- « Déclaration explicite » : ce que la carte ne couvre pas se déclare.

**Niveaux de fidélité.**

- Les points du cours (latitude, longitude) sont de **niveau 1** : justes dans
  les grandes lignes. Chaque ligne cite sa source publique.
- Le cours est celui d'aujourd'hui ; les bras du delta ont bougé depuis 1400.
  Le fichier le déclare comme une **approximation**, pas comme une affirmation
  historique.
- L'attribution d'un point à une cellule est de **niveau 2** : une anomalie
  locale n'est pas un défaut.

**Ce qui est hors de la carte, déclaré.** La carte s'arrête vers 30,4° N. La
vallée au sud du Caire a pour plus proche le centroïde de la cellule de
**Suez** (mesuré : Beni Suef, 29,07° N, 31,10° E, y tombe) : la mettre dans la
table ferait dire au monde que le Nil traverse l'isthme. Elle n'y entre donc
pas, et le fichier le déclare en toutes lettres (clé `hors_carte`).

**Mesure qui corrige l'issue.** L'issue demandait pour contre-épreuve
d'échanger latitude et longitude. Mesuré sur `World.charger(0)` : les onze
points du Caire aux embouchures, échangés, restent **tous** dans la cellule du
delta (ils sont près de la diagonale 31° N / 31° E) ; cette contre-épreuve ne
peut pas échouer, elle ne prouve rien. Elle est remplacée par la faute de
signe sur la longitude (E lu comme W), qui envoie tous les points au Maroc, et
par l'ajout d'un point de la vallée, qui fait traverser Suez (SC2, SC3).

### Ce que le codeur écrit

**1. `jeu/data/nil-cours-1400.json`** — un document, un point par ligne :

```json
{
  "description": "Points du cours du Nil, du Caire aux embouchures, une source par ligne.",
  "cours_de_1400": "Approximation déclarée : …",
  "hors_carte": "La vallée au sud du Caire … cellule de Suez …",
  "fidelite": "Niveau 1 pour les points ; niveau 2 pour leur attribution à une cellule.",
  "projection": { "type": "equirectangular", "mid_latitude": 47.5,
                  "comment": "x = lon * cos(mid_latitude), y = -lat" },
  "points": [
    { "id": 1, "nom": "Le Caire", "lat": 0, "lon": 0, "source": "…" }
  ]
}
```

(les valeurs ci-dessus sont des gabarits, pas des données.)

- **entre 8 et 14 points**, identifiants entiers croissants depuis 1, en
  degrés décimaux WGS84 : le tronc (Le Caire, la pointe du delta vers
  El-Qanater), le bras de Rosette (par exemple Kafr el-Zayat, Desouk, Rosette,
  son embouchure) et le bras de Damiette (par exemple Benha, Mit Ghamr,
  Mansourah, Damiette, son embouchure) ;
- **`source`** nomme la page publique d'où vient la coordonnée, par exemple
  « Wikipédia, Mansourah (Égypte), coordonnées de l'article ». Un point qu'on
  ne peut pas rattacher à une source nommée ne s'écrit pas ;
- `mid_latitude` vaut 47,5, la projection documentée de la carte ;
- aucun point au sud du Caire (voir SC3).

**2. `jeu/sim/fleuve.py`** — sur le motif de `sim/pluie.py`, en important
`sim/aggregation.py` **sans le modifier** :

- `CoursDuNilInvalide(ValueError)` ;
- `PointDuCours`, dataclass figée héritant de `_NoBadSpatialField` : `id`,
  `nom`, `lat`, `lon`, `source` ;
- `CelluleTraversee`, dataclass figée héritant de `_NoBadSpatialField` :
  `cell_id`, `point_ids` (tuple trié) ;
- `charger_points(path=None)` lit le fichier et **refuse** par
  `CoursDuNilInvalide`, en nommant le point (son `id`) et le champ fautif : une
  table `points` vide ou absente ; une déclaration `cours_de_1400` ou
  `hors_carte` absente ou vide ; un `id` non entier (booléen compris) ou
  dupliqué ; un `nom` ou une `source` absents ou faits de blancs ; une `lat`
  ou une `lon` non numériques, booléennes ou non finies ;
- `charger_latitude_moyenne_fleuve(path=None)` lit `projection.mid_latitude`
  de ce fichier ;
- `cellules_traversees(points, positions, latitude_moyenne)`, pure : refuse
  une liste de points vide et des positions vides par `CoursDuNilInvalide`
  (avant l'appel, pour que le refus parle du fleuve et non des provinces),
  puis appelle `derive_appartenance({point.id: (point.lat, point.lon)},
  centroïdes, latitude_moyenne)`, où chaque centroïde est un petit
  enregistrement privé figé (`id` = `cell_id`, `lat`, `lon`) construit depuis
  `positions` ; rend un tuple de `CelluleTraversee` trié par `cell_id`, chaque
  point dans exactement une cellule ;
- `cours_depuis_monde(world, positions=None, points=None,
  latitude_moyenne=None)` : restreint les positions par `positions_du_monde`
  (qui lève `PositionCelluleInconnue` en nommant la cellule) et rend la vue.

Aucun littéral numérique autre que 0, 1, −1 dans un corps de fonction
(`sim/tests/test_no_hardcoded.py` inspecte tout module neuf de `sim/`). Les
clés du document sont des noms de module, comme dans `pluie.py`.

**3. `jeu/sim/MODELE.md`** — une section « ## Le cours du Nil, vue dérivée »,
placée juste après « La pluie de 1400, vue dérivée » : provenance et
approximation déclarée, niveaux, sens de l'attribution (le point cherche sa
cellule), départage, refus, la vallée **hors de la carte** et pourquoi (le
centroïde de Suez), et « le tick ne la lit pas » : le delta reste vidé par
l'aridité tant qu'un lot suivant n'aura pas donné l'eau du fleuve aux champs.
Aucun nombre mesuré n'y est recopié, aucun `cell_id` n'y est écrit.

## Périmètre
jeu/data/nil-cours-1400.json
jeu/sim/fleuve.py
jeu/sim/tests/test_fleuve.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent par `python3 -m pytest jeu/sim/tests/test_fleuve.py -q -k <nom>`
depuis la racine ; chaque test imprime ses compteurs, et un échantillon vide
échoue. Aucun `cell_id` n'est écrit dans le test : les cellules de référence
se dérivent de points nommés dans le test (niveau 1, pas lus de la table), en
cherchant le centroïde le plus proche par `derive_appartenance` avec la même
projection.

**SC1 — la table se lit et se refuse** (`-k table`). Sur la vraie table :
`points_lus` entre 8 et 14, autant de sources non vides, `cours_de_1400` et
`hors_carte` non vides. Contre-épreuve, dans le même test : la vraie table
réécrite dans un fichier temporaire avec **une** altération à la fois — source
retirée, source en blancs, `lat` en chaîne, `lon` en booléen, `lat` en `NaN`,
`id` dupliqué, `points` vide, `hors_carte` retirée — lève `CoursDuNilInvalide`
à chaque cas, et le message nomme l'`id` du point altéré quand l'altération
porte sur une ligne.

**SC2 — le delta est traversé, le désert et Suez non** (`-k geographie`). Sur
`cours_depuis_monde(World.charger(0))` : la cellule la plus proche de
30,8° N, 31,0° E (le delta) est traversée ; celle la plus proche de 30,9° N,
28,5° E (le désert occidental) et celle la plus proche de 30,45° N, 32,5° E
(l'isthme de Suez) ne le sont pas ; les trois cellules de référence sont
distinctes (sinon le test ne prouve rien). Contre-épreuve : la même table dont
chaque longitude change de signe (E lu comme W) ne traverse plus le delta —
le test l'exige.

**SC3 — chaque point sert, et la vallée reste dehors** (`-k couverture`). La
somme des `len(point_ids)` égale `points_lus` (dénominateur lu de la table),
l'union des `point_ids` est exactement l'ensemble des `id` de la table, et
chaque cellule rendue a au moins un point. Contre-épreuve : la table augmentée
d'un point de la vallée (29,07° N, 31,10° E, Beni Suef, nouvel `id` = plus
grand + 1) fait traverser la cellule de Suez — c'est la raison de la
déclaration `hors_carte`, et le test l'exige.

**SC4 — l'égalité se départage par le plus petit `cell_id`** (`-k egalite`).
Un point synthétique à égale distance exacte de deux cellules synthétiques
d'identifiants 3 et 7 (positions symétriques en longitude) va à la cellule 3,
que les positions soient données dans l'ordre 3, 7 ou 7, 3. Contre-épreuve :
le test vérifie que les deux carrés de distance sont exactement égaux.

**SC5 — une vue pure que le tick ne lit pas** (`-k pure`). Deux appels de
`cours_depuis_monde` rendent la même vue, et `json.dumps(world.to_dict(),
sort_keys=True)` est identique avant et après ; des positions privées de la
plus petite cellule du monde lèvent `PositionCelluleInconnue` qui nomme ce
`cell_id`. Puis, depuis la racine :
`grep -rlE "sim\.fleuve|from sim import fleuve" jeu/sim --include=*.py | grep -v -e "sim/fleuve.py" -e "sim/tests/"`
ne rend rien. Contre-épreuve : la même commande sans le second filtre rend
`jeu/sim/tests/test_fleuve.py` — le détecteur voit un import quand il y en a
un.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert, sans
qu'aucun test existant ne soit modifié : `test_no_hardcoded.py` inspecte
`fleuve.py`, `test_pluie.py`, `test_aridite.py`, `test_province.py` et
`test_write_coverage.py` restent tels quels. Contre-épreuve : un littéral
`30` glissé dans un corps de fonction de `fleuve.py` rend `test_no_hardcoded`
rouge.

**SC7 — le modèle le dit.** `grep -n "^## Le cours du Nil, vue dérivée"
jeu/sim/MODELE.md` rend une ligne, et la section contient « hors de la
carte », « Suez » et « le tick ne la lit pas » ; sans la section, la commande
ne rend rien.

## Hors périmètre
- Le tick ne lit pas le cours : ni la carte (`World.lire_carte`), ni la
  production, ni le facteur d'eau, ni l'amorçage ne changent. Le delta reste
  vide dans ce lot. Donner l'eau du fleuve aux champs est un lot suivant, et
  il le fera par une cause (la crue arrose), jamais par une exception
  égyptienne ni un plancher.
- La vallée au sud du Caire, la crue et son calendrier, l'irrigation, les
  canaux, les autres fleuves : déclarés, pas simulés.
- Tout tracé entre deux points, toute largeur de fleuve, tout commerce
  fluvial.
- `jeu/data/world-1400.json`, `jeu/data/pluie-releves-1400.json`,
  `jeu/data/province-centres-1400.json`, `sim/aggregation.py`, `sim/pluie.py`,
  `sim/world.py`, `sim/engine.py`, `sim/constants.py` : aucun ne change.
- L'affichage : aucune vue (tableau, chronique, relief, Unity) ne montre le
  fleuve dans ce lot.
