# Lot #424 — L'IA règle sa part sur ses projets et sur ses gens
Jalon : J5 · Machine : vps · Taille prévue : 280 lignes

## But
Une fois par mois, chaque maison de l'IA qui tient des lieux monte ou baisse sa part, avec ses raisons de monde : son grenier face à ce qu'elle veut garder, ses chantiers, la faim et les départs de ses gens. Elle passe par le même `fixer_part` et le même dépôt que le joueur.

## Le joueur
Les voisins du joueur prélèvent comme lui, et pour des raisons : ils prennent plus quand ils bâtissent et que leurs gens sont bien nourris, moins quand leurs gens partent. Un voisin trop gourmand envoie ses foyers chez le joueur, un voisin plus doux attire les siens : c'est la décision du jalon 5, s'en méfier ou s'en servir. Après ce lot, la part d'un voisin bouge dans le monde. Le joueur la lit déjà sur `/maison` et `/maisons`, et le geste avec sa raison sur `/ia` (service `--ia`) et dans la photographie de `python3 -m forge --ia`, sous la forme brute `fixer_part maison=… part=…`. La carte et le panneau la rendront lisible avec #428 et #429.

## Règle du monde
D'après `jeu/sim/MODELE.md`, section « Les décisions et les gestes de l'IA » (complétée ici) ; la section « Les flux sur trente jours » reçoit les lieux affamés. Niveau 2 : plausible, jamais sourcé.

**Ce qui est noté (mesure, pas règle).** `JourDeFlux` reçoit `affames: set` (`field(default_factory=set)`) : les `(cell_id, rang)` dont `population > 0` et `duree_faim_ticks > 0` une fois la cellule passée par Consommation, Faim, Mortalité et Natalité. `flux.noter_affames(monde, lieux)` fait comme `noter_personnes` : un appel vide ne crée aucun jour, et un monde sans registre ne note rien. Dans `engine.tick`, les deux boucles de consommation (avec et sans `facteurs_routes`) recueillent ces lieux seulement pour les cellules dont `penurie_kg > 0`. Ailleurs, `duree_faim_ticks` vaut 0, puisque `_porter_dette_et_faim_sur_les_lieux` le remet à zéro. Après les boucles, un seul appel les note. Aucune étape n'est ajoutée au tick ; `affames` reste hors de `to_dict`.

**Qui décide, et quand.** Dans `sim/ia.decider_intentions`, chaque maison de `maisons_de_l_ia` passe par les filtres existants : hors carte exclue, départ du joueur exclu, refus nommé avant tout dépôt si une donnée manque. Ensuite, elle décide sa part si les quatre conditions suivantes tiennent :
- sa clé du registre (`_cle_du_grenier`) est dans `routes_des_lieux.noms` ;
- `_lieux_de_la_maison(monde, cle)` (sim/intentions.py, déjà lu par `ouvrir_grenier`) n'est pas vide. C'est « tenir des lieux ». Mesuré le 17/10 : ces lieux égalent, pour les 2 289 maisons, les lieux dont `lieu.maitre == cle` ;
- `t = monde.ticks_ecoules` vérifie `t % FENETRE_FLUX_TICKS == zlib.crc32(cle.encode('utf-8')) % FENETRE_FLUX_TICKS`. Le jour du mois est dérivé de l'identifiant, sans `hash()` salé : `seigneurie-6` décide aux ticks 46, 76, 106…, `grande-3` aux ticks 30, 60… ;
- la fenêtre est pleine : `monde.flux.jours` contient les ticks `t−30 … t−1`. Sinon, aucune proposition de part. C'est ce qui garde muets les mondes chargés dont on pose `ticks_ecoules` à la main.

Cette décision ne dépend pas de la tenue du bourg de la capitale. Le `continue` actuel sur `maitre_du_bourg != cle` ne garde que la route. Pour une maison, la proposition de route (s'il y en a une) vient d'abord, puis celle de part.

**Ce qu'elle lit**, sur ses lieux et sur les jours `t−30 … t−1`, en une passe par jour sur l'ensemble de ses lieux (jamais `flux_de_lieu` lieu par lieu : le prototype y passait 400 ms par tick) :
- `habitants` = Σ `population` ;
- `partis` et `arrives` = Σ de `jour.partis` et `jour.arrives` de ses lieux, en personnes ;
- `lieux_affames` = nombre de ses lieux distincts présents dans un `jour.affames` ;
- `grenier_nourriture_kg` = `monde.greniers[cle].get(MARCHANDISE_NOURRITURE, 0)` ;
- `salaires_a_venir_kg` = journées restantes × `SALAIRE_JOURNEE_KG`. Les journées restantes, c'est Σ (`travail_requis − travail_fourni`) des rues, parcelles et bâtiments `en_chantier` du plan de chaque cellule dont elle tient le rang 0 : le salaire est payé par le maître du bourg (#641) ;
- `reserve_gens_kg` = `consommation_kg_par_habitant_par_tick(MARCHANDISE_NOURRITURE) * (RESERVE_VOULUE_JOURS / TICK_DURATION_DAYS) * habitants * RESERVE_VOULUE_PART_DES_HABITANTS`, exactement dans cet ordre (le test refait le même calcul) ;
- `reserve_voulue_kg` = `reserve_gens_kg + salaires_a_venir_kg`.

**Ce qu'elle décide**, `part = monde.parts[cle]` :
- perte (`partis − arrives ≥ TAILLE_FOYER`, en net sur toute sa terre : réponse A du propriétaire) ou `lieux_affames > 0` : baisse, `nouvelle = max(0, round(part − IA_PAS_DE_PART, 9))` ;
- sinon, si `grenier_nourriture_kg < reserve_voulue_kg` : hausse, `nouvelle = min(PART_MAXIMALE, round(part + IA_PAS_DE_PART, 9))` ;
- sinon, ou si `nouvelle == part` (borne atteinte), aucune proposition.

La proposition a la forme des routes : `{'maison': {sorte, id}, 'intention': {'type': 'fixer_part', 'maison': cle, 'part': nouvelle}, 'raison': {...}}`. La raison porte, sans arrondi : `regle` (`part_sur_projets_et_gens`), `part` (l'ancienne), `habitants`, `partis`, `arrives`, `lieux_affames`, `grenier_nourriture_kg`, `reserve_gens_kg`, `salaires_a_venir_kg` et `reserve_voulue_kg`. `jouer_ia` la dépose par `recevoir_intention`, comme les routes, et le relevé la note comme elles. La raison de la route ne change pas (`departs` y vaut toujours −1).

**Le budget des routes** (`actives`) ne compte plus que les entrées dont `intention['type'] == TYPE_TRACER_ROUTE`. Sans ce filtre, une part déposée dans l'année bloquerait la route de la maison.

**Constantes** (`constants.py`, niveau 2, avec un commentaire chacune) : `IA_PAS_DE_PART = 0.05`, `RESERVE_VOULUE_JOURS = 30`, `RESERVE_VOULUE_PART_DES_HABITANTS = 0.1`. `PART_COUTUMIERE` ne bouge pas.

**Mesures du prototype** (base `64a0a66`, graine 0, `/tmp/proto424b.py`) :
- sur 365 ticks avec l'IA, 395 décisions : 31 hausses, 42 baisses, 322 « rien », aucun refus. Sur les baisses, 35 viennent d'une perte, dont 16 sans faim (la première : `grande-18` au tick 122, 35 partis contre 1 arrivé, 0,08 → 0,03) ; 26 viennent de la faim ;
- en fin d'année, 20 maisons sur 35 sont à 0, 11 au-dessus de 0,03, et 0,08 au plus ;
- aucune hausse n'est causée par un chantier, parce que l'IA ne bâtit d'elle-même qu'avec #426. La preuve « bâtit → monte » se fait donc à Biskra, avec `gestes-exemple.json` : au tick 46, `seigneurie-6` lit 630 kg de salaires à venir, sans faim ni départ, et monte de 0,03 à 0,08 ;
- au tick 30 : 3 hausses (`grande-3`, `grande-12`, `grande-19`) ;
- le coût est d'environ 2 ms par maison qui décide (35 maisons en 68 ms), soit une à trois maisons par tick.

## Périmètre
jeu/sim/ia.py
jeu/sim/flux.py
jeu/sim/engine.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_flux.py

## Conditions de succès
Toutes les commandes se lancent depuis la racine du dépôt. Chaque nouveau test vérifie d'abord son échantillon (un échantillon vide échoue) et contient sa contre-épreuve sous `pytest.raises(AssertionError)`.

**SC1 — Le registre note les lieux affamés.** `python3 -m pytest jeu/sim/tests/test_flux.py -q -k affames`. `test_flux_affames_notes` joue la graine 0 jusqu'à ce qu'au moins un lieu ait faim, puis exige qu'après chaque tick `monde.flux.jours[t].affames` égale `{(cid, lieu.rang)` avec `population > 0` et `duree_faim_ticks > 0}`, relu sur `monde.cells`. Il vérifie aussi `noter_affames(m, set())` sans jour créé, et l'absence de `affames` dans `to_dict()`.
- Contre-épreuve : `flux.noter_affames` remplacé par une fonction muette fait échouer l'égalité.
- `test_documentation_et_contre_epreuve` et `test_flux_des_lieux_documentation` restent verts : la section garde « aucune règle », reformulé en « aucune règle du tick ne la lit ; seule la décision de part de l'IA, hors du tick, relit départs, arrivées et lieux affamés, comme le joueur relit `/maison` ».

**SC2 — Jour, fenêtre, pureté et budget des routes.** `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k "part_jour_et_fenetre or budget_routes_seules"`.
- `test_ia_part_jour_et_fenetre` part d'un monde de la graine 0 joué 30 ticks sans IA (fixture de module, partagée avec SC5). `_ia_pure(ia.decider_intentions, monde, [])` y propose au moins une part, et chaque maison qui en propose une a `crc32(cle) % 30 == 0`. Contre-épreuve : on retire `monde.flux.jours[29]` d'une copie, et plus aucune `fixer_part` n'est proposée.
- `test_ia_budget_routes_seules` part de `_ia_monde()`. Une entrée `fixer_part` de l'année pour une maison laisse sa route proposée ; une entrée `tracer_route` la retire. Contre-épreuve : compter toutes les entrées, comme avant, retirerait la route (on le vérifie en recomptant à la main).

**SC3 — Une maison qui bâtit et dont les gens sont nourris monte sa part.** `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k part_biskra`. `test_ia_part_biskra_batit` lance `__main__._simulate(46, 0, gestes=<gestes-exemple.json>)`, sans IA : les chantiers sont déposés par `recevoir_intention` au nom de `seigneurie-6`. Puis `decider_intentions` doit proposer pour `seigneurie-6` `fixer_part` 0,03 → 0,08, avec `salaires_a_venir_kg > 0`, `lieux_affames == 0` et `partis − arrives < TAILLE_FOYER`. Un `jouer_ia` suivi d'un tick donne `monde.parts['seigneurie-6'] == 0.08`. Preuve que c'est le chantier qui fait monter :
- grenier posé à `reserve_gens_kg + 1` : elle monte quand même ;
- même réglage dans un second monde joué 46 ticks sans gestes : aucune part proposée pour `seigneurie-6` ;
- contre-épreuve : grenier posé à `reserve_voulue_kg` dans le premier monde, aucune proposition.

**SC4 — Sur un an, graine 0 : la part suit la règle, et tout passe par `recevoir_intention`.** `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k part_sur_un_an`. Une fixture de module joue l'année une fois (`World.charger(0)`, `random.Random(0)`, `jouer_ia` puis `engine.tick`, 365 fois, avec `pytest.MonkeyPatch.context()`). Elle capture chaque appel à `ia.recevoir_intention` avant de le transmettre. Avant chaque `jouer_ia`, pour les maisons dont c'est le jour, elle relit les raisons avec `_lire_raison_part(monde, cle)`. Cette fonction n'appelle pas `sim/ia.py` : ses lieux sont ceux dont `lieu.maitre == cle`, et elle lit `monde.flux.jours`, `greniers`, `plans` et les constantes. `test_ia_part_sur_un_an` exige :
- chaque entrée `fixer_part` a une raison égale à la lecture de son tick, et sa direction obéit à la règle : baisse ⇔ perte ou faim ; hausse ⇔ ni l'une ni l'autre, et grenier < réserve voulue ; nouvelle part bornée et arrondie comme dit plus haut ;
- toute maison lue sans entrée ce jour-là aurait gardé sa part ;
- au moins une baisse avec `partis − arrives ≥ TAILLE_FOYER` et `lieux_affames == 0` (prototype : 16), et au moins une hausse (prototype : 31) ;
- aucun refus ;
- les intentions `fixer_part` capturées égalent celles du relevé, dans l'ordre ;
- `monde.parts` final égale `PART_COUTUMIERE` rejoué entrée par entrée.

Contre-épreuves : `partis + 1` dans une raison copiée, une baisse retournée en hausse, ou un relevé vide font échouer le contrôle. `test_an_ia_sans_refus` peut lire la même fixture pour ne pas jouer l'année deux fois.

**SC5 — Le chemin unique.** `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k part_chemin_unique`. `_controle_chemin_unique(monde, jouer)` travaille sur le monde du tick 30 (SC2). Il remplace `ia.recevoir_intention` par un greffier qui ne dépose rien, appelle `jouer(copie, releve)`, puis exige trois choses : `copie.__dict__` est inchangé (parts et file compris), les intentions vues égalent celles du relevé, et au moins une est une `fixer_part`. Avec le vrai `jouer_ia` suivi d'un tick, les parts des maisons qui ont décidé valent celles du relevé. Contre-épreuve : une IA tricheuse prend les mêmes propositions mais écrit `monde.parts[cle] = part` sans déposer, et le contrôle échoue.

**SC6 — Les quatre tests de l'IA, réécrits selon la réponse A, aussi exigeants sur les routes.** `python3 -m pytest jeu/sim/tests/test_monde.py jeu/sim/tests/test_intentions.py -q -k "ia_raisons_egalent_le_monde or ia_mesure_reelle or terres_ia or an_ia_sans_refus"`.
- `test_ia_raisons_egalent_le_monde` :
  - `_verifier_raisons` exige que chaque entrée soit `tracer_route` ou `fixer_part` ;
  - `_controler_raisons` contrôle les entrées `tracer_route` et en exige au moins une. Contre-épreuve ajoutée : un relevé fait seulement de `fixer_part` échoue ;
  - la liste figée des ticks de route est remesurée. Prototype : `[25, 37, 39, 61, 64, 69]` au lieu de `[25, 36, 39, 61, 64, 69]`. Le codeur écrit la liste qu'il mesure et la cite dans sa PR ;
  - les trois mutations existantes restent.
- `test_ia_mesure_reelle` :
  - `verifier` exige au moins une route, et `intention['cell']` égal à la capitale pour chaque route ;
  - pour chaque part, il exige `tick == 30`, `intention['maison']` égal à la clé de la maison, et pas de `cell` (prototype : 3 parts) ;
  - contre-épreuves existantes gardées, plus une part au tick 29 qui doit échouer.
- `test_terres_ia` : `recevoir` vérifie le maître du bourg pour les intentions qui ont une `cell`. Pour une `fixer_part`, il vérifie que la maison est maître d'au moins un lieu. `depots == intentions du relevé`, et `verifier` reste tel quel.
- `test_an_ia_sans_refus` : `entree` cherche parmi les entrées `tracer_route` ; le reste est inchangé.

**SC7 — Documentation.** `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k part_documentation`. La section « Les décisions et les gestes de l'IA » doit contenir `part_sur_projets_et_gens`, `RESERVE_VOULUE_JOURS`, `RESERVE_VOULUE_PART_DES_HABITANTS`, `IA_PAS_DE_PART`, `TAILLE_FOYER`, `affames`, `crc32`, « niveau 2 » et la mesure en ms. Contre-épreuve : la section retirée du texte fait échouer le contrôle. La phrase « Niveau 3 : … et les départs (la raison porte −1 : le monde ne les compte pas) » est corrigée : −1 reste dans la raison de la route, et la part, elle, compte les départs.

**SC8 — Rien d'autre ne rougit, et le tick tient son budget.**
- `python3 -m pytest jeu -q` est vert ;
- `python3 -m pytest jeu/sim/tests/test_monde.py -q -k tick_sous_le_budget` reste sous `BUDGET_TICK_MS` ;
- `cd jeu && python3 -m forge --ticks 365 --seed 0 --ia --sortie /tmp/f424` rend 0, et sa photographie porte des entrées `fixer_part`.

## Hors périmètre
- Ouvrir son grenier (#425), bâtir de soi-même (#426), faire jouer les petits seigneurs plausibles (#427).
- Montrer les parts et les raisons dans le service, la photographie lisible ou Unity (#428, #429). `lignes_de_l_ia` affiche déjà un type inconnu sous la forme `type k=v`.
- Calibrer `PART_COUTUMIERE` ou le pas de 0,05. Prélèvement, convois, dû et départs restent tels quels.
- Compter lieu par lieu (réponse B écartée), ou couper la décision de part dans les tests (réponse C écartée).
- Toute autre mémoire de la faim que `affames` dans la fenêtre des flux. `duree_faim_ticks` ne change pas.
