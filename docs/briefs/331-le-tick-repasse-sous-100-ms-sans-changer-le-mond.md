# Lot #331 — Le tick repasse sous 100 ms sans changer le monde
Jalon : J3 · Machine : vps · Taille prévue : 230 lignes

## But
Le monde entier joue un jour en bien moins de 100 ms (graine 0, VPS), exactement comme avant, au bit près : les sous-lots suivants du lot #236 (le tick joue chaque lieu) ont de la marge pour jouer les 6 619 lieux sans faire sauter le budget de CAP.md.

## Règle du monde
Aucune règle ne change. Ce lot ne touche que la façon de calculer : les sections « En une page » (ordre du tick, maillons 3, 6 et 12), « Le commerce entre cellules » (« La capacité d'une arête », « Besoin, surplus et allocation ») et « Les lieux d'une cellule, vue dérivée » (« Ce que porte un lieu », la règle `partager`) de `jeu/sim/MODELE.md` restent vraies mot pour mot, et `MODELE.md` ne change pas. Pas de niveau de fidélité en jeu : aucun nombre du monde ne bouge.

**Pourquoi ce lot.** CAP.md (jalon 1, « Quand revenir sur cette décision ») : au-delà de 100 ms une fois les gains évidents pris, on porte le moteur en C#. `BUDGET_TICK_MS = 100` dans `jeu/sim/service.py`. Découpé du lot #236 (réponse A du propriétaire) : c'est le sous-lot 1 sur 5.

**Mesuré sur master `1924f24`, graine 0, VPS (2 cœurs, Python 3.12), le 05/10/2026.** 596 cellules, 1 364 arêtes, 6 619 lieux. Tick médian sur une année : **140 ms** (131 ms le matin même : le VPS est partagé). Au profil :
- `_arete_adjacence` balaie `world.adjacency` en entier pour chaque arête, appelée 917 fois par tick par `_initialiser_capacite_aretes` (via `_capacite_transport_arete_kg` → `_capacite_base_arete_kg`) : ~20 % du tick ;
- `_marchandises_du_monde` appelle `world.to_dict()` (toutes les cellules, leurs foyers, leurs lieux, les plans) pour lire les noms du panier : ~7 % ; `_matieres_premieres_du_panier` fait de même avec `cellule_vers_dict(cell)` pour chaque cellule, à chaque tick ;
- `repartir_sur_les_lieux` : 16,6 ms par tick (~12 %), surtout dans `partager`.

**Mesuré en essai jetable (hors du dépôt)** : un index des arêtes plus la liste des marchandises lue par `copier_panier` ramènent la médiane de l'année à **68 ms**, et l'empreinte de chaque tick de l'année (`to_dict`, `stocks_mer`, retour de `tick`) reste **identique** à celle de master. Un allègement simple de la répartition (ne plus recopier les paniers, surfaces calculées une fois) la passe de 16,6 à 14,0 ms par tick, empreinte identique.

**Ce qui doit être fait, sans changer un seul résultat :**
1. **L'index des arêtes.** Une table `clé non orientée → arête` (`_cle_arête`), construite **à chaque tick** à partir de `world.adjacency`, jamais gardée sur le monde d'un tick à l'autre : `test_seigneuries.py::test_fiche_voisins_et_absences` ajoute des arêtes à un monde chargé, et un monde d'épreuve (`_MondeEpreuve` de `test_write_coverage.py`) n'a que `cells` et `adjacency`. Pour deux entrées de la même paire, l'index garde **la première** dans l'ordre de la liste, comme le balayage d'aujourd'hui. `_capacite_base_arete_kg` garde son nom et son expression `DEBIT_KG_PAR_KM_DE_FRONTIERE_PAR_TICK × shared_length_m` (`test_expression_capacite_debit_km_fois_shared_length_m` la cherche dans son corps) ; `_capacite_transport_arete_kg(world, a, b)` et `_initialiser_capacite_aretes(world)` restent appelables comme aujourd'hui (des tests et `MODELE.md` les appellent).
2. **Les marchandises sans recopier le monde.** `_marchandises_du_monde` et `_matieres_premieres_du_panier` lisent les noms du panier de chaque cellule par `copier_panier` (ou un accès nommé neuf de `sim/model.py`), jamais par `to_dict` ni `cellule_vers_dict`. Même ensemble de noms, même ordre trié. **Piège** : `test_acces_directs_au_panier_hors_modele` interdit tout `.stocks` dans `sim/` hors de `model.py` ; un accès direct au panier dans `engine.py` ou `lieux.py` le fait rougir.
3. **La répartition allégée.** `repartir_sur_les_lieux` et, s'il le faut, `partager` font moins de travail pour le même résultat : même parts au bit près, même absence d'une marchandise retirée de la cellule, mêmes clés dans les paniers des lieux. Le tick continue d'appeler `_lieux.repartir_sur_les_lieux` par le module, et la répartition continue d'appeler `partager` par le module (`test_lieux.py` les remplace par `monkeypatch`).

## Périmètre
jeu/sim/engine.py
jeu/sim/lieux.py
jeu/sim/model.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_commerce.py
jeu/sim/tests/test_monde.py

## Conditions de succès
- **SC1 — le même monde au bit près sur une année.** `cd jeu && python3 -m pytest sim/tests/test_determinisme.py -q -s -k bit_pres` : le test (dans `test_determinisme.py`, sur le modèle de `test_bit` de `test_foyers.py`) joue deux courses de 365 ticks, `World.charger(0)` puis `tick(monde, random.Random(0), numero_tick=i)`. La course neuve joue le code du lot. La course de référence **charge le monde et joue** sous `monkeypatch`, avec des copies à la ligne près, prises dans `git show 1924f24:jeu/sim/<fichier>`, de **chaque** fonction que le lot modifie ou remplace dans `engine.py`, `lieux.py` et `model.py`, posées dans leur module. Après le chargement puis après chaque tick, chaque course calcule une empreinte SHA-256 de `json.dumps([monde.to_dict(), monde.stocks_mer, valeur rendue par tick], sort_keys=True)` (un flottant s'y écrit par `repr`, donc au bit près) et de `rng.getstate()`. Les 366 empreintes sont égales ; à la première différence, le message nomme le tick. Le test imprime la première et la dernière empreinte et la durée de chaque course.
- **SC2 — la référence passe vraiment par l'ancien chemin, la course neuve n'y passe plus.** Même test que SC1 : chaque copie de référence compte ses appels, et chaque compteur est > 0 après la course de référence ; `World.to_dict` et `sim.engine.cellule_vers_dict`, enveloppés d'un compteur remis à zéro avant chaque appel de `tick` et lu juste après (avant l'empreinte), sont appelés **0 fois** pendant les ticks de la course neuve et **au moins 365 fois** pendant ceux de la course de référence. Contre-épreuve, dans le même fichier (`-k bit_pres`) : l'état final de la course neuve, avec le stock de nourriture du lieu de rang 1 de la première cellule à plusieurs lieux décalé d'un seul cran (`math.nextafter`), donne une empreinte différente, et la fonction de comparaison échoue en nommant ce tick.
- **SC3 — l'index rend l'arête que trouvait le balayage.** `cd jeu && python3 -m pytest sim/tests/test_commerce.py -q -s -k index_aretes` : un petit monde avec deux entrées pour la même paire (la première à 1 000 m, la seconde à 5 000 m et écrite `b`, `a`), une paire sans arête, et une arête sans `shared_length_m`. pour chaque paire, l'arête que trouve l'index est celle que trouve la copie de l'ancien `_arete_adjacence` (le balayage) : la première entrée, `None` pour la paire absente ; et `_capacite_transport_arete_kg` comme `_initialiser_capacite_aretes` donnent exactement les capacités de l'ancien chemin (celle de la première entrée, le repli `TRADE_CAPACITY_KG_PER_EDGE_PER_TICK` pour la paire absente et pour l'arête sans longueur). Puis une arête ajoutée à `world.adjacency` entre deux ticks est vue au tick suivant (pas d'index périmé). Contre-épreuve : le test vérifie que la règle « dernière entrée » donnerait une capacité différente sur ce monde, pour que le cas ne soit pas aveugle.
- **SC4 — le tick se mesure contre le budget du service.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -s -k sous_le_budget` : `World.charger(0)`, 5 ticks de chauffe, puis 20 ticks mesurés un par un par `time.perf_counter` ; la médiane est **strictement sous `BUDGET_TICK_MS`, importé de `sim.service`** (jamais recopié). Le test imprime la médiane, le maximum et le budget. Contre-épreuve dans le même test : la même fonction de mesure, avec `sim.engine._apply_commerce` enveloppé d'une attente de `BUDGET_TICK_MS` millisecondes, lève `AssertionError`, et l'enveloppe a bien été appelée.
- **SC5 — la marge, mesurée sur le VPS.** Le codeur écrit dans `/tmp/mesure-331.py` (hors du dépôt) :
  ```python
  import random, statistics, time
  import sim.lieux as L
  from sim.engine import tick
  from sim.world import World
  monde, rng, durees, rep = World.charger(0), random.Random(0), [], [0.0]
  repartir = L.repartir_sur_les_lieux
  def mesure(c):
      t = time.perf_counter(); repartir(c); rep[0] += time.perf_counter() - t
  L.repartir_sur_les_lieux = mesure
  for i in range(365):
      t = time.perf_counter(); tick(monde, rng, numero_tick=i); durees.append((time.perf_counter() - t) * 1000)
  print(f"mediane={statistics.median(durees):.1f} ms max={max(durees):.1f} ms repartition={rep[0] / 365 * 1000:.2f} ms/tick")
  ```
  puis le joue coup sur coup sur master (`cd ~/Forge/jeu && python3 /tmp/mesure-331.py`) et dans son chantier (`cd jeu && python3 /tmp/mesure-331.py`). Exigé dans le chantier : **médiane ≤ 80 ms**, et répartition **au moins 10 % sous** celle de master dans la même séance. Les deux lignes, avant et après, vont dans son compte rendu. Si le VPS est chargé (d'autres lots tournent), il rejoue les deux et le dit.
- **SC6 — rien d'autre ne bouge.** `python3 -m pytest jeu -q` depuis la racine passe, sans qu'aucun test existant ne soit modifié ni assoupli : en particulier `test_bit` de `test_foyers.py`, `test_tick_repartit_sur_une_annee_et_suit_les_ecritures` et la contre-épreuve `perdre_un_habitant` de `test_lieux.py`, `test_acces_directs_au_panier_hors_modele` et `test_horloge_pause_vitesse_et_budget` de `test_monde.py`, `test_expression_capacite_debit_km_fois_shared_length_m` de `test_commerce.py`, tout `test_write_coverage.py`. `git diff --stat master` ne montre que des fichiers du périmètre ; `jeu/sim/MODELE.md` et `jeu/sim/service.py` n'y sont pas.

## Hors périmètre
- Toute règle du monde : aucun nombre, aucune constante, aucun ordre de maillon ne change ; `jeu/sim/MODELE.md` ne change pas.
- Le tick par lieu (les sous-lots 2 à 5 du lot #236) : amorçage du bourg, production et consommation par lieu, faim et naissances par lieu, commerce par le bourg, fin de la répartition proportionnelle.
- `BUDGET_TICK_MS` et `jeu/sim/service.py` : le budget se lit, il ne se change pas.
- Le commerce lui-même (passes 1a à 1b, allocation, maritime) au-delà de la lecture des arêtes et des marchandises ; le portage en C#.
- Garder l'index sur `World` d'un tick à l'autre, ou changer le format de `world.adjacency` ou de `data/`.
- Unity et le PC.
