# Lot #125 — Un lieu porte une identité stable
Jalon : J3 · Machine : vps · Taille prévue : 190 lignes

## But
Le monde sait retrouver un lieu par son couple (`cell_id`, `rang`), refuse
tout couple qui ne désigne aucun lieu, et prouve que ce couple désigne le même
lieu quels que soient le jour du monde, la graine et l'ordre des cellules. Le
maître de chaque lieu (le pas suivant du jalon 3, CAP.md : « chaque lieu a un
maître ») pourra donc s'y accrocher sans qu'un tick le détache.

## Règle du monde
Le lot #234 a découpé chaque cellule en lieux, d'identité (`cell_id`, `rang`),
le rang 0 étant le bourg. Ce lot ne change pas ce découpage : il rend
l'identité **adressable** et prouve qu'elle est **stable**.

- **Retrouver un lieu.** Un lieu se retrouve par son couple, dans le monde,
  en ne découpant que sa cellule. `cell_id` doit être une cellule du monde,
  `rang` un entier de 0 à `n − 1` (n = nombre de lieux de cette cellule). Un
  rang négatif est **refusé**, jamais lu à la manière de Python (`lieux[-1]`
  rendrait en silence le dernier lieu : c'est la contre-épreuve de SC1).
- **Refus.** Deux cas distincts, parce qu'un appelant futur (le service) les
  traitera différemment :
  - un couple **mal formé** — `cell_id` ou `rang` booléen, textuel, flottant
    (même `2.0`), `None` — lève `LieuxInvalides` ;
  - un couple **bien formé qui ne désigne rien** — cellule absente du monde,
    rang négatif ou ≥ n — lève `LieuInconnu`, sous-classe de `LieuxInvalides`.
  Dans les deux cas le message nomme le `cell_id` et le `rang` reçus. Une
  surface de cellule invalide reste refusée par `lieux_de_cellule`, comme au
  lot #234. Rien n'est deviné, rien n'est ramené dans l'intervalle.
- **Stable, et pourquoi.** Le découpage ne lit que `area_km2` et
  `SURFACE_KM2_PAR_LIEU`. Le tick ne modifie pas la surface, l'amorçage la lit
  sur la carte figée sans tirage, et la vue trie par `cell_id` : un couple
  désigne donc le même lieu, de même surface, **à tout tick, pour toute
  graine, dans tout ordre de `world.cells`**. Ce lot le mesure au lieu de le
  supposer.
- **Ce qui la change.** Changer la surface d'une cellule sur la carte, ou
  `SURFACE_KM2_PAR_LIEU`, renumérote les lieux de la cellule. C'est un
  changement du monde : il passe par `MODELE.md`, et tout ce qui s'accrochera
  à un lieu (le maître, demain) devra le suivre. Il n'y a pas de numéro global
  de lieu : un tel numéro dépendrait de l'ordre d'énumération des cellules,
  que rien ne fixe (contre-épreuve de SC4).

Cela découle de `jeu/sim/MODELE.md` :

- « Les lieux d'une cellule, vue dérivée » : l'identité (`cell_id`, `rang`),
  « aucun identifiant spatial supplémentaire n'est stocké », « le tick ne la
  lit pas » — ce lot n'y ajoute aucun champ et ne branche rien sur le tick ;
- « La province dérivée et ses centres », « Ce que l'agrégation ne fait pas —
  et le motif que toute vue recopie » : pure, hors de `sim.model`, refuse de
  deviner ;
- « Le moteur sans état caché » : la constante se relit par son module à
  chaque appel.

**Niveau de fidélité.** Inchangé : le nombre de lieux et leurs surfaces sont
de **niveau 2**. L'identité est une propriété de construction, pas une
donnée historique : aucun niveau 1 n'entre. **Niveau 3, pas simulé** : la
forme, la position, les noms des lieux ; aucun lieu n'a d'habitant ni de
maître dans ce lot.

### Ce que le codeur écrit

**1. `jeu/sim/lieux.py`** — ajouts seulement, rien de ce qui existe ne
change :

- `LieuInconnu(LieuxInvalides)` ;
- `lieu_du_monde(world, cell_id, rang) -> Lieu` : pure, lecture seule. Refuse
  d'abord la forme (`isinstance(x, bool)` ou `not isinstance(x, int)` pour
  chacun des deux → `LieuxInvalides`), puis l'absence de la cellule dans
  `world.cells` (→ `LieuInconnu`), puis découpe **cette seule cellule** par
  `lieux_de_cellule(cell_id, getattr(cellule, "area_km2", None))`, puis
  refuse `rang < 0` ou `rang >= len(lieux)` (→ `LieuInconnu`) avant
  d'indexer. Message : contient `cell_id` et `rang` tels que reçus (`repr`).

Aucun littéral numérique autre que 0, 1 et −1 dans un corps de fonction
(`test_no_hardcoded.py` inspecte le module). Aucune autre fonction publique.

**2. `jeu/sim/tests/test_lieux.py`** — les cas des conditions ci-dessous,
**ajoutés à la fin** ; aucune ligne existante n'est modifiée ni retirée.

**3. `jeu/sim/MODELE.md`** — dans la section « Les lieux d'une cellule, vue
dérivée », une sous-section « ### L'identité d'un lieu, et ce qui la change »,
à la fin de la section : un lieu se retrouve par son couple avec
`lieu_du_monde` ; les deux refus (`LieuxInvalides` pour un couple mal formé,
`LieuInconnu` pour un couple qui ne désigne rien, rang négatif compris) ; la
stabilité (à tout tick, pour toute graine, dans tout ordre des cellules) et sa
raison ; ce qui la change (la surface de la carte, `SURFACE_KM2_PAR_LIEU`), et
qu'un tel changement est un changement du monde que devra suivre tout ce qui
s'accroche à un lieu ; pas de numéro global de lieu, et pourquoi. Aucun
compte mesuré n'y est recopié.

## Périmètre
jeu/sim/lieux.py
jeu/sim/tests/test_lieux.py
jeu/sim/MODELE.md

## Conditions de succès
Toutes se jouent depuis la racine par
`python3 -m pytest jeu/sim/tests/test_lieux.py -q -s -k <nom>` ; chaque test
imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` n'est
écrit en dur dans un test sur le vrai monde : les cellules se choisissent par
leurs propriétés (surface, nombre de lieux), lues du monde.

**SC1 — chaque lieu se retrouve par son couple** (`-k retrouve`). Sur
`World.charger(0)` : pour chaque lieu de `lieux_depuis_monde(monde)`,
`lieu_du_monde(monde, lieu.cell_id, lieu.rang) == lieu` ; compteur
`lieux_retrouvés` égal au nombre total de lieux (> 0). Contre-épreuve, dans le
même test, sur une cellule choisie parce qu'elle a au moins deux lieux :
`lieu_du_monde(monde, c, -1)` et `lieu_du_monde(monde, c, n)` lèvent
`LieuInconnu`, alors que l'indexation naïve `lieux_depuis_monde(monde)[c][-1]`
rend bien un lieu — la garde du rang négatif n'est pas décorative.

**SC2 — un couple invalide est refusé, jamais deviné** (`-k refus_du_couple`).
Sur `World.charger(0)`, avec `c` la cellule de plus petit `cell_id` :
- `LieuxInvalides` (et **pas** `LieuInconnu`) pour chacun des couples
  `(True, 0)`, `(c, True)`, `(c, False)`, `(str(c), 0)`, `(c, "0")`,
  `(float(c), 0)`, `(c, 0.0)`, `(None, 0)`, `(c, None)` ;
- `LieuInconnu` pour `(max(monde.cells) + 1, 0)` et `(c, -1)` ;
- chaque message contient le `repr` du `cell_id` et du `rang` reçus ;
compteur `refus_observés` égal à la longueur des deux listes (> 0). Sur une
copie profonde du monde où `area_km2` de `c` vaut `None`,
`lieu_du_monde(copie, c, 0)` lève `LieuxInvalides` qui nomme `c`.
Contre-épreuve, dans le même test : `lieu_du_monde(monde, c, 0)` passe et rend
un bourg ; et `(True, 0)` lève `LieuxInvalides` et non `LieuInconnu` : la
forme est jugée avant la recherche, un booléen n'est jamais pris pour un
numéro de cellule.

**SC3 — le temps ne détache pas un lieu** (`-k tick`). Sur
`World.charger(0)`, vue `avant` ; puis 30 ticks par
`tick(monde, random.Random(0), numero_tick=i)` ; vue `après`. Exigé :
`après == avant`, et au moins une cellule a changé de population pendant ces
ticks (compteur `cellules_changées` > 0 : le monde a vraiment vécu).
Contre-épreuve, dans le même test : sur une copie profonde du monde joué, la
surface de la plus grande cellule est divisée par deux (ce que ferait un tick
qui rognerait la terre) ; la même comparaison trouve alors exactement une
cellule dont les lieux diffèrent (compteur `cellules_détachées` = 1).

**SC4 — ni la graine ni l'ordre ne changent l'identité** (`-k graine`).
`lieux_depuis_monde(World.charger(0)) == lieux_depuis_monde(World.charger(1))`,
alors que les populations des deux mondes diffèrent sur au moins une cellule
(compteur imprimé, > 0). Puis, sur une copie du monde de graine 0 dont
`cells` est reconstruit dans l'ordre inverse des clés : même vue, mêmes clés
dans le même ordre, et `lieu_du_monde` rend le même lieu pour chaque couple.
Contre-épreuve, dans le même test : un « numéro global » calculé par
énumération de `world.cells` (position du lieu dans l'aplatissement des lieux
cellule après cellule, dans l'ordre d'insertion) diffère entre les deux ordres
pour au moins un lieu (compteur `numéros_globaux_déplacés` > 0) — c'est
pourquoi l'identité est un couple et pas un numéro.

**SC5 — la constante renumérote, et le test le voit** (`-k renumerote`).
Sur `World.charger(0)`, une cellule choisie parce qu'elle a au moins trois
lieux, avec `n` son nombre de lieux : `lieu_du_monde(monde, c, n - 1)` passe ;
puis, avec `monkeypatch.setattr` qui double
`sim.constants.SURFACE_KM2_PAR_LIEU`, le même couple lève `LieuInconnu` et le
nombre de lieux de `c` a strictement baissé (compteurs imprimés). C'est la limite déclarée de la
stabilité : elle tient tant que la carte et la constante tiennent.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert.
`git diff origin/master -- jeu/sim/tests/test_lieux.py | grep -E '^-[^-]'` ne
rend rien (le lot n'a fait qu'ajouter), et
`git diff --name-only origin/master -- jeu/sim/tests | grep -v test_lieux.py`
ne rend rien. La commande de SC5 du lot #234,
`grep -rlE "sim\.lieux|from sim import lieux" jeu/sim --include=*.py | grep -v -e "sim/lieux.py" -e "sim/tests/"`,
ne rend toujours rien : le tick ne lit pas la vue. Contre-épreuve : un
littéral `2` glissé dans le corps de `lieu_du_monde` rend
`test_no_hardcoded` rouge.

**SC7 — le modèle le dit.**
`grep -n "^### L'identité d'un lieu, et ce qui la change" jeu/sim/MODELE.md`
rend une ligne, placée après `^## Les lieux d'une cellule, vue dérivée` et
avant la section `^## ` suivante ; cette sous-section contient
`lieu_du_monde`, `LieuInconnu`, `SURFACE_KM2_PAR_LIEU` et « rang négatif ».
Contre-épreuve : sur la base, avant le lot, la commande ne rend rien.

## Hors périmètre
- Le maître d'un lieu, son suzerain, le prélèvement, le transport à
  l'intérieur de la cellule : les lots suivants du jalon 3.
- Le service : `/lieu?cell=` continue de rendre une cellule ; aucune route ne
  sert un lieu par son couple dans ce lot, et `sim/service.py` ne change pas.
  Unity, le snapshot, la chronique et le tableau ne montrent pas les lieux.
- Toute forme textuelle ou numéro global du lieu (`lieu_id`, `"412:3"`…) :
  l'identité reste le couple.
- Le découpage lui-même (`lieux_de_cellule`, `lieux_par_cellule`,
  `lieux_depuis_monde`, `Lieu`, `SURFACE_KM2_PAR_LIEU`) : inchangé.
- La population, les stocks et la production par lieu ; le tick, l'amorçage,
  `sim/model.py`, `sim/world.py`, `sim/engine.py`, `sim/constants.py`,
  `jeu/data/` : aucun ne change.
- La forme, la position, les frontières et les noms des lieux ; tout lieu
  historique nommé.
