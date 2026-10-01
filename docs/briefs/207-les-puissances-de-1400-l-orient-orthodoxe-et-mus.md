# Lot #207 — Les puissances de 1400 : l'Orient orthodoxe et musulman
Jalon : J2 · Machine : vps · Taille prévue : 270 lignes

## But
Le monde sait dire qu'au 1er janvier 1400 la cellule de Constantinople relève de Byzance, celle du Caire des Mamelouks, celle d'Edirne des Ottomans, celle de Tunis des Hafsides, celle de Novgorod de Novgorod, et que chaque cellule restée sans maître l'est pour une raison écrite dans la table : la table des puissances couvre l'Europe et la Méditerranée de la carte, pour la carte des royaumes et la preuve « des points connus appartiennent à la bonne puissance (Paris, Londres, Venise, Constantinople, Le Caire) ; un point que la table ne couvre pas est déclaré, jamais deviné » (CAP.md, jalon 2).

## Règle du monde
La règle ne change pas. La table `data/puissances-1400.json` gagne des lignes,
et la vue existante les lit telles quelles : une cellule relève de la puissance
qui tient l'ancre la plus proche de son centroïde, dans la **portée** de 4,0
degrés projetés ; au-delà, elle est **non couverte**. Cela découle de
`jeu/sim/MODELE.md`, section « Les puissances de 1400, vue dérivée » (et « La
province dérivée et ses centres » pour la règle du plus proche et son
départage). La portée, la projection, `charger_table`, `puissance_par_cellule`
et `puissances_depuis_monde` ne changent pas ; **le tick ne lit pas la table**.

**Ce qui s'ajoute : la raison déclarée d'une cellule non couverte.** La table
gagne une liste `lacunes` : chaque lacune est un point nommé avec sa raison
(« Finlande, suédoise en 1400, sans ancre dans la table »). Une cellule non
couverte est **expliquée** par la lacune la plus proche de son centroïde (même
règle du plus proche, même départage par le plus petit identifiant, même
projection), si cette lacune est dans la portée ; sinon elle reste **sans
raison**, et le test l'interdit. Une lacune n'attribue rien : elle ne donne
aucune cellule à aucune puissance. C'est le « refus de deviner » de la section
« La province dérivée et ses centres », écrit cellule par cellule.

**Niveaux de fidélité.**

- **Niveau 1** (sources publiques) : l'existence de chaque puissance au
  1er janvier 1400, sa nature, sa religion, et l'appartenance de chaque ancre
  à sa puissance ce jour-là.
- **Niveau 2** (plausible, une anomalie n'est pas un défaut) : la frontière du
  plus proche, et le point de chaque lacune. Mesuré par le chef sur la carte
  figée : Rhodes donne aux Hospitaliers les Cyclades orientales, l'est de la
  Crète et un bout de côte carienne ; Mistra donne à Byzance l'Attique, les
  îles Ioniennes et l'ouest de la Crète. C'est accepté, pas corrigé.
- **Niveau 3, pas simulé** : les suzerainetés (Serbie et Valachie vassales
  des Ottomans, Byzance tributaire, Chypre tributaire des Mamelouks), le siège
  de Constantinople (1394-1402), l'Église de Bosnie, les beyliks d'Anatolie
  comme puissances : ceux que Bayezid a annexés avant 1400 (Karesi, Saruhan,
  Teke, Karaman) sont sous les Ottomans ; ceux qui restent libres (Candar à
  Sinop, Trébizonde) sont hors de la carte.

**Trois natures de plus.** `NATURES` gagne `empire` (Byzance), `sultanat`
(Ottomans, Mamelouks, Hafsides, Zayyanides, Mérinides) et `khanat` (Horde
d'Or). Rien d'autre ne s'élargit : `duché`, `comté`, `beylik`, `despotat`
restent refusés ; les religions ne changent pas (`orthodoxe` et `musulmane`
existent déjà).

### Ce que le codeur écrit

**1. `jeu/data/puissances-1400.json`.** La `description` dit « l'Ouest,
l'Italie, le Nord, le Centre et l'Orient » ; `projection`, `portee`, `date`
identiques. Les 24 puissances et les 46 ancres existantes restent
**identiques, mêmes `id`**. On ajoute, une ligne par entrée :

| id | nom (exact, le test le lit) | nature | religion | ancres (lat ; lon) |
|---|---|---|---|---|
| 25 | `Byzance` | empire | orthodoxe | Constantinople (41,01 ; 28,98), Mistra (37,07 ; 22,37) |
| 26 | `Ottomans` | sultanat | musulmane | Edirne (41,68 ; 26,56), Sofia (42,70 ; 23,32), Thessalonique (40,64 ; 22,94), Manisa (38,61 ; 27,43), Ankara (39,93 ; 32,85), Konya (37,87 ; 32,48), Antalya (36,89 ; 30,71), Balıkesir (39,65 ; 27,88) |
| 27 | `Serbie` | principauté | orthodoxe | Kruševac (43,58 ; 21,33) |
| 28 | `Bosnie` | royaume | catholique | Bobovac (44,14 ; 18,22) |
| 29 | `Valachie` | principauté | orthodoxe | Târgoviște (44,93 ; 25,46) |
| 30 | `Moldavie` | principauté | orthodoxe | Suceava (47,65 ; 26,26) |
| 31 | `Novgorod` | république | orthodoxe | Novgorod (58,52 ; 31,27) |
| 32 | `Pskov` | république | orthodoxe | Pskov (57,82 ; 28,33) |
| 33 | `Horde d'Or` | khanat | musulmane | Qırq Yer (44,74 ; 33,88) |
| 34 | `Mamelouks` | sultanat | musulmane | Alexandrie (31,20 ; 29,92), Damiette (31,42 ; 31,81) |
| 35 | `Hafsides` | sultanat | musulmane | Tunis (36,81 ; 10,18) |
| 36 | `Zayyanides` | sultanat | musulmane | Tlemcen (34,88 ; −1,32) |
| 37 | `Mérinides` | sultanat | musulmane | Fès (34,03 ; −5,00), Marrakech (31,63 ; −7,99) |
| 38 | `Chypre` | royaume | catholique | Nicosie (35,17 ; 33,36) |
| 39 | `Hospitaliers` | ordre | catholique | Rhodes (36,43 ; 28,22) |
| 23 (existante) | `Pologne-Lituanie` | — | — | **deux ancres de plus** : Kiev (50,45 ; 30,52), Smolensk (54,78 ; 32,05) |

L'apostrophe de `Horde d'Or` est l'apostrophe droite `'`. Ancres numérotées de
**48 à 74** dans l'ordre du tableau (Constantinople 48 … Rhodes 72, Kiev 73,
Smolensk 74) ; **l'id 24 reste libre** (la contre-épreuve Calais de
`test_ancrage_dans_la_carte` l'utilise). Total : **39 puissances, 73 ancres**.
Kiev et Smolensk sont nécessaires : sans elles, la Moldavie et Novgorod
prennent les cellules lituaniennes (mesuré).

Chaque `source` nomme l'article public qui atteste l'appartenance en 1400 (par
exemple : Thessalonique, ottomane de 1387 à 1403 ; Konya, Karaman annexé par
Bayezid en 1397-1398 ; Manisa, Saruhan annexé en 1390 ; Smolensk, prise par
Vytautas en 1395 ; Suceava, capitale moldave depuis 1388 ; Rhodes, aux
Hospitaliers depuis 1310). Le codeur vérifie chaque ligne contre sa source.
Une ancre qu'il ne peut pas sourcer est remplacée par une ancre de la même
puissance qu'il peut sourcer, au même nombre (pour Qırq Yer : Or Qapı /
Perekop, 46,16 ; 33,69), et il remesure SC4 et SC5 ; s'il ne trouve pas de
remplaçant, il s'arrête et le dit dans la PR — **il ne baisse jamais les
planchers 39 et 73**.

**Pièges, à ne pas ancrer** (mesurés ou vérifiés par le chef) : **Bursa** et
**Iznik** (ottomanes en 1400, mais une ancre ottomane à l'une ou l'autre fait
tomber la cellule de Constantinople sous les Ottomans : mesuré) ; **Athènes**
(duché des Acciaioli, florentins, pas byzantine) ; **Le Caire** (30,04 N, au
sud de la carte, qui s'arrête à 30,45 N ; la cellule du Caire tombe sous les
Mamelouks par Alexandrie et Damiette) ; **Kaffa**, **Moscou**, **Tver**,
**Sarai**, **Sinop**, **Trébizonde**, **Damas** (hors de la carte).

Le fichier gagne enfin, au niveau racine, la liste **`lacunes`** (champs `id`,
`nom`, `lat`, `lon`, `raison`), exactement ces huit, dont le chef a mesuré
qu'elles expliquent les 31 cellules non couvertes :

| id | nom | lat ; lon | raison (une phrase, à reprendre ou préciser) |
|---|---|---|---|
| 1 | `Shetland` | 60,15 ; −1,15 | norvégiennes en 1400 (Union de Kalmar), plus loin de Bergen que la portée |
| 2 | `Féroé` | 62,01 ; −6,77 | norvégiennes en 1400 (Union de Kalmar), plus loin de Bergen que la portée |
| 3 | `Finlande` | 60,45 ; 22,27 | Finlande et Åland, suédoises en 1400 (Union de Kalmar), sans ancre dans la table |
| 4 | `Hiiumaa` | 58,88 ; 22,65 | île de Livonie (Ordre livonien, évêché d'Ösel-Wiek), puissance absente de la table |
| 5 | `Dalécarlie` | 60,61 ; 15,63 | Suède centrale (Union de Kalmar), plus loin de Kalmar et de Bergen que la portée |
| 6 | `Tripolitaine` | 32,89 ; 13,19 | marge du sultanat hafside, plus loin de Tunis que la portée |
| 7 | `Cyrénaïque` | 32,49 ; 20,83 | terres bédouines entre Hafsides et Mamelouks, sans ville tenue par une puissance de la table |
| 8 | `Oued Righ` | 33,10 ; 6,07 | oasis du Sahara, tribus hors de tout État de la table |

**2. `jeu/sim/puissances.py`** (sous ce qui existe ; aucun littéral numérique
hors {0, 1, −1} dans un corps de fonction, `test_no_hardcoded` y veille) :

- `NATURES` gagne `"empire"`, `"sultanat"`, `"khanat"` ; la docstring du
  module ne dit plus « d'Europe » seulement.
- `Lacune(_NoBadSpatialField)`, dataclass gelée : `id`, `nom`, `lat`, `lon`,
  `raison`.
- `charger_lacunes(path=None) -> tuple` : lit `lacunes`, triées par `id` ;
  refuse (`PuissanceInvalide`) une liste absente ou vide (message
  « champ lacunes »), un `id` dupliqué ou booléen, un `nom` ou une `raison`
  absents ou vides, une `lat`/`lon` non numérique ou non finie (message
  « lacune <id>, champ <champ> »). Elle réutilise `_refuser_id`, `_texte` et
  `_nombre` ; `_nombre` peut gagner un paramètre `sorte` dont la valeur par
  défaut garde le message « ancre … » actuel. `charger_table` ne lit pas les
  lacunes et n'en dépend pas.
- `lacune_par_cellule(positions, vue, lacunes, portee, latitude_moyenne) ->
  dict` : pure ; ses clés sont exactement `cellules_non_couvertes(vue)` ; la
  valeur est l'`id` de la lacune la plus proche par `derive_appartenance`, si
  le carré de sa distance projetée est `≤ portee²`, sinon `None`. Le codeur
  peut mettre en commun le calcul « plus proche dans la portée » avec
  `puissance_par_cellule` dans une fonction privée, à comportement identique.

**3. `jeu/sim/tests/test_puissances.py`** : les nouveaux cas s'**ajoutent**
dans de nouvelles fonctions de test. **Quatre lignes existantes, et elles
seules, sont réécrites**, décidées par le propriétaire sur l'issue #207 (deux
réponses « A ») :

```python
    assert noms["Le Caire"].nom == "Mamelouks" and cellules["Le Caire"] not in non_couvertes
    assert noms["Constantinople"].nom == "Byzance" and cellules["Constantinople"] not in non_couvertes
```

à la place des deux lignes `is None … in non_couvertes` de
`test_geographie_des_puissances_et_des_non_couvertes` (lot #220), et

```python
        assert 39 <= len(table.puissances) == len(document["puissances"]) <= 40
        assert 73 <= len(table.ancres) == len(document["ancres"]) <= 80
```

à la place des deux lignes `24 <=` / `46 <=` de `verifier_bornes` dans
`test_lecture_des_douze_ajouts` (lot #206). Rien d'autre ne change : ni
`test_lecture_de_toutes_les_lignes`, ni `CAS_REFUS`, ni `_alterer`, ni
`_connues`, ni `_compter_ancrage`, ni la suite de ces deux tests.

**4. `jeu/sim/MODELE.md`**, section « Les puissances de 1400, vue dérivée »
seulement : la table couvre aussi l'Orient (Byzance, les Ottomans, les
Mamelouks, le Maghreb, la Russie de Novgorod) ; les natures `empire`,
`sultanat`, `khanat` ; la couverture remesurée (565 couvertes, 31 non
couvertes, sur 596) ; les **lacunes** et la règle qui les lie aux cellules
non couvertes ; Le Caire au sud de la carte, sa cellule la plus proche sous
les Mamelouks ; les puissances hors de la carte (Moscou, Tver, la Horde à
Sarai, Kaffa, Sinop, Trébizonde, Damas) ; les anomalies de niveau 2 mesurées.
La phrase « laisse notamment Le Caire et Constantinople hors de la table
actuelle » disparaît (le texte « Constantinople hors de la table » ne reste
nulle part dans le fichier).

## Périmètre
jeu/data/puissances-1400.json
jeu/sim/puissances.py
jeu/sim/tests/test_puissances.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par
`python3 -m pytest jeu/sim/tests/test_puissances.py -q -s -k <nom>` ; chaque
test imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` ni
`id` de puissance n'est écrit dans un test : les puissances se trouvent par
leur `nom`, les cellules par des points nommés dans le test (niveau 1, pas lus
de la table) qui cherchent leur centroïde par `_cellule_la_plus_proche` (déjà
dans le fichier). Prouver chaque contre-épreuve rouge avant de la garder.

**SC1 — toute la table se lit** (`-k lecture`). Les deux tests existants sont
verts (`test_lecture_des_douze_ajouts` avec ses seules bornes réécrites : la
table sans la Hongrie y viole désormais le plancher 39). Un nouveau test
vérifie que les 15 noms ajoutés sont lus, chacun avec au moins une ancre
(`ajouts_lus == 15`), et que Kiev et Smolensk sont des ancres de
`Pologne-Lituanie`. Contre-épreuve : la table réécrite sans Byzance ni ses
ancres rend `ajouts_lus == 14`.

**SC2 — les refus tiennent, les trois natures n'ouvrent rien d'autre**
(`-k refus`). Les 17 cas de `CAS_REFUS` et les 4 cas du lot #206 restent
verts, inchangés. Un nouveau test paramétré ajoute, une altération à la fois
dans `tmp_path` : toutes les ancres de Byzance retirées (message « puissance
<id de Byzance> » et `ancres`) ; nature des Ottomans à `"beylik"` ; nature de
la Horde d'Or à `"horde"` ; religion des Mamelouks à `"copte"`. Chacun lève
`PuissanceInvalide` en nommant la ligne et le champ. Contre-épreuve : la vraie
table, où Byzance est `empire`, se charge.

**SC3 — les puissances ajoutées sont justes** (`-k connues`). Une nouvelle
fonction vérifie sur la vraie table les 15 noms exacts avec leur nature et
leur religion du tableau ; `_connues` (#219) et le test du lot #206 restent
vrais. Contre-épreuves : fausse sur la table où Byzance est `catholique`, puis
sur celle où les Hospitaliers sont retirés avec leur ancre.

**SC4 — Constantinople sous Byzance** (`-k geographie`). Le test existant, ses
deux lignes réécrites, est vert : Paris → `France`, Londres → `Angleterre`,
Constantinople (41,01 N 28,98 E) → `Byzance`, Le Caire (30,04 N 31,24 E) →
`Mamelouks`. Un nouveau test, sur `puissances_depuis_monde(World.charger(0))`,
exige des cellules **distinctes** (sinon échec) et la puissance nommée pour :
Mistra 37,07 N 22,37 E → `Byzance` ; Edirne 41,68 N 26,56 E et Ankara
39,93 N 32,85 E → `Ottomans` ; Kruševac 43,58 N 21,33 E → `Serbie` ; Bobovac
44,14 N 18,22 E → `Bosnie` ; Târgoviște 44,93 N 25,46 E → `Valachie` ; Suceava
47,65 N 26,26 E → `Moldavie` ; Novgorod 58,52 N 31,27 E → `Novgorod` ; Pskov
57,82 N 28,33 E → `Pskov` ; Qırq Yer 44,74 N 33,88 E → `Horde d'Or` ; Tunis
36,81 N 10,18 E → `Hafsides` ; Tlemcen 34,88 N 1,32 W → `Zayyanides` ; Fès
34,03 N 5,00 W → `Mérinides` ; Nicosie 35,17 N 33,36 E → `Chypre` ; Rhodes
36,43 N 28,22 E → `Hospitaliers` ; Kiev 50,45 N 30,52 E → `Pologne-Lituanie`.
(Alexandrie n'y est pas : sa cellule est celle du Caire.) Contre-épreuves, en
mémoire (`dataclasses.replace`) : les ancres de Byzance et des Ottomans
échangent leur champ `puissance` → Constantinople relève des Ottomans et
Edirne de Byzance ; une ancre ottomane ajoutée à Bursa (40,19 N 29,06 E) →
Constantinople relève des Ottomans (le piège mesuré).

**SC5 — chaque puissance couvre au moins une cellule** (`-k compte`). Le test
existant du lot #220 est vert, inchangé, sur les 39 puissances (il nomme
celle qui n'en couvre pas). Le nouveau test de SC4 imprime `couvertes` et
`non_couvertes` (somme égale à `len(world.cells)` ; mesuré 565 et 31).
Contre-épreuve : la table sans l'ancre de Nicosie (en mémoire) ne donne plus
aucune cellule à Chypre.

**SC6 — chaque cellule non couverte a sa raison** (`-k lacune`). Sur le monde
d'épreuve : `charger_lacunes()` rend 8 lacunes, toutes avec une `raison` non
vide ; les clés de `lacune_par_cellule` sont exactement
`cellules_non_couvertes(vue)` ; `sans_raison` (valeurs `None`) vaut 0 ;
`lacunes_inutiles` (lacunes qui n'expliquent aucune cellule) vaut 0 ; le test
imprime `non_couvertes`, `sans_raison`, `lacunes_inutiles`, et exige
`non_couvertes > 0`. Contre-épreuves : sans la lacune `Cyrénaïque`,
`sans_raison == 1` ; avec une lacune de plus à Paris (48,86 N 2,35 E),
`lacunes_inutiles == 1`. Refus, une altération à la fois dans `tmp_path` :
`lacunes` retirée, `raison` vide, `raison` absente, `lat` en chaîne, `lon` à
`NaN`, `id` dupliqué → `PuissanceInvalide` nommant `lacunes` ou
« lacune <id> » et le champ (compteur `refus_observés` égal à la longueur de
la liste, > 0) ; et `charger_table` lit toujours chacune de ces tables
altérées.

**SC7 — pas d'ancre sur un piège** (`-k ancrage`). Les deux tests existants
restent verts, inchangés (toute ancre hors de la carte, comme Le Caire, y est
déjà refusée). Un nouveau test écrit ses points : Bursa, Iznik
(40,43 N 29,72 E), Athènes (37,98 N 23,73 E) ; aucune ancre à moins de 0,2° en
latitude **et** en longitude de l'un d'eux (`ancres_sur_piege == 0`).
Contre-épreuve : une ancre ottomane ajoutée à Bursa compte 1.

**SC8 — quatre réécritures, et rien d'autre ne bouge.**
`git diff origin/master -- jeu/sim/tests/test_puissances.py | grep -c '^-[^-]'`
rend **4**, et ces quatre lignes retirées sont les deux `is None … in
non_couvertes` et les deux bornes `24 <=` / `46 <=` de `verifier_bornes`.
Contre-épreuve : toute autre ligne existante touchée fait monter ce compte.
Puis `python3 -m pytest jeu -q` est vert ; `test_no_hardcoded.py` inspecte
toujours `puissances.py` (un littéral `4` glissé dans `lacune_par_cellule` le
fait rougir).

**SC9 — le modèle le dit.**
`awk '/^## Les puissances de 1400, vue dérivée/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep -c -e Byzance -e lacune`
rend au moins 2, et
`grep -c "Constantinople hors de la table" jeu/sim/MODELE.md` rend 0.
Contre-épreuve : sur la base, avant le lot, la première commande rend 0 et la
seconde 1.

## Hors périmètre
- Moscou, Tver, Sarai, Kaffa, Sinop, Trébizonde, Damas, Jérusalem : hors de la
  carte, aucune ancre ; aucune extension de la carte.
- Toute ancre de plus pour l'Union de Kalmar, la Livonie ou la Tripolitaine :
  ces cellules restent non couvertes, avec leur lacune.
- Les beyliks libres d'Anatolie comme puissances, les suzerainetés, les
  tributs, le siège de Constantinople, les possessions vénitiennes et
  génoises d'outre-mer (Candie, Corfou, Chio, Péra), les maisons.
- Toute modification de la portée, de la projection, de la règle du plus
  proche, de `charger_table`, de `puissance_par_cellule`,
  `puissances_depuis_monde`, `puissance_de_cellule`,
  `cellules_non_couvertes` (hors mise en commun privée à comportement
  identique), des 24 puissances et 46 ancres existantes, et des tests
  existants hors des quatre lignes.
- Le tick, l'amorçage, `World.charger`, les villes du lot #209, les lieux, le
  service et toute vue : aucune puissance ni lacune n'entre dans le monde
  simulé ni ne s'affiche dans ce lot.
- `jeu/data/world-1400.json`, `province-centres-1400.json`,
  `villes-1400.json`, `sim/aggregation.py`, `sim/model.py` : aucun ne change.
