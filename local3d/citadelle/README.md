# Citadelle alpine — direction gothique enneigée

Une scène 3D inspirée de la référence fournie le 14 septembre 2026 : citadelle sur un éperon, cathédrale gothique, maisons à colombages, pont de pierre, sapins enneigés, teintes froides et feux chauds.

La scène est une interprétation stylisée de la référence. Ses formes et ses textures restent plus simples que l'illustration. Le contexte est imaginaire, de fidélité 2 : montagne enneigée, bourg fortifié, culture gothique alpine, année 1400. Ce travail artistique ne modifie ni le monde simulé ni la carte figée.

La passe du 15 septembre développe les modules existants : pierre chanfreinée,
ornements gothiques, menuiseries, lucarnes, neige continue, sapins à branches
irrégulières, relief raviné et matériaux avec rugosité. Le [diagnostic](DIAGNOSTIC.md)
explique les écarts observés et les corrections. La galerie compare les mêmes
dix cadrages avant et après dans les deux implantations.

## Ouvrir

À la racine du projet : `Ouvrir_Unity_Citadelle.cmd`, `Ouvrir_Blender_Citadelle.cmd`, `Ouvrir_Galerie_Citadelle.cmd`.

La galerie `sorties/index.html` contient les vues actuelles du kit modulaire, les captures des ambiances Unity, les deux implantations et une vidéo de huit secondes réellement enregistrée dans Unity.

Dans Unity : flèches pour déplacer le point visé, clic droit pour tourner, molette pour approcher, F pour retrouver la vue générale, H pour masquer les commandes. F1 et F2 changent de disposition. **F3** place la caméra sur le pont, **F4** sur le parvis et **F5** devant la cathédrale. Le panneau règle la lumière, la neige et le brouillard.

**F6** montre les maisons mitoyennes et les ruelles du hameau.

**Tab** active la marche depuis la place de la citadelle. **ZQSD**, WASD ou les
flèches déplacent le personnage ; **Maj** accélère ; le clic droit permet de
regarder. **Tab** retrouve la caméra libre. La marche utilise les collisions des
ponts, du terrain, des bâtiments et des troncs. **E**, près d'un sapin, lance un
essai d'abattage : le sapin tombe. Cette interaction locale se réinitialise au
rechargement de la scène.

Dans Blender : les caméras **Citadelle**, **Porte**, **Cathedrale**, **Passage** et **Parvis** sont dans la collection `05 • Atmosphère`. Le pavé numérique 0 affiche la caméra active ; F12 lance son rendu. La lecture de la chronologie anime les bannières, certains sapins et les lueurs des torches.

## Bibliothèque et scènes

`sorties/bibliotheque/Kit_Citadelle.blend` conserve les 31 modules d'origine et deux ajouts : `lucarne_gothique` et `reserve_bois_tonneaux`. Les objets sont marqués comme assets Blender. Ajouter ce dossier dans les bibliothèques d'assets de Blender permet de les parcourir dans son navigateur.

Chaque module dispose d'un FBX avec trois niveaux de détail, appelés LOD : ils servent à alléger les objets éloignés. Les petites pièces conservent parfois la même géométrie aux trois niveaux. Le catalogue dérive les triangles et les dimensions des maillages réels.

Le kit d’habitat ajoute des pièces assemblables et six nouvelles compositions. Les anciens modules comprennent six maisons, trois tours, un rempart de dix mètres, une porte à ogive traversante, un pont à arche de quatorze mètres, quatre pièces de cathédrale, trois sapins, quatre falaises, trois montagnes, une torche, une bannière, un garde, un escalier et des pavés.

La cathédrale est assemblée avec sa façade, ses travées de nef, ses clochers et ses arcs-boutants. L'enceinte utilise des segments de mur et des tours indépendants. Les terrains, les terrasses et le chemin sont propres à chaque scène.

Deux dispositions sont déclarées dans `recette.json` : **Éperon des Veilleurs** et **Col des Cendres**. Elles partagent le même catalogue et le même contexte. La seconde change la répartition des maisons, le placement de la cathédrale, le hameau, le relief de vallée et les arbres. Le plan de l'enceinte demeure commun à cette passe.

Les fichiers `sorties/villages/<identifiant>/<identifiant>.json` contiennent les placements en coordonnées Blender. La conversion importée dans Unity est `(-x, z, -y)`, avec rotation Y opposée à la rotation Z Blender. Six sommets réels du terrain vérifient cette conversion après import. Les prefabs sont partagés sous `unity/Assets/ForgeLocal3D/Citadelle/Prefabs/`.

## Fabriquer et retoucher

Depuis la racine, dans PowerShell :

```powershell
py local3d/atelier_citadelle.py fabriquer --unity
py local3d/atelier_citadelle.py fabriquer --disposition col_des_cendres
py local3d/atelier_citadelle.py fabriquer --sans-rendus --unity
py local3d/atelier_citadelle.py edition --asset maison_gothique_0
py local3d/atelier_citadelle.py verifier
py local3d/atelier_citadelle.py visite
py local3d/atelier_citadelle.py parcours
py local3d/citadelle/galerie.py
py local3d/citadelle/comparer.py
```

`edition` prépare `sources/<identifiant>.blend`, sans écraser un fichier existant. Le fichier `sources/maison_gothique_0.blend` est déjà prêt pour une retouche manuelle.

Conserver les noms `<identifiant>_LOD0`, `_LOD1`, `_LOD2`, leurs matériaux, l'origine et les transformations appliquées. Le LOD0 est visible ; les deux autres sont masqués. Retoucher le maillage, puis enregistrer. La reconstruction reprend ce fichier en priorité dans toutes les scènes. Une source sans ses trois objets ou avec des transformations non appliquées est refusée.

La fabrication calcule une empreinte des scripts, de la recette et des retouches. Une scène inchangée est réutilisée. `--force` impose sa reconstruction. Les sorties générées ne sont pas le bon emplacement pour une retouche durable ; utiliser `sources/`.

Si Unity est déjà ouvert sur ce projet, l'atelier dépose une demande locale dans
`unity/Library/ForgeCitadelle/`. Revenir dans l'éditeur déclenche l'actualisation
des scripts. L'opération attend la sortie du mode Play et l'enregistrement des
scènes modifiées ; elle ne ferme pas la fenêtre. Les scènes qui étaient ouvertes
sont restaurées après la construction ou le contrôle. Sans éditeur ouvert, les
mêmes commandes utilisent Unity en arrière-plan.

Les textures sont procédurales et partagées entre Blender et Unity. Les fichiers de scène Blender les embarquent. Les falaises et la neige des toitures sont des géométries ; les couloirs de neige des montagnes sont des textures calculées depuis leur relief.

Les cartes de matériaux sont en 1024² ; les cartes des montagnes sont en 1536².
La couleur, les normales et le lissage sont utilisés dans les deux moteurs de
rendu. Les normales décrivent le petit relief sans ajouter de triangles.
Les cartes communes sont actualisées dans la bibliothèque reconstruite, y compris
pour une géométrie provenant de `sources/`, sans réenregistrer la source manuelle.
Les chanfreins automatiques s'appliquent seulement aux modules générés au LOD0.

`cameras.py` définit les cadrages en coordonnées Blender et leur focale. Le manifeste
les transmet à Unity avec la même conversion d'axes que les modèles. L'escalier
conserve son pivot et son placement ; ses marches rejoignent désormais sa terrasse
sans masquer les portails.

`paysage.py` définit les profils des rues, leurs largeurs, les seuils des maisons,
le sentier forestier et quatre clairières de 13 × 12 m. Ces profils sculptent le
terrain ; leurs surfaces sont exportées dans le paysage FBX. Les arbres et les
éboulis sont écartés des accès et des clairières. Les quatre piquets d'une
clairière en délimitent la surface disponible ; ils ne ferment pas son entrée.
Les caméras **Vallee**, **Contrechamp**, **Village** et **Foret** complètent les
cinq vues de comparaison. Leurs positions sont aussi importées dans Unity.

`urbanisme.py` compose les maisons en îlots mitoyens de deux à six bâtiments.
La graine varie leurs largeurs, profondeurs, hauteurs, orientations, retraits et
teintes d'enduit. Les maisons partagent visuellement des murs et des débords de
toiture, mais chacune conserve son objet Blender, son identifiant et son instance
de prefab Unity. Le champ `urban_group` décrit seulement leur regroupement visuel.
Les ruelles suivent l'avant des îlots et chaque porte conserve son accès propre.
Leurs accotements rejoignent le terrain et mêlent neige, terre et pavés par
plaques irrégulières. Les textures et leurs coordonnées sont communes aux deux
rendus, sans shader réservé aux captures Blender.

Le cadrage **Ilots** permet d'examiner ce regroupement. `--sans-rendus` prépare
les volumes et permet leur contrôle dans Unity ; une fabrication ordinaire doit
ensuite produire les images définitives. Cette préparation ne valide pas le cache
des rendus. Les chanfreins des petites pièces sont limités aux arêtes structurantes
pour consacrer le budget de géométrie aux volumes visibles.

## Vérification

`verifier` rouvre chaque `.blend`, compare les placements et les triangles au manifeste, contrôle les textures embarquées, mesure l'animation des bannières et lance un rayon à travers la porte. Il déplace volontairement un objet en mémoire et exige que le contrôle échoue, puis le remet en place sans enregistrer.

Le contrôle de série exige une bibliothèque commune, un contexte identique et des placements de maisons différents. Le budget de cette étude est inférieur à trois millions de triangles au niveau le plus détaillé. Il reste un plafond de contenu, pas une garantie de fréquence d'affichage.

L'import Unity compare les dimensions, les triangles, les positions et les repères du terrain. Il rouvre les scènes sauvegardées, compte leurs groupes de LOD, contrôle les matériaux et refuse un shader en erreur après rendu.

`visite` entre dans le véritable mode Play : précipitations et flammes non vides, variation d'intensité des torches, changement des pixels à caméra fixe, changement de scène. Il produit les captures, le rapport `sorties/visite/verification-play.json` et la vidéo H.264.

`comparer.py` contrôle la conservation des identifiants de modules, des instances,
des fichiers d'identité des prefabs et de l'empreinte des sources manuelles.
Il vérifie aussi les cadrages et la présence des couples d'images avant/après. Il utilise
l'état initial conservé dans `sorties/diagnostic/avant/` et écrit
`sorties/diagnostic/conservation.json` ; ce contrôle concerne cette évolution.

La reprise du relief déplace le hameau et les arbres. La composition mitoyenne
change aussi les proportions et les positions des maisons de la ville haute et
leurs torches. Les identifiants et modèles sont conservés. La migration autorise
ces transformations artistiques et le dégagement des falaises devant la porte ;
tout autre changement initial est refusé. Le détail avant/après est écrit dans
`sorties/diagnostic/migration_<implantation>.json`.

`parcours` ouvre les deux scènes sauvegardées en Play. Il vérifie la connexion de
toutes les branches, puis les parcourt avec le contrôleur de marche utilisé par
la visite, sans téléportation entre les branches. Un mur ajouté temporairement
doit arrêter le personnage. Le contrôle rejoint ensuite la lisière et approche
un tronc pour essayer l'abattage. Rapport et captures : `sorties/parcours/`.
Le contrôle Blender vérifie aussi les surfaces des chemins par des rayons,
mesure les pentes et refuse une route déplacée sous le terrain.

Les captures ont aussi été examinées visuellement. La parité d'import porte sur les modèles et les placements ; Cycles et Unity conservent des éclairages distincts.

## Décor tiers de l'Asset Store

La scène Unity ajoute un décor venu de trois packs de l'Asset Store. Blender ne
le connaît pas : il n'entre ni dans le manifeste ni dans la parité d'import.
`unity/Assets/ForgeLocal3D/Editor/CitadelDecor.cs` le pose à chaque
construction, après les rues et les clairières.

| pack | ce qui est posé |
|---|---|
| Rocks and Boulders 2 | éboulis au pied des falaises, blocs et petits groupes sur les pentes (versions enneigées) |
| Fantasy Exteriors — Blacksmith (3DForge) | forge et écurie sur assises en pierre, abreuvoirs, clôtures le long des chemins |
| Polylised — Medieval Desert City | arbres morts, tonneaux et caisses près des maisons, trois charrettes, un puits |

Les packs vivent sous `unity/Assets/Vendor/`, que git ignore : leur licence
interdit de les republier, et le dépôt est public. Sur une machine sans ces
packs, la construction passe et le rapport `unity-verification.json` porte `-1`
pour ce qui manque. Un pack présent qui ne pose rien fait échouer la
construction.

Le placement est tiré de la graine de la disposition. Il évite les rues et
leurs accotements, les clairières, le point d'arrivée et la lisière qu'utilise
le contrôle `parcours`, et tout ce qui porte une collision. Les matériaux des
packs, prévus pour l'ancien pipeline, deviennent des matériaux
`Forge/CitadelLit` rangés sous `Materials/Tiers`. Les accessoires Polylised
reprennent les bois, fers et pierres de la citadelle. Les modèles Polylised
sont exportés axe Z vers le haut et reçoivent une rotation de -90° sur X.

La forge du pack Blacksmith (15 × 8 m) et l’écurie sont posées dans les deux
dispositions. Une assise en pierre compense le dénivelé mesuré sous chaque
bâtiment, sans changer le terrain ni les routes. Les prefabs
`PB_FS_*` de Frontier Settlement ne sont pas utilisés : il leur manque des
dizaines de maillages du kit complet « Village & Towns ».

## Terrain Sample Project de Unity

Le pack `Unity Terrain — HDRP Demo Scene` (1.0.3) est adapté aux deux scènes
de citadelle. Le projet conserve URP, son moteur de rendu actuel. Le terrain
reste le maillage sculpté dans Blender : ses altitudes, ses collisions et les
accès ne changent pas.

`CitadelTerrainSample.cs` applique les couches `Cliff_Mossy_E`, `Grass_Soil_A`
et `Pebbles_B` au sol, aux falaises et aux montagnes. La roche se projette
sur trois plans pour éviter les étirements sur les parois. La couleur,
les normales et les masques de surface du pack sont réellement utilisés.
Les masques HDRP donnent le métal, l'occlusion et le lissage par leurs canaux
rouge, vert et alpha, conformément à la
[documentation Unity](https://docs.unity.cn/Packages/com.unity.render-pipelines.high-definition%4012.1/manual/Mask-Map-and-Detail-Map.html).
La neige conserve les couloirs des montagnes ; le sol mêle neige, terre et
gravier par plaques. Les matériaux sont sous
`unity/Assets/ForgeLocal3D/Citadelle/Materials/Tiers/TerrainSample/`.

Les herbes sèches `GrassDry_A/B/C`, les buissons `Bush_Twig` et `BushDry_B`
et les rochers `Rock_A_01/B_01/C_01` composent les accotements et la lande.
Leurs couleurs sont atténuées pour cette scène hivernale. Les plantes
bougent au vent ; les rochers ont une collision et une légère couverture
neigeuse. Ils utilisent le maillage intermédiaire LOD02 du pack. Les
placements dépendent de la graine et évitent les chemins, les clairières,
les bâtiments, les troncs et le point de départ.

Les arbres du manifeste reçoivent les couronnes `Conifer`, `Pine_A`, `Pine_B`
et `Pine_D` du pack. Le pied, la collision et l’abattage sont conservés.
Chaque arbre utilise trois niveaux de détail, puis disparaît à distance.
Les masques SpeedTree utilisent leurs propres canaux : lissage rouge,
métal vert, occlusion bleue. La couverture des aiguilles est préservée dans
les textures réduites pour éviter une forêt transparente au loin.

La roche couvre aussi les flancs du socle des terrasses. Des variations de
teinte et de strates cassent la répétition. Les normales des montagnes sont
adoucies sans ajouter de triangles ni modifier leurs collisions. Les blocs
de Rocks and Boulders 2 habillent les cassures et les éboulis du piton.

Les originaux sont rangés sous `unity/Assets/Vendor/TerrainDemoScene_HDRP/`,
avec leurs fichiers `.meta`, qui portent leurs identifiants. Cet emplacement
et l'emplacement d'import initial `Assets/TerrainDemoScene_HDRP/` sont
acceptés et ignorés par git. Conserver une seule copie. Les matériaux et
prefabs adaptés sont reconstruits par :

```powershell
py local3d/atelier_citadelle.py unity
py local3d/atelier_citadelle.py parcours
py local3d/atelier_citadelle.py visite
```

La commande isole les scripts du tutoriel dans une assembly conditionnelle,
c'est-à-dire un groupe de scripts exclu de la compilation courante. Ils ne
demandent donc plus Visual Scripting à la citadelle. Le symbole
`FORGE_TERRAIN_SAMPLE_TUTORIEL` permet de les réactiver dans un projet avec
les dépendances du tutoriel. Les scènes de démonstration, leurs terrains et
leurs réglages HDRP ne sont pas importés dans la citadelle.

Après sauvegarde et réouverture, `terrain-sample-verification.json` contrôle
les surfaces, les textures, les accès, les rochers et leurs collisions.
Trois contre-épreuves retirent un matériau, déplacent un objet sur le
point de départ puis masquent une couronne : le contrôle doit refuser
chacune avant restauration.
Si le pack manque, les surfaces d'origine sont conservées et les compteurs
du rapport valent `-1`. Les captures `unity_lande.png` et `unity_roche.png`
montrent les assets de près ; `unity_vallee.png` montre leur implantation.
Cette adaptation est propre à Unity et ne change pas les exports Blender.

## Limites de cette passe

Les maisons et la cathédrale n'ont pas d'intérieurs aménagés. Les quatre clairières accueillent le chantier modulaire jouable. L'abattage montre la chute du sapin, sans inventaire ni économie
de bois. Les gardes sont statiques. La neige, les fumées et les feux restent des
effets visuels. Le branchement au moteur historique relève d'un travail distinct.
Cette évolution améliore le relief et les accès ; elle ne constitue pas une
validation de qualité AAA ni une mesure de performance sur plusieurs machines.

## Budget de rendu et mesure

La visite est plafonnée à 60 images/s pour éviter de consommer toute la
carte graphique sur les vues faciles. Réglages : rendu à 90 % de la
résolution de fenêtre, anticrénelage 2×, ombres à 180 m et carte 2048 pixels,
deux cascades, occlusion en demi-résolution, quatre lumières secondaires
par objet. Les arbres immobiles n’exécutent plus de mise à jour par image.
Les textures des packs réellement utilisées sont limitées à 1024 pixels ;
l’atlas des bâtiments garde 2048 pixels. Les objets immobiles compatibles
sont regroupés lors de la compilation. Le rendu SRP Batcher reste désactivé
à cause du défaut de matériaux constaté précédemment sur ce projet.

`CitadelQuality.BuildPlayer` produit `sorties/joueur/Citadelle.exe`.
Le paramètre `-forge-benchmark -forge-output CHEMIN` mesure les deux scènes
sur huit vues mobiles, avec huit maisons ajoutées au chantier, avec neige dans la forêt et sur le pont. La cadence
est déplafonnée pendant cette mesure uniquement. Chaque vue chauffe trois
secondes puis est chronométrée six secondes ; les captures sont prises
ensuite. Une capture uniforme invalide le contrôle. Le rapport donne la
médiane, les 95e et 99e centiles, le matériel et la mémoire allouée par Unity.
L’objectif passe seulement si le 95e centile reste sous 16,67 ms partout.
Cela ne mesure ni les watts ni toutes les configurations possibles.

PB Frontier Settlement demeure incomplet : l’audit des identifiants est
conservé dans `sorties/diagnostic/frontier-dependances.json`. Il manque
notamment les murs `fi_vil_wall01_01` et les toits `fi_vil_roof_thatch01_1X2_D`.
Le cache local du paquet PB contient les plans seuls (environ 166 ko) ;
les maillages manquants ne peuvent pas être reconstruits à partir de ceux-ci.

Pour jouer sans l’éditeur : lancer `Jouer_Citadelle.cmd` à la racine.
F7 cadre la forge ; F1/F2 changent de disposition. Pour reconstruire
et remesurer : `py local3d/atelier_citadelle.py performance`.

## Cohérence du paysage et des façades

Le piton secondaire situé à côté du pont est retiré à la source dans
`fabriquer.py`, avec ses six falaises, ses remparts, ses gardes et ses feux.
Le plateau de la citadelle et le parcours du pont restent raccordés.

La forêt compte 1 600 arbres par disposition, regroupés en cinq massifs,
avec 3,2 m minimum entre les troncs. Les clairières, seuils et chemins sont
exclus avant le placement. Le fichier Blender, le manifeste et Unity
partagent ces nouveaux emplacements. Les couronnes sont élargies de 24 %
et portent une neige permanente ; le shader garde des zones sombres sous
les branches, sans ajouter de maillage ni de carte de texture.

`CitadelArchitecture.cs` adapte les façades, soubassements et charpentes
avec les vraies zones de pierre et de bois de `fe_village_base.png` et sa
carte normale. Les zones se répètent sur les UV métriques des bâtiments ;
les textures ne sont ni copiées ni agrandies. Les anciennes teintes d’enduit
sont retirées. Les matériaux adaptés sont partagés entre les objets et
leurs niveaux de détail. La forge et l’écurie reçoivent aussi de la neige
sur les surfaces orientées vers le ciel.

La comparaison de la galerie utilise les captures antérieures à cette
passe, rangées dans `sorties/diagnostic/coherence/avant/`. Les distances entre
voisins et l’absence du piton secondaire sont relevées dans
`sorties/diagnostic/coherence/implantation.json`.


## Habitations modulaires et chantier jouable

`habitat.py` définit les pièces et les compositions. La bibliothèque exporte
`habitat.json` et un FBX par module, avec trois niveaux de détail. Les nouvelles
maisons portent les identifiants `maison_modulaire_*`. La source manuelle
`maison_gothique_0.blend` et les anciennes maisons restent disponibles.

Le rez-de-chaussée et les étages mesurent 6 × 6 m, pour 3 m de hauteur.
La trame de pose est de 0,75 m ; un demi-étage vaut 1,5 m. Les deux variantes
avec porte desservent une galerie ; les autres étages restent fermés.
L'escalier monte de 3 m et rejoint le plancher de la galerie. La pièce de
passerelle peut prolonger des appuis existants. Les textures d'enduit et de
brique proviennent aussi de l'atlas Blacksmith, partagé avec sa pierre et son
bois. Blender conserve ses cartes procédurales de travail pour ces surfaces.

Unity fabrique `Prefabs/Habitat/Kit_Habitat.asset`. Les maisons proches
assemblent des pièces qui partagent leurs maillages ; leurs deux niveaux
lointains sont fusionnés. Chaque maison garde son identité et un seul groupe
de détail. Les pièces individuelles ont leurs propres niveaux de détail et
collisions. `habitat-verification.json` contrôle les références de maillage,
les raccords et les rotations après réouverture ; déplacer une pièce doit
faire échouer le contrôle.

Dans la visite, **B** ouvre le chantier. Les flèches du panneau choisissent
une des quatre clairières ; six maisons complètes sont disponibles, ainsi
que toutes leurs pièces. Le clic pose, **R** tourne de 90°, **Suppr** retire
la pièce pointée, **Ctrl+Z** annule la dernière pose. Les boutons de hauteur
ou Page précédente/suivante déplacent le plan de pose de 1,5 m. Une maison
complète reste ensuite démontable pièce par pièce. Le bouton « Marcher près
de la construction » permet de parcourir les escaliers et galeries.

Les appuis, superpositions et limites du terrain sont vérifiés avant la pose.
Un support portant un étage ne peut pas être retiré avant ce dernier.
Le plafond est de 120 pièces, sans achat, inventaire ni simulation économique.
Les constructions sont enregistrées par scène dans le dossier persistant
Unity, fichier `habitat_<nom-scene>.json`, avec sauvegarde précédente `.bak`.
Une sauvegarde invalide est refusée entièrement. Le catalogue du chantier
référence les mêmes prefabs que les maisons initiales.

`py local3d/atelier_citadelle.py construction` construit le joueur et contrôle
les refus, les poses, la sauvegarde/relecture, les entrées B/R/clic et la
montée réelle d'un escalier. Ses fichiers restent dans `sorties/construction/`,
séparés des constructions personnelles. `performance` mesure aussi la vue
des colombages et celle du chantier chargé, toujours dans le vrai joueur.

Dans Unity, déposer les prefabs `Citadelle/Prefabs/habitat_*.prefab` pour
assembler des pièces avec collisions et niveaux de détail. Le sous-dossier
`Habitat/Pieces` sert à l'affichage proche des maisons composées. Pour changer
la géométrie et les recettes des nouvelles habitations à la source, modifier
`habitat.py`, puis reconstruire la bibliothèque et les scènes.
