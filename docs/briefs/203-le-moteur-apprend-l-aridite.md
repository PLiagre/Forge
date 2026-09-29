# Lot #203 — Le moteur apprend l'aridité
Jalon : J2 · Machine : vps · Taille prévue : 290 lignes

## But
Le monde de 1400 cesse de cultiver le désert : la production agricole de chaque
cellule dépend de la pluie qu'elle reçoit, et comme la population de départ se
dérive de la production, le désert occidental égyptien s'amorce vide alors
qu'il était jusqu'ici plus peuplé que la médiane (CAP.md, jalon 2 : « le moteur
apprend l'aridité » ; la preuve du jalon exige qu'« un amorçage sans aridité »
échoue).

## Règle du monde
Un champ sans eau ne donne rien. Sous une certaine pluie annuelle, la culture
pluviale est impossible : la terre ne nourrit plus que ce que le parcours des
troupeaux en tire. Au-dessus d'une autre, l'eau ne manque plus aux champs et
la pluie ne limite plus rien. Entre les deux, le rendement monte avec la pluie.
C'est une **cause** posée dans la production (l'eau manque aux champs), pas un
« si désert alors −x % » sur la population : la population suit d'elle-même,
parce qu'elle se dérive de la production.

Cela découle de trois sections de `jeu/sim/MODELE.md` :

- « Le rendement agricole et sa variabilité » : il n'y a **qu'une formule de
  production** dans `sim/`, et le plafond de survie comme l'amorçage la lisent ;
  le facteur d'eau y entre comme le relief et la saison y sont entrés, par un
  facteur lu dans la carte, cellule par cellule, refusé s'il manque ;
- « Population initiale par cellule » : la population amorcée est une part de
  `population_soutenable_de`, elle-même dérivée de cette formule. **Aucune
  ligne de l'amorçage ne change** : elle suit ;
- « La pluie de 1400, vue dérivée » : la pluie d'une cellule est celle du
  relevé le plus proche. Le tick ne consulte toujours pas la vue : la carte la
  reçoit **à sa lecture**, et le moteur lit la carte, comme pour le relief.

**Niveaux de fidélité.**

- La pluie reste de **niveau 1** (les relevés du lot #202, sources citées,
  climat actuel déclaré comme approximation de 1400). Ce lot ne touche pas la
  table.
- La courbe du facteur d'eau est de **niveau 2** : plausible, jamais sourcée.
  Trois constantes, fixées ici avant tout code, et non réglées après mesure :

| constante | valeur | sens |
|---|---|---|
| `PLUIE_SANS_CULTURE_MM` | 250.0 | en dessous (et à égalité), pas de culture pluviale : c'est l'ordre de grandeur usuel de la limite d'un désert |
| `PLUIE_PLEINE_CULTURE_MM` | 400.0 | au-dessus (et à égalité), l'eau ne limite plus : ordre de grandeur de la limite de la céréaliculture pluviale sûre |
| `FACTEUR_EAU_PLANCHER` | 0.05 | ce que la terre sèche nourrit sans culture : le parcours des troupeaux. Strictement positif : un désert de 1400 n'est pas inhabité |

  `facteur_eau(mm)` vaut `FACTEUR_EAU_PLANCHER` pour `mm ≤ PLUIE_SANS_CULTURE_MM`,
  **exactement `1.0`** pour `mm ≥ PLUIE_PLEINE_CULTURE_MM`, et monte en ligne
  droite du plancher à 1 entre les deux. La courbe ne punit pas l'excès d'eau
  (monotone, jamais au-dessus de 1) : la plaine mouillée reste la référence du
  rendement nominal, comme la plaine l'est pour le relief.

**Ce que le lot rend faux, à déclarer dans `MODELE.md`** : la pluie n'est pas
l'eau (déjà écrit par le lot #202). Le delta et la vallée du Nil reçoivent la
pluie du Caire ou d'Alexandrie, sous `PLUIE_SANS_CULTURE_MM` : ce lot **les
vide aussi**. C'est une erreur de niveau 1, connue et datée, que seul un lot du
fleuve (la crue comme source d'eau) réparera. Le lot la dit ; il ne la masque
ni par un plancher relevé, ni par une exception pour l'Égypte.

### Ce que le codeur écrit

**1. `jeu/sim/constants.py`** — les trois constantes ci-dessus, commentées
« niveau 2 », et `facteur_eau(pluie_mm_par_an: float) -> float`, qui **relit
les trois constantes à chaque appel** (motif de `facteurs_production_par_relief`,
voir `MODELE.md`, « Le monde d'épreuve, et pourquoi certaines constantes se
cachent » : le monde d'épreuve n'a pas de pluie, ces constantes ne se lisent
donc jamais par leur nom dans `engine.py`). Aucun littéral autre que 0, 1, −1
dans le corps. `SNAPSHOT_SCHEMA_VERSION` passe de `"v0a-4"` à `"v0a-5"` : le
document du snapshot gagne une couche.

**2. `jeu/sim/world.py`** — `World.lire_carte()` rend la carte figée **et la
pluie que lui donnent les relevés** : chaque enregistrement de cellule reçoit
la clé `"pluie_mm_par_an"` (un nombre, les millimètres du relevé le plus
proche ; aucun identifiant de relevé n'est posé), calculée par
`pluie_par_cellule(charger_positions(), charger_releves(),
charger_latitude_moyenne_pluie())` de `sim/pluie.py`, importé sans être
modifié. Une cellule de la carte absente de la vue lève `PositionCelluleInconnue`
en la nommant : pas de pluie par défaut. Le fichier sur le disque ne change
pas ; seule sa lecture en mémoire porte la pluie. Rien n'est posé sur `Cell`.
`World.charger(carte_doc=…)` n'ajoute rien : il lit ce que le document porte,
ce qui permet à la sonde d'altérer la pluie **avant** l'amorçage. Le docstring
de `lire_carte` dit ce qu'elle rend désormais.

**3. `jeu/sim/engine.py`** — `PluieInvalideError(ValueError)`, et
`_facteur_eau_pour_cellule(cell, carte)` sur le modèle de
`_facteur_relief_pour_cellule` : lit `carte[cell_id]["pluie_mm_par_an"]`,
**refuse** en nommant le `cell_id` un enregistrement absent, une clé absente
ou `None`, un booléen, une valeur non numérique, non finie ou négative ; `0.0`
est accepté (une mesure) ; rend `_constantes.facteur_eau(mm)`.
`production_du_tick_kg` multiplie son produit par ce facteur, **après** le
relief et la part agricole et avant la saison. Rien d'autre : le plafond
(`population_soutenable_de`, `production_moyenne_kg_par_tick`) et l'amorçage
suivent par la formule unique. Les docstrings de `production_du_tick_kg` et de
`population_soutenable_de` nomment l'eau.

**4. `jeu/sim/snapshot_export.py`** — `"pluie"` rejoint `_COUCHES` ; `_alterer`
remplace, pour cette couche, `pluie_mm_par_an` de chaque enregistrement par
`_SONDE_PLUIE_MM = 0.0` (constante de module, à côté des trois autres). Le
drapeau `utilisee_par_le_moteur` reste une **mesure** : aucune valeur écrite à
la main. Le docstring du module cesse de dire que le tick ne se sert d'aucune
couche.

**5. Deux tests existants, et eux seuls, évoluent — sans s'assouplir.** Ils
figeaient un « pas encore » que ce lot est chargé de lever ; chacun reste une
égalité exacte, et rougit dans plus de cas qu'avant :

- `jeu/sim/tests/test_monde.py`, `test_schema_ferme_et_couches` : l'ensemble
  attendu devient `{"relief", "climat", "gisements", "pluie"}`. Une ligne. Le
  schéma reste fermé : une couche en trop ou en moins rougit toujours.
- `jeu/sim/tests/test_pluie.py`, `test_pure_et_non_lue_par_le_tick` : la
  pureté, la stabilité, `avant == apres`, `modules_parcourus > 0` et la
  contre-épreuve synthétique restent **mot pour mot**. Seule l'assertion
  `usages_interdits == []` devient : l'ensemble des modules de `sim/` (hors
  `pluie.py`) qui lisent la vue est **exactement** `{"world.py"}`. Le tick
  (`engine.py`) ne la lit toujours pas, et un second lecteur (moteur, snapshot,
  service) rougit ; un monde qui cesserait de lire la pluie rougit aussi, ce
  que l'ancienne assertion ne voyait pas. Le test imprime les lecteurs trouvés.

Aucun autre test existant ne change. Fait mesuré avant le lot, à connaître :
la première cellule de chaque classe de relief dans la carte (celles de
`test_production_kg_modulée_par_le_relief`) reçoit plus de
`PLUIE_PLEINE_CULTURE_MM`, donc un facteur d'eau d'exactement 1 ; la cellule
de plus petite amplitude du jour (celle de
`test_le_nord_a_une_saison_plus_violente_que_le_sud`) est au plancher, qui
n'est jamais nul. Si l'un de ces tests rougit, c'est le code qui a tort.

**6. `jeu/sim/tests/test_aridite.py`** — neuf, les cas du lot (voir
Conditions de succès). Chaque test imprime ses compteurs ; un échantillon vide
échoue.

**7. `jeu/sim/MODELE.md`** — réécrit, dans le même mouvement :

- « En une page », étape 4 : la production est aussi multipliée par le facteur
  d'eau de la pluie de la cellule ; le paragraphe de la pluie dit que la pluie
  n'est pas stockée sur `Cell`, qu'elle entre dans la carte à sa lecture, et
  que le tick la lit là — jamais dans la vue ;
- « Ce que le moteur ne fait pas encore » : la carte, telle que le monde la
  lit, porte quatre couches, et le tick les joue toutes ; la sonde de la pluie
  la **remplace** par zéro au lieu de la multiplier ;
- « Population initiale par cellule » : la formule morte
  (`INITIAL_POPULATION_PER_KM2`, « le monde démarre plat ») est remplacée par
  la vraie — `population = max(0, int(population_soutenable_de(cellule) ×
  PART_SOUTENABLE_AMORCEE × variation))` — et ce qu'elle entraîne : la
  population de départ suit le relief, la saison, la part minière et l'eau ;
  le désert s'amorce presque vide ;
- « Le rendement agricole et sa variabilité » : la formule gagne
  `× facteur_eau(pluie_mm_par_an de la cellule)`, la table des trois
  constantes et leur niveau, le refus `PluieInvalideError`, le plancher
  strictement positif et sa raison ; « L'équilibre que ces valeurs
  produisent » cesse de parler de 10 hab/km² ;
- « La pluie de 1400, vue dérivée » : le Nil vidé par ce lot, déclaré ; la
  phrase « le tick ne la lit pas » reste vraie et reste écrite (le tick lit la
  carte, pas la vue).

Aucun nombre mesuré n'y est recopié : un compteur se cite par son nom.

## Périmètre
jeu/sim/constants.py
jeu/sim/engine.py
jeu/sim/world.py
jeu/sim/snapshot_export.py
jeu/sim/tests/test_aridite.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_pluie.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent par `python3 -m pytest jeu/sim/tests/test_aridite.py -q -k <nom>`
depuis la racine, sauf mention. Le désert occidental est la cellule dont le
centroïde est le plus proche de (30,9° N, 28,5° E), la Flandre celle du plus
proche de (51,0° N, 3,7° E), par la projection de la table de pluie (même
calcul que `test_pluie.py`, SC4) ; ces points sont écrits dans le test, les
cellules en sont dérivées.

**SC1 — la courbe** (`-k courbe`). Sur une grille de pluies dérivée des
constantes (0, le seuil bas, le milieu, le seuil haut, dix fois le seuil
haut) : plancher à 0 et au seuil bas, exactement `1.0` au seuil haut et
au-delà, strictement entre les deux au milieu, jamais décroissante, jamais
au-dessus de 1, toujours strictement positive. Contre-épreuve : doubler
`PLUIE_PLEINE_CULTURE_MM` en mémoire (monkeypatch du module) change la valeur
au milieu — la fonction relit ses constantes.

**SC2 — la carte lue porte la pluie de la vue** (`-k carte`). Pour chaque
cellule de `World.lire_carte()`, `pluie_mm_par_an` égale
`pluie_de_cellule(cell_id, pluie_depuis_monde(World.charger(0)))` :
`cellules_conformes == len(world.cells)` (dénominateur lu du monde), `> 0`.
Le fichier `data/world-1400.json` sur le disque ne contient aucune clé
`pluie_mm_par_an`. Contre-épreuve : la même comparaison contre la vue
calculée sur les relevés **inversés par rang** (le motif de `test_pluie.py`,
SC4) donne au moins une cellule non conforme.

**SC3 — le moteur refuse une pluie absente** (`-k refus`). Sur une copie de
`World.lire_carte()` dont **un** enregistrement est altéré à la fois — clé
retirée, `None`, `True`, `"sec"`, `NaN`, `-1.0` — `World.charger(0,
carte_doc=…)` lève `PluieInvalideError` et le message contient ce `cell_id`.
Contre-épreuve : la même cellule à `0.0` s'amorce sans erreur, et sa
population soutenable vaut celle du plancher.

**SC4 — le désert se vide, la terre mouillée ne bouge pas** (`-k desert`).
Sur `World.charger(0)`, densité = population / surface, médiane dérivée du
monde : densité du désert occidental **strictement sous** la médiane, densité
de la Flandre au-dessus. Contre-épreuve, exigée par la demande : avec
`sim.constants.facteur_eau` remplacé en mémoire par une fonction qui rend
toujours `1.0`, le même monde rechargé donne au désert occidental une densité
**supérieure ou égale** à la médiane — le test l'exige, et le rouge se prouve
ainsi dans les deux sens.

**SC5 — une seule formule** (`-k formule`). Pour le désert occidental, le
rapport `population_soutenable_de` avec facteur / sans facteur (neutralisé
comme en SC4) égale `facteur_eau` de sa pluie à 1e-12 près ; pour la Flandre,
les deux soutenables sont **identiques**. Contre-épreuve : pour chaque
cellule, `population_soutenable_de(cell, carte) ×
FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK` égale
`_production_du_tick_kg_saison_moyenne(cell, rendement_moyen_courant(),
carte)` à 1e-9 près relatif — un amorçage qui appliquerait l'eau à part de la
production casserait l'un ou l'autre.

**SC6 — la sonde voit la couche** (`-k sonde`). `build_snapshot_document(
World.charger(0), 0, 0)["couches"]["pluie"]` vaut `{"dans_la_carte": True,
"utilisee_par_le_moteur": True}`, et `schema_version == "v0a-5"`.
Contre-épreuve : avec `facteur_eau` neutralisé comme en SC4,
`_couche_consommee("pluie")` rend `False`.

**SC7 — rien d'existant ne s'assouplit.** `python3 -m pytest jeu -q` est vert.
`git diff origin/master -- jeu/sim/tests/test_monde.py jeu/sim/tests/test_pluie.py`
ne montre que les deux changements du point 5, et
`test_no_hardcoded.py`, `test_write_coverage.py`, `test_survie.py` et
`test_commerce.py` sont intacts. Contre-épreuve :
`python3 -m pytest jeu/sim/tests/test_pluie.py -q -k pure` rougit si l'on
ajoute `from sim.pluie import pluie_de_cellule` dans `sim/engine.py`, et
`python3 -m pytest jeu/sim/tests/test_monde.py -q -k schema_ferme` rougit si
l'on retire `"pluie"` de `_COUCHES`.

**SC8 — le modèle le dit.** `grep -n "facteur_eau" jeu/sim/MODELE.md` rend au
moins une ligne dans la section « Le rendement agricole et sa variabilité » et
une dans « Population initiale par cellule » ;
`grep -c "INITIAL_POPULATION_PER_KM2" jeu/sim/MODELE.md` rend `0` ;
`grep -n "le tick ne la lit pas" jeu/sim/MODELE.md` rend une ligne, et la
section de la pluie contient « Nil » et « vide ». Contre-épreuve : sur le
`MODELE.md` de `origin/master`, les deux premières commandes échouent.

## Hors périmètre
- Le Nil, la crue, les fleuves, l'irrigation, les oasis : non simulés. Le delta
  et la vallée du Nil sont vidés par ce lot, et c'est déclaré ; la preuve du
  jalon 2 sur la densité du delta attend le lot du fleuve.
- La table de pluie (`jeu/data/pluie-releves-1400.json`) et `sim/pluie.py` :
  inchangés. Aucune interpolation, aucune correction par le relief.
- La carte figée `jeu/data/world-1400.json` : inchangée sur le disque.
- La pluie dans l'année (mois, saisons sèches), sa variabilité d'une année à
  l'autre, la sécheresse comme événement, l'excès d'eau qui noie les champs.
- La table de référence des densités de 1400, les royaumes, les villes, la
  carte de départ du joueur : lots suivants du jalon 2.
- Les vues (tableau, chronique, relief, Unity) : aucune ne montre la pluie ni
  le facteur d'eau dans ce lot.
- `sim/aggregation.py`, `sim/model.py`, `sim/service.py`,
  `sim/__main__.py` : inchangés.
