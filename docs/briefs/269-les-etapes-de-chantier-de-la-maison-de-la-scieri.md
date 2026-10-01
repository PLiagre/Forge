# Lot #269 — Les étapes de chantier de la maison, de la scierie et du four entrent dans le kit du désert
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
Le kit du désert sait montrer un bâtiment en chantier. Pour `maison_pise_0`, la scierie et le four, il gagne deux étapes : les piquets et le cordeau, puis les murs à mi-hauteur sous les perches. Chaque étape est posée exactement sur l'emprise du bâtiment fini. Le catalogue dit dans quel ordre elles se suivent, et Unity les reçoit en prefabs à trois LOD, sans que rien ne bouge dans les anciens modules ni dans les scènes.

## Règle du monde
Sans objet : c'est un lot d'outil et de vue. `sim/` n'est pas touché, et aucune section de `jeu/sim/MODELE.md` n'en découle. Les formes sont de **fidélité 2** (plausibles, jamais sourcées), comme tout le kit (`3d/local3d/desert/recette.json`).

Le lot sert l'écran du jalon J4 de `CAP.md` : « le chantier qui prend des bras aux champs ». Le chantier doit pouvoir se voir, étape par étape, à l'endroit exact où le bâtiment se dressera. Le lot ne s'appuie sur rien que J2 ou J3 doivent livrer : le kit, la commande `kit` du lot 266 (`kit.py`, `fabriquer.py kit`, `DesertKit.cs`) et les trois bâtiments finis sont déjà sur master. Dire quelle étape montrer selon l'avancement du chantier dans `sim/` est un autre lot.

Ce qui existe, vérifié sur master le 01/10/2026 :

- `desert/kit.py` : `NOUVEAUX = ['scierie', 'four_pain_pise']`, leurs `PLAFONDS`, `juger`, neuf contre-épreuves, et les étiquettes `budget`, `origine`, `lod`, `materiau`, `echantillon`, `catalogue` et `empreinte`.
- `fabriquer.py kit_nouveaux()` construit les modules de `kit.NOUVEAUX` à partir de `assets.jobs()`. Il reprend tels quels les enregistrements anciens du catalogue et écrit `sorties/cache/kit_nouveaux.blend` pour la planche. `library()` écrit un catalogue `{schema, assets, materials}`.
- Les builders de `assets.py` sont déterministes (`house` a sa propre graine). Un `Mesh` garde ses sommets dans `m.verts`, tous niveaux de détail confondus.
- `inspecter_kit.py` range les modules par famille, c'est-à-dire par le premier mot du nom avant `_`.
- `DesertKit.cs` crée et mesure les prefabs de `selection.json` : nombre de LOD, triangles, `y_min` et matériaux.
- Au catalogue, les bâtiments finis mesurent : `maison_pise_0` 6,7 × 6,8 m sur 4,75 m ; `scierie` 8,4 × 5,3 m sur 4,25 m ; `four_pain_pise` 3,3 × 2,5 m sur 2,19 m.

Ce que le lot fait :

- **Six modules d'étape**, de type `batiment`, ajoutés **à la fin** de `assets.jobs()`, après `four_pain_pise` :
  - `chantier_maison_pise_0_piquets` et `chantier_maison_pise_0_murs` ;
  - `chantier_scierie_piquets` et `chantier_scierie_murs` ;
  - `chantier_four_pain_pise_piquets` et `chantier_four_pain_pise_murs`.

  Le préfixe `chantier_` les range dans une seule famille pour la planche.
- **L'emprise se tire du bâtiment fini**, jamais d'un nombre recopié. Une fonction `emprise(builder)` de `assets.py` appelle le builder du bâtiment fini (`house(0)`, `sawmill`, `bread_oven`) et rend les x et y minimaux et maximaux et le z maximal de ses sommets. Deux builders génériques la reçoivent :
  - `chantier_piquets(emprise)` : un piquet à chaque coin de l'emprise, et d'autres le long des côtés tous les 1,5 à 2 m environ. Un cordeau tendu de piquet en piquet, à environ 0,4 m. Une hauteur de 1,2 m au plus.
  - `chantier_murs(emprise, cotes)` : des murs de pisé montés à mi-hauteur du bâtiment fini sur les côtés `cotes`, avec la baie de la porte en façade (−Y). Une perche à chaque coin de l'emprise, des planches posées en travers sur des boulins, et une échelle **dans** l'emprise. La maison et le four sont murés sur leurs quatre côtés ; la scierie seulement au fond et au pignon ouest, comme ses murets finis.
  - Ils n'utilisent que des matériaux déjà au catalogue (`pise`, `bois_palmier`, `stipe_palmier`, `bois_sombre`…). Ils ont l'origine au sol, la façade vers −Y et trois niveaux de détail : ornements au LOD0 (cordeau, planches, échelle), silhouette seule au LOD2 (piquets ou perches des coins, murs).
- **`kit.py` reste le seul endroit** des nombres et du jugement :
  - `CHANTIERS = ['maison_pise_0', 'scierie', 'four_pain_pise']` et `suite(fini)`, qui rend `['chantier_<fini>_piquets', 'chantier_<fini>_murs', fini]` ;
  - `NOUVEAUX` devient `['scierie', 'four_pain_pise']` suivi des six étapes, dans l'ordre de `CHANTIERS` ;
  - des plafonds pour chaque étape : piquets (400, 200, 80), murs (1 200, 600, 240) ;
  - `TOLERANCE_EMPRISE = 0.3` m, `HAUTEUR_PIQUETS_MAX = 1.2` m et `RAPPORT_MURS = (0.5, 0.8)`, la hauteur de l'étape des murs, perches comprises, rapportée à celle du bâtiment fini ;
  - trois étiquettes de plus : `emprise`, `hauteur` et `suite`.
- **Le catalogue déclare la suite dans une clé à part**, `chantiers`, placée après `materials` : `{"maison_pise_0": [piquets, murs, "maison_pise_0"], …}`.
  - `kit_nouveaux()` l'écrit d'après `kit.suite`. `library()` l'écrit aussi (une ligne), pour qu'une reconstruction complète ne la perde pas.
  - Aucune fiche d'`assets` ne gagne de champ. `schema` et `materials` ne changent pas.
- **Unity, `DesertKit`** :
  - `selection.json` gagne `references`, les bâtiments finis de `CHANTIERS` qui ne sont pas dans `NOUVEAUX` (aujourd'hui `maison_pise_0`), dérivés par Python ;
  - `DesertKit` charge leur prefab **existant** et le mesure sans le recréer ni l'enregistrer ;
  - chaque mesure gagne `x_min`, `x_max`, `z_min`, `z_max` et `y_max` : l'enveloppe des maillages du LOD0 dans le repère d'Unity, prefab posé à l'origine, avec -1 pour « non mesuré » ;
  - le rapport gagne la liste `references`. Unity mesure, Python juge.

## Périmètre
3d/local3d/desert/assets.py
3d/local3d/desert/kit.py
3d/local3d/desert/fabriquer.py
3d/local3d/desert/inspecter_kit.py
3d/local3d/desert/README.md
3d/local3d/atelier_desert.py
3d/unity/Assets/ForgeLocal3D/Editor/DesertKit.cs
3d/local3d/desert/sorties/bibliotheque/catalogue.json
3d/local3d/desert/sorties/bibliotheque/scierie.fbx
3d/local3d/desert/sorties/bibliotheque/four_pain_pise.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_maison_pise_0_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_maison_pise_0_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_scierie_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_scierie_murs.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_four_pain_pise_piquets.fbx
3d/local3d/desert/sorties/bibliotheque/chantier_four_pain_pise_murs.fbx
3d/local3d/desert/sorties/diagnostic/kit_ateliers.png
3d/local3d/desert/sorties/diagnostic/kit_chantiers.png
3d/local3d/desert/sorties/kit/selection.json
3d/local3d/desert/sorties/kit/unity-kit.json
3d/local3d/desert/sorties/kit/jugement.json
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
docs/briefs/269-les-etapes-de-chantier-de-la-maison-de-la-scieri.md

Précisions sur ce périmètre :

- `assets.py` : ajout de `emprise`, `chantier_piquets`, `chantier_murs` et des six lignes de fin de `jobs()`. Aucun builder existant ne change.
- `inspecter_kit.py` : ajout du seul groupe `('chantiers', ['chantier'])`.
- `fabriquer.py` : la clé `chantiers` dans les deux écritures du catalogue, rien d'autre. Le chemin `module()` et le refus de `kit.controler` ne changent pas.
- `atelier_desert.py` :
  - `selection.json` porte `references` ;
  - `planche` rend et copie `kit_ateliers.png` **et** `kit_chantiers.png` ;
  - le jugement reçoit l'écart des deux planches ;
  - l'affichage donne, pour chaque étape, son enveloppe et sa hauteur.
- `README.md` : quelques lignes sous « Ajouter un module au kit : `kit` » (les étapes, la clé `chantiers`).
- Les fichiers de `sorties/` et ceux de `Desert/` sous Unity sont refaits par la commande. On ne les édite pas à la main. Les FBX et les PNG passent par LFS : après la poussée, vérifier qu'ils sont sur le serveur.

Tout autre chemin est interdit, en particulier :

- `Kit_Desert.blend` ;
- les FBX, prefabs et matériaux des 49 anciens modules, dont `maison_pise_0.prefab`, mesuré en lecture seule ;
- les scènes `Desert/Scenes/*.unity` ;
- `sorties/villages/` ;
- `DesertBuilder.cs` et `VillageV2Builder.cs` ;
- `jeu/`.

## Conditions de succès
Toutes se lisent dans une seule commande, jouée sur le PC depuis la racine, Unity fermé :

```powershell
py 3d/local3d/atelier_desert.py kit
```

La commande garde son déroulé du lot 266 : empreintes avant, Blender, planches, copie vers Unity, `DesertKit`, vérificateur des scènes, empreintes après, puis `kit.jugement`. Elle écrit `sorties/kit/jugement.json` et sort en code non nul au premier défaut.

Chaque contre-épreuve rejoue `kit.juger` sur une **copie** déréglée de ses entrées, et entre dans le dictionnaire `contre_epreuves`. Si une contre-épreuve ne rougit pas, **ou rougit sans l'étiquette attendue**, c'est un défaut. Les **neuf contre-épreuves du lot 266 restent telles quelles** et doivent toujours rougir. Le lot ajoute les siennes, ci-dessous.

- **SC1 — Budget, origine et trois LOD, pour chaque étape.**
  - Les contrôles du lot 266 (`budget`, `origine`, `lod`, `materiau`) s'appliquent sans changement aux huit modules de `kit.NOUVEAUX`.
  - Blender refuse une étape au-dessus de son plafond.
  - Unity mesure 3 niveaux, des triangles égaux au catalogue et strictement décroissants, le LOD0 au sol à 1 cm près, et seulement des matériaux du catalogue.
  - *Contre-épreuves* : celles du lot 266 (`piece_trop_lourde`, `origine_relevee`, `triangles_divergents`, `materiau_neuf`), sur les modules qu'elles visent déjà.
- **SC2 — L'étape est posée sur l'emprise du bâtiment fini.**
  - Pour chaque étape, chacun des quatre bords horizontaux mesurés par Unity (`x_min`, `x_max`, `z_min`, `z_max` du LOD0) est à `TOLERANCE_EMPRISE` au plus du même bord du bâtiment fini, mesuré lui aussi par Unity : dans `modules` pour la scierie et le four, dans `references` pour `maison_pise_0`.
  - Une mesure à -1, ou un bâtiment fini non mesuré, est un défaut `emprise`.
  - *Contre-épreuve « étape décalée de 2 m »* (`contre_epreuves.etape_decalee`) : `x_min` et `x_max` de `chantier_scierie_piquets`, augmentés de 2 m dans une copie du rapport, doivent donner un défaut `emprise`.
- **SC3 — Les hauteurs montent avec le chantier.**
  - Le `y_max` des piquets est à `HAUTEUR_PIQUETS_MAX` au plus, et strictement sous celui des murs.
  - Le `y_max` des murs est compris entre 0,5 et 0,8 fois celui du bâtiment fini (`RAPPORT_MURS`).
  - *Contre-épreuve « murs plus hauts que le bâtiment fini »* (`contre_epreuves.murs_trop_hauts`) : le `y_max` de `chantier_maison_pise_0_murs`, porté à celui de `maison_pise_0` plus 0,5 m dans une copie du rapport, doit donner un défaut `hauteur`.
- **SC4 — La suite est déclarée, et complète.**
  - La clé `chantiers` du catalogue après a exactement les bâtiments de `kit.CHANTIERS`.
  - Chacun porte exactement `kit.suite(fini)`.
  - Chaque identifiant de la suite est une fiche d'`assets`, et chaque étape a été mesurée par Unity.
  - Un catalogue après sans clé `chantiers` est un défaut `suite`.
  - *Contre-épreuve « étape manquante »* (`contre_epreuves.etape_manquante`) : `chantier_four_pain_pise_murs`, retirée de la suite de `four_pain_pise` dans une copie du catalogue après, doit donner un défaut `suite`.
- **SC5 — Les anciennes fiches ne bougent pas.**
  - Le contrôle du lot 266 tient toujours : les 49 anciens modules sont à l'identique et dans le même ordre, et les nouveaux sont à la fin.
  - En plus, toute fiche présente dans le catalogue avant, y compris `scierie` et `four_pain_pise`, se retrouve à l'identique après. Hors `chantiers`, aucune clé du catalogue n'apparaît ni ne change.
  - Défaut `catalogue`.
  - *Contre-épreuve* : `ancien_module_change`, du lot 266.
- **SC6 — Rien d'autre n'est touché.**
  - Les empreintes après sont égales aux empreintes avant, `maison_pise_0.prefab` compris, alors qu'Unity l'a chargé pour le mesurer.
  - `py 3d/local3d/atelier_desert.py verifier` reste vert, rejoué par la commande comme au lot 266.
  - *Contre-épreuves* : `scene_touchee` et `verification_rouge`, du lot 266.
- **SC7 — Un échantillon vide échoue.**
  - Unity a mesuré exactement les huit modules de `kit.NOUVEAUX` et exactement les bâtiments de `references`, au moins un.
  - *Contre-épreuve* : `echantillon_vide`, du lot 266.
- **SC8 — Ce qu'on voit.**
  - `sorties/diagnostic/kit_chantiers.png` montre les six étapes au LOD0. `kit_ateliers.png` montre toujours les deux ateliers.
  - Le jugement refuse une planche absente ou uniforme, pour chacune des deux, avec le seuil `ECART_CAPTURE`.
  - *Contre-épreuve « planche des chantiers uniforme »* (`contre_epreuves.planche_chantiers_uniforme`) : l'écart d'une image toute rouge, mis à la place de celui de `kit_chantiers.png`, doit donner un défaut `echantillon`.
  - Le codeur regarde l'image lui-même et dit dans la PR ce qu'on y voit : le cordeau entre les piquets, les murs à mi-hauteur, les perches, les planches et l'échelle.

## Hors périmètre
- Choisir quelle étape montrer selon l'avancement d'un chantier dans `sim/`, et le chantier comme intention ou comme travail pris aux champs : d'autres lots de J4.
- Poser une étape dans une scène (ksar ou ville), et toute reconstruction de scène.
- Des étapes pour les autres maisons (`maison_pise_1` à `5`) ou pour d'autres bâtiments.
- `Kit_Desert.blend` : les étapes y entreront à la prochaine reconstruction complète (`fabriquer --force`), que ce lot ne lance pas.
- De nouveaux matériaux ou de nouvelles textures.
- Une collision propre aux étapes, au-delà de ce que `DesertBuilder.AddAssetCollision` fait déjà pour un `batiment`.
