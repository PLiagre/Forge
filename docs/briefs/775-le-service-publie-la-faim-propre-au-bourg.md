# Lot #775 — Le service publie la faim propre au bourg
Jalon : J4 · Machine : vps · Taille prévue : 240 lignes

## But
Le service donne la faim réellement éprouvée par les habitants du bourg, avec leur panier et le jour observé, pour que la capitale vive d'après le monde.

## Le joueur
Le joueur verra les étals de sa capitale suivre la faim de ses habitants : des champs pleins ne masqueront plus un bourg affamé, et un panier vidé par une ration complète ne fera pas croire à une famine. Ce lot de fond prépare le choix du jalon J4 entre une route vers les champs et d'autres chantiers ; #420, dont il est découpé, rendra cette information visible dans la ville. La demande fournie ne contient pas de phrase « Le joueur » distincte : celle-ci explicite son bénéfice, conformément à « La règle d'un lot » de `CAP.md`.

## Règle du monde
Sans objet : projection du service, aucune règle du moteur ne change. Elle lit les données de niveau 2, plausibles, déjà décrites dans `jeu/sim/MODELE.md`, « Les lieux d'une cellule, vue dérivée » → « Ce que porte un lieu », « La distribution à l'intérieur de la cellule » et « Ce que veut dire « affamée » ». Le rang 0 est le bourg ; sa `duree_faim_ticks` mesure son manque après consommation et transport intérieur. Le stock restant, la dette et la faim cellulaire ne permettent pas de la déduire.

Contrat à livrer :

- `GET /lieu?cell=X&bourg=1` ajoute un bloc `bourg` contenant exactement `rang`, `population`, `stocks`, `duree_faim_ticks` et `tick`. Il lit le rang 0, trouvé par son rang, sans supposer sa position dans la liste. `tick` égale celui de la réponse ; `stocks` conserve toutes les marchandises et leur précision locale, sans arrondi supplémentaire.
- L'absence du paramètre conserve les octets actuels de `/lieu`. Seule la valeur unique `bourg=1` active l'extension ; valeur vide, répétée ou différente : HTTP 400 sans mutation. Les refus existants de cellule absente ou inconnue restent applicables.
- Les deux variantes sont préparées dans le même appel à `_construire_etat` et portées par `EtatPublie`. Le traitement HTTP choisit des octets déjà publiés ; il ne consulte jamais le monde mutable pour compléter le bourg.
- Un rang 0 absent, dupliqué, ou une faim absente, négative ou non entière provoque un refus nommé à la construction, par `SnapshotExportError`. Aucun zéro n'est inventé. Une faim mesurée à zéro reste publiée, même avec un panier vide.
- `cell_id` reste la seule clé spatiale ; `rang` désigne la part dérivée. Le bloc ne reçoit aucun nouvel identifiant.

Ce choix d'extension explicite garde intacts les invariants existants : égalité des lieux avec la photographie, listes exactes de clés, réponses figées des ticks 3 et 4 et empreintes historiques du service sans IA. Aucun test existant ni fichier figé n'a besoin de changer. Documenter le paramètre et le sens du bloc dans `MODELE.md`, près de la publication des lieux ; préciser que la faim locale devient accessible par cette extension du service, tandis que la photographie reste inchangée.

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
docs/briefs/775-le-service-publie-la-faim-propre-au-bourg.md

## Conditions de succès
Commandes depuis la racine du dépôt. Ajouter les cas dans `test_monde.py`, sans modifier les tests, aides, références ou assertions déjà présents. Avant le code du service, les nouveaux cas doivent échouer sur l'absence du bloc demandé. Les montages comptent au moins un bourg habité et un champ ; aucun échantillon vide ne vaut preuve.

SC1 — **Trois situations que le service distingue.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_bourg_faim`.
Ajouter des cas paramétrés utilisant le vrai service HTTP et un monde de test préparé avant publication :

- bourg affamé, champ rassasié avec surplus : la faim publiée est celle, positive, du rang 0, et son panier est distinct du total cellulaire ;
- champ affamé, bourg rassasié : la faim cellulaire est positive mais celle du bloc vaut exactement zéro ;
- ration complète du bourg, panier alimentaire final nul : sa faim vaut zéro malgré ce stock nul. Produire ce dernier état par la consommation existante, avec une ration dérivée des constantes et de la population, plutôt que décréter que stock nul signifie satiété.

Comparer chaque champ du bloc à une référence copiée depuis le rang 0 avant publication, et vérifier le statut HTTP, le tick commun et toutes les marchandises, dont une quantité fractionnaire qui révèle un arrondi. Contre-épreuves rejetées par le même vérificateur : remplacer la faim locale par la faim cellulaire dans le deuxième cas ; l'inférer du stock nul dans le troisième ; substituer au panier du bourg le panier cellulaire dans le premier. Chaque altération doit faire lever `AssertionError`.

SC2 — **Une publication cohérente et figée.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_bourg_publication`.
Après publication à l'arrêt, lire l'extension, puis modifier la faim et un stock du monde sans republier : une nouvelle requête rend exactement les mêmes octets. Publier ensuite un nouvel état et vérifier que le bloc reprend ses données et son tick, avec au moins une différence observée. Réordonner les lieux dans un montage valide doit conserver la sélection du rang 0. Contrôler aussi une faim locale positive différente de la durée cellulaire.
Contre-épreuves : une copie de réponse avec un ancien tick ou le panier d'un autre rang échoue au même contrôle ; une lecture qui compléterait le document depuis le monde mutable fait échouer la première comparaison d'octets.

SC3 — **Données absentes et requêtes refusées.** Commande : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_bourg_refus`.
Ajouter les refus de rang 0 absent ou dupliqué et de faim invalide à la construction, avec erreur qui nomme la cellule et la cause. Tester en HTTP les paramètres vide, répété et différent de `1`, ainsi que la cellule inconnue. Comparer tick, intentions en attente et réponses publiées avant et après les requêtes refusées.
Contre-épreuves : le montage valide à faim zéro se publie ; `bourg=1` rend HTTP 200. Un refus systématique échoue donc lui aussi.

SC4 — **Extension isolée et compatibilité conservée.** Commandes : `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'service_bourg_compatibilite or reponse_figee or service_ia_sans or noms_publication_et_documentation or lieu_porte_les_lieux'`, puis `python3 -m pytest jeu -q`.
Ajouter `test_service_bourg_compatibilite` : retirer seulement `bourg` de la réponse étendue retrouve exactement le document ordinaire du même état ; les requêtes ordinaires et `/monde` gardent leurs octets avant et après la lecture étendue. Vérifier cette égalité sur deux publications différentes. Les tests existants passent sans retouche, notamment ceux des fichiers figés et des empreintes historiques.
Contre-épreuve : ajouter le bloc à une copie du document ordinaire fait échouer son égalité ; retirer ou altérer un ancien champ de la réponse étendue fait échouer la comparaison après retrait du seul bloc. Ces contrôles empêchent d'obtenir la compatibilité en ignorant toute la réponse.

## Hors périmètre
Animation, lecture et tests Unity, captures et réglages des étals, fumées ou lumières : suite du lot #420 sur PC. Aucun changement de consommation, faim, dette, transport, IA ou amorçage ; aucune modification de `snapshot_export.py`, de la photographie, des schémas ni des réponses figées. Aucun nouveau calcul de faim dans une vue. Pas de publication de la faim de tous les rangs ni de nouvel ordre du joueur. Aucun test existant assoupli ou réécrit.
