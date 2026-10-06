# Lot #361 — La ville redessine ses rues au lancement d'après le plan
Jalon : J4 · Machine : pc · Taille prévue : 260 lignes

## But
À l'ouverture de la scène de ville, Unity lit le plan de sa cellule (`GET /plan?cell=<cell_id>`) et pose toutes ses rues dans l'ordre du plan, en terre battue, sur le terrain vierge. Une rue que le relief refuse est déclarée à l'écran par son identifiant, jamais sautée. Unity relancé redessine donc la même ville, à l'octet, et une ville que seul Unity connaîtrait n'existe pas (CAP.md, jalon 4, « sa preuve »).

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que la vue respecte, de `jeu/sim/MODELE.md`, section « Le plan du bourg » : le plan de chaque cellule vit dans `World.plans`. Un monde neuf a un plan vide par cellule. Les rues sont triées par `identifiant`. Les points sont relus tels quels, dans le repère que #293 a fixé (`DesertRoads.Poser` reçoit `x`, `y` du plan sans conversion). Le monde accepte toute route d'au moins 2 points et de largeur positive (`sim/intentions.py`) : il ne connaît pas le relief. Une rue du plan peut donc être refusée par le relief d'Unity. Elle reste au plan : la vue la déclare, elle ne la corrige pas.

Ce qui existe sur master (dd7c65e), vérifié le 06/10/2026 :

- `DesertRoadTool.cs` (#263, #293) : `Valider` essaie la route (`Poser(essai:true)`), relève les identifiants du plan (`connues`), dépose `tracer_route`. `Attendre` dessine, après le tick, les rues absentes de `connues`. Rien ne dessine au lancement : relancé, Unity montre le sable vierge, quel que soit le plan.
- `DesertRoads.cs` travaille sur une copie du `TerrainData` (`Preparer`). L'asset n'est jamais écrit : Unity ne garde rien d'une session à l'autre. Ce lot ne change pas ce fichier.
- `DesertCityRoads.cs` (contrôle de #263/#293) mesure `asset_avant` sur `terrain.terrainData` deux images après le chargement. `routes.py` exige `asset_avant == asset_apres` (ligne 843). Si l'outil ouvre la ville dès son `Start`, le terrain porte la copie à ce moment-là, et ce contrôle rougit. Ce lot ajoute donc une ligne de mise en place, détaillée au Périmètre. Elle ne change ni une mesure, ni un seuil, ni le juge.
- Le jeu (`pc/jouer.py`) lance le service avant Unity et vérifie `/lieu` : à l'ouverture, le plan est lisible. Un service neuf sert, pour la cellule 1175 (cellule par défaut), un plan sans rue. L'IA ne trace que dans les capitales de ses maisons.

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : le service, `/plan` et `tracer_route` sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRoads.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRelance.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRelance.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot361.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot361.cs.meta
3d/local3d/atelier_desert.py

Précisions :

- **`DesertRoadTool.cs`**
  - **Membres publics neufs.**
    - `public readonly List<(long identifiant,DesertRoads.Resultat resultat)> Ouverture` : chaque rue essayée à l'ouverture, dans l'ordre du plan, acceptée ou refusée.
    - `public long TickOuverture` : vaut -1 tant qu'aucun plan n'a été lu à l'ouverture.
  - **Un ensemble privé `essayees`** des identifiants déjà essayés dans la session, posés ou refusés. Il remplace `connues`. Une seule méthode privée, `Dessiner(PlanLu)`, pose dans l'ordre du plan chaque rue absente d'`essayees` : `Poser` en terre battue, à `rue.LargeurM`, aux points du plan. Elle ajoute l'identifiant à `essayees` et rend la liste de ce qu'elle a essayé. `Attendre` et `Ouvrir` passent toutes deux par elle. Une rue n'est jamais posée deux fois, ni réessayée. `Valider` ne relève plus les identifiants du plan avant le dépôt : il lit encore le plan pour déclarer son absence, comme aujourd'hui.
  - **`public bool Ouvrir()`**, appelée par un `Start()` neuf, qu'`automatique` soit vrai ou faux. Dans l'ordre :
    1. Elle vide `Ouverture` et `essayees`, et met `TickOuverture` à -1.
    2. Si la cellule est en erreur, ou si le plan est absent, elle l'affiche et rend faux. Le terrain ne change pas.
    3. Elle lit les paramètres par `DesertRoads.Lire(roads.implantation)`. S'ils manquent, elle affiche le message de l'exception et rend faux.
    4. Sinon, elle prépare une copie vierge (`roads.Preparer(parametres, graine)`), même si le plan n'a aucune rue. Elle dessine toutes les rues par `Dessiner`, remplit `Ouverture`, met `TickOuverture` au tick du plan, et rend vrai.

    Elle ne touche pas à un dépôt en attente. Pas de nouvel essai périodique.
  - **Le panneau déclare.** Après `Ouvrir` comme après `Attendre`, le message porte une ligne de tête : `Plan du tick T : N rue(s) posée(s).` ou `Après le tick T : N rue(s) neuve(s) posée(s).`. Il porte aussi une ligne par rue refusée : `Rue <identifiant> refusée par le relief : <resultat.message>`.
  - **`Intention(DesertRoads.Geste)` devient publique.** Le contrôle et la capture forment leurs dépôts avec elle. Son texte ne change pas.
  - **Aucune écriture hors de la copie** : ni `AssetDatabase`, ni fichier, ni `PlayerPrefs`. Unity ne garde aucun plan à lui.
- **`DesertCityRoads.cs`** : une seule ligne ajoutée, `roads.Restaurer();`, juste avant `report.asset_avant=…` dans `Run`, avec le commentaire « Lot 361 : l'outil a ouvert la ville d'après le plan ; le contrôle part de l'asset ». Aucune autre ligne ne change.
- **`DesertCityRelance.cs`** (neuf) : le contrôle du relancement, sur le modèle de `DesertCityRoads` : `[InitializeOnLoad]`, un drapeau `SessionState`, `EditorApplication.update`, deux images d'attente, puis `CitadelEditorBridge.Finish(code)`. Pas de changement de pipeline : il ne capture aucune image.
  - **Ses trois points d'entrée :** `Tracer`, `Relancer` et `Vierge`. Chacun ouvre la scène `Forge_Desert_Ville_<id>` de la première implantation de `sorties/ville/selection.json`, puis entre en Play. Il écrit `sorties/ville/<id>/relance/<session>.json`, où `<session>` vaut `tracer`, `relance` ou `vierge`. Le code de sortie vaut 0 sans défaut, 1 sinon. `Relancer` et `Vierge` jouent le même code : seuls le nom du fichier et la référence attendue diffèrent.
  - **Le rapport (`JsonUtility`)** porte :
    - `session`, `implantation`, `cell`, `port`, `tick_ouverture` ;
    - `ouverture` : `identifiant`, `acceptee`, `motif`, `message` de chaque essai ;
    - `traces`, sur le même modèle ;
    - `plan` : les identifiants des rues du plan, relus par un `ClientPlan` après l'ouverture ;
    - `panneau` (`tool.Message`) ;
    - `empreinte` : `roads.Empreintes().Tout`, relevée en fin de session ;
    - `vierge` : relevée ensuite, sur un `roads.Preparer(parametres, graine)` frais ;
    - `defauts`.
  - **`Tracer`** (service neuf). L'outil passe en `automatique`. Pour la première route de la famille `plaine`, puis pour la première de la famille `flanc`, du jeu de gestes (`DesertRoads.Lire`) :
    1. les points sont cliqués à l'écran par `tool.Clic`, la caméra posée au-dessus et rendue dans une RenderTexture 1600×900, comme le clic de `DesertCityRoads` ;
    2. `tool.Valider()` ;
    3. un vrai tick (`POST /tick?n=1`, hors du fil de l'éditeur par `Task.Run`, comme `Lot293.AuTick`) ;
    4. `tool.Attendre()` doit rendre vrai, et chaque entrée de `tool.Posees` s'ajoute à `traces`.

    Ensuite, la première route `raide_long` est déposée **directement** par `ClientIntention.Deposer(tool.Intention(g))`, sans passer par l'essai du relief, suivie d'un tick. Le reçu doit être accepté. L'outil ne l'attend pas.
  - **Défauts de `Tracer`** :
    - `tick_ouverture < 0` ;
    - `ouverture` non vide (le service n'est pas neuf) ;
    - une route non cliquée, refusée à l'essai ou non acceptée par le monde ;
    - `traces` qui n'est pas exactement 2 essais acceptés d'identifiants distincts ;
    - `plan` qui n'a pas exactement 3 rues ;
    - `empreinte == vierge`.
  - **Défauts de `Relancer`.** La session lit `tracer.json` et signale :
    - le rapport `tracer.json` absent ;
    - `tick_ouverture < 0` ;
    - les identifiants d'`ouverture` différents de `plan`, dans l'ordre (une rue sautée ou essayée deux fois rougit) ;
    - les identifiants acceptés d'`ouverture` différents de ceux de `tracer.traces`, dans le même ordre ;
    - un nombre de rues refusées différent de 1 ;
    - la rue refusée qui n'est pas celle du plan absente de `tracer.traces`, ou dont le `motif` est vide ;
    - un `panneau` qui ne contient pas `Rue <identifiant> refusée par le relief` ;
    - `empreinte != tracer.empreinte`, ou `vierge != tracer.vierge`.
  - **Défauts de `Vierge`.** La session lit aussi `tracer.json` et signale :
    - `tick_ouverture < 0` (une ville vierge parce que le plan n'a pas été lu ne prouve rien) ;
    - `plan` non vide ;
    - `ouverture` non vide ;
    - `empreinte != vierge`, avec un défaut qui contient « la ville n'est pas revenue vierge » ;
    - `vierge != tracer.vierge`.
- **`atelier_desert.py`** : une action `relance` et une option `--sans-service-neuf`. Les trois méthodes entrent dans `ACTIONS` et dans `LOGS` (`relance_tracer.log`, `relance.log`, `relance_vierge.log`). L'action fait, dans l'ordre :
  1. `ecrire_gestes` pour la première implantation de la sélection (`--disposition` pour en choisir une), puis écrit `selection.json` à elle seule ;
  2. efface les trois rapports ;
  3. refuse si Unity est ouvert, comme `routes` ;
  4. `lancer_service()`, puis `Tracer`, puis `Relancer`, puis `arreter_service` ;
  5. un `lancer_service()` neuf, puis `Vierge`, puis `arreter_service`. Avec `--sans-service-neuf`, `Vierge` joue sur le premier service, avant son arrêt.

  Elle imprime une ligne par session (essais de l'ouverture, traces, défauts). Elle lève si un rapport manque ou porte un défaut. `routes`, `lancer_service` et `arreter_service` ne changent pas.
- **`Lot361.cs`** : le scénario de la Photo.
- **Les deux `.meta`** sont ceux qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` (commande de SC1 du lot #360) rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. `python3 -m pytest jeu -q` reste vert (`py -m pytest jeu -q` sur le PC).

**SC2 — Unity relancé redessine la même ville, à l'octet (PC).**
Depuis `3d/` : `py local3d/atelier_desert.py relance`. Le code de sortie vaut 0, et les trois rapports existent sans défaut. Valeurs exigées, contrôlées par Unity et relues dans les rapports pour la PR :
- `tracer.json` :
  - `ouverture` vide et `tick_ouverture ≥ 0` ;
  - `traces` = 2 essais acceptés, plaine puis flanc ;
  - `plan` = 3 identifiants ;
  - `empreinte != vierge`.
- `relance.json` :
  - `ouverture` = les 3 identifiants de `plan`, dans l'ordre : 2 acceptés (ceux de `tracer.traces`), 1 refusé (la route raide, `motif` non vide) ;
  - `panneau` nomme `Rue <id> refusée par le relief` ;
  - `empreinte` **égale** à celle de `tracer.json`, hauteurs, couches et touffes.
- `vierge.json` :
  - `tick_ouverture ≥ 0`, `plan` vide, `ouverture` vide ;
  - `empreinte == vierge == tracer.vierge`.

La PR cite les trois empreintes et les lignes imprimées.

**SC3 — contre-épreuve : une ville que seul Unity connaîtrait rougit (PC).**
`py local3d/atelier_desert.py relance --sans-service-neuf` rend un code non nul. `vierge.json` porte un défaut qui contient « la ville n'est pas revenue vierge », et `plan` y compte 3 rues. La PR montre la sortie.
Contre-épreuves faites à la main et dites dans la PR, chacune retirée ensuite :
- (a) `Ouvrir` rend vrai sans appeler `Dessiner` : `relance` rougit (empreinte, et ouverture ≠ plan) ;
- (b) `Dessiner` ignore `essayees` : `tracer` rougit, avec 3 traces dont une rue posée deux fois ;
- (c) une rue refusée n'entre pas dans `Ouverture` : `relance` rougit (ouverture ≠ plan).

**SC4 — le contrôle des routes de #263/#293 reste vert (PC).**
`py local3d/atelier_desert.py routes` rend 0, sans défaut, pour chaque implantation de la sélection. `py local3d/atelier_desert.py routes --service-sourd` échoue toujours sur la faute du service sourd. Sans la ligne `roads.Restaurer();`, `routes` rougit sur « l'asset du terrain a changé » : à dire dans la PR.

**SC5 — la photo se prend (PC).**
La capture du lot (`-forgeLot 361`) se termine sans exception du scénario et écrit `<scène>--ouverture.png`.

**SC6 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff origin/master...HEAD -- 3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRoads.cs | grep '^[-+][^-+]'
```
La première commande ne nomme que les fichiers du Périmètre et ce brief. La seconde ne sort que la ligne `roads.Restaurer();` et son commentaire, sans aucune ligne retirée. `3d/local3d/desert/routes.py`, `DesertRoads.cs`, `Lot293.cs` et `jeu/` sont hors du diff.

## Hors périmètre
- Dessiner les parcelles et les bâtiments du plan : sous-lots 3 et 4 de #261.
- Les pavés, ou un revêtement lu au plan : toute rue se pose en terre battue.
- Réessayer une rue refusée, la corriger, ou la retirer du plan. Relire le plan si le service manque à l'ouverture.
- Changer ce que le monde accepte d'une route : le relief reste une affaire de vue.
- Toucher `routes.py`, son juge, `DesertRoads.cs`, `ClientPlan.cs`, `ClientIntention.cs`, `Lot293.cs`, les scènes, les asmdef, ou `jeu/`.
- Toucher `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md` ou `CAP.md`.

## Photo
La capitale ouverte d'après le plan : une rue de terre battue dessinée sur le sable, et le panneau qui nomme la rue raide refusée. Le plan fixe de la capture, pris avant, montre le sable vierge.

Le scénario `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot361.cs`, `[ScenarioDeCapture(361, "ouverture")]`, au Périmètre, joue la capture avec son service sur le port 8000 :
1. Il trouve `DesertRoadTool` et `DesertCityCamera` (exception sinon), puis met l'outil en `automatique`.
2. Il dépose au service, hors du fil de l'éditeur (`Task.Run`), la première route `plaine` et la première `raide_long` du jeu de gestes, par `ClientIntention.Deposer(outil.Intention(g))`. Les deux reçus doivent être acceptés. Puis il fait passer un tick (`POST /tick?n=1`, statut 200).
3. Il appelle `outil.Ouvrir()`, le code même que le `Start` de la scène joue au lancement. Il exige :
   - vrai ;
   - dans `Ouverture`, la rue de plaine acceptée et la rue raide refusée ;
   - `outil.Message` qui contient `Rue <identifiant de la raide> refusée par le relief`.
4. Il pose la caméra par `ville.Poser(milieu de la plaine, ville.Cap, 60, 90)`, comme `Lot293`, et laisse passer 10 images.

Une exception fait échouer la capture.
