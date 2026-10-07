# Lot #370 — Unity relancé repose les mêmes bâtiments
Jalon : J4 · Machine : pc · Taille prévue : 230 lignes

## But
Une commande prouve que les bâtiments de la capitale vivent dans le monde, pas dans Unity. Elle pose une maison, une scierie et un four sur un service neuf et voit la maison passer par piquets, murs puis fini. Relancé sur le même service, Unity repose les mêmes pièces aux mêmes places. Sur un service neuf, il n'en pose aucune (CAP.md, jalon 4 : « Le plan de la ville vit dans le monde : Unity relancé redessine la même ville d'après le service » ; contre-épreuve : « une ville que seul Unity connaît »).

## Règle du monde
Sans objet : c'est un lot d'outil, un contrôle. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que le contrôle lit de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Le plan du bourg ».** Un bâtiment a une `nature`, une `emprise`, `travail_fourni`, `travail_requis`, et `en_chantier == (travail_fourni < travail_requis)`. Les bâtiments sont servis triés par identifiant.
- **« Le chantier et ses bras ».** 2 journées par m² d'emprise, soit 300 pour 10 m × 15 m. Chaque foyer envoie 5 bras par tick.
- **L'étape montrée** est la convention de la vue de #368 (`LectureDuBatiment.Etape`). Un bâtiment achevé est `fini`. Un bâtiment en chantier est aux `piquets` tant que `2 × fourni < requis`, puis aux `murs`.

Ce qui existe sur master (37fc81b), vérifié le 07/10/2026 :

- `Editor/DesertCityRelance.cs` (#361, #362) : le modèle à suivre. Il a trois sessions (`Tracer`, `Relancer`, `Vierge`), chacune un lancement d'Unity en batch sur la première implantation de `selection.json`. Il passe la session par `SessionState`, s'accroche à `EditorApplication.update` par `[InitializeOnLoad]` et attend deux images. Il écrit un rapport JSON et sort par `CitadelEditorBridge.Finish(0|1)`. `JugerTracer` et `JugerRelance` exigent exactement deux parcelles : on n'y ajoute rien.
- `atelier_desert.py relance` (#361) lance le service (`lancer_service`), joue `tracer` puis `relance` sur ce service, puis `vierge` sur un service neuf. Avec `--sans-service-neuf`, `vierge` joue sur le premier service.
- `DesertRoadTool` (#369) : `Ouvrir()` est le code même du `Start`. Il repart d'une copie vierge du terrain et redessine rues, parcelles et bâtiments d'après `/plan`. `Batiments` donne `(identifiant, etat, message)`, avec `etat` parmi `piquets`, `murs`, `fini` ou `refusee`. Il expose aussi `RacineBatiments` (enfants nommés `Bâtiment <id>`) et `EmpreinteBatiments` (SHA-256 de la description du dernier dessin, `SHA-256("")` pour un plan sans bâtiment). `Rafraichir()` ne redessine pas les rues : il ne sert pas ici.
- `Editor/Captures/Lot362.cs` : les aides `internal static` `Deposer`, `Tick`, `Lire` et `Identifiant` (hors du fil de l'éditeur ; elles lèvent en cas d'échec). Elles sont dans le même assembly que l'éditeur.
- `Pont/KitDesBatiments.cs` : `KitDesBatiments.Charger()`, puis `Piece(nature, etape).Prefab`.
- **La recette, rejouée le 07/10/2026 sur un service neuf** (`python3 -m sim.service --jours-par-seconde 0`, graine par défaut, cellule 1175) :
  - Au tick 0, le plan est vide : 0 rue, 0 parcelle, 0 bâtiment.
  - La route `plaine_neuve` de `ksar_des_sept_puits` (la première route `plaine` de `gestes.json`, 11 points) est déposée, puis un tick. Elle devient la rue 0.
  - Trois `decouper_parcelle` sur la rue 0, à gauche : segments 4, 6 et 8, `debut_m` 0, `facade_m` 10, `profondeur_m` 15, `foyers` 100. Deux ticks : les parcelles 0, 1 et 2 sont à 15/15.
  - Trois `poser_batiment` : `maison` à 24 foyers sur la parcelle 0, `scierie` à 12 sur la 1, `four` à 1 sur la 2. Ils sont appliqués au tick suivant.
  - Puis un tick à la fois :

    | tick du plan | maison | scierie | four |
    |---|---|---|---|
    | 4 | 120/300 piquets | 60/300 piquets | 5/300 piquets |
    | 5 | 240/300 murs | 120/300 piquets | 10/300 piquets |
    | 6 | 300/300 fini | 180/300 murs | 15/300 piquets |

  La maison passe donc par piquets, murs puis fini, et au tick 6 les trois étapes sont là ensemble. Le centre de la maison est (−36,18 ; 127,40), comme dans la capture de #369.

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, les trois gestes, l'étape Chantiers, #361, #362, #368 et #369 sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityBatiments.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityBatiments.cs.meta
3d/local3d/atelier_desert.py

Précisions :

- **`DesertCityBatiments.cs`** (neuf, namespace `ForgeLocal3D`, `[InitializeOnLoad] public static class DesertCityBatiments`). C'est la mécanique de `DesertCityRelance`, recopiée et non partagée (on ne touche pas `DesertCityRelance.cs`). Ses clés `SessionState` sont à elle : `Forge.Desert.Batiments`, `Forge.Desert.Batiments.Session` et `Forge.Desert.Batiments.Implantation`. Sinon, les deux contrôles se déclencheraient l'un l'autre.
  - **Trois entrées** : `Poser()`, `Relancer()`, `Vierge()`, sessions `poser`, `relance` et `vierge`. Même scène, même attente de deux images, même sortie par `CitadelEditorBridge.Finish` que `DesertCityRelance`.
  - **Le rapport** est écrit dans `DesertRoads.Sorties + <implantation> + "/batiments/<session>.json"`, au format `JsonUtility`, même quand un défaut est trouvé. Une exception levée pendant la session (une aide de `Lot362`, par exemple) devient le défaut `exception : <message>`, et le rapport est quand même écrit.
    - `Batiment` : `identifiant`, `nature`, `fourni`, `requis`, `en_chantier`, `attendue`, `dessinee`, `message`, `maillages`.
    - `Releve` : `tick` (le tick du plan), `batiments` (`Batiment[]`), `pieces` (`RacineBatiments.childCount`, `-1` sans racine), `empreinte` (`EmpreinteBatiments`).
    - `Rapport` : `session`, `implantation`, `cell`, `port`, `tick_ouverture`, `ouverture` (le relevé de la ville telle que le `Start` l'a dessinée), `ticks` (`Releve[]`), `sequence_maison` (`string[]`), `defauts` (`string[]`).
  - **Un relevé** se fait juste après un `Ouvrir()` (ou après le `Start` pour `ouverture`). On lit le plan (`Lot362.Lire`), puis pour chaque bâtiment du plan, dans l'ordre :
    - `attendue` est **calculée ici, à partir des nombres du plan** : `fini` si le bâtiment n'est pas en chantier, `piquets` si `2 × fourni < requis`, `murs` sinon. Le contrôle n'appelle **ni** `LectureDuBatiment.Etape` **ni** `DesertBatiments` : une étape mal lue par la vue doit se voir.
    - `dessinee` est l'`etat` de l'entrée de même identifiant dans `outil.Batiments`, ou `absente` s'il n'y en a pas. `message` est celui de l'entrée.
    - `maillages` est vrai si l'enfant `Bâtiment <id>` existe sous `RacineBatiments` et que ses maillages (`sharedMesh` de tous ses `MeshFilter`, tous LOD compris, dans l'ordre de la hiérarchie) sont ceux du prefab `kit.Piece(nature, attendue).Prefab`. C'est le test de `Lot369.Maillages`, réécrit ici en deux lignes. Si cette pièce manque au kit, `maillages` est faux.
  - **Session `poser`** (service neuf), dans cet ordre :
    1. `outil.automatique = true`. Le relevé `ouverture` est pris.
    2. La première route `famille == "plaine"` de `DesertRoads.Lire(implantation)` est déposée par `Lot362.Deposer(port, outil.Intention(g))`, puis `Lot362.Tick`. La rue est retrouvée par `Lot362.Identifiant`.
    3. Les trois découpes de la recette, puis deux ticks. Les trois parcelles doivent être achevées : sinon c'est un défaut, et la session s'arrête là.
    4. Les trois poses de la recette (maison 24, scierie 12, four 1, sur les parcelles découpées, dans l'ordre).
    5. **Trois fois** : `Lot362.Tick`, puis `outil.Ouvrir()` (s'il rend faux, c'est un défaut), puis un relevé ajouté à `ticks`.
    6. `sequence_maison` : la `dessinee` du bâtiment `maison` de chaque relevé de `ticks`, en fusionnant les répétitions qui se suivent.
  - **Session `relance`** (même service) : aucun dépôt, aucun tick. Le relevé `ouverture` seul.
  - **Session `vierge`** (service neuf) : le relevé `ouverture` seul.
  - **Le jugement**, dans Unity, comme `DesertCityRelance`. Un défaut est une phrase qui nomme le bâtiment, son tick et ce qui manque.
    - `poser` :
      - à l'`ouverture`, aucun bâtiment au plan et 0 pièce : sinon le service n'est pas neuf ;
      - `ticks` compte 3 relevés ;
      - dans chacun, 3 bâtiments au plan. Pour chacun, `dessinee == attendue` et `maillages` vrai. `pieces` est égal au nombre de bâtiments dont `dessinee` n'est ni `refusee` ni `absente`, et vaut 3 ;
      - `sequence_maison` vaut exactement `piquets, murs, fini` ;
      - au dernier relevé, les `dessinee` de la maison, de la scierie et du four valent `fini`, `murs` et `piquets` : les trois étapes sont là ensemble ;
      - l'empreinte du dernier relevé n'est pas `SHA-256("")`.
    - `relance` : on lit le rapport `poser.json`. Son absence est un défaut. Puis on exige :
      - le `tick` de l'`ouverture` égal à celui du dernier relevé de `poser` ;
      - la même liste `(identifiant, nature, dessinee)`, dans le même ordre ;
      - pour chaque bâtiment, `dessinee == attendue` et `maillages` vrai ;
      - le même nombre de `pieces` ;
      - la **même empreinte** (`la ville relancée ne repose pas les mêmes pièces aux mêmes places : empreinte <a> pour <b>`).
    - `vierge` :
      - aucun bâtiment au plan ;
      - `outil.Batiments` vide ;
      - `pieces == 0` ;
      - une empreinte égale à `SHA-256("")`.
- **`atelier_desert.py`** :
  - On ajoute à `ACTIONS` les trois méthodes `ForgeLocal3D.DesertCityBatiments.Poser|Relancer|Vierge`, actions `desert_batiments_poser`, `desert_batiments_relance` et `desert_batiments_vierge`. On ajoute à `LOGS` `batiments_poser.log`, `batiments_relance.log` et `batiments_vierge.log`.
  - Une fonction neuve, `batiments(ds, service_neuf=True)`, calquée sur `relance` :
    1. Elle écrit les gestes et `selection.json` de `ds[0]` et efface les anciens rapports `batiments/*.json`.
    2. La garde « Unity est ouvert » passe **avant** tout effet sur Unity ou sur le service.
    3. Elle joue `poser` puis `relance` sur un service. Elle joue `vierge` sur un second service neuf, ou sur le premier avec `--sans-service-neuf`.
    4. Pour chaque session, elle imprime : le tick d'ouverture, une ligne par relevé (`tick N : <id> <nature> <fourni>/<requis> <dessinee>` pour chaque bâtiment, les pièces et l'empreinte), `sequence_maison` et chaque défaut.
    5. Elle lève comme `relance` : rapport manquant, défauts, puis échec d'Unity.
  - `relance` et ses lignes ne changent pas.
  - Dans l'argparse, `batiments` s'ajoute aux `choices`. L'aide de `--sans-service-neuf` nomme aussi `batiments`. Une ligne de dispatch s'ajoute : `if a.action=='batiments':batiments(ds,not a.sans_service_neuf)`.
- **Le `.meta`** est celui qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. `py -m pytest jeu -q` reste vert.

**SC2 — le contrôle passe (PC).**
Depuis `3d/`, `py local3d/atelier_desert.py batiments` rend 0. Ses trois rapports n'ont aucun défaut. La sortie montre :
- pour `poser`, les relevés des ticks 4, 5 et 6 avec les nombres du tableau de la Règle du monde, et la séquence `piquets, murs, fini` ;
- pour `relance`, l'empreinte du tick 6 de `poser` ;
- pour `vierge`, 0 bâtiment, 0 pièce et l'empreinte de `""`.

La PR colle cette sortie.

**SC3 — contre-épreuves (PC).** Chacune doit faire rendre une erreur à la commande. La PR donne la sortie et le défaut attendu ; on retire chaque changement fait à la main ensuite.
- (a) `py local3d/atelier_desert.py batiments --sans-service-neuf` échoue : `vierge` compte 3 bâtiments au plan et 3 pièces.
- (b) **Une étape lue sans la moitié.** Dans `LectureDuBatiment.Etape`, `Piquets` seulement si `TravailFourni == 0`, `Murs` sinon. `poser` échoue : au tick 4, la maison à 120/300 est dessinée `murs` au lieu de `piquets` (la scierie et le four aussi), et `sequence_maison` vaut `murs, fini`.
- (c) **Une pièce décalée à chaque lancement.** Dans `DesertBatiments.Dessiner`, le centre de chaque pièce reçoit `x += 0.03f` quand la ligne de commande d'Unity contient `DesertCityBatiments.Relancer`. `poser` passe, et `relance` échoue sur l'empreinte.
- (d) **Un redessin qui ne vide pas.** `Dessiner` ne vide pas la racine. `poser` échoue au tick 5 : 6 pièces sous la racine pour 3 posées.

**SC4 — les contrôles existants restent verts (PC).**
Depuis `3d/` :
- `py local3d/atelier_desert.py relance` rend 0, sans défaut ;
- `relance --sans-service-neuf` échoue toujours, sur les mêmes défauts qu'avant ;
- `py local3d/atelier_desert.py routes` rend 0 ;
- `routes --service-sourd` échoue toujours.

La PR montre les sorties.

**SC5 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff -U0 origin/master...HEAD -- 3d/local3d/atelier_desert.py | grep '^-[^-]'
```
La première ne nomme que les fichiers du Périmètre et ce brief. La seconde ne montre au plus que trois lignes : la fin de `ACTIONS`, la fin de `LOGS` et la ligne de l'argparse. Rien de la fonction `relance` n'y est. Restent hors du diff : `DesertCityRelance.cs`, `DesertBatiments.cs`, `DesertRoadTool.cs`, `DesertParcelles.cs`, tout `Pont/`, toutes les captures (`Lot362.cs` et `Lot369.cs` compris), les prefabs, les scènes et `jeu/`.

## Hors périmètre
- Toucher la vue (`DesertBatiments.cs`, `DesertRoadTool.cs`), le pont, le kit ou les prefabs. Si le contrôle trouve un défaut de la vue, le lot s'arrête et le dit dans sa PR.
- Changer `DesertCityRelance.cs` ou l'action `relance` : elle garde ses deux parcelles.
- Faire jouer ce contrôle par la CI (`.github/`), ou l'ajouter à la boîte aux lettres de l'éditeur ouvert (`CitadelEditorBridge`).
- Une capture ou une photo : celle de #369 montre déjà les trois étapes.
- Mettre à jour `3d/local3d/desert/README.md`, `VILLE.md` ou `docs/NOTICE.md`.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ajoute un contrôle en batch et rien de ce qu'on voit ne change. Aucune scène, aucun composant ni aucune pièce de la ville n'est modifié, et ses trois sessions ne capturent rien. Ce qu'il vérifie à l'écran (la maison finie, la scierie aux murs, le four aux piquets) est la photo du lot #369, `-forgeLot 369`.
