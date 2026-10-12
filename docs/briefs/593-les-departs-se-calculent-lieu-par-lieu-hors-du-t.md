# Lot #593 — Les départs se calculent lieu par lieu, hors du tick
Jalon : J3 · Machine : vps · Taille prévue : 260 lignes

## But
Le monde sait calculer, pour chaque lieu habité, qui part vers un lieu
nettement mieux nourri — d'abord dans sa cellule, sinon vers le bourg d'une
cellule voisine — sans qu'un kilo, une dette ou une faim ne voyage, par une
fonction que le tick n'appelle pas encore.

## Le joueur
Lot de fond. Il prépare la décision du jalon 3 : « prendre plus aujourd'hui
ou garder ses gens — trop prendre les appauvrit et les fait partir chez le
voisin ». Après ce lot, la règle qui fait partir les foyers vers le mieux
nourri existe et se prouve seule ; le joueur ne la sent pas encore. Le
sous-lot 2 de #591 la branche dans le tick : alors une part trop forte vide
les greniers des lieux du joueur, leur réserve tombe sous celle du voisin, et
ses foyers s'en vont. #401 et #403 montreront ces lieux qui se vident sur la
carte.

## Règle du monde
Niveau 2 : plausible, jamais sourcé. Découle de `jeu/sim/MODELE.md`,
« La migration de famine » (« Où l'on va » : les arrivants rejoignent le
bourg ; « L'atomicité » : les métiers suivent au prorata, aucun kilo, aucune
dette ni aucune faim ne voyage) et « Les lieux d'une cellule, vue dérivée ».
`MODELE.md` ne change pas dans ce lot : la section « Les départs » vient
avec le branchement dans le tick (sous-lot 2 de #591).

Nouveau module `jeu/sim/departs.py`, une fonction publique
`appliquer_departs(world) -> int`, qui rend le nombre de personnes parties.
**Le tick ne l'appelle pas** : `engine.py` n'est pas touché.

Trois constantes nouvelles dans `jeu/sim/constants.py`, de niveau 2, chacune
avec son commentaire (« Niveau 2 : … ») :

| constante | valeur | sens |
|---|---|---|
| `ECART_DE_DEPART_JOURS` | 30 | écart de réserve, en jours, qu'il faut dépasser strictement pour partir ; c'est aussi la tranche du taux |
| `TAUX_DE_DEPART` | 0.002 | part des habitants qui part par jour, par tranche entière d'écart |
| `PLAFOND_DE_DEPART` | 0.01 | part des habitants qui peut partir au plus par jour |

`departs.py` les lit par `_constantes.` (`import sim.constants as
_constantes`), jamais par `from sim.constants import …`, avec `TAILLE_FOYER`,
`MARCHANDISE_NOURRITURE`, `TICK_DURATION_DAYS` et
`consommation_kg_par_habitant_par_tick`. Aucun littéral numérique autre que
0, 1, −1 dans ses fonctions (`test_no_hardcoded.py` balaie tout `sim/`).

**La photo.** Avant tout mouvement, on lit pour chaque lieu habité
(`population > 0`) de chaque cellule à lieux :

```
ration  = consommation_kg_par_habitant_par_tick(nourriture) / TICK_DURATION_DAYS   # 2 kg
réserve = (nourriture − dette_alimentaire_kg) / (population × ration)               # en jours
```

La nourriture se lit par `lire_stock_marchandise(lieu, MARCHANDISE_NOURRITURE)`
(jamais `lieu.stocks` : `test_acces_directs_au_panier_hors_modele` le
refuse) ; la sentinelle −1 d'un panier sans nourriture se lit 0 kg, comme
`_surplus_nourriture_tick` de la migration de famine. La réserve peut être
négative (dette plus grosse que le grenier). Tout le reste se calcule sur
cette photo : populations et réserves ne sont jamais relues après un
mouvement.

**Un lieu vide** (`population == 0`) n'envoie ni ne reçoit personne. Une
cellule sans lieux (`cell.lieux` vide) n'envoie ni ne reçoit personne.

**La destination**, pour chaque lieu habité L de réserve r :

1. le meilleur des **autres** lieux habités de sa cellule, s'il a une
   réserve strictement supérieure à r + `ECART_DE_DEPART_JOURS` ;
2. sinon, le meilleur des **bourgs (rang 0) habités des cellules voisines**,
   s'il passe le même seuil strict. Voisines : les arêtes de
   `world.adjacency` dont les deux bouts sont des cellules du monde (les
   arêtes vers la mer, `b = -1`, n'en sont pas). Un lieu de rang ≥ 1 d'une
   cellule voisine n'est jamais une destination, même mieux pourvu ;
3. sinon, L ne bouge pas.

« Meilleur » = plus forte réserve ; à réserve égale, le plus petit couple
`(cell_id, rang)`. Un lieu de la cellule qui passe le seuil l'emporte sur un
bourg voisin mieux pourvu (la cellule d'abord).

**La recherche ne regarde chaque lieu qu'une fois** (la version naïve, tous
les lieux de la cellule pour chaque lieu, coûtait environ 120 ms de plus par
tick) : une passe sur les lieux habités calcule les réserves et retient, par
cellule, le meilleur et le deuxième ; le meilleur autre lieu de L est le
premier de sa cellule, ou le deuxième si L est le premier. Puis une passe sur
`world.adjacency` retient, pour chaque cellule, le meilleur bourg voisin.
Mesuré sur un prototype en une passe, monde de 1400 graine 0 (596 cellules,
6 619 lieux) : 21 à 36 ms par appel ; aucun départ aux ticks 0 et 30,
6 lieux et 90 personnes au tick 60, 101 lieux et 4 855 personnes au tick 120,
dont 58 lieux vers une cellule voisine.

**Combien partent**, avec `écart = réserve(destination) − r` :

```
tranches  = floor(écart / ECART_DE_DEPART_JOURS)                   # ≥ 1 puisque écart > 30
part      = min(TAUX_DE_DEPART × tranches, PLAFOND_DE_DEPART) × TICK_DURATION_DAYS
partants  = floor(population_photo × part / TAILLE_FOYER) × TAILLE_FOYER
```

Les partants sont des foyers entiers, arrondis vers le bas ; il n'y a pas de
report de fraction (un lieu de moins de 2 500 habitants n'envoie personne à
une tranche, un lieu de moins de 500 n'envoie personne même au plafond).
Taux et plafond sont des parts **par jour** : à `TICK_DURATION_DAYS = 1`, le
facteur ne change rien.

**L'application**, une fois toutes les destinations fixées sur la photo :

- chaque lieu reçoit `population += entrées − sorties` ; comme les sorties
  d'un lieu ne dépassent jamais sa population photographiée, aucun lieu ne
  devient négatif, et l'ordre d'application ne change rien. Un lieu peut
  envoyer et recevoir dans le même appel (pas d'annulation comme dans la
  migration de famine) ;
- dans une même cellule, ni `cell.population` ni les métiers ne bougent ;
- entre deux cellules, le **solde** de chaque cellule (entrées moins sorties
  hors cellule) passe une seule fois par `_ajouter_par_les_foyers` ou
  `_retirer_par_les_foyers`, dans l'ordre des `cell_id` croissants, comme le
  fait `_apply_migration` : les métiers suivent au prorata et
  `cell.population` reste la somme de ses lieux. `departs.py` importe le
  module (`from sim import engine as _engine`) et appelle
  `_engine._retirer_par_les_foyers` au moment de l'appel — jamais
  `from sim.engine import _retirer_par_les_foyers` : le sous-lot 2 fera
  importer `departs` par `engine`, et les tests existants remplacent ces deux
  fonctions sur le module `engine` ;
- **rien d'autre ne bouge** : paniers des lieux et des cellules, dettes,
  `duree_faim_ticks`, reports de mortalité, de natalité et de migration,
  maîtres, `food_deficit_kg`, `hunger_ticks`, bassin maritime.

**La règle ne lit ni le maître ni la part prélevée** : aucun accès à
`maitre`, `parts`, `PART_COUTUMIERE`, `PART_DUE_AU_SUZERAIN`, ni import de
`prelevement`, `maitres`, `greniers`, `convois`. Le prélèvement n'agit sur
les départs que parce qu'il vide les paniers.

## Périmètre
jeu/sim/departs.py
jeu/sim/constants.py
jeu/sim/tests/test_commerce.py

## Conditions de succès
Les cas neufs vont à la fin de `jeu/sim/tests/test_commerce.py`, appellent
`appliquer_departs` directement, et leur nom commence par `test_departs_`.
Ils peuvent réutiliser `_cellule_bourg` et `_conserver_bourg` du même
fichier. Aujourd'hui, `-k departs` ne recueille qu'un test existant,
`test_bourg_contre_epreuves_memes_controles[departs]` (une mutation de la
migration de famine) : il reste tel quel, et le décompte des cas neufs se lit
à part. Rouge d'abord : avant le module, chaque cas neuf échoue à
l'import de `sim.departs`.

Les valeurs ci-dessous supposent une ration de 2 kg, `TAILLE_FOYER = 5` et un
lieu source de 5 000 habitants à réserve 0, sauf mention.

- **SC1 — seuil strict.** Destination dans la cellule à réserve 30 jours
  exactement (60 000 kg pour 1 000 habitants) : 0 partant. À 30,01 jours
  (60 020 kg) : 10 partants. Contre-épreuve : un `>=` au lieu de `>` fait
  partir 10 personnes au premier cas ; `ECART_DE_DEPART_JOURS` remplacé par 31
  (monkeypatch) fait échouer le second.
- **SC2 — dette déduite**, des deux côtés. Destination à 50 jours de grain
  mais 20 jours de dette : réserve 30, 0 partant (10 sans la dette). Source
  sans grain avec 20 jours de dette (réserve −20), destination à 15 jours :
  écart 35, 10 partants (0 sans la dette). Contre-épreuve : les deux cas
  attendent un nombre différent de celui que donnerait une règle qui ignore
  la dette.
- **SC3 — taux.** Écart 60,5 jours → 20 partants ; écart 90,5 → 30.
  Contre-épreuve : `TAUX_DE_DEPART` doublé (monkeypatch) → 40 et 50 (le
  plafond mord), le cas échoue.
- **SC4 — plafond.** Écart 400 jours (13 tranches) → 50 partants, pas 130.
  Contre-épreuve : `PLAFOND_DE_DEPART` doublé → 100, le cas échoue.
- **SC5 — foyers entiers.** Écart 30,5 jours : source de 2 499 habitants →
  0 ; 2 500 → 5 ; 7 499 → 10. Contre-épreuve : `TAILLE_FOYER = 1`
  (monkeypatch) → 4, 5, 14, le cas échoue.
- **SC6 — la cellule d'abord, puis les bourgs voisins.** Cellule 1 = source
  (réserve 0) + un lieu à 40 jours ; cellule 2 voisine, bourg à 200 jours :
  les partants vont au lieu de la cellule 1. Même monde avec le lieu de la
  cellule 1 à 20 jours : ils vont au bourg de la cellule 2. Le rang 1 de la
  cellule 2 à 500 jours, un bourg vide de la cellule 4 voisine riche en grain,
  et le bourg d'une cellule 3 non voisine à 500 jours ne reçoivent jamais
  personne. Égalités : deux bourgs voisins à la même réserve → le plus petit
  `cell_id` ; deux lieux de la cellule à la même réserve → le plus petit rang.
  Contre-épreuve : déplacer un habitant de la destination attendue vers une
  autre après l'appel fait échouer le contrôle.
- **SC7 — lieu vide et photo.** Un lieu à 0 habitant et 100 000 kg ne reçoit
  personne et n'envoie personne. Chaîne A → B → C : dans la cellule 1, A
  (rang 1, réserve 0, 2 500 habitants) et B (rang 0, réserve 35) ; C est le
  bourg de la cellule 2 voisine (réserve 70, 1 000 habitants). A part vers B
  (le seuil passe dans sa cellule), B part vers C (rien dans sa cellule).
  Avec B à 5 000 habitants : A 2 495, B 4 995, C 1 010 — B envoie et reçoit
  dans le même appel. Avec B à 2 495 habitants : A 2 495, B 2 500, C 1 000 —
  sur la photo B n'envoie personne. Le même monde, cellules et arêtes en
  ordre inverse, donne le même `to_dict()`. Contre-épreuve : une version qui
  relirait la population de B après l'arrivée de A enverrait 5 personnes à C
  dans le second cas, et le cas échoue.
- **SC8 — maître ignoré.** Le même monde, avec des `maitre` différents sur
  chaque lieu et `world.parts` rempli de valeurs quelconques, donne les mêmes
  populations. Une lecture AST de `departs.py` ne trouve aucun attribut
  `maitre`, `parts`, `PART_COUTUMIERE`, `PART_DUE_AU_SUZERAIN`, aucun import
  de `prelevement`, `maitres`, `greniers`, `convois`, et lit
  `ECART_DE_DEPART_JOURS`, `TAUX_DE_DEPART`, `PLAFOND_DE_DEPART`,
  `TAILLE_FOYER` comme attributs de `_constantes`. Contre-épreuve : la même
  lecture AST sur un texte qui contient `lieu.maitre` doit échouer.
- **SC9 — conservation exacte.** Sur un monde de trois cellules voisines à
  plusieurs lieux, avec départs dans la cellule et entre cellules : la
  population du monde est la même ; chaque cellule vaut la somme de ses lieux
  (`_conserver_bourg`) ; une cellule sans départ hors d'elle garde ses
  métiers à l'identique ; une cellule de solde −n a pour métiers
  `foyers.retirer(avant, n)`, de solde +n `foyers.ajouter(avant, n)` ; chaque
  lieu garde, au-delà de sa population, tous ses champs à l'identique
  (`vars(lieu)` sans `population`) ; chaque cellule garde ses paniers, ses
  reports et sa faim ; la somme des paniers de chaque cellule et du monde est
  la même, exactement (`Fraction`). La valeur rendue égale la somme des
  sorties. Contre-épreuves : un kilo déplacé d'un lieu à l'autre, un
  habitant ajouté à un lieu, ou `engine._retirer_par_les_foyers` remplacé
  par une version qui ne retire que `cell.population` font chacun échouer le
  contrôle.
- **SC10 — une seule lecture par lieu.** `departs.py` importe
  `lire_stock_marchandise` par son nom (`from sim.model import …`). Sur le
  monde de SC9, `departs.lire_stock_marchandise` remplacé par un compteur est appelé
  exactement une fois par lieu habité. Une cellule de 4 000 lieux habités à
  réserves toutes différentes, avec deux voisines, se calcule en moins d'une
  demi-seconde (une recherche naïve, 16 millions de comparaisons, prend
  plusieurs secondes). Contre-épreuve : un compteur qui attend une lecture de
  plus échoue.

Commandes :

- `python3 -m pytest jeu/sim/tests/test_commerce.py -q -k departs` — vert,
  et `python3 -m pytest jeu/sim/tests/test_commerce.py -q -k test_departs_ --co`
  recueille au moins dix cas.
- `python3 -m pytest jeu/sim -q` — vert, en particulier
  `test_no_hardcoded.py`, `test_write_coverage.py`
  (`test_aucune_constante_terminale` : chaque constante neuve est lue par
  `departs.py`) et `test_monde.py::test_acces_directs_au_panier_hors_modele`.
  Contre-épreuve : une constante neuve que `departs.py` ne lit pas fait
  rougir `test_aucune_constante_terminale`.
- `grep -n departs jeu/sim/engine.py` ne rend rien : le tick ne l'appelle
  pas, aucune empreinte ni preuve historique ne bouge.

## Hors périmètre
- Brancher `appliquer_departs` dans le tick, la section « Les départs » de
  `MODELE.md`, les titres de `test_commerce.py` et `test_foyers.py` qui
  parlent des départs, l'isolement des preuves historiques
  (`TAUX_DE_DEPART = 0`) et le temps du tick : sous-lot 2 de #591.
- `engine.py`, `MODELE.md`, tout test existant : aucun ne change.
- Les départs par la mer, vers un lieu de rang ≥ 1 d'une autre cellule, ou
  plus loin qu'une cellule voisine.
- Les métiers propres à un lieu ; les arrivants prennent ceux de la cellule
  d'arrivée (niveau 3, comme la migration de famine).
- Un report de fraction des départs.
- Ce que le joueur voit : #400, #401, #403.
