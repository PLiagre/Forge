# Lot #386 — Unity joue les gestes de la preuve et redessine la même ville
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Une commande joue dans Unity les trois gestes du joueur par son outil (une route, une parcelle, une scierie), fait passer les ticks et relève l'empreinte de la ville dessinée. Unity relancé sur le même service doit retrouver cette empreinte. Sur un service neuf, il ne dessine rien. Une rue que seul Unity connaît doit faire échouer la commande (CAP.md, jalon 4 : « Unity relancé redessine la même ville d'après le service » ; contre-épreuve : « une ville que seul Unity connaît »).

## Règle du monde
Sans objet : c'est un lot d'outil, un contrôle. Aucun nombre du monde n'est décidé ici, et `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

Ce que le contrôle lit de `jeu/sim/MODELE.md`, sans rien y changer :

- **« Les intentions du joueur »** : un geste est une intention déposée au service et appliquée au tick suivant.
- **« Le plan du bourg »** : rues, parcelles et bâtiments, triés par identifiant, avec `en_chantier == (travail_fourni < travail_requis)`.
- **« Le chantier et ses bras »** : route à 0,5 journée/m², parcelle à 0,1 journée/m², bâtiment à 2 journées/m² d'emprise.
- **L'étape dessinée.** Une parcelle en chantier est au `cordeau`, achevée aux `bornes` (#362). Un bâtiment achevé est `fini`. En chantier, il est aux `piquets` tant que `2 × fourni < requis`, puis aux `murs` (#370).

Ce qui existe sur master (e714cfe), vérifié le 07/10/2026 :

- **`Editor/DesertCityBatiments.cs` (#370) : le modèle à suivre.** Il a trois sessions, chacune un lancement d'Unity en batch sur la première implantation de `selection.json`. Il passe la session par `SessionState`, s'accroche à `EditorApplication.update` par `[InitializeOnLoad]` et attend deux images. Une exception levée pendant la session devient un défaut, et le rapport JSON est écrit quand même. Il sort par `CitadelEditorBridge.Finish(0|1)`.
- **`Editor/DesertCityRelance.cs` (#361, #362).** L'empreinte des rues est `roads.Empreintes().Tout`. Le sable vierge se mesure par `roads.Preparer(gestes.parametres, gestes.graine)`, puis `Empreintes().Tout`, puis `roads.Restaurer()`. Les clics de route se font sur une `RenderTexture` de 1600 × 900.
- **`DesertRoadTool`, l'outil du joueur (#293, #361, #362, #369, #375, #377).** Avec `automatique = true`, `Update` ne lit ni souris ni clavier. Chaque touche est alors l'appel que `Update` fait pour elle :
  - `Clic(écran)` pour le clic gauche ;
  - `Valider()` pour Entrée en mode route ;
  - `EntrerParcelle()` pour P, puis `ValiderParcelle()` pour Entrée en mode parcelle ;
  - `EntrerBatiment(PoseDeBatiment.Natures[1])` pour la touche 2 (scierie) ;
  - `Annuler()` pour Échap.

  `Attendre()` dessine ce qu'un tick a appliqué. `Rafraichir()` redessine parcelles et bâtiments d'après le plan, sans toucher aux rues. `Ouvrir()` est le code du `Start`.

  L'outil expose `Recu`, `Tracee`, `Pose`, `Posees`, `Ouverture`, `TickOuverture`, `Parcelles`, `Batiments`, `RacineParcelles`, `RacineBatiments`, `EmpreinteParcelles` et `EmpreinteBatiments`. Pour un dessin vide, ces deux empreintes valent `SHA-256("")`.
- **Les aides `internal static`**, dans le même assembly que l'éditeur :
  - `Captures/Lot375.cs` : `Point(rue, i, s, h)`, `Milieu(terrain, rue, i)`, et `Cliquer(camera, ville, outil, vise, points…)`, qui vise de haut et clique chaque point avec l'outil ;
  - `Captures/Lot362.cs` : `Tick`, `Lire`, `Monde`.

  En Play, la caméra est `outil.view`, et la `DesertCityCamera` s'y branche seule.
- **`atelier_desert.py`** : `lancer_service(sourd)` lance un service à vitesse 0 ; avec `sourd`, le monde ignore toute intention. On y trouve aussi `arreter_service`, `run_unity`, et `batiments(ds, service_neuf)`, le modèle de la fonction neuve.
- **La recette, rejouée le 07/10/2026 sur un service neuf** (`python3 -m sim.service --jours-par-seconde 0`, graine par défaut, cellule 1175). Les points et les mesures sont exacts ici ; ceux des clics sont arrondis au centimètre, donc un requis peut différer d'une journée.

  | plan du tick | ce qui vient d'entrer | rue 0 | parcelle 0 | bâtiment 0 |
  |---|---|---|---|---|
  | 0 | rien : 0 rue, 0 parcelle, 0 bâtiment | — | — | — |
  | 1 | la route `plaine` du jeu de gestes (11 points, 4 m) | 5/200 | — | — |
  | 2 | la parcelle : segment 5, à gauche, début 1 m, façade 8 m, profondeur 15 m | 10/200 | 5/12 cordeau | — |
  | 3 | la scierie sur la parcelle 0 | 15/200 | 10/12 cordeau | 0/240 piquets |
  | 10 | sept ticks plus tard | 50/200 | 12/12 bornes | 30/240 piquets |

Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer : `/plan`, les trois gestes, l'étape Chantiers, l'outil, ses modes, #361, #362, #369 et #370 sont sur master.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityPreuve.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityPreuve.cs.meta
3d/local3d/atelier_desert.py

Précisions :

- **`DesertCityPreuve.cs`** (neuf, namespace `ForgeLocal3D`, `[InitializeOnLoad] public static class DesertCityPreuve`). C'est la mécanique de `DesertCityBatiments`, recopiée et non partagée : on ne touche ni `DesertCityBatiments.cs` ni `DesertCityRelance.cs`. Ses clés `SessionState` sont à elle : `Forge.Desert.Preuve`, `Forge.Desert.Preuve.Session` et `Forge.Desert.Preuve.Implantation`.
  - **Trois entrées** : `Jouer()`, `Relancer()` et `Vierge()`, sessions `jouer`, `relance` et `vierge`.
  - **Le rapport** est écrit dans `DesertRoads.Sorties + <implantation> + "/preuve/<session>.json"`, au format `JsonUtility`, même quand un défaut est trouvé.
  - **La consigne** se lit dans `…/preuve/consigne.json` (`{"ville_locale": true|false}`). Si elle est absente, c'est un défaut.
  - **Les types du rapport :**
    - `Trace` : `identifiant`, `nature` (vide pour une parcelle), `etat`.
    - `Geste` : `type` (`tracer_route`, `decouper_parcelle` ou `poser_batiment`), `apres_le_tick` (le `AppliqueeAuTick` du reçu), `identifiant` (au plan, après le tick).
    - `Releve` :
      - `tick` (le tick du plan relu) ;
      - `rues` (les identifiants du plan) et `rues_posees` (les rues que l'outil a posées dans la session : `Posees` acceptées pour `jouer`, `Ouverture` acceptées sinon) ;
      - `parcelles` (`Trace[]` de `outil.Parcelles`), `parcelles_plan` (`cordeau` ou `bornes`, d'après `en_chantier`) ;
      - `batiments` (`Trace[]` de `outil.Batiments`, nature lue au plan), `batiments_plan` (étape calculée **ici** d'après les nombres du plan, comme `DesertCityBatiments.Relever`, sans appeler la vue) ;
      - `pieces_parcelles` et `pieces_batiments` (`childCount` des racines, `-1` sans racine) ;
      - `empreinte_rues`, `empreinte_parcelles`, `empreinte_batiments` et `empreinte`. Cette dernière est le SHA-256 des trois, joints par `\n`.
    - `Rapport` : `session`, `implantation`, `cell`, `port`, `tick_ouverture`, `ville_locale`, `gestes` (`Geste[]`), `ouverture` (le relevé de la ville telle que le `Start` l'a dessinée), `ville` (le relevé jugé), `vierge` (l'empreinte du sable vierge, prise après le relevé `ville`, puis `Restaurer`) et `defauts`.
  - **Session `jouer`** (service neuf). Chaque étape qui échoue ajoute un défaut qui la nomme, et la session s'arrête là. Les étapes :
    1. `outil.automatique = true`, puis le relevé `ouverture`.
    2. **La route.** La première route `famille == "plaine"` de `DesertRoads.Lire(implantation)`. La vue est posée de haut (`ville.Poser(milieu de la route, ville.Cap, 85, 160)`, sur une `RenderTexture` 1600 × 900, comme `Lot293.Depot`). Puis `outil.largeur = g.largeur`, `Annuler()`, un `Clic` par point, et `Valider()` (Entrée). L'essai et le reçu doivent être acceptés. Ensuite `Lot362.Tick`, puis `Attendre()` doit rendre vrai. Le plan doit compter **une** rue de plus, et `Posees` doit l'avoir acceptée.
    3. **La parcelle.** `EntrerParcelle()` (P), puis `Lot375.Cliquer` aux coins `Point(rue, 5, 1, 3)` et `Point(rue, 5, 9, 17)`, en visant `Milieu(terrain, rue, 5)`. Puis `ValiderParcelle()` (Entrée) : `Tracee.Presente` et le reçu accepté. Ensuite `Lot362.Tick` et `Attendre()`. Le plan doit compter une parcelle de plus, dessinée `cordeau`.
    4. **L'atelier.** `EntrerBatiment(PoseDeBatiment.Natures[1])` (touche 2), puis un `Lot375.Cliquer` au centre du contour de la parcelle : `Pose.Presente`, nature `scierie`, sur cette parcelle, reçu accepté. Ensuite `Lot362.Tick` et `Attendre()`. Le plan doit compter un bâtiment de plus, `scierie` sur cette parcelle, dessiné `piquets`.
    5. **Le temps.** `TICKS_APRES = 7` fois `Lot362.Tick`, puis `outil.Rafraichir()` (s'il rend faux, c'est un défaut).
    6. **La ville locale.** Si la consigne dit `ville_locale`, la première route `famille == "flanc"` est posée par `roads.Poser(g)`, sans dépôt ni essai : une rue que seul Unity connaît. Si le relief la refuse, c'est un défaut : la contre-épreuve ne doit jamais passer à vide.
    7. Le relevé `ville`, puis `vierge`.

    Aucun geste ne passe par `Lot362.Deposer` ni par un `ClientIntention` à soi : tout dépôt est celui de l'outil.
  - **Session `relance`** (même service) : aucun clic, aucun tick. `ville` est le relevé `ouverture`.
  - **Session `vierge`** (service neuf) : de même.
  - **Le jugement**, dans Unity. Un défaut est une phrase qui nomme la session, le tick et ce qui manque.
    - **Partout** : `tick_ouverture >= 0`. Pour chaque relevé, `parcelles` doit égaler `parcelles_plan`, et `batiments` doit égaler `batiments_plan` (identifiants, natures, états, ordre).
    - **`jouer`** :
      - à l'`ouverture`, plan vide, 0 pièce, et `empreinte_rues == vierge` : sinon le service n'est pas neuf ;
      - `gestes` compte 3 entrées dans l'ordre ;
      - `ville.tick` vaut le tick du plan après l'atelier, plus 7 ;
      - `ville` compte 1 rue (`rues_posees == rues`), 1 parcelle `bornes` et 1 `scierie` aux `piquets`, avec `pieces_parcelles == 1` et `pieces_batiments == 1` ;
      - `empreinte_rues != vierge`, et aucune des deux autres empreintes n'est `SHA-256("")`.
    - **`relance`** : on lit `jouer.json`. S'il est absent, ou si `jouer` n'a pas de `ville` relevée, c'est un défaut. On exige :
      - `ville.tick` égal à celui de `jouer` ;
      - les mêmes `rues` et `rues_posees` ;
      - les mêmes `parcelles` et `batiments` ;
      - les mêmes nombres de pièces ;
      - chacune des trois empreintes égale, avec un défaut par empreinte différente : `la ville relancée n'a pas les mêmes <rues|parcelles|bâtiments> : empreinte <a> pour <b>` ;
      - le même `vierge`.
    - **`vierge`** :
      - plan vide ;
      - `outil.Parcelles`, `outil.Batiments` et `Ouverture` vides ;
      - 0 pièce ;
      - `empreinte_rues == vierge`, et les deux autres empreintes valent `SHA-256("")` ;
      - le même `vierge` que `jouer`, si `jouer.json` existe.
- **`atelier_desert.py`** :
  - **Les actions.** On ajoute à `ACTIONS` les trois méthodes `ForgeLocal3D.DesertCityPreuve.Jouer|Relancer|Vierge`, actions `desert_preuve_jouer`, `desert_preuve_relance` et `desert_preuve_vierge`. On ajoute à `LOGS` `preuve_jouer.log`, `preuve_relance.log` et `preuve_vierge.log`.
  - **Une fonction neuve**, `preuve(ds, service_neuf=True, ville_locale=False, sourd=False)`, calquée sur `batiments` :
    1. Elle écrit les gestes et `selection.json` de `ds[0]`, efface les anciens `preuve/*.json`, puis écrit `preuve/consigne.json`.
    2. La garde « Unity est ouvert » passe avant le lancement de tout service et de tout Unity.
    3. Elle joue `jouer` puis `relance` sur un service, lancé par `lancer_service(sourd)`. Elle joue `vierge` sur un second service neuf, jamais sourd, ou sur le premier avec `service_neuf` faux.
    4. Pour chaque session, elle imprime :
       - le tick d'ouverture et `ville_locale` ;
       - une ligne par geste (`<type> après le tick N → <identifiant>`) ;
       - le relevé `ville` : tick ; rues ; parcelles et bâtiments `id [nature] état` ; pièces ; les quatre empreintes et `vierge` ;
       - chaque défaut.
    5. Elle lève comme `batiments` : rapport manquant, défauts, puis échec d'Unity.
  - **L'argparse.** `preuve` s'ajoute aux `choices`. On ajoute `--ville-locale` (aide : « preuve : la session jouer dessine une rue que seul Unity connaît (contre-épreuve du lot 386) »). Les aides de `--service-sourd` et `--sans-service-neuf` nomment aussi `preuve`. Une ligne de dispatch s'ajoute : `if a.action=='preuve':preuve(ds,not a.sans_service_neuf,a.ville_locale,a.service_sourd)`.
  - `routes`, `relance`, `batiments` et leurs lignes ne changent pas.
- **Le `.meta`** est celui qu'Unity génère.

## Conditions de succès

**SC1 — Unity compile, rien d'existant ne rougit.**
Le workflow `unity` est vert : aucune `error CS`. Sur le PC, les tests EditMode `Forge.Pont.Tests` rendent 0 et `failed="0"`, avec le même nombre de cas qu'avant. `py -m pytest jeu -q` reste vert.

**SC2 — la preuve passe (PC).**
Depuis `3d/`, `py local3d/atelier_desert.py preuve` rend 0, et ses trois rapports n'ont aucun défaut. La sortie montre :
- pour `jouer` : ouverture au tick 0 ; les trois gestes, après les ticks 0, 1 et 2 ; la ville au tick 10 avec la rue 0, la parcelle 0 `bornes` et le bâtiment 0 `scierie piquets`, 1 pièce de chaque ;
- pour `relance` : le tick 10 et les quatre empreintes de `jouer` ;
- pour `vierge` : ni rue, ni parcelle, ni bâtiment ; 0 pièce ; `empreinte_rues == vierge` ; les deux autres empreintes valent `SHA-256("")`.

La PR colle cette sortie.

**SC3 — contre-épreuves (PC).** Chacune doit faire rendre une erreur à la commande. La PR donne la sortie et le défaut attendu ; on retire ensuite chaque changement fait à la main.
- **(a) Une ville que seul Unity connaît.** `py local3d/atelier_desert.py preuve --ville-locale` échoue. `jouer` passe, avec `ville_locale` vrai. `relance` échoue au moins sur `la ville relancée n'a pas les mêmes rues`.
- **(b) Pas de service neuf.** `preuve --sans-service-neuf` échoue : `vierge` compte 1 rue, 1 parcelle et 1 bâtiment au plan, des pièces, et des empreintes non vierges.
- **(c) Un moteur qui ignore l'intention.** `preuve --service-sourd` échoue. `jouer` s'arrête à la route : le plan ne compte aucune rue de plus. `relance` n'a pas de ville à comparer.
- **(d) Un relancement qui oublie les bâtiments.** Dans `DesertRoadTool.Ouvrir`, on saute `DessinerBatiments` quand la ligne de commande d'Unity contient `DesertCityPreuve.Relancer`. `jouer` passe. `relance` échoue : aucun bâtiment dessiné pour `0 scierie piquets` au plan, 0 pièce, et l'empreinte des bâtiments vaut `SHA-256("")`.
- **(e) Le temps sans redessin.** Dans `DesertCityPreuve`, on retire l'appel à `Rafraichir()`. `jouer` échoue : la parcelle est dessinée `cordeau` alors que le plan du tick 10 la dit `bornes`.

**SC4 — les contrôles existants restent verts (PC).**
Depuis `3d/` :
- `py local3d/atelier_desert.py relance` et `py local3d/atelier_desert.py batiments` rendent 0 ;
- `batiments --sans-service-neuf` échoue toujours ;
- `routes --service-sourd` échoue toujours.

La PR montre les sorties.

**SC5 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff -U0 origin/master...HEAD -- 3d/local3d/atelier_desert.py | grep '^-[^-]'
grep -cE 'Lot362\.Deposer|new ClientIntention' 3d/unity/Assets/ForgeLocal3D/Editor/DesertCityPreuve.cs
```
- La première ne nomme que les fichiers du Périmètre et ce brief.
- La seconde montre au plus trois lignes : la fin de `ACTIONS`, la fin de `LOGS` et la ligne de l'argparse.
- La troisième rend `0`.

Restent hors du diff : `DesertCityBatiments.cs`, `DesertCityRelance.cs`, tout `Desert/` (l'outil et la vue), tout `Pont/`, toutes les captures (`Lot362.cs` et `Lot375.cs` compris), les scènes, les prefabs et `jeu/`.

## Hors périmètre
- Le rejeu du monde par `python3 -m sim --gestes`, la comparaison à l'octet avec le service, et les foyers par métier. C'est l'épreuve de bout en bout (sous-lots 1 et 3 de #264).
- La capture de la capitale pour le journal (sous-lot 4 de #264).
- Toucher l'outil, la vue, le pont, le kit, les scènes ou le service. Si le contrôle trouve un défaut de la vue, le lot s'arrête et le dit dans sa PR.
- De vrais événements de clavier et de souris (Input System simulé). La session appelle ce que `Update` appelle pour chaque touche, comme les captures #375 et #377.
- Faire jouer ce contrôle par la CI, ou l'ajouter à la boîte aux lettres de l'éditeur ouvert (`CitadelEditorBridge`).
- Mettre à jour `3d/local3d/desert/README.md`, `VILLE.md` ou `docs/NOTICE.md`.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.

## Photo
Sans objet : le lot ajoute un contrôle en batch, et rien de ce qu'on voit ne change. Aucune scène, aucun composant ni aucune pièce de la ville n'est modifié, et ses trois sessions ne capturent rien. La capitale bâtie par ces gestes sera photographiée par le sous-lot 4 de #264 ; la parcelle et l'atelier posés par l'outil le sont déjà par #375 et #377.
