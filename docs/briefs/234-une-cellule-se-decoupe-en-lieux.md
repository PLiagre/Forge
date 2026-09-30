# Lot #234 — Une cellule se découpe en lieux
Jalon : J3 · Machine : vps · Taille prévue : 260 lignes

## But
Le monde sait dire en combien de lieux se découpe chaque cellule, et quelle
surface tient chacun d'eux — le rang 0, le bourg, et les lieux de rang 1, 2…
autour de lui —, sans perdre ni créer un kilomètre carré. C'est le premier pas
du jalon 3 (CAP.md : « la cellule découpée en lieux » ; preuve : « les lieux
d'une cellule font la cellule (rien ne se perd au découpage) »), celui sur
lequel viendront ensuite le maître de chaque lieu, puis le prélèvement.

## Règle du monde
Une cellule couvre plusieurs milliers de kilomètres carrés : c'est une région,
pas un lieu. Elle se découpe en **lieux** — un bourg et les pays qui
l'entourent —, en nombre tiré de sa surface.

- **Combien.** `n = max(1, floor(surface_km2 / SURFACE_KM2_PAR_LIEU))`. Une
  cellule plus petite que `SURFACE_KM2_PAR_LIEU` est **un seul lieu**, son
  bourg ; aucune cellule n'a zéro lieu.
- **Qui.** Un lieu a pour identité le couple (`cell_id`, `rang`), `rang` allant
  de 0 à `n − 1`. Le **rang 0 est le bourg**. Il n'y a aucun `lieu_id`, aucun
  champ qui serait une seconde clé spatiale : l'identité se dérive de
  `cell_id`, jamais ne se stocke à côté (AGENTS.md, dernière ligne du § 3).
- **Quelle surface, exactement.** Avec `q = floor(surface_km2 / n)` (un entier
  de kilomètres carrés), chaque lieu de rang 1 à `n − 1` reçoit `q`, et le
  bourg reçoit le reste, `surface_km2 − (n − 1) × q`. Le bourg est donc
  toujours le plus grand lieu de sa cellule (reste ≥ `surface/n` ≥ `q`).
  Pourquoi cette forme et pas `surface/n` pour chacun : `(n − 1) × q` est un
  entier, et une surface lue de la carte (au moins 1 km², sous 2⁵³) moins un
  entier plus petit qu'elle se calcule **sans arrondi** en flottant ; la somme
  des surfaces égale donc la surface de la cellule au bit près. Mesuré le
  29 septembre 2026 sur `World.charger(0)` : ce découpage est exact sur les
  596 cellules ; le partage naïf `surface/n` ne l'est pas sur 307 d'entre
  elles. C'est la contre-épreuve de SC2.
- **Refus.** Une surface absente (`None`, ou une cellule absente de la table
  des surfaces), booléenne, textuelle, non finie, nulle ou négative est
  **refusée** par `LieuxInvalides`, dont le message nomme le `cell_id` : elle
  n'est jamais devinée, remplacée par une moyenne ni écartée en silence. Une
  valeur de `SURFACE_KM2_PAR_LIEU` non finie ou inférieure à 1 est refusée de
  même (en dessous de 1 km², `q` pourrait valoir zéro et créer un lieu vide).

Cela découle de `jeu/sim/MODELE.md` :

- « La province dérivée et ses centres », sous-section « Ce que l'agrégation
  ne fait pas — et le motif que toute vue recopie » : le découpage est une
  **vue dérivée**, pure, hors de `sim.model`, qui ne pose rien sur `Cell`,
  refuse de deviner, se recalcule à chaque consultation, et que **le tick ne
  lit pas** ;
- « Ce qu'est une ville, à l'échelle d'une cellule » : le bourg y est la part
  des habitants qui ne cultive pas, et `bourg_id` y est interdit. Le lieu de
  rang 0 est le bourg de ce texte, vu par sa surface ; ce lot ne lui donne
  aucun habitant, et la distribution à l'intérieur de la cellule **reste
  gratuite** (ce lot découpe la surface, pas les stocks ni la population) ;
- « Le moteur sans état caché » : la constante se lit par son module
  (`_constantes.SURFACE_KM2_PAR_LIEU`), à chaque appel, jamais importée par
  valeur.

**Niveau de fidélité.** Les surfaces des cellules viennent de la carte figée,
inchangée. Le nombre de lieux et leurs surfaces sont de **niveau 2** :
plausibles, jamais sourcés ; une anomalie n'est pas un défaut.
`SURFACE_KM2_PAR_LIEU = 1000.0` est l'ordre de grandeur d'un pays autour de
son bourg de marché, qu'on rejoint et quitte dans la journée. Mesuré le
29 septembre 2026 sur la carte figée : 6 619 lieux, 9 par cellule en
médiane, 37 au plus ; 194 cellules, surtout des îles, sont un seul lieu. Ce
nombre ne coûte rien au tick aujourd'hui, puisqu'il ne lit pas la vue ; il se
mesurera contre le budget du tick au lot qui la lui fera lire (VISION.md,
« combien de lieux dans une cellule »). **Niveau 3, pas simulé** : la forme,
la position et les frontières des lieux, leurs noms, leur relief propre.

### Ce que le codeur écrit

**1. `jeu/sim/constants.py`** — une constante `SURFACE_KM2_PAR_LIEU = 1000.0`,
sous un commentaire de deux ou trois lignes qui dit ce qu'elle gouverne, son
niveau 2 et ce qu'elle ne prétend pas. Rien d'autre ne change dans ce fichier.

**2. `jeu/sim/lieux.py`** — nouveau module, sur le motif de `sim/puissances.py`
(`import sim.constants as _constantes`) :

- `LieuxInvalides(ValueError)` ;
- `Lieu`, dataclass figée héritant de `_NoBadSpatialField`, avec **exactement**
  trois champs : `cell_id: int`, `rang: int`, `surface_km2: float` ; une
  propriété `est_bourg` (`rang == 0`) ;
- `lieux_de_cellule(cell_id, surface_km2) -> tuple` : pure ; relit
  `_constantes.SURFACE_KM2_PAR_LIEU` à chaque appel et la refuse si elle est
  invalide ; refuse la surface comme dit plus haut ; rend les `n` lieux triés
  par rang ;
- `lieux_par_cellule(surfaces) -> dict` : pure ; `surfaces` est un
  dictionnaire `cell_id → surface_km2` ; rend `cell_id → tuple de Lieu` pour
  chaque clé, et refuse la première surface invalide en nommant sa cellule ;
- `lieux_depuis_monde(world) -> dict` : adaptateur en lecture seule ; prend
  pour chaque cellule de `world.cells` son `area_km2`
  (`getattr(cellule, "area_km2", None)`, absente = `None`, donc refusée) et
  rend la vue. N'écrit rien, ni sur les cellules, ni sur disque.

Aucune fonction de consultation de plus. Aucun littéral numérique autre que 0,
1 et −1 dans un corps de fonction (`sim/tests/test_no_hardcoded.py` inspecte
tout module neuf de `sim/`). Les ordres de sortie suivent `cell_id` puis
`rang` croissants.

**3. `jeu/sim/tests/test_lieux.py`** — les cas des conditions ci-dessous.

**4. `jeu/sim/MODELE.md`** — une section « ## Les lieux d'une cellule, vue
dérivée », placée juste après « Les puissances de 1400, vue dérivée » : la
règle du nombre et la constante nommée avec sa valeur, l'identité
(`cell_id`, `rang`) et « le rang 0 est le bourg », la règle des surfaces et
pourquoi elle est exacte, les refus, le niveau 2, le lien avec le bourg de
« Ce qu'est une ville » (même bourg, vu par sa surface ; la distribution dans
la cellule reste gratuite), et « le tick ne la lit pas ». Aucun compte mesuré
n'y est recopié. Dans « En une page », le paragraphe qui dit que la province,
la pluie et la puissance ne se stockent pas nomme aussi les lieux ; dans « Ce
que le moteur ne fait pas encore », la puce « descendre sous la cellule » dit
que la cellule se découpe désormais en lieux par sa surface, mais que la
population, les stocks et le tick restent à l'échelle de la cellule.

## Périmètre
jeu/sim/constants.py
jeu/sim/lieux.py
jeu/sim/tests/test_lieux.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par
`python3 -m pytest jeu/sim/tests/test_lieux.py -q -s -k <nom>` ; chaque test
imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` n'est
écrit en dur dans un test sur le vrai monde : les cellules se choisissent par
leur surface, lue du monde.

**SC1 — le nombre de lieux suit la surface** (`-k nombre`). Sur
`lieux_depuis_monde(World.charger(0))` : les clés sont exactement
`set(world.cells)` ; pour chaque cellule, `len(lieux) == max(1,
floor(area_km2 / SURFACE_KM2_PAR_LIEU))` (constante lue du module, pas
recopiée), et au moins 1 ; `lieux_total` (imprimé) > `len(world.cells)` ; au
moins une cellule a un seul lieu et au moins une en a plusieurs (sinon le test
échoue). Contre-épreuve, dans le même test : avec `monkeypatch.setattr` qui
double `sim.constants.SURFACE_KM2_PAR_LIEU`, `lieux_total` baisse
strictement — la vue relit sa constante, elle ne l'a pas figée.

**SC2 — les lieux font la cellule, au bit près** (`-k surface`). Sur le même
monde, pour chaque cellule : `sum(Fraction(l.surface_km2) for l in lieux) ==
Fraction(area_km2)` et `sum(l.surface_km2 for l in lieux) == area_km2` ;
chaque surface est strictement positive ; les lieux de rang ≥ 1 ont tous la
même surface, entière ; le bourg a la plus grande. Compteur
`cellules_exactes` = `len(world.cells)`. Contre-épreuve, dans le même test :
le partage naïf `[area_km2 / n] * n`, évalué avec la même comparaison en
`Fraction`, échoue sur au moins une cellule du monde (compteur imprimé, > 0) —
la preuve de l'exactitude peut rougir.

**SC3 — l'identité est (`cell_id`, `rang`), le rang 0 est le bourg**
(`-k identite`). Les champs de `Lieu` (`dataclasses.fields`) sont exactement
`{"cell_id", "rang", "surface_km2"}` ; `Lieu` est figée et hérite de
`_NoBadSpatialField`. Sur le vrai monde : les couples (`cell_id`, `rang`) sont
tous distincts, leur nombre égale `lieux_total` ; dans chaque cellule, les
rangs valent exactement `0 … n − 1` ; exactement un lieu par cellule a
`est_bourg`, celui de rang 0 ; chaque lieu porte le `cell_id` de sa clé.
Contre-épreuve : une dataclass de test identique à `Lieu` plus un champ
`lieu_id` ne passe pas le même contrôle d'ensemble de champs (le contrôle
est une fonction du test, appliquée aux deux).

**SC4 — une surface absente est refusée, jamais devinée** (`-k refus`).
`lieux_par_cellule` sur `{7: s}` lève `LieuxInvalides`, dont le message
contient `7`, pour chaque `s` de la liste : `None`, `True`, `"1200"`,
`float("nan")`, `float("inf")`, `0`, `-5.0` ; compteur `refus_observés` égal
à la longueur de la liste (> 0). `lieux_de_cellule(7, 1200.0)` avec
`SURFACE_KM2_PAR_LIEU` patchée à `0.5`, puis à `float("nan")`, lève
`LieuxInvalides`. Sur une copie profonde du vrai monde dont la cellule la plus
petite a `area_km2 = None`, `lieux_depuis_monde` lève `LieuxInvalides` qui
nomme son `cell_id`. Contre-épreuve, dans le même test : `{7: 1200.0}`,
`{7: 1}` (entier) et `{7: 0.3}` passent (un, un et un lieu), le refus ne vise
que l'invalide ; et une cellule de 0,3 km² donne un bourg de 0,3 km², pas
zéro lieu.

**SC5 — une vue pure que le tick ne lit pas** (`-k pure`). Deux appels de
`lieux_depuis_monde` rendent des vues égales ;
`json.dumps(world.to_dict(), sort_keys=True)` est identique avant et après ;
aucune `Cell` n'a gagné d'attribut (`vars()` comparés). Puis, depuis la
racine :
`grep -rlE "sim\.lieux|from sim import lieux" jeu/sim --include=*.py | grep -v -e "sim/lieux.py" -e "sim/tests/"`
ne rend rien. Contre-épreuve : la même commande sans le second filtre rend
`jeu/sim/tests/test_lieux.py` — le détecteur voit un import quand il y en a
un.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert, sans
qu'aucun test existant ne soit modifié : `test_no_hardcoded.py` inspecte
`lieux.py`, `test_write_coverage.py` trouve un lecteur à
`SURFACE_KM2_PAR_LIEU`, et `test_determinisme.py`, `test_monde.py`,
`test_province.py`, `test_puissances.py` restent tels quels. Contre-épreuve :
un littéral `1000` glissé dans un corps de fonction de `lieux.py` rend
`test_no_hardcoded` rouge.

**SC7 — le modèle le dit.** `grep -n "^## Les lieux d'une cellule, vue
dérivée" jeu/sim/MODELE.md` rend une ligne, et la section contient
`SURFACE_KM2_PAR_LIEU`, « rang 0 », « bourg » et « le tick ne la lit pas ».
Et `awk '/^## En une page/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep
-n -i "lieux"` rend au moins une ligne. Contre-épreuve : sur la base, avant
le lot, la première commande ne rend rien et la seconde non plus (le mot
« lieux » n'apparaît pas dans « En une page »).

## Hors périmètre
- Le tick, l'amorçage, `World.lire_carte`, le service et le snapshot ne lisent
  pas la vue : aucun lieu n'entre dans le monde simulé dans ce lot.
- La population, les stocks, la production par lieu ; la répartition du bourg
  (`RepartitionBourg` de `sim/aggregation.py`) ne change pas et n'est pas
  branchée sur le lieu de rang 0.
- Le maître d'un lieu, son suzerain, le prélèvement, le transport à
  l'intérieur de la cellule : les lots suivants du jalon 3.
- La forme, la position, les frontières et les noms des lieux ; tout lieu
  historique nommé (niveau 1) ; toute ville comme lieu (lot #209).
- La mesure du nombre de lieux contre le budget du tick : au lot qui fera
  lire la vue au tick.
- `jeu/data/world-1400.json`, `sim/model.py`, `sim/world.py`,
  `sim/engine.py`, `sim/aggregation.py` : aucun ne change.
- L'affichage : aucune vue (tableau, chronique, relief, Unity) ne montre les
  lieux dans ce lot.
