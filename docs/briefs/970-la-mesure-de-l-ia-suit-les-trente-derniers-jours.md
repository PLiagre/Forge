# Lot #970 — La mesure de l'IA suit les trente derniers jours
Jalon : J5 · Machine : vps · Taille prévue : 90 lignes

## But
`maisons_actives_30j` compte les maisons de l'IA qui ont déposé un geste accepté pendant les trente derniers jours, et plus seulement pendant les trente premiers. Les tests de l'IA qui jouaient 30 jours en jouent 31, avec les mêmes exigences, et tout reste vert avec la règle actuelle de l'IA.

## Le joueur
C'est un lot de fond. Il prépare le geste du jalon J5 « laisser filer les années et voir toutes les maisons agir, chacune pour ses raisons ». La preuve du jalon le demande aussi : « chaque maison de l'IA a déposé au moins un geste ». Aujourd'hui, la ligne « L'IA : N maisons ; actives sur 30 jours » de la forge (`vues/relief/carte1400.py`) et `GET /ia` comptent toujours le premier mois. Après un an, elles disent encore ce qui s'est passé en janvier 1400. Après ce lot, elles disent combien de voisins agissent ce mois-ci. Le joueur qui laisse filer le temps voit si ses voisins sont encore actifs.

Le lot sert surtout le sous-lot 4 de #951 (réponse A du propriétaire). Le programme de l'IA y lira « le mois passé » : aucune route, aucune part, aucun secours avant le 30e jour. Mesurée sur le premier mois, l'activité vaudrait 0 pour toujours. #428 (service et photographie montrent les voisins) et #429 (la carte de Unity) rendront cette mesure visible au joueur.

## Règle du monde
Aucune règle du monde ne change. La mesure est lue hors du monde, sur le relevé de l'IA, qui reste hors de `World`. Le lot modifie la section **« ## Les décisions et les gestes de l'IA »** de `jeu/sim/MODELE.md`, au paragraphe de `python3 -m sim --ia` (« couples distincts déposés dans les trente premiers jours ») et à ceux de `GET /ia` et de la forge, qui renvoient à `maisons_actives_30j`.

**La règle de la mesure.** `maisons_actives_30j(ticks_ecoules, releve)`, dans `sim/ia.py`, avec `T = ticks_ecoules × TICK_DURATION_DAYS` et `D = IA_DUREE_MESURE_JOURS` :
- si `T < D` : −1, comme aujourd'hui, même à zéro tick ;
- sinon : le nombre de couples distincts (`maison.sorte`, `maison.id`) des entrées sans `refus` dont `T − D ≤ tick × TICK_DURATION_DAYS < T`.

Les gestes de l'IA sont notés avant le tick, avec le tick écoulé. Après `T` ticks, la fenêtre couvre donc les ticks `T − 30` à `T − 1`. À `T = 30`, elle couvre les ticks 0 à 29 : c'est exactement l'ancienne fenêtre, quel que soit le relevé. Tout appel existant à 30 ticks rend donc la même valeur. Le nom de la fonction, sa signature, ses appelants (`__main__.py`, `service.py`, `snapshot_export.py`) et les constantes ne changent pas. Seul le corps de la fonction et sa docstring changent. Les deux constantes restent lues par `_constantes.X`.

**Mesure du chef** (graine 0, base 58a59fcb, `python3 -m sim --ticks 31 --seed 0 --json --ia`, environ 15 s ; jamais recopiée dans un test) : 4 entrées et 0 refus. Ce sont une route au tick 25 et trois `fixer_part` au tick 30. Ancienne règle à 31 : 1. Nouvelle règle à 31 : 4. Les deux règles valent 1 à 30.

## Périmètre
jeu/sim/ia.py
jeu/sim/MODELE.md
jeu/sim/README.md
docs/interface/VOISINS.md
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_intentions.py
jeu/forge/tests/test_forge.py

## Conditions de succès
Les tests modifiés sont ceux que nomme l'issue, sur la réponse A du propriétaire à #951. Le lot n'en retire aucune exigence. Dans les cinq tests à 31 jours, seuls les nombres de jours changent : 30 devient 31 partout dans ces tests (ticks joués, `/tick?n=`, tick attendu, `range`, `['ia', 'tick'] * 31`). Les assertions de la mesure listées en SC1 et SC2 sont réécrites pour la fenêtre glissante. `_ia_cli` garde son défaut de 30 ticks : les trois tests qui changent lui passent `ticks=31`. `test_ia_rejeu_octets`, `test_snapshot_ia_gestes` et `test_forge_ia_sans` ne bougent pas.

- **SC1 — La mesure suit la fenêtre glissante sur le vrai monde.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k ia_mesure_reelle`. `verifier` et ses trois contre-épreuves restent tels quels. Le test regroupe les contrôles de la mesure dans une aide `controler_mesure(fonction, resume, releve)` :
  - `compte` est dérivé dans le test sur les entrées acceptées de ticks `31 − 30` à `30`. On a `0 < compte ≤ len(capitales)` et `resume['ia']['maisons_actives_30j'] == fonction(31, releve) == compte` ;
  - `fonction(29, releve) == -1` et `fonction(31, releve * 2) == compte` ;
  - une entrée acceptée d'une maison `tardive` au tick 30 compte : `compte + 1`. La même au tick 1 (`T − 30`) compte aussi. La même au tick 0 (`T − 31`) ne compte pas : `compte`. La même au tick 30 avec `refus` ne compte pas : `compte` ;
  - à 30 ticks, la fonction rend la même valeur que l'ancienne règle des trente premiers jours, recopiée dans le test, sur `releve` et sur `releve` + les entrées tardives ci-dessus ;
  - `compte` diffère du nombre de couples acceptés des ticks 0 à 29 : les parts du tick 30 entrent dans la fenêtre. Les deux valeurs sont affichées par `print`.

  Contre-épreuve : `controler_mesure(ia.maisons_actives_30j, …)` passe. `controler_mesure(ancienne, …)` lève `AssertionError`, avec `ancienne` la copie de la fonction d'avant le lot.
- **SC2 — Un refus ne compte pas, et un geste vieux de plus de trente jours non plus.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -q -k ia_refus_compte_pour_l_annee`. Le début du test ne change pas (refus au tick 0, seconde passe muette, refus de l'année suivante au tick `CALENDAR_DAYS_PER_YEAR`). Les deux lignes de la mesure (`maisons_actives_30j(31, …)`) deviennent, avec `an = k.CALENDAR_DAYS_PER_YEAR` :
  - `maisons_actives_30j(an + 1, releve) == 0` : les refus du tick `an` sont dans la fenêtre et ne comptent pas ;
  - les mêmes propositions acceptées au tick `an` donnent `maisons_actives_30j(an + 1, …) == len(couples) > 0`.

  Contre-épreuves : acceptées au tick 0, elles donnent 0 à `an + 1`, puisque le geste est sorti de la fenêtre, et `len(couples)` à 30. Une copie de l'ancienne règle donnerait `len(couples)` à `an + 1` pour les acceptées du tick 0 : le test affirme que la vraie fonction diffère de cette copie.
- **SC3 — Les cinq tests jouent 31 jours, avec les mêmes exigences.**
  `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -k "ia_option_explicitement or service_ia_egal_cli or service_ia_raison"` puis `cd jeu && python3 -m pytest forge/tests/test_forge.py -q -k "forge_ia_boucle or forge_ia_sorties"`. Avec l'IA, le monde de 31 jours diffère du témoin sans IA. `GET /ia` après `/tick?n=31` est égal au résumé de la CLI à 31 ticks, avec `tick=31`, et `maisons_actives_30j > 0`. Chaque entrée porte sa raison. La forge alterne `ia, tick` 31 fois et rend le monde du témoin. Ses deux sorties à 31 jours sont identiques, avec une activité au-dessus de zéro. À zéro tick, elle rend −1. Les contre-épreuves existantes restent : IA interdite sans option, tick faussé, raison retirée, ordre inversé, IA muette, `activite([])`, geste retiré, population changée. `git diff -U0 master -- jeu/sim/tests jeu/forge/tests | grep '^-.*assert'` ne montre que des lignes réécrites dans ces cinq tests et en SC1 et SC2, et chacune a sa remplaçante.
- **SC4 — Le modèle, le README et l'interface disent la mesure.** `grep -q "trente derniers jours" jeu/sim/MODELE.md && grep -q "trente derniers jours" jeu/sim/README.md && grep -q "trente derniers jours" docs/interface/VOISINS.md && ! grep -n "trente premiers jours" jeu/sim/MODELE.md jeu/sim/README.md docs/interface/VOISINS.md`. MODELE.md dit la fenêtre (les ticks `T − 30` à `T − 1`, refus ignorés, −1 avant trente jours). Il dit aussi qu'à 30 ticks elle égale l'ancienne. Contre-épreuve : sur `master`, la même commande échoue, puisque MODELE.md et VOISINS.md disent « trente premiers jours ».
- **SC5 — Tout le reste passe.** `python3 -m pytest jeu -q` passe en entier. En particulier, `test_snapshot_ia_gestes` (mesure à 30 ticks), `test_ia_rejeu_octets` et les tests de `vues/relief/tests/test_carte1400.py` passent sans changement. Ils restent verts parce que la règle est égale à l'ancienne à 30 ticks.

## Hors périmètre
- Le programme de l'IA, la route vers le champ, `route_si_bourg_affame`, le juge de `test_monde` : sous-lots 2, 3 et 4 de #951. La règle des gestes de l'IA ne change pas ici.
- Renommer `maisons_actives_30j` ou `IA_DUREE_MESURE_JOURS`, changer leur valeur, la forme de `GET /ia`, du bloc `ia` de la photographie ou du résumé de la CLI.
- Toucher `sim/__main__.py`, `sim/service.py`, `sim/snapshot_export.py`, `sim/constants.py` et `vues/relief/carte1400.py`, dont le libellé « actives sur 30 jours » reste juste.
- Changer le défaut de `_ia_cli`, `test_ia_rejeu_octets`, `test_snapshot_ia_gestes`, `test_forge_ia_sans` et tout test que l'issue ne nomme pas.
- Corriger la phrase du README sur le refus IA qui rend 500 : elle date d'avant le relevé des refus et appartient à un autre lot.
