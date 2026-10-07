# Lot #514 — La maison du joueur est une maison du registre
Jalon : J3 · Machine : vps · Taille prévue : 235 lignes

## But
Le monde retiendra la maison du joueur sous son identifiant du registre, `seigneurie-<n>`, pour qu'elle soit une maison comme les autres, prête à tenir des lieux.

## Le joueur
Le joueur choisit toujours sa terre par son numéro (service, `--depart` de la forge, bientôt Unity avec #404) ; sa terre choisie devient une maison du registre, celle qui tiendra ses lieux, son grenier et son dû (#391, #394, #397). Ce lot de fond prépare le geste du jalon J3, fixer sa part sur ses lieux (#395) et la voir monter vers son grenier puis vers son suzerain : sans une seule étiquette pour sa maison, #391 ne pourrait pas lui donner ses lieux. Le monde, `/monde`, le compte rendu et le refus « départ déjà choisi » disent désormais « seigneurie-3 » pour Bar ; #400 et #401 montreront ses lieux et ses flux, puis #405 dans Unity.

## Règle du monde
Découpé de #390. Dépend de : #513. Découle de « Les maisons du monde », « Les intentions du joueur », « Les maisons de l'IA et leurs capitales, vue dérivée » et « La photographie de 1400, vue dérivée » de `jeu/sim/MODELE.md`.

Décision technique A du pilote, suivie : le monde retient `seigneurie-<n>` ; les quinze lignes de tests listées plus bas sont réécrites, aucune ne devient moins exigeante.

**Un seul format.** Ajouter à `sim/seigneuries.py` deux fonctions pures : `identifiant_de_seigneurie(numero)` rend `f"seigneurie-{numero}"` ; `numero_de_seigneurie(identifiant)` rend l'entier et refuse par `SeigneurieInconnue("seigneurie inconnue : <repr>")` tout ce qui n'est pas exactement `seigneurie-` suivi de chiffres décimaux sans signe ni zéro de tête : entier nu, booléen, `None`, `"grande-3"`, `"seigneurie-03"`, `"seigneurie-"`, espace en trop. `sim/registre_maisons.py` fabrique l'id de ses fiches de seigneurie par `identifiant_de_seigneurie` (pas de second format). `seigneuries.py` est le seul endroit possible : `registre_maisons.py` importe `capitales.py`, qui ne peut donc pas l'importer.

**Le dépôt.** `deposer_intention` lit toujours le numéro entier, refuse comme avant, puis vérifie que `identifiant_de_seigneurie(n)` est une fiche de sorte `seigneurie` de `monde.maisons` ; sinon « seigneurie inconnue : <n> », sans rien mettre en attente. `ChoixDepart` garde le numéro entier (`ChoixDepart(bar)` inchangé). Le refus d'un second choix dit « départ déjà choisi : seigneurie-<n> », que le premier soit en attente ou appliqué.

**L'application.** `ChoixDepart.appliquer` pose `monde.maison_du_joueur = identifiant_de_seigneurie(self.identifiant)` sans lire `monde.maisons` : piège de #513, le tick ne consulte jamais le registre (garde `_tick_sans_lecture_registre` de `test_maisons.py`). On valide au dépôt, jamais à l'application.

**Les lecteurs.** `to_dict()` et `/monde` (`service.py`) portent la valeur telle quelle : code inchangé. `forge` copie la valeur dans `resume.json["simulation"]["maison_du_joueur"]` : code inchangé, `--depart` reste entier. `capitales.py` (`maisons_de_l_ia`) écarte la seigneurie dont `identifiant_de_seigneurie(s.id)` vaut `maison_du_joueur` ; ses lignes gardent leur `id` entier. `ia.py` compare en identifiant du registre le choix appliqué et le choix en attente (`ChoixDepart.identifiant` converti). `snapshot_export.py` appelle `fiche_de_seigneurie(numero_de_seigneurie(world.maison_du_joueur), …)` : `terre_choisie` de la photographie garde la même fiche et son `id` entier, octet pour octet ; une valeur mal formée lève `SnapshotExportError` « seigneurie inconnue ». Mettre à jour la docstring de `World.maison_du_joueur` dans `world.py`.

**Tests réécrits (valeur attendue entier → `seigneurie-<n>`), quinze lignes :** `test_intentions.py` 58 (motif du message), 61, 93, 94, 125, 247, 867 ; `test_monde.py` 3285, 3341, 3344, 3355, 3786 (la comparaison `m['id'] != monde.maison_du_joueur` deviendrait toujours vraie : comparer `identifiant_de_seigneurie(m['id'])`) ; `test_maisons.py` 702 ; `test_carte_servie.py` 40 ; `forge/tests/test_forge.py` 135. Ne toucher à aucune autre ligne existante ; `test_forge.py` 140 et 186 (`terre_choisie` entier) et `test_determinisme.py` restent tels quels.

`MODELE.md` : dans « Les intentions du joueur », la valeur posée, le message « départ déjà choisi : seigneurie-<n> », le contrôle au dépôt, `to_dict()`/`/monde`/`resume.json` portant l'identifiant du registre, et le « Niveau 2 » qui réduisait la maison à l'id de sa terre ; dans « Les maisons du monde », la maison du joueur est la fiche `seigneurie-<n>` ; dans « Les maisons de l'IA », l'exclusion par identifiant du registre ; dans « La photographie », `terre_choisie` dérivé du numéro de l'identifiant. Niveau 1 : terres et fiches inchangées. Niveau 2 : aucun ajout. Niveau 3 : lieux, grenier, part et dû du joueur, pas dans ce lot. Budget : code 35, réécritures 30, cas neufs 90, modèle 15, brief 65.

## Périmètre
jeu/sim/seigneuries.py
jeu/sim/registre_maisons.py
jeu/sim/intentions.py
jeu/sim/ia.py
jeu/sim/capitales.py
jeu/sim/snapshot_export.py
jeu/sim/world.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_carte_servie.py
jeu/forge/tests/test_forge.py

## Conditions de succès
Commandes depuis `jeu/`, sauf SC6. Écrire les cas neufs d'abord et prouver leur rouge avant l'implémentation. Les terres attendues viennent de `charger_seigneuries()`, jamais d'un total fixé ; tout échantillon est non vide.

SC1 — `python3 -m pytest sim/tests/test_intentions.py -q -k registre` (nouveau `test_choix_depart_registre`) : pour chaque terre de la table, sur `World.charger(0)`, dépôt par le numéro puis un tick ; `maison_du_joueur` et `to_dict()["maison_du_joueur"]` valent `seigneurie-<n>`, fiche de sorte `seigneurie` de `monde.maisons` dont le nom est la maison de la terre et le siège son siège ; un second dépôt est refusé par le message exact « départ déjà choisi : seigneurie-<n> », avant et après le tick. Contre-épreuves : un monde dont `maisons` est privé de cette seule fiche refuse le dépôt par « seigneurie inconnue : <n> », `to_dict()` et l'attente inchangés ; un `appliquer` remplacé pour poser l'entier fait échouer l'égalité.

SC2 — `python3 -m pytest sim/tests/test_maisons.py -q -k "registre_choix or registre_identifiant or capitale_maisons_ia"` : `test_registre_choix` applique un `ChoixDepart` déposé sous `_tick_sans_lecture_registre`, sur une copie d'un monde chargé : zéro accès à `maisons`, et la maison posée appartient au registre. Contre-épreuve : un `appliquer` qui lit `monde.maisons` lève « registre consulté au tick ». `test_registre_identifiant` : aller-retour exact pour chaque terre ; l'ensemble des ids de sorte `seigneurie` du registre égale `{identifiant_de_seigneurie(s.id)}` ; chaque valeur mal formée listée plus haut est refusée en se nommant. `test_capitale_maisons_ia_et_choix`, inchangé, reste vert. Contre-épreuve : un refus retiré de `numero_de_seigneurie` fait échouer son cas.

SC3 — `python3 -m pytest sim/tests/test_monde.py -q -k "photographie_1400 or snapshot_ia_maisons"` : lignes réécrites, plus `test_photographie_1400_registre` : avec `maison_du_joueur = "seigneurie-<n>"`, `terre_choisie` égale le document de `fiche_de_seigneurie(n)`, `id` entier ; chaque valeur mal formée, dont l'ancien entier nu, lève `SnapshotExportError` « seigneurie inconnue » sans changer `to_dict()`. Contre-épreuve : la terre d'une autre seigneurie fait échouer l'égalité ; la ligne 3786 réécrite échoue si `capitales.py` compare encore l'entier.

SC4 — `python3 -m pytest sim/tests/test_intentions.py sim/tests/test_carte_servie.py forge/tests/test_forge.py -q` : `/monde` après le tick porte `seigneurie-<n>`, l'IA écarte la terre du joueur en attente comme appliquée, `resume.json` porte `seigneurie-<n>` et `terre_choisie` garde l'entier. Contre-épreuve : `ia.py` restée sur la comparaison entière fait rougir `test_ia_budget_annuel_et_branches`.

SC5 — `python3 -c 'from pathlib import Path; t=Path("sim/MODELE.md").read_text(); assert "départ déjà choisi : seigneurie-<n>" in t and "réduite à l'"'"'id de sa terre" not in t'` réussit. Contre-épreuve : le même contrôle sur le `MODELE.md` de `master` échoue.

SC6 — Depuis la racine, `python3 -m pytest jeu -q` passe, sans autre test changé que les quinze lignes citées ; `git diff --check` réussit. Contre-épreuve : `git diff master -- jeu/sim/tests jeu/forge/tests` ne retire que ces quinze lignes, chacune remplacée par une égalité aussi stricte.

## Hors périmètre
Les lieux du joueur et leur maître (#391), grenier (#394), part (#395), dû au suzerain (#397). Aucun changement de `--depart`, du corps de `/intention`, de `ChoixDepart`, de `terre_choisie` ni des `id` entiers des lignes `ia.maisons` de la photographie et de `maisons_de_l_ia`. Pas de changement de `service.py`, `forge/__main__.py`, du tick, des données, de Unity ou Blender. Changer de départ, sauvegarder et recharger restent non simulés.
