# Lot #219 — La table des puissances de l'Ouest se lit et se refuse
Jalon : J2 · Machine : vps · Taille prévue : 295 lignes

## But
Le monde sait lire, dans une table qui cite ses sources, quelles puissances se
partagent l'Ouest au 1er janvier 1400 — îles Britanniques, France, péninsule
Ibérique, Empire — avec leur nature, leur religion et les villes qu'elles
tiennent, et il refuse une table fausse en nommant la ligne et le champ : c'est
la première pierre de « les royaumes entrent dans le monde » (CAP.md, jalon 2),
celle dont la carte de 1400 et le choix de la terre de départ auront besoin.

## Règle du monde
En 1400, une terre de l'Ouest relève d'une **puissance** : un royaume, une
république, une Église ou un ordre, d'une religion donnée. Ce qu'on sait
sûrement d'une puissance, c'est qu'elle tient certaines villes : la table les
note comme **points d'ancrage** — un lieu réel, en latitude et longitude, que la
puissance tenait au 1er janvier 1400, avec la source publique qui l'atteste.
Une ancre est un point, pas une frontière : dire quelles cellules relèvent de
quelle puissance est le travail d'un lot suivant.

Cela découle de `jeu/sim/MODELE.md`, section « La province dérivée et ses
centres » : provenance déclarée (« Provenance »), points en degrés et non en
cellules, **refus de deviner** (« Refus de deviner »), et le motif de
« Ce que l'agrégation ne fait pas » — rien n'est posé sur `Cell`, rien n'entre
dans `sim.model`, le tick ne lit pas la table. `cell_id` reste la seule clé
spatiale : la table ne stocke ni `cell_id`, ni province, ni frontière.

**Niveaux de fidélité.**

- **Niveau 1** (obligatoire, sources publiques : Wikipédia, atlas,
  encyclopédies) : l'existence de chaque puissance au 1er janvier 1400, sa
  nature, sa religion, et l'appartenance de chaque ancre à sa puissance ce
  jour-là.
- **Niveau 3, pas simulé** : le Grand Schisme (Rome contre Avignon) — les deux
  obédiences sont « catholique » ; les maisons, les suzerainetés et les
  hommages — les grands fiefs de France et les principautés laïques de
  l'Empire n'ont pas de ligne à eux : **leurs villes sont des ancres de la
  couronne ou de l'Empire**, leurs maisons viendront plus tard.

**Une ancre sans source ne s'écrit pas.** Une terre disputée ou plus petite
qu'une cellule (~15 000 km²) n'a pas d'ancre : une ancre de moins vaut mieux
qu'une ancre devinée. Pièges connus, à ne pas ancrer : **Calais** (anglaise,
enclave), **Avignon** et le Comtat (pontificaux), **Évreux** (navarraise
jusqu'en 1404), **Berwick** (disputée), la **ville de Cologne** (affranchie de
son archevêque depuis Worringen, 1288), toute ville libre d'Empire.

### Ce que le codeur écrit

**1. `jeu/data/puissances-1400.json`** (≤ 50 lignes, une ligne par entrée) :

```json
{
  "description": "Puissances de l'Ouest au 1er janvier 1400 et leurs points d'ancrage.",
  "date": "1400-01-01",
  "fidelite": "Niveau 1 … ; le Grand Schisme, les maisons et les suzerainetés ne sont pas simulés.",
  "puissances": [
    { "id": 1, "nom": "Angleterre", "nature": "royaume", "religion": "catholique" }
  ],
  "ancres": [
    { "id": 1, "puissance": 1, "nom": "Londres", "lat": 51.51, "lon": -0.13, "source": "…" }
  ]
}
```

(gabarit, pas donnée.)

- **Puissances, entre 12 et 16**, identifiants entiers depuis 1. Obligatoires,
  sous **ces noms exacts** (le test les lit) : `Angleterre`, `Écosse`,
  `France`, `Portugal`, `Castille`, `Aragon`, `Navarre`, `Grenade`
  (musulmane), `Saint-Empire`, `Bohême` ; plus **un archevêché électeur**
  (nature `Église` ; Trèves conseillé, ancré à Trèves ou Coblence) et **la
  Confédération des cantons suisses** (nature `république`, ancrée à Berne ou
  Lucerne ; une ville libre est plus petite qu'une cellule, elle n'aurait pas
  d'ancre). Natures, liste fermée : `royaume`, `république`, `Église`,
  `ordre`. Religions, liste fermée : `catholique`, `orthodoxe`, `musulmane`.
  Grenade est `royaume` (le royaume nasride) ; le `Saint-Empire` est
  `royaume` — son chef en 1400, Venceslas, est roi des Romains, jamais
  couronné empereur ; la liste ne s'élargit pas pour lui.
- **Ancres, entre 20 et 30**, identifiants entiers depuis 1 ; `puissance` est
  l'`id` d'une puissance ; `lat`, `lon` en degrés décimaux WGS84, ceux de la
  ville. Au moins : pour l'Angleterre, Londres, **Bordeaux** (Guyenne) et
  **Dublin** (seigneurie d'Irlande) ; pour la France, Paris et une ville de
  chacun de ces grands fiefs : Bourgogne (Dijon), Bretagne, Flandre ; pour le
  Saint-Empire, trois principautés laïques (par exemple Vienne, Munich,
  Heidelberg) ; au moins une ancre pour chaque autre puissance.
- **`source`** nomme la source publique qui atteste l'appartenance en 1400,
  par exemple « Wikipédia, article Guyenne : possession du roi d'Angleterre
  de 1152 à 1453 ».
- Toute ancre tombe dans l'étendue de la carte : entre les latitudes et les
  longitudes extrêmes des centroïdes de `data/world-1400.json`.

**2. `jeu/sim/puissances.py`** (≤ 125 lignes), chargeur seul, sur le modèle de
`sim/pluie.py` (clés du document en constantes de module) :

- `PuissanceInvalide(ValueError)` ; `NATURES` et `RELIGIONS`, deux
  `frozenset` de chaînes ;
- `Puissance` (`id`, `nom`, `nature`, `religion`), `Ancre` (`id`,
  `puissance`, `nom`, `lat`, `lon`, `source`) et `TableDesPuissances`
  (`date`, `puissances`, `ancres` : tuples triés par `id`), dataclasses
  figées héritant de `_NoBadSpatialField` ;
- `charger_table(path=None)` lit le fichier et **refuse** par
  `PuissanceInvalide`, avec un message « puissance <id>, champ <champ> : … »
  ou « ancre <id>, champ <champ> : … » (ou « champ <clé> : … » pour le
  document) : une `date` autre que `"1400-01-01"` ; une liste `puissances` ou
  `ancres` vide ou absente ; un `id` non entier, **booléen** ou dupliqué
  (dans chaque liste) ; un `nom` ou une `source` absents ou faits de blancs ;
  une `nature` ou une `religion` hors liste ; une `puissance` d'ancre non
  entière, **booléenne** (`true == 1` en Python : sans ce refus, `true` viserait
  la puissance 1) ou inconnue ; une `lat` ou une `lon` non numérique,
  booléenne ou non finie ; enfin une puissance qu'aucune ancre ne vise
  (« puissance <id>, champ ancres : aucune ancre »).

Aucun littéral numérique autre que 0, 1, −1 dans un corps de fonction
(`test_no_hardcoded.py` inspecte tout module neuf de `sim/`).

**3. `jeu/sim/tests/test_puissances.py`** (≤ 120 lignes). Les altérations sont
une liste paramétrée : la vraie table est relue en JSON, altérée une seule
fois, réécrite dans `tmp_path`, puis rechargée.

## Périmètre
jeu/data/puissances-1400.json
jeu/sim/puissances.py
jeu/sim/tests/test_puissances.py

## Conditions de succès
Toutes se jouent par `python3 -m pytest jeu/sim/tests/test_puissances.py -q -k <nom>`
depuis la racine ; chaque test imprime ses compteurs, et un échantillon vide
échoue.

**SC1 — la vraie table se lit** (`-k lecture`). `charger_table()` rend
`puissances_lues` et `ancres_lues` **égaux au nombre de lignes du fichier**
(relu en JSON brut par le test : rien n'est écarté en silence), entre 12 et 16
et entre 20 et 30 ; `puissances_sans_ancre == 0` (une mesure). Contre-épreuve :
la table réécrite **sans altération** se recharge et donne la même
`TableDesPuissances` — sinon les refus de SC2 pourraient venir de la réécriture.

**SC2 — une seule altération à la fois est refusée** (`-k refus`). Chaque cas
lève `PuissanceInvalide`, et le message contient la ligne visée
(« puissance <id> » ou « ancre <id> ») et le champ : `nature` à `"duché"` ;
`religion` à `"protestante"` ; `source` retirée ; `source` à `"   "` ; `nom`
d'ancre à `"  "` ; `puissance` d'ancre au plus grand `id` + 1 ; `puissance`
d'ancre à `true` ; toutes les ancres de la Navarre retirées (message :
l'`id` de la Navarre et `ancres`) ; `id` de puissance dupliqué ; `id` de
puissance à `true` ; `id` d'ancre dupliqué ; `id` d'ancre à `false` ; `lat` en
chaîne ; `lon` à `NaN` ; `lat` à `Infinity` ; `date` à `"1453-05-29"` ;
`ancres` vide. Le nombre de cas joués est compté et doit égaler la longueur de
la liste (> 0).

**SC3 — les puissances connues sont justes** (`-k connues`). Une fonction du
test vérifie, sur une table chargée : les dix noms obligatoires présents ;
`Grenade` musulmane, les neuf autres catholiques ; au moins une `Église` et au
moins une `république` ; l'Angleterre ancrée à Londres, Bordeaux et Dublin.
Vraie sur la vraie table. Contre-épreuve : la même fonction rend faux sur la
table réécrite avec Grenade `catholique`, puis sur la table sans l'ancre de
Bordeaux.

**SC4 — pas d'ancre hors carte ni sur une terre exclue** (`-k ancrage`).
L'étendue de la carte est dérivée des centroïdes par `charger_positions()` de
`sim/aggregation.py` ; `ancres_hors_carte == 0`. Calais (50,95° N ; 1,86° E)
et Avignon (43,95° N ; 4,81° E), écrits dans le test : aucune ancre à moins de
0,2° en latitude **et** en longitude de l'un d'eux, `ancres_sur_terre_exclue
== 0`. Contre-épreuves : une ancre ajoutée à Calais pour l'Angleterre compte
1 ; la table où l'ancre de Paris a `lat` et `lon` échangées compte
`ancres_hors_carte == 1`.

**SC5 — un chargeur que personne ne lit encore.**
`grep -rl --include='*.py' puissances jeu/sim | grep -v /tests/` rend
exactement `jeu/sim/puissances.py`. Contre-épreuve : une ligne
`import sim.puissances` dans `jeu/sim/engine.py` y ajouterait ce fichier.

**SC6 — rien d'existant ne bouge.** `python3 -m pytest jeu -q` est vert sans
qu'aucun test existant ne soit modifié ; `test_no_hardcoded.py` inspecte
`puissances.py`. Contre-épreuve : un littéral `90` glissé dans un corps de
fonction de `puissances.py` rend `test_no_hardcoded` rouge.

## Hors périmètre
- Aucune vue : ni cellule attribuée à une puissance, ni frontière, ni carte,
  ni fiche ; le tick, l'amorçage et le service ne lisent pas la table.
- Les puissances hors de l'Ouest (Italie, Scandinavie, Europe centrale et
  orientale, Balkans, Orient, Afrique du Nord hors Grenade) : d'autres lots.
- Les maisons, les grands fiefs et les principautés comme puissances, les
  liens de suzeraineté et d'hommage, les dynasties.
- Le Grand Schisme, les villes libres, les terres disputées.
- `jeu/sim/MODELE.md` : sa section vient avec le lot qui fait entrer les
  puissances dans les cellules ; `jeu/data/world-1400.json`,
  `jeu/data/province-centres-1400.json`, `sim/aggregation.py`, `sim/model.py`
  et `sim/pluie.py` ne changent pas.
