# Lot #601 — Le monde garde trente jours de ce qui circule
Jalon : J3 · Machine : vps · Taille prévue : 285 lignes

## But
Le monde garde, sur ses trente derniers ticks, ce que chaque maison a
prélevé, reçu à son grenier, envoyé à son suzerain, perdu en route et rendu
à ses lieux, et ce que chaque lieu a donné, perdu et gagné en habitants,
sans qu'aucune règle ne le lise ni qu'aucune empreinte ne bouge.

## Le joueur
Lot de fond. Il prépare l'écran et la décision du jalon 3 : « les flèches de
ce qui monte vers le siège du joueur et vers celui de son suzerain ; les
lieux qui se vident quand il prend trop », et l'arbitrage « prendre plus
aujourd'hui ou garder ses gens ». Pour que le joueur sente ce que sa part
lui coûte, il faut que le monde se souvienne de ce qui a circulé :
combien est monté de ses lieux, combien est arrivé à son grenier, combien
est parti chez son suzerain, combien les charretiers ont mangé, et combien
de foyers sont partis de chacun de ses lieux. Après ce lot, le monde le
sait ; le joueur ne le voit pas encore. Les sous-lots suivants de #400 le
servent (`/maisons`, `/maison`, puis `/lieu`) ; #401 en dessine les flèches
dans la forge, #403 et #405 dans Unity.

## Règle du monde
Aucune règle nouvelle : le registre **observe** les règles existantes, il
ne décide rien. Il découle de `jeu/sim/MODELE.md`, « Le prélèvement »
(convois, perte en route, dû au suzerain, secours), « Le grenier d'une
maison » (« L'ouvrir ») et « Les départs » (la famine, le mieux-vivre).
Ses chiffres sont des mesures exactes du monde ; aucune constante de monde
ne s'ajoute, aucun niveau de fidélité ne change. `MODELE.md` gagne une
section `## Les flux sur trente jours`, placée juste après
`## Le prélèvement` et avant `## Les intentions du joueur`. La liste
« En une page » ne change pas : le registre n'est pas une étape du tick.

**La fenêtre.** Une constante nouvelle dans `jeu/sim/constants.py`,
`FENETRE_FLUX_TICKS = 30`, avec son commentaire : fenêtre de lecture, trente
jours à un jour par tick, pas une règle du monde. `flux.py` la relit par
`_constantes.FENETRE_FLUX_TICKS` à chaque appel (jamais
`from sim.constants import …`, et aucun littéral autre que 0, 1, −1 dans ses
fonctions : `test_no_hardcoded.py` balaie tout `sim/`).

**Le module `jeu/sim/flux.py`.** Il n'importe que la bibliothèque standard
et `sim.constants`. Il contient :

- `JourDeFlux`, une dataclass (hors de `sim/model.py`, pour rester hors de
  `test_write_coverage.py`) : `tick` ; cinq vecteurs `array('d')` alignés
  sur `monde.routes_des_lieux.noms` — `preleve`, `recu`, `du`, `mange`,
  `rendu` ; `taux` et `recoltes`, les références (pas des copies) à la liste
  des parts et au dictionnaire des récoltes que le prélèvement a lus ce
  tick, `None` sans prélèvement ; `partis` et `arrives`,
  `(cell_id, rang) → personnes`.
- `Flux`, une dataclass : `jours`, `tick → JourDeFlux`, et `en_route`, un
  `array('d')` aligné sur les mêmes noms, la charge courante en route vers
  le grenier de chaque maison. **L'égalité se fait par contenu** (les
  dataclasses le donnent) : des tests existants comparent
  `monde.__dict__` à sa copie profonde (`test_intentions.py`,
  `_ia_pure`, `test_ia_depot_commun_et_copies`), et une égalité par identité
  les ferait rougir.
- `jour_courant(monde)` : rend `None` si `monde` n'a pas d'attribut `flux`
  (les mondes de fortune des tests) ; sinon le `JourDeFlux` du tick
  `monde.ticks_ecoules`, créé s'il n'existe pas. À la création, les jours
  de tick `< ticks_ecoules + 1 − FENETRE_FLUX_TICKS` sont retirés, et les
  vecteurs prennent la longueur de `routes_des_lieux.noms` (0 sans routes) ;
  un vecteur plus court que les noms, ou `en_route`, s'allonge de zéros.
- `noter_personnes(monde, partis, arrives)` : ajoute deux dictionnaires
  `(cell_id, rang) → personnes` au jour courant ; ne fait rien, pas même
  créer le jour, si les deux sont vides ou si `monde` n'a pas de `flux`.
- `flux_de_maison(monde, maison) -> dict` : clés `preleve_kg`, `recu_kg`,
  `du_envoye_kg`, `mange_en_route_kg`, `rendu_kg`, sommes sur les jours de
  tick `≥ ticks_ecoules − FENETRE_FLUX_TICKS`. Une maison du registre absente
  des noms des routes (sans lieu ni vassal routé) rend cinq zéros, qui sont
  une mesure ; un identifiant absent de `monde.maisons` lève `ValueError` en
  le nommant.
- `flux_de_lieu(monde, cell_id, rang) -> dict` : clés `preleve_kg`, `partis`,
  `arrives`, sur la même fenêtre. Le prélevé d'un lieu se relit
  `taux[indices[rang]] × recoltes[cell_id][rang]`, avec `indices` tiré de
  `routes_des_lieux.par_cellule[cell_id]` : c'est le même produit, au même
  flottant, que celui que le prélèvement a retiré du lieu ; un lieu sans
  route ou sans récolte ce tick compte 0. Un lieu absent du monde lève
  `ValueError`.

Ces deux lecteurs ne sont appelés par aucun module de `sim/` : ils servent
les tests et, demain, le service.

**Pourquoi le prélevé d'un lieu se relit au lieu de s'écrire.** Le tick est
mesuré à 96,48 ms (médiane, `test_tick_sous_le_budget_du_service`, srv1914711,
14/10/2026) pour un budget de 100 ms. Un prototype qui écrivait un tableau
par cellule et trois cases par lieu faisait passer l'étape Prélèvement de
5,4–6,0 ms à 8,9–9,3 ms. Garder les références de `taux` et `recoltes`
(fraîches à chaque tick, jamais relues après le prélèvement) ne coûte rien.

**Qui écrit quoi.** Chaque écrivain prend `jour = flux.jour_courant(monde)`
une fois par appel et n'écrit rien si c'est `None`.

1. `prelevement.prelever`, après `if not routes: return` :
   - perte des secours : le mangé de chaque charge `(cell_id, rang)`
     s'ajoute à `mange[i]`, où `i` est l'indice du maître du lieu lu dans
     `routes.par_cellule[cell_id][0][rang]` (« les secours vers ses lieux ») ;
   - perte des convois : pour chaque maison, `mange[i] += en_route[i] ×
     PERTE_CONVOI_PAR_JOUR`, et `en_route[i]` garde le reste — la charge en
     route vers son grenier fois la perte du jour ;
   - arrivées : `en_route[i]` perd l'entrée (après perte, avant dû) ;
     `du[i]` reçoit le dû ; `en_route[indice du suzerain]` reçoit le dû, qui
     roule désormais vers ce grenier ; `recu[i]` reçoit ce qui entre
     vraiment au grenier, dû déduit. Le dû qu'un suzerain reçoit est une
     arrivée comme une autre à son tour ;
   - départ de la récolte : `preleve[i] += kg` par lieu, et chaque kilo
     prélevé entre une fois dans `en_route[i]` ; puis `jour.taux` et
     `jour.recoltes` prennent les références du tick.
   `prelevement.py` ne lit toujours aucun attribut nommé `maitre`,
   `maisons` ou `suzerain` (`test_tick_sans_maitre_ni_registre`,
   `test_modele_du_au_suzerain_et_tick_sans_registre`) : les noms du
   registre restent ceux de la table des routes.
2. `departs.appliquer_departs` : `partis[source] += partants` et
   `arrives[destination] += partants`, en personnes, bruts (un lieu qui
   envoie et reçoit dans le même appel compte les deux), puis
   `noter_personnes`. Les mouvements dans la cellule comptent aussi.
3. `engine._apply_migration`, au moment où les lieux changent (après toute
   validation et toute annulation) : `arrives[(cid, 0)] += delta` pour une
   cellule à lieux qui reçoit, `partis[(cid, rang)] += retrait` pour chaque
   lieu qui perd, puis `noter_personnes`. Une cellule sans lieux n'a pas de
   lieu : elle n'est pas comptée. `engine.py` importe `from sim import flux
   as _flux`, ne lit ni `routes_des_lieux`, ni `PERTE_CONVOI_PAR_JOUR`, ni
   `PART_COUTUMIERE`, et n'importe pas `convois` (`test_convois.py`,
   `test_prelevement.py`).
4. `OuvrirGrenier.appliquer` (`intentions.py`) : `rendu[i] += kg` pour la
   maison qui ouvre, `i` étant son indice dans `routes_des_lieux.noms`.

`World.__init__` pose `self.flux = Flux()` (vide au chargement et pour un
`World(...)` d'épreuve), sa ligne entre dans la docstring « Attributs » ;
`to_dict()` ne le publie pas. Aucune règle ne lit `World.flux`.

## Périmètre
jeu/sim/flux.py
jeu/sim/constants.py
jeu/sim/world.py
jeu/sim/prelevement.py
jeu/sim/departs.py
jeu/sim/engine.py
jeu/sim/intentions.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/README.md
jeu/sim/tests/test_flux.py

## Conditions de succès
Les cas neufs vivent dans `jeu/sim/tests/test_flux.py` (fichier neuf, nommé
dans `jeu/sim/tests/README.md` ; `sim/flux.py` est nommé dans
`jeu/sim/README.md`). Rouge d'abord : avant le module, chaque cas échoue à
l'import de `sim.flux`. Le monde réel se charge une fois par module
(`World.charger(0)`, `random.Random(0)`), copié par `copy.deepcopy` si un
cas le modifie.

- **SC1 — le prélevé des lieux fait celui de leur maître.** Monde réel,
  35 ticks : pour chaque maison des routes, la somme de `flux_de_lieu(…)
  ["preleve_kg"]` sur ses lieux égale `flux_de_maison(…)["preleve_kg"]`
  (`pytest.approx`, rel 1e-12), et au moins une maison a un prélevé non nul
  (un échantillon vide échoue). Contre-épreuve : le même contrôle, sur un
  flux où l'on a ajouté 1 kg au `preleve` d'une maison dans un seul jour,
  échoue.
- **SC2 — le 31e jour sort de la fenêtre.** Petit monde à une cellule, deux
  lieux, une maison, route d'un jour (le motif de
  `test_paniers_production_puis_prelevement`) : un prélèvement au tick 0
  seulement (part remise à 0 ensuite), un départ de mieux-vivre au tick 0
  seulement. Avec `ticks_ecoules = 30`, la maison et le lieu comptent encore
  le tick 0 ; à `ticks_ecoules = 31`, prélevé, partis et arrivés valent 0.
  Après 40 ticks du monde réel, `len(monde.flux.jours) ≤ FENETRE_FLUX_TICKS`.
  Contre-épreuves : `FENETRE_FLUX_TICKS` porté à 31 (monkeypatch) fait
  échouer l'assertion du 31e jour ; un lecteur qui somme tous les jours
  gardés, sans filtre de tick, la fait échouer aussi.
- **SC3 — chaque compteur contre une mesure indépendante du monde.** Monde
  réel, `PERTE_GRENIER_PAR_AN = 0`, 35 ticks, lus tick par tick par le test
  sur le monde lui-même : pour chaque maison, la somme de `recu_kg` sur la
  fenêtre égale la hausse de nourriture de son grenier sur les mêmes ticks ;
  à chaque tick, la somme des `mange` égale la hausse de
  `mange_convois_kg`, et la somme des `preleve` égale la variation des
  charges en route (`prelevement.charges_en_route`) plus la somme des
  `recu` plus la hausse de `mange_convois_kg` ; à la fin, `en_route[i]` égale
  la somme des charges en route de la maison i (rel 1e-9). Le dû : la somme
  des `du_envoye_kg` est positive, et pour chaque maison le dû envoyé vaut
  `PART_DUE_AU_SUZERAIN / (1 − PART_DUE_AU_SUZERAIN)` fois son reçu, jour
  par jour, quand elle a un suzerain routé (rel 1e-9). Contre-épreuve : un `en_route` qui oublie le dû (le dû
  retiré à la main de l'`en_route` du suzerain) fait échouer la dernière
  égalité.
- **SC4 — partis et arrivés, bruts, des deux départs.** Sur la chaîne A → B
  → C de #593 (B à 5 000 habitants, `_cellule_bourg` de
  `test_commerce.py`, résultat attendu A 2 495, B 4 995, C 1 010) : `partis`
  vaut 5 pour A et 10 pour B, `arrives` 5 pour B et 10 pour C ; pour chaque
  lieu, `arrives − partis` égale la variation de sa population, et la somme
  des `partis` égale ce que rend `appliquer_departs`. Une migration de famine sur un petit monde à lieux :
  les `partis` des lieux affamés égalent leurs pertes, l'`arrives` du rang 0
  de la cellule receveuse égale son gain. Un appel sans départ ne crée aucun
  jour. Contre-épreuve : un flux qui noterait le solde au lieu des bruts
  donnerait à B 5 partis et 0 arrivé, et le cas échoue.
- **SC5 — le rendu à l'ouverture.** Monde réel : grenier de `seigneurie-1`
  rempli à 1 000 kg, une intention `ouvrir_grenier` de 400 kg, un tick :
  `rendu_kg` vaut 400 ; après la fin des secours, son `mange_en_route_kg`
  dépasse celui d'une copie sans ouverture. Une maison du registre absente
  des routes rend cinq zéros ; un identifiant inconnu lève `ValueError`.
  Contre-épreuve : une ouverture refusée (plus que le grenier) ne change
  aucun compteur.
- **SC6 — les empreintes ne bougent pas, aucune règle ne lit le registre.**
  Deux copies du monde réel jouent 40 ticks ; dans l'une, après chaque tick,
  `monde.flux` est remplacé par un `Flux()` vide : les deux `to_dict()` sont
  identiques à l'octet, et aucune clé de `to_dict()` ne contient `flux`.
  Contre-épreuve : un `prelever` enveloppé qui double les parts quand le
  flux porte un prélevé non nul fait diverger les deux copies, et le cas
  échoue. `python3 -m pytest jeu/sim/tests/test_determinisme.py -q` reste
  vert sans toucher une empreinte figée.
- **SC7 — le coût du tick est mesuré** (marque `chronometre`). Monde réel,
  graine 0, ticks 5 à 24 après 5 de chauffe, comme
  `test_tick_sous_le_budget_du_service` : médiane sous `BUDGET_TICK_MS`,
  avec un flux rempli (vingt jours, un prélevé et un mangé non nuls) ; la
  médiane est imprimée. Contre-épreuve : `flux.jour_courant` ralenti de
  `BUDGET_TICK_MS` fait échouer la mesure. La section de `MODELE.md` donne
  la médiane du tick et celle de l'étape Prélèvement, avant et après le
  lot, mesurées sur srv1914711. **Les tests de budget existants
  (`test_tick_sous_le_budget_du_service`, `test_ateliers_budget`,
  `test_departs_budget_comparaison`) ne s'assouplissent pas** : si le tick
  passe 100 ms, on allège les écritures (variables locales, boucles sur les
  maisons fusionnées, aucune allocation par lieu), et si l'on n'y arrive
  pas, on le dit sur la PR avec les mesures, sans toucher un seuil.
- **SC8 — la section du modèle.** `## Les flux sur trente jours` existe et
  contient `FENETRE_FLUX_TICKS`, `to_dict`, `aucune règle`, `en_route`,
  `ms` ; un contrôle sur le texte privé de la section échoue.

Commandes :

- `python3 -m pytest jeu/sim/tests/test_flux.py -q` — vert, au moins huit
  cas recueillis.
- `python3 -m pytest jeu/sim/tests/test_flux.py -q -m chronometre` puis
  `python3 -m pytest jeu/sim -q -m chronometre` — verts, joués seuls.
- `python3 -m pytest jeu/sim -q` — vert, en particulier
  `test_no_hardcoded.py`, `test_write_coverage.py`
  (`test_aucune_constante_terminale`), `test_determinisme.py`,
  `test_prelevement.py`, `test_convois.py`, `test_commerce.py`,
  `test_intentions.py`.

## Hors périmètre
- Le service (`/maisons`, `/maison`, `/lieu`), la photographie et la preuve
  par rejeu : sous-lots suivants de #400. `service.py` et
  `snapshot_export.py` ne sont pas touchés.
- Les flèches de la forge et de Unity : #401, #403, #405.
- Une règle qui lirait le registre (l'IA qui regarde ses départs, au
  jalon 5) : aucune ici.
- Les flux de commerce, de naissance et de mort ; les départs d'une cellule
  sans lieux.
- Sauver ou recharger le registre : il repart vide à chaque chargement
  (jalon 9, #489).
- Tout test existant : aucun ne change.
