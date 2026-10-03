# Lot #266 — La scierie et le four en pisé entrent dans le kit du désert, vérifiés jusqu'à Unity
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Le kit du désert gagne deux ateliers, une scierie et un four à pain en pisé. Ce sont les deux pièces que le joueur de J4 posera dans sa capitale. Blender les fabrique, et Unity les reçoit en prefabs à trois LOD, sans que rien ne bouge dans les 49 anciens modules ni dans les scènes du ksar.

## Règle du monde
Sans objet : c'est un lot d'outil et de vue. `sim/` n'est pas touché, et aucune section de `jeu/sim/MODELE.md` n'en découle. Les formes sont de **fidélité 2** (plausibles, jamais sourcées), comme tout le kit (`3d/local3d/desert/recette.json`).

Le lot sert le geste « pose un atelier (une scierie, un four) » du jalon J4 de `CAP.md`, qui dit aussi : « le kit du désert […] sert ici ». Il ne s'appuie sur rien que J2 ou J3 doivent livrer : le kit, la chaîne Blender → Unity (`fabriquer.py`, `VillageV2Builder.MakePrefab`) et les 45 matériaux du catalogue sont déjà sur master. Poser l'atelier comme intention dans `sim/` est un autre lot.

Ce qui existe, vérifié sur master le 30/09/2026 :

- `desert/assets.py` : `jobs()` liste 49 modules. `fabriquer.py library()` les reconstruit **tous** et réécrit `catalogue.json` (schéma 3 : `id`, `kind`, `triangles` par LOD, `bounds_min`, `bounds_max`) et `Kit_Desert.blend`.
- `atelier_desert.py fabriquer` reconstruit aussi les scènes du ksar dès que l'empreinte des sources change.
- Côté Unity, `DesertBuilder.Build` refait tous les prefabs **et** les scènes. Aucune commande n'ajoute un module seul.
- Aucun budget de triangles n'est écrit nulle part.

Ce que le lot fait :

- **Les deux modules**, dans `assets.py`, de type `batiment`, construits avec les primitives existantes et les niveaux d'ornement de `Mesh` : ornements au LOD0, silhouette seule au LOD2. Ils s'ajoutent **à la fin** de `jobs()`, pour qu'une reconstruction complète garde l'ordre du catalogue.
  - `scierie` : atelier de scieurs de long, d'environ 8 × 5 m sur 4,5 m de haut au plus. Un auvent de palmes sur poteaux de palmier, deux murets de pisé, un chevalet haut portant une grume, une scie de long, une pile de planches.
  - `four_pain_pise` : four en coupole de pisé sur socle, d'environ 3 × 3 m sur 2,5 m au plus. Une bouche en arc, un évent, un banc de brique crue, une réserve de bois.
  - Les deux modules ont l'origine au sol : le point le plus bas du LOD0 est à z = 0. Façade vers −Y, comme le reste du kit.
  - Ils n'utilisent **que des matériaux déjà au catalogue**, par exemple `pise`, `enduit_pise`, `brique_crue`, `bois_palmier`, `stipe_palmier`, `palme_seche`, `bois_sombre`, `fer_noir`, `poterie` ou `baie_sombre`. Aucune texture n'est ajoutée.
- **Un seul endroit pour le budget** : un nouveau fichier `desert/kit.py`, en Python pur, importable par Blender comme par Python.
  - Il tient la liste des nouveaux modules (`NOUVEAUX`).
  - Il tient leurs plafonds de triangles par LOD : `scierie` (2 400, 1 200, 400) et `four_pain_pise` (1 600, 800, 300).
  - Il tient la tolérance d'origine : 1 cm.
  - Il porte aussi le jugement.
  - Personne d'autre ne recopie ces nombres.
- **Blender, action `kit` de `fabriquer.py`** :
  - elle construit seulement les modules de `kit.NOUVEAUX`, par **le même chemin** que `library()` (chanfrein, `clean_mesh`, contrôle des trois LOD, export FBX). Ce chemin est factorisé en une fonction, sans changer ce qu'il produit ;
  - elle refuse un module qui dépasse son plafond, ou qui porte un matériau absent de la liste `materials` du catalogue ;
  - elle réécrit `catalogue.json` avec les enregistrements anciens repris tels quels, dans le même ordre, puis ceux des nouveaux modules. Un enregistrement déjà présent pour un nouveau module est remplacé : la commande se rejoue. La liste `materials` reste identique ;
  - elle ne touche ni `Kit_Desert.blend`, ni les FBX des anciens modules, ni les scènes.
- **Unity, `ForgeLocal3D.DesertKit.Start`** (nouveau script d'éditeur, en mode batch) :
  - il lit `sorties/kit/selection.json`, écrit par Python d'après `kit.NOUVEAUX` ;
  - il charge les matériaux **existants** de `Desert/Materials/<nom>.mat`, sans les recréer. Un matériau manquant est noté dans le rapport ;
  - il crée chaque prefab par `VillageV2Builder.ImportPrefab`, une méthode publique **ajoutée** qui fixe `Root` et `Desert`, puis appelle `MakePrefab` tel quel. Aucune ligne existante de `VillageV2Builder` ne change ;
  - il instancie chaque prefab à l'origine et mesure : le nombre de niveaux du `LODGroup`, les triangles de chaque LOD lus sur les maillages, le y minimal des renderers du LOD0 et les noms des matériaux ;
  - il écrit `sorties/kit/unity-kit.json`. Il n'ouvre aucune scène et ne juge rien : **Unity mesure, Python juge**, comme aux lots 263 et 251.

## Périmètre
3d/local3d/desert/assets.py
3d/local3d/desert/kit.py
3d/local3d/desert/fabriquer.py
3d/local3d/desert/inspecter_kit.py
3d/local3d/desert/README.md
3d/local3d/atelier_desert.py
3d/unity/Assets/ForgeLocal3D/Editor/DesertKit.cs
3d/unity/Assets/ForgeLocal3D/Editor/DesertKit.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/VillageV2Builder.cs
3d/local3d/desert/sorties/bibliotheque/catalogue.json
3d/local3d/desert/sorties/bibliotheque/scierie.fbx
3d/local3d/desert/sorties/bibliotheque/four_pain_pise.fbx
3d/local3d/desert/sorties/diagnostic/kit_ateliers.png
3d/local3d/desert/sorties/kit/selection.json
3d/local3d/desert/sorties/kit/unity-kit.json
3d/local3d/desert/sorties/kit/jugement.json
3d/unity/Assets/ForgeLocal3D/Desert/Data/catalogue.json
3d/unity/Assets/ForgeLocal3D/Desert/Models/scierie.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/scierie.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Models/four_pain_pise.fbx
3d/unity/Assets/ForgeLocal3D/Desert/Models/four_pain_pise.fbx.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/scierie.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/scierie.prefab.meta
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/four_pain_pise.prefab
3d/unity/Assets/ForgeLocal3D/Desert/Prefabs/four_pain_pise.prefab.meta
docs/briefs/266-la-scierie-et-le-four-en-pise-entrent-dans-le-ki.md

Précisions sur ce périmètre :

- `VillageV2Builder.cs` : ajout de la seule méthode `ImportPrefab`. Aucune ligne existante ne change, puisque l'alpin et la citadelle en dépendent.
- `inspecter_kit.py` : ajout du seul groupe `('ateliers', ['scierie', 'four'])`.
- `README.md` : une courte section « Ajouter un module au kit : `kit` ».
- Les fichiers de `sorties/` et ceux de `Desert/` sous Unity sont refaits par la commande. On ne les édite pas à la main. Les FBX et les PNG passent par LFS : après la poussée, vérifier qu'ils sont sur le serveur.

Tout autre chemin est interdit, en particulier :

- `Kit_Desert.blend` ;
- les FBX, les prefabs et les matériaux des 49 anciens modules ;
- les scènes `Desert/Scenes/*.unity` ;
- `sorties/villages/` ;
- `DesertBuilder.cs` ;
- `jeu/`.

## Conditions de succès
Toutes se lisent dans une seule commande, jouée sur le PC depuis la racine, Unity fermé :

```powershell
py 3d/local3d/atelier_desert.py kit
```

La commande fait ceci, dans l'ordre :

1. Elle relève les **empreintes avant** (SHA-256), dérivées du disque par glob et jamais d'une liste écrite à la main :
   - `Desert/Scenes/*.unity` ;
   - les prefabs, FBX et `.mat` de `Desert/` qui ne sont pas ceux des nouveaux modules ;
   - `sorties/villages/*/*.json` et `*.fbx`.
2. Elle lit le catalogue avant.
3. Elle prépare les textures si elles manquent.
4. Elle lance Blender (`fabriquer.py kit`), puis la planche (`inspecter_kit.py -- scierie four`).
5. Elle copie les deux FBX et `catalogue.json` dans Unity.
6. Elle lance `ForgeLocal3D.DesertKit.Start`. Elle refuse de tourner si Unity est ouvert, comme `routes`.
7. Elle relève les empreintes après et juge avec `kit.juger`.

Elle écrit `sorties/kit/jugement.json` et sort en code non nul au premier défaut.

Chaque défaut porte une étiquette : `budget`, `origine`, `lod`, `materiau`, `echantillon`, `catalogue` ou `empreinte`. Chaque contre-épreuve rejoue `kit.juger` sur une **copie** modifiée de ses entrées, et entre dans le dictionnaire `contre_epreuves`. Si une contre-épreuve ne rougit pas, **ou rougit sans l'étiquette attendue**, c'est un défaut.

- **SC1 — Le budget est tenu.**
  - Pour chaque nouveau module, les triangles de chaque LOD mesurés par Unity sont sous le plafond de `kit.py`.
  - Blender refuse déjà de livrer un module trop lourd. Le jugement le revérifie sur la mesure Unity.
  - *Contre-épreuve « pièce trop lourde »* (`contre_epreuves.piece_trop_lourde`) : le plafond LOD0 de `scierie`, mis à ses triangles mesurés moins un, doit donner un défaut `budget`.
- **SC2 — L'origine est au sol.**
  - Pour chaque nouveau module, le y minimal du LOD0 mesuré dans Unity est à 1 cm de 0 au plus.
  - *Contre-épreuve « origine relevée de 5 cm »* (`contre_epreuves.origine_relevee`) : le y minimal de `four_pain_pise`, augmenté de 0,05 m dans une copie du rapport, doit donner un défaut `origine`.
- **SC3 — Trois LOD, et Unity a reçu ce que Blender a fait.**
  - Chaque `LODGroup` a exactement 3 niveaux.
  - Les triangles de chaque LOD sont égaux à ceux du catalogue.
  - Les triangles décroissent strictement : LOD0 > LOD1 > LOD2 > 0.
  - *Contre-épreuve « triangles divergents »* (`contre_epreuves.triangles_divergents`) : le LOD1 de `scierie`, augmenté d'un triangle dans une copie du rapport, doit donner un défaut `lod`.
- **SC4 — Un échantillon vide échoue.**
  - Le rapport Unity contient **exactement** les modules de `kit.NOUVEAUX`, et au moins un. Il en va de même pour le catalogue après.
  - Les empreintes avant ne sont pas vides.
  - *Contre-épreuve « échantillon vide »* (`contre_epreuves.echantillon_vide`) : un rapport dont la liste des modules est vidée doit donner un défaut `echantillon`.
- **SC5 — Seulement les matériaux du catalogue.**
  - La liste `materials` du catalogue après est identique à celle d'avant.
  - Chaque matériau mesuré sur les prefabs y figure.
  - Aucun matériau n'est noté manquant par Unity.
  - *Contre-épreuve* (`contre_epreuves.materiau_neuf`) : un matériau `inconnu` ajouté à un prefab dans une copie du rapport doit donner un défaut `materiau`.
- **SC6 — Pas une ligne des 49 anciens modules ne change.**
  - Les enregistrements du catalogue avant qui ne sont pas dans `kit.NOUVEAUX` se retrouvent à l'identique, dans le même ordre, dans le catalogue après. Leur nombre est dérivé, et la commande l'affiche : 49 aujourd'hui.
  - *Contre-épreuve* (`contre_epreuves.ancien_module_change`) : une copie du catalogue après où `bounds_max` de `maison_pise_0` change doit donner un défaut `catalogue`.
- **SC7 — Les scènes du ksar ne sont pas reconstruites.**
  - Toutes les empreintes après sont égales aux empreintes avant.
  - *Contre-épreuve* (`contre_epreuves.scene_touchee`) : une copie des empreintes après où celle de `Forge_Desert_ksar_des_sept_puits.unity` change doit donner un défaut `empreinte`.
- **SC8 — Ce qu'on voit.**
  - `sorties/diagnostic/kit_ateliers.png` montre les deux ateliers au LOD0.
  - Le jugement refuse une image absente ou uniforme : l'écart-type des pixels est mesuré, avec le même seuil `ECART_CAPTURE` que `routes.py`.
  - Le codeur regarde l'image lui-même et dit dans la PR ce qu'on y voit : l'auvent, la grume, la coupole et sa bouche.
- **SC9 — Rien d'ancien ne régresse.**
  - `py 3d/local3d/atelier_desert.py verifier` reste vert.
  - Le contrôle existant de `library()` (LOD ≥, « Source sans ses trois LOD ») garde sa rigueur : la factorisation ne l'assouplit pas.
  - *Contre-épreuve* : les sept contre-épreuves ci-dessus, qui doivent rougir à chaque passage.

## Hors périmètre
- Le geste « poser un atelier » comme intention dans `sim/`, la parcelle qui le reçoit et les bras qu'il prend aux champs : ce sont d'autres lots de J4.
- La pose des ateliers dans une scène, que ce soit celles du ksar ou de la ville, et toute reconstruction de scène.
- `Kit_Desert.blend`. `edition --asset scierie` répondra « Module inconnu » jusqu'à la prochaine reconstruction complète du kit (`fabriquer --force`). C'est cette reconstruction qui les y fera entrer.
- De nouveaux matériaux ou de nouvelles textures, et les matériaux photographiés.
- Un budget pour les 49 anciens modules : `kit.py` ne plafonne que les nouveaux.
- La collision des ateliers au-delà de ce que `DesertBuilder.AddAssetCollision` fait déjà pour un `batiment` (maillage du LOD2).
