# API d'hébergement City Mode

État : contrats, lifecycle de présentation, shell de transition et partitions
d'assets v1 isolés et validés dans des hôtes Unity minimaux
(`M3-FH-02..04`, `M3-FH-06`). URP `17.0.4` est la stratégie retenue ; les vues
urbaines riches ne réintroduisent jamais l'adaptateur laboratoire.

## Import minimal

Un backend qui veut seulement compiler le contrat importe le package sans
dépendance Unity :

```text
Packages/com.victoria.citymode.contracts
```

L'hôte Unity de production importe en plus le lifecycle de présentation :

```text
Packages/com.victoria.citymode.presentation
```

Le contenu approuvé et son contrat de chargement forment un troisième package :

```text
Packages/com.victoria.citymode.assets
```

Pour un import UPM Git, épingler un commit VictoriaCityLab et le sous-chemin :

```text
https://github.com/PLiagre/VictoriaCityLab.git?path=/Packages/com.victoria.citymode.contracts#<commit>
https://github.com/PLiagre/VictoriaCityLab.git?path=/Packages/com.victoria.citymode.presentation#<commit>
https://github.com/PLiagre/VictoriaCityLab.git?path=/Packages/com.victoria.citymode.assets#<commit>
```

Le package expose l'assembly `Victoria.CityMode.Contracts`, marqué
`noEngineReferences`. `Victoria.CityMode.Presentation` dépend seulement de cet
assembly et de `UnityEngine` : ni URP, ni Input System, ni AI Navigation, ni
scène, ni fixture. Le bundle historique `com.victoria.citymode` est désormais
identifié comme **laboratoire uniquement** ; il contient simulation, sauvegarde,
fixtures et présentation du vertical slice et ne doit jamais être importé dans
ForgeHistory.

`Victoria.CityMode.Assets` ne dépend d'aucun autre package City Mode. Il expose
seulement le catalogue de partition et `ICityModeAssetPartitionHost`; les
adresses de scènes, `SceneManager` et le rendu URP appartiennent à l'hôte.

## Ouverture explicite

L'hôte construit un contexte valide, implémente les deux ports autoritaires et
ouvre la transition :

```csharp
using Victoria.CityMode.Integration;
using Victoria.CityMode.Presentation;

using var shell = new CityModeTransitionShell(
    forgeHistoryTransitionHost,
    loadingScreenObserver);
var result = await shell.EnterAsync(
    launchContext,
    forgeHistorySnapshotSource,
    forgeHistoryIntentSink,
    cancellationToken);
if (!result.Succeeded)
    ShowRecoverableError(result.Error, result.Message);
```

`TryOpen` :

- valide version, identité, tick, révision et politique de temps ;
- refuse un port absent et un snapshot incompatible ;
- exige une égalité tick/révision sous `PauseWorld` ;
- refuse une deuxième session active avec `SessionAlreadyActive` ;
- ne crée aucun `GameObject`, aucune scène, aucun tick et aucune sauvegarde.

`CityModePresentationHost.TryCreate` est l'unique création Unity du socle v1.
Elle reçoit une session déjà validée, crée une racine jetable portant l'identité
opaque de la ville et refuse une seconde présentation active. Aucun `Awake`,
`RuntimeInitializeOnLoadMethod` ou chargement de scène ne la crée implicitement.

`ICityModeTransitionHost` appartient au projet hôte. Il charge la scène ville,
retourne son `ICityModePresentationView`, décharge la scène et restaure le
viewport/sélection contenus dans `CityLaunchContext`. Le package ignore les noms
de scène et n'appelle jamais `SceneManager`.

`CityModeTransitionShell` impose les états
`Map→LoadingCity→City→ReturningToMap→Map`, bloque une deuxième entrée, publie
la progression 0–1 et transforme annulation/timeout/échec en
`CityModeErrorCode`. Une entrée échouée déclenche toujours le rollback :
présentation/session libérées, scène ville déchargée si nécessaire, puis
restauration carte. Le premier chargement dispose de 10 s, un chargement chaud
de 3 s et le retour de 5 s par défaut ; l'hôte peut injecter d'autres budgets
explicitement.

## Boucle de session

`CurrentSnapshot` est le dernier snapshot complet validé. Une implémentation de
`ICityModePresentationView` reçoit l'ouverture, le snapshot initial, chaque reçu
et la fermeture ; elle ne reçoit aucun droit de tick ou de sauvegarde. Une vue
émet une intention à la révision courante via `TrySubmitIntent`. Une intention
périmée est refusée localement avant d'appeler l'hôte et produit un reçu
`RevisionConflict`. Après une acceptation, la présentation appelle
`TryRefreshSnapshot` avant l'intention suivante.

La fermeture appartient à l'hôte :

```csharp
var result = await shell.ExitAsync(cancellationToken);
```

Le shell ferme présentation puis session avant de décharger, et remet toujours
la carte active après la tentative de déchargement. Tous les `Dispose` sont
idempotents. Le shell ne possède ni horloge, ni simulation, ni transport, ni
sauvegarde.

## Partitions d'assets

`CityModeAssetPartitionLoader` impose l'ordre `Common→Biome→City` et libère en
ordre inverse. Chaque scène additive possède exactement un
`CityModeAssetPartitionCatalog` avec révision, références sérialisées, GUID,
SHA-256, licence et budget résident. Le package ne connaît aucun nom de scène et
n'utilise pas `Resources.Load` ; l'hôte implémente
`ICityModeAssetPartitionHost.LoadAsync/UnloadAsync`.

Le manifeste autoritaire
`Docs/Integration/city-mode-asset-port-v1.json` relie 11 sources approuvées à
11 cibles bit-identiques : six textures PBR communes, deux textures de biome et
trois variantes de scierie. Les nouveaux GUID cible ont été générés par Unity,
restent distincts des GUID source pour éviter les collisions dans le dépôt
laboratoire et sont désormais versionnés. PNG et FBX suivent Git LFS.

Si un catalogue, une métrique ou un budget est invalide, le loader inclut la
partition courante dans le rollback. Une annulation pendant un chargement est
également nettoyée côté hôte ; aucune simulation ou sauvegarde de secours n'est
créée.

## Laboratoire autonome

Le bundle `com.victoria.citymode` et `Assets/CityLabHost` forment ensemble le
laboratoire autonome. `CityLabBootstrap` n'a plus de
`RuntimeInitializeOnLoadMethod`. La scène
`Assets/CityLabHost/Scenes/CityLab.unity` contient déjà explicitement
`CityLabGame`, ce qui conserve son comportement autonome. Les outils qui créent
une scène de laboratoire à la volée peuvent appeler :

```csharp
var game = CityLabBootstrap.StartLaboratory();
// ...
CityLabBootstrap.StopLaboratory(game);
```

`StartLaboratory` retourne l'instance existante et n'en crée donc pas une
seconde. Cette API est réservée aux fixtures, smokes et revues du laboratoire ;
elle n'accepte pas de `CityLaunchContext` et ne doit pas être appelée par
ForgeHistory.

## Preuve d'import minimal

`Tools/UnityHosts/CityModeMinimalHost` épingle Unity `6000.0.43f1` et importe
uniquement Test Framework, contrats et présentation. Il ne contient ni scène,
ni fixture, ni asset CityLab et n'importe pas le bundle laboratoire. Ses trois
tests prouvent l'absence d'auto-démarrage, le refus d'une double instance et la
chaîne snapshot→intention→reçu→refresh→fermeture.

`Tools/UnityHosts/CityModeTransitionHost` est un second fixture isolé. Ses scènes
`MapMirror` et `CityModeView` n'embarquent aucune donnée ForgeHistory/CityLab ;
elles prouvent uniquement la composition `SceneManager` additive, la sélection
de cellule, la progression, le retour et la restauration du JSON de viewport.
Son soak Editor et son player GPU exécutent chacun 50 cycles.

`Tools/UnityHosts/CityModeAssetHost` est le troisième fixture isolé. Il importe
uniquement URP, Test Framework et le package d'assets, puis compose quatre
scènes : carte vide, socle commun, biome et ville. Ses tests et son player
chargent/libèrent dix fois les trois partitions ; le player produit les trois
captures de zoom et mesure la mémoire résidente sans importer contrats,
présentation ou laboratoire.

Commande :

```powershell
py Tools/run_unity_locked.py -- '<Unity.exe>' -batchmode -nographics `
  -projectPath Tools/UnityHosts/CityModeMinimalHost -runTests `
  -testPlatform EditMode -testResults Logs/editmode-citymode-minimal-host.xml
```
