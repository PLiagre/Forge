# Lot #1037 — Le joueur prend la tête de n'importe quel pays de 1400
Jalon : J6 · Machine : vps · Taille prévue : 750 lignes

## But
Le choix de départ accepte toute maison du registre qui tient au moins un lieu — un royaume, un duché, un petit seigneur —, hors républiques, Église et ordres, et l'IA cesse de la jouer dès que le choix est déposé.

## Le joueur
Sur la carte de 1400, le joueur ne prend plus seulement l'une des six terres de départ : il prend la tête d'un royaume (les Valois), d'un duché ou d'un petit seigneur, et le joue. Les six terres de départ restent proposées en tête de la liste des pays jouables. Dès son choix, son pays ne bouge plus que par lui : l'IA ne fixe plus sa part, n'ouvre plus son grenier, ne trace plus ses routes, ne dépense plus ses jauges ni ses points. Ce qu'il voit dans `/pays` (ses terres, ses jauges, ses points) est à lui. Une république, l'Église ou un ordre militaire se refusent avec leur raison : ils élisent leur chef (#441). Le clic dans Unity sur un royaume viendra par un lot `pc` ; ce lot ouvre le chemin du service et de la photographie, qu'il lira.

Décision du propriétaire (réponse A, 10 novembre 2026) : la photographie accepte tout pays jouable et refuse toujours les identifiants mal formés ; les ordres militaires sont refusés comme l'Église.

## Règle du monde
Découle de `jeu/sim/MODELE.md`, « Les intentions du joueur » (le choix de départ), « Les décisions et les gestes de l'IA » (l'exclusion de la maison du joueur), « Les maisons servies, vue dérivée » (`terre_choisie`, `maisons_du_joueur` dans la photographie) et « Le pays et ses jauges » ; et de `docs/VISION.md`, décision 26 (« tous ceux qui tiennent de la terre, vassaux compris »).

- **Jouable** (module neuf `sim/jouables.py`, pur, sans écriture ni aléa) : une maison de `World.maisons` est jouable si elle n'est pas une institution et si au moins un lieu du monde l'a pour maître actuel (`lieu.maitre`, relu sur les cellules, jamais une seconde clé). Les institutions sont exactement les puissances de nature `république`, `Église` ou `ordre` (`maisons._NATURES_SANS_MAISON`) ; leur nature se relit dans la table des puissances (`charger_table`, niveau 1, sourcée). `raison_de_refus(monde, identifiant)` rend `None` ou la raison, dans cet ordre :
  1. « maison inconnue ou mal formée : <repr> » — pas une chaîne, ou pas une fiche du registre (même phrase que `ouvrir_grenier`) ;
  2. « maison non jouable : <id> (<nom>), une république élit ses magistrats » / « …, l'Église élit ses prélats » / « …, un ordre élit son maître » — selon la nature (Venise, sans lieu, est refusée comme république) ;
  3. « maison sans lieu : <id> » — aucun lieu tenu (les Djötchides, `grande-21`).
  `maisons_jouables(monde)` rend la liste des jouables : les six seigneuries de départ d'abord, par numéro, puis les grandes maisons, puis les petits seigneurs (`plausible`), chacun par identifiant ; chaque entrée porte `id`, `nom`, `sorte` et `lieux` (lieux tenus en propre).
- **Le choix** : `{"type": "choisir_depart", "maison": <id du registre>}` s'ajoute au chemin d'aujourd'hui, `{"type": "choisir_depart", "seigneurie": <n>}`, qui reste mot pour mot (sans champ, toujours « seigneurie inconnue : None »). Les deux champs à la fois : « choisir_depart : seigneurie ou maison, pas les deux ». Une maison `seigneurie-<n>` passe par l'ancien chemin et dépose le même `ChoixDepart(n)`. Toute autre maison jouable dépose un `ChoixDeMaison(maison)` gelé, dont `appliquer` pose `maison_du_joueur = maison` au tick suivant, sans relire le registre. Un choix déjà appliqué ou en attente, quel que soit son chemin : « départ déjà choisi : <id> » (409 dans le service, comme aujourd'hui).
- **L'IA** : une fonction `maison_choisie(monde)` (dans `intentions.py`) rend la clé du registre du choix appliqué, sinon de celui en attente (`ChoixDepart` converti par `identifiant_de_seigneurie`, `ChoixDeMaison` tel quel). `ia.decider_intentions` et `capitales.maisons_de_l_ia` écartent la maison dont `_cle_du_grenier` vaut cette clé — grande maison comprise, plus seulement une seigneurie. Au tick où le choix est déposé, l'IA ne propose déjà plus rien pour elle (route, secours, part, jauge, bâtiment, amélioration). Les petits seigneurs ne sont pas joués par l'IA avant #427 : pour eux, rien ne change côté IA.
- **Ses jauges et ses points** : les jauges sont déjà tenues par maison du registre (`World.jauges`, `jauges.mettre_a_jour` pour toutes les maisons) ; ce lot ne change aucune règle des jauges. Ce qui change : l'IA ne les dépense plus, et le joueur les dépense par `depenser_jauge` avec sa maison.
- **La photographie** : pour une maison jouable autre qu'une seigneurie, `terre_choisie` vaut `null` (la fiche de terre ne décrit que les six) et `maisons_du_joueur` porte sa fiche et celle de son suzerain, par `document_de_maison`, comme aujourd'hui. Une institution ou une maison sans lieu posée à la main dans `maison_du_joueur` lève `SnapshotExportError` avec sa raison. Tout autre identifiant (mal formé, entier, booléen, hors registre) suit l'ancien chemin et lève « seigneurie inconnue », sans muter le monde.
- **Le service** : `GET /jouables` sert `{"tick", "date", "jouables": maisons_jouables(monde)}` sous `verrou_tick`. `/maisons`, `/departs` et `/pays` ne changent pas (leurs clés sont figées par les tests).
- Le monde sans choix est inchangé, octet pour octet ; le chemin `seigneurie` aussi. Aucune constante neuve.

`MODELE.md` : ces quatre sections sont mises à jour (le paragraphe du choix de départ, l'exclusion de l'IA, `terre_choisie`), et la liste fermée des intentions reste la même (aucun type neuf).

## Périmètre
jeu/sim/jouables.py
jeu/sim/intentions.py
jeu/sim/ia.py
jeu/sim/capitales.py
jeu/sim/snapshot_export.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py

## Conditions de succès
- **SC1 — un royaume et un petit seigneur se choisissent.** `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k "tout_pays" -q` : sur `World.charger(0)`, `{"type": "choisir_depart", "maison": "grande-3"}` (Valois) puis un tick donnent `maison_du_joueur == "grande-3"` ; de même pour le premier petit seigneur jouable de `maisons_jouables` (`plausible-…`). Avant le tick, `to_dict()` est inchangé et `maison_du_joueur` vaut `None`. `{"maison": "seigneurie-<n>"}` dépose exactement `ChoixDepart(n)`. Contre-épreuve dans le test : un `ChoixDeMaison.appliquer` neutralisé (monkeypatch) laisse `maison_du_joueur` à `None`, et l'assertion du choix appliqué doit échouer (`pytest.raises(AssertionError)`).
- **SC2 — les refus disent leur raison.** Même fichier, `-k "tout_pays_refus"` : une maison sans lieu (`grande-21`), une république (`institution-15`, Florence), l'Église (`institution-17`, Papauté), un ordre (`institution-22`, Ordre teutonique), une maison inconnue (`"grande-999"`), un non-texte (`3`, `True`), les deux champs à la fois, et un second choix après un royaume — chacun refusé par `IntentionRefusee` au message exact de la règle, sans changer l'attente ni `to_dict()`. Contre-épreuve : `raison_de_refus` remplacé par une fonction qui rend toujours `None` fait accepter la Papauté, et le test doit échouer. `test_refus_inconnu` et ses cas restent tels quels et passent.
- **SC3 — l'IA ne dépose plus rien pour eux, au même tick.** Même fichier, `-k "tout_pays_ia"`, sur le montage `_ia_monde` (faim du mois, greniers pleins) : sans choix, les propositions de `decider_intentions` contiennent au moins une route et une part de `("grande maison", 3)` (le filtre mord) ; avec un `ChoixDeMaison("grande-3")` en attente, puis appliqué, elles n'en contiennent plus aucune, et les propositions des autres maisons sont exactement les mêmes. `capitales.maisons_de_l_ia` n'a plus les Valois. Sur `jouer_ia` d'un mois entier, le relevé ne porte aucune entrée de `grande-3` ni du petit seigneur choisi. Contre-épreuve : `maison_choisie` remplacée par une fonction qui rend `None` fait revenir la route des Valois, et l'assertion doit échouer. `test_ia_registre_choix` et `test_ia_budget_annuel_et_branches` passent sans être touchés.
- **SC4 — la photographie accepte tout pays jouable.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "photographie_1400" -q` : dans `test_photographie_1400_registre`, le cas `"grande-3"` change de sens (décision A) — sa photographie a `terre_choisie` à `null` et `maisons_du_joueur["maison"]["id"] == "grande-3"`, monde inchangé ; un cas neuf fait de même pour le petit seigneur ; un cas neuf refuse `institution-17` et `grande-21` par `SnapshotExportError` avec leur raison ; tous les autres identifiants mal formés de `IDENTIFIANTS_SEIGNEURIE_MAL_FORMES` (et l'entier) lèvent toujours « seigneurie inconnue ». Les six terres gardent leur fiche exacte. Contre-épreuve : la fiche d'une autre maison (`grande-1`) mise à la place de celle des Valois doit faire échouer la vérification (`pytest.raises(AssertionError)`). `IDENTIFIANTS_SEIGNEURIE_MAL_FORMES` lui-même ne change pas (`test_registre_identifiant` refuse toujours `"grande-3"` comme numéro de seigneurie).
- **SC5 — le service propose les six en tête et prend un royaume.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "jouables" -q` : un `ServeurMonde` sur la graine 0 sert `GET /jouables` dont les six premières entrées sont les six seigneuries de départ par numéro, qui contient `grande-3` et des `plausible-…`, et ne contient ni `grande-21`, ni aucune `institution-…` ; `POST /intention` `{"type": "choisir_depart", "maison": "grande-3"}` répond 200, un second choix 409, une république 400 avec sa raison ; après un tick, `fixer_part` pour `grande-3` est accepté et `GET /pays?maison=grande-3` porte ses jauges. Contre-épreuve : un document dont l'ordre met une grande maison avant les six doit faire échouer l'assertion d'ordre.
- **SC6 — rien d'autre ne bouge.** `cd jeu && python3 -m pytest sim -q` passe en entier. Aucune empreinte épinglée ne change (`grep -rnE 'sha256|EMPREINTE' jeu/`) : le monde sans choix et le chemin `seigneurie` donnent les mêmes octets ; aucun fichier de test d'empreinte n'est au périmètre, et si l'une rougit, le lot est faux.

## Hors périmètre
- Le clic dans Unity sur un royaume ou un seigneur, et la liste des jouables à l'écran (lot `pc` à venir, qui lira `/jouables`).
- Les règles d'élection des républiques, de l'Église et des ordres (#441) ; aucun d'eux n'est jouable avant.
- Le jeu des petits seigneurs par l'IA (#427).
- Une garde du service qui réserverait `depenser_jauge`, `batir_dans_une_province` ou `ameliorer_une_province` à la maison du joueur : les dépôts restent ceux d'aujourd'hui.
- `python3 -m forge --depart ID` (garde le numéro entier de seigneurie) ; `/maisons`, `/departs` et `/pays` (clés figées).
- Une fiche de terre pour un pays hors des six (`terre_choisie` reste `null`) ; le panneau égal à la photographie de la preuve du jalon (#448).
- Le vassal joué qui refuse l'hommage (question ouverte de `docs/VISION.md`).
