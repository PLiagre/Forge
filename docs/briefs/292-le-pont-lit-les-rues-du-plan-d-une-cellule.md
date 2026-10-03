# Lot #292 — Le pont lit les rues du plan d'une cellule
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Unity sait demander au service local de `sim/` le plan d'une cellule (`GET /plan?cell=<cell_id>` sur 127.0.0.1) et en relire le tick et les rues telles que le monde les tient (identifiant, points en mètres locaux, largeur, chantier ou non), ou dire pourquoi il ne les a pas, jamais une rue devinée. La capitale en 3D aura ainsi une source pour se dessiner « d'après le plan que tient le monde » (CAP.md, jalon 4).

## Règle du monde
Sans objet : c'est un lot d'outil. Aucun nombre du monde n'est décidé ici et `sim/` n'est pas touché. Niveau de fidélité : sans objet.

Le lot sert la preuve du jalon J4 de `CAP.md` : « Le plan de la ville vit dans le monde : Unity relancé redessine la même ville d'après le service ». Le côté du service est déjà sur master : #253 (le plan) et #254 (la route tracée par intention). Il manque la lecture côté Unity. Le lot ne s'appuie sur rien que J2 ou J3 doivent encore livrer.

Ce qui existe, vérifié sur master le 03/10/2026 :

- `jeu/sim/service.py`, `do_GET` sur `/plan` : `200` et les octets publiés avec la photographie du tick, `{"cell_id", "rang": 0, "tick", "date", "rues", "parcelles", "batiments"}`. Une cellule inconnue rend `404 {"erreur": "cell inconnu : reçu <n>"}`, et un paramètre absent ou non entier rend `400`.
- `jeu/sim/plan.py`, `Rue` : `identifiant` (entier ≥ 0), `points` (au moins 2 points `[x, y]`, nombres finis), `largeur_m` (> 0, fini), `en_chantier` (booléen). `Plan.to_dict` écrit les quatre clés de chaque rue, et les rues sont triées par `identifiant`.
- `jeu/sim/tests/test_intentions.py`, `test_service_route_recu_refus_et_rejeu` : après une route déposée puis un tick, `rues == [{"identifiant": 0, "points": [[0, 0], [40, 0], [40, 25]], "largeur_m": 4, "en_chantier": true}]`. Sans route, `rues == []`, et c'est le plan de toute cellule au départ.
- `3d/unity/Assets/ForgeLocal3D/Pont/` contient `LecteurJson.LireObjet` (#185 : tableaux en `List<object>`, nombres en `double`, `true`/`false` en `bool`) et `ClientLieu.cs` (#186), dont ce lot reprend la manière : un `HttpClient` gardé par l'instance, aucune redirection suivie, un délai tenu par une minuterie, une absence qui nomme sa cause.

Ce que le client respecte du modèle :

- **« Le plan du bourg »** (MODELE.md) : les points sont en mètres locaux du bourg (x vers l'est, y vers le nord). Le client les relit tels quels, sans conversion, sans borne et sans tri. L'ordre des rues est celui de la réponse. `cell_id` reste la seule clé : le plan lu porte le `cell_id` relu, jamais un autre identifiant.
- **Un plan sans rue est une mesure.** `"rues": []` est l'état réel de toute cellule avant la première route. Il se relit comme un plan présent à zéro rue, jamais comme une absence. En revanche, une clé `rues` absente, ou qui n'est pas un tableau, est une absence.
- **« Ce qui se refuse plutôt que se devine »** et AGENTS.md § 4 : `en_chantier` ne vaut jamais `false` par défaut. Une rue sans `en_chantier` refuse tout le plan, et aucun plan partiel n'est rendu.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientPlan.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientPlanTests.cs.meta

Précisions :

- Les `.meta` sont ceux qu'Unity génère à l'import (deux lignes, comme `ClientLieu.cs.meta`). Chaque `guid` est neuf et unique dans le projet.
- `ClientPlan.cs` vit dans l'assemblage existant `Forge.Pont` (espace de noms `Forge.Pont`). **Ni l'asmdef, ni `ClientLieu.cs`, ni `LecteurJson.cs` ne changent.** Il n'utilise que la bibliothèque standard (`System.Net.Http`, `System.Globalization`, `System.Text`, `System.Threading`). Les aides de `ClientLieu` sont privées : celles dont le client a besoin sont réécrites dans le fichier neuf. Le fichier porte quatre types :
  - `RueDuPlan` (immuable) : `long Identifiant`, `IReadOnlyList<PointLocal> Points`, `double LargeurM`, `bool EnChantier`. `PointLocal` est une structure immuable `double X`, `double Y` déclarée dans le même fichier. Le nom `RueDuPlan` évite tout conflit avec un futur `Rue`.
  - `PlanLu` (immuable) : `long CellId`, `long Tick`, `IReadOnlyList<RueDuPlan> Rues`. La liste peut être vide, mais n'est jamais nulle.
  - `LecturePlan` contient soit un `PlanLu` (`Plan` non nul, `Absence` nulle), soit une absence (`Plan` nul, `Absence` = un texte non vide). Elle expose `bool Presente`. Jamais les deux, jamais aucun : une fabrique appelée avec `null` ou une cause vide lève une `ArgumentException`.
  - `ClientPlan : IDisposable` : `ClientPlan(int port, TimeSpan delai)`, avec les mêmes bornes que `ClientLieu` (un port hors `1..65535` lève `ArgumentOutOfRangeException`). L'hôte est figé à `127.0.0.1`. `LecturePlan Lire(long cellId)` fait `GET http://127.0.0.1:<port>/plan?cell=<cellId>` et ne lève jamais pour une cause du service. Chaque absence commence par `plan <cellId> : ` :
    - connexion refusée ou erreur réseau → `service absent sur 127.0.0.1:<port>` ; minuterie échue → `délai dépassé (<n> ms)` ;
    - statut autre que 200 (un `404` de cellule inconnue, un `302` jamais suivi) → absence qui nomme le code, le `cell_id` demandé et le corps reçu ;
    - `ErreurJson` → `JSON invalide à la position <n>` ;
    - `cell_id` absent ou non entier → `clé absente : cell_id` / `clé cell_id : …`. Un `cell_id` relu différent du demandé donne une absence qui nomme les deux ;
    - `tick` absent ou non entier (entier < 2^53, comme dans `ClientLieu`) → la clé `tick` est nommée ;
    - `rues` absente ou qui n'est pas un tableau → la clé `rues` est nommée ;
    - pour la rue de rang `i` dans le tableau, la clé fautive est nommée par son chemin pointé : `rues[i]` (un élément qui n'est pas un objet), `rues[i].identifiant` (absent, non entier ou négatif), `rues[i].points` (absent, pas un tableau, ou moins de 2 points), `rues[i].points[j]` (un point qui n'est pas un tableau de **exactement** 2 éléments), `rues[i].points[j]` avec le message `un nombre attendu` (une coordonnée non numérique : texte, `null`, booléen), `rues[i].largeur_m` (absente, non numérique, ou ≤ 0), `rues[i].en_chantier` (absent, ou pas un booléen : `0`, `"true"`, `null` sont refusés).
  - Les autres clés (`rang`, `date`, `parcelles`, `batiments`) ne sont ni lues ni exigées : elles appartiennent aux lots qui les dessineront.
- `ClientPlanTests.cs` (espace de noms `Forge.Pont.Tests`, assemblage existant `Forge.Pont.Tests` inchangé) : un faux service `HttpListener` sur `http://127.0.0.1:<port>/`, construit comme celui de `ClientLieuTests`. Le port libre est trouvé par un `TcpListener` sur le port 0 aussitôt refermé ; le service tourne sur un fil d'arrière-plan et se ferme dans `[TearDown]`. Il rend un statut et des octets fixés par le cas, et **retient le chemin et la requête** de la dernière requête reçue. Aucun fichier figé n'est ajouté. Les corps sont des littéraux du test, écrits dans la forme du service. Le plan de référence, `PLAN_DEUX_RUES`, vaut :
  `{"cell_id":9922,"rang":0,"tick":5,"date":{"annee":1400,"jour_de_l_annee":6},"rues":[{"identifiant":0,"points":[[0,0],[40,0],[40,25]],"largeur_m":4,"en_chantier":true},{"identifiant":3,"points":[[-12.5,7.25],[0,0]],"largeur_m":2.5,"en_chantier":false}],"parcelles":[],"batiments":[]}`.
  La première rue est celle que `test_intentions.py` fige pour le service. La seconde rue porte des décimales, une coordonnée négative et `en_chantier` à faux, pour que rien ne passe par défaut. Chaque cas de refus part de ce texte et y fait **un seul** remplacement ; le test vérifie d'abord que le remplacement a bien changé le texte.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`, qui interrompt `-runTests`). Le code de sortie vaut 0 et le XML dit `failed="0"`. Il compte les cas existants de `LecteurJsonTests`, `ClientLieuTests` et `PanneauLieuTests`, inchangés, **et au moins 8 cas** de `ClientPlanTests`. Zéro cas de `ClientPlanTests` est un échec.
Contre-épreuve, faite à la main et dite dans la PR : faire rendre `EnChantier = false` à une rue dont la clé `en_chantier` manque fait rougir le cas de SC4 ; retirer ce changement le rétablit.

**SC2 — un plan servi est relu exactement (PC, dans SC1).**
Le faux service rend `200` et `PLAN_DEUX_RUES`. `Lire(9922)` doit rendre `Presente`, `Absence` nulle, et le faux service doit avoir reçu le chemin `/plan` et la requête `cell=9922`. Les valeurs sont **égales** (`==`, sans tolérance) aux littéraux : `CellId` 9922, `Tick` 5, `Rues.Count` == 2, dans l'ordre de la réponse :
- rue 0 : `Identifiant` 0, points `(0,0) (40,0) (40,25)`, `LargeurM` 4.0, `EnChantier` vrai ;
- rue 1 : `Identifiant` 3, points `(-12.5,7.25) (0,0)`, `LargeurM` 2.5, `EnChantier` faux.

Contre-épreuve, cas distinct : le faux service rend le même texte avec `"rues":[]` (le test vérifie que le remplacement a changé le texte). `Lire(9922)` réussit, avec `Tick` 5 et `Rues.Count` == 0, et le cas affirme que ce plan **diffère** du plan de référence (`Assert.AreNotEqual(2, Rues.Count)`). Un plan vide ne passe donc pas pour le plan aux deux rues. Un client qui rendrait toujours une liste vide fait rougir SC2.

**SC3 — une cellule inconnue ou un service absent deviennent une absence déclarée (PC, dans SC1).**
Dans chaque cas, `Presente` est faux, `Plan` est nul et `Absence` contient `9922` :
- **port fermé** (aucun faux service sur le port libre trouvé) → `Absence` contient `service absent` et le port ;
- **404** : le faux service rend `404` avec le corps `{"erreur":"inconnu"}`, qui ne contient **pas** l'identifiant → `Absence` contient `404` et `9922` : c'est le client qui nomme la cellule ;
- **service muet** (requête acceptée, jamais répondue, délai de 200 ms) → `Absence` contient `délai dépassé`.

**SC4 — toute réponse mal formée est refusée en nommant la clé (PC, dans SC1).**
Chaque cas part de `PLAN_DEUX_RUES`, fait un seul remplacement, appelle `Lire(9922)` et exige `Presente` faux, `Plan` nul et une `Absence` qui contient le texte indiqué :
- **autre cellule** : `Lire(9923)` contre le texte inchangé → `9923` et `9922` ;
- **coordonnée non numérique** : `[-12.5,7.25]` devient `["-12.5",7.25]` → `rues[1].points[0]` ;
- **largeur absente** : `,"largeur_m":2.5` est retiré → `rues[1].largeur_m` ;
- **rue sans `en_chantier`** : `,"en_chantier":false` est retiré → `rues[1].en_chantier` ;
- **`rues` absente** : `"rues":[…],` est retiré en entier → `rues` ;
- **JSON invalide** : le `}` final est retiré → `JSON invalide` et `position`.

La faute porte exprès sur la **seconde** rue : un client qui rendrait la première rue seule, ou un plan partiel, fait rougir le cas.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que des chemins du périmètre, plus ce brief. `ClientLieu.cs`, `LecteurJson.cs`, les deux asmdef et les fichiers de tests existants n'apparaissent pas.

## Hors périmètre
- dessiner les rues dans une scène, les meshes, la caméra de la capitale, l'affichage du chantier : lots suivants du jalon J4 (découpe de #260) ;
- lire `parcelles`, `batiments`, `date` ou `rang` du plan ; lire `/monde`, `/horloge` ou `/lieu` ;
- déposer une intention (lot #291, fichiers distincts) ; lancer le service depuis Unity ; toute lecture asynchrone ou coroutine ;
- toute modification de `ClientLieu.cs`, `LecteurJson.cs`, `PanneauLieu.cs`, des deux asmdef, des tests existants de `Forge.Pont.Tests`, de `jeu/sim/` (service, plan, moteur, `MODELE.md`, tests) et du contrat ville (`jeu/ville/`) ;
- référencer `Forge.Pont` depuis `Assembly-CSharp`, les scènes ou `Assets/ForgeLocal3D/Editor/` ;
- une dépendance externe (Newtonsoft, `System.Text.Json`, `UnityWebRequest`) ;
- brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
