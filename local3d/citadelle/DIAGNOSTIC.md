# Citadelle alpine — diagnostic et évolution du 15 septembre 2026

## Lecture de l'existant

La référence est `reference.png`. Les deux scènes Blender existantes ont été
rouvertes avec Blender 5.2, puis photographiées sans enregistrer leurs modifications.
Les vues générales, de porte et de cathédrale ont été conservées. Deux cadrages
supplémentaires montrent le pont et le parvis à environ 1,7 m du sol.
Les preuves avant retouche vivent dans `sorties/diagnostic/avant/`.

| Sujet | Écart observé | Travail dans les sources de fabrication |
|---|---|---|
| Silhouettes | Flèches striées de bandes régulières ; cathédrale peu sculptée | Nervures, fleurons, gâbles, corniches et chanfreins |
| Architecture | Verre posé sur les murs ; menuiseries répétitives | Ébrasements, appuis, remplages, consoles, volets et lucarnes |
| Parcours visuel | L'escalier dépasse sa terrasse et masque les portails | Hauteur de chaque marche corrigée ; même origine et même placement |
| Matériaux | Joints uniformes, pierre et bois peu différenciés | Cartes 1024², pierre de taille sans faux joints sur les moulures, grain et rugosité exportée |
| Neige | Bandes rectangulaires sur les couvertures | Couverture continue avec bord irrégulier et épaisseur réelle |
| Relief | Cônes lissés, ravines radiales uniformes | Plusieurs sommets asymétriques, ravinement, masque de neige dérivé des pentes |
| Végétation | Sapins en disques identiques | Branches tombantes, couronnes poreuses, amas de neige sur les faces supérieures |
| Implantation | Bourg peu dense, pieds de falaises trop nets | Maisons supplémentaires, réserves de bois, tonneaux, éboulis et lucarnes |
| Lumière | Éclairage bleu uniforme ; vitraux orange plats | Lumière froide plus neutre, torches chaudes, verre coloré dont le plomb reste sombre |
| Atmosphère Unity | Neige très dense masquant les détails ; surfaces peu sensibles à leur rugosité | Précipitations plus fines, éclairage PBR URP et occlusion des petits contacts |

PBR signifie que la lumière tient compte de la couleur, du relief fin, du caractère
métallique et de la rugosité de la surface. L'occlusion assombrit les petits creux
et les contacts calculés depuis la profondeur de l'image.

## Conservation et reconstruction

- Les 31 identifiants d'origine sont conservés. Deux modules complètent le kit :
  `lucarne_gothique` et `reserve_bois_tonneaux`.
- `sources/maison_gothique_0.blend` reste la source prioritaire. Sa géométrie ne
  reçoit pas les chanfreins automatiques. Les cartes communes sont actualisées
  lors de l'assemblage, sans enregistrer ce fichier de retouche.
- Les ajouts d'instances se font après les placements initiaux pour conserver
  leurs identifiants. Les fichiers `.meta` des prefabs Unity sont conservés.
- Le changement de hauteur de l'escalier est commun aux deux implantations et
  aux exports FBX. Sa mise à l'échelle existante raccorde désormais le sommet
  des marches à la terrasse de la cathédrale.
- `cameras.py` porte les dix cadrages. Le manifeste les transmet à Unity.
  Les trois caméras historiques gardent position, cible et focale.
- Toutes les retouches durables vivent dans les scripts de `local3d/citadelle/`
  et dans l'intégration Unity. Le moteur historique et la carte sont hors périmètre.

## Vérification visuelle

La galerie présente un comparateur avant/après pour chaque implantation et chaque
cadrage. Les images sont des rendus des scènes 3D. Les premiers rendus intermédiaires
ont conduit à remplacer les contours carrés de neige et à retirer le motif de
maçonnerie des pierres de moulure.

L'objectif AAA reste une direction artistique exigeante. La conformité technique
du workflow ne vaut pas, à elle seule, validation d'un niveau de production AAA.

## Reprise du 16 septembre : relief et accès

Le retour sur les images a confirmé des montagnes encore lissées, un socle en
colonnes trop verticales et un chemin qui quittait le pont sans desservir les
maisons. Une vue aérienne ne suffisait pas à vérifier les usages du lieu.

- Les falaises ont désormais un pied évasé, des cassures et des couches de
  schiste, granite et pierre oxydée. Le socle comporte six niveaux irréguliers.
- Les montagnes portent des ravines plus marquées et une carte de relief fin ;
  leur neige suit les pentes et laisse apparaître davantage de roche.
- Les chemins modèlent le terrain. Ils relient la place, le pont, le hameau,
  chaque seuil, quatre terrains libres et une clairière forestière.
- Le terrain utilise une grille continue. Les sections des chemins partagent
  les mêmes positions dans les virages pour éviter les fentes entre tronçons.
- Les maisons du hameau forment des îlots le long des rues. Les déplacements
  du hameau et de la forêt sont consignés dans les rapports de migration ; les
  identifiants et les sources manuelles restent conservés.
- Unity reçoit des collisions et un mode marche. Un contrôle parcourt les
  branches avec le même personnage, puis approche un tronc et essaie l'abattage.
- Quatre vues supplémentaires montrent la vallée, l'arrière de la citadelle,
  la rue et la lisière. Les cinq cadrages de comparaison restent disponibles.

Les maisons restent des extérieurs. Les terrains réservent la surface nécessaire
à une construction future. L'abattage anime la chute d'un arbre, sans inventaire,
économie de ressources ni modification du moteur historique.

## Reprise de l'habitat : une cité moins régulière

Le second retour demande de supprimer l'aspect lotissement : des maisons trop
isolées et alignées restent artificielles, même lorsque la rue ondule légèrement.

`urbanisme.py` remplace ces placements par des groupes mitoyens. Les largeurs et
profondeurs changent ; les façades avancent ou reculent, les corniches et les
faîtages se décalent. Des teintes de chaux et d'enduit différencient les maisons.
Les pièces générées reçoivent aussi de petites déformations cohérentes de leurs
poutres et de leurs murs, en conservant les pieds et les pivots. La source manuelle
reste prioritaire et n'est pas réenregistrée.

Les regroupements concernent le hameau et l'intérieur de la citadelle. Chaque
maison reste un objet distinct dans Blender et un prefab instancié séparément
dans Unity. Les ruelles desservent chaque seuil. La reconstruction, les autres
angles et le parcours physique vérifient ensemble cette composition plus dense.

L'examen du cadrage des îlots a aussi révélé des dessertes brunes trop nettement
découpées dans la neige. Leurs bords descendent maintenant vers le terrain ;
des textures de transition mêlent neige et sol par plaques. Cette correction
conserve les axes des chemins et la largeur centrale disponible pour marcher.
