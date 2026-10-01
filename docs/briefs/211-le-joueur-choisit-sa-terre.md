# Lot #211 — Le joueur choisit sa terre
Jalon : J2 · Machine : vps · Taille prévue : 285 lignes

## But
Le joueur choisit sa terre de départ parmi les cinq seigneuries de 1400 par une intention, `choisir_depart`, déposée par `POST /intention` sur le service ou par `python3 -m forge --depart <id>` ; le tick suivant l'applique et le monde la retient comme la maison du joueur. Une seigneurie inconnue ou un second choix sont refusés. Même graine et même choix donnent le même monde ; sans choix, rien ne change.

## Règle du monde
Elle découle de « Les seigneuries de départ, vue dérivée » (#210) de `jeu/sim/MODELE.md`, et de la décision du jalon 1 dans `CAP.md` : Unity et les autres clients déposent des intentions (`/intention`), et c'est le tick suivant qui les applique. C'est la première intention appliquée. **Base : master après #210** (`a4732dd`). Si la branche part d'avant, le codeur la rebase d'abord sur `origin/master`.

**L'intention.** C'est un objet JSON `{"type": "choisir_depart", "seigneurie": <id>}`, où `<id>` est l'`id` entier d'une seigneurie de `data/seigneuries-1400.json`. Le dépôt se fait par **un seul chemin**, `deposer_intention(monde, intention)` de `sim/intentions.py`. Le service et la commande `forge` l'appellent tous deux. L'IA prendra le même chemin au jalon 5.

**Le dépôt vérifie, puis met en attente. Il ne touche jamais le monde visible.** Les refus lèvent `IntentionRefusee` (sous-classe de `ValueError`) avec un message qui nomme la cause. Tout refus intervient avant la mise en attente :
- `seigneurie` absente, booléenne ou non entière, ou `id` absent de la table : « seigneurie inconnue : <valeur reçue> ». La table se lit par `charger_seigneuries()` ; un siège hors carte est refusé par `cellule_du_siege` (une terre hors carte ne se joue pas) ;
- **second choix** : le monde a déjà une maison du joueur, ou un choix est déjà en attente. Le message est « départ déjà choisi : <id retenu ou en attente> ».

Une intention acceptée devient un `ChoixDepart(identifiant)`, dataclass gelée de `sim/intentions.py`, et s'ajoute à `monde.intentions_en_attente` (une liste). Elle n'entre ni dans `cells`, ni dans `plans`, ni dans `to_dict()`.

**Le tick l'applique.** Une nouvelle étape `_appliquer_intentions(world)` de `sim/engine.py` vient juste après `_valider_numero_tick` (une garde passe avant l'effet) et avant `_apply_fabrication`. Pour un `World`, elle vide `intentions_en_attente` dans l'ordre et pose `world.maison_du_joueur = intention.identifiant`. Pour un autre objet (les mondes d'épreuve des tests), elle ne fait rien, comme `_avancer_compteur_ticks`. Elle ne tire aucun aléa et ne lit ni n'écrit aucune cellule. Le tick ne lit `maison_du_joueur` nulle part ailleurs : au jalon 2, le choix ne change ni production, ni commerce, ni population.

**Le monde la retient.** `World.maison_du_joueur` vaut `None` au chargement, et l'`id` de la seigneurie une fois le choix appliqué. `World.to_dict()` ne porte la clé `"maison_du_joueur"` **que si elle n'est pas `None`**. Sans choix, la sérialisation et son empreinte sont donc exactement celles d'avant le lot. Avec un choix, elles en diffèrent.

**Le service.** Dans `POST /intention`, un objet dont le `type` vaut `"choisir_depart"` passe par `deposer_intention`, sous `verrou_tick` : un dépôt ne se croise jamais avec un tick. Les réponses :
- acceptée : 200 `{"acceptee": true, "appliquee_au_tick": <tick publié>}`, comme aujourd'hui ;
- seigneurie inconnue ou mal formée : 400, avec le message ;
- second choix : 409 (`HTTPStatus.CONFLICT`), avec le message.

Tout autre objet garde le comportement d'aujourd'hui : il est accepté et ne change rien. `test_service_monde_est_leger_et_intention_ne_mute_rien` le fige (`{"route": "essai"}`). Le refuser serait une liste fermée d'intentions : elle viendra avec la deuxième intention, c'est une **lacune déclarée**. Le document `/monde` ne porte `"maison_du_joueur"` que s'il y en a une. Les octets de `/monde`, `/lieu` et `/plan` d'un monde sans choix ne changent pas.

**La commande.** Dans `python3 -m forge`, l'option `--depart ID` (entier, répétable par `action="append"`) dépose chaque valeur dans l'ordre par `deposer_intention`, sur le monde chargé et **avant le premier tick**. Le premier tick applique donc le choix. Les refus rendent le code 2 avec le message sur stderr, avant de simuler et sans écrire `resume.json` :
- un refus de `deposer_intention` (y compris un second `--depart`) ;
- `--depart` avec `--ticks 0` : « l'intention s'applique au tick suivant ».

Avec un choix, `resume.json["simulation"]["maison_du_joueur"]` vaut l'`id` ; sans choix, la clé est absente. La photographie `monde.json` ne porte pas le choix : elle reste identique octet pour octet, avec ou sans `--depart`.

**Le piège payé par #210.** `test_seigneuries.py::test_pure` exige que le mot `seigneur` n'apparaisse sur **aucune ligne** de `engine.py`, `world.py` et `model.py`, commentaires compris. Le moteur et le monde disent `maison_du_joueur`, `ChoixDepart`, `identifiant`. Seul `sim/intentions.py` lit la clé `"seigneurie"` du JSON. `ChoixDepart` ne vit jamais dans `sim/model.py`, que `test_write_coverage.py` inspecte. `engine.py` n'importe pas `sim.intentions` : il ne lit que `.identifiant`. Sinon on aurait un import circulaire, car `seigneuries` importe `engine`.

**Niveaux.**
- Niveau 1 : les cinq seigneuries et leurs attributions, héritées de #210, sans changement.
- Niveau 2, plausible : la maison du joueur réduite à l'`id` de sa seigneurie, donc à la cellule de son siège.
- Niveau 3, pas simulé : ce que la maison du joueur fait au monde (prélèvement, jalon 3), les maisons de l'IA (jalon 5), les personnes (jalon 6).

### Ce que le codeur écrit
1. **`jeu/sim/intentions.py`** (nouveau, sans littéral numérique hors {0, 1, −1}) : `TYPE_CHOISIR_DEPART = "choisir_depart"`, `IntentionRefusee`, `ChoixDepart`, `deposer_intention(monde, intention, seigneuries=None) -> ChoixDepart`.
2. **`jeu/sim/engine.py`** : `_appliquer_intentions`, son appel dans `tick()` et la ligne correspondante dans la docstring « Ordre du tick ».
3. **`jeu/sim/world.py`** : `intentions_en_attente = []` et `maison_du_joueur = None` dans `__init__`, la docstring des attributs et la clé conditionnelle de `to_dict()`.
4. **`jeu/sim/service.py`** : le branchement de `/intention` décrit plus haut, et la clé conditionnelle du document `/monde` dans `_construire_etat`.
5. **`jeu/forge/__main__.py`** : `--depart`, le dépôt dans `_simuler`, la clé de `resume.json`, une ligne dans la docstring du module.
6. **`jeu/sim/MODELE.md`** :
   - dans « En une page », une étape 2 **Intentions** (`_appliquer_intentions`), puis la renumérotation 3 à 12 ;
   - une section « ## Les intentions du joueur », juste après « Les seigneuries de départ, vue dérivée » : la règle ci-dessus, les refus, la clé conditionnelle, la lacune déclarée et les trois niveaux. La section des seigneuries n'est pas réécrite.
7. **`jeu/sim/README.md`** : deux phrases sur `POST /intention` et `choisir_depart`, et `sim/intentions.py` dans la table des modules.
8. Les tests ci-dessous, en ajouts seulement.

## Périmètre
jeu/sim/intentions.py
jeu/sim/engine.py
jeu/sim/world.py
jeu/sim/service.py
jeu/forge/__main__.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_determinisme.py
jeu/forge/tests/test_forge.py
docs/briefs/211-le-joueur-choisit-sa-terre.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`. Aucun `id` de seigneurie n'est écrit en dur dans un test : on le trouve par `nom` dans `charger_seigneuries()`. « max + 1 » se dérive de la table. Chaque test imprime ses compteurs, et un échantillon vide échoue. Chaque contre-épreuve est prouvée rouge avant d'être gardée.

**SC1 — le dépôt refuse ce qu'il ne peut pas jouer.** Commande : `python3 -m pytest sim/tests/test_intentions.py -q -s -k refus`.
- Un test paramétré sur `World.charger(0)` essaie `seigneurie` absente, `True`, `"Bar"`, `2.5` et max + 1 : chacun lève `IntentionRefusee` en nommant la valeur. Après chaque refus, `intentions_en_attente == []`, `maison_du_joueur is None`, et `to_dict()` est inchangé (`refus_observés == len(cas) > 0`).
- Second choix : un dépôt (Duché de Bar) accepté, puis un second (Despotat de Morée) refusé « déjà choisi », avant le tick puis après un tick. Dans les deux cas, `maison_du_joueur` reste l'`id` de Bar.
- Contre-épreuve : le dépôt de Bar sur un monde neuf est accepté et rend `ChoixDepart` avec son `id`.

**SC2 — le tick suivant l'applique, et seulement lui.** Commande : `python3 -m pytest sim/tests/test_intentions.py -q -s -k applique`.
- Après le dépôt et avant tout tick, `maison_du_joueur is None` et `to_dict()` n'a pas changé.
- Après un `tick(monde, random.Random(0), 0)`, `maison_du_joueur` est l'`id` de Bar et la liste d'attente est vide.
- `_etapes_tick_dans_code` (importée de `sim.tests.test_monde`), appliquée à `engine.py`, rend `_appliquer_intentions` juste après `_valider_numero_tick`, en deuxième position.
- `python3 -m pytest sim/tests/test_monde.py -q -k ordre_du_tick` reste vert.
- Contre-épreuve : un tick dont le numéro est faux (`numero_tick = 5` sur un monde à 0) lève `ValueError` et laisse le choix en attente. La garde passe avant l'effet.

**SC3 — même graine et même choix, même monde ; sans choix, rien ne change.** Commande : `python3 -m pytest sim/tests/test_determinisme.py -q -s -k depart`.
- Deux `World.charger(0)` reçoivent le même choix et jouent 10 ticks avec `random.Random(0)` : leurs `to_dict()` sont égaux, de même que leurs empreintes SHA-256 et `rng.getstate()`.
- Un troisième monde, sans choix, joue les mêmes ticks. Ses `to_dict()["cells"]` et `["plans"]` sont égaux à ceux des deux premiers, et ses clés sont exactement `{"cells", "plans", "ticks_ecoules"}`. Le choix ne tire aucun aléa et ne touche aucune cellule.
- Contre-épreuves : le même parcours avec la Morée au lieu de Bar donne une empreinte différente. Une cellule modifiée d'un habitant fait échouer la comparaison des cellules.

**SC4 — le service retient le choix et refuse le reste.** Commande : `python3 -m pytest sim/tests/test_intentions.py -q -s -k service`. Elle passe par `lancer_service(0)` et `requete_service` de `sim.tests.test_monde`.
- Refus d'abord : l'`id` max + 1 et `"Bar"` rendent 400 avec « seigneurie » dans l'erreur. Les octets de `/monde` sont inchangés et `tick == 0`.
- Ensuite le choix de Bar : 200 `{"acceptee": true, "appliquee_au_tick": 0}`. `/monde` n'a pas encore `maison_du_joueur`. Après `POST /tick?n=1`, `/monde` porte `maison_du_joueur` égal à l'`id` de Bar.
- Un second choix (Morée) rend 409 avec « déjà choisi », et les octets de `/monde` restent les mêmes.
- `{"route": "essai"}` rend toujours 200 et ne change rien.
- Contre-épreuve : un service de graine 0 où l'on ne dépose rien n'a pas `maison_du_joueur` dans `/monde` après le même tick. `python3 -m pytest sim/tests/test_monde.py -q -k "service or intention"` reste vert sans modification.

**SC5 — la commande `forge --depart`.** Commande : `python3 -m pytest forge/tests/test_forge.py -q -s -k depart`, au même horizon court que les autres tests du fichier.
- `--depart <id de Bar>` rend 0 et `resume.json["simulation"]["maison_du_joueur"]` vaut cet `id`.
- Sans `--depart`, la clé est absente.
- Le `monde.json` des deux exécutions est identique octet pour octet.
- Refus, en code 2, sans écrire `resume.json` : max + 1, `--depart` donné deux fois, `--depart` avec `--ticks 0`.
- Contre-épreuve : le test qui exige le code 2 pour max + 1 rougit si `deposer_intention` accepte tout. On le prouve en mémoire par `monkeypatch`.

**SC6 — rien d'existant ne bouge, et le modèle le dit.** Commande : `python3 -m pytest jeu -q` depuis la racine. Elle reste verte, en particulier `test_seigneuries.py::test_pure`, `test_write_coverage.py`, `test_no_hardcoded.py` et `test_ordre_du_tick_documente_est_celui_du_code`.
- `git diff origin/master -- jeu/sim/tests jeu/forge/tests | grep -E '^-[^-]'` ne rend rien : les tests existants ne reçoivent que des ajouts.
- `grep -c "^## Les intentions du joueur" jeu/sim/MODELE.md` rend 1.
- Contre-épreuves :
  - écrire « seigneurie » dans un commentaire de `world.py` fait rougir `test_pure` ;
  - ôter `_appliquer_intentions` de « En une page » fait rougir l'ordre du tick ;
  - sur la base, le `grep` de la section rend 0.

## Hors périmètre
- La carte de 1400 à l'écran, la fiche de la terre choisie dans une vue ou dans Unity, la capture du jalon et la photographie `--snapshot-json` qui porterait le choix.
- Une liste fermée des intentions : tout autre objet reste accepté sans effet, comme aujourd'hui.
- Tout effet du choix sur le monde : prélèvement, siège, capitale, lieux (jalon 3), plan du bourg (jalon 4), maisons de l'IA (jalon 5), personnes (jalon 6).
- Revenir sur un choix, en changer, sauvegarder ou recharger une partie, relire un monde depuis `to_dict()`.
- `seigneuries-1400.json`, `seigneuries.py`, `puissances.py`, `maisons.py`, `villes.py`, l'amorçage, la carte figée, les vues (`vues/`), la chronique rejouée par `forge`, `jeu/ville/`, `3d/`, et tout test existant.
