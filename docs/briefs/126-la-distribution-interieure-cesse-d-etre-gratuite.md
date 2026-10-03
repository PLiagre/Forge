# Lot #126 — La distribution intérieure cesse d'être gratuite
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Le bourg d'une cellule ne mange plus que ce que ses propres champs et les
chemins venus des autres lieux lui apportent : sans chemin, le bourg a faim
pendant que les champs débordent (CAP.md, jalon 3, sa preuve).

## Règle du monde
Aujourd'hui, une cellule n'a qu'un panier, et tous ses habitants y mangent
comme s'ils se tenaient au même endroit. `MODELE.md` le dit : « Ce que B coûte,
dit franchement : la distribution à l'intérieur d'une cellule est gratuite. […]
Le jour où la cellule se subdivisera, c'est ici qu'il faudra revenir. » Le
lot #234 l'a subdivisée (« Les lieux d'une cellule, vue dérivée ») : ce lot y
revient.

**Qui est au bourg.** Les habitants qui ne cultivent pas : la part minière que
le moteur calcule déjà, `population × part_miniere_de(gisements, facteurs)`
— la même part que `_facteur_agricole` retire des champs et que l'extraction
envoie à la mine (« Ce qu'est une ville », « D'où vient la donnée »). Ils
vivent au lieu de rang 0, le bourg (« Les lieux d'une cellule »). Rien de
neuf n'est stocké : ni population par lieu, ni stock par lieu.

**Ce que le bourg peut atteindre, à chaque consommation.** Le panier est
réputé réparti entre les lieux au prorata de leur surface. Avec `s0` la
surface du rang 0, `A` celle de la cellule, `n` son nombre de lieux et
`stock` la nourriture du panier (sentinelle −1 lue comme 0) :

- `local = stock × s0 / A` — ce qui est déjà au bourg ;
- `capacite = CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK × (n − 1) × facteur_transport(relief)`
  — un chemin par lieu de rang ≥ 1 vers le bourg, freiné par le relief de la
  cellule avec la table de transport déjà utilisée par le commerce ;
- `accessible = min(stock, local + capacite)` ; une cellule d'un seul lieu
  n'a aucun chemin, et son bourg atteint tout le panier : `accessible = stock`.

**Qui mange quoi.** `besoin_bourg = population × part × ration`,
`besoin_champs = besoin_total − besoin_bourg`. Le bourg mange
`min(besoin_bourg, accessible)` ; il lui manque `manque_bourg`. Les champs
mangent ensuite sur le reste ; il y reste `reste_champs = stock −
mange_bourg − besoin_champs`.

- **Le bourg a faim pendant que les champs débordent** — si et seulement si
  `manque_bourg > 0` **et** `reste_champs > 0`. Alors le panier passe à
  `reste_champs` (les kilos restent dans les champs, rien ne se perd), la dette
  `food_deficit_kg` monte de `manque_bourg`, aucune dette ancienne n'est
  remboursée ce tick, et `manque_bourg` est la pénurie rendue : la faim, la
  mortalité, la natalité et la migration la lisent comme n'importe quelle
  pénurie.
- **Sinon, la consommation d'aujourd'hui s'applique, inchangée, au bit près.**
  Quand le bourg est servi, rien ne change ; quand le panier entier ne suffit
  pas, la cellule manque de toute façon, et à l'échelle de la cellule — la
  seule où vivent la dette et la population — savoir qui manque ne change
  aucun nombre.

**Conservation.** Aucun kilo n'est créé : ce qui sort du panier est ce qui a
été mangé, jamais plus que le besoin du tick, et le panier ne descend pas
sous zéro.

Cela découle de `jeu/sim/MODELE.md` : « Ce qu'est une ville, à l'échelle d'une
cellule » (le bourg, la décision B, et ce qu'elle coûte), « Les lieux d'une
cellule, vue dérivée » (rang 0 et surfaces), « Le commerce entre cellules »
(la table `facteurs_transport_par_relief()`), « Le moteur sans état caché »
et « Le monde d'épreuve, et pourquoi certaines constantes se cachent ».

**Niveau de fidélité : 2.** `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = 2500.0`
(× `TICK_DURATION_DAYS`) : l'ordre de grandeur de cinq charrettes d'une
demi-tonne par jour sur le chemin d'un pays vers son bourg ; plausible, jamais
sourcé. Mesuré le 30 septembre 2026 sur `World.charger(0)`, un an joué avec
la règle observée sans l'appliquer : 25 cellules ont un bourg ; sans chemin,
5 d'entre elles l'auraient laissé manquer (338 jours-cellule) ; à 2 500 kg,
une seule, pendant 2 jours. Le monde change donc peu, et seulement où il le
doit. **Niveau 3, pas simulé** : le délai et les pertes en route, les bras des
porteurs, le tracé des chemins, un stock propre à chaque lieu (le panier est
re-réparti par surface à chaque consommation), la distribution entre les
lieux des champs.

### Ce que le codeur écrit

**1. `jeu/sim/constants.py`** — `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = 2500.0
* TICK_DURATION_DAYS`, sous un commentaire de deux ou trois lignes (ce qu'elle
gouverne, niveau 2) ; et une fonction
`capacite_chemins_interieurs_kg(nombre_chemins, facteur_transport)` qui relit
la constante à chaque appel, refuse par `ValueError` nommant la constante une
valeur NaN ou négative (l'infini est accepté), et rend `constante ×
nombre_chemins × facteur_transport`. **La constante n'est jamais lue par son
nom dans `sim/engine.py`** : le monde d'épreuve de `test_write_coverage.py`
n'a ni carte ni gisement, elle y serait inerte et le contrôle rougirait
(MODELE.md, « Le monde d'épreuve… »). C'est la fonction que le moteur appelle.

**2. `jeu/sim/engine.py`** — `_apply_consumption(cell, carte=None)` : sans
carte, ou pour une cellule sans part minière (`part == 0`), exactement le
chemin actuel ; les appels existants `_apply_consumption(cell)` des tests ne
changent pas. Avec une carte, la règle ci-dessus, dans une fonction d'aide
(par exemple `_nourriture_accessible_au_rang0_kg`) qui lit `n` et `s0` par
`sim.lieux.lieux_de_cellule(cell.cell_id, cell.area_km2)`, la part par
`_constantes.part_miniere_de(_gisements_de(cell, carte),
_constantes.facteurs_richesse_extraction())`, le relief par
`_facteur_transport_pour_cellule`, et la capacité par la fonction de
`constants.py`. Les lieux, le relief et la capacité ne se calculent que si
`part > 0` et `n > 1`. `tick()` passe `carte` (éventuellement `None`) à
`_apply_consumption`. Interdits dans `engine.py` : importer
`sim.aggregation`, ou nommer l'un des noms de la vue du bourg que
`test_province.py::test_bourg_tick_ne_consulte_pas_la_vue` refuse. Aucun
littéral numérique autre que 0, 1, −1 (et leurs formes flottantes) dans un
corps de fonction.

**3. `jeu/sim/tests/test_distribution_interieure.py`** — les cas ci-dessous.
Le test construit lui-même ses cellules d'épreuve (`Cell`,
`ecrire_stock_marchandise`) et une carte minimale `{cell_id: {"relief": …,
"gisements": [{"ressource": "fer", "richesse": "majeure"}]}}` ; ses attentes
se calculent à partir des constantes lues du module et de
`lieux_de_cellule`, jamais recopiées. Les kilos se comparent avec
`math.isclose(rel_tol=1e-12)`, les signes strictement.

**4. `jeu/sim/MODELE.md`** — une section « ## La distribution à l'intérieur de
la cellule », placée juste après « Les lieux d'une cellule, vue dérivée » :
qui est au bourg, la répartition du panier par surface, la capacité et sa
constante nommée avec sa valeur, les deux cas (le bourg a faim pendant que les
champs débordent ; sinon la consommation inchangée), la conservation, le
niveau 2 et ce qui reste de niveau 3 (dont : la distribution entre les lieux
des champs, et les villes nommées qui ne sont pas comptées au bourg). Aucun
compte mesuré n'y est recopié. Dans la même passe :
- « Les lieux d'une cellule » : le tick lit désormais la vue à la
  consommation, sans rien stocker ; les phrases « le tick ne la lit pas », « il
  ne reçoit aucun habitant » et « reste gratuite » y sont remplacées ;
- « En une page » : le point 6 (Consommation) dit que le bourg ne mange que
  ce qu'il atteint, et le paragraphe des vues dérivées ne dit plus que le tick
  ne consomme pas celle des lieux ;
- « Ce qu'est une ville », « Ce que B coûte » : la gratuité prend fin pour le
  bourg ; renvoi à la nouvelle section par son titre ;
- « Ce que le moteur ne fait pas encore », puce « descendre sous la cellule » :
  les stocks restent un seul panier, réparti par surface à la consommation.

## Périmètre
jeu/sim/constants.py
jeu/sim/engine.py
jeu/sim/tests/test_distribution_interieure.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par
`python3 -m pytest jeu/sim/tests/test_distribution_interieure.py -q -s -k <nom>` ;
chaque test imprime ses compteurs, et un échantillon vide échoue.

Cellule d'épreuve « C » : surface `20 × SURFACE_KM2_PAR_LIEU` (20 lieux, le
bourg tient 1/20), relief `plaine`, un gisement `majeure` (part 0,10),
10 000 habitants, un panier égal à 1,5 × le besoin total du tick : le panier
couvre toute la cellule, mais sa part au bourg (1/20) ne couvre pas le besoin
du bourg (1/10).

**SC1 — sans chemin, le bourg a faim pendant que les champs débordent**
(`-k sans_chemin`). Constante patchée à `0.0` (`monkeypatch.setattr` sur
`sim.constants`) : `_apply_consumption(C, carte)` rend une pénurie égale à
`besoin_bourg − local` (> 0) ; le panier après est strictement positif et égal
à `reste_champs` ; `food_deficit_kg` a monté de la pénurie ; après
`_update_hunger`, `hunger_ticks == 1`. Contre-épreuve, dans le même test : la
même cellule par `_apply_consumption(C)` sans carte (la distribution
gratuite d'hier) ne manque de rien, et avec la constante du module non
patchée non plus — les chemins suffisent.

**SC2 — les chemins et le relief font la capacité** (`-k capacite`). Avec
`k = 2 × manque_sans_chemin / 19` : en plaine, pas de pénurie ; la même
cellule en `montagne` manque de `manque_sans_chemin − 19 × k ×
FACTEUR_TRANSPORT_MONTAGNE` (> 0) ; avec `k / 4` en plaine, la pénurie est
strictement entre 0 et celle sans chemin. Une cellule d'un seul lieu
(surface `SURFACE_KM2_PAR_LIEU / 2`), même part et même panier relatif,
constante à `0.0` : aucune pénurie — son bourg tient tout le panier. Et
`capacite_chemins_interieurs_kg` lève `ValueError` pour une constante patchée
à `float("nan")` puis à `-1.0`. Contre-épreuve : la montagne manque plus que
la plaine à constante égale (compteur imprimé).

**SC3 — aucun kilo créé** (`-k conservation`). Sur C sans chemin :
`panier_avant − panier_après == mange_bourg + besoin_champs`, ce total est ≤
au besoin du tick, le panier après ≥ 0, et `dette_après − dette_avant ==
pénurie rendue` (une dette ancienne posée à 1 000 kg n'est pas remboursée ce
tick). Le contrôle est une fonction du test ; contre-épreuve : appliquée à un
résultat fabriqué où le bourg a mangé sans que le panier baisse, elle échoue.

**SC4 — quand les chemins suffisent, rien ne change au bit près**
(`-k identique`). Constante patchée à `float("inf")` : pour chacune des
cellules de `World.charger(0)`, au monde amorcé puis après 30 ticks joués
(`tick(world, rng, n)`), une copie profonde passée à `_apply_consumption(copie,
world.carte)` et une autre à `_apply_consumption(copie2)` rendent la même
pénurie, le même panier et la même dette, à l'égalité exacte ; compteur
`cellules_comparees` = 2 × le nombre de cellules, dont `avec_bourg` > 0.
Contre-épreuve : sur C, constante à `0.0`, les deux chemins diffèrent.

**SC5 — le monde réel le ressent** (`-k monde`). Deux `World.charger(0)`,
120 ticks chacun avec `random.Random(0)` et `numero_tick`, l'un avec la
constante à `0.0`, l'autre avec celle du module : la population totale des
cellules à part minière > 0 (dérivées de la carte, jamais écrites en dur) est
**strictement plus basse** sans chemin (direction, pas valeur ; les deux
totaux imprimés). Mesuré le 30 septembre 2026 avec la règle observée : sans
chemin, 5 cellules manquent dès les 120 premiers jours. Contre-épreuve, dans
le même test : les deux mêmes parties rejouées avec
`engine._apply_consumption` remplacé (`monkeypatch`) par une enveloppe qui
rappelle l'original **sans** carte — la distribution gratuite — rendent deux
totaux égaux : la comparaison stricte, appliquée à eux, échoue.

**SC6 — rien d'existant ne s'assouplit.** `python3 -m pytest jeu -q` est
vert, et `git diff --name-only origin/master -- jeu/sim/tests` ne rend que
`jeu/sim/tests/test_distribution_interieure.py`. En particulier
`test_write_coverage.py` trouve un lecteur à la constante,
`test_province.py::test_bourg_tick_ne_consulte_pas_la_vue`,
`test_no_hardcoded.py`, `test_survie.py`, `test_determinisme.py` et
`test_lieux.py` restent tels quels. Contre-épreuve : lire
`_constantes.CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK` par son nom dans
`engine.py` rend `test_write_coverage.py` rouge (constante inerte sur le monde
d'épreuve).

**SC7 — le modèle le dit.** `grep -n "^## La distribution à l'intérieur de la
cellule" jeu/sim/MODELE.md` rend une ligne, et la section contient
`CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK`, « rang 0 » et « niveau 2 ». Et
`awk '/^## Les lieux d.une cellule/{s=1;next} /^## /{s=0} s' jeu/sim/MODELE.md | grep -c "le tick ne la lit pas"`
rend 0. Contre-épreuve : sur la base, la première commande ne rend rien et la
seconde rend 1.

## Hors périmètre
- Le maître d'un lieu, son suzerain, le prélèvement et « ce que le siège
  reçoit, moins le transport » : les lots suivants du jalon 3.
- Un stock ou une population propres à chaque lieu ; les pertes et le délai
  en route ; les bras des porteurs ; la distribution entre les lieux des
  champs, qui reste gratuite.
- La route et tout ce qui augmente la capacité d'un chemin : jalon 4.
- Les villes nommées (`villes.py`) : leur population n'est pas comptée au
  bourg ; en décider change la règle de « Ce qu'est une ville », au
  propriétaire.
- `sim/aggregation.py`, `sim/lieux.py`, `sim/world.py`, `sim/model.py`,
  `sim/service.py`, le snapshot et toutes les vues : aucun ne change, aucune
  vue ne montre la faim du bourg dans ce lot.
- La mesure contre le budget du tick : la règle ne s'applique qu'aux cellules
  à part minière (25 aujourd'hui) ; aucun nouveau passage sur tout le monde.
