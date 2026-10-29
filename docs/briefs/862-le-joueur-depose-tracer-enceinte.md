# Lot #862 — Le joueur dépose `tracer_enceinte`
Jalon : J4 · Machine : vps · Taille prévue : 285 lignes

## But
Le joueur pourra confier au monde le contour de l’enceinte de sa capitale, qui deviendra au tick suivant un chantier du plan ou sera refusé sans effet avec sa raison.

## Le joueur
Le joueur trace les murs autour de la place de sa capitale et choisit combien de foyers il retire aux champs pour ce chantier ; il sent que son tracé engage la ville parce qu’il doit entourer sa place, épargner les maisons de 1400 et rester sur sa terre. Un contour impossible, posé chez un autre ou déjà engagé est refusé avec une raison précise. Ce lot livre le geste Python de J4 ; #417 le rendra visible et manipulable dans la capitale en 3D.

## Règle du monde
Découle des sections « Les intentions du joueur » et « Le plan du bourg » de `jeu/sim/MODELE.md`. Niveau 2, plausible, jamais sourcé : forme du contour, assise de 6 m et coût en journées. Niveau 1 : aucune donnée historique nouvelle. Niveau 3, non simulé ici : portes, matériaux, hauteur, effet défensif et siège.

L’intention est `{"type": "tracer_enceinte", "maison": M, "cell": C, "points": [[x, y], ...]}` avec `foyers` facultatif, égal à 1 par défaut. Les champs, la cellule, les points finis et les foyers suivent les validations communes des constructions. Le contour est fermé implicitement entre son dernier et son premier point. Il est refusé avant toute mutation si deux côtés non voisins se coupent ou se touchent, avec « enceinte : contour qui se croise », ou s’il ne contient pas entièrement la place de la base de 1400 sans que son bord la traverse, avec « enceinte : place de 1400 non entourée ».

`ASSISE_ENCEINTE_M = 6` est la largeur totale au sol du mur, relue dans `sim.constants` au contrôle. Chaque côté, fermeture comprise, devient une emprise de cette largeur pour la garde existante des maisons de 1400. La première maison touchée conserve le refus nommé « cellule C : maison de 1400 R (F foyers) touchée ». Une base absente est déclarée, jamais devinée. La garde territoriale relit ensuite le maître actuel du bourg et conserve exactement « ce lieu n’est pas à toi : <maître> ».

Un plan qui porte déjà une enceinte refuse « enceinte déjà tracée ». Une `TracerEnceinte` de la même cellule déjà en attente refuse « enceinte déjà promise ». Tous ces refus laissent le monde, le plan et la file inchangés. Une acceptation ajoute seulement une intention gelée à la file. Au tick suivant, elle reconstruit le plan avec son unique `Enceinte`, `en_chantier=True`, le nombre de foyers demandé, zéro travail fourni et le travail requis recalculé par `travail_requis_de_enceinte`; rues, parcelles et bâtiments restent identiques. Sans tick, rien ne change.

Le service traite `tracer_enceinte` comme les trois constructions existantes : il exige un départ appliqué, remplace toute `maison` reçue par `maison_du_joueur` sur une copie, puis passe par le dépôt commun. `--gestes` exige au contraire la maison explicite. Le reçu, le verrou, le tick annoncé et les refus HTTP gardent leur contrat.

## Périmètre
docs/briefs/862-le-joueur-depose-tracer-enceinte.md
jeu/sim/constants.py
jeu/sim/intentions.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_intentions.py

## Conditions de succès
SC1 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k enceinte_depot` dépose un contour simple qui entoure la place, ne touche aucune maison et appartient au déposant : le monde et le plan restent identiques, une seule `TracerEnceinte` gelée attend avec les points copiés et `foyers=1`, puis un second dépôt refuse « enceinte déjà promise ». Contre-épreuves : retirer chaque champ obligatoire, ajouter un champ, donner moins de trois points, un point non fini, un foyer nul ou booléen, un contour croisé ou seulement tangent, une place traversée ou extérieure, une base absente, une terre voisine, une enceinte présente ou promise doivent produire leur refus nommé sans modifier monde, plan ni file ; un échantillon vide échoue.

SC2 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k enceinte_assise` éprouve à Biskra et à Paris tous les côtés du contour, fermeture comprise : avec `ASSISE_ENCEINTE_M == 6`, une assise qui rencontre une maison de 1400 la nomme avec son rang et ses foyers, tandis qu’un contour dégagé est accepté. Contre-épreuves : omettre le côté de fermeture ou remplacer en mémoire la constante par une largeur qui ne touche plus la maison doit changer le verdict ; appeler le contrôle sans amorçage doit déclarer l’absence au lieu de deviner une base.

SC3 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k enceinte_tick` vérifie qu’avant le tick le plan est inchangé, puis qu’au tick suivant l’enceinte entre seule au plan en chantier avec le contour copié, les foyers demandés, `travail_fourni == 0` et le requis de `travail_requis_de_enceinte`, sans altérer les trois listes du plan. Contre-épreuves : appliquer dès le dépôt, laisser l’enceinte hors chantier, perdre une rue, une parcelle ou un bâtiment, oublier la fermeture dans le coût, ou figer la constante de travail avant le tick fait rougir.

SC4 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k enceinte_service` exerce `POST /intention` sous le verrou : sans départ puis avec un départ seulement en attente, le service refuse ; après application du départ du Zab, il accepte à Biskra, impose `seigneurie-6` malgré une maison absente ou falsifiée, annonce le tick suivant, et `/plan` ne publie l’enceinte qu’après ce tick. Contre-épreuves : viser Paris reste refusé au nom de son maître ; chaque refus conserve tick, état publié, plan, file et journal à l’octet près.

SC5 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q -k 'enceinte_cli or enceinte_documentation'` rejoue deux fois par `--gestes` une enceinte à Biskra avec maison explicite et obtient le même monde canonique ; le README et les deux sections nommées de `MODELE.md` portent le JSON, les refus, l’assise et l’application différée. Contre-épreuves : retirer `maison`, croiser le contour ou enlever un terme exigé de la documentation fait échouer la commande sans écrire de nouvelle sortie.

SC6 — `python3 -m pytest jeu/sim/tests/test_intentions.py -q`, puis `python3 -m pytest jeu -q`, passent sans suppression, réécriture ni assouplissement d’un test existant. `git diff --check`, `git diff --name-only`, `git ls-files --others --exclude-standard` et `git diff --numstat` ne montrent que le périmètre et un total ajouté plus retiré strictement inférieur à 300 lignes, brief compris. Contre-épreuve : un ancien geste, un plan sans enceinte ou un chemin hors périmètre modifié, ou un total d’au moins 300 lignes, refuse la livraison.

## Hors périmètre
L’avancement quotidien, l’affectation effective des bras, le paiement en grain, la récolte perdue et l’achèvement du chantier ; les portes et leur raccord aux rues ; matériaux, hauteur, entretien, effet défensif, bataille et siège ; décision de l’IA ; commande depuis la carte ; Unity, Blender, outil de tracé, panneau, dessin et capture de #417. Aucun test existant n’est assoupli et tout autre chemin est interdit.
