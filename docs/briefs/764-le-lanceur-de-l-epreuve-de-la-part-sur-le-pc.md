# Lot #764 — Le lanceur de l'épreuve de la part, sur le PC
Jalon : J3 · Machine : pc · Taille prévue : 295 lignes

## But
Le joueur pourra se fier à sa part et au grenier affichés grâce à une épreuve PC qui confronte deux gestes Unity aux chiffres du monde.

## Le joueur
Lot de fond découpé de #660, sous-lot de #405 : il prouve le geste de J3 « fixer la part qu'il prend sur ses lieux », visible depuis #656 dans le curseur et depuis #655 dans « Ma maison ». Prendre davantage doit remplir davantage son grenier dans ces deux essais ; le joueur peut croire le panneau pour arbitrer entre ses réserves et ce qu'il laisse à ses gens. Ce lot rend la preuve exécutable sur le PC et en conserve les verdicts réels. Il ne démontre pas encore les départs de foyers. Dépend de : #763, juge pur livré, qui s'appuie sur la session Unity #659.

## Règle du monde
Sans objet : outil d'épreuve, aucune règle ni constante du monde ne change. Contrats lus dans `jeu/sim/MODELE.md` : « Les intentions du joueur », « Le prélèvement », « Le grenier d'une maison », « Les maisons servies, vue dérivée ». Le choix déposé au tick 0 s'applique au tick 1 ; la part déposée au tick 1 précède trente ticks, jusqu'au tick 31. La comparaison forte > faible concerne ces essais neufs, graine 0, pas toute durée possible. Aucun niveau de vraisemblance nouveau.

## Périmètre
pc/epreuve_part.py
jeu/ville/tests/test_epreuve_part.py
jeu/ville/README.md
docs/mesures/660-epreuve-part/verdict-normal.txt
docs/mesures/660-epreuve-part/verdict-contre-epreuve.txt
docs/briefs/764-le-lanceur-de-l-epreuve-de-la-part-sur-le-pc.md

Tout autre chemin est interdit. Budget visé, ajouts et retraits, fichiers neufs et brief compris : 100 lignes de lanceur, 60 de tests ajoutés, 10 de README, 60 de verdicts et 65 de brief ; total strictement inférieur à 300. Les rapports JSON et journaux Unity restent dans les dossiers temporaires des essais.

Ajouter `main(argv)` et l'entrée de script à `pc/epreuve_part.py`, sans changer `juger`, ses tolérances ni ses 23 lignes. Commande depuis la racine, éditeur fermé : `py pc\epreuve_part.py --sortie <dossier> [--part-forte P] [--part-faible P] [--unity CHEMIN]`. Pourcentages entiers entre 0 et 60 inclus, défauts 50 et 10 ; zéro est valide. Graine fixée à 0. Une valeur hors bornes ou illisible sort à 2 avant tout lancement ; 10 contre 10 est autorisé pour éprouver le juge.

Réutiliser via `CAPITALE` les aides existantes de `epreuve_capitale.py`, `CARTE`, `JOUER` et `JALON1` : découverte d'Unity, contrôle du port 8000, lancement en pause, attente du service, exécution Unity bornée, arrêt et écriture du verdict. Ne pas recopier ces mécanismes ni modifier leurs fichiers. Avant toute session, vérifier Unity et le port libre ; ne jamais réutiliser ni arrêter un service étranger. Purger les anciens rapports et verdicts de cette épreuve dans `--sortie`, sans effacer d'autres fichiers.

Jouer dans l'ordre forte puis faible, avec un service neuf par essai, jamais les deux simultanément. Lire `/departs` au tick 0 et trouver l'unique fiche `MOREE` par son nom, avec `_fiche` ; ne figer aucun id. Vérifier que les deux fiches désignent la même terre. Lancer `ForgeLocal3D.EpreuvePart.Jouer` avec `-batchmode -projectPath <projet> -executeMethod <méthode> -forgeEpreuve <rapport> -forgeTerre <id trouvé> -forgePart <P> -logFile <journal>`, sans `-quit` ni `-nographics`. Nommer les fichiers `rapport-forte.json`, `rapport-faible.json`, `unity-forte.log`, `unity-faible.log`.

Python ne dépose aucun geste et ne fait avancer aucun tick : Unity joue le curseur, la confirmation et le temps. Après chaque session terminée, avant l'arrêt du service, lire indépendamment `/monde` et `/maison?id=seigneurie-<id trouvé>`. Conserver le corps UTF-8 intégral de `/maison`, sans décoder puis réencoder le JSON ni ajouter une fin de ligne : `juger` le compare caractère pour caractère. Les lectures réseau sont bornées et exigent HTTP 200. Arrêter chaque service possédé dans un `finally`, y compris si Unity, une lecture ou le rapport échoue.

Exiger un rapport neuf selon la marge d'horodatage existante, non vide et JSON lisible ; Unity non nul, rapport absent ou ancien, panne HTTP et donnée requise absente rendent l'épreuve impossible, avec cause et côté nommés. Dans `/monde`, `tick` doit être un entier non booléen et `maison_du_joueur` un texte : absence ou type invalide donne 2. Une valeur relevée différente du tick final rapporté ou de la maison attendue donne 1, avec ligne explicite. Après les deux essais valides, appeler une seule fois `juger(forte, faible, departs, relu_forte, relu_faible, part_forte, part_faible)` ; les départs sont ceux du premier essai, vérifiés contre le second. L'impossible prime tout écart. Rendre 0 si toutes les comparaisons sont égales, 1 pour un écart observé, 2 si l'épreuve est impossible ; écrire `verdict.txt` par `_ecrire` et imprimer le même verdict. Aucun kilo attendu n'est codé dans le lanceur.

Ajouter au fichier de tests existant des cas d'orchestration avec services, HTTP et Unity remplacés en mémoire ; reprendre ses rapports bâtis et ses corps mesurés de #763. Ils prouvent le câblage, pas une exécution PC. Ajouter au README « L'épreuve de la part » : commande, prérequis, deux services neufs en pause, codes, contre-épreuve et liens vers les deux verdicts réels.

## Conditions de succès
Depuis la racine ; commandes PC sous PowerShell. Le codeur conserve les sorties rouge/vert dans son rendu au pilote.

SC1 — Rouge d'abord. Avant le lanceur, `py -m pytest jeu/ville/tests/test_epreuve_part.py -q -k main` exécute les nouveaux cas et échoue parce que `main` manque, sans erreur de collecte. Après implémentation, la même commande passe. Contre-épreuve : zéro cas collecté ou des doublures qui contournent `main` ne prouvent rien.

SC2 — Le câblage dépend des observations. `py -m pytest jeu/ville/tests/test_epreuve_part.py -q -k main` exige deux services distincts, graines `[0, 0]`, arrêt avant le suivant, arguments Unity 50 puis 10, terre trouvée dans des départs réordonnés, lectures après chaque session et corps brut transmis au vrai juge. Le cas 10 contre 10 rend 1 avec le seul écart `grenier`. Contre-épreuves paramétrées : corps rapporté différent du relu, tick ou maison du monde décalés rendent 1 ; code Unity non nul, rapport absent, ancien ou illisible et erreur HTTP rendent 2 avec leur cause, même au second essai, et tous les services démarrés sont arrêtés. Le harnais refuse toute écriture HTTP et tout argument Unity interdit.

SC3 — Les gardes précèdent l'effet. `py -m pytest jeu/ville/tests/test_epreuve_part.py -q -k main` vérifie Unity absent, port occupé, pourcentage 61 ou non entier : code 2, aucun lancement ; un ancien verdict égal ne subsiste pas comme résultat courant. Contre-épreuves : 0 reste 0 dans l'argument Unity ; des données `/monde` manquantes ou mal typées rendent 2 ; une Morée absente ou ambiguë interdit la session. Tout accès au service étranger ou lancement malgré la garde fait échouer ces cas.

SC4 — Mesure réelle normale. Sur le PC, éditeur fermé et port 8000 libre : `py pc\epreuve_part.py --sortie "$env:TEMP\lot764-normal"` ; lire immédiatement `$LASTEXITCODE`, attendu 0. Le verdict contient les 23 comparaisons égales du juge et le grenier fort supérieur au faible. Copier son texte intégral dans `docs/mesures/660-epreuve-part/verdict-normal.txt`, précédé de trois lignes `commande : ...`, `date : ...`, `code de sortie : 0` donnant la commande exacte et la date effective. Contre-épreuve : SC5 doit rougir sans altération des rapports ; un code Unity 0 seul ne vaut pas égalité.

SC5 — Mesure réelle qui peut échouer. `py pc\epreuve_part.py --sortie "$env:TEMP\lot764-contre" --part-forte 10` ; lire immédiatement `$LASTEXITCODE`, attendu 1. Deux nouvelles sessions complètes, à 10 % chacune : toutes les comparaisons de chaque côté sont égales, seule la comparaison finale `grenier` est en ÉCART. Copier intégralement le verdict dans `docs/mesures/660-epreuve-part/verdict-contre-epreuve.txt`, avec commande exacte, date effective et `code de sortie : 1` en en-tête. Contre-épreuve : accepter forte = faible donnerait 0 et fait échouer ce contrôle ; un code 2, un rapport retouché ou un jugement synthétique ne remplacent pas cette mesure PC.

SC6 — L'impossible est explicite et les contrats restent verts. `py pc\epreuve_part.py --sortie "$env:TEMP\lot764-impossible" --unity "$env:TEMP\unity-764-absent.exe"`, après vérification que ce chemin n'existe pas, rend 2 et nomme Unity absent. Contre-épreuve : un verdict 0 hérité d'un essai précédent ou un service lancé refuse la livraison. Puis `py -m pytest jeu/ville/tests -q` et `py -m pytest jeu -q` passent sans modifier les assertions existantes ; les nouveaux cas SC2–SC3 doivent toujours détecter leurs fautes injectées.

SC7 — Livraison bornée. `git diff --check`, `git diff --name-only origin/master`, `git diff --numstat origin/master` et `git ls-files --others --exclude-standard` permettent de vérifier les six chemins et de compter aussi les fichiers neufs : moins de 300 lignes ajoutées et retirées. Contre-épreuve : un septième chemin, 300 lignes, un test existant assoupli ou un verdict sans en-tête refuse la livraison.

## Hors périmètre
La session et les fichiers Unity, les scènes et panneaux, les aides des autres lanceurs, le juge de #763 et ses mesures VPS. Aucune règle de simulation, aucun format de rapport ou de service ne change. Ni ouverture du grenier, ni départs de foyers, ni flux positifs exigés : ce n'est pas la preuve complète de J3 (#406). Aucun rapport PC fabriqué et aucune modification des tests existants ; seuls de nouveaux cas s'ajoutent.

## Photo
sans objet : outil de lancement et de jugement sans changement de ce que le joueur voit à l'écran. Le geste reste celui déjà photographié par `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot656.cs` ; ce lot ajoute les verdicts des sessions réelles, sans nouveau scénario de capture.
