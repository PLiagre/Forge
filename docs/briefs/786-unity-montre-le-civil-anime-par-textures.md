# Lot #786 — Unity montre le civil animé par textures
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Unity importe la silhouette civile cuite par #785 et montre sa marche articulée par texture, sur place et sans squelette.

## Le joueur
Lot de fond découpé de #421 « Les gens du bourg circulent dans les rues » : il prépare le geste de J4, entrer dans sa capitale et y marcher parmi ses habitants. Le joueur peut voir un civil de Biskra marcher avec des bras et des jambes animés, et sentir les prémices d’une ville habitée plutôt qu’un décor immobile. Ce lot prouve le rendu d’un civil témoin à position fixe ; le sous-lot 6 de #421 le fera circuler dans les rues d’après les effectifs et les trajets. Dépend de : #785.

## Règle du monde
Sans objet : import et rendu de vue, sans règle du monde ni modification de `jeu/sim/MODELE.md`. L’apparence plausible de niveau 2, les poses, les couleurs et les durées viennent entièrement de `civil.vat` livré par #785. Unity ne déduit ni personne, ni métier, ni vitesse, ni trajet ; il ne fait que rejouer les sommets cuits.

Copier `3d/local3d/civils/sorties/civil.vat` à l’identique dans le projet actif. Un `ScriptedImporter` de `.vat` relit le contrat `VAT1` de #785 et expose comme sous-assets un maillage, une texture et un matériau, sans asset dérivé versionné : C coins déroulés et triangles `(0,1,2)…`, positions, normales et couleurs de référence ; texture linéaire `RGBAHalf` de `2*C × 48`, filtrage `Point`, bouclage `Clamp`, positions puis normales et une ligne par image ; matériau utilisant `Forge/CivilVAT`. Refuser signature, longueur, compte, clips, valeur non finie ou normale incohérente. Exiger exactement `marche` 24 images / 1,15 s puis `repos` 24 images / 4 s. Les bornes du maillage couvrent toutes les poses.

Le shader URP reçoit la phase de marche dans `[0,1[`, interpole les deux lignes voisines en bouclant, anime position et normale par `SV_VertexID`, éclaire les couleurs cuites et permet de teinter seulement la tunique marquée par alpha 1. `_VATActif = 0` rend strictement le maillage de référence, indépendamment de la phase. Changer la phase ne déplace jamais le `Transform` : la marche reste sur place, la translation appartiendra au futur passant.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/ImporterCivil.cs
3d/unity/Assets/ForgeLocal3D/Editor/ImporterCivil.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot786.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot786.cs.meta
3d/unity/Assets/ForgeLocal3D/Desert/Civils/civil.vat
3d/unity/Assets/ForgeLocal3D/Desert/Civils/civil.vat.meta
3d/unity/Assets/ForgeLocal3D/Desert/Shaders/Civil.shader
3d/unity/Assets/ForgeLocal3D/Desert/Shaders/Civil.shader.meta
docs/briefs/786-unity-montre-le-civil-anime-par-textures.md

## Conditions de succès
SC1 — Import exact, rouge d’abord. Depuis la racine sur le PC Windows, éditeur fermé, commande I :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -quit -projectPath 3d/unity -executeMethod ForgeLocal3D.ImporterCivil.Verifier -logFile 3d/unity/Temp/lot786-import.log
```
Avant l’importeur, I échoue ; après, elle force la réimportation, vérifie l’égalité SHA-256 des deux VAT, les noms et paramètres des clips, C, les triangles, couleurs, bornes, format, dimensions et réglages de texture, ainsi que le shader et ses références, puis sort 0 avec un bilan non vide. Contre-épreuve : rejouer I avec `-forge786TronquerVat` tronque les octets en mémoire avant de passer par le même lecteur ; la commande doit sortir non zéro pour longueur invalide, sans modifier aucun fichier.

SC2 — La texture change réellement la pose, pas la place. Commande P, avec rendu, sans `-nographics` ni `-quit` :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 786 -forgeCaptures 3d/unity/Temp/lot786-photo -logFile 3d/unity/Temp/lot786-photo.log
```
Le scénario charge les trois sous-assets importés, pose un seul civil, garde exactement le même `Transform`, rend successivement les phases 1/4 et 3/4 dans le même cadrage et écrit `lot786-quart.png`, `lot786-trois-quarts.png` et `lot786-rapport.json`. Il exige le civil entier dans le champ et une part non nulle, mesurée et publiée, de pixels différents dans son rectangle ; le rapport porte phase, position, rotation, échelle, rectangle, pixels comparés et pixels changés. Contre-épreuve C : la commande de la section Photo avec `-forge786SansAnimation` doit sortir non zéro après avoir produit ses deux images et son JSON ; elle exige zéro pixel changé et échoue précisément parce que la marche a disparu.

SC3 — La marche se voit. Commandes : P puis C. Ouvrir soi-même les quatre PNG propres aux scénarios : avec P, pieds et bras alternent nettement entre les deux phases, le civil reste au même endroit, entier, éclairé et tourné de trois quarts ; avec C, les deux images sont identiques. Le scénario final de P produit aussi une capture `*--marche-position-fixe.png` et une trace `CAPTURE_SCENARIO_OK`. Contre-épreuve : pose figée, glissement du corps entier, faces retournées, silhouette hors champ, membres détachés ou différence provenant d’un cadrage déplacé refuse la livraison, même si l’import est vert.

SC4 — Acquis, périmètre et budget. Commandes : I, P, `git diff --check`, `git diff --name-only`, `git diff --numstat` et `git ls-files --others --exclude-standard`. Le VAT copié reste identique à celui de #785 ; aucun test existant ne change et les archives restent intactes. Compter fichiers neufs, métadonnées et brief : moins de 300 lignes ajoutées et supprimées, cible 290, environ 75 d’importeur, 65 de shader, 65 de capture, 20 de métadonnées et 65 de brief ; le VAT est binaire. Contre-épreuve : source divergente, chemin supplémentaire, asset dérivé versionné ou total ≥ 300 refuse la livraison.

## Hors périmètre
Tout autre chemin est interdit. Aucun changement de simulation, service, contrat, lecteur, population, métier, destination ou plan. Pas de composant de foule, trajet, translation, vitesse, collision, horaire, affectation aux chantiers, branchement dans la capitale ni optimisation de #422 ; les comptes de #784, les trajets de #787 et leur intégration appartiennent aux autres sous-lots de #421. Pas de squelette Unity, prefab, scène enregistrée, pack externe, fichier d’archive, clip de combat ou asset dérivé committé. Aucun test existant n’est modifié ou assoupli.

## Photo
`Lot786.cs` expose `[ScenarioDeCapture(786, "marche-position-fixe")]`. Il charge le maillage, la texture et le matériau depuis `Assets/ForgeLocal3D/Desert/Civils/civil.vat`, place le civil sur un sol visible près de Biskra et cadre son corps entier avec `DesertCityCamera.Poser`. Dans une même image du jeu, sans déplacer caméra ni objet, il rend et enregistre la phase 1/4, puis la phase 3/4 ; il laisse cette dernière pose à `Photographier`. Toute référence absente, image antérieure déjà présente, mesure vide, objet hors champ ou `Transform` changé lève une erreur. Les dossiers ci-dessous doivent donc être neufs.

Photo, commande P complète :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 786 -forgeCaptures 3d/unity/Temp/lot786-photo -logFile 3d/unity/Temp/lot786-photo.log
```
Contre-épreuve, commande C complète :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 786 -forgeCaptures 3d/unity/Temp/lot786-sans-animation -forge786SansAnimation -logFile 3d/unity/Temp/lot786-sans-animation.log
```
P sort 0 ; C sort non zéro seulement après avoir écrit son rapport. Joindre au compte rendu les deux images de phase, `lot786-rapport.json` et le journal de chaque dossier. P, qui a le moins de drapeaux, fournit la photo du lot ; C montre la contre-épreuve animation désactivée.
