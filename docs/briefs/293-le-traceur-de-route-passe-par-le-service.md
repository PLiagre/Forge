# Lot #293 — Le traceur de route passe par le service
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
Quand le joueur trace une route dans la ville du désert, son geste devient une intention `tracer_route` déposée dans `sim/`. Unity affiche le reçu du service et ne dessine la route qu'au tick suivant, d'après les rues neuves que le monde publie dans `/plan`. Avant ce tick, le terrain ne bouge pas.

## Règle du monde
Le monde ne change pas : `jeu/sim/` n'est pas touché, et `MODELE.md` non plus. Le lot fait passer un geste d'Unity par le chemin que `MODELE.md` décrit déjà :

- **« Les intentions du joueur »** : `recevoir_intention` accepte `{"type": "tracer_route", "cell", "points", "largeur_m"}` et refuse tout champ en trop. L'étape Intentions du tick suivant ajoute la rue au plan, avec `en_chantier` à vrai.
- **« Le plan du bourg »** : les points sont en mètres locaux du bourg, sans borne. Ici, ce sont les points du repère de `paysage.py`, tels que `DesertRoads.PointExact` les donne, arrondis au centimètre. Ils sont pris tels quels comme mètres locaux du bourg. La position et la forme du bourg dans la cellule ne sont pas simulées : **niveau 3**.

Décision du propriétaire sur l'issue #293 (réponse **A**), à suivre telle quelle :

- **Unity refuse la route trop raide avant de la déposer.** Le relief du bourg n'existe que dans Unity. Une route que `DesertRoads` refuserait (pente en long, talus qui ne se referme pas, hors du terrain, hors de la boîte des hauteurs, points confondus) n'est **jamais** envoyée au service. Le monde, lui, accepte toute route valide pour `Rue`.
- **Toute route en chantier est en terre battue.** Le revêtement n'entre ni dans l'intention ni dans le monde. La touche T disparaît. L'outil pose toujours `terre`. Le contrôle compare donc le clic de plaine à la **même route posée en terre** (et non plus en pavés, comme le jeu de gestes la pose). C'est le seul point où le contrôle 263 change de référence, et c'est le propriétaire qui l'a tranché. Le jeu de gestes, lui, garde ses revêtements, et toutes ses vérifications restent en place.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/Forge.Pont.asmdef
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoadTool.cs
3d/unity/Assets/ForgeLocal3D/Desert/DesertRoads.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertCityRoads.cs
3d/local3d/desert/routes.py
3d/local3d/atelier_desert.py

Ce que le contrôle régénère sous `3d/local3d/desert/sorties/ville/<implantation>/routes/` (gestes, rapport Unity, jugement, captures) entre avec lui, comme au lot 263.

Précisions, fichier par fichier :

- **`Forge.Pont.asmdef`** : la seule ligne `"autoReferenced": false` devient `true`. Rien d'autre ne change, ni le nom, ni les références. Ainsi `Assembly-CSharp` (`DesertRoadTool`) et `Assembly-CSharp-Editor` (`DesertCityRoads`) voient `ClientIntention` et `ClientPlan`. L'asmdef des tests ne change pas.
- **`DesertRoads.cs`** : `Poser` reçoit un dernier paramètre optionnel, `bool essai=false`. En essai, la route passe par **tous** les refus existants, dans le même ordre, puis retourne `acceptee = true` (avec `ax`, `ay`, `profil`, `valeur`, `position`, `longueur` remplis) **juste avant** la première écriture : `heights`, `SetHeights`, `SetAlphamaps`, `SetDetailLayer` et `AddSpline` ne sont pas atteints. Sans `essai`, le comportement reste identique à l'octet près. Rien d'autre ne change dans ce fichier.
- **`DesertRoadTool.cs`** :
  - le champ `revetement` et la touche T disparaissent. La constante `Revetement = "terre"` sert à toute pose. Le texte d'aide perd « T : terre battue / pavés », et l'état affiché dit « Terre battue ». Les scènes ne sont pas régénérées : la clé `revetement` devenue orpheline y est ignorée par Unity ;
  - au `Awake`, l'outil lit la cellule par `PanneauLieu.LireCellule(Environment.GetCommandLineArgs(), PanneauLieu.CELLULE_PAR_DEFAUT, out erreur)`, et le port vaut `PanneauLieu.DEFAULT_SERVICE_PORT`. Il ouvre un `ClientIntention` et un `ClientPlan`, avec un délai d'une seconde chacun, et les ferme dans `OnDestroy`. Si `-forgeCell` est mal formé, le panneau affiche l'erreur et l'outil refuse tout dépôt. Les champs publics `Cellule` et `Port` sont exposés en lecture ;
  - `Valider()` garde sa signature. Avec moins de deux points, rien ne change. Sinon :
    1. il construit le geste (revêtement `terre`, largeur `largeur`) et appelle `roads.Poser(g, essai: true)`. Si la route est refusée, il affiche le message de refus, **ne dépose rien** et retourne ce résultat ;
    2. il lit `/plan` de la cellule et retient l'ensemble des identifiants de rue présents. Si ce plan est absent, il affiche « Pas de plan : <absence> » et ne dépose rien ;
    3. il dépose `{"type":"tracer_route","cell":<cellule>,"points":[[x,y],…],"largeur_m":<largeur>}`. Les nombres sont écrits en `CultureInfo.InvariantCulture`, au format `"R"`, et le texte est formé à la main, sans dépendance. Le reçu est gardé dans la propriété publique `Recu` (`RecuIntention`, nulle tant que rien n'a été déposé, remise à nulle par `Annuler` et à chaque `Valider`). L'outil affiche « Route déposée au monde : elle se trace au tick suivant (après le tick <n>). », ou « Le monde refuse la route : <Erreur, mot pour mot> », ou « Pas de reçu : <Absence> ». Il retourne le résultat de l'essai. **Le terrain n'a pas bougé** ;
  - `public bool Attendre()` : si aucun reçu accepté n'est en attente, retourne faux. Sinon, il lit `/plan`. Si le plan est absent, ou si `Plan.Tick` vaut au plus `AppliqueeAuTick`, il retourne faux sans rien toucher. Sinon, pour chaque rue dont l'identifiant n'était pas dans l'ensemble retenu, et dans l'ordre du plan, il appelle `roads.Poser(new Geste{id = "plan_<identifiant>", revetement = "terre", largeur = LargeurM, x/y = points relus tels quels})`. Il affiche le message de la dernière pose, range les résultats dans `Posees` (liste publique d'identifiants et de résultats, vidée à chaque `Valider`), oublie le reçu en attente et retourne vrai. Les rues neuves de **tout** auteur sont dessinées, pas seulement la sienne. Les rues déjà présentes avant le dépôt ne le sont jamais ;
  - `Update` : hors mode `automatique`, quand un reçu accepté attend, il appelle `Attendre()` au plus toutes les 0,25 s (temps réel). En mode `automatique`, c'est le contrôle qui l'appelle.
- **`DesertCityRoads.cs`** (le contrôle). Ses deux clics passent par le service :
  - le `Rapport` gagne `public Service service = new Service()`, une classe sérialisable avec `cell = -1`, `port = -1`, `empreinte_vierge`, et deux blocs. `raide` porte `bool clique`, `bool depose`, `int rues_avant = -1`, `int rues_apres = -1`. `plaine` porte `bool depose`, `bool recu_accepte`, `long appliquee_au_tick = -1`, `string recu`, `string empreinte_avant_tick`, `bool dessinee_avant_tick`, `long tick_plan = -1`, `int rues_neuves = -1`, `double[] rue_x`, `double[] rue_y`, `double rue_largeur = -1`, `bool rue_en_chantier`. Les valeurs « non calculé » valent `-1` ou sont vides, jamais 0 ;
  - une aide `static long Tick(int port)` envoie `POST http://127.0.0.1:<port>/tick?n=1` avec `HttpClient` et lit le `tick` rendu. Un statut autre que 200 ajoute un défaut qui le nomme. C'est l'horloge que le contrôle fait passer à la main, le service tournant à vitesse 0 ;
  - **clic raide** (bloc des captures) : la ligne `tool.revetement = …` est retirée. On relève `rues_avant` par `ClientPlan` ; les clics et `Valider` ne changent pas, ni le défaut « n'est pas refusée ». Ensuite `depose = tool.Recu != null`, puis `Tick(port)`, puis `rues_apres`. La capture `refus` est inchangée ;
  - **clic de plaine** : la ligne `tool.revetement = …` est retirée. Après `roads.Preparer`, on relève `empreinte_vierge = roads.Empreintes().Tout`. Après les clics et `Valider`, on remplit `depose`, `recu_accepte`, `appliquee_au_tick` et `recu` (le texte du reçu : erreur ou absence comprise). Ensuite `empreinte_avant_tick = roads.Empreintes().Tout` et `dessinee_avant_tick = tool.Attendre()`, puis `Tick(port)`. Si `tool.Attendre()` rend faux après ce tick, c'est un défaut. On relit enfin le plan : `tick_plan`, puis `rues_neuves`, `rue_*` d'après les rues de `tool.Posees`, et `empreinte_clic = roads.Empreintes().Tout`. La référence `empreinte_gestes` devient la même route posée **en terre** : une copie de `plainGeste` avec `revetement = "terre"`, posée par `roads.Poser` sur une copie fraîche. `c.acceptee` reste le résultat de `Valider` ;
  - tout le reste de `Run` (jeu de gestes, mesures, marcheurs, mur, captures, empreintes A/B/C, profil relevé, pente à 40 %, caméra du lot 251) reste identique.
- **`routes.py`** : une fonction `juger_service(s, c)` rend la liste des fautes ; `juger` l'appelle après SC8 et ajoute ses fautes. Elle exige :
  - `cell ≥ 0` et `port == 8000` ;
  - côté raide : `clique`, `not depose`, `rues_avant ≥ 0` et `rues_apres == rues_avant` ;
  - côté plaine : `depose`, `recu_accepte` et `appliquee_au_tick ≥ 0`. Aussi `empreinte_vierge` non vide, `empreinte_avant_tick == empreinte_vierge`, `not dessinee_avant_tick` et `tick_plan > appliquee_au_tick`. Puis `rues_neuves == 1`, `rue_x`/`rue_y` égaux à `c['obtenus_x']`/`c['obtenus_y']` à 1 cm près, `rue_largeur` égale à la largeur du geste de plaine, `rue_en_chantier` vrai, et `c['empreinte_clic'] != empreinte_vierge`.

  Chaque faute nomme ce qui manque, par exemple « service : la route acceptée n'a pas paru au plan après le tick ». Une clé `service` absente du rapport est une faute. Une contre-épreuve du jugement s'ajoute à `ce` : `ce['service_sourd']` doit être vrai quand on juge une copie où `rues_neuves = 0`, `rue_x = rue_y = []` et `empreinte_clic = empreinte_vierge`. Aucune vérification existante de `juger` n'est retirée ni desserrée.
- **`atelier_desert.py`**, action `routes` :
  - avant `run_unity`, elle lance le service : `subprocess.Popen([sys.executable, '-m', 'sim.service', '--port', '8000', '--jours-par-seconde', '0'], cwd=<dépôt>/jeu)`. Elle attend sur sa sortie la ligne `service prêt sur 127.0.0.1:8000`, deux minutes au plus. Sinon elle échoue avec un message qui nomme le port 8000 (déjà pris, ou service tombé) et la fin de sa sortie. Elle arrête le service dans un `finally`, qu'Unity réussisse ou non ;
  - une option `--service-sourd` (sans effet hors de `routes`) lance à la place le même service, dont `sim.service.recevoir_intention` est remplacée, dans ce seul processus, par une fonction qui appelle la vraie, puis retire l'intention de `monde.intentions_en_attente`. Le reçu reste « accepté », mais le monde ignore le geste. Le code de ce service sourd vit dans `routes.py` (par exemple `py -c` ou `-m local3d.desert.routes --service-sourd`) : `jeu/sim/` n'est jamais modifié ;
  - le reste de l'action (gestes, `selection.json`, garde « Unity est ouvert », impression, code de sortie) ne change pas.

## Conditions de succès

**SC1 — Unity compile, et les tests du pont restent verts (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" -testResults <temp>\pont.xml -logFile <temp>\pont.log
```
Le code de sortie vaut 0, le XML dit `failed="0"`, et le nombre de cas est celui de master (au moins un cas de chacun de `LecteurJsonTests`, `ClientLieuTests`, `PanneauLieuTests`, `ClientIntentionTests`, `ClientPlanTests`). Contre-épreuve : remettre `autoReferenced` à `false` fait échouer la compilation (`error CS0246` sur `ClientIntention` dans `DesertRoadTool.cs`). C'est fait à la main et dit dans la PR.

**SC2 — le contrôle du lot 263 passe par un vrai service, et toutes ses vérifications restent (PC).**
```
py 3d/local3d/atelier_desert.py routes
```
Code de sortie 0 sur les deux implantations, et `jugement.json` `status: valide` pour chacune. Le jugement contient toujours toutes les contre-épreuves du lot 263 et du lot 251, plus `service_sourd`, toutes vraies. Pendant la commande, un service tourne sur 127.0.0.1:8000 à vitesse 0. Il est arrêté à la fin : après la commande, plus rien n'écoute sur 8000. Contre-épreuve : avec un autre processus déjà à l'écoute sur 8000, la commande échoue et nomme le port.

**SC3 — la route raide est refusée par Unity et n'atteint jamais le monde (PC, dans SC2).**
Dans `unity-routes.json` de chaque implantation, `service.raide` porte `clique` vrai, `depose` faux et `rues_apres == rues_avant` après un vrai tick. Le défaut « la route trop raide, cliquée à l'écran, n'est pas refusée » reste absent. Les SC4 du lot 263 (refus, terrain identique à l'octet) passent toujours. Contre-épreuve, faite à la main et dite dans la PR : un `DesertRoadTool` qui déposerait sans l'essai (étape 1 retirée) fait `depose` vrai et `rues_apres = rues_avant + 1`, et `juger` rougit.

**SC4 — la route de plaine ne se dessine qu'au tick suivant, d'après le plan (PC, dans SC2).**
Pour chaque implantation, `service.plaine` porte `recu_accepte` vrai et `empreinte_avant_tick == empreinte_vierge` (le terrain n'a pas bougé au dépôt). Il porte aussi `dessinee_avant_tick` faux, `tick_plan > appliquee_au_tick`, `rues_neuves == 1`, des points de rue égaux aux points obtenus par le clic à 1 cm près, et `rue_en_chantier` vrai. Le clic du lot 263 passe : points à moins de 0,5 m, et `empreinte_clic == empreinte_gestes`, la référence étant la même route posée en terre. Sur la seconde implantation, la rue de la première est déjà au plan, et elle n'est **pas** redessinée (`rues_neuves == 1`).

**SC5 — contre-épreuve de l'issue : un service qui ignore l'intention fait rougir le contrôle (PC).**
```
py 3d/local3d/atelier_desert.py routes --disposition <une implantation> --service-sourd
```
La commande sort en code non nul. Son `jugement.json` dit `echec` avec la faute « la route acceptée n'a pas paru au plan », et le rapport Unity montre `recu_accepte` vrai, `rues_neuves == 0` et `empreinte_clic == empreinte_vierge` : le terrain est resté inchangé. Relancée sans `--service-sourd`, la commande repasse au vert. Les deux sorties sont collées dans la PR.

**SC6 — captures regardées (PC, dans SC2).**
Les quatre captures `routes/captures/` de chaque implantation sont non uniformes, comme au lot 263. Celle du refus montre le message de refus, et l'aide affichée ne parle plus de pavés. Celui qui livre les regarde et dit dans la PR ce qu'il y a vu.

**SC7 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q
py 3d/local3d/atelier_desert.py terrain --force
git diff --name-only origin/master...HEAD
git diff --stat origin/master...HEAD
```
La suite du jeu reste verte, et `terrain` reste valide avec ses six contre-épreuves. Le diff ne nomme que les six chemins du périmètre, les sorties régénérées et ce brief. Aucun fichier de `jeu/`, aucune scène, aucun test du pont n'apparaît. Le code ajouté reste sous 300 lignes.

## Hors périmètre
- Le revêtement dans le monde (intention, `Rue`, `MODELE.md`) et les pavés posés par le travail du chantier : un lot futur, si le propriétaire le demande.
- Redessiner au lancement les rues déjà au plan (« Unity relancé redessine la même ville ») : un autre lot du jalon J4.
- Le refus d'une route raide par le monde, et le relief du bourg dans `sim/`.
- Tout changement de `jeu/sim/` (service, intentions, plan, moteur, tests), de `ClientIntention.cs`, `ClientPlan.cs`, `ClientLieu.cs`, `LecteurJson.cs`, `PanneauLieu.cs`, des tests du pont et de leur asmdef.
- Toute autre ligne de `DesertRoads.cs` que le paramètre `essai`. Aussi `DesertCityTerrain.cs`, `DesertCityCamera.cs`, les scènes, `paysage.py`, `terrain.py`, `README.md`, `VILLE.md`, le manifeste Unity.
- Un service lancé depuis Unity, une lecture asynchrone, une file d'intentions, un nouvel essai automatique.
- Retirer ou desserrer une vérification de `routes.juger`. Le seul changement de référence est celui que le propriétaire a tranché : le clic de plaine comparé à la même route en terre.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
