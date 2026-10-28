# Lot #425 — L'IA ouvre son grenier quand ses gens ont faim
Jalon : J5 · Machine : vps · Taille prévue : 290 lignes

## But
Chaque maison de l'IA secourt chaque jour ses lieux durablement affamés avec le grain disponible au-dessus de la moitié de sa réserve voulue, par le même `ouvrir_grenier` que le joueur.

## Le joueur
Dans une mauvaise année, le joueur voit ses voisins nourrir leurs gens — ou les laisser partir chez lui. Celui qui garde son grain pour bâtir le paie en foyers. Après ce lot, le secours existe dans le monde et son geste avec sa raison entre au relevé brut de l'IA ; #428 et #429 le rendront lisible sur la carte. Le joueur peut alors préparer la décision du jalon J5 : se méfier d'un voisin qui affame ses lieux, ou se servir de l'attraction d'une terre mieux nourrie.

## Règle du monde
Découle de `jeu/sim/MODELE.md`, sections « Le grenier d'une maison », « Le prélèvement » et « Les décisions et les gestes de l'IA ». Niveau 2 : le délai, la réserve et la règle de secours sont plausibles, jamais sourcés. Décision du propriétaire : le secours est quotidien après plus de sept jours de faim ; seul le réglage de la part reste mensuel.

`constants.py` ajoute `FAIM_AVANT_SECOURS_JOURS = 7`, en jours. À chaque appel de `decider_intentions`, pour chaque maison de l'IA sur carte qui n'est pas celle du joueur :

- ses lieux sont ceux de `_lieux_de_la_maison`, donc de l'index des routes ; un lieu est à secourir si `duree_faim_ticks * TICK_DURATION_DAYS > FAIM_AVANT_SECOURS_JOURS` et `dette_alimentaire_kg > 0` ;
- la réserve voulue est exactement celle de #424 : nourriture de trente jours pour 10 % de tous ses habitants, plus les salaires restant dus par les chantiers des bourgs qu'elle tient. Le calcul commun est extrait de `_lire_part` afin que part et secours ne puissent pas diverger ; contrairement à la décision mensuelle, il ne lit pas les trente jours de flux et fonctionne dès le huitième jour ;
- `plancher_kg = reserve_voulue_kg / 2`, `disponible_kg = max(0, grenier_nourriture_kg - plancher_kg)` et `dette_affamee_kg` est la somme des dettes des seuls lieux à secourir ;
- si `disponible_kg > 0`, elle propose `{"type": "ouvrir_grenier", "maison": cle, "kg": min(disponible_kg, dette_affamee_kg)}`. Elle se tait à sept jours, à dette nulle, ou lorsque le grenier est exactement au plancher. Le geste existant répartit ensuite ce grain entre les lieux tenus selon les dettes, le transporte et le perd comme l'ouverture du joueur ; ce lot ne crée aucun raccourci de livraison ;
- la raison vaut `regle: "secours_apres_faim"` et porte, sans arrondi, la liste triée des lieux à secourir (`cell_id`, `rang`, `duree_faim_ticks`, `dette_alimentaire_kg`), `grenier_nourriture_kg`, `reserve_voulue_kg`, `plancher_kg` et `dette_affamee_kg`.

Pour une même maison et un même jour, l'ordre des propositions est route, secours, puis éventuelle part mensuelle. Comme aujourd'hui, `jouer_ia` décide tout avant le premier dépôt, appelle uniquement `recevoir_intention` et copie chaque proposition, raison comprise, dans le relevé. Un refus reste noté et n'arrête pas les autres maisons. Aucun budget annuel ou mensuel ne limite le secours : si la faim et l'excédent subsistent le lendemain, la maison peut ouvrir de nouveau.

## Périmètre
jeu/sim/ia.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_prelevement.py

## Conditions de succès
Toutes les commandes se lancent depuis la racine. Les nouveaux contrôles exigent un échantillon non vide et prouvent d'abord leur rouge.

SC1 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k ia_grenier_decision` prouve sur un monde d'épreuve qu'une maison propose chaque jour un unique `ouvrir_grenier` dès que l'un de ses lieux dépasse sept jours de faim. L'intention ouvre exactement le minimum entre la dette des lieux admissibles et l'excédent au-dessus de la moitié de la réserve de #424 ; sa raison égale une lecture indépendante du monde. Elle fonctionne sans fenêtre de flux pleine. À sept jours, à dette nulle, au plancher exact, sans lieu tenu, hors carte ou pour la maison du joueur, aucune ouverture n'est proposée ; route et part gardent leurs règles. Contre-épreuves : remplacer `>` par `>=`, omettre les salaires de la réserve, prendre toute la dette ou descendre sous le plancher fait échouer les égalités.

SC2 — `python3 -m pytest jeu/sim/tests/test_prelevement.py -q -k ia_ouverture_baisse_dette` joue deux copies affamées et identiques, production neutralisée : dans l'une `jouer_ia` dépose un secours, dans l'autre l'IA se tait. Le relevé contient au moins un `ouvrir_grenier` accepté et, après le délai réel des routes, la somme des dettes de ses lieux est strictement plus basse que dans le témoin. Le grenier ne passe jamais sous son plancher au dépôt. Contre-épreuves : rendre `recevoir_intention` muet ou neutraliser la livraison des secours fait échouer la direction.

SC3 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k ia_grenier_chemin_unique` étend le contrôle du chemin unique : avec `ia.recevoir_intention` remplacé par un greffier, le monde entier reste identique et les intentions vues égalent exactement celles du relevé, dont au moins une `ouvrir_grenier`. Avec le vrai dépôt puis un tick, le grenier et les secours changent par l'intention. Contre-épreuve : une fausse IA qui débite directement `monde.greniers` ou écrit `monde.secours` sans appeler le dépôt fait échouer le contrôle.

SC4 — `python3 -m pytest jeu/sim/tests/test_intentions.py jeu/sim/tests/test_monde.py -q -k "terres_ia or ia_raisons_egalent_le_monde"` garde les contrôles existants des routes et des parts et ajoute `ouvrir_grenier` à leur liste fermée. `test_terres_ia` traite explicitement les trois types et exige que la maison de chaque ouverture tienne au moins un lieu ; tout type inconnu échoue. Le contrôle des raisons relit indépendamment les champs de `secours_apres_faim`. La liste exacte des ticks de route est remesurée sur la graine 0 et reste figée pour le nouveau monde, sans retirer aucune contre-épreuve existante. Contre-épreuves : changer la maison, la dette, la faim, le plancher ou retirer l'intention du relevé fait échouer le contrôle.

SC5 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k ia_grenier_documentation` exige dans « Les décisions et les gestes de l'IA » la constante, le seuil strict, le calcul partagé de la réserve, le plancher, la raison et le dépôt par `recevoir_intention`. Retirer la section ou l'un de ces termes fait échouer le contrôle.

SC6 — `python3 -m pytest jeu -q` et `git diff --check` réussissent. Aucun test existant n'est assoupli : les assertions qui fermaient les gestes à route et part sont étendues avec des vérifications propres au secours.

## Hors périmètre
Montrer une phrase de raison ou le secours sur la carte (#428, #429), changer `ouvrir_grenier`, sa répartition, les routes ou les pertes de convoi, anticiper le grain déjà en route, modifier la fréquence mensuelle de `fixer_part`, faire bâtir l'IA (#426), faire jouer les petits seigneurs plausibles (#427), recalibrer les constantes de #424, ou changer le service et la photographie qui publient déjà le relevé. Aucun fichier hors périmètre n'est modifié.
