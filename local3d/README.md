# Atelier 3D local — Forge

Le travail courant est la **citadelle gothique alpine enneigée** :
[guide et retouches](citadelle/README.md), [galerie et visite animée](citadelle/sorties/index.html).
Son équivalent chaud est le **ksar du désert** :
[guide et retouches](desert/README.md), [galerie et visite animée](desert/sorties/index.html).
L'étude précédente conserve le **kit alpin réutilisable** :
[guide](alpin/README.md), [galerie et visite animée](alpin/sorties/index.html).
La V2 à quatre biomes reste consultable : [guide V2](GUIDE_V2.md),
[galerie V2](v2/index.html).
La documentation ci-dessous conserve le mode d'emploi de la première scène.

Ce dossier est le poste de fabrication Blender et de vérification Unity de
Forge sur ce PC. Le dépôt de référence est `PLiagre/Forge` ; le travail local
vit dans `ForgeLocal3D`, sur la branche `codex/blender-v1`.

## Ouvrir la scène

- À la racine, double-cliquer sur `Ouvrir_Blender_V1.cmd`.
- Le fichier principal est `local3d/v1/Forge_Village_V1.blend`. Les textures utilisées
  sont embarquées. Les deux caméras donnent une vue générale et une vue de la place.
- Pour Unity, double-cliquer sur `Ouvrir_Unity_V1.cmd`, puis utiliser Play.
  La scène est `unity/Assets/ForgeLocal3D/Scenes/Forge_Village_V1.unity`.
  Flèches : déplacement ; molette : zoom ; clic droit : orbite ; F : retour ; H : aide.

## Ce qui est livré

Le **village pilote déjà décrit dans le dépôt** est matérialisé : 40 bâtiments,
140 × 140 mètres, terrain lu dans le plan existant, 250 décors. La géométrie
visible compte 201 288 triangles, sous le plafond de 300 000 du catalogue.

Les 24 variantes couvrent résidence, grenier, entrepôt, marché, forge,
grange, chapelle et scierie. Chaque bâtiment dispose de trois niveaux de
détail (LOD) dans son FBX. Les dix recettes de décor produisent arbres,
buissons, rochers, herbe, clôtures, puits, étals, tonneaux et caisses.

| Chemin sous `local3d/v1/` | Contenu |
|---|---|
| `Forge_Village_V1.blend` | Scène complète, collections, caméras et textures embarquées |
| `assets/` | 34 bibliothèques `.blend` à charger avec Fichier → Ajouter, et 34 FBX |
| `exports/Forge_Village_V1.fbx` | Géométrie complète de la scène, à échelle métrique |
| `textures/` | Les six cartes PBR 2048² reconstruites depuis la recette du dépôt |
| `renders/` | Vues calculées dans Blender et capture de contrôle Unity |
| `rapport.json` | Géométrie, budgets, graines, marqueurs et matériaux mesurés |
| `verification.json` | Réouverture du `.blend` et réimport du FBX |
| `unity-verification.json` | Résultat de la construction réelle dans Unity |

## Sources et limites

L'implantation et les hauteurs viennent de
`fabrique/donnees/Manifests/village_pilot.json`. Les bâtiments utilisent
`fabrique/Blender/generate_building_family.py`, `building_kit.py`, le catalogue
`building_pilot.json` et le style `frontier.json`. Les textures proviennent
de `texture_citylab_trim_v2.json`. Ces sources ne sont pas modifiées.

Les binaires Git LFS historiques manquent sur le serveur. Les décors tiers
référencés par l'ancien plan sont donc **remplacés par des créations Blender
locales**, aux emplacements du plan. Aucun fichier Vendor n'est importé et
aucune identité avec les anciens modèles n'est revendiquée.

Cette livraison est une **V1 graphique de visite** du bourg pilote. Elle ne
branche pas la ville au moteur de simulation et ne rétablit pas les assets
historiques manquants. La validation artistique reste à examiner.

Unity peut encore signaler les trois anciens FBX de scierie manquants dans
`Packages/com.victoria.citymode.assets/Runtime/Content/City/`. La scène locale
utilise les nouveaux modèles de `Assets/ForgeLocal3D/` et s'ouvre avec ses
matériaux résolus. Son rendu désactive le regroupement SRP après constat
visuel d'un mélange des couleurs entre sous-maillages sur cette version.

## Reproduire

Outils utilisés : Blender 5.2.0 LTS, Unity 6000.0.43f1, URP 17.0.4,
Python via `py` avec NumPy et Pillow. Depuis la racine :

```powershell
.\local3d\reconstruire.ps1              # Blender et vérification du FBX
.\local3d\reconstruire.ps1 -AvecUnity   # ajoute l'import et la scène Unity
```

La reconstruction réécrit les livrables de `local3d/v1/`. Sauvegarder une copie
avant de l'exécuter si la scène a été retouchée à la main. Le constructeur
Unity réécrit uniquement la scène locale, ses matériaux et ses réglages de
rendu ; la scène locale devient la scène de démarrage du projet Unity.

Les bibliothèques d'assets conservent des chemins relatifs vers `../textures/`.
Garder ces dossiers ensemble. La scène principale est autonome grâce aux
textures embarquées. Les exports sont préparés localement ; aucun envoi vers
GitHub n'est effectué par ces scripts.
