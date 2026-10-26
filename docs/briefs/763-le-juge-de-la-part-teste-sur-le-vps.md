# Lot #763 — Le juge de la part, testé sur le VPS
Jalon : J3 · Machine : vps · Taille prévue : 290 lignes

## But

Le joueur pourra se fier au prélèvement affiché et à son effet sur son grenier grâce à un juge qui confronte deux essais de part aux observations du monde.

## Le joueur

Lot de fond, découpé de #660 (sous-lot 8 de #405). Il prépare la preuve du geste de J3 « fixer la part qu'il prend sur ses lieux », déjà visible depuis #656 (curseur et bouton) et #655 (panneau « Ma maison »). Le joueur qui prend 50 % plutôt que 10 % doit voir un grenier plus plein et pouvoir croire le chiffre de son panneau, pour arbitrer entre ses réserves et ce qu'il laisse à ses gens. Ce lot écrit le juge qui le vérifiera. L'autre morceau de #660, le lanceur PC, le fera tourner sur de vraies sessions Unity. Le joueur ne voit rien de neuf. Dépend de : #659 (format du rapport), déjà livré.

## Règle du monde

Sans objet : c'est un outil d'épreuve, aucune règle ni constante ne change. Le juge lit ces contrats de `jeu/sim/MODELE.md` : « Les intentions du joueur » (le choix et la part s'appliquent au tick suivant ; le reçu recopie le tick courant au dépôt, donc 0 puis 1), « Le prélèvement », « Le grenier d'une maison » et « Les maisons servies, vue dérivée » (`id`, `part`, `grenier`, `tick`, `absents`). La comparaison forte > faible porte sur ces deux essais de trente ticks, sans en faire une loi valable à toute durée. La part coutumière vaut 3 % (`PART_COUTUMIERE`), ce qui sépare un monde sans geste d'un monde où le joueur a fixé 10 %. Aucun niveau de vraisemblance nouveau.

Mesures confirmées par le chef sur ce VPS (21/10/2026, base `0164d5b`), avec un service neuf par essai, graine 0, en pause. Choix de la Morée (`{"type":"choisir_depart","seigneurie":3}`, accepté au tick 0), un tick, `fixer_part` sur `seigneurie-3` (accepté au tick 1), puis 30 ticks. Le corps de `/maison?id=seigneurie-3` est au tick 31, avec la part 0,5 ou 0,1 et un grenier `{"nourriture":570982.179398794}` ou `{"nourriture":115486.43624743563}`.

## Périmètre

pc/epreuve_part.py
jeu/ville/tests/test_epreuve_part.py
docs/mesures/763-juge-part/maison-moree-50.json
docs/mesures/763-juge-part/maison-moree-10.json
docs/briefs/763-le-juge-de-la-part-teste-sur-le-vps.md

Tout autre chemin est interdit. Le budget, brief et fichiers neufs compris, reste sous 300 lignes ajoutées et retirées : environ 110 lignes de juge, 100 de tests, 2 de mesures et 75 de brief. Les aides, tests et fixtures existants restent inchangés.

**Les deux corps mesurés.** Les écrire octet pour octet tels que le service les rend, sans les reformater ni ajouter de fin de ligne. On les obtient par les commandes de SC1. Ce sont des relevés VPS, pas des rapports PC. La suite de tests ne lance aucun service.

**Le juge.** `pc/epreuve_part.py` suit le modèle de `pc/epreuve_capitale.py`. Il charge ce fichier par `importlib`, comme celui-ci charge `epreuve_carte.py`, et réutilise ses `_fiche`, `_ecrire`, `EGALITE`, `ECART`, `IMPOSSIBLE` et `TITRES`, sans les recopier ni modifier `epreuve_capitale.py`. Il définit `MOREE = "Despotat de Morée"` et ne porte ni `main`, ni service, ni Unity, ni HTTP : ces éléments appartiennent au sous-lot suivant. Signature : `juger(forte, faible, departs, relu_forte, relu_faible, part_forte, part_faible) -> tuple[int, list[str]]`. `forte` et `faible` sont les rapports JSON de #659, déjà décodés. `departs` est `/departs` lu avant la session. `relu_*` est le corps texte de `/maison` relu indépendamment après la session, fourni au juge sans accès réseau. `part_*` est le pourcentage demandé, un entier de 0 à 60 inclus, booléens exclus. Charger `_ecrire` prépare le lanceur suivant ; `juger` ne l'appelle pas, ne modifie pas ses arguments et n'écrit rien.

**Ce qui rend l'épreuve impossible (code 2, sans aucune ligne « égal »).** Rapport non objet, vide, champ requis absent ou mal typé : valider les seize champs de #659 (`terre`, `part_demandee_pct`, `curseur_pct`, `maison`, `tick_avant`, `tick_apres_choix`, `tick_apres`, `ticks_part`, `choix`, `ordre`, `intention_json`, `message_ordre`, `panneau`, `maison_statut`, `maison_json`, `defaut`). Ticks, pourcentages et statuts : `int` non booléens ; textes : `str` ; reçus : objets {statut entier, tick entier, raison texte}. Sont aussi impossibles : `defaut` non vide (cité), fiche Morée absente ou ambiguë (`_fiche`), départ hors tick 0, pourcentage demandé hors de 0–60, corps relu non JSON objet ou sans `id` texte, `tick` entier, `part` numérique finie et `grenier` objet de kilos numériques finis non négatifs (booléens exclus). Aucun champ absent n'est deviné ; un panier `{}` est une mesure. Une impossibilité sur un côté est prioritaire sur les égalités ou écarts de l'autre.

**Ce que le juge exige pour chaque essai.** Soit `t = 0`, vérifié dans `/departs`, et P la part de l'essai. Chaque ligne commence par `forte · ` ou `faible · `, puis le nom de la ligne. Elle se lit `<nom> : <vu> · attendu <attendu> · égal|ÉCART`, comme dans `epreuve_capitale.py`. Il y a onze lignes par essai, dans cet ordre :

1. `terre` : `terre` est l'id de la fiche Morée.
2. `demande` : `part_demandee_pct` et `curseur_pct` valent P tous les deux.
3. `choix` : le reçu est `200 au tick t «»`.
4. `ordre` : le reçu est `200 au tick t+1 «»`.
5. `ticks` : on a avant t, choix t+1, après t+31 et part 30 (`ticks_part`), soit trente ticks de part.
6. `intention` : `intention_json` se décode en objet de `type` `fixer_part`, `maison` égale à la maison attendue, et `part` numérique finie non booléenne à 1e-9 près de P/100. Un JSON illisible est un ÉCART sur cette ligne.
7. `maison` : la maison du rapport, l'`id` relu et `seigneurie-<id de la fiche>` coïncident, et le tick relu vaut t+31.
8. `part relue` : la `part` relue vaut P/100 à 1e-9 près.
9. `corps` : `maison_statut` vaut 200 et `maison_json` est identique, caractère pour caractère, au corps relu. La ligne montre le statut et les longueurs, jamais les corps entiers.
10. `panneau part` : `panneau` commence par `Prélèvement : X % · tick N`, avec N égal au tick relu et X, lu en nombre à virgule, à 0,005 près de 100 × part relue.
11. `panneau grenier` : la ligne `Grenier : k : v kg · …`, ou `Grenier : vide` si le grenier relu est `{}`. Elle porte exactement les clés relues, chacune une seule fois, chaque v (à virgule) à 0,005 près de la valeur relue. Comme `CommandesMaison.Decrire`, les nombres entiers s'écrivent sans virgule ; la lecture ne dépend pas de la langue du VPS.

Un panneau qui ne se lit pas est un ÉCART sur sa ligne, pas un plantage.

**La ligne finale.** `grenier : forte <total> kg · faible <total> kg · attendu forte > faible`, suivie de `· égal` ou `· ÉCART`. Chaque total est la somme de toutes les valeurs du grenier relu, sans arrondi avant comparaison. Aucun total ni seuil de kilos n'est écrit dans le juge. Le code vaut 0 si les 23 lignes sont égales, 1 sinon.

**Les tests.** Ils vont dans `jeu/ville/tests/test_epreuve_part.py`, sur le modèle de `test_epreuve_capitale.py`. On reprend `departs-graine0-tick3.json` du pont, ramené au tick 0. Les deux corps mesurés sont lus en texte brut. Une aide `_rapport(P, corps)` bâtit en mémoire le rapport qu'une session #659 aurait écrit. Il porte la terre 3, la maison `seigneurie-3`, les reçus, les ticks, l'intention `{"type":"fixer_part","maison":"seigneurie-3","part":P/100}` et `maison_json` égal au corps. Le panneau est formaté comme `CommandesMaison.Decrire`, en fr-FR « 0.## », clés triées : `Prélèvement : 50 % · tick 31\nGrenier : nourriture : 570982,18 kg`. Une docstring le dit : ces rapports sont bâtis, ils ne sont pas des mesures PC. Le panneau attendu est écrit en littéral dans le test, jamais recalculé par le code du juge.

## Conditions de succès

Depuis la racine du chantier, sur le VPS.

SC1 — Les corps mesurés sont ceux du service. Commande depuis `jeu/` : `python3 -m sim.service --seed 0 --port 18763 --jours-par-seconde 0`. Dans un second terminal, utiliser `curl -fsS` : déposer sur `/intention` le choix `{"type":"choisir_depart","seigneurie":3}`, poster `/tick?n=1`, déposer `{"type":"fixer_part","maison":"seigneurie-3","part":0.5}`, puis poster `/tick?n=30` ; vérifier HTTP 200 et reçus aux ticks 0 et 1. `curl -fsS 'http://127.0.0.1:18763/maison?id=seigneurie-3'` fournit `maison-moree-50.json` au chemin autorisé. Arrêter ce service, en lancer un neuf et répéter avec 0.1 pour `maison-moree-10.json`. `python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q -k corps_mesures`, depuis la racine, exige deux corps non vides, maison `seigneurie-3`, tick 31, parts 0.5/0.1 et nourriture `570982.179398794`/`115486.43624743563`. Contre-épreuve : retirer le dépôt de part laisse la coutume à 3 % et fait échouer ce contrôle. Le codeur joint les commandes et les réponses à son rendu, sans fichier supplémentaire.

SC2 — Rouge d'abord. Avant le juge, `python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q` échoue sur « fichier introuvable : …/pc/epreuve_part.py », pas sur une erreur de collecte. Le codeur joint cette sortie. Contre-épreuve : après ajout du juge, ce défaut doit disparaître et SC3 passer ; zéro cas collecté ou une erreur de syntaxe ne valent pas preuve rouge.

SC3 — Les deux rapports bâtis sont égaux. Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q`. Un cas juge `_rapport(50, corps50)` contre `_rapport(10, corps10)` avec 50 et 10 : code 0, 23 lignes, toutes « · égal ». La ligne finale contient `570982.18` et `115486.44` (ou leurs valeurs pleines). Contre-épreuve, imprimée par un cas (`-s` la montre) : les deux côtés bâtis sur le corps à 10 %, jugés avec 10 et 10, donnent le code 1 et un seul ÉCART, la ligne `grenier`. Un juge qui accepterait l'égalité des greniers, ou qui la signalerait ailleurs, échoue.

SC4 — Un faux sur une ligne est un ÉCART sur cette ligne seule. Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q -k ecart`. Cas paramétrés sur le côté fort, chacun copié en mémoire : code 1 et exactement un ÉCART au préfixe attendu. Panneau à `51 %` → `forte · panneau part` ; grenier affiché à `570982,20 kg` → `forte · panneau grenier` ; part relue à 0.49, avec `maison_json` modifié pareil et panneau aligné à 49 %, mais demande, curseur et intention conservés à 50 % → `forte · part relue` ; un espace ajouté seulement au corps rapporté → `forte · corps` ; tick d'ordre à 2 → `forte · ordre` ; `ticks_part=29` → `forte · ticks` ; intention à 0.4 → `forte · intention` ; curseur à 40 → `forte · demande`. Vérifier aussi choix refusé, tick final faux, identité fausse et panneau illisible : code 1 et lignes concernées en écart. Face au relu `570982.179398794`, un panneau à `570982,18` reste égal, mais `570982,19` donne un écart ; changer seulement le tick affiché fait rougir `panneau part`. Contre-épreuve : omettre une comparaison ou élargir sa tolérance fait échouer son cas.

SC5 — L'impossible est nommé. Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q -k impossible`. Cas paramétrés : rapport `{}`, champ `panneau` retiré, `defaut` = « session interrompue », `ticks_part` booléen, fiche Morée retirée ou doublée, `/departs` au tick 3, corps relu `pas du json`, relu sans `grenier` ou avec `grenier:null`, kilo non fini, part demandée 61. Chaque cas donne 2, au moins une ligne, aucune ligne « · égal », même si l'autre essai est correct. La cause (« session interrompue », « panneau », « grenier »…) figure dans les lignes. Contre-épreuve : accepter l'entrée vide, lui substituer zéro ou laisser une exception non traitée fait échouer son cas.

SC6 — Le juge dépend des observations. Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q -k references`. Réordonner `/departs` conserve 0 ; changer l'id de la fiche puis les maisons des rapports, intentions et corps en conséquence conserve 0. Sur des copies explicitement synthétiques, changer paniers et panneaux ensemble conserve 0 si forte > faible ; inverser ensuite les totaux ne fait rougir que la ligne finale. Couvrir plusieurs marchandises, un panier vide et une clé de panneau manquante ou répétée. Deux appels identiques rendent les mêmes lignes sans modifier les arguments. Contre-épreuve : id ou kilos figés, somme du seul premier produit, référence prise dans le panneau ou mutation des entrées font échouer ces cas.

SC7 — Rien d'autre ne bouge. Commandes : `python3 -m pytest jeu/ville/tests -q`, puis `python3 -m pytest jeu -q`. Les deux sont verts, et `test_epreuve_capitale.py` passe inchangé. Puis `git diff --check`, `git diff --name-only origin/master`, `git diff --numstat origin/master` et `git ls-files --others --exclude-standard` : seuls les cinq chemins du périmètre apparaissent, avec moins de 300 lignes ajoutées et retirées. Contre-épreuve : un sixième chemin, un test existant modifié ou 300 lignes refusent la livraison.

## Hors périmètre

Le `main` du juge, le lancement des services et d'Unity, le README, les verdicts PC normal et contre-épreuve (`--part-forte 10`) et leur rangement dans `docs/mesures` : tout cela appartient à l'autre sous-lot de #660, sur le PC. Ce lot ne touche à aucun fichier Unity, à aucune session, ni à `pc/epreuve_capitale.py`. Il ne change aucune règle, aucune constante ni aucun format du service. Il n'exige rien des départs, des flux ou du dû au suzerain. Il ne fait pas la preuve du jalon 3 (#406). Il ne modifie ni n'assouplit aucun test existant.
