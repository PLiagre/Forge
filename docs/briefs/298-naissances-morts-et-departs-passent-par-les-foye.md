# Lot #298 — Naissances, morts et départs passent par les foyers
Jalon : J4 · Machine : vps · Taille prévue : 270 lignes

## But
Quand le moteur fait naître, mourir ou partir des habitants, il les prend dans les métiers de la cellule, ou les y range, au prorata. Pendant une année du vrai monde, les foyers de chaque cellule comptent alors exactement sa population. Aucun mineur n'apparaît là où il n'y en avait pas, et aucun chiffre du monde ne bouge.

## Règle du monde
Elle découle de quatre sections de `jeu/sim/MODELE.md` :
- « La mortalité » et « La natalité » donnent le nombre de morts et de naissances d'une cellule ;
- « La migration de famine » donne les partants et les arrivants ;
- « Les foyers par métier » (#297) donne les métiers d'une cellule et l'invariant somme des métiers = population.

Ce lot ne change **aucun** de ces nombres. Il dit seulement **qui** naît, meurt, part ou arrive.

- **Le prorata, plus forts restes d'abord.** Répartir `n` personnes entre les métiers `{m: c_m}` de somme `S > 0` se fait en deux temps.
  - Chaque métier reçoit d'abord `n × c_m // S`, en calcul entier, sans aucun flottant.
  - Les personnes qui restent vont une à une aux métiers dont le reste `n × c_m % S` est le plus fort. À reste égal, le nom de métier le plus petit passe d'abord.
  - Exemples :
    - un mort parmi `{mineurs: 50, paysans: 950}` est un paysan, puisque les restes sont 50 et 950 ;
    - deux morts parmi `{mineurs: 5, paysans: 5}` font un mineur et un paysan ;
    - un mort parmi les mêmes est un mineur (nom le plus petit).
- **Morts.** `_apply_mortality` calcule ses morts comme aujourd'hui. Les personnes réellement retirées valent `population − max(0, population − morts)`. Elles quittent les métiers de la cellule au prorata. Un métier tombé à zéro disparaît.
- **Naissances.** `_apply_natalite` calcule ses naissances comme aujourd'hui. Elles rejoignent les métiers de la cellule au prorata : l'enfant d'une cellule minière peut être mineur. Ce n'est pas un héritage par famille, que ce lot ne simule pas.
- **Départs et arrivées.** `_apply_migration` garde ses transferts, son atomicité et ses arrondis. Pour chaque cellule, le solde `entrées − sorties` du tick s'applique ainsi :
  - un solde négatif quitte les métiers de la cellule au prorata ;
  - un solde positif rejoint les métiers de la cellule **d'arrivée** au prorata. Le migrant ne garde pas son métier : un mineur affamé qui arrive dans une plaine devient paysan ;
  - si la cellule d'arrivée n'a aucun métier (population nulle), les arrivants sont tous paysans (`METIER_PAYSANS`).

  Une cellule receveuse n'envoie personne le même tick, donc son solde n'a qu'un signe.
- **Une cellule aux métiers non calculés** (`lire_habitants_par_metier(cell) == -1`, une `Cell` construite à la main) voit sa population écrite exactement comme aujourd'hui.
- **Une écriture directe de `cell.population`, hors de ces trois maillons**, garde la règle `repartir` de #297 : le reste va au plus nombreux. Les tests existants qui écrivent la population en dépendent, et `test_ecriture` fige `repartir({"mineurs": 100, "paysans": 900}, 999) == {"mineurs": 99, "paysans": 900}`. Ce lot ne touche ni à `repartir` ni à `Cell.__setattr__`.
- **Aucun nombre du tick ne dépend des métiers.** Population, stocks, dettes, reports de fraction et transferts restent identiques au bit près. Les métiers sont écrits par le tick, jamais lus pour calculer un nombre.

Niveau de fidélité : **niveau 2**. Le prorata est plausible, jamais sourcé. La mort qui frappe la mine plus que les champs, le métier qu'un migrant emporte et l'enfant qui hérite du métier de ses parents restent au **niveau 3**, non simulés.

### Ce que le code porte
- `sim/foyers.py` gagne trois fonctions :
  - `au_prorata(n, habitants_par_metier)` rend `{métier: part}` par la règle ci-dessus (somme exacte `n`, parts nulles absentes) ;
  - `retirer(habitants_par_metier, n)` rend les métiers moins leur part, sans les métiers tombés à zéro ;
  - `ajouter(habitants_par_metier, n)` rend les métiers plus leur part, ou `{METIER_PAYSANS: n}` s'il n'y a aucun métier et `n > 0`.

  Toutes trois rendent un nouveau dictionnaire et ne modifient pas leur argument. Elles lèvent `FoyersInvalides` dans ces cas :
  - un `n` négatif, booléen ou non entier ;
  - un retrait plus grand que la somme ;
  - un `au_prorata` sur des métiers vides avec `n > 0`.

  `n = 0` rend une copie inchangée.
- `sim/model.py` gagne l'écrivain `ecrire_habitants_par_metier(cell, metiers)`. Il valide (`valider_metiers`), écrit `cell.habitants_par_metier`, puis `cell.population = sum(metiers.values())`. `repartir` voit alors une somme égale et ne change rien.
- `sim/engine.py` gagne deux helpers de module, `_retirer_par_les_foyers(cell, n)` et `_ajouter_par_les_foyers(cell, n)` :
  - pour une cellule non calculée, ils écrivent `cell.population` comme aujourd'hui ;
  - sinon, ils passent par `foyers.retirer` / `foyers.ajouter` et l'écrivain.

  Les trois maillons appellent ces helpers à la place de leurs écritures de `cell.population`, et de rien d'autre. `tick()` ne les appelle pas directement.

### Pièges, payés ailleurs
- **L'ordre du tick.** `test_ordre_du_tick_documente_est_celui_du_code` lit les appels de **`tick()`** vers les fonctions du module. Les helpers s'appellent depuis les maillons, jamais depuis `tick()`, sinon l'ordre documenté rougit.
- **Les littéraux.** `test_no_hardcoded.py` refuse dans `sim/` tout littéral hors de {0, 1, −1}.
- **La couverture d'écriture.** `Foyers` ne s'importe pas par nom dans `sim/model.py` (`import sim.foyers as _foyers`), sinon `test_write_coverage.py` lui demande un écrivain.
- **Le mot « seigneurie ».** Il reste hors de `world.py`.
- **La phrase figée.** `test_gardes_et_documentation` exige que la section « Les foyers par métier » contienne « le tick ne lit pas les métiers ». La phrase reste, complétée : il ne les lit pas pour calculer un nombre, il les écrit.
- **Les égalités.** Elles se départagent par nom de métier. `_repartir_habitants_proportionnellement` (départage par `cell_id`, sur des flottants) ne se réutilise pas.

### `MODELE.md` change
- « Les foyers par métier » :
  - « Naissances, morts et migrations par foyer sont à venir » est remplacé par la règle du prorata, avec ses trois exemples ;
  - la règle d'une écriture directe (`repartir`) reste, présentée comme celle des écritures hors du tick.
- « La mortalité », « La natalité » et « La migration de famine » gagnent chacune une ligne : qui meurt, qui naît, qui part et qui arrive, au prorata des métiers ; les arrivants sont paysans dans une cellule vide.
- « Ce que le moteur ne fait pas encore » : la puce « répartir le travail » dit que naissances, morts et départs suivent les métiers, mais qu'aucun nombre du tick ne les lit.

## Périmètre
jeu/sim/foyers.py
jeu/sim/model.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/tests/test_foyers.py
docs/briefs/298-naissances-morts-et-departs-passent-par-les-foye.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`. Les nouveaux cas **s'ajoutent** à `sim/tests/test_foyers.py`, le fichier qui porte l'invariant. Chaque test imprime ses compteurs, et un échantillon vide échoue. Aucun `cell_id` n'est écrit en dur.

Le test porte sa **propre** règle de référence du prorata, écrite dans le test sans appeler `sim.foyers`. Sans elle, la preuve se vérifierait par le code qu'elle juge.

- **SC1 — Le prorata, plus forts restes d'abord.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k prorata`
  - `au_prorata(1, {"mineurs": 50, "paysans": 950}) == {"paysans": 1}`.
  - `au_prorata(2, {"mineurs": 5, "paysans": 5}) == {"mineurs": 1, "paysans": 1}`.
  - `au_prorata(1, {"paysans": 5, "mineurs": 5}) == {"mineurs": 1}`.
  - `retirer({"mineurs": 1, "paysans": 9}, 10) == {}`.
  - `ajouter({}, 3) == {"paysans": 3}` et `ajouter({}, 0) == {}`.
  - Sur 200 couples (métiers, `n`) tirés par `random.Random(0)`, `au_prorata` égale la référence du test, et la somme des parts vaut `n`. Le compteur `cas_comparés` est imprimé.
  - Lèvent `FoyersInvalides` : `retirer({"paysans": 3}, 4)`, `n = -1`, `n = True`, `n = 2.5` ; l'argument reste intact après chaque appel.
  - Contre-épreuve : la règle `repartir` de #297, mise sous la forme d'un retrait (`repartir(m, S − 1)`) et passée au même comparateur, le fait échouer sur `{"mineurs": 50, "paysans": 950}`, puisqu'elle retire un mineur.
- **SC2 — Une année du vrai monde : à chaque tick, les foyers font la population, et chaque mouvement suit le prorata.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k un_an`
  - `World.charger(0)` joue 365 ticks avec `random.Random(0)`.
  - Le test enveloppe par `monkeypatch` `sim.engine._apply_mortality`, `_apply_natalite` et `_apply_migration`. Avant et après chaque appel, il relève les métiers de chaque cellule touchée.
  - Après chaque tick, pour toutes les cellules :
    - `sum(habitants_par_metier.values()) == population` ;
    - aucun métier n'a moins d'une personne (aucun métier sans foyer) ;
    - aucune cellule sans gisement dans `monde.carte` et sans mineurs au tick 0 n'a la clé `mineurs`.
  - Pour chaque cellule dont la population a changé dans un maillon, la variation de chaque métier égale la référence du test :
    - un retrait au prorata des métiers d'avant ;
    - un ajout au prorata, ou des paysans si la cellule était vide.
  - Compteurs imprimés, tous strictement positifs :
    - `vérifications` ;
    - `morts_contrôlées` ;
    - `naissances_contrôlées` ;
    - `départs_contrôlés` ;
    - `arrivées_contrôlées` ;
    - `mouvements_en_cellule_minière` ;
    - `cellules_sans_gisement_contrôlées`.
  - Contre-épreuve 1 : le même contrôle, sur 30 ticks avec un moteur dont `_retirer_par_les_foyers` et `_ajouter_par_les_foyers` écrivent `cell.population` directement (la règle `repartir` de #297), lève `AssertionError` sur la variation par métier. Mesuré au brief : 366 naissances et 51 migrations s'en écartent dès les 30 premiers ticks.
  - Contre-épreuve 2 : sur 30 ticks, avec des helpers qui écrivent la population par `cell.__dict__["population"]`, donc sans passer par les foyers, le contrôle somme des foyers = population lève `AssertionError`.
  - Contre-épreuve 3 : un `ajouter` remplacé pour rendre les arrivants mineurs fait rougir le contrôle « pas de mineurs sans gisement ».
- **SC3 — Les chiffres du moteur sont identiques au bit près.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k bit`
  - On joue deux fois `World.charger(0)` pendant 365 ticks, avec `random.Random(0)` :
    - la course A avec le moteur du lot ;
    - la course B avec les deux helpers remplacés par l'écriture d'avant ce lot (`cell.population = cell.population ∓ n`).
  - `World.to_dict()` des deux courses, chaque cellule privée de sa clé `"foyers"`, donne le même JSON trié à l'octet. Leurs SHA-256 sont imprimés.
  - Pour chaque cellule, les `population` sont égales et de même type (`int`).
  - Une cellule construite sans métiers (`Cell(cell_id=…, area_km2=10.0, population=50)`) et mise en famine par le test voit sa population écrite comme en B, et ses métiers restent `-1`.
  - Contre-épreuve : sur 30 ticks, la course A rejouée avec un `foyers.retirer` qui retire une personne de moins (dès que `n ≥ 1`) donne un JSON différent de la course B sur 30 ticks. La comparaison voit la dérive du moteur.
- **SC4 — Le modèle le dit.** `python3 -m pytest sim/tests/test_foyers.py -q -s -k documentation`
  - La section « Les foyers par métier » contient « plus forts restes », « nom de métier » et « paysans ».
  - Les sections « La mortalité », « La natalité » et « La migration de famine » contiennent chacune « prorata ».
  - `test_gardes_et_documentation` reste vert, phrase « le tick ne lit pas les métiers » comprise.
  - Contre-épreuve : sur une copie du texte privée du mot « prorata » dans « La natalité », le même contrôle lève `AssertionError`.
- **SC5 — Rien d'autre ne rougit.** `python3 -m pytest sim/tests -q`
  - Toute la suite est verte, en particulier :
    - `test_write_coverage.py` et `test_no_hardcoded.py` ;
    - `test_ordre_du_tick_documente_est_celui_du_code` ;
    - `test_determinisme.py` et `test_survie.py` ;
    - les cas de `test_foyers.py` livrés par #297 ;
    - les fichiers figés de `/lieu`.
  - Contre-épreuve : un appel direct à `_retirer_par_les_foyers` ajouté dans `tick()` fait rougir `test_ordre_du_tick_documente_est_celui_du_code`.
- **SC6 — Aucun test existant ne s'assouplit.** `git diff origin/master -- sim/tests | grep -E '^-[^-]'` ne rend rien.
  - Contre-épreuve : une ligne existante retirée ou modifiée apparaît dans la sortie.

## Hors périmètre
- Le métier que le migrant emporte, la mort qui frappe un métier plus qu'un autre, l'enfant qui hérite du métier de ses parents : niveau 3.
- `repartir` et `Cell.__setattr__` (la règle d'une écriture directe, livrée par #297) ne changent pas.
- Le bourg compté par les foyers non paysans : `sim/aggregation.py`, `RepartitionBourg` et la distribution à l'intérieur de la cellule ne changent pas. C'est le sous-lot 3 de #255.
- Les foyers dans `/lieu`, `/monde`, la photographie ou Unity, et donc les fichiers figés `lieu-graine0-tick{3,4}.json` (sous-lot 4, sur le PC).
- Tout nombre du tick qui lirait les métiers : l'extraction reste `population × part`.
- Le chantier qui prend des bras aux champs, l'atelier, tout métier autre que mineur et paysan, le logement, la parenté, les âges.
- `sim/world.py`, `sim/constants.py`, `sim/service.py`, `sim/snapshot_export.py`, `jeu/vues/`, `jeu/ville/`, `3d/`, et tout test existant.
