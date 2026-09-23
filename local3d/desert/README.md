# Ksar du désert — terre crue, grès et palmeraie

Le pendant chaud de la [citadelle alpine](../citadelle/README.md) : un ksar de
terre crue posé sur une table de grès, sa grande mosquée à minaret carré, un
bourg bas au bord des jardins, un souk, une palmeraie autour d'une guelta, un oued
sec et des cordons de dunes. Lumière de fin de journée, vent de sable, lanternes.

Contexte imaginaire, de fidélité 2 : désert de sable et de grès, ksar fortifié et
oasis, culture saharienne imaginaire, année 1400. Ce travail artistique ne modifie
ni le monde simulé ni la carte figée.

## Ce qui correspond à quoi

La chaîne est celle de la citadelle, pièce pour pièce. Seul le contenu change.

| citadelle | désert |
|---|---|
| éperon rocheux, socle en falaises | table de grès stratifiée, chicots de grès en bancs durs et tendres |
| remparts de pierre, tours à flèche | remparts de pisé sur assise de grès, merlons en dents de scie, tours à fruit et merlons à redans |
| porte à ogive, pont à arche | porte à arc outrepassé et alfiz, pont de grès à arches outrepassées |
| cathédrale : façade, nef, clochers | mosquée : portail à zellige, deux travées de salle à toits de tuiles vertes, minaret à réseau de losanges |
| maisons à colombages en îlots | maisons de pisé à terrasse en îlots mitoyens (même `rangee`), teintes d'enduit ocre et rose |
| forêt de 1 600 sapins, clairière | palmeraie de 1 200 palmiers-dattiers et 70 acacias, lisière au-dessus de la guelta |
| quatre clairières constructibles | quatre jardins irrigués ceints de murets |
| marché, étals | souk : épices, tissus, poteries, dattes, tapis, jarres, vélums |
| montagnes enneigées | dunes en étoile et buttes-témoins lointaines |
| neige, brouillard, torches | vent de sable, brume de chaleur, lanternes |

Le tracé des rues reprend celui de la citadelle, qui avait déjà prouvé sa
continuité ; `paysage.Z` ramène les altitudes au désert (plateau à 30 m, bourg
vers 4 à 9 m). La lisière de la palmeraie reste au niveau du sol naturel,
au-dessus de la guelta.

## Ouvrir

À la racine du projet : `Ouvrir_Unity_Desert.cmd`, `Ouvrir_Blender_Desert.cmd`,
`Ouvrir_Galerie_Desert.cmd`.

Dans Unity : flèches pour déplacer le point visé, clic droit pour tourner, molette
pour approcher, F pour la vue générale, H pour masquer les commandes. F1 et F2
changent d'implantation (en marchant). **F3** pont, **F4** parvis, **F5** mosquée,
**F6** maisons et ruelles, **F7** oasis, **F8** palmeraie, **F9** souk. **Tab**
active la marche depuis la place du ksar (ZQSD, WASD ou flèches, Maj pour courir).
Le panneau règle l'heure (de 12 à 22 h) et le temps : plein soleil, vent de sable,
brume de chaleur. Les lanternes s'allument au crépuscule.

Dans Blender : les caméras sont dans la collection `05 • Atmosphère`. Le pavé
numérique 0 affiche la caméra active ; F12 lance son rendu. La lecture de la
chronologie anime les étendards, quelques palmiers et les lanternes.

## Fabriquer et retoucher

Depuis la racine, dans PowerShell :

```powershell
py local3d/atelier_desert.py fabriquer --unity
py local3d/atelier_desert.py fabriquer --disposition oued_des_vents
py local3d/atelier_desert.py fabriquer --sans-rendus --unity
py local3d/atelier_desert.py edition --asset maison_pise_0
py local3d/atelier_desert.py verifier
py local3d/atelier_desert.py visite
py local3d/atelier_desert.py parcours
py local3d/atelier_desert.py terrain
py local3d/desert/galerie.py
```

`blender -b --python local3d/desert/inspecter_kit.py` produit des planches de
contrôle du kit dans `sorties/diagnostic/`.

Les règles de retouche sont celles de la citadelle : `edition` prépare
`sources/<identifiant>.blend` sans écraser un fichier existant ; conserver les
objets `<identifiant>_LOD0`, `_LOD1`, `_LOD2`, leurs matériaux, l'origine et les
transformations appliquées. Une source présente est prioritaire à la
reconstruction. La fabrication calcule une empreinte des scripts, de la recette et
des sources : une scène inchangée est réutilisée, `--force` impose la reconstruction.

| fichier | rôle |
|---|---|
| `recette.json` | contexte et deux implantations : **Ksar des Sept Puits** (1433), **Oued des Vents** (2851) |
| `textures.py` | palette procédurale : pisé à banchées et trous de boulins, grès en bancs, sable ridé, zellige, palmes, tissus |
| `assets.py` | les 49 modules et leurs trois niveaux de détail |
| `urbanisme.py` | îlots mitoyens du ksar et du bourg |
| `paysage.py` | relief, oued, dunes, guelta, rues, jardins |
| `terrain.py` | la ville : `paysage.field` échantillonné pour un Unity Terrain |
| `cameras.py` | treize cadrages communs à Blender et Unity |
| `fabriquer.py` | bibliothèque puis scène par implantation |
| `verifier.py` | contrôles de la scène livrée, chacun avec sa contre-épreuve |
| `galerie.py` | page `sorties/index.html` |

Les dunes et les buttes lointaines portent une couleur et des normales calculées
depuis leur propre relief (faces d'avalanche plus sombres, rides éoliennes).

## Vérification

`verifier` rouvre chaque `.blend` et contrôle : placements, cadrages et focales,
raccord de l'escalier au parvis de la mosquée, budget de triangles, textures
embarquées, animation des étendards, porte traversable à hauteur d'homme, surface
de chaque chemin sous les pieds et pente maximale, eau de la guelta au-dessus du
fond. Chaque contrôle est suivi d'une contre-épreuve : la scène est déréglée en
mémoire, le contrôle doit échouer, puis elle est restaurée sans enregistrer.

Ce contrôle a trouvé un vrai défaut pendant la construction : là où deux rues se
recouvrent (place du souk et descente), le sol sautait de 60 cm d'un profil à
l'autre. `paysage.blend_profiles` mêle désormais les profils voisins sur un mètre ;
la grille du terrain et les points isolés donnent la même hauteur.

Le parcours Unity en a trouvé un second : les murets des jardins étaient fermés
des deux côtés, et le personnage butait dessus au bout du chemin d'accès. Le côté
de l'accès garde désormais une porte de 3,6 m.

Le contrôle de série exige une bibliothèque commune, un contexte identique et des
placements de maisons différents entre les deux implantations.

L'import Unity compare dimensions, triangles, positions et repères du terrain,
rouvre les scènes, compte les groupes de LOD, contrôle l'identité de chaque maison
et refuse un shader en erreur. `visite` entre en Play (plein soleil, vent de sable,
crépuscule, nuit, brume, quatre cadrages, vidéo de huit secondes, changement
d'implantation). `parcours` fait marcher le personnage sur toutes les rues des deux
scènes, sans téléportation, après une contre-épreuve contre un mur, puis rejoint
la lisière de la palmeraie.

## Unity

`unity/Assets/ForgeLocal3D/Desert/` reçoit modèles, textures, manifestes et
scènes `Forge_Desert_*`. Le constructeur partagé (`VillageV2Builder`) a un mode
désert : il reprend le shader, les collisions, la teinte des enduits et la marche
de la citadelle. `DesertBuilder.cs` règle le ciel (`Forge/DesertSky`), l'étalonnage,
le vent de sable, les lanternes et la marche ; `DesertEnvironment.cs` pilote l'heure
et le temps pendant la visite. Si Unity est déjà ouvert, l'atelier passe par la même
boîte aux lettres que la citadelle (`unity/Library/ForgeCitadelle/`).

Décor tiers : le pack **Polylised — Medieval Desert City**, déjà présent sous
`unity/Assets/Vendor/` (ignoré par git, licence), fournit tentes, chariots,
tonneaux, lampes, puits, fontaine et arbres morts. `DesertDecor.cs` les pose
d'après la graine, hors des rues, des jardins, du point de départ et de toute
collision, et remplace leurs matériaux par ceux du désert. Pack absent : les
compteurs du rapport valent `-1` ; pack présent sans pose : la construction échoue.

## Limites de cette passe

Pas d'intérieurs, pas de chantier de construction ni de mesure de performance dans
le joueur autonome (la citadelle en a ; le désert pourra les reprendre). Les gardes
et les dromadaires sont statiques. Le vent de sable, la brume et les fumées sont
des effets visuels. Le branchement au moteur historique relève d'un travail distinct.

## La ville du désert — étape 1 : un vrai Unity Terrain

La ville se construira dans Unity, à l'exécution, à partir des gestes du joueur.
Son sol ne peut donc plus être un maillage figé : c'est un **Unity Terrain** que
les routes creuseront et peindront. Il est tiré de la même fonction que le
maillage Blender, `paysage.field`.

```powershell
py local3d/atelier_desert.py terrain                 # les deux implantations
py local3d/atelier_desert.py terrain --disposition oued_des_vents
py local3d/atelier_desert.py terrain --force         # rééchantillonne même sans changement
```

`terrain.py` échantillonne `paysage.field` sur 1 024 m de côté, au pas de 0,5 m
(2 049² hauteurs), et écrit sous `sorties/ville/<implantation>/` :

| fichier | contenu |
|---|---|
| `hauteurs.f32` | altitudes en mètres, ligne par ligne |
| `horizon.f32` | le cordon de dunes jusqu'à 1,5 km, au pas de 16 m |
| `couches.u8` | poids de quatre couches par mètre carré : sable, reg, grès, terre humide |
| `details_*.u8` | touffes par mètre carré : trois herbes sèches, deux broussailles |
| `terrain.json` | dimensions, empreintes des fichiers, couverture, échantillon de contrôle |

Les grilles binaires sont ignorées par git ; la commande les refait (environ
75 s par implantation) quand `paysage.py`, `terrain.py` ou la graine changent.

`DesertCityTerrain.cs` en fait la scène `Forge_Desert_Ville_<implantation>` :
terrain, horizon de dunes raccordé par un rideau vertical, eau de la guelta,
soleil et ciel du désert. Le grès vient des textures du désert ; le reg (galets
`Pebbles_B`), la terre humide (`Grass_Soil_A`) et les touffes (`GrassDry_*`,
`BushDry_B`, `Bush_Twig`) du Terrain Sample, convertis en `Forge/CitadelLit`.
Sans le pack, le reg et la terre reprennent les textures du désert, il n'y a
pas de touffes, et leurs compteurs valent `-1`. Les anciennes scènes
`Forge_Desert_<implantation>` ne changent pas.

Le contrôle rouvre la scène enregistrée et écrit `unity-terrain.json` :

- **l'échantillon** : chaque point de rue au sol, les coins et centres des
  seuils et des jardins, et un point tiré par carré de 16 m (≈ 4 950 points) ;
- **transport** : hauteurs, couches, touffes et horizon identiques aux fichiers,
  à la quantification 16 bits près ;
- **fidélité** : en chaque point, la hauteur Unity ne s'écarte pas plus de
  `paysage.field` que la grille idéale elle-même, quantification comprise ;
- **sol marchable** : sur les rues et les seuils, surface affichée et collision
  à moins de 5 cm de `paysage.field` (le sixième d'une marche de 0,32 m) ;
- **raccord** : à chaque échantillon du bord, le rideau couvre le bord du
  terrain et celui de l'horizon ; aucune touffe sur une rue ou un seuil.

Six contre-épreuves doivent chacune faire échouer le contrôle, puis tout est
restauré et le contrôle doit repasser : échantillon vide, terrain relevé de
50 cm, axes permutés, sable et reg échangés, touffe posée sur une rue, horizon
relevé de 2 m. Captures : `sorties/ville/<implantation>/captures/`.

Deux défauts trouvés en construisant :

- Unity n'interpole pas les hauteurs en bilinéaire : chaque carreau est coupé
  en deux triangles le long de la diagonale (i, j)–(i+1, j+1). Mesuré à 0,01 mm
  près ; la grille idéale de référence suit donc ce découpage.
- Un TerrainData enregistré après la pose des couches perd leurs textures de
  contrôle au changement de scène. L'asset est désormais créé d'abord.

Et deux corrections de `paysage.py`, vues sur les captures au pas de 0,5 m : les
bosselures en produit de sinus dessinaient une boîte à œufs régulière en
lumière rasante (remplacées par un bruit), et la crête vive des dunes se
crénelait (arrondie sur 1,5 m environ). Elles changeront aussi le relief des
scènes Blender à leur prochaine fabrication, de quelques décimètres au plus.

Ce qui reste visible : `paysage.field` porte encore la rampe d'accès du ksar
et les terrasses de l'ancien bourg, sans ksar dessus ; des pointillés d'ombre
sur les crêtes lointaines (cascades d'ombre, étape rendu) ; le reg qui se lit
comme une tache à mi-distance.

