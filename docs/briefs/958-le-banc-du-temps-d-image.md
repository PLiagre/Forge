# Lot #958 — Le banc du temps d'image
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Forge sait mesurer honnêtement combien de millisecondes coûte une image de la capitale, vue d'une caméra posée, rendue en 1920 × 1080 sans synchronisation ni plafond, et la résumer en médiane, 95e centile et maximum. Un interrupteur prépare la mesure « sans optimisations ».

## Le joueur
Le joueur ne voit rien de neuf : rien ne change à l'écran. Lot de fond du geste du J4 « entre dans sa capitale en 3D, y marche », et de son écran « une ville vivante dont chaque fumée, chaque étal et chaque passant suit le monde » (`CAP.md`, jalon 4). C'est le sous-lot 2 de #422 « La capitale dense tient 60 images par seconde ». Le sous-lot 3 de #422 mesurera avec ce banc la ville dense de Biskra sous quatre vues (survol, rue, place, chantier). Les sous-lots 4 et 5 l'accéléreront derrière l'interrupteur, et le sous-lot 6 prouvera un 95e centile sous 16,7 ms, avec sa contre-épreuve sans optimisations. Ce que le joueur sentira, à la fin de #422 : sa capitale pleine de maisons, de fumées et de passants ne saccade pas quand il la survole ou marche dans ses rues.

## Règle du monde
Sans objet : lot d'outil et de mesure. Aucun nombre du monde n'est lu ni décidé, `jeu/` n'est pas touché. Niveau de fidélité : sans objet.

**Ce que le chef a relevé (01/11/2026, master 95a1c9a9).**
- En batch, l'éditeur ne rend pas la vue du jeu. `EpreuveVille1400` mesure `Time.unscaledDeltaTime` sans rien rendre : 0,226 ms par image (`docs/mesures/739-session-ville1400/relance-10103.json`, `image_ms`). Le banc doit donc **rendre lui-même** la caméra à chaque image et attendre la fin du rendu. Sinon il mesure le vide.
- Le rendu explicite existe déjà : `CitadelPlayCheck.Capture` fait `RenderPipeline.SubmitRenderRequest(camera, new UniversalRenderPipeline.SingleCameraRequest{ destination = rt })` (URP 17). Il ne touche pas `camera.targetTexture`.
- Qualité courante : Ultra (5), `vSyncCount: 1`. Le pipeline du désert a un MSAA de 2 (`Desert/Settings/Pipeline.asset`), et `QualitySettings.antiAliasing` vaut 2 en Ultra.
- `CitadelBenchmark` calcule déjà médiane et P95, mais dans un joueur Windows et sans test. On ne le touche pas et on ne le réutilise pas.
- Un scénario de capture avance d'un `MoveNext` par image (`Capture.AvancerScenario`). Un `yield return` d'un autre `IEnumerator` ne l'exécute pas (`ScenarioDeCapture.cs`). Le banc est donc un itérateur que le scénario déroule lui-même. Délai d'un scénario : 60 s (`DELAI_SCENARIO_S`). 361 images y tiennent largement.
- La première scène du build est `Forge_Desert_Ville_ksar_des_sept_puits`.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/TempsDImage.cs
3d/unity/Assets/ForgeLocal3D/Pont/TempsDImage.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/OptimisationsDeLaVille.cs
3d/unity/Assets/ForgeLocal3D/Pont/OptimisationsDeLaVille.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TempsDImageTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TempsDImageTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/BancDuTempsDImage.cs
3d/unity/Assets/ForgeLocal3D/Editor/BancDuTempsDImage.cs.meta
docs/briefs/958-le-banc-du-temps-d-image.md

Chaque `.meta` fait deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf. Budget du `numstat`, hors brief : `TempsDImage` 45, `OptimisationsDeLaVille` 15, tests 95, banc et scénario 105, `.meta` 8.

**`Pont/TempsDImage.cs`**, espace de noms `Forge.Pont`, sans `UnityEngine` : un calcul pur, sans aléa, sans horloge, sans réseau.
- `public sealed class ResumeDesTempsDImage`, immuable : `int Nombre`, `double MedianeMs`, `double P95Ms`, `double MaximumMs`.
- `public static class TempsDImage`, avec `public static ResumeDesTempsDImage Resumer(IReadOnlyList<double> tempsMs)` :
  - `tempsMs` nul : `ArgumentNullException`. Vide : `ArgumentException`, dont le message dit « échantillon vide ». Un élément NaN, infini ou négatif : `ArgumentOutOfRangeException`, dont le message nomme son rang et sa valeur. Zéro est permis ;
  - on trie une **copie** : la liste reçue n'est jamais modifiée ;
  - **médiane** : n impair, l'élément du milieu ; n pair, la moyenne des deux du milieu ;
  - **95e centile au rang le plus proche** : le rang k = ⌈95·n/100⌉, compté à partir de 1, calculé **en entiers** : `k = (95 * n + 99) / 100`. On rend l'élément trié de rang k. Le calcul en `double` de `0.95 * n` est interdit (il donne 95,00000000000001 pour certains n) ;
  - **maximum** : le dernier élément trié.
- Un commentaire en tête dit pourquoi le rang le plus proche : c'est une image vraiment mesurée, jamais une valeur interpolée.

**`Pont/OptimisationsDeLaVille.cs`**, espace de noms `Forge.Pont`, une classe statique pure :
- `public const string SANS = "-forgeSansOptimisations";`
- `public static bool Lire(string[] arguments)` : nul, `ArgumentNullException`. Sinon `false` si un argument est **exactement** `SANS` (casse comprise), `true` dans tous les autres cas ;
- `public static readonly bool Actives = Lire(Environment.GetCommandLineArgs());`
- Un commentaire dit que rien ne la lit encore : les sous-lots 4 et 5 de #422 brancheront leurs optimisations sur `Actives`, et le sous-lot 6 jouera sa contre-épreuve avec `-forgeSansOptimisations`.

**`Pont/Tests/TempsDImageTests.cs`**, espace de noms `Forge.Pont.Tests`, deux classes de test dans ce fichier : `TempsDImageTests` et `OptimisationsDeLaVilleTests`. Les séries sont des littéraux, sans fichier. Un `TestCase` vaut mieux qu'un cas recopié.
- `TempsDImageTests` (au moins 12 cas) :
  - 1 à 20 dans le désordre `{7, 20, 3, 14, 1, 18, 9, 12, 5, 16, 2, 19, 11, 6, 15, 4, 17, 8, 13, 10}` : `Nombre` 20, médiane 10,5, P95 19, maximum 20. Le tableau est inchangé après l'appel ;
  - 1 à 10 : médiane 5,5, P95 **10** (rang 10). L'interpolation donnerait 9,55, et le rang tronqué `95 * n / 100` donnerait 9 ;
  - `{5, 1, 4, 2, 3}` : médiane 3, P95 5 ;
  - un seul élément `{16.7}` : médiane, P95 et maximum valent 16,7 ;
  - 1 à 21 : P95 20 ; 1 à 100 : médiane 50,5, P95 95, maximum 100 ;
  - `{0, 0, 0}` : tout vaut 0, sans exception ;
  - `{2, 2, 9, 2}` : médiane 2, P95 9, maximum 9 ;
  - refus : `null` lève `ArgumentNullException` ; `new double[0]` lève `ArgumentException`, et son message contient « vide » ; `{1, NaN}`, `{1, +∞}`, `{1, −∞}` et `{1, -0.001}` lèvent `ArgumentOutOfRangeException`, dont le message contient « 1 », le rang fautif compté à partir de 0.
- `OptimisationsDeLaVilleTests` (au moins 5 cas) :
  - `Lire(new string[0])` vrai ;
  - `Lire({"Unity.exe", "-forgeSansOptimisations", "-batchmode"})` faux ;
  - `Lire({"-forgesansoptimisations"})` vrai, et `Lire({"-forgeSansOptimisationsX"})` vrai ;
  - `Lire(null)` lève `ArgumentNullException` ;
  - `Actives == Lire(Environment.GetCommandLineArgs())`.

**`Editor/BancDuTempsDImage.cs`**, espace de noms `ForgeLocal3D`, script d'éditeur sans asmdef, comme ses voisins.
- `public sealed class ReleveDuBanc`, dont les champs publics servent aussi au rapport `JsonUtility` (voir le scénario) : `temps_ms` (`double[]`), `nombre`, `mediane_ms`, `p95_ms`, `maximum_ms`, `largeur`, `hauteur`, `anticrenelage`, `chauffe`, `images`, `rendu`, `vsync_avant`, `vsync_pendant`, `vsync_apres`, `plafond_avant`, `plafond_pendant`, `plafond_apres`.
- `public static IEnumerator Mesurer(Camera camera, int chauffe, int images, Action<ReleveDuBanc> rendre, bool rendu = true)`. C'est une méthode **non itératrice**, qui vérifie d'abord ses arguments puis rend l'itérateur privé. `camera` ou `rendre` nul : `ArgumentNullException`. `chauffe < 0` ou `images < 1` : `ArgumentOutOfRangeException`. L'itérateur :
  1. relève `QualitySettings.vSyncCount` et `Application.targetFrameRate` (« avant »), puis les met à 0 et à −1 et les relit (« pendant ») ;
  2. crée un `RenderTexture` de **1920 × 1080**, profondeur 24, `ARGB32`, `antiAliasing = Mathf.Max(1, QualitySettings.antiAliasing)`, et une `Texture2D` de 1 × 1 en `RGB24`. Il ne touche **jamais** `camera.targetTexture` ni la pose de la caméra ;
  3. joue `chauffe + images + 1` images. À chaque image : si `rendu`, `RenderPipeline.SubmitRenderRequest(camera, new UniversalRenderPipeline.SingleCameraRequest{ destination = rt })`, puis `RenderTexture.active = rt`, `ReadPixels(new Rect(0, 0, 1, 1), 0, 0)` dans la texture de 1 × 1 (ce qui attend la fin du rendu GPU), et l'ancien `RenderTexture.active` remis. Ensuite seulement, l'instant est relevé par un `Stopwatch` unique, puis `yield return null`. Le temps d'une image est l'écart entre deux instants consécutifs : il compte tout ce que l'image a coûté (scripts du jeu, rendu, attente du GPU). Les `chauffe` premiers écarts sont écartés, les `images` suivants gardés, en millisecondes ;
  4. dans un `finally` : remet `vSyncCount` et `targetFrameRate`, relit les valeurs (« après »), puis libère et détruit le `RenderTexture` et la texture (`DestroyImmediate`) ;
  5. résume les temps gardés par `TempsDImage.Resumer` et appelle `rendre` une fois, avec le relevé rempli.
- En tête, un commentaire dit l'usage : `var m = BancDuTempsDImage.Mesurer(...); while (m.MoveNext()) yield return null;` depuis un scénario de capture. Il dit aussi pourquoi le banc rend lui-même : le relevé de 0,226 ms de #739.
- **Le scénario** `[ScenarioDeCapture(958, "banc")] static IEnumerator Banc(Camera camera)`, dans le même fichier :
  - il refuse un `lot958-banc.json` déjà présent dans `Capture.DossierDesCaptures` (`InvalidOperationException` qui dit « lot958-banc.json existe déjà ») ;
  - il mesure la caméra reçue, **sans la déplacer**, avec `chauffe` 60 et `images` 300. Le paramètre `rendu` vaut `false` seulement sous `-forge958SansRendu` : c'est le témoin de la contre-épreuve, et la constante de ce drapeau vit dans ce fichier ;
  - il écrit `lot958-banc.json` (UTF-8 sans BOM, `JsonUtility.ToJson`) avec tous les champs du relevé, plus `camera` (le nom de l'objet), `optimisations` (`OptimisationsDeLaVille.Actives`), `contre_epreuve` (`""` ou `"forge958SansRendu"`) et `defaut` (`""` quand tout va bien). Puis `Debug.Log("CAPTURE_958 " + rapport)` ;
  - il laisse dix images passer avant de rendre la main, pour que la photo du scénario montre la scène telle qu'elle était.

## Conditions de succès
Les commandes Unity se jouent sur le PC, depuis la racine, éditeur fermé, **avec rendu** (jamais `-nographics`, jamais `-quit`), chaque fois dans un dossier neuf. `$unity` = `'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Les commandes M, C1 et C2 sont dans la section Photo.

`CONTROLE <dossier> <rendu 0|1> <optimisations 0|1>` = `py -3 -c $controle <dossier> <rendu> <optimisations>`, avec ce code indépendant du C# :
```powershell
$controle = @'
import json,math,sys
from pathlib import Path
d,rendu,optim=sys.argv[1],sys.argv[2]=='1',sys.argv[3]=='1'
r=json.loads((Path(d)/'lot958-banc.json').read_text(encoding='utf-8-sig')); t=r['temps_ms']; n=len(t)
assert r['defaut']=='', r['defaut']
assert (r['largeur'],r['hauteur'],r['chauffe'],r['images'])==(1920,1080,60,300) and n==300==r['nombre'], 'banc'
assert all(math.isfinite(x) and x>0 for x in t), 'temps'
assert (r['vsync_pendant'],r['plafond_pendant'])==(0,-1), 'reglages pendant'
assert (r['vsync_apres'],r['plafond_apres'])==(r['vsync_avant'],r['plafond_avant']), 'reglages rendus'
assert r['rendu'] is rendu and r['optimisations'] is optim, 'drapeaux'
s=sorted(t); med=(s[n//2-1]+s[n//2])/2 if n%2==0 else s[n//2]; p95=s[(95*n+99)//100-1]
assert abs(r['mediane_ms']-med)<1e-6 and abs(r['p95_ms']-p95)<1e-6 and abs(r['maximum_ms']-s[-1])<1e-6, 'resume'
print('ok', n, round(med,3), round(p95,3), round(s[-1],3), 'vsync avant', r['vsync_avant'])
'@
```

SC1 — **Le résumé et l'interrupteur, testés.**
```powershell
& $unity -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames "Forge.Pont.Tests" -testResults 3d/unity/Temp/lot958-tests.xml -logFile 3d/unity/Temp/lot958-tests.log
```
Il sort en 0, avec `failed="0"` dans le XML. Le XML compte au moins 12 cas `TempsDImageTests` et 5 cas `OptimisationsDeLaVilleTests`, aucun ignoré. Il compte tous les cas des autres classes de `Forge.Pont.Tests`, en même nombre et sous les mêmes noms que sur master. Zéro cas d'une des deux classes neuves est un échec. Le workflow `unity` est vert, sans aucune `error CS`.
Contre-épreuves, faites à la main et dites dans la PR (le rouge, puis le vert remis) :
- les tests écrits avant les classes : ça ne compile pas ;
- le rang du P95 écrit `95 * n / 100` : le cas 1 à 10 rougit (9 au lieu de 10) ;
- la médiane prise à `tri[n / 2]` : le cas 1 à 20 rougit (11 au lieu de 10,5) ;
- la garde des négatifs retirée : le cas `{1, -0.001}` rougit.

SC2 — **Le banc mesure une vraie image.** La commande M sort en 0, et `CONTROLE 3d/unity/Temp/lot958-banc 1 1` sort en 0 et affiche `ok 300 …`. Le codeur montre d'abord le rouge (le rapport est absent avant le code), puis le vert. Contre-épreuve : SC3.

SC3 — **Sans rendu, l'image ne coûte presque rien.** La commande C1 sort en 0, et `CONTROLE 3d/unity/Temp/lot958-sans-rendu 0 1` sort en 0. Puis :
```powershell
py -3 -c "import json,sys;from pathlib import Path;L=lambda d:json.loads((Path(d)/'lot958-banc.json').read_text(encoding='utf-8-sig'));a,b=L(sys.argv[1]),L(sys.argv[2]);assert a['rendu'] and not b['rendu'] and a['mediane_ms']>=2*b['mediane_ms'],(a['mediane_ms'],b['mediane_ms']);print('ok',a['mediane_ms'],b['mediane_ms'])" 3d/unity/Temp/lot958-banc 3d/unity/Temp/lot958-sans-rendu
```
Elle sort en 0. Les deux arguments inversés, elle sort en 1. Un banc qui ne rendrait rien en batch (le défaut de 0,226 ms de #739) donnerait deux médianes voisines, et cette comparaison rougirait. Le codeur écrit les deux médianes dans la PR.

SC4 — **L'interrupteur passe.** La commande C2 sort en 0. `CONTROLE 3d/unity/Temp/lot958-sans-optimisations 1 0` sort en 0, et `CONTROLE 3d/unity/Temp/lot958-sans-optimisations 1 1` sort en 1 sur `AssertionError: drapeaux`. Sur le rapport de M, c'est l'inverse : `1 1` passe (SC2), et `1 0` sort en 1.

SC5 — **Le banc refuse un vieux rapport.** On rejoue la commande M dans le même dossier `3d/unity/Temp/lot958-banc`, sans rien effacer. Elle sort en 1, et son journal (`-logFile 3d/unity/Temp/lot958-banc-bis.log`) nomme `lot958-banc.json existe déjà`.

SC6 — **Rien ne change à l'écran.** M donne `Forge_Desert_Ville_ksar_des_sept_puits.png` (le plan fixe) et `Forge_Desert_Ville_ksar_des_sept_puits--banc.png`. Le codeur ouvre les deux, dit ce qu'il voit, et donne la valeur de `--banc.ecart.txt`. On doit voir le même cadre et la même scène, sans image noire ni rognée. Une caméra déplacée, ou une vue du jeu qui serait restée tournée vers le `RenderTexture`, refuse le lot.

SC7 — **Les acquis et le budget.** La capture de régression sort en 0 sans changer son scénario :
```powershell
& $unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 908 -forgeCaptures 3d/unity/Temp/lot958-regres-908 -logFile 3d/unity/Temp/lot958-regres-908.log
```
Tous les tests EditMode restent verts (`-runTests -testPlatform EditMode` sans `-assemblyNames`, XML neuf, ni échec ni cas ignoré). `python3 -m pytest jeu -q` passe sur le VPS. `git diff --name-only origin/master` ne nomme que le Périmètre. `git diff origin/master -- jeu/ 3d/unity/Assets/ForgeLocal3D/Desert/ 3d/unity/Assets/ForgeLocal3D/Citadelle/ 3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs` est vide. Hors brief, `git diff --numstat origin/master` totalise moins de 300 lignes.

## Hors périmètre
- La ville dense, ses quatre vues, la mesure d'avant et `docs/mesures/422-capitale-dense/` (sous-lot 3 de #422). Le regroupement des maisons et de l'enceinte (sous-lot 4). Le LOD des fumées et des lampes (sous-lot 5). La preuve P95 < 16,7 ms et sa contre-épreuve (sous-lot 6).
- Tout code qui lit `OptimisationsDeLaVille.Actives` : rien ne le lit encore.
- Toucher `ForgeCapture.cs` (délais, drapeaux), `CitadelBenchmark`, `CitadelPlayCheck`, `EpreuveVille1400` et son `image_ms`, les scènes, les qualités, le pipeline, `jeu/`.
- Une mesure dans un joueur Windows construit. Un seuil d'images par seconde : ce banc mesure, il ne juge pas.
- Aucun rapport ni aucune image versés dans git.

## Photo
Sans objet : le lot ne change rien de ce qu'on voit à l'écran. C'est un outil de mesure et un interrupteur que rien ne lit encore. L'image `--banc.png` du scénario 958 reprend le plan fixe, sans rien poser : c'est la vérification de SC6, pas une photo de lot. Les commandes ci-dessous sont celles des conditions de succès. Leurs rapports `lot958-banc.json`, leurs journaux, les sorties de `CONTROLE` et de la comparaison, et les deux images de M sont joints au compte rendu.

Mesure, commande M :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 958 -forgeSeed 0 -forgeTicks 0 -forgeCaptures '3d/unity/Temp/lot958-banc' -logFile '3d/unity/Temp/lot958-banc.log'
```
Contre-épreuve C1, sans rendu :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 958 -forgeSeed 0 -forgeTicks 0 -forge958SansRendu -forgeCaptures '3d/unity/Temp/lot958-sans-rendu' -logFile '3d/unity/Temp/lot958-sans-rendu.log'
```
Contre-épreuve C2, sans optimisations :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 958 -forgeSeed 0 -forgeTicks 0 -forgeSansOptimisations -forgeCaptures '3d/unity/Temp/lot958-sans-optimisations' -logFile '3d/unity/Temp/lot958-sans-optimisations.log'
```
