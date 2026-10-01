# Lot #270 — La planche Unity des neuf étapes de chantier
Jalon : J4 · Machine : pc · Taille prévue : 200 lignes

## But
La commande `kit` fait photographier par Unity les trois chantiers du kit du désert : la maison, la scierie et le four, chacun à ses trois étapes (piquets, murs, fini), côte à côte sur une seule planche. La photo est prise dans une scène jamais enregistrée. Python juge la planche case par case, et les scènes du ksar n'en gardent aucune trace.

## Règle du monde
Sans objet : c'est un lot de vue. `sim/` n'est pas touché, et aucune section de `jeu/sim/MODELE.md` n'en découle. Les formes restent de **fidélité 2**, comme tout le kit (`3d/local3d/desert/recette.json`).

Le lot sert l'écran du jalon J4 de `CAP.md` : « le chantier qui prend des bras aux champs ». Le lot 269 a fait entrer les étapes dans Unity, mais seul Blender les a montrées (`kit_chantiers.png`). Ce lot fait voir ce qu'Unity affichera vraiment : ses prefabs, ses matériaux, son rendu. Il ne s'appuie sur rien que J2 ou J3 doivent livrer. La commande `kit`, `kit.py`, `DesertKit.cs`, les six prefabs d'étape et les trois prefabs finis sont déjà sur master.

Ce qui existe, vérifié sur master le 01/10/2026 :

- `kit.py` porte :
  - `CHANTIERS = ['maison_pise_0', 'scierie', 'four_pain_pise']` et `suite(fini)`, qui rend `[piquets, murs, fini]` ;
  - `NOUVEAUX` (huit modules) et `REFERENCES` (`['maison_pise_0']`) ;
  - `ecart_pixels`, `juger`, `juger_chantiers` et treize contre-épreuves.
- `atelier_desert.py kit_ateliers()` :
  - relève les empreintes par `proteges()`, c'est-à-dire `Desert/Scenes/*.unity`, les anciens prefabs, FBX et `.mat`, et `sorties/villages/` ;
  - écrit `sorties/kit/selection.json` (`modules`, `references`) ;
  - lance `ForgeLocal3D.DesertKit.Start` en mode batch, puis le vérificateur des scènes, puis juge.
- `DesertKit.Start` crée et mesure les prefabs dans la scène vide par défaut du mode batch. Il n'ouvre ni n'enregistre aucune scène.
- `CitadelPlayCheck.Capture(camera, chemin, largeur, hauteur)` rend une caméra URP dans une image PNG et rend ses pixels.
- `routes.ECART_CAPTURE = 6` est le seuil d'une image uniforme, déjà repris par le lot 266.

Ce que le lot fait :

- **Python choisit ce qu'on photographie.** `selection.json` gagne une clé `planche` : une rangée par bâtiment de `kit.CHANTIERS`, dans cet ordre, au format `{"fini": …, "etapes": kit.suite(fini)}`. La clé est dérivée par Python, jamais écrite à la main.
- **Unity photographie** : une méthode `Planche` dans `DesertKit.cs`, appelée à la fin de `Start`, après les mesures.
  - Elle ouvre une scène neuve par `EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single)`. Elle ne l'enregistre jamais.
  - Elle y crée une lumière directionnelle et une caméra au fond uni (`CameraClearFlags.SolidColor`), sans sol.
  - Elle instancie chacun des neuf prefabs de `Desert/Prefabs/`, LOD0 forcé (`LODGroup.ForceLOD(0)`).
  - Elle rend **une case par prefab**. Seul ce prefab est actif pendant le rendu, et la case est rendue par `CitadelPlayCheck.Capture`.
  - Le cadrage est **le même pour les trois cases d'une rangée** : il est calé sur l'enveloppe du bâtiment fini, et le point de vue est de trois quarts, depuis la façade. Ainsi les étapes d'un même bâtiment se comparent à la même échelle.
  - Elle assemble les neuf cases en une image de 3 colonnes (piquets, murs, fini) sur 3 rangées (maison, scierie, four). Elle l'écrit dans `sorties/diagnostic/kit_chantiers_unity.png`, puis supprime les fichiers de case intermédiaires.
  - Le rapport `unity-kit.json` gagne `planche`, avec :
    - `chemin`, `largeur` et `hauteur` de l'image ;
    - `fond` : la couleur du fond, en RGB 0–255 ;
    - `scene_chemin` : le chemin de la scène active au moment du rendu, vide si elle n'a jamais été enregistrée ;
    - `cases` : pour chaque case, son `id`, sa `rangee`, sa `colonne`, son rectangle `x`, `y`, `largeur`, `hauteur` et `renderers`.
  - Le rectangle est en pixels de l'image PNG, origine en haut à gauche, comme Python la lit.
  - `renderers` est le nombre de renderers actifs du LOD0 au moment du rendu, -1 s'il n'est pas mesuré.
  - Unity mesure, Python juge.
- **Python juge la planche** : une fonction `juger_planche` dans `kit.py`, appelée par `juger`. Elle reçoit les pixels de l'image dans `entrees['planche']`, sous forme de tableau hauteur × largeur × 3, ou `None` si l'image manque. Le jugement **rejoue la mesure** sur ces pixels : chaque contre-épreuve dérègle une copie de l'image, pas un nombre déjà calculé.
  - Le nouveau défaut a l'étiquette `planche`, ajoutée à `ETIQUETTES`.
- **La commande** :
  - efface `kit_chantiers_unity.png` avant de lancer Unity, pour qu'une ancienne image ne compte jamais ;
  - lit l'image avec PIL en RGB ;
  - passe ses pixels au jugement ;
  - affiche l'écart-type de chaque case.
- **`jugement.json`** gagne une clé `planche` : pour chaque case, son `id`, sa place et son écart-type. Les pixels n'y entrent pas.

## Périmètre
3d/local3d/desert/kit.py
3d/local3d/atelier_desert.py
3d/local3d/desert/README.md
3d/unity/Assets/ForgeLocal3D/Editor/DesertKit.cs
3d/local3d/desert/sorties/diagnostic/kit_chantiers_unity.png
3d/local3d/desert/sorties/diagnostic/kit_ateliers.png
3d/local3d/desert/sorties/diagnostic/kit_chantiers.png
3d/local3d/desert/sorties/kit/selection.json
3d/local3d/desert/sorties/kit/unity-kit.json
3d/local3d/desert/sorties/kit/jugement.json
3d/local3d/desert/sorties/bibliotheque/catalogue.json
3d/local3d/desert/sorties/bibliotheque/scierie.fbx
3d/local3d/desert/sorties/bibliotheque/four_pain_pise.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_maison_pise_0_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_maison_pise_0_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_scierie_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_scierie_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_four_pain_pise_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_four_pain_pise_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Data/catalogue.json
3d/unity/Assets/ForgeLocal3D/Desert/Models/scierie.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/scierie.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/four_pain_pise.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/four_pain_pise.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_maison_pise_0_piquets.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_maison_pise_0_piquets.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_maison_pise_0_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_maison_pise_0_murs.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_scierie_piquets.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_scierie_piquets.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_scierie_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_scierie_murs.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_four_pain_pise_piquets.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_four_pain_pise_piquets.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_four_pain_pise_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_four_pain_pise_murs.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/scierie.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/scierie.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/four_pain_pise.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/four_pain_pise.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_maison_pise_0_piquets.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_maison_pise_0_piquets.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_maison_pise_0_murs.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_maison_pise_0_murs.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_scierie_piquets.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_scierie_piquets.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_scierie_murs.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_scierie_murs.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_four_pain_pise_piquets.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_four_pain_pise_piquets.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_four_pain_pise_murs.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_four_pain_pise_murs.prefab.meta
docs/briefs/270-la-planche-unity-des-neuf-etapes-de-chantier.md

Précisions sur ce périmètre :

- On écrit à la main **quatre fichiers seulement** : `kit.py`, `atelier_desert.py`, `DesertKit.cs` et `README.md`.
  - Tous les autres sont refaits par la commande `kit`, qui rejoue Blender et Unity comme au lot 269. On ne les édite pas à la main.
  - S'ils sortent identiques, ils ne figurent pas dans le diff.
  - Les FBX et les PNG passent par LFS. Après la poussée, vérifier qu'ils sont sur le serveur.
- `DesertKit.cs` :
  - on ajoute la méthode `Planche`, la classe de la planche dans le rapport et le champ `planche` de la sélection ;
  - `Measure` et la création des prefabs ne changent pas.
- `atelier_desert.py` :
  - la clé `planche` de `selection.json` ;
  - la lecture de l'image et son passage au jugement ;
  - l'affichage des cases ;
  - `proteges()` relève aussi **toute scène du projet**, `unity/Assets/**/*.unity`, en plus de `Desert/Scenes/*.unity`. Le glob s'élargit, il ne se resserre pas.
- `README.md` : quelques lignes sous « Ajouter un module au kit : `kit` », qui disent ce que montre la planche Unity et ce que le jugement refuse.

Tout autre chemin est interdit, en particulier :

- les scènes `*.unity`, toutes ;
- les prefabs, FBX et matériaux des 49 anciens modules, dont `maison_pise_0.prefab`, chargé en lecture seule ;
- `inspecter_kit.py`, `assets.py` et `fabriquer.py` ;
- `CitadelPlayCheck.cs`, qu'on appelle tel qu'il est ;
- `DesertBuilder.cs` et `VillageV2Builder.cs` ;
- `Kit_Desert.blend` et `sorties/villages/` ;
- `jeu/`.

## Conditions de succès
Toutes se lisent dans une seule commande, jouée sur le PC depuis la racine, Unity fermé :

```powershell
py 3d/local3d/atelier_desert.py kit
```

La commande garde son déroulé du lot 269 et y ajoute la planche. Elle écrit `sorties/kit/jugement.json` et sort en code non nul au premier défaut.

Chaque contre-épreuve rejoue `kit.juger` sur une **copie** déréglée de ses entrées, et entre dans le dictionnaire `contre_epreuves`. Si une contre-épreuve ne rougit pas, **ou rougit sans l'étiquette attendue**, c'est un défaut. Les **treize contre-épreuves des lots 266 et 269 restent telles quelles** et doivent toujours rougir. Le lot ajoute les six siennes, ci-dessous.

- **SC1 — La planche existe et n'est pas uniforme.**
  - L'image `kit_chantiers_unity.png`, effacée avant le passage d'Unity, est relue après.
  - Ses dimensions sont égales à `largeur` × `hauteur` du rapport.
  - Son `ecart_pixels` est au moins `ECART_CAPTURE`.
  - Une image absente, un rapport sans `planche`, ou des dimensions différentes donnent un défaut `planche`.
  - *Contre-épreuve « planche absente »* (`contre_epreuves.planche_unity_absente`) : `entrees['planche']` mis à `None` doit donner un défaut `planche`.
  - *Contre-épreuve « planche uniforme »* (`contre_epreuves.planche_unity_uniforme`) : une image de mêmes dimensions, toute de la couleur `fond`, doit donner un défaut `planche`.
- **SC2 — Les neuf cases sont celles des chantiers, à leur place.**
  - Les cases du rapport sont **exactement**, rangée par rangée, `kit.suite(fini)` pour chaque `fini` de `kit.CHANTIERS`. Les rangées suivent l'ordre de `CHANTIERS`, et les colonnes celui de la suite : 9 cases aujourd'hui, nombre dérivé, au moins une.
  - Chaque case a au moins un renderer actif.
  - Les rectangles des cases tiennent dans l'image et ne se chevauchent pas.
  - Sinon, c'est un défaut `planche`.
  - *Contre-épreuve « case retirée »* (`contre_epreuves.case_absente`) : la case de `chantier_four_pain_pise_piquets`, retirée de `cases` dans une copie du rapport, doit donner un défaut `planche`.
- **SC3 — Aucune étape ne manque à l'image.**
  - Pour chaque case, l'`ecart_pixels` des pixels de son rectangle est au moins `ECART_CAPTURE`. Une case qui n'a que son fond est une étape manquante : défaut `planche`, qui nomme la case.
  - *Contre-épreuve « étape manquante »* (`contre_epreuves.etape_manquante_planche`) : dans une copie des pixels, le rectangle de `chantier_scierie_murs` est repeint de la couleur `fond`. Le jugement doit donner un défaut `planche`. Les huit autres cases restent intactes.
- **SC4 — La scène de la planche n'est jamais enregistrée, et le ksar est intact.**
  - `scene_chemin` est vide.
  - Les empreintes après égalent les empreintes avant. Elles couvrent maintenant toute scène `.unity` du projet : une scène apparue n'importe où sous `Assets/` est un défaut `empreinte`.
  - `verifier` reste vert, rejoué par la commande comme au lot 266.
  - Les contre-épreuves `scene_touchee` et `verification_rouge` restent.
  - *Contre-épreuve « scène enregistrée »* (`contre_epreuves.scene_enregistree`) : `scene_chemin` mis à `Assets/ForgeLocal3D/Desert/Scenes/Planche.unity` dans une copie du rapport doit donner un défaut `empreinte`.
  - *Contre-épreuve « scène apparue »* (`contre_epreuves.scene_apparue`) : une empreinte `3d/unity/Assets/Planche.unity` ajoutée aux empreintes après doit donner un défaut `empreinte`.
- **SC5 — Rien de ce que les lots 266 et 269 jugeaient ne régresse.**
  - Les défauts et contre-épreuves de `juger` et de `juger_chantiers` restent tels quels : budget, origine, LOD, matériaux, catalogue, emprise, hauteurs, suite, et les deux planches Blender.
  - Un lot n'assouplit aucun contrôle : il ajoute les siens.
- **SC6 — Ce qu'on voit.**
  - Le codeur ouvre `kit_chantiers_unity.png` lui-même et dit dans la PR ce qu'il y voit, rangée par rangée :
    - les piquets et le cordeau ;
    - les murs à mi-hauteur, les perches, les planches et l'échelle ;
    - le bâtiment fini ;
    - les trois cases d'une rangée à la même échelle ;
    - les matériaux d'Unity, sans rose de matériau manquant.
  - S'il voit un défaut que le jugement laisse passer, il le dit dans la PR.

## Hors périmètre
- Choisir quelle étape montrer selon l'avancement d'un chantier dans `sim/`, et le chantier comme intention ou comme travail pris aux champs : d'autres lots de J4.
- Poser une étape dans une scène du ksar ou de la ville, et toute reconstruction de scène.
- Changer les étapes elles-mêmes, leurs formes, leurs plafonds ou leur jugement d'emprise et de hauteur (lot 269).
- La planche Blender `kit_chantiers.png` et `inspecter_kit.py`, qui restent tels quels.
- Un sol, un ciel ou une lumière de scène réelle sur la planche : c'est un banc de contrôle, pas un rendu du jeu.
- Des étapes pour d'autres bâtiments que ceux de `kit.CHANTIERS`.
