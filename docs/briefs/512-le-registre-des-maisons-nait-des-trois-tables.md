# Lot #512 — Le registre des maisons naît des trois tables
Jalon : J3 · Machine : vps · Taille prévue : 285 lignes

## But
Le monde saura identifier les grandes maisons, les institutions et les maisons de départ, leur siège et leur suzerain, pour préparer la tenue des lieux.

## Le joueur
Sans registre des maisons, personne ne tient rien : ce sous-lot prépare « Chaque lieu a son seigneur » (#391) et le geste du jalon J3, fixer sa part, prélever et devoir une part à son suzerain. Il n'ajoute pas encore d'écran ; #391 rendra ces maîtres effectifs sur les lieux, puis #400 et #401 les montreront dans le service et la carte de la forge. Le joueur pourra alors reconnaître ses terres et celui à qui il doit du grain, avant d'arbitrer entre remplir son grenier et garder ses gens.

## Règle du monde
Découpé de #390. S'appuyer sur « Les maisons de 1400, vue dérivée », « Les seigneuries de départ, vue dérivée », « Les maisons de l'IA et leurs capitales, vue dérivée » et « Les lieux d'une cellule, vue dérivée » de `jeu/sim/MODELE.md`.

Créer `sim/registre_maisons.py` : un chargement pur construit un registre complet depuis les trois fichiers `data/puissances-1400.json`, `data/capitales-1400.json` et `data/seigneuries-1400.json`, avec la carte passée en argument. Réutiliser leurs lecteurs et le placement existant par polygone ; permettre les copies de tables pour les contre-épreuves. Rendre un tuple de fiches gelées héritant de `_NoBadSpatialField`, ordonné de façon stable. Le registre comprend aussi la maison du joueur ; aucun choix de départ ne la retire.

Une fiche porte `id`, `nom`, `sorte`, `suzerain`, le nom du `siege`, `cell_id`, `rang` et `hors_carte`. Une ligne par grande maison, identifiée par `grande-<id maison>` ; une par puissance déclarée sans maison dans `charger_maisons().par_puissance`, identifiée par `institution-<id puissance>` ; une par seigneurie de départ, identifiée par `seigneurie-<id>`. Les sortes sont `grande maison`, `institution`, `seigneurie`. Le nom vient respectivement de la maison, de la puissance et du champ `maison` de la seigneurie. Deux branches de même nom restent distinctes, notamment les Paléologue de Constantinople et de Morée.

Le suzerain d'une seigneurie est `grande-<id maison>` de sa puissance suzeraine, ou `institution-<id puissance>` si celle-ci est sans maison. Les grandes maisons et institutions ont `suzerain = None` : racines de niveau 2, sans prétendre restituer leurs hommages historiques. Ne pas ajouter de lien aux grands vassaux déjà présents dans les ancres. Une validation appelée avant de rendre le registre refuse un suzerain inconnu ou tout cycle, même une maison qui se désigne elle-même, avec `PuissanceInvalide` nommant la maison concernée. Cette validation doit pouvoir éprouver un registre altéré.

Le siège d'une grande maison vient de sa capitale ; celui d'une institution de son ancre de plus petit id, quel que soit l'ordre des lignes ; celui d'une seigneurie de son siège déclaré. Projeter les ancres avec `projeter_epsg3035`, chercher le polygone contenant le point, départager une frontière par le plus petit `cell_id`, jamais par le centroïde le plus proche. Sur carte, `rang = 0` désigne le bourg ; l'identité du siège reste le couple (`cell_id`, `rang`), sans seconde clé spatiale.

Hors carte, `cell_id` et `rang` valent `None` et `hors_carte` porte une raison non vide : reprendre Saraï depuis les capitales ; ajouter seulement le champ `hors_carte` à l'ancre 25 de Venise dans les puissances, expliquant que son point est hors des polygones de la carte figée. Lire cette raison déclarée, sans exception fondée sur le nom ou l'id. Refuser une raison absente ou vide hors carte, ainsi qu'une raison hors carte sur un point contenu ; refuser une géométrie absente. Ne pas déplacer Venise, modifier la carte ni lui inventer un bourg.

Niveau 1 : identités, capitales et sièges déjà sourcés, conservés. Niveau 2, plausible, jamais sourcé : racines sans suzerain, siège institutionnel choisi par id, rattachement au bourg de rang 0. Niveau 3 : propriété des lieux, hommage matériel, greniers, personnes et succession dans ce sous-lot. Le chargement ne modifie ni tables ni carte, n'amorce rien sur `World` ou `Cell` et n'entre pas dans le tick.

Ajouter « ## Les maisons du monde » à `MODELE.md` : provenance, identifiants, champs, choix des sièges, liens, refus et niveaux ci-dessus. Préciser dans les passages voisins qui disent la suzeraineté non simulée que le registre ajoute ces seuls liens de départ ; les anciennes vues gardent leur contrat. Budget indicatif du diff, brief compris : module 105 lignes, cas ajoutés 105, modèle 18, donnée 2, brief 55 ; rester sous 300.

## Périmètre
jeu/sim/registre_maisons.py
jeu/sim/tests/test_maisons.py
jeu/data/puissances-1400.json
jeu/sim/MODELE.md

## Conditions de succès
Commandes depuis `jeu/`. Ajouter les cas dans `sim/tests/test_maisons.py`, sans modifier les cas existants ; nommer les nouveaux tests avec `registre`. Prouver leur rouge avant l'implémentation. Les références et compteurs viennent des tables, jamais d'un total fixé ; chaque catégorie éprouvée est non vide.

SC1 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_chargement` vérifie exactement les ensembles d'identifiants, noms et sortes attendus des trois tables, sans doublon ni fusion des branches Paléologue. Contre-épreuves : une copie du résultat privée d'une ligne de chaque sorte, puis une fusion des deux Paléologue, font échouer les assertions de complétude ; une table source absente ou vide est refusée.

SC2 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_pyramide` vérifie toutes les racines, chaque rattachement des départs et l'absence de cycle en parcourant les liens. Éprouver aussi une seigneurie dont le suzerain est changé vers une puissance sans maison : elle relève de son institution. Contre-épreuves : suzerain inconnu dans une copie de table, puis registre altéré avec référence inconnue, boucle sur soi et cycle entre deux maisons ; tous sont refusés en nommant la maison. Un rattachement vers une mauvaise racine connue fait échouer la preuve de filiation, même sans cycle.

SC3 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_sieges` vérifie les sièges de toutes les lignes depuis leurs points sources et les polygones, leur rang 0, notamment les Valois dans la cellule de Paris, 10322. Contre-épreuves : capitale des Valois déplacée vers un autre polygone, institution placée sur une autre ancre que celle de plus petit id, carte synthétique dont le centroïde le plus proche n'est pas le polygone contenant ; la preuve détecte chaque erreur. Sur une frontière synthétique, le plus petit `cell_id` gagne dans les deux ordres de carte.

SC4 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_hors_carte` vérifie les sièges hors carte et leurs raisons depuis les données : Saraï et Venise sur la carte actuelle, sans lieu inventé. Contre-épreuves sur copies : retirer ou vider chaque raison est refusé ; déclarer Paris hors carte est refusé ; retirer une géométrie est refusé en nommant la cellule. Aucun siège hors carte sans raison n'est accepté.

SC5 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_pure` vérifie l'égalité de deux chargements, des fiches gelées et des résultats après permutation des tables et de la carte ; comparer les entrées et l'état d'un monde avant et après l'appel. Contre-épreuves : une tentative d'écriture sur une fiche est refusée ; un résultat témoin avec une fiche modifiée fait échouer l'égalité, une copie d'entrée modifiée fait échouer la garde de pureté.

SC6 — `python3 -c 'from pathlib import Path; t=Path("sim/MODELE.md").read_text(); assert t.count("\n## Les maisons du monde\n") == 1; assert "sim/registre_maisons.py" in t'` vérifie la nouvelle section et sa référence de code. Contre-épreuve : exécuter le même contrôle sur une copie privée de cette section doit échouer ; relire ses règles contre SC1 à SC5.

SC7 — `python3 -m pytest sim -q`, puis `python3 -m pytest . -q`, passent sans assouplir aucun test existant. Garder les contrats figés de `test_maisons.py` (tenures, capitales, sélection IA, pureté), `test_seigneuries.py` (sièges, fiches, refus), `test_puissances.py` (ancres hors polygones et comptes), ainsi que déterminisme, absence de nombres magiques et couverture des champs. Contre-épreuves : leurs cas existants de table invalide, capitale déplacée et géométrie absente restent actifs et détectent leurs défauts ; l'ajout de la seule raison de Venise ne change ni coordonnées ni tenures.

## Hors périmètre
L'attribution des lieux à leur maître (#391), les seigneurs plausibles, les noms des lieux, les greniers, les parts coutumières, prélèvements, convois et dus au suzerain. Aucune intention, décision d'IA, personne ou succession. Aucun changement aux anciennes vues de maisons et de capitales, à leurs comptes ou à la sélection de l'IA. Aucun branchement dans le monde, le tick, la photographie, le service ou les cartes ; aucun travail Unity ou Blender. Aucun changement aux capitales, seigneuries de départ, polygones ou sources historiques ; la donnée autorisée se limite à la raison hors carte de l'ancre 25.
