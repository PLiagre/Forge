# Lot #206 — Les puissances de 1400 : l'Italie, le Nord et le Centre
Jalon : J2 · Machine : vps · Taille prévue : 190 lignes

## But
Le monde sait dire qu'au 1er janvier 1400 la cellule de Venise relève de Venise, celle de Rome de la Papauté, celle de Buda de la Hongrie, celle de Copenhague de l'Union de Kalmar : la table des puissances passe de l'Ouest à l'Italie, au Nord et au Centre, pour la carte des royaumes et la preuve « des points connus appartiennent à la bonne puissance » (CAP.md, jalon 2).

## Règle du monde
Aucune règle neuve. La table `data/puissances-1400.json` gagne des lignes, et la
vue existante les lit telle quelle : une cellule relève de la puissance qui
tient l'ancre la plus proche de son centroïde, dans la **portée** de 4,0 degrés
projetés, sinon elle est **non couverte**. Cela découle de `jeu/sim/MODELE.md`,
section « Les puissances de 1400, vue dérivée » (et « La province dérivée et
ses centres » pour la règle du plus proche et son départage). La portée, la
projection, le chargeur et la vue ne changent pas ; **le tick ne lit pas la
table**.

**Niveaux de fidélité.**

- **Niveau 1** (sources publiques : Wikipédia, atlas, encyclopédies) :
  l'existence de chaque puissance au 1er janvier 1400, sa nature, sa religion,
  et l'appartenance de chaque ancre à sa puissance ce jour-là.
- **Niveau 2** (plausible, une anomalie n'est pas un défaut) : la frontière du
  plus proche. Naples couvre une partie de la rive est de l'Adriatique, Savoie
  des cellules de Provence : c'est accepté, pas corrigé.
- **Niveau 3, pas simulé** : les suzerainetés — Milan et la Savoie sont des
  fiefs d'Empire, Gênes a donné sa seigneurie au roi de France en 1396, la
  Lituanie est unie à la Pologne par la personne du roi — et le Grand Schisme
  (la Papauté est celle de Rome, Boniface IX).

**Une nature de plus.** Milan (duché depuis 1395) et la Savoie (comté) ne sont
ni royaume, ni république, ni Église, ni ordre. `NATURES` gagne une seule
valeur, **`principauté`** : une puissance tenue par un duc, un comte ou un
prince. Rien d'autre ne s'élargit : `duché` et `comté` restent refusés, les
religions ne changent pas.

### Ce que le codeur écrit

**1. `jeu/data/puissances-1400.json`** : sa `description` dit « l'Ouest,
l'Italie, le Nord et le Centre » ; rien d'autre ne change en tête du fichier
(`projection`, `portee` identiques). Les 12 puissances et les 23 ancres
existantes restent **identiques, mêmes `id`**. On ajoute, une ligne par entrée :

| id | nom (exact, le test le lit) | nature | ancres (lat ; lon) |
|---|---|---|---|
| 13 | `Venise` | république | Venise (45,44 ; 12,33) |
| 14 | `Milan` | principauté | Milan (45,46 ; 9,19) |
| 15 | `Florence` | république | Florence (43,77 ; 11,26), Arezzo (43,46 ; 11,88) |
| 16 | `Gênes` | république | Gênes (44,41 ; 8,93) |
| 17 | `Papauté` | Église | Rome (41,90 ; 12,50) |
| 18 | `Naples` | royaume | Naples (40,85 ; 14,27), Bari (41,12 ; 16,87) |
| 19 | `Sicile` | royaume | Palerme (38,12 ; 13,36), Catane (37,50 ; 15,09) |
| 20 | `Savoie` | principauté | Chambéry (45,57 ; 5,92), Nice (43,70 ; 7,27) |
| 21 | `Union de Kalmar` | royaume | Copenhague (55,68 ; 12,57), Kalmar (56,66 ; 16,36), Bergen (60,39 ; 5,32) |
| 22 | `Ordre teutonique` | ordre | Marienbourg (54,04 ; 19,03), Königsberg (54,71 ; 20,51) |
| 23 | `Pologne-Lituanie` | royaume | Cracovie (50,06 ; 19,94), Vilnius (54,69 ; 25,28), Lviv (49,84 ; 24,03) |
| 24 | `Hongrie` | royaume | Buda (47,50 ; 19,04), Zagreb (45,81 ; 15,98), Kolozsvár (46,77 ; 23,59) |

Toutes `catholique`. Ancres numérotées de 24 à 46 dans l'ordre du tableau.
Chaque `source` nomme l'article public qui atteste l'appartenance en 1400 (par
exemple « Wikipédia, article Nice : dédition de Nice à la Savoie en 1388 » ;
Arezzo, florentine depuis 1384 ; Rome, reprise en main par Boniface IX en
1398 ; Königsberg, à l'Ordre depuis 1255). Le codeur vérifie chaque ligne
contre sa source ; une ancre qu'il ne peut pas sourcer ne s'écrit pas, et il
le dit dans la PR.

**Pièges, à ne pas ancrer** (tous mesurés ou vérifiés par le chef) :
**Vérone** (milanaise en 1400, mais une ancre de Milan à Vérone fait tomber la
cellule de Venise sous Milan : mesuré), **Pise** et **Sienne** (vendue et
soumise à Milan en 1399, pas florentines), **Pérouse** (se donne à Milan
courant 1400, date incertaine), **Bologne** (disputée), **Padoue** (aux
Carrare, vénitienne en 1405 seulement), **Turin** (à la branche de
Savoie-Achaïe), **Visby** (Gotland, tenue par l'Ordre de 1398 à 1408, plus
petite qu'une cellule), **Candie** et **Corfou** (vénitiennes, mais plus
petites qu'une cellule : mesuré, Corfou donnerait à Venise une partie des
Balkans).

**2. `jeu/sim/puissances.py`** : `NATURES` gagne `"principauté"`, et la
docstring du module ne dit plus seulement « occidentales ». Rien d'autre.

**3. `jeu/sim/tests/test_puissances.py`** : les nouveaux cas s'**ajoutent**
dans de nouvelles fonctions de test. **Une seule réécriture est permise**,
décidée par le propriétaire sur l'issue #206 (réponse « Oui » à la question
A) : dans `test_lecture_de_toutes_les_lignes`, les deux lignes des plafonds
deviennent

```python
    assert 24 <= puissances_lues == len(brut["puissances"]) <= 40
    assert 46 <= ancres_lues == len(brut["ancres"]) <= 80
```

Le plancher est le compte de ce lot (retirer une ligne fait rougir), le
plafond laisse la place aux puissances de l'Orient. L'égalité avec le fichier
relu en brut, `puissances_sans_ancre == 0` et la relecture sans altération
restent tels quels. Aucune autre ligne existante ne change : ni `CAS_REFUS`,
ni `_alterer`, ni `_connues`, ni `_compter_ancrage`, ni les tests du lot #220.

**4. `jeu/sim/MODELE.md`**, section « Les puissances de 1400, vue dérivée »
seulement : la table couvre l'Ouest, l'Italie, le Nord et le Centre ; la
nature `principauté` et pourquoi ; la couverture mesurée sur la carte figée
(406 cellules couvertes, 190 non couvertes, à remesurer par le codeur) ; la
phrase sur Le Caire et Constantinople reste vraie (toujours non couvertes,
elles attendent les puissances de l'Orient).

## Périmètre
jeu/data/puissances-1400.json
jeu/sim/puissances.py
jeu/sim/tests/test_puissances.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par
`python3 -m pytest jeu/sim/tests/test_puissances.py -q -s -k <nom>` ; chaque
test imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` ni
aucun `id` de puissance n'est écrit dans un test : les puissances se trouvent
par leur `nom`, les cellules par des points nommés dans le test (degrés, niveau
1, pas lus de la table), qui cherchent leur centroïde le plus proche par
`_cellule_la_plus_proche` (déjà dans le fichier). Prouver chaque contre-épreuve
rouge avant de la garder.

**SC1 — toute la table se lit** (`-k lecture`). Le test existant, avec ses
seuls plafonds remplacés, est vert. Un nouveau test vérifie que les 12 noms
ajoutés sont tous lus et que chacun a au moins une ancre (compteur
`ajouts_lus`, égal à 12). Contre-épreuve : la table réécrite sans la ligne de
la Hongrie ni ses ancres fait échouer la condition du test existant (fonction
du test qui en reprend les deux bornes, appliquée au document altéré) et rend
`ajouts_lus == 11`.

**SC2 — les refus tiennent, et `principauté` n'ouvre rien d'autre**
(`-k refus`). Les 17 cas de `CAS_REFUS` restent verts, inchangés. Un nouveau
test paramétré ajoute, une altération à la fois dans `tmp_path` :
toutes les ancres de Gênes retirées (message : « puissance <id de Gênes> » et
`ancres`) ; nature de Milan à `"duché"` ; nature de la Savoie à `"comté"` ;
religion de la Hongrie à `"protestante"`. Chacun lève `PuissanceInvalide` en
nommant la ligne et le champ ; `refus_observés` égale la longueur de la liste
(> 0). Contre-épreuve : la vraie table, où Milan est `principauté`, se charge.

**SC3 — les puissances ajoutées sont justes** (`-k connues`). Une nouvelle
fonction du test vérifie sur une table chargée : les 12 noms exacts présents,
tous `catholique` ; Venise, Florence et Gênes `république` ; Papauté `Église` ;
Ordre teutonique `ordre` ; Milan et Savoie `principauté` ; les cinq autres
`royaume`. Vraie sur la vraie table ; `_connues` du lot #219 y reste vraie.
Contre-épreuves : fausse sur la table où la Papauté est `royaume`, puis sur
celle où Milan est retirée avec ses ancres.

**SC4 — Venise sous Venise** (`-k geographie`). Sur
`puissances_depuis_monde(World.charger(0))`, les cellules de ces douze points
sont **distinctes** (sinon échec) et relèvent chacune de la puissance nommée :
Venise 45,44 N 12,33 E → `Venise` ; Milan 45,46 N 9,19 E → `Milan` ; Florence
43,77 N 11,26 E → `Florence` ; Gênes 44,41 N 8,93 E → `Gênes` ; Rome 41,90 N
12,50 E → `Papauté` ; Naples 40,85 N 14,27 E → `Naples` ; Palerme 38,12 N
13,36 E → `Sicile` ; Chambéry 45,57 N 5,92 E → `Savoie` ; Copenhague 55,68 N
12,57 E → `Union de Kalmar` ; Marienbourg 54,04 N 19,03 E → `Ordre
teutonique` ; Cracovie 50,06 N 19,94 E → `Pologne-Lituanie` ; Buda 47,50 N
19,04 E → `Hongrie`. Le test existant (Paris, Londres, Le Caire,
Constantinople) reste vert, inchangé : Le Caire et Constantinople toujours non
couverts. Contre-épreuves, dans le même test (`dataclasses.replace`, en
mémoire) : les ancres de Venise et de Milan échangent leur champ `puissance`
→ Venise relève de Milan et Milan de Venise ; une ancre de Milan ajoutée à
Vérone (45,44 N 10,99 E) → la cellule de Venise relève de Milan (le piège
mesuré par le chef).

**SC5 — chaque puissance couvre au moins une cellule** (`-k compte`). Le test
existant du lot #220 est vert sur la table étendue, inchangé : il exige que les
24 puissances couvrent chacune au moins une cellule, en nommant celle qui n'en
couvre pas. Le nouveau test de SC4 imprime `couvertes` et `non_couvertes`
(somme égale à `len(world.cells)`). Contre-épreuve : la table où l'ancre de
Venise est retirée (en mémoire) ne donne plus aucune cellule à Venise.

**SC6 — pas d'ancre sur un piège** (`-k ancrage`). Le test existant (Calais,
Avignon, hors carte) reste vert, inchangé. Un nouveau test écrit ses propres
points : Vérone, Pise, Sienne, Pérouse, Bologne, Padoue, Turin, Visby, Candie,
Corfou ; aucune ancre à moins de 0,2° en latitude **et** en longitude de l'un
d'eux (`ancres_sur_piege == 0`). Contre-épreuve : une ancre de Florence ajoutée
à Pise compte 1.

**SC7 — une seule réécriture, et rien d'autre ne bouge.**
`git diff origin/master -- jeu/sim/tests/test_puissances.py | grep -c '^-[^-]'`
rend **2**, et ces deux lignes retirées sont les deux plafonds `<= 16` et
`<= 30`. Contre-épreuve : toute autre ligne existante touchée fait monter ce
compte. Puis `python3 -m pytest jeu -q` est vert ; `test_no_hardcoded.py`
inspecte toujours `puissances.py` (un littéral `4` glissé dans un corps de
fonction le fait rougir).

**SC8 — le modèle le dit.**
`awk '/^## Les puissances de 1400, vue dérivée/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep -c -e principauté -e Venise`
rend au moins 2. Contre-épreuve : sur la base, avant le lot, la même commande
rend 0.

## Hors périmètre
- L'Orient et le Sud : Byzance, Ottomans, Mamelouks, Serbie, Valachie,
  Moscovie, Horde d'Or, Hafsides, Mérinides — Le Caire et Constantinople
  restent non couverts.
- Toute modification de la portée, de la projection, de la règle du plus
  proche, du chargeur hors `NATURES`, des 12 puissances et 23 ancres
  existantes, et des tests existants hors des deux plafonds.
- Les petites seigneuries d'Italie (Mantoue, Ferrare, Padoue), les villes
  libres, les possessions d'outre-mer plus petites qu'une cellule, les
  suzerainetés, les maisons, le Grand Schisme.
- Le tick, l'amorçage, `World.charger`, les villes du lot #209, les lieux, le
  service et toute vue : aucune puissance n'entre dans le monde simulé ni ne
  s'affiche dans ce lot.
- `jeu/data/world-1400.json`, `province-centres-1400.json`,
  `villes-1400.json`, `sim/aggregation.py`, `sim/model.py` : aucun ne change.
