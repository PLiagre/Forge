# Lot #513 — Le monde porte son registre
Jalon : J3 · Machine : vps · Taille prévue : 285 lignes

## But
Le monde portera les maisons et leurs suzerains dans son état sérialisé, pour préparer les maîtres des lieux et les parts dues.

## Le joueur
Même geste préparé : « Chaque lieu a son seigneur » (#391), puis fixer sa part (#395), la voir rejoindre son grenier (#396) et devoir une part à son suzerain (#397). Ce lot de fond donne à ces futurs gestes des maisons présentes dans le monde, dont l'identité ne dépend ni de l'écran ni du temps écoulé. #391 rendra les maîtres effectifs sur les lieux ; #400 et #401 les montreront dans le service et la carte de la forge, avant les gestes dans Unity (#405). Le joueur pourra reconnaître ses terres et celui à qui il doit du grain, puis choisir entre remplir son grenier et garder ses gens.

## Règle du monde
Découpé de #390. Dépend de : #512. Découle de « Les maisons du monde », « Les maisons de 1400, vue dérivée » et « Les maisons de l'IA et leurs capitales, vue dérivée » de `jeu/sim/MODELE.md` ; mettre aussi à jour « En une page ».

`World.charger` appelle `charger_registre_maisons` de #512 avec sa carte et remplit `World.maisons`. Conserver le tuple de fiches gelées et tous ses champs : `id`, `nom`, `sorte`, `suzerain`, `siege`, `cell_id`, `rang`, `hors_carte`. Le registre est un état initial du monde, chargé une fois ; aucune vue ne le recalcule pour le stocker. Il comprend aussi la maison du joueur. Ne changer ni les données, ni les liens, ni les placements de #512. Initialiser explicitement le registre vide pour les mondes construits directement par `World(...)`, sans charger les tables sur ces mondes d'épreuve ; un monde chargé depuis la carte doit avoir un registre non vide.

`to_dict()` ajoute toujours la clé `maisons`, liste de fiches converties en dictionnaires et triée par `id`, quel que soit l'ordre du tuple stocké. Sérialiser l'état détenu, sans relire les tables ou appeler une vue. La conversion ne modifie pas le registre et rend des dictionnaires indépendants. Les autres clés et valeurs gardent leur contrat ; aucune maison, puissance ou province n'est ajoutée à `Cell`. Le siège reste (`cell_id`, `rang`), sans seconde clé spatiale.

L'ajout de cette seule clé change l'empreinte canonique une fois. Ensuite, sans geste, les octets du registre restent identiques pour toute graine et tout tick. Cela ne fige pas le monde : populations, paniers et compteur évoluent comme auparavant. À tick et graines identiques, retirer uniquement `maisons` de la nouvelle sérialisation doit retrouver la trajectoire sans registre, au bit près, y compris les retours du tick, le bassin maritime et l'état de l'aléa. Le tick ne consulte pas le registre, même pour une lecture sans effet ; ne modifier aucun maillon du moteur.

Décision technique A déjà prise par le pilote : adapter dans ce lot le contrôle de `test_pure` dans `sim/tests/test_maisons.py` qui exige aujourd'hui zéro occurrence de `maisons` dans `world.py`. Garder toutes ses assertions de pureté des vues, des cellules et des tables, ainsi que l'interdiction des lectures des vues par le moteur. Remplacer seulement la confusion entre stockage dans `World` et lecture au tick, et ajouter une garde dynamique qui échoue sur toute consultation de `World.maisons` pendant le tick. Retirer simplement `world.py` du contrôle sans cette preuve serait insuffisant. Aucun autre cas existant ni empreinte figée ne s'assouplit.

Dans « En une page », distinguer la maison tenante dérivée par la vue du registre désormais détenu par `World`, présent dans `to_dict()` et non lu au tick. Dans « Les maisons du monde », remplacer la phrase qui dit que le chargement n'amorce rien sur `World` par ce nouveau contrat ; conserver la pureté du lecteur de #512 et des anciennes vues.

Niveau 1 : identités et sièges déjà sourcés de #512, conservés. Niveau 2, plausible, jamais sourcé : mêmes racines et liens de départ, sans nouvelle règle ni constante. Niveau 3 : maîtrise effective des lieux, prélèvement, hommage matériel, greniers, personnes et succession dans ce lot. Budget indicatif, brief compris : état et sérialisation 30 lignes, contrôle adapté et nouveaux cas maisons 100, cas de déterminisme 80, modèle 15, brief 60 ; rester sous 300 lignes de diff.

## Périmètre
jeu/sim/world.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_determinisme.py
jeu/sim/MODELE.md

## Conditions de succès
Commandes depuis `jeu/`, sauf SC5. Ajouter les cas au fichier qui porte leur invariant, avec les noms indiqués ci-dessous ; prouver leur rouge avant l'implémentation. Les ensembles et compteurs attendus se dérivent des tables et de #512, sans total fixé. Toute catégorie éprouvée et toute course doivent être non vides. Seule l'adaptation de contrôle explicitement décidée ci-dessus touche un cas existant.

SC1 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_world` vérifie qu'un monde chargé détient exactement les fiches de #512, toutes catégories présentes, y compris les départs et les branches homonymes ; le lecteur est appelé au chargement, jamais aux consultations suivantes. Vérifier aussi le registre explicitement vide d'un `World(...)` d'épreuve. Contre-épreuves : lecteur remplacé par un résultat privé d'une fiche, puis par un résultat vide, font échouer la complétude ; une fiche altérée fait échouer l'égalité. Un lecteur qui lève au chargement doit faire échouer `World.charger`, sans repli silencieux.

SC2 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre_serialisation` vérifie la clé toujours présente, tous les champs, l'ordre des identifiants et les octets canoniques identiques après inversion du tuple. Interdire le lecteur et les vues après chargement, puis sérialiser avec succès ; modifier le dictionnaire rendu ne change pas l'état. L'empreinte avec `maisons` diffère de celle du même document privé de cette seule clé. Contre-épreuves : clé omise, fiche manquante, champ altéré ou liste non triée font échouer les assertions correspondantes ; une fiche du registre réellement remplacée doit changer les octets et l'empreinte.

SC3 — `python3 -m pytest sim/tests/test_determinisme.py -q -k registre_bit_pres` joue deux mondes distincts par couple de graines : l'un chargé normalement, l'autre chargé avec le seul lecteur du registre neutralisé en tuple vide. Comparer dès l'amorçage, puis à chaque tick sur une année, les sérialisations privées uniquement de `maisons`, les cartes, cellules complètes, bassin maritime, retours et états des générateurs. Éprouver plusieurs graines de chargement et de tick, dont 0 et 42 ; les octets du registre normal restent ceux du départ dans toutes ces courses. Contre-épreuves : remplacer une fiche fait échouer la stabilité ; changer un stock d'un seul flottant représentable fait échouer la comparaison au tick concerné ; supprimer tous les points comparés fait échouer l'échantillon. Conserver les tests existants qui exigent des mondes différents pour des graines différentes.

SC4 — `python3 -m pytest sim/tests/test_maisons.py -q -k 'pure or registre_tick'` conserve la pureté des anciennes vues et éprouve le tick avec une interception de l'accès à l'attribut `maisons`, activée uniquement pendant son exécution. Toute lecture lève, y compris un simple `getattr` dont le résultat serait jeté ; le véritable tick doit réussir avec zéro accès mesuré, sur des mondes chargés non vides. Contre-épreuve : envelopper le tick en mémoire avec cette lecture sans effet doit faire échouer la même garde. Éprouver aussi une vue qui altère le registre : les assertions de pureté du monde doivent échouer. La présence légitime du registre dans `world.py` reste acceptée.

SC5 — Depuis la racine, `python3 -m pytest jeu -q` conserve tous les contrôles du jeu, notamment les formats fermés, les empreintes figées des exports, la pureté des capitales et l'absence de sérialisation pendant le tick. Contre-épreuve : la lecture injectée de SC4 fait rougir son contrôle dans cette suite. `git diff --check` doit réussir ; contre-épreuve : un espace final ajouté à une copie du diff est détecté. Relire « En une page » et « Les maisons du monde » : une mention disant encore que `World` ne porte aucun registre contredirait SC1.

## Hors périmètre
Attribution d'un maître à chaque lieu (#391), seigneurs plausibles, nouveaux liens historiques, noms ou données, parts, greniers, convois et dû au suzerain, nouvelles intentions, décisions de l'IA, sauvegarde et rechargement. Aucun changement du tick, des vues, du service, des schémas d'export ou des écrans ; aucun travail Unity ou Blender. Tout chemin absent du périmètre est interdit en écriture.
