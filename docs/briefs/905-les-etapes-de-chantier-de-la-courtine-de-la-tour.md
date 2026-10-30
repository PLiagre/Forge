# Lot #905 — Les étapes de chantier de la courtine, de la tour et de la porte entrent dans le kit du désert
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
Le kit du désert sait montrer l'enceinte en chantier : `rempart_pise_10m`, `tour_ksar_0` et `porte_ksar` gagnent chacun deux étapes, d'abord les piquets et le cordeau, puis la terre banchée à mi-hauteur sous ses perches. Elles sont posées sur l'emprise de la pièce finie, déclarées dans `chantiers` du catalogue et livrées à Unity en prefabs à trois LOD, comme les étapes du lot #269.

## Le joueur
Lot de fond, découpé de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues ». Il prépare le geste du J4 de `CAP.md` : le joueur **trace son enceinte**, et l'écran du jalon montre « son enceinte ; ses chantiers ». Aujourd'hui, une enceinte en chantier coûte des milliers de journées (19 200 pour le carré de ±80 m de Biskra, lot #904), mais le kit n'a rien pour la montrer avant qu'elle soit finie. Après ce lot, chaque pièce du mur a son allure de chantier : le tracé au cordeau, puis la terre qui monte entre les banches. Le sous-lot de #417 qui dessine le mur lira `PlanLu.Enceinte` (lot #904) et posera ces étapes selon le travail fourni. Le joueur verra alors son mur monter journée après journée, et pèsera mieux « des murs, ou des maisons ». Ici, il ne le voit que dans la galerie de la photo.

## Règle du monde
Sans objet : lot d'outil et de vue. `sim/` n'est pas touché. L'enceinte du monde (`jeu/sim/MODELE.md`, « Le plan du bourg ») ne change pas. Les formes sont de **fidélité 2** (plausibles, jamais sourcées), comme tout le kit. Une chose est vraie au niveau 1 : le pisé se monte par levées, entre des banches de bois.

Ce qui existe sur master, vérifié le 30/10/2026 :
- `kit.py` : `CHANTIERS`, `ETAPES`, `suite`, `NOUVEAUX`, `REFERENCES`, les plafonds, `juger_chantiers` (emprise, hauteurs, suite), `juger_planche` (lot 270), et 21 contre-épreuves. Tout se dérive de `CHANTIERS`, y compris les rangées de la planche Unity (`rangees_planche`).
- `fabriquer.py` écrit `chantiers` d'après `kit.CHANTIERS`, à ses deux écritures. `inspecter_kit.py` range tout ce qui commence par `chantier` dans une même planche. `DesertKit.cs` mesure `references` et photographie les rangées de `selection.json`. Aucun de ces trois fichiers n'a besoin de changer.
- Les prefabs de `rempart_pise_10m`, `tour_ksar_0` et `porte_ksar` existent, chacun avec son LODGroup. Mesures du catalogue : le rempart fait 10,07 × 3,34 m sur 10,89 m ; la tour 7,2 × 7,2 m sur 16,60 m ; la porte 15,9 × 7,7 m sur 15,82 m. La façade de chacune regarde −Y.
- `chantier_piquets(emprise)` sert tel quel sur ces trois emprises (16, 16 et 24 piquets). En revanche, `chantier_murs` monte une boîte creuse avec une porte en façade : c'est juste pour une maison, faux pour un rempart plein ou une porte qu'on traverse.

Ce que le lot fait :
- **`assets.py`** :
  - `PORTE_PASSAGE = 4.4`, au niveau du module. `gate()` le lit à la place de son `w = 4.4` : c'est la seule ligne de `gate()` qui change, et sa sortie reste identique au sommet près.
  - Un builder neuf, `chantier_massif(emprise, passage=0.0)` : la levée de pisé en cours. Il pose :
    - une assise de grès basse (`gres_ocre`, 1,2 m au plus) ;
    - un massif de `pise` monté à la moitié de la hauteur finie, avec un léger fruit, juste en dedans des perches. Si `passage > 0`, il fait deux massifs, de part et d'autre de x = 0, et laisse libre une bande de `passage` m sur toute la profondeur ;
    - au sommet de chaque massif, une banche : des planches (`bois_sombre`) sur les deux faces ±Y, tenues par des montants (`bois_palmier`) tous les 1,5 m environ ;
    - une perche (`stipe_palmier`) à chaque coin de l'emprise, à 0,65 fois la hauteur finie, liée aux autres en tête ;
    - une échelle contre la face +Y, dans l'emprise, son pied à 3 cm au-dessus du sol, hors du passage.

    LOD0 : banches, montants et échelle. LOD1 : les liens de tête en plus de la silhouette. LOD2 : la silhouette seule (assise, massifs, perches). Le builder n'utilise aucun matériau neuf, met l'origine au sol et la façade vers −Y.
  - Dans `jobs()`, à la fin, après les étapes du lot 269 et dans cet ordre : `chantier_rempart_pise_10m_piquets`, `_murs`, `chantier_tour_ksar_0_piquets`, `_murs`, `chantier_porte_ksar_piquets`, `_murs`, tous de type `batiment`.
    - Les piquets : `chantier_piquets(emprise(b))`.
    - Les murs : `chantier_massif(emprise(b))`, et pour la porte `chantier_massif(emprise(gate), PORTE_PASSAGE)`.
    - `b` vaut `wall`, `lambda: tower(0)` ou `gate`.
- **`kit.py`** :
  - `ENCEINTE = ['rempart_pise_10m', 'tour_ksar_0', 'porte_ksar']` et `CHANTIERS = [les trois du lot 269] + ENCEINTE`. `NOUVEAUX` et `REFERENCES` s'en déduisent : 14 modules, et 4 références (`maison_pise_0` puis les trois pièces).
  - Les plafonds des étapes de `ENCEINTE` : piquets (600, 400, 120), murs (1 600, 800, 320). Ceux du lot 269 ne changent pas.
  - Les contre-épreuves de SC3.
- **`README.md`** : quelques lignes sous « Ajouter un module au kit : `kit` » (les étapes de l'enceinte, `chantier_massif`, le passage de la porte).

## Périmètre
3d/local3d/desert/assets.py
3d/local3d/desert/kit.py
3d/local3d/desert/README.md
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot905.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot905.cs.meta
3d/local3d/desert/sorties/bibliotheque/catalogue.json
3d/local3d/desert/sorties/kit/selection.json
3d/local3d/desert/sorties/kit/unity-kit.json
3d/local3d/desert/sorties/kit/jugement.json
3d/local3d/desert/sorties/diagnostic/kit_ateliers.png
3d/local3d/desert/sorties/diagnostic/kit_chantiers.png
3d/local3d/desert/sorties/diagnostic/kit_chantiers_unity.png
3d/unity/Assets/ForgeLocal3D/Desert/Data/catalogue.json
3d/local3d/desert/sorties/bibliotheque/scierie.fbx
3d/local3d/desert/sorties/bibliotheque/four_pain_pise.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_maison_pise_0_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_maison_pise_0_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_scierie_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_scierie_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_four_pain_pise_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_four_pain_pise_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_rempart_pise_10m_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_rempart_pise_10m_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_tour_ksar_0_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_tour_ksar_0_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_porte_ksar_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_porte_ksar_murs.fbx
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
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_rempart_pise_10m_piquets.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_rempart_pise_10m_piquets.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_rempart_pise_10m_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_rempart_pise_10m_murs.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_tour_ksar_0_piquets.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_tour_ksar_0_piquets.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_tour_ksar_0_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_tour_ksar_0_murs.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_porte_ksar_piquets.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_porte_ksar_piquets.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_porte_ksar_murs.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/chantier_porte_ksar_murs.fbx.meta
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
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_rempart_pise_10m_piquets.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_rempart_pise_10m_piquets.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_rempart_pise_10m_murs.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_rempart_pise_10m_murs.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_tour_ksar_0_piquets.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_tour_ksar_0_piquets.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_tour_ksar_0_murs.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_tour_ksar_0_murs.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_porte_ksar_piquets.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_porte_ksar_piquets.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_porte_ksar_murs.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/chantier_porte_ksar_murs.prefab.meta
docs/briefs/905-les-etapes-de-chantier-de-la-courtine-de-la-tour.md

Précisions :
- On écrit à la main **quatre fichiers et une méta** : `assets.py`, `kit.py`, `README.md`, `Lot905.cs` (Unity génère son `.meta`).
  - Tous les autres sont refaits par `py 3d/local3d/atelier_desert.py kit`. On ne les édite pas à la main, et ceux qui sortent identiques ne figurent pas dans le diff.
  - Les FBX et les PNG passent par LFS : après la poussée, vérifier qu'ils sont sur le serveur.
- Budget : 75 lignes d'`assets.py`, 35 de `kit.py`, 10 de `README.md`, 60 de `Lot905.cs`, et les JSON refaits.
- Interdits, en particulier :
  - les prefabs, FBX et matériaux des anciens modules, dont `rempart_pise_10m`, `tour_ksar_0`, `porte_ksar` et `maison_pise_0`, mesurés en lecture seule ;
  - les builders existants (`wall`, `tower`, `chantier_piquets`, `chantier_murs`…), sauf la seule ligne `w` de `gate()` ;
  - `fabriquer.py`, `inspecter_kit.py`, `atelier_desert.py`, `DesertKit.cs`, `DesertBuilder.cs`, `VillageV2Builder.cs`, `KitDesBatiments.cs` et sa ressource ;
  - toute scène `*.unity`, `Kit_Desert.blend`, `sorties/villages/` et `jeu/`.

## Conditions de succès
Sur le PC, depuis la racine, Unity fermé :

```powershell
py 3d/local3d/atelier_desert.py kit
```

La commande garde le déroulé des lots 266, 269 et 270 : empreintes, Blender, planches, Unity, vérificateur, puis jugement. Elle écrit `sorties/kit/jugement.json` et sort en code non nul au premier défaut. Chaque contre-épreuve rejoue `kit.juger` sur une copie déréglée de ses entrées. Elle doit rougir **avec son étiquette** ; sinon, c'est un défaut. Les 21 contre-épreuves existantes restent telles quelles et rougissent toujours.

- **SC1 — Les étapes de l'enceinte sont des modules du kit.** Unity a mesuré exactement les 14 modules de `NOUVEAUX`, dans l'ordre, et exactement les 4 références. Les contrôles `budget`, `origine`, `lod` et `materiau` passent sur les six étapes neuves : trois LOD strictement décroissants, égaux au catalogue et sous leur plafond, LOD0 au sol à 1 cm près. Blender refuse une étape au-dessus de son plafond.
  - *Contre-épreuve* `tour_hors_references` (`echantillon`) : `tour_ksar_0` retirée des `references` d'une copie du rapport.
- **SC2 — Chaque étape est posée sur l'emprise de sa pièce finie, et monte avec le chantier.** C'est `juger_chantiers` sans retouche, appliqué aux trois pièces :
  - chaque bord mesuré par Unity est à 0,3 m au plus de celui de la pièce finie ;
  - les piquets montent à 1,2 m au plus, sous les murs ;
  - les murs montent entre 0,5 et 0,8 fois la hauteur finie.
  - *Contre-épreuves* :
    - `porte_decalee` (`emprise`) : `z_min` et `z_max` de `chantier_porte_ksar_murs` + 2 m ;
    - `rempart_trop_bas` (`hauteur`) : `y_max` de `chantier_rempart_pise_10m_murs` porté à 0,4 fois celui de la référence `rempart_pise_10m`.
- **SC3 — La suite est déclarée.** `chantiers` des deux catalogues porte exactement les six bâtiments de `CHANTIERS`, chacun avec `kit.suite(fini)`. Les autres fiches, `materials` et `schema` sont à l'identique (défaut `catalogue`).
  - *Contre-épreuve* `porte_sans_piquets` (`suite`) : `chantier_porte_ksar_piquets` retirée de la suite de `porte_ksar`.
- **SC4 — Les planches montrent les trois pièces.** La planche Unity a 6 rangées × 3 colonnes, les 18 cases à leur place, aucune réduite à son fond. `kit_chantiers.png` n'est pas uniforme.
  - *Contre-épreuve* `case_tour_absente` (`planche`) : la case `chantier_tour_ksar_0_murs` retirée du rapport.
  - Le codeur regarde les deux images et dit dans la PR ce qu'il y voit : le cordeau autour de chaque pièce ; les banches à mi-hauteur ; le passage de la porte libre entre ses deux massifs ; les perches et l'échelle.
- **SC5 — Rien d'autre ne bouge.** Les empreintes avant et après sont égales, prefabs des quatre références compris. `verifier` reste vert. Les contre-épreuves `scene_touchee`, `verification_rouge` et `ancien_module_change` rougissent toujours.
- **SC6 — La galerie se pose dans Unity.** Les deux commandes de la Photo sortent en code 0, chacune avec son rapport. Le rapport de la photo compte 9 pièces, celui de la contre-épreuve 3. Le scénario échoue, en nommant sa cause, si : une rangée manque à `selection.json`, un prefab est absent, une pièce n'a pas de renderer au LOD0, ou une pièce sort du cadre.

## Hors périmètre
- Poser les étapes dans la capitale selon le travail fourni à l'enceinte, et inscrire l'enceinte dans `KitDesBatiments` : le sous-lot de #417 qui dessine le mur et ses portes.
- Les étapes de `tour_ksar_1` et `tour_ksar_2`, d'un angle de rempart, ou d'une porte à une autre largeur que celle du kit.
- Des matériaux, des textures ou des collisions neufs.
- `Kit_Desert.blend` : il les recevra à la prochaine reconstruction complète, que ce lot ne lance pas.
- Toute règle de `sim/` (coût, bras, assise de 6 m de l'enceinte).

## Photo
La galerie des étapes de chantier des trois pièces, posée dans le désert de la capture. Trois rangées : courtine, tour, porte. Trois colonnes : piquets, levée à mi-hauteur, pièce finie. On y voit le mur passer du cordeau à la terre banchée, puis aux merlons.

`Lot905.cs` : un scénario `[ScenarioDeCapture(905, "galerie-enceinte")]`, serré comme `Lot779`, qui échoue en nommant sa cause.
1. Il refuse un `lot905-rapport.json` déjà présent dans `Capture.DossierDesCaptures`.
2. Il lit `../local3d/desert/sorties/kit/selection.json` (chemin relatif au projet, comme `DesertKit`) avec `JsonUtility`, et prend les rangées `planche` dont le `fini` est `rempart_pise_10m`, `tour_ksar_0` ou `porte_ksar`, dans cet ordre. Chacune doit porter 3 étapes finissant par son `fini`. Avec `-forge905FinisSeuls`, il ne garde que la colonne du fini.
3. Il charge chaque prefab par `AssetDatabase.LoadAssetAtPath("Assets/ForgeLocal3D/Desert/Prefabs/<id>.prefab")`, l'instancie sous une racine « Lot 905 : galerie de l'enceinte », sans rotation, et force son LOD0 (`LODGroup.ForceLOD(0)`).
   - Pas d'une colonne : la plus grande largeur des trois pièces finies + 6 m. Pas d'une rangée : leur plus grande profondeur + leur plus grande hauteur. Les deux se tirent des enveloppes des renderers.
   - La galerie se pose au bord de la ville de 1400, du côté le plus plat, à 20 m de la dernière maison (méthode de `Lot779`). Chaque pièce est posée à la hauteur du terrain sous son centre.
4. La caméra passe par `DesertCityCamera.Poser` (ville et marcheur en `automatique`), à 35° d'inclinaison, avec le cap qui regarde les façades (+Z des prefabs). Elle recule par pas de 6 % jusqu'à ce que les huit coins de l'enveloppe de chaque pièce tiennent entre 0,02 et 0,98 de l'image, en 1600 × 900. Puis dix images de pose.
5. Il écrit `lot905-rapport.json` : pour chaque pièce, son id, sa rangée, sa colonne, sa position, son enveloppe et ses renderers actifs au LOD0 ; puis le nombre de pièces. Ensuite `Debug.Log("CAPTURE_905 …")`.

La photo, puis sa contre-épreuve (les trois pièces finies seules, sans leurs étapes, rapport à 3 pièces) :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 905 -forgeCaptures 3d/unity/Temp/lot905-photo -logFile 3d/unity/Temp/lot905-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 905 -forgeCaptures 3d/unity/Temp/lot905-finis-seuls -forge905FinisSeuls -logFile 3d/unity/Temp/lot905-finis-seuls.log
```
