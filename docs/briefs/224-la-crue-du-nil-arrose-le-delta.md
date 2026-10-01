# Lot #224 — La crue du Nil arrose le delta
Jalon : J2 · Machine : vps · Taille prévue : 260 lignes

## But
Le monde de 1400 rend au delta du Nil sa fertilité par sa cause, la crue du
fleuve : la cellule que le Nil traverse s'amorce plus dense que la médiane du
monde, alors que le désert occidental et Suez restent vides (CAP.md, jalon 2 :
« les régions denses de 1400 […] delta du Nil sont plus denses que la
médiane, le désert plus vide »).

## Règle du monde
Un champ boit la pluie qui tombe dessus **et** l'eau que le fleuve y dépose.
Là où le Nil passe, sa crue submerge les terres chaque année : c'est de l'eau
pour les champs, au même titre que la pluie, et elle s'y ajoute. Le rendement
lit donc `facteur_eau(pluie + crue)` : une seule courbe, une seule formule de
production, aucune exception égyptienne, aucun plancher relevé. Une cellule
que le fleuve ne traverse pas reçoit une crue de **zéro**, qui est une mesure,
et son rendement ne bouge pas d'un bit.

Cela découle de quatre sections de `jeu/sim/MODELE.md` :

- « Le rendement agricole et sa variabilité » : il n'y a qu'une formule de
  production ; le plafond de survie et l'amorçage la lisent. La crue y entre
  **dans l'argument** du facteur d'eau, pas comme un facteur de plus, et elle
  est refusée si elle manque, comme la pluie ;
- « Population initiale par cellule » : la population amorcée est une part de
  `population_soutenable_de`. Aucune ligne de l'amorçage ne change : elle
  suit ;
- « Le cours du Nil, vue dérivée » (lot #223, sur la base) : une cellule est
  traversée si un point du cours lui appartient. Ce lot branche cette vue sur
  la carte **à sa lecture**, exactement comme la pluie ; le tick lit la carte,
  jamais la vue ;
- « La pluie de 1400, vue dérivée » : elle dit aujourd'hui que le Nil est vidé
  et que « seul le futur mécanisme du fleuve pourra la réparer ». Ce lot est
  ce mécanisme ; la pluie elle-même n'est pas touchée (la pluie n'est toujours
  pas l'eau : l'eau est la pluie plus la crue).

**Niveaux de fidélité.**

- Quelles cellules le Nil traverse : niveau 1 pour les points, niveau 2 pour
  leur attribution (lot #223, inchangé).
- `CRUE_EQUIVALENT_PLUIE_MM` : **niveau 2**, plausible, jamais sourcée. Fixée
  ici avant tout code, non réglée après mesure : **600.0** mm par an —
  l'eau qu'une submersion de bassin laisse aux champs, comptée comme une pluie
  qui suffit largement. Elle est **strictement au-dessus** de
  `PLUIE_PLEINE_CULTURE_MM` (400.0) : une cellule traversée a un facteur d'eau
  d'exactement 1, quelle que soit sa pluie.
- La crue est tout ou rien sur la cellule : toute la cellule traversée est
  arrosée, même la part qui, en vrai, est désert au-delà de la vallée. C'est
  une anomalie de niveau 2, déclarée, pas un défaut.

**Faits mesurés sur la base, à connaître** (non recopiés dans `MODELE.md`) :
les onze points du cours tombent dans **une seule** cellule, celle du delta ;
`charger_positions()` porte exactement les cellules de la carte (aucune en
plus, aucune en moins). Mesuré en mémoire avec une crue de 600 mm ajoutée à la
cellule du delta, graine 0 : sa densité passe de 0,35 à 7,06 hab/km² pour une
médiane de 6,32 ; le désert occidental (0,35) et Suez (0,37) ne bougent pas.
La marge du delta sur la médiane est modeste : si SC3 rougit, c'est le code
qu'on regarde, jamais la constante qu'on règle.

### Ce que le codeur écrit

**1. `jeu/sim/constants.py`** — `CRUE_EQUIVALENT_PLUIE_MM = 600.0`, dans le
bloc « Eau dans le rendement », commentée « niveau 2, jamais sourcé ».
`facteur_eau` ne change pas. `SNAPSHOT_SCHEMA_VERSION` reste `"v0a-5"`
(`test_aridite.py` l'exige, et aucune couche n'est ajoutée).

**2. `jeu/sim/world.py`** — `World.lire_carte()` ajoute en mémoire, à chaque
enregistrement de cellule, la clé `"crue_mm_par_an"` : la constante pour une
cellule traversée, `0.0` sinon. Les cellules traversées viennent de
`cellules_traversees(charger_points(), charger_positions(),
charger_latitude_moyenne_fleuve())` de `sim/fleuve.py`, importé **sans être
modifié** (pas de `cours_depuis_monde` : le monde n'existe pas encore à la
lecture de la carte). La constante se lit **par le module à chaque appel**
(`from sim import constants as _constantes`, puis
`_constantes.CRUE_EQUIVALENT_PLUIE_MM`), pour qu'un remplacement en mémoire
l'atteigne (contre-épreuve de SC1). `pluie_mm_par_an` n'est **jamais** écrit
ni modifié par ce code. Le fichier sur le disque ne change pas ; rien n'est
posé sur `Cell`. Le docstring de `lire_carte` dit qu'elle porte la pluie et la
crue.

**3. `jeu/sim/engine.py`** — `CrueInvalideError(ValueError)`, et dans
`_facteur_eau_pour_cellule`, **après** les refus de la pluie existants (qui
restent mot pour mot, pour que `test_aridite.py` lève toujours
`PluieInvalideError`) : lit `raw.get("crue_mm_par_an")` et refuse, en nommant
le `cell_id`, une clé absente ou `None`, un booléen, une valeur non numérique,
non finie ou négative ; `0.0` est accepté. Rend
`_constantes.facteur_eau(float(pluie) + float(crue))`. **Le moteur ne lit
jamais `CRUE_EQUIVALENT_PLUIE_MM` par son nom** : le monde d'épreuve de
`test_write_coverage.py` n'a pas de carte, la constante y serait inerte et
`test_chaque_constante_du_moteur_change_le_monde` rougirait (MODELE.md, « Le
monde d'épreuve, et pourquoi certaines constantes se cachent »). Rien d'autre
ne change dans le moteur : le plafond et l'amorçage suivent par la formule
unique.

**4. `jeu/sim/tests/test_crue.py`** — neuf, les cas du lot (voir Conditions
de succès). Les cellules de référence se dérivent de points écrits dans le
test par `derive_appartenance` avec la projection de
`charger_latitude_moyenne_fleuve()` (motif de `test_fleuve.py`) : le delta
(30,8° N, 31,0° E), le désert occidental (30,9° N, 28,5° E), l'isthme de Suez
(30,45° N, 32,5° E). Aucun `cell_id` écrit. Densité = population / surface ;
médiane dérivée du monde par `statistics.median`. Chaque test imprime ses
compteurs ; un échantillon vide échoue.

**5. `jeu/sim/MODELE.md`** — dans le même mouvement :

- « En une page », étape 4 : la production est multipliée par le
  `facteur_eau` de **l'eau de la cellule, sa pluie plus la crue du fleuve** ;
  le paragraphe d'après dit que la crue, comme la pluie, n'est pas stockée
  sur `Cell` et entre dans la carte à sa lecture. **Aucun nom de fonction
  commençant par `_` n'est ajouté entre accents graves dans la liste
  numérotée** : `test_ordre_du_tick_documente_est_celui_du_code` le lirait
  comme une étape du tick ;
- « Le rendement agricole et sa variabilité » : la formule devient
  `× facteur_eau(pluie_mm_par_an + crue_mm_par_an de la cellule)` ; le
  paragraphe des refus nomme `CrueInvalideError` ; la table du facteur d'eau
  gagne la ligne `CRUE_EQUIVALENT_PLUIE_MM | 600.0 |` avec son sens, et le
  texte dit son niveau 2, pourquoi elle dépasse le seuil haut, et le tout ou
  rien sur la cellule ;
- « La pluie de 1400, vue dérivée » : le dernier paragraphe cesse de dire que
  le Nil est vidé ; il dit que la pluie n'est pas l'eau, et que l'eau du delta
  lui vient de la crue (renvoi à la section du Nil). La phrase « le tick ne la
  lit pas » reste ;
- « Le cours du Nil, vue dérivée » : le dernier paragraphe dit que
  `World.lire_carte` en dérive `crue_mm_par_an` à la lecture et que le moteur
  lit cette valeur dans la carte ; « le tick ne la lit pas » reste vrai et
  reste écrit ; le delta n'y est plus dit vidé.

Aucun nombre mesuré n'y est recopié, aucun `cell_id` n'y est écrit.

## Périmètre
jeu/sim/constants.py
jeu/sim/world.py
jeu/sim/engine.py
jeu/sim/tests/test_crue.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent par `python3 -m pytest jeu/sim/tests/test_crue.py -q -k <nom>`
depuis la racine, sauf mention.

**SC1 — la carte lue porte la crue, et la pluie n'a pas bougé** (`-k carte`).
Sur `World.lire_carte()` : `CRUE_EQUIVALENT_PLUIE_MM >
PLUIE_PLEINE_CULTURE_MM` ; pour chaque enregistrement, `crue_mm_par_an` vaut
la constante si la cellule est dans `cellules_traversees(…)` (calculé dans le
test), `0.0` sinon — `cellules_conformes == len(cellules)`, `> 0` ; le nombre
de cellules à crue non nulle égale le nombre de cellules traversées, au moins
un, strictement moins que toutes ; pour chaque enregistrement,
`pluie_mm_par_an` égale `pluie_de_cellule(cell_id, pluie_depuis_monde(
World.charger(0)))` ; le fichier `data/world-1400.json` sur le disque ne
contient aucune clé `crue_mm_par_an`. Contre-épreuve : avec
`sim.constants.CRUE_EQUIVALENT_PLUIE_MM` remplacé en mémoire par `0.0`
(monkeypatch), `lire_carte()` ne porte plus aucune crue non nulle — la
constante est relue à l'appel.

**SC2 — le moteur refuse une crue absente** (`-k refus`). Sur une copie de
`World.lire_carte()` dont l'enregistrement du delta est altéré — clé retirée,
`None`, `True`, `"crue"`, `NaN`, `inf`, `-1.0` — `World.charger(0,
carte_doc=…)` lève `CrueInvalideError` et le message contient ce `cell_id`.
Contre-épreuve : la même cellule à `0.0` s'amorce sans erreur, et sa pluie
dans `monde.carte` est celle de la carte lue, inchangée.

**SC3 — le delta se remplit, le désert et Suez restent vides** (`-k densite`).
Sur `World.charger(0)` : les trois cellules de référence sont distinctes ; la
densité du delta est **strictement au-dessus** de la médiane ; celles du
désert occidental et de Suez **strictement en dessous**. Contre-épreuve,
exigée par la demande : la carte lue dont **chaque** `crue_mm_par_an` est
forcé à `0.0`, amorcée par `World.charger(0, carte_doc=…)`, donne au delta une
densité **strictement sous** la médiane de ce monde-là — le test l'exige.

**SC4 — une seule formule** (`-k formule`). Pour le delta, le rapport
`population_soutenable_de` avec crue / avec crue forcée à zéro (même carte que
la contre-épreuve de SC3) égale `facteur_eau(pluie + crue) /
facteur_eau(pluie)` à 1e-12 près relatif, et ce rapport est **différent de 1**
(sinon le test ne prouve rien). Contre-épreuve : pour le désert et Suez, les
deux soutenables sont **identiques** au bit près ; et pour chaque cellule du
monde avec crue, `population_soutenable_de × FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK`
égale `_production_du_tick_kg_saison_moyenne(…, rendement_moyen_courant(), …)`
à 1e-9 près relatif — un amorçage qui ajouterait la crue hors de la formule
casserait l'un ou l'autre.

**SC5 — la vue du fleuve n'a qu'un lecteur** (`-k lecteurs`). L'ensemble des
modules de `jeu/sim/` (hors `tests/` et hors `fleuve.py`) dont l'arbre
syntaxique importe `sim.fleuve` est **exactement** `{"world.py"}` : le tick
(`engine.py`) ne lit pas la vue, il lit la carte ; le test imprime les
lecteurs et `modules_parcourus > 0`. Contre-épreuve, dans le même test : le
même détecteur appliqué à une source synthétique `"from sim.fleuve import
charger_points"` la voit comme lectrice.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert, et
`git diff --stat origin/master -- jeu/sim/tests/` ne montre que
`test_crue.py` : `test_aridite.py`, `test_fleuve.py`, `test_pluie.py`,
`test_monde.py`, `test_write_coverage.py` et `test_no_hardcoded.py` sont
intacts. Contre-épreuves : si `lire_carte` ajoutait la crue **dans**
`pluie_mm_par_an`, `python3 -m pytest jeu/sim/tests/test_aridite.py -q -k carte`
rougirait ; si `engine.py` lisait `_constantes.CRUE_EQUIVALENT_PLUIE_MM` par
son nom, `python3 -m pytest jeu/sim/tests/test_write_coverage.py -q -k change_le_monde`
rougirait.

**SC7 — le modèle le dit.** `grep -n "CRUE_EQUIVALENT_PLUIE_MM" jeu/sim/MODELE.md`
rend au moins une ligne dans « Le rendement agricole et sa variabilité » ;
`grep -n "crue_mm_par_an" jeu/sim/MODELE.md` rend une ligne dans la formule ;
la section « En une page » contient « crue » ; dans « La pluie de 1400, vue
dérivée », ni « vide aussi » ni « les **vide** » ne restent ;
`python3 -m pytest jeu/sim/tests/test_monde.py -q -k ordre_du_tick` est vert.
Contre-épreuve : sur le `MODELE.md` de `origin/master`, les deux premières
commandes ne rendent rien.

## Hors périmètre
- Aucune nouvelle couche dans le snapshot : `_COUCHES`, `_alterer` et
  `SNAPSHOT_SCHEMA_VERSION` (`"v0a-5"`) ne changent pas ;
  `jeu/sim/snapshot_export.py` n'est pas touché.
- La vallée au sud du Caire (hors de la carte, déclarée par le lot #223), le
  calendrier de la crue, ses bonnes et mauvaises années, les canaux,
  l'irrigation, les oasis, les autres fleuves : non simulés.
- Toute fraction de cellule arrosée, toute largeur de vallée : la crue est
  tout ou rien sur la cellule traversée.
- `jeu/sim/fleuve.py`, `jeu/sim/pluie.py`, `jeu/sim/aggregation.py`,
  `jeu/data/nil-cours-1400.json`, `jeu/data/pluie-releves-1400.json`,
  `jeu/data/world-1400.json` : inchangés.
- `facteur_eau` et ses trois constantes : inchangés.
- La table de référence des densités de 1400, les royaumes, les villes, la
  carte de départ du joueur : autres lots du jalon 2.
- Les vues (tableau, chronique, relief, Unity) : aucune ne montre la crue.
