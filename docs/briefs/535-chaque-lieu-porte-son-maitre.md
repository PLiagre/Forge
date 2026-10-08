# Lot #535 — Chaque lieu porte son maître
Jalon : J3 · Machine : vps · Taille prévue : 290 lignes

## But
Le monde chargé sait à quelle maison appartient chaque lieu et conserve ce maître d'un jour au suivant, pour préparer la part du domaine et son prélèvement.

## Le joueur
Le monde sait désormais, lieu par lieu, à qui appartient la terre, et il s'en souvient d'un tick à l'autre : c'est sur ce maître que s'appuieront la part que le joueur fixe sur son domaine (#395) et le grain qui monte vers son grenier (#396). Lot de fond : rien de neuf à l'écran avant le sous-lot suivant. Il prépare le geste de J3 : prendre davantage pour remplir son grenier, ou laisser davantage à ses gens ; #400 exposera les maîtres dans le service et la photographie, #401 les montrera sur la carte de la forge et #405 permettra le réglage dans Unity.

## Règle du monde
Découpé de #391 par le propriétaire. Dépend de : #534, livré. Découle de « Ce que porte un lieu » et « Les maisons du monde », paragraphe « Le maître de chaque lieu », de `jeu/sim/MODELE.md`. Niveau 2, plausible, jamais sourcé, comme l'attribution ; les fiches historiques de niveau 1 restent exactes. Aucune constante nouvelle, aucune nouvelle règle d'attribution.

`EtatDeLieu` reçoit en dernier `maitre: str | None = None` : un identifiant de maison, jamais une clé spatiale. Les appels existants, y compris positionnels, gardent leur sens. `creer_etat_de_lieu` accepte le maître en argument nommé facultatif ; `None` déclare une donnée absente, sans deviner. `World(...)` ne lit aucune table, ne crée aucun lieu ni maître et garde son registre vide ; les états fournis à la main peuvent conserver `None`.

Dans `World.charger`, après l'amorçage des lieux et le chargement du registre historique, appeler une seule fois `attribuer_maitres` de `sim/maitres.py`. Écrire chaque résultat sur le lieu du couple correspondant ; compléter `World.maisons` avec les plausibles une seule fois, dans un tuple trié par `id`, aux fiches gelées et sans doublon. Tout lieu chargé reçoit un maître présent dans ce registre. Le lecteur des trois tables reste pur, inchangé, et rend exactement ses fiches historiques. L'initialisation existante des greniers reste après le registre complet : paniers vides et distincts, sans grain ajouté ni changement des pertes ou des paniers historiques.

Dans `model.py`, fournir une véritable écriture de l'attribut et une véritable lecture, exercées respectivement par le chargement et la sérialisation ; pas une lecture factice pour la couverture. `cellule_vers_dict` et `to_dict()` portent `maitre`, y compris `None`, et les fiches plausibles. Aucun chargement ni attribution pendant la sérialisation. Le dénominateur de couverture reste dérivé de toutes les dataclasses, sans exclusion de champ ni ajout de fichier pour contourner le contrôle.

Le tick ne lit ni les maîtres ni le registre, ne les réattribue pas et ne change aucun de leurs contenus. Hors du nouveau champ et des nouvelles fiches, les anciens champs des lieux et cellules, plans, mer, carte, graphe, retours et tirages suivent exactement l'évolution précédente, sans arrondi. L'empreinte canonique change par les seuls nouveaux champs et fiches ; aucun effet économique.

Dans `MODELE.md`, « Ce que porte un lieu » décrit le maître, l'absence déclarée des états manuels et la complétude du monde chargé ; « Les maisons du monde » précise l'intégration unique des plausibles et retire les mentions devenues fausses « maître stocké » au niveau 3 et « rien n'entre dans l'état ». Garder la règle d'attribution de #534 et les contrats de photographie et de service.

Budget du diff, ajouts et retraits compris : modèle et chargement 35 lignes, documentation du modèle 20, tests 170, brief 65 ; total 290. Réutiliser les contrôles existants, ajouter leurs cas dans les fichiers qui portent l'invariant.

## Périmètre
jeu/sim/model.py
jeu/sim/world.py
jeu/sim/MODELE.md
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_maisons.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_write_coverage.py
docs/briefs/535-chaque-lieu-porte-son-maitre.md

## Conditions de succès
Commandes depuis `jeu/`, sauf SC9. Constater le rouge des nouvelles preuves avant l'implémentation. Les adaptations ci-dessous sont autorisées par l'issue ; garder toutes les assertions historiques et leurs contre-épreuves, sans tolérance nouvelle. Tout échantillon est non vide, les ensembles et compteurs se dérivent des données.

SC1 — `python3 -m pytest sim/tests/test_lieux.py -q` : `test_amorcage_conserve_habitants_et_panier` garde son ensemble exact de champs, augmenté seulement de `maitre`, et toutes ses preuves de conservation. Ajouter les cas des constructeurs existants, du maître fourni et de `None` explicitement absent ; un `World(...)` ne charge rien et n'invente aucun lieu, même lorsque lecteurs et attribution sont remplacés par des fonctions qui lèvent. Contre-épreuves : un champ parasite échoue à l'ensemble exact ; l'omission de `maitre` dans la sérialisation échoue ; les altérations de population et de panier déjà éprouvées échouent toujours.

SC2 — `python3 -m pytest sim/tests/test_maisons.py -q -k registre` : `test_registre_world` compare exactement toutes les fiches historiques aux trois tables, puis exactement les plausibles attendus, et exactement leur union triée par `id`, sans doublon. L'attente des plausibles se dérive des rangs libres et de la couverture indépendamment de `sim.maitres`, en réutilisant `_attente_maitres`. Vérifier l'appel unique du lecteur et de l'attribution, après existence des lieux et du registre historique ; chaque couple a un maître connu et égal à cette attente. Contre-épreuves : chacun des retraits et changements de fiche historiques déjà testés reste refusé ; un plausible absent, ajouté, dupliqué ou altéré, un maître absent ou inconnu font échouer le contrôle. Registre indisponible : conserver le refus existant.

SC3 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre` : les preuves d'attribution #534 restent exactes. Leur fixture `monde_maitres` reçoit explicitement `charger_registre_maisons(monde.carte)` avant toute attribution, pour ne pas réajouter les plausibles du monde désormais chargé. Deux appels restent purs, sans mutation, avec dicts distincts et fiches gelées. Adapter seulement la garde d'import : import local et appel autorisés dans `World.charger`, interdits ailleurs dans `world.py`, ainsi que dans `engine.py`, `snapshot_export.py` et `service.py`. Contre-épreuves : l'import injecté dans un chemin interdit est détecté ; toutes les attributions invalides de #534 restent refusées.

SC4 — `python3 -m pytest sim/tests/test_determinisme.py -q -k registre_bit_pres` : conserver les quatre couples `(0, 0)`, `(0, 42)`, `(42, 0)`, `(42, 42)` et les 366 points, amorçage puis 365 ticks. Le témoin garde la désactivation existante du registre et désactive explicitement l'attribution, par remplacement de son appel par `({}, ())` ; vérifier son registre vide et tous ses maîtres à `None`. Comparer les anciens états au bit près à chaque point : retirer uniquement `maitre` des lieux dans le document et dans les données brutes comparées, et le registre déjà exclu par ce contrôle. Garder tous les autres champs, y compris plans, dette, faim, paniers, flottants bruts, mer, carte, métadonnées, graphe, retours et état du générateur ; pas d'exclusion globale de `lieux` ni d'arrondi. Contre-épreuves : le stock ancien modifié par `math.nextafter` échoue encore au point 365 ; ajouter ce cas sur un stock de lieu ; une comparaison vide échoue. Aucun point ni couple de graines retiré.

SC5 — `python3 -m pytest sim/tests/test_determinisme.py -q -k registre_bit_pres` : séparément de la comparaison économique, à chacun des 366 points et pour chaque couple de graines, comparer la totalité des maîtres par couple et le registre complet, fiches historiques et plausibles, à leurs valeurs initiales copiées. Contre-épreuves : changer un maître seul fait échouer la stabilité des maîtres ; changer une fiche historique, puis une fiche plausible, fait échouer celle du registre. Ces contrôles ne masquent aucune différence ancienne ; les compteurs confirment 366 points par couple.

SC6 — `python3 -m pytest sim/tests/test_determinisme.py -q -k maitre_tick` : ajouter une garde dédiée interceptant la lecture de `EtatDeLieu.maitre` pendant un vrai tick ; conserver aussi la garde existante sur `World.maisons`. Les gardes ne couvrent que l'appel du tick, jamais la sérialisation ou la vérification après lui. Contre-épreuves : une enveloppe du tick qui lit seulement un maître, sans effet économique, déclenche la garde ; une lecture du registre reste détectée ; rappeler l'attribution pendant le tick fait échouer un espion dédié. Le tick intact passe.

SC7 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre` : ajouter la preuve que permuter cellules et fiches historiques avant attribution, séparément puis ensemble, donne exactement les mêmes maîtres et fiches plausibles ; couvrir aussi le chargement avec l'ordre de carte et celui du lecteur inversés. Registre final trié identique. Contre-épreuve : une attribution témoin dépendant de la position dans le parcours échoue à la même comparaison ; échantillon vide refusé.

SC8 — `python3 -m pytest sim/tests/test_write_coverage.py sim/tests/test_lieux.py -q` : le nouveau champ a un écrivain et un lecteur réels dans `model.py`, tous deux exercés ; le contrôle existant conserve son dénominateur intégral. Ajouter au fichier de couverture les contre-épreuves sur des copies temporaires des sources : omettre l'écriture de `maitre`, puis sa lecture, fait échouer les contrôles existants sans supprimer le champ déclaré. Vérifier dans `test_lieux.py` la documentation du maître, de `None` et du chargement complet ; retirer cette description du texte soumis au contrôle doit le faire échouer.

SC9 — Depuis la racine, `python3 -m pytest jeu -q` et `git diff --check` réussissent. Avant toute régénération d'une empreinte de `to_dict()` dans les tests autorisés, prouver par comparaison avec le témoin que seuls `maitre` et les fiches plausibles diffèrent ; rétablir les anciens champs et le registre historique doit retrouver exactement l'ancien document. Contre-épreuve : un ancien champ changé d'un bit fait échouer cette justification. Les empreintes figées de photographie, de `/lieu`, du pont et des vues restent exactes et inchangées ; leurs contre-épreuves existantes restent actives.

## Hors périmètre
Photographie, `/lieu`, `/monde`, service, réponses figées du pont, C#, Unity, Blender et vues. Aucune modification de `sim/maitres.py`, du lecteur `registre_maisons.py`, des trois tables, des constantes, de `lieux.py` ou du tick. Pas de noms plausibles (#392), de changement de maître, de part, de prélèvement, de transport au grenier, d'hommage ou d'ouverture du grenier (#395–#398). Aucun test assoupli, aucun total historique remplacé par une inclusion, aucun chargement implicite dans `World(...)`. Tout chemin absent du périmètre est interdit.
