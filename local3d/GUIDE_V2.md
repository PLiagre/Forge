# Atelier 3D — villages V2

Quatre scènes Blender complètes et quatre scènes Unity de visite. Les paysages
et les implantations sont des études graphiques plausibles, de fidélité 2.
Leur configuration ne modifie pas le moteur historique. La V1 reste disponible.

## Ouvrir et comparer

Depuis la racine, `Ouvrir_Blender_V2.cmd` ouvre Val d’Aulne et
`Ouvrir_Unity_V2.cmd` ouvre sa visite. `Ouvrir_Galerie_V2.cmd` présente les rendus.

| Variante | Paysage | Architecture | Scène Blender |
|---|---|---|---|
| `val_aulne` | Rivière, bois de feuillus, prairies | Colombages, toitures mixtes, ateliers | `v2/villages/val_aulne/val_aulne.blend` |
| `hautes_roches` | Torrent, relief élevé, conifères, neige en altitude | Chalets et balcons | `v2/villages/hautes_roches/hautes_roches.blend` |
| `port_cypres` | Fleuve large, oliviers et cyprès | Pierre claire et tuiles | `v2/villages/port_cypres/port_cypres.blend` |
| `oasis_ocres` | Oasis, palmeraie, relief rocheux et sol aride | Terre crue, terrasses et pergolas | `v2/villages/oasis_ocres/oasis_ocres.blend` |

Dans Blender, les textures utilisées sont embarquées dans chaque scène.
Les collections séparent architecture, nature, accessoires, terrain et studio.
La caméra **Village** montre les maisons ; **Territoire** montre le paysage entier.
Choisir une caméra dans l'Outliner puis `Ctrl + Pavé numérique 0` pour l'activer.

Dans Unity, les scènes sont dans `Assets/ForgeLocal3D/V2/Scenes/`.
Lancer **Play**. Les boutons ou F1–F4 changent de village. Flèches : déplacement ;
molette : zoom ; clic droit : rotation ; clic milieu : glissement ; F : retour ; H : aide.
Les raccourcis correspondent aux variantes de la dernière commande de transfert.

## Fabriquer sans perdre les retouches

Depuis la racine du dépôt, dans PowerShell :

```powershell
py local3d/atelier.py catalogue
py local3d/atelier.py fabriquer --variante val_aulne --qualite apercu
py local3d/atelier.py fabriquer --variante toutes --qualite final --unity
```

La qualité `apercu` produit des images 1280 × 840 à 20 échantillons ; `final`,
1920 × 1260 à 64 échantillons. La géométrie reste identique. La fabrication
réutilise les étapes inchangées ; `--force` les rejoue. Les graines rendent
l'implantation reproductible. Une modification de recette ne demande pas de
réécrire les générateurs.

Pour retoucher un modèle à la main :

```powershell
py local3d/atelier.py edition --asset colombage_maison_0
```

Ouvrir `local3d/sources_v2/colombage_maison_0.blend` dans Blender. Le fichier
n'est créé que s'il manque. Retoucher et enregistrer ce fichier, puis relancer
la fabrication. Le générateur reprend cette source en priorité ; il ne la réécrit
jamais. La bibliothèque commune est réexportée après une retouche ; les scènes
demandées sont ensuite réassemblées. Il ne s'agit pas d'une reconstruction
individuelle des seuls FBX modifiés.

Un asset conserve trois objets : `IDENTIFIANT_LOD0`, `IDENTIFIANT_LOD1`,
`IDENTIFIANT_LOD2`. Un **LOD** est une géométrie moins détaillée affichée au loin.
Le LOD0 est visible à l'ouverture ; les autres sont masqués dans la vue.
Retoucher aussi leurs formes lorsque la silhouette change. Garder l'origine
au sol, les transformations appliquées, les noms et les matériaux existants.
Les LOD doivent rester non vides et décroître en nombre de triangles.
L'atelier refuse un modèle qui ne respecte pas ces conditions.

Pour changer les couleurs ou les matières communes, modifier les palettes de
`atelier_v2/recettes.json` et les recettes de `atelier_v2/textures.py`.
Les matériaux Unity lisent les textures exportées ; un matériau Blender arbitraire
à nœuds n'est pas converti automatiquement.

Les scènes de `v2/villages/`, les FBX et les fichiers Unity V2 sont des sorties
reconstruites. Une retouche d'implantation durable se fait dans `plan.py` ;
une modification de peuplement dans `recettes.json`. Une modification directe
de scène doit être enregistrée sous un autre nom avant reconstruction.

## Organisation

| Source ou sortie | Rôle |
|---|---|
| `atelier_v2/recettes.json` | Biomes, styles, graines, densités et budget graphique |
| `atelier_v2/plan.py` | Implantation, chemins, relief et échantillonnage du sol |
| `atelier_v2/assets.py` | Géométrie des bâtiments, arbres et accessoires |
| `atelier_v2/geometrie.py` | Assemblage des maillages, UV et export FBX |
| `atelier_v2/textures.py` | Couleur, normales et rugosité procédurales |
| `atelier_v2/fabriquer.py` | Bibliothèque et assemblage Blender |
| `sources_v2/` | Sources Blender retouchées à la main, prioritaires |
| `v2/bibliotheque/` | Catalogue mesuré, bibliothèque Blender et FBX avec trois LOD |
| `v2/textures/` | Textures partagées ; garder ce dossier avec la bibliothèque |
| `v2/villages/VARIANTE/` | Scène, paysage FBX, placements JSON, hauteurs et contrôles |
| `v2/villages/VARIANTE/renders/` | Deux cadrages Blender et deux cadrages Unity |
| `v2/cache/`, `v2/logs/` | Cache local et journaux, exclus de Git |

Les positions exportées sont en mètres, avec Z vertical dans Blender.
L'import FBX Unity les convertit en `(-x, z, -y)`, et inverse la rotation autour
de la verticale. Cette conversion est mesurée sur les sommets du terrain importé.
Les scènes Unity partagent les mêmes
prefabs, matériaux et textures. Les petits objets utilisent l'instanciation
GPU lorsqu'elle est applicable, et chaque instance possède un groupe de LOD.
Les trois géométries d'un même modèle ne sont pas affichées simultanément.

## Vérifier une livraison

```powershell
py local3d/atelier.py verifier --variante toutes
py local3d/atelier.py unity --variante toutes
```

Le premier contrôle réouvre les `.blend`, mesure leurs instances et triangles,
vérifie les textures embarquées, puis réimporte les paysages FBX. Il compare
l'implantation à la recette régénérée. Une contre-épreuve déplace volontairement
une instance en mémoire et exige que le contrôle la refuse.

Unity compile réellement les scripts, compare chaque FBX de LOD au catalogue,
résout les matériaux, sauvegarde puis réouvre les scènes et produit ses captures.
Les résultats sont dans `verification.json` et `unity-verification.json` de chaque
village. Les images doivent aussi être regardées : les chiffres ne prouvent
pas la qualité d'une silhouette, d'une rive ou d'un cadrage.

La visite utilise URP, sans SRP Batcher : un mélange de couleurs entre
sous-maillages avait été constaté sur ce poste avec ce regroupement actif.
L'atelier installe ses réglages de rendu et ajoute ses scènes au démarrage Unity.
Fermer Unity avant le transfert en mode commande.

## Dépendances et périmètre

Blender 5.2 LTS, Unity 6000.0.43f1 avec URP 17.0.4, `py`, NumPy et Pillow.
Les chemins des deux exécutables se règlent dans `atelier.py`.
Ces dépendances restent dans l'atelier graphique ; elles n'entrent pas dans `sim/`.
Les textures et les modèles sont produits localement, sans assets tiers téléchargés.

Cette livraison améliore les scènes et leur fabrication. Elle ne contient pas
encore d'habitants animés, d'intérieurs jouables ni de branchement de la simulation
aux bâtiments. L'eau et les arbres sont statiques. Les validations mesurent la
géométrie et l'import, pas un objectif de fréquence d'affichage. Les scripts
n'envoient rien sur GitHub.
