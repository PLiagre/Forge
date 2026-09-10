# Brief 049 — Fabriquer : le minerai devient un objet

## But

Faire qu'une matière première extraite cesse de s'accumuler indéfiniment dans
le panier de la cellule qui l'a sortie : une part du stock est **façonnée**,
tick après tick, en une marchandise nouvelle, générique, `objet`.

C'est la première transformation du jeu. Jusqu'ici le panier ne connaît que
deux mouvements — un gisement en fait sortir des kilogrammes, une arête en
déplace — et aucun des deux ne change jamais la marchandise elle-même :
« le minerai extrait reste du minerai » (`ROADMAP.md`, couche 1, « Ce que le
monde ne sait pas encore faire »).

**Ce lot dépend de 044** (« un métier : le mineur »), **déjà fusionné**
(PR #184, #188) : c'est lui qui fait qu'une cellule porte réellement du
minerai dans son panier. Sans lui l'échantillon serait vide ; avec lui il ne
l'est pas, et rien ne bloque ce lot.

**Indépendant des lots 046 et 047.** Ce lot ne touche à aucune arête et
n'ajoute aucune part de population : il transforme un stock en place, dans la
cellule qui le porte, sans transport et sans bras.

Ce qui rend ce lot caduc : si `sim/` porte déjà une marchandise fabriquée à
partir d'une autre marchandise du panier, il n'y a rien à faire ici.

```bash
grep -rn "fabriqu\|MARCHANDISE_OBJET\|_apply_fabrication" sim/*.py
py -m sim --ticks 20 --seed 0 --json
```

## Règle du monde

Découle de [`sim/MODELE.md`](../sim/MODELE.md) : § « L'extraction minière »,
sous-section « La limite d'aujourd'hui » — « ce que la mine sort ne va nulle
part » est exactement ce que ce lot corrige en partie ; § « Le panier de
marchandises » — les deux seuls accès autorisés, `lire_stock_marchandise` et
`ecrire_stock_marchandise`, et la distinction absence/zéro ; et § « Le
commerce entre cellules », sous-section « Pourquoi le minerai ne bouge pas » —
qui explique qu'aucune marchandise non alimentaire n'a de demandeur
aujourd'hui. Si l'une de ces sections a changé depuis, la relire avant de
lancer.

**Fidélité niveau 2** : le taux de façonnage et le rendement de fabrication
sont des ordres de grandeur plausibles, générés, jamais sourcés. Une
proportion locale surprenante n'est pas un défaut et n'ouvre ni correctif, ni
lot.

### 1. Une marchandise générique, pas une recette par ressource

La fabrication ne distingue pas le fer de l'argent : toute matière première
présente au panier — c'est-à-dire toute marchandise qui n'est ni la
nourriture ni l'objet lui-même — se transforme en une seule et même
marchandise, `MARCHANDISE_OBJET = "objet"`.

C'est une simplification déclarée, pas un oubli : le jeu n'a ni recette, ni
atelier nommé, ni chaîne de production par ressource. Inventer une table
« fer → outils, argent → bijou » exigerait une source que le niveau 2
n'a pas, et le niveau 3 ne se simule pas (règle 10). Le jour où une recette
par ressource existera, elle remplacera cette règle sans qu'elle soit à
deviner ici.

### 2. Le mécanisme, par cellule et par tick

Pour chaque marchandise `m` du panier de la cellule telle que
`m ∉ {nourriture, objet}` et dont le stock est strictement positif :

```
consomme(m) = stock(m) × TAUX_FABRICATION_PAR_TICK
produit(m)  = consomme(m) × RENDEMENT_FABRICATION

nouveau_stock(m)      = stock(m) − consomme(m)
nouveau_stock(objet) += produit(m)
```

| constante | valeur | ce que c'est |
|---|---:|---|
| `TAUX_FABRICATION_PAR_TICK` | 0.05 | part du stock de matière première façonnée par tick ; niveau 2 |
| `RENDEMENT_FABRICATION` | 0.6 | kg d'objet produits par kg de matière première consommée ; le reste part en perte de façonnage (chutes, scories) ; niveau 2 |

`RENDEMENT_FABRICATION < 1` est un choix de modèle, pas une approximation à
corriger : la fabrication n'est pas une conservation de la masse comme le
commerce (`test_conservation_masse_par_marchandise`) — c'est une
transformation, et une transformation perd de la matière, comme la fonte
perd en scories.

Les deux constantes se lisent par **une seule fonction** de
`sim/constants.py`, relue à chaque appel — le même motif que
`part_miniere_de()` :

```
def fabrication_kg(stock_brut_kg: float) -> tuple[float, float]:
    ...  # relit TAUX_FABRICATION_PAR_TICK et RENDEMENT_FABRICATION
```

Interdit dans `sim/engine.py` : `_constantes.TAUX_FABRICATION_PAR_TICK` ou
`_constantes.RENDEMENT_FABRICATION` nommées directement. Autorisé :
`_constantes.fabrication_kg(...)`.

**Pourquoi cette indirection n'est pas cosmétique.** Le monde d'épreuve de
`sim/tests/test_write_coverage.py` (`_MondeEpreuve`) ne porte aucune matière
première : remplacer ces deux constantes en mémoire n'y changerait jamais
rien, quelle que soit la façon dont le moteur les lit. Si `engine.py` les
nommait directement, `test_chaque_constante_du_moteur_change_le_monde` les
classerait « consultées » puis les trouverait inertes, et rougirait sans
qu'aucun défaut n'existe — exactement le piège que le lot 044 a payé pour les
mêmes deux raisons sur `PART_MINIERE_PAR_GISEMENT` et
`PART_MINIERE_MAXIMALE`. L'indirection les tient hors du dénominateur de ce
contrôle ; `test_aucune_constante_terminale` continue de les voir lues, par
`fabrication_kg` elle-même.

**Élargir `_MondeEpreuve` pour lui donner une matière première n'est pas la
solution retenue**, et le périmètre l'interdit.

### 3. Énumérer le panier sans l'indexer directement

Aucun module hors `sim/model.py` n'indexe `stocks` directement
(`test_acces_directs_au_panier_hors_modele`). Pour découvrir les
matières premières d'une cellule, ce lot emploie le même détour que
`_marchandises_du_monde` emploie déjà pour le commerce :
`cellule_vers_dict(cell).get("stocks") or {}` rend une **copie** du panier,
dont les clés sont énumérées ; chaque lecture et chaque écriture réelles
passent ensuite par `lire_stock_marchandise` et `ecrire_stock_marchandise`,
jamais par cette copie.

### 4. L'ordre : la fabrication façonne le stock d'hier, jamais celui du jour

La fabrication est le **premier** maillon du tick, avant l'extraction : elle
porte sur le panier tel qu'il était **au début du tick**, avant que la mine
n'y verse quoi que ce soit aujourd'hui. Le minerai sorti ce tick n'est
façonné qu'à partir du tick suivant.

Ce n'est pas un détail d'implémentation : c'est ce qui garde vert, sans y
toucher, tout contrôle qui joue **un seul tick** depuis un monde fraîchement
chargé et compare l'ensemble des marchandises du panier à celles que la carte
déclare — notamment `test_chaque_gisement_produit_sa_ressource`,
`test_gisement_incomplet_ignore` et `test_ressource_inconnue_acceptee`. Au
premier tick d'un monde neuf, le panier ne porte encore aucune matière
première avant l'extraction : la fabrication n'y trouve rien à faire, et
`objet` n'apparaît pas avant le second tick. Inverser l'ordre — façonner ce
que l'extraction vient de verser le même tick — ferait rougir ces trois
contrôles, qu'il est interdit de modifier (règle 4).

`_apply_fabrication` s'exécute pour toute cellule, **avec ou sans carte
chargée** : elle ne lit que le panier, jamais `world.carte`. Sur un monde
sans matière première, elle ne trouve rien et ne change rien.

### 5. Ce qui se refuse plutôt que se deviner

- **Aucune recette par ressource.** Voir § 1.
- **L'objet ne circule pas plus que le minerai.**
  `consommation_kg_par_habitant_par_tick("objet")` rend zéro, comme pour
  toute marchandise non alimentaire : ce lot ne crée aucun demandeur, il ne
  fait que transformer. L'objet fabriqué s'accumule à son tour, exactement
  comme le minerai avant lui — ce n'est pas un défaut de ce lot, c'est la
  même absence déclarée que « Pourquoi le minerai ne bouge pas », maintenant
  vraie aussi pour l'objet.
- **Aucun bras n'est occupé.** La fabrication ne retire personne aux champs
  ni à la mine ; elle ne touche à aucune population et n'ajoute aucun champ à
  `Cell`. Le jour où un métier d'artisan existera pour la borner par du
  travail, comme le lot 044 l'a fait pour l'extraction, ce sera un lot
  séparé.
- **Une matière première à zéro ne produit rien**, et ce n'est pas une
  erreur : c'est une mesure réelle, le stock a été regardé et il ne portait
  rien. La sentinelle « non calculé » du panier reste `-1`, jamais `0`, et ce
  lot ne la touche pas.

### Où ça se raccorde

Le taux et le rendement se lisent à un seul endroit, par la fonction
`fabrication_kg()`. Rien d'autre du moteur n'est modifié : la production, le
commerce, la consommation, la faim, la mortalité, la natalité et la migration
gardent exactement leurs formules actuelles. Aucun champ n'est ajouté à
`Cell` : le panier générique porte déjà tout ce qu'il faut.

## Périmètre

En écriture :

- `sim/constants.py`, pour `MARCHANDISE_OBJET`, `TAUX_FABRICATION_PAR_TICK`,
  `RENDEMENT_FABRICATION` et `fabrication_kg()` ;
- `sim/engine.py`, pour `_apply_fabrication`, sa fonction d'énumération des
  matières premières, l'appel dans `tick()` avant l'extraction, et la mise à
  jour du docstring d'en-tête qui énumère les maillons ;
- `sim/tests/test_monde.py`, **uniquement pour y ajouter** des cas — c'est le
  fichier qui porte déjà les invariants du panier et de l'extraction
  minière. Aucun test déjà présent n'est modifié, renommé ni supprimé.

Tout autre chemin est interdit, nommément : `sim/MODELE.md`, `sim/model.py`,
`sim/world.py`, `sim/aggregation.py`, `sim/snapshot_export.py`,
`sim/__main__.py`, `sim/tests/test_write_coverage.py` — dont `_MondeEpreuve`
—, `sim/tests/test_commerce.py`, `sim/tests/test_survie.py`,
`sim/tests/test_province.py`, `sim/tests/test_no_hardcoded.py`,
`sim/tests/test_determinisme.py`, la carte figée, le visualiseur, les briefs
044, 046, 047, 048, et ce brief.

**Aucun test existant n'est modifié, renommé, supprimé ni relâché**, dans
aucun fichier. Si un test existant devient rouge, c'est le code de ce lot qui
est faux, ou c'est ce brief : on s'arrête et on le dit — on ne touche pas au
test.

## Conditions de succès

Les comparaisons « avant / après » se font contre `master` rejoué au
démarrage du lot, jamais contre un nombre recopié d'ici.

### SC1 — La fabrication transforme, dans les proportions déclarées

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

Sur une cellule d'épreuve dont le panier porte une matière première à un
stock strictement positif, un appel isolé à `_apply_fabrication` :

- rend le stock final égal à `stock_avant - consomme`, où
  `consomme = stock_avant × _constantes.TAUX_FABRICATION_PAR_TICK` ;
- rend le stock final d'`objet` égal à `objet_avant + produit`, où
  `produit = consomme × _constantes.RENDEMENT_FABRICATION` et où un objet
  absent vaut zéro disponible, pas la sentinelle moins un.

Ces égalités comparent les **états finaux**, au bit près, avec les
constantes lues dans le test, jamais recopiées. Ne pas calculer la quantité
consommée par `stock_avant - stock_apres` pour exiger ensuite qu'elle soit
exactement égale au produit flottant : cette seconde soustraction peut
arrondir autrement sans aucune erreur du mécanisme. Les cas incluent un
objet déjà présent et une matière première à stock nul ou non calculé.

**Rouge prouvé d'abord** : sur `master`, `_apply_fabrication` n'existe pas et
l'appel lève une erreur d'attribut.

### SC2 — Le rendement est strictement inférieur à un

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

`RENDEMENT_FABRICATION` est strictement inférieur à 1, lu par la constante,
jamais recopié. Pour toute matière première à stock strictement positif, la
quantité d'objet produite est strictement inférieure à la quantité
consommée. C'est ce qui distingue une transformation d'un transport : le
transport conserve, la transformation perd.

### SC3 — Deux matières premières distinctes alimentent le même objet

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

Une cellule d'épreuve porte deux marchandises différentes (par exemple deux
ressources minières distinctes de la carte), toutes deux à stock
strictement positif. Après `_apply_fabrication`, le stock d'`objet` est
strictement supérieur à ce que l'une ou l'autre aurait produit seule : les
deux contributions se sont cumulées dans la même marchandise, comme § 1 le
déclare.

### SC4 — Le premier tick d'un monde neuf ne façonne rien de ce jour

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

Sur `World.charger(0)` joué pour **exactement un tick**
(`numero_tick=0`), aucune cellule ne porte `objet` dans son panier à la fin
du tick. C'est la preuve directe de la règle du monde § 4 : la fabrication
n'a rien trouvé à façonner avant que l'extraction n'ait versé le minerai de
ce tick, et c'est cet ordre qui garde verts les contrôles existants portant
sur le premier tick.

L'échantillon est le monde réel chargé ; s'il ne compte aucune cellule
porteuse de gisement, le contrôle échoue au lieu de conclure à vide.

### SC5 — Le deuxième tick façonne ce que le premier a extrait

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

Sur une cellule que la carte déclare porteuse d'au moins un gisement
complet, jouée pour deux ticks consécutifs depuis `World.charger(0)`, le
panier porte `objet` à une valeur strictement positive à la fin du second
tick.

L'échantillon est dérivé de la carte (cellules porteuses d'un gisement
complet) ; un échantillon vide fait échouer le contrôle.

### SC6 — L'objet ne circule pas

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

`_constantes.consommation_kg_par_habitant_par_tick("objet")` rend `0.0`,
exactement comme pour toute marchandise non alimentaire inconnue. Ce lot ne
crée aucun demandeur pour l'objet fabriqué.

### SC7 — Les deux constantes ne se lisent que par une fonction

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

Un contrôle parcourt l'arbre syntaxique de `sim/engine.py` et échoue si le
module référence `_constantes.TAUX_FABRICATION_PAR_TICK` ou
`_constantes.RENDEMENT_FABRICATION` par leur nom. Il n'échoue pas sur un
appel à `_constantes.fabrication_kg(...)`.

**Rouge prouvé** sur une version délibérément fautive du moteur qui nomme
l'une des deux constantes directement : le contrôle doit rougir dessus,
sinon il ne protège rien.

### SC8 — Aucun accès direct au panier hors `sim/model.py`

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.

`sim/tests/test_monde.py::test_acces_directs_au_panier_hors_modele` reste
vert **sans modification**. Le code de ce lot n'indexe `stocks` que par
`cellule_vers_dict(...).get("stocks")`, `lire_stock_marchandise` et
`ecrire_stock_marchandise` — jamais par un `cell.stocks` direct dans
`sim/engine.py`.

### SC9 — Le déterminisme tient

Commande : `python3 -m pytest sim/tests/test_monde.py -k fabrication -q`.
Les nouveaux cas de ce lot portent `fabrication` dans leur nom.

Comparer deux mondes chargés avec la même graine et joués pendant la même
suite de ticks numérotés. Comparer leur `to_dict()` (qui inclut les
paniers des cellules) et `stocks_mer`, pas seulement le résumé de la CLI :
`--json` ne contient aucun stock d'objet. L'échantillon doit contenir au
moins une cellule dont `MARCHANDISE_OBJET` est strictement positif, sinon
la preuve de déterminisme de fabrication échoue à vide.

Ajouter un cas où les mêmes matières premières sont insérées dans des
ordres différents : l'objet final reste identique au bit près. Les
marchandises sont donc parcourues dans un ordre stable, comme pour le
commerce ; l'ordre d'insertion du panier ne choisit pas l'ordre d'addition
des flottants. Aucun aléa n'entre dans la fabrication.

### SC10 — Les invariants existants restent intacts

```bash
py -m pytest sim/tests/ viewer/tests/ -q
```

- vert, et la liste des tests en échec est **vide**, comparée à celle de
  `master` plutôt que supposée ;
- `test_chaque_gisement_produit_sa_ressource`, `test_gisement_incomplet_ignore`,
  `test_ressource_inconnue_acceptee`, `test_sans_bras_pas_de_minerai`,
  `test_richesse_ordre_les_debits`, `test_extraction_suit_les_mineurs`,
  `test_cellules_minieres_produisent_moins_et_portent_moins_de_monde`, et tous les
  contrôles de `sim/tests/test_commerce.py`, `sim/tests/test_survie.py`,
  `sim/tests/test_write_coverage.py` et `sim/tests/test_province.py` restent
  verts **sans modification** ;
- `test_no_hardcoded_numeric_literals` reste vert : aucun littéral numérique
  hors 0, 1 et −1 dans le corps des fonctions ajoutées ;
- `test_aucune_constante_terminale` reste vert : `TAUX_FABRICATION_PAR_TICK`
  et `RENDEMENT_FABRICATION` sont lues par `fabrication_kg` ;
- `test_le_moteur_ne_lie_aucune_constante_par_valeur` reste vert : aucun
  `from sim.constants import ...` n'apparaît dans `sim/engine.py` ;
- `test_chaque_constante_du_moteur_change_le_monde` reste vert **sans que
  `_MondeEpreuve` soit modifiée** — voir § 2 pour la raison exacte ;
- `test_write_coverage_counter_etendu` reste vert : ce lot n'ajoute aucun
  champ à une entité de `sim.model` ;
- aucune instruction `global` dans `sim/engine.py` ;
- le nombre de tests collectés est strictement supérieur à celui de
  `master`.

```bash
git diff master -- sim/tests/ | grep "^-" | grep -v "^---"
```

Cette seconde commande ne sort **rien** : aucune ligne retirée d'aucun
fichier de test, donc aucun test existant modifié, renommé, supprimé ni
relâché.

## Hors périmètre

- `sim/MODELE.md` — la mise à jour après fusion est une dette de l'architecte
  du modèle, pas de l'exécutant ;
- toute recette par ressource (fer → outils, argent → bijou…) : un seul
  objet générique, voir § 1 ;
- tout métier d'artisan, tout bras occupé, toute nouvelle source ou
  répartition de population — y compris la part non agricole que compte le
  lot 047 : ce lot ne la touche pas et n'en crée pas une seconde définition ;
- toute demande, tout prix, tout marché pour l'objet fabriqué : il
  s'accumule sans circuler, exactement comme le minerai avant lui (§ 5) ;
- le transport de l'objet, la mer, le lot 046 ;
- le bourg, la ville, le lot 047 ;
- l'épuisement d'un gisement, le déplacement des mineurs ;
- le schéma du snapshot, sa version, le visualiseur ;
- la calibration d'un test existant après observation, et toute autre
  retouche d'un test existant, quel qu'en soit le motif.
