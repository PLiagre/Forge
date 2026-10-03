# Lot #254 — Une intention déposée s'applique au tick suivant, et la première trace une route
Jalon : J4 · Machine : vps · Taille prévue : 285 lignes

## But
Le joueur dépose `{"type": "tracer_route", "cell", "points", "largeur_m"}` par `POST /intention` ou par une liste de gestes rejouée avec `python3 -m sim --gestes`. Il reçoit un reçu : acceptée avec le tick où elle s'appliquera, ou refusée avec sa raison. Au tick suivant, la route entre au plan du bourg comme une rue en chantier. Une intention inconnue ou mal formée est refusée et ne change rien. Même graine et mêmes gestes donnent le même monde ; sans geste, le monde reste celui d'aujourd'hui.

## Règle du monde
Elle découle de deux sections de `jeu/sim/MODELE.md` : « Les intentions du joueur » (#211, le dépôt, l'attente, l'étape 2 du tick) et « Le plan du bourg » (#253, `World.plans`, `Rue`). C'est la preuve de J4 dans `CAP.md` : « chaque geste est une intention déposée dans `sim/` et appliquée au tick suivant ; même graine et mêmes gestes, même monde ; sans le geste, rien ne bouge ». Contre-épreuve de CAP : « un moteur qui ignore l'intention ». **Base : master après #253 et #211** (`7359be3`).

**Décision du propriétaire (issue #254, réponse A).** Une intention inconnue n'est plus acceptée. L'ancien envoi `{"route": "essai"}` devient un cas refusé. Les tests qui l'exigeaient sont réécrits pour être plus stricts. L'envoi « essai » figure à deux endroits, avec la même assertion « 200, rien ne bouge » :
- `test_monde.py::test_service_monde_est_leger_et_intention_ne_mute_rien`, ligne `intention = json.dumps({"route": "essai"})…` ;
- `test_intentions.py::test_service_refus_et_choix`, ligne `assert _poster(port, {"route": "essai"})[0] == HTTPStatus.OK`.

La décision A porte sur cet envoi. Le lot réécrit donc **ces deux lignes, et seulement elles** (voir SC6). La lacune déclarée de #211 (« tout autre objet reste accepté sans effet ») est levée.

**La liste fermée.** `sim/intentions.py` gagne `TYPE_TRACER_ROUTE = "tracer_route"` et un seul point d'entrée, `recevoir_intention(monde, intention)`. Le service et `python3 -m sim --gestes` l'appellent, et l'IA le prendra au jalon 5. Selon le `type` :
- `"choisir_depart"` → `deposer_intention`, **inchangée**. `test_refus_second_choix_et_acceptation` l'appelle sans `type`, et `forge --depart` continue de l'appeler directement ;
- `"tracer_route"` → le dépôt d'une route, ci-dessous ;
- tout autre `type`, ou pas de `type` → `IntentionRefusee("type d'intention inconnu : <repr>")`.

**Le dépôt d'une route vérifie, puis met en attente.** Il ne touche ni `cells`, ni `plans`, ni `to_dict()`. Chaque refus lève `IntentionRefusee` avant toute mise en attente :
- les clés doivent être exactement `type`, `cell`, `points` et `largeur_m`. Sinon : « champ manquant : <nom> » ou « champ inconnu : <nom> » ;
- `cell` doit être un entier, ni booléen, présent dans `monde.plans`. Sinon : « cell inconnu : <repr> » ;
- `points` et `largeur_m` sont vérifiés en construisant la `Rue` de `sim/plan.py`. Un `PlanInvalide` devient « route invalide : <message du plan> ». C'est la règle de #253 sans rien de neuf : au moins `POINTS_MIN_RUE` couples `(x, y)` de nombres finis, et une largeur finie strictement positive.

Une route acceptée devient un `TraceRoute(cell_id, points, largeur_m)`, dataclass gelée de `sim/intentions.py`. Ses points sont copiés en tuples : modifier ensuite la liste de l'appelant ne change pas l'attente. Elle s'ajoute à `monde.intentions_en_attente`.

**Le tick les applique en tête, dans l'ordre du dépôt.** `_appliquer_intentions` reste l'étape 2, juste après la garde `_valider_numero_tick`. Pour un `World`, elle appelle `intention.appliquer(monde)` sur chaque intention en attente, dans l'ordre de la liste, puis vide la liste. Un monde d'épreuve est ignoré, comme aujourd'hui.
- `ChoixDepart.appliquer` pose `maison_du_joueur`, exactement comme avant.
- `TraceRoute.appliquer` remplace `monde.plans[cell_id]` par un `Plan` reconstruit, ce qui revalide tout. Ce plan reçoit une `Rue` d'`identifiant` = (le plus grand identifiant de rue du plan, ou −1) + 1, avec les points, la largeur et `en_chantier=True`. Deux routes déposées sur la même cellule reçoivent donc des identifiants croissants dans l'ordre du dépôt.
- L'écriture du plan vit dans `sim/intentions.py`, **jamais dans `sim/engine.py`**. `test_plan_absent_de_l_arbre_du_moteur` interdit tout attribut `plans` dans le moteur. Le moteur n'importe toujours pas `sim.intentions` : il appelle seulement `.appliquer`.
- Rien d'autre ne lit le plan au tick, et aucune route ne tire d'aléa, ne lit ni n'écrit de cellule.

**La rue en chantier.** `Rue` gagne un dernier champ, `en_chantier: bool = False`. Tout autre type qu'un booléen lève `PlanInvalide`. Il entre dans `to_dict()` par `asdict`. Un plan vide se sérialise toujours `{"rues": [], "parcelles": [], "batiments": []}`. Les octets de `/plan`, `/monde` et `/lieu`, et l'empreinte d'un monde sans geste, ne changent donc pas. Une rue en chantier ne fait rien au monde, et rien ne la fait passer à achevée dans ce lot.

**Le reçu du service.** `POST /intention` passe **tout** objet JSON par `recevoir_intention`, sous `verrou_tick`.
- Si l'intention est acceptée, la réponse est 200 `{"acceptee": true, "appliquee_au_tick": <tick publié>}`, à l'octet comme aujourd'hui.
- Si elle est refusée, la réponse est 400, ou 409 pour « départ déjà choisi » comme aujourd'hui. Le corps est `{"acceptee": false, "erreur": "<raison>"}`. Les refus de corps (JSON illisible, pas un objet) prennent la même forme.
- Aucun refus ne fait avancer ni ne republie le monde.

**La liste de gestes en ligne de commande.** `python3 -m sim` gagne deux options :
- `--gestes FICHIER` lit une liste JSON d'entrées `{"tick": t, "intention": {…}}`. Avant de jouer le tick `t`, la commande dépose par `recevoir_intention`, dans l'ordre du fichier, les intentions de ce tick. Le tick `t` les applique donc. `_simulate(ticks, seed, gestes=None)` garde ses deux premiers paramètres.
- `--monde-json FICHIER` écrit `World.to_dict()` final en JSON canonique : clés triées, `ensure_ascii=False`, séparateurs compacts, UTF-8.

Ces cas rendent le code 2 avec la raison sur stderr, sans rien écrire (ni `--monde-json`, ni `--snapshot-json`) :
- un fichier illisible, qui n'est pas une liste, ou une entrée sans `tick` ou sans `intention` ;
- `tick` non entier, booléen ou négatif ;
- des `tick` qui décroissent dans le fichier ;
- `tick ≥ --ticks` : « l'intention s'applique au tick suivant » ;
- tout refus de `recevoir_intention`, avec le rang de l'entrée.

**Niveaux.**
- Niveau 2, plausible : la route réduite à une ligne et une largeur dans le plan du bourg, et son état « en chantier ».
- Niveau 3, pas simulé :
  - le travail qu'elle coûte, les bras pris aux champs, son achèvement, le flux qu'elle concentre ;
  - la restriction à la capitale du joueur : toute cellule de la carte est acceptée ;
  - les bornes des coordonnées, les croisements et les doublons de tracé.

**Pièges payés ailleurs.**
- `test_seigneuries.py::test_pure` interdit le mot `seigneur` sur toute ligne de `engine.py`, `world.py` et `model.py`, commentaires compris.
- `test_no_hardcoded.py` refuse tout littéral numérique hors {0, 1, −1} dans `sim/`.
- `TraceRoute` ne vit jamais dans `sim/model.py`, que `test_write_coverage.py` inspecte.
- Ne pas importer `sim.intentions` dans `engine.py` : `seigneuries` importe `engine`.

### Ce que le codeur écrit
1. **`jeu/sim/intentions.py`** : `TYPE_TRACER_ROUTE`, `TraceRoute` (avec `appliquer`), `ChoixDepart.appliquer`, le dépôt d'une route et `recevoir_intention`. `deposer_intention` ne change pas de comportement.
2. **`jeu/sim/plan.py`** : le champ `en_chantier` de `Rue` et sa vérification.
3. **`jeu/sim/engine.py`** : `_appliquer_intentions` appelle `.appliquer`, et la ligne 2 de la docstring « Ordre du tick » dit « intentions en attente, dans l'ordre du dépôt ».
4. **`jeu/sim/service.py`** : le branchement unique de `/intention` et la forme du reçu refusé.
5. **`jeu/sim/__main__.py`** : `--gestes`, `--monde-json`, le paramètre `gestes` de `_simulate`, et deux lignes dans la docstring du module.
6. **`jeu/sim/MODELE.md`** :
   - « En une page », étape 2 : « les intentions en attente s'appliquent dans l'ordre du dépôt : un choix de départ devient la maison du joueur, une route entre au plan en chantier ; sans cellule ni aléa » ;
   - « Les intentions du joueur » : la liste fermée, `recevoir_intention`, la route, le reçu, `--gestes`. La lacune déclarée est remplacée par la règle ;
   - « Le plan du bourg » : `en_chantier` ; « le tick ne le lit pas » devient « aucune règle du tick ne le lit ; seule l'étape Intentions y ajoute une rue en chantier ».
7. **`jeu/sim/README.md`** :
   - la phrase sur `POST /intention` nomme `tracer_route`, le reçu refusé et la fin de « les autres objets restent acceptés » ;
   - la table des modules dit « choix de départ et tracés de route » pour `sim/intentions.py` ;
   - une ligne d'exemple pour `python3 -m sim --gestes`.
8. Les tests ci-dessous : en ajouts, plus les deux lignes « essai » de la décision A.

## Périmètre
jeu/sim/intentions.py
jeu/sim/plan.py
jeu/sim/engine.py
jeu/sim/service.py
jeu/sim/__main__.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_determinisme.py
docs/briefs/254-une-intention-deposee-s-applique-au-tick-suivant.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`. Aucune `cell_id` n'est écrite en dur : on prend `min(monde.plans)`. Chaque test imprime ses compteurs, et un échantillon vide échoue. Chaque contre-épreuve est prouvée rouge avant d'être gardée. Une route valide de référence : `{"type": "tracer_route", "cell": X, "points": [[0, 0], [40, 0], [40, 25]], "largeur_m": 4}`.

**SC1 — une intention inconnue ou mal formée est refusée et ne change rien.** `python3 -m pytest sim/tests/test_intentions.py -q -s -k refus`
- Un test paramétré sur `World.charger(0)` passe ces cas par `recevoir_intention` :
  - sans `type`, `type` `"essai"` ;
  - `cell` absente, `True`, `"abc"`, max + 1 ;
  - un seul point, un point `[0]`, un point NaN, un point `["a", 0]` ;
  - `largeur_m` 0, −1, infinie, `"4"` ;
  - une clé en trop.
- Chaque cas lève `IntentionRefusee`, et son message contient le mot attendu (`type`, `cell`, `route invalide`, `champ`). Après chaque refus, `intentions_en_attente == []` et `to_dict()` est inchangé (`refus_observés == len(cas) > 0`).
- `Rue(0, [(0, 0), (1, 0)], 1, en_chantier=1)` lève `PlanInvalide`.
- Contre-épreuve : la route de référence est acceptée et rend un `TraceRoute`. Modifier ensuite la liste `points` de l'appelant ne change pas `TraceRoute.points`.

**SC2 — le tick suivant applique, en tête et dans l'ordre ; rien ne bouge avant.** `python3 -m pytest sim/tests/test_intentions.py -q -s -k route_appliquee`
- On dépose deux routes A puis B sur la même cellule X. Avant le tick, `to_dict()` est inchangé.
- Un tick dont le numéro est faux lève `ValueError` et laisse les deux en attente.
- Après `tick(monde, random.Random(0), 0)` :
  - `monde.plans[X].rues` vaut A (identifiant 0) puis B (identifiant 1), avec leurs points, leurs largeurs et `en_chantier is True` ;
  - la liste d'attente est vide ;
  - les autres plans sont vides.
- Un monde dont le plan X porte déjà le plan de `_donnees_plan()` (rue 7) donne l'identifiant 8 à la route suivante.
- Un choix de départ et une route déposés ensemble s'appliquent tous les deux au même tick.
- Contre-épreuve « un moteur qui ignore l'intention » : avec `monkeypatch` sur `engine._appliquer_intentions` en fonction vide, l'assertion « la rue est au plan après le tick » rougit (`pytest.raises(AssertionError)`).
- `python3 -m pytest sim/tests/test_monde.py sim/tests/test_determinisme.py -q -k "ordre_du_tick or plan_absent"` reste vert.

**SC3 — même graine et mêmes gestes, même monde ; sans geste, rien ne bouge.** `python3 -m pytest sim/tests/test_determinisme.py -q -s -k gestes`
- Deux `World.charger(0)` reçoivent les mêmes gestes : une route au tick 0 et une autre au tick 3. Ils jouent 10 ticks avec `random.Random(0)`. Leurs `to_dict()`, leurs empreintes SHA-256 et leurs `rng.getstate()` sont égaux.
- Un troisième monde, sans geste, joue les mêmes ticks. Ses `to_dict()["cells"]` et son état d'aléa égalent ceux des deux premiers : la route ne touche aucune cellule. Ses clés sont exactement `{"cells", "plans", "ticks_ecoules"}`, et tous ses plans sont vides.
- Contre-épreuves :
  - la même partie avec un point déplacé d'un mètre donne une autre empreinte ;
  - une cellule modifiée d'un habitant fait échouer la comparaison des cellules.

**SC4 — le service rend un reçu, et le tick suivant trace.** `python3 -m pytest sim/tests/test_intentions.py -q -s -k service_route`. Le test passe par `lancer_service(0)` et `requete_service`.
- La route de référence sur X rend 200 `{"acceptee": true, "appliquee_au_tick": 0}`. Les octets de `/monde` et de `/plan?cell=X` sont inchangés.
- Après `POST /tick?n=1`, `/plan?cell=X` porte une rue d'identifiant 0 avec `en_chantier: true`, et `/monde` reste égal à celui d'un service de même graine sans geste au même tick.
- Refus, sans bouger les octets de `/monde` ni de `/plan?cell=X` :
  - `{"route": "essai"}` rend 400 `{"acceptee": false, "erreur": …"type"…}` ;
  - une `cell` inconnue rend 400 ;
  - une largeur nulle rend 400.
- Contre-épreuve : deux services de graine 0 qui reçoivent les mêmes gestes rendent les mêmes octets de `/plan?cell=X` après le tick, et ceux d'un service sans geste diffèrent.

**SC5 — une liste de gestes se rejoue en ligne de commande.** `python3 -m pytest sim/tests/test_intentions.py -q -s -k ligne_de_commande`. Le test lance `[sys.executable, "-m", "sim", ...]` dans un dossier temporaire.
- `--ticks 4 --seed 0 --gestes g.json --monde-json m1.json`, lancé deux fois, rend 0 et des `m1.json` identiques à l'octet. Leur plan X porte les deux rues du fichier, en chantier.
- Sans `--gestes`, le `--monde-json` a tous ses plans vides et les mêmes `cells` qu'avec gestes.
- Refus en code 2, la raison sur stderr, sans fichier `--monde-json` écrit :
  - un `type` inconnu ;
  - un `tick` égal à `--ticks` ;
  - des `tick` qui décroissent ;
  - un fichier qui n'est pas une liste.
- Contre-épreuve : un fichier qui diffère d'un point donne un `m1.json` différent.
- `python3 -m pytest sim/tests/test_monde.py -q -k "cli or date_cli or module_cli"` reste vert.

**SC6 — rien d'existant ne bouge, sauf l'envoi « essai » décidé en A.** `python3 -m pytest jeu -q` depuis la racine. La suite reste verte, en particulier :
- `test_pure` ;
- `test_write_coverage.py` ;
- `test_no_hardcoded.py` ;
- `test_plan_absent_de_l_arbre_du_moteur` ;
- `test_plan_vide_par_cellule_et_empreinte_sensible` ;
- `test_service_refuse_de_deviner_sans_avancer_le_monde` ;
- `test_ordre_du_tick_documente_est_celui_du_code` ;
- `forge/tests/test_forge.py -k depart`.

Le diff des tests :
- `git diff origin/master -- jeu/sim/tests jeu/forge/tests | grep -E '^-[^-]'` rend **exactement deux lignes**, et toutes deux contiennent `"route": "essai"`.
- Dans `test_service_monde_est_leger_et_intention_ne_mute_rien`, l'intention devient la route de référence sur la plus petite `cell_id`. Les deux lignes suivantes (le reçu `{"acceptee": True, "appliquee_au_tick": 2}` et `/monde` inchangé) restent telles quelles. On ajoute ensuite :
  - `/plan` inchangé avant le tick ;
  - `{"route": "essai"}` refusé 400, `acceptee` faux, et `/monde` inchangé.
- Dans `test_service_refus_et_choix`, l'envoi « essai » attend `HTTPStatus.BAD_REQUEST`. La ligne suivante, `/monde` inchangé, reste telle quelle.

Contre-épreuves :
- le diff qui toucherait une troisième ligne existante sortirait dans ce `grep` ;
- `grep -c "Lacune déclarée :\*\* tout autre objet" sim/MODELE.md` rend 0 après le lot, et 1 sur la base.

## Hors périmètre
- Le travail que coûte une route : bras pris aux champs, durée du chantier, achèvement, effet de la route sur le commerce ou la distribution intérieure. Une rue en chantier ne fait rien au monde.
- Découper une parcelle et poser un atelier : ce sont les gestes suivants de J4.
- Réserver la route à la capitale du joueur ou à ses terres, et savoir qui dépose une intention : c'est la notion d'auteur, au jalon 5 avec l'IA.
- Retirer ou modifier une route ; détecter les croisements, les doublons ou un tracé hors du bourg ; borner les coordonnées.
- Unity : tracer au clic, lire `/plan` et redessiner la route (lots `pc`) ; le profil en relief de #263.
- Les vues, la photographie `--snapshot-json`, `python3 -m forge` et son `--depart` (inchangés), la sauvegarde d'une partie et la relecture d'un monde depuis `to_dict()`.
- `jeu/ville/`, `jeu/vues/`, `jeu/forge/`, `3d/`, et tout test existant hors des deux lignes « essai ».
