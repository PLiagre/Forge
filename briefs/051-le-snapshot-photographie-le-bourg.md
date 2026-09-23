# Brief 051 — Le snapshot photographie le bourg

## But

Faire porter à chaque cellule du snapshot (`sim/snapshot_export.py`) la
répartition bourg / campagne que le lot 047 sait déjà calculer, exactement
comme le snapshot porte déjà la province de chaque cellule. Après ce lot, la
photographie du monde dit combien d'habitants d'une cellule sont du bourg et
combien sont des champs ; avant, cette donnée existe dans le moteur mais
n'atteint jamais un fichier.

Ce lot ne crée **aucun mécanisme** et ne calcule rien de nouveau : il **lit**
`sim.aggregation.bourg_depuis_monde` (et les consultations qui vont avec) et
**joint** le résultat au document déjà produit, comme le fait déjà le champ
`province`. Si après ce lot `py -m sim` ou `py -m sim --ticks 365 --seed 0
--json` rend un résultat différent, le lot est faux — seul le document de
snapshot change.

Ce qui rend ce lot caduc : si `sim/snapshot_export.py` joint déjà une
répartition bourg / campagne par cellule. Ce qui le rend bloqué : si
`sim.aggregation` ne porte plus `bourg_depuis_monde` ou l'équivalent que le
lot 047 a livré.

```bash
grep -n "bourg" sim/snapshot_export.py
grep -n "bourg_depuis_monde\|RepartitionBourg" sim/aggregation.py
py -m sim --ticks 0 --seed 0 --snapshot-json /tmp/monde.json && grep -c '"bourg"' /tmp/monde.json
```

## Règle du monde

Ce lot n'ajoute aucune règle : la règle qu'il exporte est déjà écrite dans
[`sim/MODELE.md`](../sim/MODELE.md) § « Ce qu'est une ville, à l'échelle
d'une cellule », sous-section « La décision : B » — *« Le bourg d'une
cellule est la part de ses habitants qui ne tire pas sa nourriture de ses
champs »* — et livrée par le lot 047 dans `sim/aggregation.py`
(`RepartitionBourg`, `bourg_depuis_monde`). Ce brief se contente de la
rendre lisible depuis un fichier, au même titre que la province l'est déjà.

**Fidélité niveau 2**, par transitivité avec le lot 047 : la part non
agricole qu'exporte ce lot est plausible, générée, jamais sourcée ; ce lot
n'y ajoute et n'en retranche rien.

### La jointure, en une ligne

Pour chaque cellule déjà présente dans `doc["cells"]`, ajouter :

```
cell["bourg"] = {
    "habitants_du_bourg": <int>,
    "habitants_des_champs": <int>,
}
```

Les deux valeurs sont celles que rend `sim.aggregation.bourg_depuis_monde(world)`
pour le `cell_id` de la cellule (via `repartition_bourg_de_cellule_consultation`
ou une itération équivalente) — jamais une seconde formule. Les noms des
deux clés reprennent tels quels les champs de `RepartitionBourg` : aucun
second vocabulaire pour la même grandeur.

Il n'y a pas de cas « cellule sans bourg » à refuser : `bourg_depuis_monde`
rend un enregistrement pour **chaque** cellule de `world.cells` (le bourg
vaut alors zéro habitant, une mesure réelle, pas une absence — voir SC4 et
SC6 du lot 047). La jointure ne peut donc pas lever l'équivalent de
`PositionCelluleInconnue` : il n'y a rien à refuser de deviner ici.

### Le schéma se ferme, et sa version change

`bourg` est un nouveau champ du contrat de cellule : c'est un changement de
schéma, pas une extension silencieuse. `SNAPSHOT_SCHEMA_VERSION` passe de
`"v0a-3"` à `"v0a-4"` dans `sim/constants.py`, et le docstring de
`sim/snapshot_export.py` (qui cite le numéro de schéma en tête de fichier)
suit. C'est la même convention que la précédente révision de schéma a déjà
suivie : un changement de la forme d'une cellule bouge le numéro, jamais son
contenu en silence.

### Ce qui se refuse plutôt que se deviner

- aucune seconde implémentation de la part non agricole : ce module
  **importe** `bourg_depuis_monde` (ou l'équivalent) de `sim.aggregation` et
  ne recopie ni `part_miniere_de`, ni les facteurs de richesse ;
- aucun seuil, aucun drapeau « ceci est une ville » : le document rapporte
  les deux nombres, il ne les interprète pas — l'interprétation, si elle
  vient un jour, est un lot de vue (052), pas celui-ci ;
- aucune donnée de carte nouvelle n'est lue, et aucune constante n'est
  introduite au-delà du numéro de schéma (qui est une chaîne, pas un nombre
  magique).

### La chronique suit le bourg d'un instant à l'autre

La chronique découpe chaque photographie en un décor, écrit une fois, et
des champs mobiles, relus à chaque instant. Le bourg se dérive de la
population, qui bouge : il est donc mobile. Laissé dans le décor, il
figerait la répartition de t0 sur toute la chronique — une vue qui
montrerait autre chose que ce que le moteur joue (mode de défaillance 4).

`vues/chronique/tests/test_chronique.py` le mesure déjà, sans qu'on le
lui déclare : il fait tourner le moteur, regarde quels champs bougent, et
rougit si la chronique en découpe un autre ensemble. C'est ce contrôle qui
a arrêté la première livraison de ce lot, et c'est pour lui que le
périmètre s'étend à un fichier de la chronique, et à ce seul fichier.

La chronique lit ses champs mobiles sur les cellules du monde. Le bourg
n'y est pas : il se calcule. `_image_du_monde` le lit donc par la même
fonction que la jointure du snapshot, `bourg_depuis_monde`, et par
aucune autre — deux calculs du même nombre finissent par diverger.

### Où ça se raccorde, et où ça s'arrête

`sim/snapshot_export.py` appelle déjà `agregat_depuis_monde` pour joindre la
province ; il appelle désormais aussi `bourg_depuis_monde` pour joindre le
bourg, de la même façon, dans la même boucle. `sim/aggregation.py`,
`sim/engine.py`, `sim/model.py`, `sim/world.py` ne sont pas touchés : ce
lot ne lit rien de plus que ce que 047 a déjà rendu disponible, et
n'écrit rien sur les cellules du monde. Le visualiseur ne fait pas partie
de ce lot — c'est le 052, qui **dépend** de celui-ci et se déclare bloqué
tant que `bourg` n'apparaît pas dans le snapshot.

## Périmètre

En écriture : `sim/snapshot_export.py` (la jointure et le docstring de
version), `sim/constants.py` (uniquement la ligne
`SNAPSHOT_SCHEMA_VERSION`), et `sim/tests/test_monde.py` pour y **ajouter**
des cas — c'est le fichier qui porte déjà le schéma fermé du snapshot
(`_CELL_KEYS`, `test_schema_ferme_et_couches`,
`test_province_recalculee_pas_stockee`). Aucun test déjà vert n'est
modifié ; `_CELL_KEYS` s'étend avec `"bourg"`, exactement comme il porte
déjà `"province"`.

En écriture aussi : `vues/chronique/capture.py`, pour deux changements et
rien d'autre. `"bourg"` entre dans `CHAMPS_MOBILES`, et `_image_du_monde`
lit ce champ par `bourg_depuis_monde`, la fonction que la jointure du
snapshot appelle déjà, jamais par une seconde formule.

Tout autre chemin est interdit, nommément : `sim/MODELE.md`,
`sim/engine.py`, `sim/model.py`, `sim/aggregation.py`, `sim/world.py`,
`sim/__main__.py`, les autres fichiers de `sim/tests/` — dont
`test_province.py`, `test_write_coverage.py` et `test_no_hardcoded.py` —,
la carte figée, `vues/tableau/` en entier, le reste de `vues/chronique/` —
dont `vues/chronique/tests/test_chronique.py`, qui ne se modifie pas —, les
briefs 044, 046 et 047, et ce brief.

## Conditions de succès

Les comparaisons « avant / après » se font contre `master` rejoué au
démarrage du lot, jamais contre un nombre recopié d'ici.

**Rejouer `master` se fait en lisant ses objets git, jamais en ajoutant
un worktree.** Le texte d'un fichier se lit par `git show <ref>:<chemin>`,
comme `_texte_master` le fait déjà dans `sim/tests/test_monde.py`. Quand
il faut exécuter le code de `master` (SC1, SC6), on l'extrait dans un
dossier temporaire par `git archive <ref> sim data`, puis on le
décompresse. L'archive est bornée à `sim/` et `data/` : c'est tout ce
que le moteur lit pour charger le monde et construire un snapshot. Une
archive de l'arbre entier tire les objets LFS de `fabrique/`, hors lot ;
sur la PR 22, le smudge a 404 sur un PNG Unity (contrôle `sim`, run
35094855141). `GIT_LFS_SKIP_SMUDGE=1` n'est pas la prescription : il
contourne le 404 sans borner. `git worktree add` est exclu. Sur la PR
15, les deux tests SC6 qui l'appelaient sont sortis en code 128 sur
GitHub Actions (contrôle `sim`, run 35060735773). Dans le même test,
`git show` passait. Sur la machine de l'atelier, la même commande
passait aussi : la suite y était verte, et la PR ne pouvait pas entrer.

Un appel à `git`, ou à tout autre sous-processus dont un test dépend,
met sa sortie d'erreur dans le message de l'assertion quand il échoue.
Sur la PR 15, le message de git était capturé puis perdu : personne n'a pu
lire pourquoi la commande échouait.

### SC1 — Chaque cellule porte le bourg, recalculé, jamais stocké

Pour **toute** cellule du monde réel chargé, `cell["bourg"]` du document
rendu par `build_snapshot_document` est égal à l'enregistrement que rend
`sim.aggregation.bourg_depuis_monde(world)` pour le même `cell_id` — les deux
champs `habitants_du_bourg` et `habitants_des_champs`, sans arrondi ni
tolérance.

Le dénominateur est le nombre de cellules réellement comparées ; un
échantillon vide échoue.

**Rouge prouvé d'abord** : sur `master` extrait par
`git archive <ref> sim data`, `cell["bourg"]` lève `KeyError`.

### SC2 — Le schéma reste fermé, et sa version a changé

`sim/tests/test_monde.py::test_schema_ferme_et_couches`, **non modifié**,
reste vert une fois `"bourg"` ajouté à `_CELL_KEYS` : `set(doc["cells"][0])
== _CELL_KEYS` passe, `doc["schema_version"] == SNAPSHOT_SCHEMA_VERSION`
passe.

`SNAPSHOT_SCHEMA_VERSION` vaut `"v0a-4"` après ce lot, comparé à `"v0a-3"`
lu sur `master` — le contrôle compare deux valeurs réellement lues, jamais
une chaîne recopiée ici.

### SC3 — La somme reste exacte dans le document exporté

Pour **toute** cellule du document : `cell["bourg"]["habitants_du_bourg"] +
cell["bourg"]["habitants_des_champs"] == cell["population"]`, à l'entier
près et sans tolérance. Le compteur d'écarts vaut **0**, mesure réelle sur
un dénominateur dérivé du nombre de cellules du document.

### SC4 — L'échantillon exporté n'est jamais vide

Sur le monde réel, le nombre de cellules du document dont
`cell["bourg"]["habitants_du_bourg"] > 0` est **strictement positif**, et
égal au nombre que rend `sim.aggregation.repartitions_avec_bourg` sur le
même monde. Un zéro ici fait échouer le lot : il signifierait que la
jointure a perdu la mesure du lot 047, pas que le monde n'a pas de bourg.

### SC5 — Une seule voie de lecture de la part non agricole

Un contrôle parcourt le code source de `sim/snapshot_export.py` et échoue
si le module référence `part_miniere_de` ou
`facteurs_richesse_extraction`, ou définit localement une fonction dont le
nom normalisé contient `bourg`. La seule façon d'obtenir la donnée est
d'appeler ce que `sim.aggregation` expose déjà.

**Rouge prouvé** en insérant temporairement un appel à `part_miniere_de`
dans une copie du module d'épreuve : le contrôle doit rougir dessus, sinon
il ne protège rien.

### SC6 — Rien d'autre ne change : la seule différence est le bourg et la version

Produire le snapshot du même monde, même graine, même tick, sur `master`
rejoué par `git archive <ref> sim data`, puis après ce lot. Sur le
document « après », retirer la clé `bourg` de chaque cellule et remettre
`schema_version` à la valeur lue sur `master` ; l'empreinte SHA-256 du
document ainsi restauré est **identique** à celle du document « avant ».
C'est le critère qui distingue une jointure d'un mécanisme : s'il
rougit, ce lot a changé autre chose que ce qu'il déclare.

`py -m sim --ticks 365 --seed 0 --json` (le résumé, pas le snapshot) rend
par ailleurs une sortie identique octet pour octet à celle de `master` :
cette commande ne passe jamais par `sim/snapshot_export.py`, et un écart
signalerait une régression sans rapport avec ce lot.

### SC7 — Les invariants existants restent intacts, et la suite reste verte

```bash
python3 -m pytest sim/tests/ vues/ -q
```

Le contrôle `vues` de la CI joue les trois vues ; celle-ci aussi, pour
qu'une vue que ce lot casse se voie avant la PR, pas après.

- vert, et la liste des tests en échec est **vide**, comparée à celle de
  `master` plutôt que supposée ;
- tous les contrôles déjà présents dans `sim/tests/test_province.py`
  restent verts **sans modification**, y compris les huit
  `test_bourg_*` que le lot 047 a livrés ;
- `sim/tests/test_write_coverage.py` reste vert sans modification : ce lot
  n'ajoute aucun champ à une entité de `sim.model` ;
- `test_no_hardcoded_numeric_literals` reste vert : `"v0a-4"` est une
  chaîne, pas un littéral numérique ;
- `test_aucune_constante_terminale` reste vert : la version de schéma est
  déjà lue par `build_snapshot_document` et par les tests, elle n'est pas
  terminale ;
- deux exécutions de `py -m sim --ticks 0 --seed 0 --snapshot-json …`
  produisent des fichiers strictement identiques ;
- le nombre de tests collectés est au moins celui de `master`.

### SC8 — La chronique suit le bourg, par la fonction de la jointure

```bash
python3 -m pytest vues/chronique/tests/test_chronique.py -q
grep -nE "part_miniere_de|facteurs_richesse_extraction" vues/chronique/capture.py
```

- la première commande est verte, **sans modification** de ce fichier de
  test ;
- `test_les_champs_mobiles_sont_mesures_et_pas_declares` passe : l'ensemble
  des champs que le moteur fait bouger est égal à `CHAMPS_MOBILES`, et
  `"bourg"` en fait partie ;
- `test_la_decoupe_rend_la_photographie_au_bit_pres` passe : le décor et
  l'image d'un instant recomposent la photographie de cet instant, bourg
  compris ;
- la seconde commande ne sort **rien** : la part non agricole n'est pas
  recalculée dans la chronique.

**Rouge prouvé d'abord** : sur la première livraison de ce lot, sans
retouche de la chronique, les deux contrôles nommés rougissent — mesuré
le 15 septembre 2026 sur la PR 12, par le contrôle `vues` de la CI.

## Hors périmètre

- toute autre retouche de la chronique — sa planche, sa bobine, son atlas,
  son format : seule la liste `CHAMPS_MOBILES` gagne une entrée, et
  `_image_du_monde` une lecture ;
- le visualiseur, son schéma attendu, son affichage du bourg — c'est le lot
  052, qui dépend de celui-ci ;
- tout mécanisme, tout nouveau nombre de monde : SC1 et SC6 le mesurent ;
- tout métier autre que celui du lot 044, toute nouvelle source de
  population non agricole ;
- un seuil, un drapeau, une classification « ceci est une ville » — le
  document rapporte deux nombres, il n'interprète rien ;
- le message d'aide de `--snapshot-json` dans `sim/__main__.py`, qui cite
  déjà un numéro de schéma périmé (`v0a-1`) : une dette antérieure à ce
  lot, pas la sienne ;
- les artefacts de livraison (`deliverables/`, journal de mesure) d'un
  éventuel harnais : ce dépôt n'en tient plus depuis le dégraissage V1 ;
- la calibration d'un test existant après observation ;
- `sim/MODELE.md` : aucune règle nouvelle n'est écrite, il n'y a rien à y
  documenter.
