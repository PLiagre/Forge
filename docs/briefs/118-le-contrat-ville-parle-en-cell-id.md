# Lot #118 — Le contrat ville parle en cell_id
Jalon : J1 · Machine : pc · Taille prévue : 290 lignes

## But
Unity reçoit de `sim/` des messages de vue ville (contexte, photographie,
intention, reçu) identifiés par le `cell_id` du monde, la seule clé spatiale du
modèle. Le contrat ne réclame plus une identité de ville que le moteur interdit :
le pont du jalon 1 peut désormais être branché dessus.

## Règle du monde
Aucune règle du monde ne change. Ce lot aligne le contrat sur
[`jeu/sim/MODELE.md`](../../jeu/sim/MODELE.md), section « Ce qui se refuse
plutôt que se devine » : « Aucun `city_id`, `ville_id` ni `bourg_id`. `cell_id`
reste la seule clé spatiale ». Et sur `CAP.md`, jalon 1 : « la clé qu'Unity
reçoit est `cell_id` ». Niveau de fidélité : sans objet (aucun nombre du monde).

Aujourd'hui, les quatre messages du schéma exigent `cityId` (une chaîne
opaque), et `CityLaunchContext` porte en plus `mapCellId` (une chaîne
`"cell:10:12"`). Deux clés spatiales, dont aucune n'est celle du moteur. Après
le lot :

- **les quatre messages** (`CityLaunchContext`, `CitySnapshotEnvelope`,
  `CityIntentEnvelope`, `CityIntentReceipt`) portent `cell_id`, obligatoire :
  un **entier ≥ 0**, le même type que `cell_id` dans
  `jeu/data/world-1400.json`. Le nom sur le fil est exactement `cell_id`
  (snake_case, comme dans `sim/`), en JSON comme dans le champ C# : ainsi
  `JsonUtility` écrit et lit la même clé que le schéma ;
- **`cityId` disparaît** des quatre messages, et **`mapCellId` aussi** : il
  ferait une seconde clé spatiale à côté de `cell_id`. `additionalProperties:
  false` reste sur chaque message : un message qui porte encore `cityId` ou
  `mapCellId` est refusé ;
- **côté C#**, le champ vaut `-1` par défaut (« non calculé », AGENTS.md §4) ;
  `0` est une cellule valide. La validation refuse tout `cell_id < 0`, et les
  contrôles de cohérence qui comparaient `cityId` (photographie contre
  contexte, intention contre contexte, reçu contre intention) comparent
  `cell_id`. L'erreur `InvalidCityId = 3` devient `InvalidCellId = 3` ;
  `InvalidMapCellId = 4` garde sa valeur (on ne renumérote pas un code
  filaire) mais n'est plus émis : un commentaire d'une ligne le dit ;
- **les exemples** prennent une vraie cellule de `jeu/data/world-1400.json`
  (par exemple `1175`), la même dans les cinq exemples ;
  `returnViewStateJson` dit `selectedCellId`. Le SHA-256 de la photographie ne
  change pas si `payloadJson` ne change pas ;
- **la documentation** (`jeu/ville/`, `3d/unity/README.md`) cesse de dire que
  le contrat attend une identité de ville : la clé est `cell_id` ; le lieu,
  subdivision de la cellule, viendra au jalon 3 avec une identité **dérivée**
  de `cell_id`, jamais une seconde clé.

## Périmètre
jeu/ville/Schemas/forgehistory-city-mode-v1.schema.json
jeu/ville/Schemas/forgehistory-city-mode-v1.examples.json
jeu/ville/FORGEHISTORY_CITY_MODE_CONTRACT.md
jeu/ville/README.md
jeu/ville/tests/test_contrat_cell_id.py
3d/unity/README.md
3d/unity/Packages/com.victoria.citymode.contracts/Runtime/ForgeHistoryCityModeContracts.cs
3d/unity/Packages/com.victoria.citymode.contracts/Tests.meta
3d/unity/Packages/com.victoria.citymode.contracts/Tests/Editor.meta
3d/unity/Packages/com.victoria.citymode.contracts/Tests/Editor/Victoria.CityMode.Contracts.EditorTests.asmdef
3d/unity/Packages/com.victoria.citymode.contracts/Tests/Editor/Victoria.CityMode.Contracts.EditorTests.asmdef.meta
3d/unity/Packages/com.victoria.citymode.contracts/Tests/Editor/CityModeContractCellIdTests.cs
3d/unity/Packages/com.victoria.citymode.contracts/Tests/Editor/CityModeContractCellIdTests.cs.meta
3d/unity/Packages/com.victoria.citymode.presentation/Runtime/CityModePresentationHost.cs
3d/unity/Packages/com.victoria.citymode.presentation/Tests/Editor/CityModePresentationHostTests.cs
3d/unity/Packages/com.victoria.citymode.presentation/Tests/Editor/CityModeTransitionShellTests.cs
3d/unity/Packages/com.victoria.citymode.presentation/Tests/PlayMode/CityModeTransitionPlayModeTests.cs
3d/unity/Packages/manifest.json

Précisions :
- le paquet `com.victoria.citymode.presentation` entre au périmètre parce qu'il
  lit `Context.cityId` (nom de l'objet racine) et que ses tests construisent
  des messages : sans lui, le projet ne compile plus. Dans ses trois fichiers
  de tests, **seuls les noms et les valeurs d'identité changent**
  (`cityId`/`mapCellId` → `cell_id`, `openedCityId` → `openedCellId`,
  `"city:42"`/`"cell:42"` → `42`…) : chaque assertion reste, le nombre de cas
  reste (3 + 6 en EditMode, 5 en PlayMode), aucune tolérance ne s'élargit ;
- `3d/unity/Packages/manifest.json` : **seulement** l'ajout d'une clé
  `"testables"` nommant les deux paquets, et seulement si SC3 montre que le
  lanceur de tests ne voit pas leurs assemblages sans elle. Sinon, il ne change
  pas ;
- `3d/unity/README.md` : seulement la section « Ce que la vue ville attend du
  moteur », réécrite en quelques lignes ;
- `FORGEHISTORY_CITY_MODE_CONTRACT.md` : les trois mentions (tableau
  « Identité », matrice d'autorité, section « Lecture ») ; la mention
  historique du labo se dit sans le nom de champ (« un identifiant de ville
  fixe, 1001 »).

## Conditions de succès

### SC1 — Le schéma exige `cell_id` et refuse `cityId` (VPS ou PC)
```
python3 -m pytest jeu/ville/tests -q        # py sur le PC
```
`test_contrat_cell_id.py` n'importe que la bibliothèque standard (pas de
`jsonschema` : ni la CI ni `sim/` ne l'installent). Il lit le schéma et les
exemples, et juge chaque message **d'après le schéma lu**, jamais d'après une
liste de clés recopiée dans le test : un message est refusé s'il lui manque une
clé de `required`, s'il porte une clé absente de `properties` alors que
`additionalProperties` vaut `false`, ou si `cell_id` n'est pas un entier ≥ 0
(un booléen n'est pas un entier). Les exemples sont associés à leur définition
(`launchContext` → `CityLaunchContext`, `snapshot` → `CitySnapshotEnvelope`,
`intent` → `CityIntentEnvelope`, les deux reçus → `CityIntentReceipt`). Il
vérifie :
- chacune des quatre définitions a `cell_id` dans `required`, de type
  `integer`, `minimum` 0, et `additionalProperties: false` ; aucune ne connaît
  `cityId` ni `mapCellId` ;
- les cinq exemples passent, et portent tous le même `cell_id`, qui est une
  cellule de `jeu/data/world-1400.json` (la liste des `cell_id` est lue dans le
  fichier ; une liste vide fait échouer le test) ;
- pour chaque exemple : sans `cell_id` → refusé ; avec `cityId` ajouté →
  refusé ; avec `mapCellId` ajouté → refusé ; avec `cell_id = -1`, `"1175"`
  ou `true` → refusé.

Contre-épreuve, dans le même fichier : sur une copie en mémoire du schéma où
`cityId` est rendu à `properties` et `cell_id` retiré de `required`, le même
juge **accepte** un message avec `cityId` et sans `cell_id`. Cela prouve que le
refus vient du schéma et non du juge. À la main, avant la PR : rendre `cityId`
au schéma fait rougir la suite.

### SC2 — Plus aucune identité de ville dans le contrat
```
grep -rniE "city_?id" jeu/ville 3d/unity/Packages/com.victoria.citymode.contracts 3d/unity/Packages/com.victoria.citymode.presentation
grep -rn "mapCellId" jeu/ville 3d/unity/Packages/com.victoria.citymode.contracts 3d/unity/Packages/com.victoria.citymode.presentation
```
Les deux ne rendent rien (code 1). La recherche est insensible à la casse :
elle attrape aussi `CityId`, `openedCityId` et `selectedCityId`. Contre-épreuve :
sur `master`, la première rend plus de trente lignes.

### SC3 — Unity compile, et les tests EditMode passent en batch (PC)
Le workflow `unity` (poussée sur la branche) est vert : le projet s'ouvre et
compile, sans aucune `error CS`. Puis, sur le PC, avec la version de
`ProjectSettings/ProjectVersion.txt` :
```
Unity.exe -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode `
  -assemblyNames "Victoria.CityMode.Contracts.EditorTests;Victoria.CityMode.Presentation.EditorTests" `
  -testResults <temp>\citymode-editmode.xml -logFile <temp>\citymode-editmode.log
```
(sans `-quit`, qui interrompt `-runTests`). Le code de sortie vaut 0. Le XML
dit `failed="0"` et **chaque** assemblage y compte au moins un cas. La
présentation en compte au moins 9, les contrats autant que
`CityModeContractCellIdTests.cs` en déclare. Zéro cas pour un assemblage est un
échec, jamais un succès (c'est alors qu'on ajoute `testables`).

`CityModeContractCellIdTests.cs` porte les cas de l'invariant, dans le paquet
qui le porte :
- un contexte, une photographie, une intention et un reçu valides, avec
  `cell_id = 0` puis `1175`, passent ;
- un `cell_id` laissé à sa valeur par défaut (`-1`) est refusé avec
  `InvalidCellId`, pour chacun des quatre messages ;
- une photographie, une intention ou un reçu dont le `cell_id` diffère de celui
  du contexte ou de l'intention est refusé par la session (`InvalidCellId`) ;
- `JsonUtility.ToJson` d'un contexte contient `"cell_id":1175` et ne contient
  ni `cityId` ni `mapCellId`.

Contre-épreuve, jouée à la main et dite dans la PR : retirer la garde
`cell_id < 0` de `CityModeContractValidation` fait rougir au moins quatre cas ;
la remettre les fait repasser.

### SC4 — Les tests PlayMode de la présentation passent toujours (PC)
```
Unity.exe -batchmode -projectPath 3d/unity -runTests -testPlatform PlayMode `
  -assemblyNames "Victoria.CityMode.Presentation.PlayModeTests" -testResults <temp>\citymode-playmode.xml
```
Code 0, `failed="0"`, 5 cas au moins. Le fichier n'a changé que par les noms
de clés (SC2) ; ses assertions restent.

### SC5 — Rien d'autre ne régresse
```
python3 -m pytest jeu -q        # py -m pytest jeu -q sur le PC (pc\Tests.cmd)
git diff --name-only origin/master...HEAD
```
La suite du jeu reste verte. Le diff ne nomme que des chemins du périmètre
(plus ce brief).

## Hors périmètre
- le service local et le panneau du jalon 1 (`/lieu`, `/monde`, `/intention`),
  la lecture de `sim/` depuis Unity : ce sont d'autres lots du jalon ;
- toute modification de `jeu/sim/` et de `MODELE.md` : le modèle a déjà raison ;
- le lieu comme subdivision de la cellule, et son identité dérivée de
  `cell_id` : jalon 3 ;
- le reste du contrat (politique de temps, révisions, SHA-256, codes
  d'erreur autres que 3), et la renumérotation des codes d'erreur ;
- `CITY_MODE_HOST_API.md`, `UNITY_RENDER_DEPENDENCY_MATRIX.md`, les fichiers
  JSON de portage d'assets, `docs/OBJECTIF.md` ;
- `3d/archives/` (le labo endormi garde son `cityId`) ;
- brancher `jeu/ville/tests` dans `.github/workflows/tests.yml` : ce geste
  appartient au propriétaire, en mode direct. La PR le signale, sans le faire ;
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
