# Lot #1011 — Le programme décide la route de l'IA
Jalon : J5 · Machine : vps · Taille prévue : 190 lignes

## But
Dans le jeu, la route des maisons de l'IA vient du programme (`sim.programme_ia.proposer_route_vers_le_champ`) : `decider_intentions` l'appelle, l'ancienne règle `route_si_bourg_affame` et son budget annuel disparaissent, et les tests n'ont plus besoin de brancher le programme à la main.

## Le joueur
Chaque maison de l'IA dont le bourg a eu faim le mois passé trace, si son grenier le paie, une route de sa place vers son champ le plus plein, et sa raison le dit. Il le voit dès ce lot dans le relevé de l'IA : `python3 -m sim --ia`, `GET /ia` du service lancé avec `--ia`, et la forge. C'est le geste du jalon 5 « les maisons tracent leurs routes, pour des raisons qu'elles disent », et la première marche de #426 (« L'IA bâtit sa capitale quand son grenier le permet ») : la route n'est plus une ligne fixe de 40 m au bout des rues, posée une fois par an. Elle part du bord de la place vers le champ qui nourrit, et le grenier la paie. Le dossier « Les autres maisons » de Unity ne sait pas encore mettre cette raison en mots (voir « Hors périmètre ») ; #428, #322 et #429 la montreront ensuite sur la carte.

## Règle du monde
Section « Les décisions et les gestes de l'IA » de `jeu/sim/MODELE.md`, réécrite par ce lot. Le propriétaire a décidé que l'ancienne règle disparaîtrait (réponse A à #951). Le calcul est livré, non branché, par #971 ; ce lot le branche.

Chaque jour, dans l'ordre de `maisons_de_l_ia`, pour chaque maison qui n'est ni hors carte ni la maison du joueur (même en attente) :
1. Les contrôles d'aujourd'hui restent, avant tout : cellule, plan, bourg (rang 0) ou faim (`duree_faim_ticks`) absent ou non calculé lève `ValueError` avant tout dépôt.
2. **La route** : `proposer_route_vers_le_champ(monde, maison, releve)`. La maison doit tenir le bourg (`maitre_du_bourg`) ; un maître absent ou inconnu reste un refus nommé avant tout dépôt. Budget : une `tracer_route` de cette maison, acceptée ou refusée, de moins de `FENETRE_FLUX_TICKS` (30) jours au relevé suffit à la faire taire. La fenêtre des flux doit être pleine. La faim est le nombre de jours, de t − 30 à t − 1, où le bourg est noté dans `flux.jours[…].affames` ; s'il est nul, rien. Le champ visé est le lieu de rang ≥ 1 qui porte le plus de nourriture, s'il en porte (le plus petit rang à égalité). La route fait `IA_LONGUEUR_ROUTE_M` (40 m), en `IA_LARGEUR_ROUTE_M` (4 m), avec `IA_FOYERS_ROUTE` (1) foyer. Elle part du bord de la place carrée (`DEMI_COTE_PLACE_1400_M`) vers la place du champ, avec un écart de 0, ±`IA_PAS_ECART_ROUTE_DEGRES`, ±2 pas… strictement sous `ANGLE_ROUTE_INTERIEURE_DEGRES` ; on garde le premier écart dont `lieu_de_la_route` vise ce champ et que `verifier_base` accepte. Son coût est `travail_requis_de_route` × `SALAIRE_JOURNEE_KG` ; le grenier doit dépasser strictement la réserve voulue (celle de la part et du secours) plus ce coût. Sa raison, `route_vers_le_champ`, porte `grenier_nourriture_kg`, `reserve_voulue_kg`, `journees`, `cout_kg`, `faim_du_bourg_ticks`, `champs_nourriture_kg`, `champ_vise` et `ecart_degres`.
3. Puis le secours du jour, puis la part du mois, inchangés.

Toutes les propositions sont décidées avant le premier dépôt. `jouer_ia` les dépose par `recevoir_intention`, le seul chemin du joueur, et note au relevé l'acceptation ou le refus. Niveau 2, plausible, non sourcé : la faim du mois, le budget mensuel, la géométrie et le coût en grain.

## Périmètre
jeu/sim/ia.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py

## Conditions de succès
Ce que le codeur fait (numéros de ligne de master, 6fa96049 ; ceux de l'issue datent d'avant #1010) :

`jeu/sim/ia.py`
- `decider_intentions` : le calcul de `annee` et `actives` part, ainsi que tout le bloc `if maitre_du_bourg(…) … and (maison.sorte, maison.id) not in actives:` (lignes 219-234). À sa place : `route = programme_ia.proposer_route_vers_le_champ(monde, maison, releve)`, ajoutée aux propositions si elle n'est pas `None`. Les contrôles `ValueError`, le calcul de `cle`, puis le secours et la part restent, à leur place et dans cet ordre.
- **L'import circulaire** : `programme_ia` importe déjà `sim.ia` en tête. `sim/ia.py` l'importe donc dans la fonction, `from sim import programme_ia`, en première ligne de `decider_intentions`, comme `engine.py` le fait pour `sim.world`. L'appel passe par l'attribut du module, `programme_ia.proposer_route_vers_le_champ`, pour que les sondes des tests (`setattr(programme_ia, …)`) mordent. Pas de `from sim.programme_ia import …` en tête de fichier.
- `_raison_de_la_route` part, avec la chaîne `'route_si_bourg_affame'`. Les imports devenus inutiles partent aussi : `TYPE_TRACER_ROUTE`, `verifier_base`, `maitre_du_bourg` et `contenus_des_paniers`. `maisons_de_l_ia` reste, car `snapshot_export` l'importe depuis `sim.ia`. La docstring du module et celle de `decider_intentions` ne changent pas.
- `sim/programme_ia.py` ne change pas.

`jeu/sim/tests/test_monde.py`
- `_AMORCAGE_PROGRAMME` et `_brancher_programme` (lignes 3924-3958) partent. `_JOURS_DU_PROGRAMME` reste.
- `test_ia_rejeu_octets`, `test_ia_mesure_reelle` et `test_service_ia_egal_cli` : ils lisent `_JOURS_DU_PROGRAMME` seul et appellent `_ia_cli(…)` et `_lancer_service_ia()` sans `amorcage`. Le paramètre `amorcage` de `_ia_cli`, de `lancer_service` et de `_lancer_service_ia` reste : d'autres tests s'en servent.
- `test_ia_raisons_egalent_le_monde` : le bloc `with pytest.MonkeyPatch.context() as branche:` et `_brancher_programme(branche)` partent, et `releve = _verifier_raisons(_JOURS_DU_PROGRAMME)` reste, désindenté.
- Rien d'autre ne change : ni `_lire_raison_monde`, ni la branche « ancienne » de `_controler_raisons`, ni la contre-épreuve `regle_ancienne`, ni les données écrites à la main des lignes 4236 et 4511.

`jeu/sim/tests/test_intentions.py`
- `_ia_monde` : les lignes 911-913 (`if regle == 'programme':` et le branchement) partent. La docstring ne dit plus que le montage du programme. La signature et le reste ne changent pas.
- `test_ia_budget_annuel_et_branches` : la ligne 1017 (`ancienne = …`) et les lignes 1045-1046 (la contre-épreuve de l'ancienne règle) partent. Le budget mensuel reste prouvé par les lignes 1030-1050 et par `test_ia_budget_routes_seules`, qui ne change pas.
- `annee_programme` : l'import (ligne 1631) et l'appel (ligne 1644) de `_brancher_programme` partent. La docstring ne dit plus « branchée ». `annee_ia` reste telle quelle : `test_ia_part_sur_un_an` la lit.
- `test_ia_base_route_avant_depot` : ligne 1474, la sonde ne remplace plus que `programme_ia.verifier_base`, car `sim.ia` n'a plus de `verifier_base` (`setattr` lèverait `AttributeError`). Elle ne mordait que sur l'ancienne règle : ce n'est pas un assouplissement.
- `test_ia_grenier_decision` : l'import (ligne 2302) et l'appel (ligne 2305) de `_brancher_programme` partent.
- **Nouveau test `test_ia_ordre_route_secours_part`**, après `test_ia_grenier_decision`. Il part de `_ia_monde(monkeypatch, 'programme')`. Il prend une maison du montage dont c'est le jour de part (`ia._jour_de_la_part(cle, monde.ticks_ecoules)`) et qui a une route dans `ia.decider_intentions(monde, [])` ; il exige qu'il en existe une. Il porte son bourg à `duree_faim_ticks = FAIM_AVANT_SECOURS_JOURS + 1` et à `dette_alimentaire_kg = 1000`, et exige deux choses. D'abord, les types de ses propositions sont exactement `['tracer_route', 'ouvrir_grenier', 'fixer_part']`. Ensuite, les maisons des propositions apparaissent dans l'ordre de `ia.maisons_de_l_ia(monde)`, chacune en un seul bloc. Si la part de cette maison est nulle, il la porte d'abord à `PART_COUTUMIERE`.
- **Nouveau test `test_ia_route_documentation`**, après `test_ia_part_documentation` et sur son modèle. La section « Les décisions et les gestes de l'IA » contient `route_vers_le_champ`, `proposer_route_vers_le_champ`, `FENETRE_FLUX_TICKS`, `affames`, `IA_PAS_ECART_ROUTE_DEGRES`, `travail_requis_de_route`, `SALAIRE_JOURNEE_KG` et `reserve_voulue_kg`, et ne contient plus `route_si_bourg_affame`. Contre-épreuve dans le test : la section retirée lève `AssertionError` ou `IndexError`, et une section où l'on remet `route_si_bourg_affame` lève `AssertionError`.

`jeu/sim/MODELE.md`, section « Les décisions et les gestes de l'IA »
- Le premier bloc (de « `sim/ia.py` décide sans écrire » à « `y = largeur × nombre de rues`. ») et, dans le paragraphe « Paramètres relus… », la description de la raison (`regle (route_si_bourg_affame)`… `departs (−1)`) sont réécrits selon « Règle du monde » ci-dessus : contrôles, maître du bourg, budget mensuel lu au relevé, refus compris, faim du mois lue dans `affames`, champ le plus plein, tracé et écarts, coût, grenier au-dessus de la réserve plus le coût, champs de la raison. Les phrases sur l'exclusion du départ choisi, `jouer_ia`, le relevé et `maisons_actives_30j` restent.
- « La raison d'une route porte des départs à −1 : ce geste ne les compte pas » devient « La route ne lit pas les départs ; la part, elle, les compte ». « une part déposée dans l'année ne bloque pas le tracé » devient « dans le mois ».
- Les paragraphes de la part et du secours, et les mots que leurs tests cherchent, restent tels quels.

SC1 — L'ancienne règle n'existe plus, et l'import tient dans les deux sens. `cd jeu && grep -rn "route_si_bourg_affame\|_raison_de_la_route\|_brancher_programme\|_AMORCAGE_PROGRAMME" sim/ia.py sim/programme_ia.py sim/MODELE.md sim/tests/test_intentions.py` ne rend rien (sauf la contre-épreuve de `test_ia_route_documentation`). `grep -c "_brancher_programme\|_AMORCAGE_PROGRAMME" sim/tests/test_monde.py` rend 0. `python3 -c "import sim.programme_ia"` et `python3 -c "import sim.ia"` réussissent, chacun dans un processus neuf. Contre-épreuve : sur master, le premier `grep` liste entre autres `sim/ia.py:25`, `sim/ia.py:32`, `sim/ia.py:234`, `sim/MODELE.md:2667` et `sim/tests/test_intentions.py:913`, et le second rend 6. Dans une copie jetée ensuite, un `from sim.programme_ia import proposer_route_vers_le_champ` en tête de `sim/ia.py` fait échouer `python3 -c "import sim.programme_ia"` (`ImportError`, import circulaire).

SC2 — Le vrai `decider_intentions` propose la route du programme, sans branchement de test. `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k "lecture_locale or lecture_refus_avant_depot or registre_choix or budget_annuel or depot_commun or raison_lue or refus_compte or base_route_avant_depot or an_ia_sans_refus or terres_ia or budget_routes_seules or grenier_decision or ordre_route_secours_part"` passe, aucun cas sauté. Puis `python3 -m pytest sim/tests/test_monde.py -q -k "rejeu_octets or mesure_reelle or raisons_egalent_le_monde or service_ia_egal_cli or ia_option_explicitement or service_ia_raison"` passe. Contre-épreuve : dans une copie jetée ensuite, la ligne `route = programme_ia.proposer_route_vers_le_champ(…)` devient `route = None`. Les cas qui passent par `_ia_monde(…, regle)` rougissent alors (`regles == {'route_vers_le_champ'}` voit un ensemble vide). Rougissent aussi `test_an_ia_sans_refus` (aucune `route_vers_le_champ` dans l'année), `test_ia_rejeu_octets`, `test_ia_raisons_egalent_le_monde` (« aucune route du programme ») et `test_service_ia_egal_cli`.

SC3 — L'ordre route, secours, part tient, et les contrôles restent avant. `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k "ordre_route_secours_part or lecture_refus_avant_depot or grenier_decision"` passe. Contre-épreuve, dans une copie jetée ensuite : le bloc du secours déplacé avant l'appel du programme fait rougir `test_ia_ordre_route_secours_part`. Les contrôles `ValueError` retirés de `decider_intentions` font rougir `test_ia_lecture_refus_avant_depot` aux cas `faim` et `faim_absente` : le programme ne lit pas `duree_faim_ticks`, donc rien ne lève.

SC4 — Le budget est mensuel, refus compris. `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k "budget_annuel or budget_routes_seules or refus_compte"` passe. Contre-épreuve : dans une copie jetée ensuite, `programme_ia._route_deja_proposee_ce_mois` qui rend toujours `False` fait rougir `test_ia_budget_annuel_et_branches` (quatre routes par maison dans le mois) et `test_ia_budget_routes_seules`.

SC5 — La règle est écrite. `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k "documentation"` passe : `test_ia_route_documentation`, `test_ia_part_documentation`, `test_ia_grenier_documentation` et `test_ouverture_documentation`. `grep -c "route_si_bourg_affame" sim/MODELE.md` rend 0. Contre-épreuve : la sienne, dans `test_ia_route_documentation`. Sur master, ce test rougirait (`route_vers_le_champ` est absent de la section).

SC6 — Rien d'autre ne bouge. `cd jeu && python3 -m pytest sim/tests/test_intentions.py sim/tests/test_monde.py sim/tests/test_programme_ia.py sim/tests/test_prelevement.py forge/tests/test_forge.py -q` passe, puis `python3 -m pytest jeu -q` depuis la racine. Contre-épreuve : dans une copie jetée ensuite, la ligne 1474 de `test_ia_base_route_avant_depot` remise à `for module in (ia, programme_ia):` fait tomber ses deux cas (`AttributeError` : `sim.ia` n'a plus de `verifier_base`). Dernière vérification : `git diff --name-only origin/master` ne liste que les quatre fichiers du périmètre et ce brief.

## Hors périmètre
- **Le dossier « Les autres maisons » de Unity** (`3d/unity/Assets/Interface/DossierVoisins.cs`) ne met en mots que `route_si_bourg_affame`. Après ce lot, une route de l'IA y lit « Raison non interprétée par cette vue. », comme le secours et la part aujourd'hui. Lui donner la phrase de `route_vers_le_champ` (faim du mois, champ visé, coût et grenier) est un lot `pc` à créer, avant #429.
- Fondre `annee_ia` et `annee_programme`, qui jouent maintenant la même année : la mesure du temps y gagnerait, mais `test_ia_part_sur_un_an` et `test_an_ia_sans_refus` changeraient de fixture. C'est un lot d'outil à part.
- Retirer des juges de `test_monde.py` la lecture de l'ancienne raison (`_lire_raison_monde`, la branche « ancienne » de `_controler_raisons`) et les données écrites à la main qui portent `route_si_bourg_affame` : elles ne rougissent pas. Un nettoyage à part.
- Renommer `test_ia_budget_annuel_et_branches` ou `test_ia_refus_compte_pour_l_annee`.
- `sim/programme_ia.py`, ses constantes et `sim/tests/test_programme_ia.py` : la règle elle-même ne change pas.
- `jeu/sim/tests/durees.json` : il ne borne rien.
- Les autres gestes de l'IA (bâtir sa capitale, la suite de #426) et le fil des nouvelles.
