# Lot #896 — Un service d'épreuve peut vider le bourg
Jalon : J4 · Machine : vps · Taille prévue : 230 lignes

## But
Un service d'épreuve jetable peut envoyer tous les habitants du bourg d'une cellule dans ses autres lieux, sans toucher à la population, aux métiers ni aux stocks, et publier ce bourg vide pour éprouver que les passants de la capitale suivent le monde.

## Le joueur
Lot de fond, sous-lot 1 de #789 « L'épreuve montre les ouvriers au chantier et la rue qui se vide », lui-même découpé de #421 « Les gens du bourg circulent dans les rues ». Il prépare l'écran du J4 : « une ville vivante dont chaque passant suit le monde ». Quand le joueur entre dans sa capitale, il doit voir des rues pleines si son bourg est peuplé, et des rues vides si ses gens sont partis : la ville ne lui ment pas. La faim ne vide pas un bourg (mesure de #789 : Biskra descend à 159 habitants puis remonte), d'où ce montage. Les sous-lots 2 (session Unity, pc) et 3 (juge, pc) de #789 le rendront visible : à Biskra, 165 habitants au bourg, donc 16 passants avant, zéro après (#784, dix habitants par passant). Ce lot seul ne change rien à l'écran ni au jeu.

## Règle du monde
Sans objet : outil d'épreuve, aucune règle de jeu neuve. Il s'appuie sur `jeu/sim/MODELE.md`, « Les lieux d'une cellule, vue dérivée » (le bourg est le rang 0, la somme des habitants des lieux est la population de la cellule), « Les foyers par métier » (les métiers sont ceux de la cellule) et « Le chantier et ses bras ». Le montage est décrit dans « Ce que porte un lieu », juste après celui de #777 (`vider-panier`).

Contrat à livrer, dans `jeu/sim/service.py` :

- `POST /epreuve/vider-bourg?cell=X` n'existe qu'avec `--epreuve` ; sur le service ordinaire, HTTP 404 sans rien toucher. Ce n'est jamais un type d'intention, ni pour le joueur ni pour l'IA.
- Mêmes refus que `vider-panier`, dans le même ordre, sous les mêmes verrous (`verrou_tick`, `condition_vitesse`), avant toute mutation : horloge active → 409 ; `cell` absent, vide, répété ou non entier → 400 ; cellule inconnue → 404 ; montage invalide pour `_valider_epreuve` → 400. Un refus en plus : une cellule sans autre lieu que le bourg → 400 (194 cellules habitées n'ont qu'un lieu, graine 0). Réutiliser la garde existante, sans la modifier : partager la branche de `vider-panier` est permis, changer son comportement non.
- Le montage : `P` = habitants du rang 0. `partager(P, surfaces des rangs 1 à n−1)` de `sim/lieux.py` (plus fort reste, reliquat au rang 1), surfaces de `surfaces_des_lieux` ; chaque autre lieu reçoit sa part, le rang 0 passe à 0. Rien d'autre ne bouge : population et métiers de la cellule, paniers de la cellule et de chaque lieu, dettes, faims, reliquats de mortalité et de natalité, maîtres, compte des bras du jour (non publié, effacé au tick suivant par `avancer_chantiers`), greniers, plans, intentions, journal des flux, autres cellules, tick, aléa. Les flux sur 30 jours ne comptent ni départ ni arrivée : ce n'est pas une migration.
- Republier `EtatPublie` par `_construire_etat`, comme `vider-panier`, puis répondre HTTP 200 `{"cell_id", "tick"}`. Le tick ne bouge pas : il désigne cet état préparé.

Mesures, service `--epreuve`, graine 0 : Biskra = cellule 10103, 21 lieux, 3 459 paysans ; bourg 165. Après le montage : bourg 0, rangs 1 à 5 à 174, 6 à 14 à 173, 15 à 20 à 172 ; total 3 459. Au tick 5 avec trois routes, 15 ouvriers tous pris au bourg : le montage passe, et un tick joué ensuite garde le bourg à 0 et prend ses ouvriers aux autres lieux (essai du chef, non livré).

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
docs/briefs/896-un-service-d-epreuve-peut-vider-le-bourg.md

## Conditions de succès
Commandes depuis la racine. Les cas neufs vont dans `jeu/sim/tests/test_monde.py`, à côté de ceux du service d'épreuve, avec `vider_bourg` dans leur nom ; aucun test, aide ou référence existant ne change (réutiliser `_service_epreuve`, `_memoire_epreuve`, `requete_service`, `lancer_service` sans les modifier). Montrer leur rouge avant le code, puis leur vert. Budget : 40 lignes de service, 110 de tests, 10 de `MODELE.md`, le reste au brief.

SC1 — **Réservé au service jetable.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k vider_bourg_reserve`. Sur le service ordinaire, `POST /epreuve/vider-bourg?cell=<Biskra>` rend 404 et `_memoire_epreuve` est identique avant et après. Le vrai module lancé avec `--epreuve` (sous-processus, comme `test_service_epreuve_reserve`) rend 200 `{cell_id, tick: 0}` puis `/lieu?cell=X&bourg=1` sert un bourg à 0 habitant. `/intention` refuse un type `vider_bourg` par 400, même en épreuve. Contre-épreuve : un geste ouvert au service ordinaire, ou servi comme intention, fait rougir le cas.

SC2 — **Le bourg se vide, rien d'autre ne bouge.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k vider_bourg_montage`. Sur Biskra (cellule tirée de `depart_biskra` et vérifiée dans `/departs`), puis sur une autre cellule à plusieurs lieux et bourg habité. Avant le POST, poser au bourg une marchandise non alimentaire fractionnaire (accesseurs de `sim.model`, total cellulaire accordé) et un grenier ; relire `/lieu?cell=X` et `/lieu?cell=X&bourg=1`. Référence : copie profonde du monde où seules les populations des lieux reçoivent le partage attendu. Exiger : `pickle.dumps(monde) == pickle.dumps(référence)`, aléa et tick identiques ; à Biskra, bourg à 0, chaque autre lieu gagne 8 ou 9, total 165 gagné, cellule à 3 459. Les deux `/lieu` relus ne diffèrent des anciens que par les champs `population` des lieux et du bloc `bourg` (population et foyers de la cellule, paniers, faims, `flux_30j`, tick identiques). `/monde`, `/plan`, `/occupation` annoncent le même tick. Contre-épreuves rejetées par le même vérificateur : tout le bourg envoyé au rang 1, un habitant laissé au bourg, une population de cellule diminuée de 165, des métiers changés, un panier déplacé avec ses gens, l'ancien `/lieu` publié.

SC3 — **Les refus précèdent le montage.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k vider_bourg_refus`. Horloge neutralisée par `monkeypatch` de `_faire_avancer_horloge`, comme `test_service_epreuve_refus`. Refus attendus : horloge active 409 ; `cell` absent, vide, répété, non entier 400 ; cellule inconnue 404 ; bourg absent, dupliqué ou déjà vide, lieux absents ou nuls, rang invalide, population négative ou textuelle 400 ; cellule habitée à un seul lieu 400. Chaque refus laisse `_memoire_epreuve` identique. Contre-épreuve : la même cellule, remise intacte et horloge à l'arrêt, rend 200 et vide son bourg ; un faux 200 sans montage et un refus systématique rougissent donc aussi.

SC4 — **Après le montage, le monde joue encore.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k vider_bourg_tick`. Biskra en épreuve : choix du départ, trois routes de 40 m au tick 1, ticks jusqu'au 5, puis le POST (200, tick 5) ; `POST /tick?n=1` rend 200, la somme des lieux reste la population de la cellule, le bourg reste à 0. Deux services identiques donnent les mêmes octets de `/lieu?cell=X&bourg=1` après le POST. Contre-épreuve : un montage qui laisse la somme des lieux différente de la population fait rougir le cas.

SC5 — **Rien d'ancien ne bouge.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'service_epreuve or service_bourg or reponse_figee or service_ia_sans'`, puis `python3 -m pytest jeu -q`. Tout vert, sans retouche d'un test existant ; `vider-panier` garde ses réponses et ses refus. Contre-épreuve : un `git diff master -- jeu/sim/tests/test_monde.py` qui retire ou modifie une ligne existante interdit la livraison.

`MODELE.md` : trois à six lignes après le paragraphe de `vider-panier`, disant la route, ses refus, le partage par surface vers les rangs 1 à n−1, ce qui ne bouge pas, l'absence de tick et de flux, et que ce geste n'est jamais une intention.

## Hors périmètre
La session Unity et le juge de #789 (sous-lots 2 et 3, pc), les passants eux-mêmes (#784, #788). Aucune migration ni départ ajouté au jeu, aucun changement de démographie, de faim, de chantier, de répartition des lieux au tick ni de constante. Aucun bouton ni intention, aucune sauvegarde du montage, aucune clé spatiale neuve. `vider-panier` et ses tests ne changent pas ; aucun test existant assoupli ou réécrit.
