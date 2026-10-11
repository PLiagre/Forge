# Lot #423 — Chaque geste de l'IA dit sa raison
Jalon : J5 · Machine : vps · Taille prévue : 250 lignes

## But
Chaque entrée du relevé de l'IA porte la raison de monde du geste — les nombres que la maison a lus au tick de sa décision et la règle qui a tranché — et un geste refusé au dépôt y entre avec son refus, sans arrêter la partie.

## Le joueur
Le joueur lit pourquoi son voisin a agi : « Les Valois tracent une route vers leurs champs : leur bourg a faim depuis 12 jours, leurs champs gardent 40 t ». L'IA cesse d'être une boîte noire. Après ce lot, cette raison sort du moteur avec chaque geste, par `python3 -m sim --ia`, la photographie de la forge et `GET /ia` du service ; la carte de la forge dit aussi quand un geste a été refusé. La phrase à l'écran viendra de #428 (le service et la photographie montrent les voisins et leurs raisons) et #429 (la carte de Unity). Il prépare la décision du jalon 5, s'en méfier ou s'en servir : le joueur ne peut juger un voisin que s'il sait ce qui l'a fait agir.

## Règle du monde
Découle de `jeu/sim/MODELE.md`, « Les décisions et les gestes de l'IA », que ce lot réécrit. Dépend de : #408, livré (a192c91) ; ce lot ne s'appuie **pas** sur une garde territoriale : sur la base, ni `intentions.py` ni `ia.py` ne lisent la maison d'une route. **Le comportement ne change pas** : une route par couple (`sorte`, `id`) et par année quand le bourg (rang 0) de la capitale est peuplé et affamé, mêmes maisons, même tracé, même ordre. Seule sa raison s'écrit. Aucune constante nouvelle. **Niveau 2** pour la règle (inchangée) ; la raison n'est qu'une lecture du monde. **Niveau 3** : les départs, que le monde ne compte pas.

Décision du propriétaire (réponse A, 10/10/2026) : un geste refusé au dépôt est noté au relevé avec son refus, la partie continue, et ce refus compte pour la route de l'année de cette maison. Les départs sont déclarés absents.

**La raison.** `decider_intentions` reste pure (sans écriture ni aléa) et ajoute à chaque proposition une clé `raison`, lue sur le monde avant tout dépôt du tick :

- `regle` : `"route_si_bourg_affame"`, la seule règle d'aujourd'hui (rang 0 peuplé, `duree_faim_ticks > 0`, aucune entrée de ce couple au relevé cette année) ;
- `bourg` : `population`, `duree_faim_ticks`, `dette_alimentaire_kg` et `nourriture_kg` du lieu de rang 0 de la cellule de capitale, copiés sans arrondi ;
- `champs_nourriture_kg` : la nourriture de chaque lieu de rang 1 à n, dans l'ordre des rangs, sans arrondi ni somme (la vue fera le total) ;
- `grenier_nourriture_kg` : la nourriture du panier de la maison dans `monde.greniers`, sous l'identifiant du registre (`grande-<id>` pour une grande maison, `identifiant_de_seigneurie(id)` pour une seigneurie) ; −1 si ce panier manque au registre ;
- `chantiers_en_cours` : `{"rues": n, "parcelles": n, "batiments": n}`, les tracés `en_chantier` du plan de la cellule ;
- `departs` : −1, déclaré « non calculé » : le monde ne garde aucun compte de départs (seulement `migration_remainder`), le lot n'en invente pas.

Les paniers (lieux et grenier) se lisent comme le moteur les lit pour manger (`contenus_des_paniers` : une marchandise absente pèse zéro). Mesuré sur la base 697b125, graine 0, tick 25 (Visconti, grande maison 10, Milan, cellule 10466, première route de l'année) : bourg de 20 742 habitants, `duree_faim_ticks` 1, dette 4 203,3 kg, 0,8 kg au bourg, onze champs à environ 197 500 kg chacun, grenier vide, aucun chantier. C'est exactement l'exemple de l'issue : bourg affamé, champs pleins.

**Le relevé.** `jouer_ia` décide tout avant le premier dépôt, puis dépose dans l'ordre. Un dépôt accepté ajoute `{tick, maison, intention, raison}` (pas de clé `refus`). Un dépôt qui lève `IntentionRefusee` ajoute `{tick, maison, intention, raison, refus: "<message>"}`, rien n'est déposé, et la maison suivante joue. Seule `IntentionRefusee` est rattrapée : une donnée absente (cellule, plan, bourg, faim) reste un refus nommé levé avant tout dépôt, comme aujourd'hui, et le service garde son retour arrière et son 500 pour ce cas. Le budget annuel lit toutes les entrées du relevé, refus compris. `maisons_actives_30j` ne compte que les entrées sans `refus` (« couples distincts déposés », texte actuel de MODELE). Le relevé reste hors de `World` ; `to_dict()` et l'empreinte du monde ne changent pas.

**La publication.** `python3 -m sim --ia` et `GET /ia` publient le relevé tel quel (aucun code à changer). `_photographie_ia` (`sim/snapshot_export.py`) copie aujourd'hui chaque geste clé par clé (`tick`, `maison`, `intention`) : la raison s'y perdrait ; elle copie désormais l'entrée entière (copie profonde), donc `raison` et `refus` entrent dans la photographie de la forge. `vues/relief/carte1400.py` (`lignes_de_l_ia`) ajoute à la ligne d'un geste qui porte `refus` « — refusé : <refus> », pour ne pas montrer comme tracée une route refusée ; les autres lignes restent identiques à l'octet.

**Mesures de la base** (697b125, VPS, 10/10/2026) : `python3 -m sim --ticks 365 --seed 0 --ia --json --monde-json <f>` dure environ 2 min 20 s, relève 7 routes, toutes acceptées : ticks 25, 36, 39, 61, 64, 69, 260 ; grandes maisons 10, 3, 1, 22, 16, 2, 28 (Valois : maison 3, Paris, tick 36) ; `maisons_actives_30j` = 1. SHA-256 du monde écrit : `86b7e163b013dfa44a4e75f1886eeb63086c69ed5e78895b1fdf03f460b6ebb8`. Aucun refus en graine 0 : le chemin du refus se prouve par la sonde du test.

**MODELE.md**, « Les décisions et les gestes de l'IA » : remplacer « budget dérivé des dépôts acceptés » par « budget dérivé des entrées du relevé, refus compris » ; remplacer « copie `{tick, maison: {sorte, id}, intention}` après acceptation » par la forme de l'entrée, la liste de la raison ci-dessus et le sort d'un refus ; dire que `maisons_actives_30j` ignore les refus, que les départs valent −1 (niveau 3) ; dans le paragraphe du service, « Un refus remet file et relevé » devient « Une donnée absente remet file et relevé » (un refus de dépôt n'arrête plus le tick) ; dire que la photographie porte l'entrée entière.

Budget du diff : `ia.py` 35, `snapshot_export.py` 3, `carte1400.py` 3, MODELE 14, tests 120, brief 75 ; total ≈ 250.

## Périmètre
jeu/sim/ia.py
jeu/sim/snapshot_export.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py
jeu/vues/relief/carte1400.py
jeu/vues/relief/tests/test_carte1400.py
docs/briefs/423-chaque-geste-de-l-ia-dit-sa-raison.md

## Conditions de succès
Commandes depuis `jeu/`, sauf SC7. Constater le rouge des nouvelles preuves avant l'implémentation. Échantillons non vides, références dérivées du monde. **Seule réécriture d'assertions existantes autorisée** (décision A du propriétaire) : dans `test_ia_depot_commun_et_copies`, les deux lignes `with pytest.raises(IntentionRefusee): ia.jouer_ia(monde, refus)` et `assert refus == []` sont remplacées par des preuves au moins aussi exigeantes (SC2). Toute autre assertion, contre-épreuve et valeur reste telle quelle, en particulier `assert releve == [dict(tick=0, **p) for p in propositions]` et le tracé exact de la première route (ils passent parce que la raison est dans la proposition et que l'entrée acceptée n'a pas de `refus`).

SC1 — `python3 -m pytest sim/tests/test_intentions.py -q -k ia_` : tous les tests `ia_` existants passent sans changement (hors SC2), `_ia_pure` compris (la raison est pure et déterministe). Ajouter `test_ia_raison_lue` : sur `_ia_monde()`, poser pour une maison des valeurs distinctes (population, `duree_faim_ticks` 12, dette, nourriture du bourg et de chaque champ, un panier de grenier, une rue et une parcelle `en_chantier`) ; la raison de sa proposition égale exactement ces valeurs, `regle` vaut `"route_si_bourg_affame"`, `departs` vaut −1 ; retirer le panier du grenier du registre donne −1. Contre-épreuves : changer après coup la faim, un champ, le grenier ou un chantier du monde, sans redécider, rend la raison différente du monde ; une raison où `duree_faim_ticks` vaut 12 pour un bourg à 0 échoue à la même comparaison.

SC2 — `python3 -m pytest sim/tests/test_intentions.py -q -k "depot_commun or ia_refus"` : avec `recevoir_intention` remplacé par une sonde qui lève `IntentionRefusee('refus sonde')`, `jouer_ia` ne lève pas ; `monde.__dict__` égale exactement `avant` (rien déposé, file intacte) ; le relevé égale `[dict(tick=0, refus='refus sonde', **p) for p in propositions]`, un refus par maison. Ajouter `test_ia_refus_compte_pour_l_annee` : après ces refus, un second `jouer_ia` la même année ne propose rien et ne dépose rien ; l'année suivante, toutes les maisons proposent de nouveau ; `maisons_actives_30j(31, releve)` ignore les entrées refusées (0 pour un relevé de refus seuls, le compte des acceptées sinon) ; une donnée absente (`ValueError` de `test_ia_lecture_refus_avant_depot`) lève toujours avant tout dépôt. Contre-épreuves : une entrée refusée sans `refus`, ou un relevé vide après refus, échoue ; une sonde qui dépose puis lève fait échouer `monde.__dict__ == avant`.

SC3 — `python3 -m pytest sim/tests/test_monde.py -q -k ia_raisons` : `test_ia_raisons_egalent_le_monde` appelle un assistant `_verifier_raisons(ticks)` qui joue `sim.__main__._simulate(ticks, 0, ia=True)` en enveloppant `tick` de `sim.__main__` ; avant chaque tick réel, l'enveloppe lit elle-même, sans appeler `sim/ia.py`, pour chaque maison de l'IA placée, la population, la faim, la dette et la nourriture du bourg, la nourriture des champs par rang, le panier du grenier et les chantiers du plan. Chaque entrée du relevé doit avoir une `raison` égale exactement à la lecture de sa maison à son tick ; l'assistant rend le relevé. Le test joue 70 ticks : 6 entrées attendues (ticks 25, 36, 39, 61, 64, 69), dérivées du relevé, non nulles. Contre-épreuves sur une copie : une raison dont `duree_faim_ticks` cite une faim que le bourg n'avait pas (lecture + 1), un champ changé, une entrée sans `raison`, ou un relevé vide font échouer la vérification.

SC4 — `python3 -c "from sim.tests.test_monde import _verifier_raisons; r = _verifier_raisons(365); print(len(r), [e['tick'] for e in r])"` imprime `7 [25, 36, 39, 61, 64, 69, 260]` (environ 2 à 3 min) : toutes les raisons d'une année graine 0 égalent le monde au tick de leur décision. Puis `python3 -m sim --ticks 365 --seed 0 --ia --json --monde-json /tmp/m423.json > /tmp/r423.json && sha256sum /tmp/m423.json` donne `86b7e163b013dfa44a4e75f1886eeb63086c69ed5e78895b1fdf03f460b6ebb8`, l'empreinte de la base : le monde est identique au bit près. Si master a bougé, remesurer la référence sur master avec la même commande. Dans `/tmp/r423.json`, les `tick`, `maison` et `intention` des 7 entrées égalent ceux de la base listés plus haut. Contre-épreuve : la même commande avec `IA_LONGUEUR_ROUTE_M` porté à 41 sur une copie donne une autre empreinte.

SC5 — `python3 -m pytest sim/tests/test_monde.py -q -k "ia_ or snapshot_ia or service_ia"` : tous les tests existants passent sans changement (`test_ia_rejeu_octets`, `test_ia_mesure_reelle`, `test_snapshot_ia_gestes`, `test_service_ia_refus`…). Ajouter à `test_snapshot_ia_gestes`, ou dans un test voisin, un relevé dont les entrées portent `raison` et, pour l'une, `refus` : chaque geste photographié égale l'entrée d'origine entière. Contre-épreuve : une photographie qui perd `raison` ou `refus` échoue. Ajouter que `GET /ia` d'un service `--ia` après 30 ticks publie un relevé non vide dont chaque entrée porte `raison`.

SC6 — `python3 -m pytest vues/relief/tests/test_carte1400.py -q -k capitales_ia` : `test_capitales_ia_encadre` passe sans changement. Ajouter un cas : un geste portant `refus` donne la ligne de geste suivie de « — refusé : <refus> » ; sans `refus`, la ligne est celle d'aujourd'hui. Contre-épreuve : retirer `refus` du geste fait disparaître la mention.

SC7 — Depuis la racine, `python3 -m pytest jeu -q` et `git diff --check` réussissent.

## Hors périmètre
Aucune règle de décision nouvelle : ni part (#424), ni grenier ouvert (#425), ni bâtiment (#426), ni petits seigneurs à leur tour (#427), ni rythme mensuel. Aucune phrase de raison à l'écran : service et photographie la montreront dans #428, Unity dans #429 ; la carte de la forge ne gagne que la mention d'un refus. Aucun compte de départs inventé. Aucune garde territoriale. Aucune modification de `sim/intentions.py`, `sim/service.py`, `sim/__main__.py`, `forge/`, du tick, de `World`, des constantes ni de `SNAPSHOT_SCHEMA_VERSION`. Aucun test assoupli ; tout chemin absent du périmètre est interdit.
