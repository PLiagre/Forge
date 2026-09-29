# Lot #185 — Unity lit le JSON du service sans liste fermée
Jalon : J1 · Machine : pc · Taille prévue : 290 lignes

## But
Unity sait relire, dans un assemblage à lui (`Forge.Pont`), une réponse `/lieu` du service de `sim/` telle qu'elle est écrite — toutes ses marchandises, sans liste de clés fermée —, et refuse à voix haute un texte cassé : le client et le panneau du jalon J1 pourront afficher les vrais chiffres du monde au lieu d'un objet vide.

## Règle du monde
Sans objet : c'est un lot d'outil, un regard (CAP.md, jalon 1 : « Ce que le jalon change dans le monde : rien »). Aucun nombre du monde n'est décidé ici ; niveau de fidélité : sans objet.

Ce qu'il doit respecter du modèle (`jeu/sim/MODELE.md`, « Le panier de marchandises » et « Ce qui se refuse plutôt que se devine ») :

- **Le panier est ouvert.** `Cell.stocks` associe un nom de marchandise à des kilogrammes ; la liste des marchandises se dérive du monde (le fer, le sel, l'`objet`… apparaissent selon les gisements). Le lecteur ne connaît donc **aucun nom de clé** : ni `nourriture`, ni `stocks`, ni `cell_id`. Une marchandise nouvelle dans `sim/` passe sans toucher au C#. C'est pourquoi `JsonUtility` (champs fixes, pas de dictionnaire) ne convient pas.
- **Une absence se déclare, rien ne se devine** (AGENTS.md, § 4) : un texte invalide ou tronqué lève une exception qui nomme la position (index du caractère dans le texte) ; jamais un objet vide, jamais `null` rendu en silence, jamais une valeur par défaut.
- **`0` est une mesure** : `0.0` et `0` se lisent comme des nombres, pas comme une absence.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont.meta
3d/unity/Assets/ForgeLocal3D/Pont/Forge.Pont.asmdef
3d/unity/Assets/ForgeLocal3D/Pont/Forge.Pont.asmdef.meta
3d/unity/Assets/ForgeLocal3D/Pont/LecteurJson.cs
3d/unity/Assets/ForgeLocal3D/Pont/LecteurJson.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/Forge.Pont.Tests.asmdef
3d/unity/Assets/ForgeLocal3D/Pont/Tests/Forge.Pont.Tests.asmdef.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json.meta
jeu/sim/tests/test_monde.py

Précisions :
- les `.meta` sont ceux qu'Unity génère à l'import (on ne les écrit pas à la main) ; chaque `guid` est neuf et unique dans le projet ;
- `Forge.Pont.asmdef` : `"name": "Forge.Pont"`, `"autoReferenced": false`, aucune référence, `"noEngineReferences": true` (bibliothèque standard seule : le lecteur n'a besoin ni d'`UnityEngine` ni d'`UnityEditor`). Le dossier `Pont/` n'est pas sous un dossier `Editor/` : l'assemblage est un assemblage d'exécution, isolé d'`Assembly-CSharp` — ni `Assembly-CSharp` ni `Assembly-CSharp-Editor` ne le référencent dans ce lot ;
- `Forge.Pont.Tests.asmdef` : `"name": "Forge.Pont.Tests"`, `"references": ["Forge.Pont"]`, `"optionalUnityReferences": ["TestAssemblies"]`, `"includePlatforms": ["Editor"]`, `"autoReferenced": false` — le même patron que `Victoria.CityMode.Contracts.EditorTests.asmdef` ;
- `LecteurJson.cs` (espace de noms `Forge.Pont`, ~110 lignes, `System` et `System.Collections.Generic` et `System.Globalization` seuls) : une analyse descendante récursive qui rend `object` — `Dictionary<string, object>` pour un objet (clés dans l'ordre du texte, clé en double → erreur), `List<object>` pour un tableau, `string` (échappements `\" \\ \/ \b \f \n \r \t \uXXXX`), `double` pour tout nombre (lu avec `CultureInfo.InvariantCulture`, grammaire JSON stricte : pas de `+` initial, pas de zéro de tête, pas de `.5`, pas de `NaN`), `bool`, et `null` pour le littéral `null`. Deux entrées publiques : `object Lire(string texte)` et `Dictionary<string, object> LireObjet(string texte)`, qui exige un objet à la racine ; les espaces JSON sont admis autour des valeurs ; tout caractère non blanc après la valeur racine est une erreur. Une seule exception, `ErreurJson : FormatException`, qui porte `Position` (int, index dans le texte) et dont le message contient `position <n>` et ce qui était attendu ;
- `lieu-graine0-tick3.json` : les **octets exacts** de la réponse du service, sans fin de ligne ajoutée, obtenus par `py -m sim.service --seed 0 --port 0 --jours-par-seconde 0` (depuis `jeu/`), `POST /tick?n=3`, puis `GET /lieu?cell=<C>`, où `C` est la **première cellule par `cell_id`** dont `stocks` compte au moins deux marchandises au tick 3 (aujourd'hui 9922, avec `fer`, `nourriture`, `objet`) ;
- `jeu/sim/tests/test_monde.py` : **un cas ajouté**, rien d'autre ne change dans le fichier.

## Conditions de succès

**SC1 — la réponse figée est bien celle du service (VPS ou PC).**
```
python3 -m pytest jeu/sim/tests/test_monde.py -q -k service_reponse_figee_du_pont
```
Le cas ajouté (nommé `test_service_reponse_figee_du_pont_est_celle_du_service`) démarre le service par le `lancer_service(0)` existant (horloge en pause), fait `POST /tick?n=3`, lit `/monde`, **dérive** `C` comme ci-dessus (aucune cellule à deux marchandises → échec : un échantillon vide échoue), lit `GET /lieu?cell=C` et exige que ses octets soient **identiques** à ceux de `3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json`. Il exige aussi, sur le fichier relu par `json.loads`, `len(stocks) >= 2`. Contre-épreuve, dans le même cas : les octets de `GET /lieu` après un `POST /tick?n=1` de plus diffèrent de ceux du fichier (la comparaison voit un tick de décalage).

**SC2 — Unity compile l'assemblage isolé (PC).**
Le workflow `unity` (poussée sur la branche) est vert : aucune `error CS`. Puis, sur le PC, avec la version de `ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Forge.Pont.Tests" `
  -testResults <temp>\pont-editmode.xml -logFile <temp>\pont-editmode.log
```
(sans `-quit`). Code de sortie 0, le XML dit `failed="0"` et compte **au moins 8 cas** pour `Forge.Pont.Tests` ; zéro cas est un échec. Contre-épreuve, à la main et dite dans la PR : ajouter `using UnityEngine;` et un appel `Debug.Log` dans `LecteurJson.cs` fait échouer la compilation (`noEngineReferences` tient l'isolement) ; le retirer la rétablit.

**SC3 — la réponse `/lieu` figée est relue en entier, sans liste fermée (PC, dans SC2).**
`LecteurJsonTests.cs` lit le fichier figé par `File.ReadAllText(Path.Combine(Application.dataPath, "ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json"))` (fichier absent ou vide → échec explicite, pas `Ignore`) et exige de `LireObjet` :
- les clés de tête sont exactement `cell_id`, `date`, `food_deficit_kg`, `hunger_ticks`, `population`, `stocks`, `tick` (la liste est celle **attendue** du test, le lecteur n'en connaît aucune) ; `date` est un dictionnaire à deux clés ;
- `stocks` est un `Dictionary<string, object>` d'**au moins deux** marchandises, dont `nourriture` et une autre ;
- chaque valeur est **égale** (`==` sur `double`, sans tolérance) à celle écrite dans le texte : `cell_id`, `population`, `tick`, `hunger_ticks`, `food_deficit_kg` et chaque stock valent les littéraux du fichier, recopiés dans le test (`9922`, `109752`, `1086412.323983`…) ; ce sont des nombres que le texte écrit, et SC1 garantit que le texte est celui du service.

Contre-épreuve, dans le même fichier : sur une copie en mémoire du texte où **un seul chiffre** d'un stock est changé (par exemple `1086412.323983` → `1086412.323984`), `LireObjet` réussit et la valeur relue **diffère** du littéral attendu ; le cas l'exige (`Assert.AreNotEqual`). Un deuxième cas ajoute au texte une marchandise inventée (`"zinc_du_test":1.5`) dans `stocks` : elle est relue avec sa valeur, sans une ligne de C# changée.

**SC4 — un texte cassé est refusé en nommant la position (PC, dans SC2).**
Des cas de `LecteurJsonTests.cs` exigent une `ErreurJson` dont `Position` vaut la valeur attendue et dont le message contient `position` :
- le texte figé **tronqué**, deux fois : sans son `}` final (ses `Length - 1` premiers caractères), puis coupé juste après le `:` de la clé `stocks` → erreur, `Position` égale à la longueur du texte tronqué (fin inattendue) ;
- `[1]` passé à `LireObjet` → erreur à la position 0 (un tableau n'est pas un objet ; `Lire("[1]")` rend en revanche une liste d'un élément, `1.0`) ;
- la chaîne vide `""` → erreur à la position 0 ; `null` (référence C#) → `ArgumentNullException` ;
- `{"a":1}x` (déchet après la racine) → erreur à la position 7 ; `{"a":1,"a":2}` (clé en double) → erreur ;
- aucun de ces cas ne rend un dictionnaire vide : le test vérifie qu'une exception est levée, jamais un résultat.

Contre-épreuve, jouée à la main et dite dans la PR : faire rendre un dictionnaire vide à `LireObjet` quand le texte est vide fait rougir le cas de la chaîne vide ; le remettre le fait repasser.

**SC5 — rien d'autre ne bouge.**
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
git diff origin/master...HEAD -- jeu/sim/tests/test_monde.py
```
La suite du jeu reste verte, `test_no_hardcoded.py` compris. Le diff ne nomme que des chemins du périmètre (plus ce brief) ; celui de `test_monde.py` ne montre que des ajouts.

## Hors périmètre
- le client HTTP (`HttpClient`, `UnityWebRequest`), l'appel au service depuis Unity, le panneau, `pc\Jouer.cmd`, l'épreuve de bout en bout du jalon et sa capture : lots suivants du jalon J1 ;
- toute conversion vers des types du monde (une classe `Lieu`, `Stocks`…) : le lecteur rend des dictionnaires, rien de plus ;
- écrire du JSON (sérialiseur) ;
- toute modification de `jeu/sim/service.py`, du moteur, de `MODELE.md`, du contrat ville (`jeu/ville/`, paquets `com.victoria.citymode.*`) et de `3d/unity/Packages/manifest.json` ;
- référencer `Forge.Pont` depuis `Assembly-CSharp`, les scènes ou `Assets/ForgeLocal3D/Editor/` ;
- une dépendance externe (Newtonsoft, `System.Text.Json`) : bibliothèque standard seule ;
- brancher les tests EditMode dans un workflow : ce geste appartient au propriétaire, en mode direct ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
