# Lot #186 — Unity lit un lieu du service local
Jalon : J1 · Machine : pc · Taille prévue : 280 lignes

## But
Unity sait demander un lieu au service local de `sim/` (`GET /lieu?cell=<cell_id>` sur 127.0.0.1) et en relire les vrais chiffres — date, habitants, chaque marchandise du panier, faim, dette — ou dire pourquoi il ne les a pas, jamais des zéros : le panneau du jalon J1 aura enfin une source qui est `sim/` au même tick.

## Règle du monde
Sans objet : c'est un lot d'outil, un regard (CAP.md, jalon 1 : « Ce que le jalon change dans le monde : rien »). Aucun nombre du monde n'est décidé ici ; niveau de fidélité : sans objet.

Ce qu'il doit respecter du modèle (`jeu/sim/MODELE.md`) :

- **« Le panier de marchandises »** : `stocks` est ouvert. Le client relit **toutes** les clés de `stocks` telles que le service les écrit, sans liste de marchandises ; une marchandise nouvelle passe sans toucher au C#. Une marchandise absente de la réponse est absente du `Lieu` (jamais inventée à `0`) ; `0.0` reçu est une mesure et se garde.
- **« Ce qui se refuse plutôt que se devine »** et AGENTS.md § 4 : `cell_id` est la seule clé ; une clé absente, un type inattendu, le service injoignable, un statut autre que 200 ou un JSON invalide rendent une **absence déclarée qui nomme la cause** — aucun `Lieu` partiel, aucune valeur par défaut.
- **« La base de temps »** : la date se relit telle que le service l'écrit (`date.annee`, `date.jour_de_l_annee`) ; le client ne la recalcule pas depuis `tick`.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientLieu.cs
3d/unity/Assets/ForgeLocal3D/Pont/ClientLieu.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientLieuTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json.meta
jeu/sim/tests/test_monde.py

Précisions :
- les `.meta` sont ceux qu'Unity génère à l'import (on ne les écrit pas à la main) ; chaque `guid` est neuf et unique dans le projet ;
- `ClientLieu.cs` vit dans l'assemblage existant `Forge.Pont` (espace de noms `Forge.Pont`), dont l'asmdef **ne change pas** : `noEngineReferences` reste vrai, bibliothèque standard seule (`System`, `System.Collections.Generic`, `System.Net.Http`, `System.Globalization` ; le projet est en .NET Standard 2.1). Il s'appuie sur `LecteurJson.LireObjet` du lot #185, sans modifier `LecteurJson.cs`. Il porte trois types (~120 lignes) :
  - `Lieu` (immuable) : `long CellId`, `long Tick`, `int Annee`, `int JourDeLAnnee`, `long Population`, `IReadOnlyDictionary<string, double> Stocks`, `long HungerTicks`, `double FoodDeficitKg` ;
  - `LectureLieu` : soit un `Lieu` (`Lieu` non nul, `Absence` nulle), soit une absence (`Lieu` nul, `Absence` : un texte qui nomme la cause) ; `bool Presente` ; jamais les deux, jamais aucun ;
  - `ClientLieu` : `ClientLieu(int port, TimeSpan delai)` (port hors `1..65535` → `ArgumentOutOfRangeException`), hôte figé à `127.0.0.1` ; `LectureLieu Lire(long cellId)` fait `GET http://127.0.0.1:<port>/lieu?cell=<cellId>` avec un `HttpClient` gardé par l'instance (`IDisposable`), et ne lève jamais pour une cause du service. Les absences, chacune nommant `cell_id` et sa cause :
    - connexion refusée ou erreur réseau → `service absent sur 127.0.0.1:<port>` ; délai dépassé → `délai dépassé` ;
    - statut autre que 200 → le code (`404`), le `cell_id` demandé et le corps reçu ;
    - `ErreurJson` → `JSON invalide` avec sa position ;
    - clé de tête ou de `date` absente → `clé absente : <nom>` (chemin pointé pour `date.annee`, `date.jour_de_l_annee`) ; valeur qui n'est pas un nombre, ou nombre non entier là où un entier est attendu (`cell_id`, `tick`, `population`, `hunger_ticks`, `date.*`) → `clé <nom> : ...` ; une valeur de `stocks` non numérique → nomme `stocks.<marchandise>` ;
    - `cell_id` relu différent du demandé → absence qui nomme les deux ;
- `lieu-graine0-tick4.json` : les **octets exacts** de `GET /lieu?cell=<C>` au tick 4, où `C` est le `cell_id` du fichier figé du lot #185 (`lieu-graine0-tick3.json`, aujourd'hui 9922), obtenus par `py -m sim.service --seed 0 --port 0 --jours-par-seconde 0` (depuis `jeu/`), `POST /tick?n=4`, sans fin de ligne ajoutée ;
- `ClientLieuTests.cs` (espace de noms `Forge.Pont.Tests`, assemblage existant `Forge.Pont.Tests` inchangé) : un faux service `HttpListener` sur `http://127.0.0.1:<port>/`, port libre trouvé par un `TcpListener` sur le port 0 aussitôt refermé ; il rend un statut et des octets fixés par le cas, sur un fil d'arrière-plan, et se ferme dans `[TearDown]`. Les fichiers figés se lisent comme au lot #185 (`Application.dataPath`, absent ou vide → échec explicite) ;
- `jeu/sim/tests/test_monde.py` : **un cas ajouté**, rien d'autre ne change dans le fichier.

## Conditions de succès

**SC1 — la réponse décalée d'un tick est bien celle du service (VPS ou PC).**
```
python3 -m pytest jeu/sim/tests/test_monde.py -q -k "service_reponse_figee_du_pont"
```
Le cas existant du lot #185 reste vert, inchangé. Le cas ajouté, `test_service_reponse_figee_du_pont_tick4_est_celle_du_service`, lit `cell_id` dans `lieu-graine0-tick3.json`, démarre `lancer_service(0)`, fait `POST /tick?n=4`, et exige que les octets de `GET /lieu?cell=<C>` soient **identiques** à `lieu-graine0-tick4.json`, que son `tick` vaille 4 et qu'il **diffère** octet à octet du fichier du tick 3. Contre-épreuve, dans le même cas : après un `POST /tick?n=1` de plus, les octets ne sont plus ceux du fichier du tick 4.

**SC2 — Unity compile et joue les tests (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Code de sortie 0, le XML dit `failed="0"`, compte les cas de `LecteurJsonTests` (lot #185, inchangés) **et au moins 7 cas** de `ClientLieuTests` ; zéro cas est un échec. Contre-épreuve, à la main et dite dans la PR : faire rendre à `Lire` un `Lieu` à `Population = 0` quand la clé manque fait rougir le cas de SC4 ; le retirer le rétablit.

**SC3 — un lieu servi est relu exactement (PC, dans SC2).**
Le faux service rend `200` et les octets de `lieu-graine0-tick3.json`. `Lire(9922)` (le `cell_id` lu dans le fichier) rend `Presente`, `Absence` nulle, et des valeurs **égales** (`==`, sans tolérance) aux littéraux du fichier recopiés dans le test : `CellId` 9922, `Tick` 3, `Annee` 1400, `JourDeLAnnee` 4, `Population` 109752, `HungerTicks` 0, `FoodDeficitKg` 0.0, et `Stocks` a **exactement** les clés du fichier (au moins deux : `fer`, `nourriture`, `objet`) avec `625.890235`, `1086412.323983`, `19.415859`.
Contre-épreuve, cas distinct : le faux service rend `lieu-graine0-tick4.json` ; `Lire(9922)` réussit, mais `Tick` vaut 4 et `Stocks["nourriture"]` **diffère** du littéral du tick 3 (`Assert.AreNotEqual`) — un service décalé d'un tick ne passe pas pour le bon.

**SC4 — chaque défaut rend une absence qui nomme sa cause, jamais des zéros (PC, dans SC2).**
Dans chaque cas, `Presente` est faux, `Lieu` est nul, et `Absence` contient `9922` :
- **port fermé** (aucun faux service sur le port libre trouvé) → `Absence` contient `service absent` et le port ;
- **404** : le faux service rend `404` avec le corps `{"erreur":"inconnu"}` (qui ne contient **pas** l'identifiant) → `Absence` contient `404` et `9922` : c'est le client qui nomme la cellule ;
- **clé retirée** : le texte du tick 3 privé de `"population":109752,` (le test vérifie d'abord que le remplacement a changé le texte) → `Absence` contient `population` ; de même sans `"annee":1400,` → `Absence` contient `date.annee` ;
- **JSON invalide** : le texte du tick 3 tronqué de son `}` final → `Absence` contient `JSON invalide` et `position` ;
- **autre cellule** : `Lire(9923)` contre le fichier du tick 3 → absence qui nomme `9923` et `9922`.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
git diff origin/master...HEAD -- jeu/sim/tests/test_monde.py 3d/unity/Assets/ForgeLocal3D/Pont/LecteurJson.cs 3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
```
La suite du jeu reste verte, `test_no_hardcoded.py` compris. Le diff ne nomme que des chemins du périmètre (plus ce brief) ; celui de `test_monde.py` ne montre que des ajouts ; `LecteurJson.cs` et `LecteurJsonTests.cs` n'apparaissent pas.

## Hors périmètre
- le panneau, la scène, `pc\Jouer.cmd`, le lancement du service par Unity, l'horloge (pause, accélération), l'épreuve de bout en bout du jalon contre `--snapshot-json` et sa capture : lots suivants du jalon J1 ;
- `/monde`, `/intention`, `/tick` côté Unity ; toute lecture asynchrone ou coroutine ;
- toute modification de `LecteurJson.cs`, des deux asmdef, de `jeu/sim/service.py`, du moteur, de `MODELE.md`, du contrat ville (`jeu/ville/`, paquets `com.victoria.citymode.*`) et de `3d/unity/Packages/manifest.json` ;
- référencer `Forge.Pont` depuis `Assembly-CSharp`, les scènes ou `Assets/ForgeLocal3D/Editor/` ;
- une dépendance externe (Newtonsoft, `System.Text.Json`, `UnityWebRequest`) ;
- brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
