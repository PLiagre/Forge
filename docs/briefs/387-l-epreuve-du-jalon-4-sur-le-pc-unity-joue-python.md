# Lot #387 — L'épreuve du jalon 4 sur le PC : Unity joue, Python rejoue, verdict
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Le joueur peut retrouver après relance la ville qu'il a bâtie, avec la preuve que ses gestes ont changé le même monde dans Unity et dans Python et conservé ses habitants.

## Le joueur
Le joueur trace une route, découpe une parcelle et pose un atelier dans sa capitale ; il voit ses gestes prendre corps au tick suivant et retrouve cette ville en la rouvrant, sans perdre ses habitants rangés en foyers. Ce lot de fond vérifie ce geste déjà visible par #386 ; #388 en publiera la capitale bâtie et le panneau. Il rend les constructions fiables avant les arbitrages entre champs, maisons et murs du jalon.

CAP.md distingue cette preuve des gestes déjà livrés de la preuve complète #508. Dépend de : #385, #386, présents sur la base (`59a60f5`, `f74886f`). Aucun maître, grenier, prélèvement ou autre livraison restante de J3 n'est nécessaire ; aucun départ au Zab n'est supposé livré.

## Règle du monde
Sans objet : outil de preuve, aucune règle ni constante ne change. Les invariants éprouvés viennent de « Les intentions du joueur », « Le plan du bourg », « Le chantier et ses bras » et « Les foyers par métier » de `jeu/sim/MODELE.md` : dépôt accepté, application au tick suivant, plan détenu par le monde, conservation exacte des personnes. Les constructions et métiers existants sont de niveau 2, plausibles ; aucune donnée historique nouvelle. `cell_id` reste la seule clé spatiale.

## Périmètre
pc/epreuve_jalon4.py
jeu/ville/tests/test_epreuve_jalon4.py
jeu/ville/README.md
docs/mesures/264-preuve-du-jalon-4/verdict.txt
docs/mesures/264-preuve-du-jalon-4/verdict-service-sourd.txt
docs/mesures/264-preuve-du-jalon-4/verdict-ville-locale.txt
docs/briefs/387-l-epreuve-du-jalon-4-sur-le-pc-unity-joue-python.md

Tout autre chemin est interdit en écriture livrée. Les journaux, mondes complets, rapports et logs bruts restent dans la sortie temporaire demandée et les sorties locales ignorées des outils existants. Aucun asset ni fichier Unity suivi n'est réécrit. Budget de diff, suppressions comprises : environ 130 lignes de script, 45 de tests ajoutés, 15 de notice, 30 de verdicts et 70 de brief ; total inférieur à 300.

## Conditions de succès
SC1 — Le PC joue réellement les trois sessions. Depuis la racine, `py pc/epreuve_jalon4.py --avec-unity --sortie "$env:TEMP/forge-387-normal"` rend 0. Ajouter ce mode explicite, en gardant inchangée la recette HTTP et les options de #385 sans ce drapeau ; `--ville-locale` n'est admis qu'avec Unity. La recette Unity utilise graine 0, cellule 1175 et 10 ticks ; refuser les options incompatibles avant de lancer l'essai. Charger les aides 3D seulement dans ce mode, pour que les tests Python restent exécutables sans leurs dépendances.

Réutiliser `DesertCityPreuve.Jouer`, `Relancer`, `Vierge`, `PREUVE`, la première disposition de `RECIPE`, les gestes de routes et la consigne de #386. Le script orchestre lui-même ces entrées, sans appeler `preuve()` qui lancerait un service sans journal : service de #385 à vitesse 0, sans IA ; `jouer`, puis `relance` sur ce même service ; arrêt ; `vierge` sur un second service neuf, jamais sourd. Les seuls dépôts viennent de l'outil Unity. Le journal est la copie des intentions HTTP acceptées, sous le verrou existant, avec leur tick de dépôt ; ne pas reconstruire les intentions depuis le plan ou depuis la recette HTTP de #385. Le service vierge écrit dans un sous-dossier distinct pour préserver ce journal.

Le jugement exige trois rapports de cet essai, leurs sessions, cellule et port attendus, et aucun défaut. Au normal, les trois gestes sont acceptés aux ticks 0, 1, 2 ; la ville au tick 10 contient une rue, une parcelle aux bornes et une scierie aux piquets, avec une pièce de chaque type. Contre-épreuve : rapport manquant ou rapport ancien laissé dans les sorties doit rendre 2, jamais un verdict valide ; effacer les sorties de preuve précédentes avant les sessions.

SC2 — Python rejoue le monde joué par Unity. La commande SC1 relève `/monde-complet` avant puis après `relance`, exige leurs octets égaux et un journal inchangé, puis lance les deux vrais rejeux `py -m sim --ticks N --seed 0 --gestes <journal> --monde-json <monde-rejoue>` et la même commande sans `--gestes`, depuis `jeu/`, chemins absolus et même interpréteur. N vient du monde servi ; au normal il vaut 10. Réutiliser `juger`, `serialiser` et `controler_foyers` de #385 : égalité exacte de tout le monde, différence avec le témoin sans geste, échantillon non vide, conservation des habitants de chaque cellule dans chaque monde. Le journal doit correspondre aux types et ticks des reçus Unity ; aucun compteur de cellules n'est fixé à la main.

Contre-épreuves : `py -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` conserve tous les cas existants et ajoute les refus d'un reçu Unity ne correspondant pas au journal et d'un monde changé pendant la relance. Les altérations d'un stock hors du plan, d'un journal vide et d'une personne perdue restent refusées par les cas de #385. Un lancement CLI en échec n'est jamais remplacé par une référence fabriquée depuis le service.

SC3 — Le relancement et le témoin vierge sont mesurés. La commande SC1 exige les mêmes identifiants, états, nombres de pièces et empreintes de rues, parcelles et bâtiments entre `jouer` et `relance`. La session `vierge`, sans geste, ouvre au tick 0 un plan vide, sans pièce ; ses empreintes sont celles du terrain vierge et du dessin vide mesurées par #386. Le témoin Python sans geste est au tick N : son plan reste vide, mais sa population et ses stocks peuvent évoluer avec le temps. Contre-épreuve ajoutée dans `py -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` : une empreinte de relance différente, ou une pièce dans le rapport vierge, donne un verdict d'invariant violé.

SC4 — Les deux défauts réels rougissent avant le normal. Exécuter d'abord `py pc/epreuve_jalon4.py --avec-unity --sortie "$env:TEMP/forge-387-sourd" --service-sourd`, puis `py pc/epreuve_jalon4.py --avec-unity --sortie "$env:TEMP/forge-387-locale" --ville-locale`, enfin SC1. Les contre-épreuves rendent chacune 1, avec leurs rapports frais ; une absence d'Unity ou une panne ne vaut pas contre-épreuve. Le mode sourd garde le comportement de #385 : intention de bâtiment acceptée et journalisée, mais retirée de l'attente ; Unity constate le bâtiment absent et le vrai rejeu diffère du monde servi au tick effectivement atteint. Le mode local transmet `ville_locale: true` à #386 : la rue supplémentaire est réellement dessinée dans `jouer`, absente du journal et du plan ; `relance` échoue sur l'empreinte des rues. Le verdict local indique que l'égalité Python peut rester vraie : c'est le redessin qui échoue. Ne jamais inverser ces codes pour faire passer les contre-épreuves.

SC5 — Chaque essai laisse un verdict exploitable et ferme ses ressources. Les trois commandes écrivent `verdict.txt` dans leur propre sortie, même en échec : code 0 preuve valide, 1 invariant violé, 2 essai impossible ; statut séparé pour égalité du monde, relancement, sans geste et foyers, avec motif pour tout échec ou contrôle non exécuté. Ajouter un contrôle des gestes journalisés. Les valeurs, compteurs et écarts viennent des données ; un contrôle non exécuté ne devient jamais un succès. Avant tout service, vérifier Unity, la scène et ses données locales, l'éditeur fermé et le port 8000 libre, y compris sous Windows. Borner les appels Unity et CLI ; arrêter seulement les ressources créées, dans un `finally`.

Contre-épreuves ajoutées dans `py -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q` : Unity indisponible, délai Unity dépassé, session en erreur et rapport absent ; chacune vérifie le code, le verdict et le nettoyage. Les appels Unity peuvent être simulés dans ces tests de conduite, mais les verdicts livrés viennent exclusivement des commandes PC réelles de SC4. Le test existant du port occupé reste inchangé et laisse son occupant intact.

SC6 — Les résultats réels et la notice sont livrés sans affaiblir la base. Après SC4, copier les trois verdicts vers les trois fichiers autorisés de `docs/mesures/264-preuve-du-jalon-4/`. Ils indiquent commande, date, révision éprouvée, version Unity, code de sortie et quatre statuts avec leurs motifs ; garder les preuves brutes localement, ne pas inventer de mesure. Ajouter « L'épreuve du jalon 4 » à `jeu/ville/README.md`, avec commandes PowerShell, prérequis du contrôle #386, codes et liens vers les verdicts ; distinguer cette épreuve de #508.

`py -m pytest jeu/ville/tests/test_epreuve_jalon4.py jeu/ville/tests/test_epreuve_jalon1.py jeu/ville/tests/test_contrat_cell_id.py -q`, puis `py -m pytest jeu -q`, restent verts ; depuis `3d/`, `py local3d/atelier_desert.py preuve` reste vert. Contre-épreuve documentaire : les commandes sourde et locale de SC4 doivent encore produire 1 avec le motif nommé dans la notice ; un code 2 ou un verdict manquant interdit de déclarer SC6 réussi. Ajouter les tests au fichier de l'invariant, sans modifier aucun cas existant.

## Hors périmètre
La capture et le panneau (#388), la preuve complète #508, le Zab et le choix de capitale, la propriété, les greniers et salaires, les moissons saisonnières, l'enceinte, la ville vivante et l'IA. Aucun changement du moteur, de son contrat HTTP livré, de l'outil Unity, de ses rapports, du kit, des scènes ou des contrôles #386 ; aucune référence fixée depuis les résultats attendus. Aucune extension de la CI ni assouplissement d'un test existant.

## Photo
Sans objet : ce lot ajoute un outil de verdict et sa notice, sans changer ce que le joueur voit. Les trois sessions réutilisent le contrôle batch de #386 ; la capture de la capitale bâtie et de son panneau est réservée à #388.
