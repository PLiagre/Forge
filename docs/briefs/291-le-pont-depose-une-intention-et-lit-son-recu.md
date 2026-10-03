# Lot #291 — Le pont dépose une intention et lit son reçu
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Unity sait déposer un geste du joueur dans `sim/` (`POST /intention` sur 127.0.0.1) et en lire le reçu tel que le service le rend — accepté avec le tick que le service nomme, ou refusé avec sa raison — ou dire pourquoi il n'a pas de reçu, jamais un faux reçu : les gestes de la capitale (tracer une route, et les suivants) auront un chemin depuis Unity.

## Règle du monde
Sans objet : c'est un lot d'outil. Aucun nombre du monde n'est décidé ici, `sim/` n'est pas touché ; niveau de fidélité : sans objet.

Le lot sert la preuve du jalon J4 de `CAP.md` : « chaque geste est une intention déposée dans `sim/` et appliquée au tick suivant ». Le côté du service est sur master (#211, #254, `24e6be3`) ; il manque le côté d'Unity. Le lot ne s'appuie sur rien que J2 ou J3 doivent livrer.

Ce qui existe, vérifié sur master le 03/10/2026 :

- `jeu/sim/service.py`, `do_POST` sur `/intention` :
  - accepté → `200 {"acceptee": true, "appliquee_au_tick": <etat.tick>}` ; le nombre est le tick publié au moment du dépôt (`test_monde.py` attend `2` après `POST /tick?n=2`) ;
  - refusé → `400` (corps invalide, type inconnu, champ manquant…) ou `409` (« départ déjà choisi : … »), corps `{"acceptee": false, "erreur": "<raison>"}` ;
  - chemin inconnu → `404 {"erreur": …}`, sans `acceptee`.
- `jeu/sim/MODELE.md`, « Les intentions du joueur » : `recevoir_intention` est l'entrée commune ; la liste des types est fermée côté service.
- `3d/unity/Assets/ForgeLocal3D/Pont/` : `LecteurJson.LireObjet` (#185, lit `true`/`false`, lève `ErreurJson` avec `Position`) et `ClientLieu.cs` (#186), dont ce lot reprend la manière : `HttpClient` gardé par l'instance, aucune redirection suivie, délai tenu par une minuterie, absence qui nomme sa cause.

Ce que le client respecte du modèle :

- **Le client ne juge pas l'intention.** Il ne connaît aucun type d'intention et n'en valide aucun champ : la liste fermée vit dans `sim/`. Il exige seulement que le texte soit un objet JSON, comme le service.
- **Le client ne recalcule rien.** `appliquee_au_tick` est relu tel que le service l'écrit, sans `+1`. La raison d'un refus est relue mot pour mot.
- **« Ce qui se refuse plutôt que se devine »** : un reçu n'est accepté que si le statut **et** le corps le disent tous les deux ; toute incohérence est une absence.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientIntention.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientIntention.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientIntentionTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientIntentionTests.cs.meta

Précisions :

- les `.meta` sont ceux qu'Unity génère à l'import (deux lignes, comme `ClientLieu.cs.meta`) ; chaque `guid` est neuf et unique dans le projet ;
- `ClientIntention.cs` vit dans l'assemblage existant `Forge.Pont` (espace de noms `Forge.Pont`). **Ni l'asmdef, ni `ClientLieu.cs`, ni `LecteurJson.cs` ne changent.** Bibliothèque standard seule (`System.Net.Http`, `System.Globalization`, `System.Text`, `System.Threading`). Les petites aides de `ClientLieu` étant privées, celles dont il a besoin sont réécrites dans le fichier neuf. Il porte deux types :
  - `RecuIntention` (immuable), trois états exclusifs, construits par trois fabriques :
    - `Acceptee(long tick)` → `Presente` vrai, `Acceptee` vrai, `AppliqueeAuTick` = `tick`, `Statut` 200, `Erreur` nulle, `Absence` nulle ;
    - `Refusee(int statut, string erreur)` → `Presente` vrai, `Acceptee` faux, `AppliqueeAuTick` **nul** (`long?`), `Statut` 400 ou 409, `Erreur` non vide, `Absence` nulle ;
    - `Absente(string cause)` → `Presente` faux, `Acceptee` faux, `AppliqueeAuTick` nul, `Statut` nul (`int?`), `Erreur` nulle, `Absence` : un texte non vide qui nomme la cause ;
    - une fabrique appelée hors de ces bornes (`statut` autre que 400/409, erreur ou cause vide) lève `ArgumentException` ;
  - `ClientIntention : IDisposable` : `ClientIntention(int port, TimeSpan delai)`, mêmes bornes que `ClientLieu` (port hors `1..65535` → `ArgumentOutOfRangeException`), hôte figé à `127.0.0.1`. `RecuIntention Deposer(string intentionJson)` :
    - `intentionJson` nul, ou qui n'est pas un objet JSON selon `LecteurJson.LireObjet` → `ArgumentException`, **avant tout envoi** : c'est une faute de l'appelant, pas du service ;
    - sinon `POST http://127.0.0.1:<port>/intention`, corps = les octets UTF-8 du texte **inchangé**, `Content-Type: application/json` ; ne lève jamais pour une cause du service. Chaque absence commence par `intention : ` ;
    - connexion refusée ou erreur réseau → `service absent sur 127.0.0.1:<port>` ; minuterie échue → `délai dépassé (<n> ms)` ;
    - statut autre que 200, 400, 409 (un 302 compris, jamais suivi) → absence qui nomme le code et le corps reçu ;
    - `ErreurJson` sur le corps → `JSON invalide à la position <n>` ;
    - **200** : le corps doit porter `acceptee` = `true` (le booléen) et `appliquee_au_tick` entier ≥ 0 et < 2^53 ; sinon absence qui nomme `200` et la clé fautive (`clé absente : appliquee_au_tick`, `clé acceptee : true attendu…`) ;
    - **400 ou 409** : le corps doit porter `acceptee` = `false` (le booléen) et `erreur` = un texte non vide ; sinon absence qui nomme le code et la clé fautive. Un `400` dont le corps dit `"acceptee": true` n'est **jamais** un reçu accepté ;
- `ClientIntentionTests.cs` (espace de noms `Forge.Pont.Tests`, assemblage existant `Forge.Pont.Tests` inchangé) : un faux service `HttpListener` comme celui de `ClientLieuTests` (port libre par un `TcpListener` sur le port 0 aussitôt refermé, fil d'arrière-plan, fermeture dans `[TearDown]`, option `muet`). Il rend un statut et des octets fixés par le cas, et **retient** la méthode, le chemin et les octets du corps de la dernière requête reçue. Les corps de réponse sont des littéraux du test, copiés des formes de `service.py` ; aucun fichier figé n'est ajouté. L'intention envoyée par les cas est `{"type":"tracer_route","cell":9922,"points":[[0,0],[40,0],[40,25]],"largeur_m":4}`.

## Conditions de succès

**SC1 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` (6000.0.43f1) :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Code de sortie 0, le XML dit `failed="0"`, compte tous les cas existants de `LecteurJsonTests`, `ClientLieuTests` et `PanneauLieuTests`, **et au moins 9 cas** de `ClientIntentionTests` ; zéro cas est un échec.

**SC2 — un reçu accepté est relu exactement, et l'intention arrive intacte (PC, dans SC1).**
Le faux service rend `200 {"acceptee":true,"appliquee_au_tick":7}`. `Deposer(<intention>)` rend `Presente`, `Acceptee`, `AppliqueeAuTick == 7` (pas 8 : le client ne recalcule pas), `Statut == 200`, `Erreur` et `Absence` nulles. Le faux service a reçu `POST`, chemin `/intention`, et des octets **identiques** à l'UTF-8 de l'intention envoyée.
Contre-épreuve, cas distinct : `200 {"acceptee":false,"erreur":"incohérent"}` → absence qui contient `200` et `acceptee` ; `200 {"acceptee":true}` → absence qui contient `appliquee_au_tick`.

**SC3 — un refus reste un refus, avec la raison du service (PC, dans SC1).**
- `400 {"acceptee":false,"erreur":"type d'intention inconnu : 'x'"}` → `Presente`, `Acceptee` faux, `AppliqueeAuTick` nul, `Statut == 400`, `Erreur` égale **mot pour mot** à la raison ;
- `409 {"acceptee":false,"erreur":"départ déjà choisi : X"}` → idem avec `409`, accent compris.

Contre-épreuve, celle de l'issue, dans un cas distinct : `400 {"acceptee":true,"appliquee_au_tick":7}` → `Acceptee` faux, `AppliqueeAuTick` nul, absence qui contient `400`. Un client qui lirait `acceptee` sans regarder le statut, ou qui prendrait un 4xx pour une acceptation, fait rougir ce cas et ceux du refus. **À la main, dit dans la PR** : remplacer dans `Deposer` le test de `acceptee` à 400/409 par `Acceptee(…)` fait rougir ces cas ; le retirer les rétablit.

**SC4 — sans reçu, une absence qui nomme sa cause (PC, dans SC1).**
Dans chaque cas, `Presente` faux, `Acceptee` faux, `AppliqueeAuTick` nul, `Absence` commence par `intention : ` :
- **service absent** (aucun faux service sur le port libre) → contient `service absent` et le port ;
- **délai** : faux service `muet`, `ClientIntention(port, 300 ms)` → contient `délai dépassé` ;
- **corps invalide** : `200 {"acceptee":true,"appliquee_au_tick":7` (sans `}` final) → contient `JSON invalide` et `position` ;
- **autre statut** : `404 {"erreur":"chemin inconnu : '/x'"}` → contient `404` et ce corps.

**SC5 — les fautes de l'appelant lèvent avant tout envoi (PC, dans SC1).**
`Deposer(null)`, `Deposer("[1]")` et `Deposer("{")` lèvent `ArgumentException`, faux service à l'écoute, et le faux service n'a reçu **aucune** requête ; `new ClientIntention(0, …)` et `new ClientIntention(65536, …)` lèvent `ArgumentOutOfRangeException`.

**SC6 — rien d'autre ne bouge.**
```
git diff --name-only origin/master...HEAD
git diff --stat origin/master...HEAD
```
Le diff ne nomme que les quatre chemins du périmètre (plus ce brief) ; `ClientLieu.cs`, `LecteurJson.cs`, les deux asmdef et les tests existants n'apparaissent pas. Le total reste sous 300 lignes.

## Hors périmètre
- tout geste d'Unity qui appelle ce client (tracer une route à la souris, choisir sa terre dans une scène), le panneau du reçu, la relecture du plan après le tick : lots suivants du jalon J4 ;
- toute validation des types ou des champs d'une intention côté C# ; une file d'attente, un nouvel essai, un dépôt asynchrone ou une coroutine ;
- `/tick`, `/vitesse`, `/plan`, `/monde` côté Unity ;
- toute modification de `ClientLieu.cs`, `LecteurJson.cs`, `PanneauLieu.cs`, des deux asmdef, des tests existants, de `jeu/sim/service.py`, de `jeu/sim/intentions.py`, du moteur et de `MODELE.md` ;
- une dépendance externe (Newtonsoft, `System.Text.Json`, `UnityWebRequest`) ;
- brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
