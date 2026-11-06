# Lot #999 — Les tests de la règle des routes passent sur le programme
Jalon : J5 · Machine : vps · Taille prévue : 230 lignes

## But
Cinq tests de l'IA (budgets, grenier, une année sans refus, terres) se jouent aussi avec la route vers le champ le plus plein, branchée par `_brancher_programme`, et prouvent que les budgets, le grenier et les terres de l'IA tiennent avec elle.

## Le joueur
Le joueur y gagne des preuves que les budgets, le grenier et les terres de l'IA tiennent avec la route qui part vers le champ le plus plein. Lot de fond du geste du jalon 5 « regarder le monde vivre » : sur la carte, les maisons de l'IA tracent leurs routes pour des raisons qu'elles disent. Le branchement du programme dans `decider_intentions` (sous-lot de #987) rendra cette route visible au service et à la forge, puis #429 sur la carte de Unity ; ce lot garantit d'avance qu'avec elle une maison ne trace pas deux routes dans le mois, qu'un grenier qui ne couvre pas sa réserve ne trace rien, qu'une année entière se dépose sans refus et que chaque route est déposée au nom du maître du bourg.

## Règle du monde
Sans objet : `sim/ia.py`, `sim/programme_ia.py` et `jeu/sim/MODELE.md` ne bougent pas. Les tests relisent deux règles déjà sur la base :
- l'ancienne (`route_si_bourg_affame`, `sim/ia.py`, `MODELE.md` « Les décisions et les gestes de l'IA ») : une route par maison et par année civile ;
- le programme (`route_vers_le_champ`, `sim/programme_ia.py`, décidé en #951) : une route par maison tous les trente jours (`FENETRE_FLUX_TICKS`, refus compris), seulement si le bourg a eu faim le mois passé et si le grenier dépasse strictement la réserve voulue plus le coût de la route.

Mesures sur la base 513d0b56 (prototype `/tmp/proto999`, graine 0) :
- montage `_ia_monde(…, 'programme')` au tick 30 : 35 maisons, 16 routes du programme ; `maisons[0]` (Lancastre) n'en trace pas, la première qui trace est grande-2 (Stuart) ; des deux seigneuries, Bar (1) trace, la Morée (3) non ;
- budget : aux ticks 30, 30, 31, 59 (`_mois_affame`), 16 routes et 0 refus ; au tick 60, toujours en 1400, 32 routes et 0 refus ;
- grenier de grande-2 : réserve voulue 295 602 kg, coût 243 kg ; à 0, à la moitié de la réserve et à réserve + coût, aucune route ; à réserve + coût + 1, la route ;
- `_monde_de_secours` (mois plein, jour de part) : `['ouvrir_grenier', 'fixer_part']` sous le programme ; il n'a pas de places (`_places_de` → None), donc l'absence de route n'y prouve rien seule ;
- `programme_ia.verifier_base` neutralisé au montage : le programme pose la route d'écart 0 et `jouer_ia` la fait refuser (« maison de 1400 … touchée », cellules 10237, 10231…) ;
- `test_terres_ia` sur grande-2 : un autre maître → `[]` ; maître `None`, `'inconnu'`, `True` → `IntentionRefusee` « maître absent ou inconnu » ; maître rendu → `['tracer_route']` ;
- une année (365 ticks) branchée sur le programme : 281 s sur le VPS, 0 refus, 70 `fixer_part`, 17 `ouvrir_grenier`, 7 `tracer_route` toutes `route_vers_le_champ` (ticks 65 grande-22, 68 grande-9, 70 grande-2, 70 grande-28, 94 seigneurie-3, 98 grande-9, 361 grande-2), chaque route déposée au nom du maître du bourg. Une seule fixture sert donc SC3 et SC5 : une seconde année coûterait encore près de cinq minutes.

## Périmètre
jeu/sim/tests/test_intentions.py

## Conditions de succès
Chaque test touché porte `@_REGLES_IA` (variantes `ancienne` et `programme`) ; la variante `ancienne` garde mot pour mot les assertions d'aujourd'hui. La variante `programme` passe par `_ia_monde(monkeypatch, 'programme')`, ou, pour un monde chargé, par `_brancher_programme` dans un `pytest.MonkeyPatch.context()`. Aucune autre ligne du fichier ne change, hors l'appel imbriqué de `test_ia_registre_choix`, qui passe `(monkeypatch, 'ancienne')` à `test_ia_budget_annuel_et_branches`.

SC1 — `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k "budget_annuel_et_branches or registre_choix" -q` passe. Variante `programme` de `test_ia_budget_annuel_et_branches` : les branches comparent les couples qui proposent une route du programme, moins la seigneurie choisie ou en attente, et Bar au moins en fait partie (sinon l'exclusion ne mord pas) ; le budget joue `jouer_ia` aux ticks t, t, t+1, t+29 portés par `_mois_affame` et compte 16 `tracer_route` (une par maison qui trace, aucun refus), puis 32 au tick t+30, dans la même année. Contre-épreuves : l'oubli du relevé (`deepcopy` du monde, relevé vide) redépose et dépasse le compte ; au tick t+30, sur le même relevé, l'ancienne règle (`ia.decider_intentions` d'origine, gardée avant le branchement) ne propose aucune route aux 16 maisons qui ont déjà tracé — le budget du programme est bien mensuel, celui de l'ancienne annuel.

SC2 — `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k budget_routes_seules -q` passe. Variante `programme` : la maison est la première qui trace sous le programme (pas `maisons[0]`) ; une part au relevé ne bloque pas sa route, une route datée du tick courant la bloque, une route datée de t − `FENETRE_FLUX_TICKS` ne la bloque plus et une route datée de t − `FENETRE_FLUX_TICKS` + 1 la bloque encore. Contre-épreuves : `assert not routes([part])` échoue ; sous l'ancienne règle, la route datée de t − `FENETRE_FLUX_TICKS` (même année) bloque encore — la variante `ancienne` l'affirme aussi.

SC3 — `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k an_ia_sans_refus -q` passe. Une fixture de module neuve, `annee_programme`, joue la même année que `annee_ia` (graine 0, 365 ticks, `jouer_ia` puis `engine.tick`) avec `_brancher_programme` dans un `pytest.MonkeyPatch.context()` ; elle garde le relevé et, pour chaque dépôt, l'intention et le maître du bourg (rang 0) de sa cellule au moment du dépôt. `annee_ia` ne change pas. Variante `programme` : au moins une route `route_vers_le_champ` acceptée et aucun refus dans le relevé. Contre-épreuve : au montage, `programme_ia.verifier_base` neutralisé, `jouer_ia` note au moins un refus « touchée » sur une `tracer_route` du programme — c'est le contrôle de la base dans le programme qui garde l'année sans refus.

SC4 — `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k "grenier_decision" -q` passe. Variante `programme` (`_brancher_programme(monkeypatch)` après le premier `maisons_de_l_ia`) : tout le test d'aujourd'hui tient, sauf les deux listes du mois, qui deviennent `['ouvrir_grenier', 'fixer_part']` puis `['ouvrir_grenier']` (un grenier vide ne trace aucune route). Contre-épreuve, sur le montage `_ia_monde(monkeypatch, 'programme')`, la première maison qui trace : grenier à 0, puis à réserve voulue + coût (lus dans la raison de sa route) → aucune route de cette maison ; à réserve + coût + 1 → sa route revient. Sous l'ancienne règle, le même grenier à 0 trace encore : la variante `ancienne` l'affirme.

SC5 — `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k "terres_ia" -q` passe. Variante `programme` : la première partie se joue sur la première maison qui trace (un autre maître → `[]` ; `None`, `'inconnu'`, `True` → « maître absent ou inconnu » sans intention en attente ; le maître rendu → une proposition) ; la seconde lit `annee_programme` au lieu de rejouer une année : `verifier` sur son relevé (`tracer_route`, `fixer_part`, `ouvrir_grenier` présents, `maison` de chaque intention égale à l'identité de la maison), chaque `tracer_route` déposée au nom du maître du bourg noté au dépôt, les dépôts égaux aux intentions du relevé. Contre-épreuves : `verifier([])` et `verifier(faux)` (un identifiant de maison échangé) échouent ; une route dont le maître noté est changé fait échouer le contrôle du maître.

SC6 — `cd jeu && python3 -m pytest sim/tests/test_intentions.py sim/tests/test_programme_ia.py -q` passe en entier, et `git diff --stat origin/master` ne nomme que `jeu/sim/tests/test_intentions.py`. Contre-épreuve : avec `_brancher_programme` neutralisé (corps remplacé par `return`, essai local non commis), les variantes `programme` de SC1 à SC5 rougissent toutes (l'assertion de règle de `_ia_monde` ou le compte de routes du programme).

## Hors périmètre
- Brancher le programme dans `decider_intentions`, retirer `route_si_bourg_affame`, écrire la règle dans `MODELE.md` : autres sous-lots de #987.
- `sim/ia.py`, `sim/programme_ia.py`, `jeu/sim/MODELE.md`, `test_monde.py`, `test_programme_ia.py`, `durees.json` : ne bougent pas.
- Les autres tests de l'IA (`test_ia_part_sur_un_an`, `test_ia_part_chemin_unique`, `test_ia_grenier_chemin_unique`, la forge, le service) : non rejoués ici.
- Donner des places au monde de `_monde_de_secours` ; faire lire la population au programme (constat de #986).
