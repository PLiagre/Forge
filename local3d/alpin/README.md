# Kit alpin — une bibliothèque, plusieurs villages

Le travail porte sur un **village de vallée alpine, en 1400, de culture alpine
centrale**. Cette désignation est une direction artistique plausible de niveau 2.
Les dispositions changent ; le biome, la typologie, l'année, la culture et le
catalogue de modèles restent identiques.

## Voir le résultat

- À la racine, `Ouvrir_Unity_Alpin.cmd` ouvre Unity et lance Play.
- `Ouvrir_Blender_Alpin.cmd` ouvre la Combe du Moulin avec ses textures embarquées.
- `Ouvrir_Galerie_Alpine.cmd` montre les dispositions, les météos et la vidéo.

Dans Unity, les boutons F1–F3 changent de disposition. Le panneau règle l'heure,
les éclaircies, le couvert, la brume, la pluie et la neige. L'eau défile, le vent
agit sur les arbres et le linge, la roue tourne, les cheminées fument. Le soir,
les fenêtres s'éclairent. La pluie assombrit les surfaces ; la neige apparaît
progressivement sur les faces exposées vers le haut.

Flèches : déplacer la caméra ; molette : zoom ; clic droit : tourner ; clic milieu :
glisser ; F : vue générale ; H : masquer les commandes.

Blender propose trois caméras : **Territoire**, **Village**, **Moulin**. Sélectionner
une caméra puis `Ctrl + Pavé numérique 0` l'active. La barre d'espace joue
les animations de la roue, du vent et de l'eau sur la plage de 240 images.
Le panneau météo et les précipitations sont propres à la visite Unity.

## Réutilisation réelle

Le kit contient 67 modèles : bâtiments, conifères et petits modules de décor.
La roue du moulin est un objet distinct, avec son origine au centre de l'axe.
Bûches, bancs, lanternes, linge, fleurs, abreuvoirs et murets sont des assets
indépendants. Chaque FBX contient trois LOD, c'est-à-dire des géométries adaptées
à différentes distances. Les objets déjà très simples peuvent garder la même
géométrie à plusieurs distances.

Les trois dispositions livrées utilisent **exactement le même catalogue** :

| Disposition | Graine |
|---|---:|
| Combe du Moulin | 7141 |
| Rive des Mélèzes | 8249 |
| Val des Roches | 9359 |

Une graine est le nombre qui fixe les choix de génération. Elle change le relief,
le tracé du torrent, le chemin principal, les maisons et les peuplements végétaux.
Rejouer la même graine donne le même plan. La scène exporte les identifiants des
assets et leurs transformations ; elle ne fabrique pas une copie unique du modèle
pour chaque maison. Dans Unity, les instances renvoient aux prefabs communs.

## Produire une autre disposition

Depuis la racine du dépôt, avec Unity fermé :

```powershell
py local3d/atelier_alpin.py fabriquer --disposition toutes --unity
py local3d/atelier_alpin.py fabriquer --graine 7001 --unity
```

La seconde commande crée `sorties/villages/alpin_7001/` avec le même kit.
La dernière sélection transférée détermine les boutons disponibles dans Unity.
Pour restaurer les trois dispositions de référence, relancer la première commande.

`recette.json` fixe le contexte, les densités et le budget. `paysage.py` porte le
relief et les placements ; `assets.py`, les modèles ; `textures.py`, la palette ;
`fabriquer.py`, l'assemblage Blender. Les éléments géométriques communs viennent
de `../atelier_v2/`. Il n'y a pas de dépendance de `sim/` vers cet atelier.

L'année et la culture sont fixées pour ce kit. Les changer dans les métadonnées
ne crée pas automatiquement une autre architecture historique.

## Retoucher un asset dans Blender

```powershell
py local3d/atelier_alpin.py edition --asset alpin_maison_0
```

Ouvrir `sources/alpin_maison_0.blend`, le retoucher et l'enregistrer. La commande
ne réécrit jamais une source existante. La reconstruction reprend cette source
en priorité dans toutes les dispositions. Un fichier de départ est déjà fourni.

Conserver les trois objets `alpin_maison_0_LOD0`, `..._LOD1`, `..._LOD2`, leurs
matériaux et leur origine métrique. Appliquer les transformations avant de sauver.
Les LOD1 et LOD2 sont masqués à l'ouverture ; les actualiser lorsque la silhouette
change. Le générateur refuse un LOD absent, vide ou plus dense que le précédent.
Les matériaux Blender arbitraires ne sont pas convertis automatiquement : les
textures et les palettes communes se modifient dans leurs recettes.

Les fichiers de `sorties/` et les scènes Unity sont reconstruits. Les modifications
durables vivent dans les recettes ou `sources/`. Le cache évite de rejouer les
étapes inchangées ; `--force` les rejoue. Une retouche de source réexporte le kit
commun, puis réassemble les dispositions demandées.

## Contrôles et captures

```powershell
py local3d/atelier_alpin.py verifier --disposition toutes
py local3d/atelier_alpin.py visite
```

La première commande réouvre les scènes Blender, mesure les instances et les
triangles, vérifie les textures embarquées, réimporte les paysages FBX et mesure
la roue à deux instants. Un déplacement volontaire en mémoire doit faire échouer
le contrôle. Les plans doivent être distincts et partager la même empreinte de
catalogue.

Le transfert Unity vérifie chaque LOD, l'échelle, les matériaux et la conservation
des instances après sauvegarde. Des sommets du terrain servent de repères pour
contrôler la conversion mesurée du FBX : `(-x, z, -y)` et rotation verticale inversée.

`visite` ouvre le vrai mode Play, contrôle la rotation, les particules, l'éclairage
du soir et le passage aux deux autres dispositions. Il produit six captures et
une vidéo de 12 secondes dans `sorties/visite/`. Cette commande demande les trois
dispositions de référence construites, Unity fermé, et FFmpeg dans le PATH.

Les résultats sont dans `villages/NOM/verification.json`,
`villages/NOM/unity-verification.json` et `visite/verification-play.json`.
Les rendus doivent aussi être regardés : les mesures ne prouvent pas à elles
seules la qualité des lumières ou des rives.

## Périmètre

Blender 5.2 LTS, Unity 6000.0.43f1 et URP 17.0.4, NumPy, Pillow, FFmpeg pour
la vidéo. Les modèles et textures sont fabriqués localement. Rien n'est envoyé
sur GitHub par ces commandes.

La météo, la fumée, l'eau et les lumières sont des effets de présentation.
Ils ne prétendent pas simuler un climat ou le fonctionnement économique du moulin.
Cette scène ne comporte pas encore d'habitants animés, d'intérieurs ni de connexion
aux bâtiments de la simulation. Aucun objectif de fréquence d'affichage n'est
revendiqué sans mesure sur la visite.
