# Lot #963 — La bande des modes en bas à droite de la carte
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
En bas à droite de la carte, une bande de trois commandes à icône (Puissances, Habitants, Flux) change la couleur de la carte. La légende du mode actif, de trois lignes au plus, se pose juste au-dessus, avec son infobulle. « Parcourir le monde » se réduit à 740 px.

## Le joueur
Le joueur regarde sa carte de 1400. En bas à droite, trois commandes à icône : une bannière pour Puissances, une foule pour Habitants, une flèche pour Flux. Au survol, chacune dit ce qu'elle fait. Il clique sur Habitants : les terres passent du clair au foncé selon leurs habitants. Juste au-dessus des commandes, une légende de trois lignes au plus dit comment lire ces couleurs. Au survol de la légende, une infobulle la redit entière et explique l'échelle. La légende reste à sa place : elle ne passe ni sous le feuillet ouvert à gauche, ni sous ses dossiers à droite, ni sous la barre du haut. Le temps continue de couler : changer de mode ne relit rien et n'arrête rien. C'est le premier des trois morceaux du geste « Les modes de carte » du jalon 4 (`CAP.md`, lot 20, #858). Ce geste sert la décision du jalon : le joueur doit trouver sa capitale et lire ses terres avant d'y descendre, sans chercher.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni le service ne sont touchés. La carte lit le monde déjà lu par le cabinet. Un clic sur un mode ne lance aucune lecture et ne touche pas l'horloge.

Ce que montre chaque mode est tranché ici (réponse A du propriétaire sur #858 : les détails vont dans l'infobulle de la légende). **Puissances**, le mode à l'ouverture comme aujourd'hui : chaque terre en pigment de sa maison, légende `CalquesCarte.LegendeDuCalque(null)` telle quelle. **Habitants** : du papier à l'accent, échelle logarithmique, légende `CalquesCarte.LegendeDuCalque(repartition)` telle quelle. **Flux** : toutes les terres en jeton `papier`, pour que les flèches se lisent, légende `"Flux : ce que vos lieux envoient à votre siège, et votre siège à son suzerain, sur trente jours · Rouge : territoire conservé"`. Dans les trois modes, la terre gardée reste en `alerte`.

## Périmètre
3d/unity/Assets/Interface/CalquesCarte.cs
3d/unity/Assets/Interface/EmblemeCommande.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CalquesCarteTests.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot891.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot943.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot963.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot963.cs.meta
docs/briefs/963-la-bande-des-modes-en-bas-a-droite-de-la-carte.md

Tout autre chemin est interdit. C'est vrai en particulier pour `LieuxDeCarte.cs`, `FlechesDeCarte.cs` et leurs légendes (sous-lot suivant), `PassageALaCapitaleTests.cs`, `SocleInterface.cs`, `Infobulle.cs`, et les scénarios `Lot549`, `Lot690`, `Lot855`, `Lot944`. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt.

Coordonnées en unités de la toile (1920 × 1080), origine en haut à gauche, comme `SocleInterface.Panneau`.

**`CalquesCarte.cs`**
- `public enum ModeDeCarte { Puissances, Habitants, Flux }`, la propriété `Mode` ; `Habitants => Mode == ModeDeCarte.Habitants` reste. Constantes `BANDE = "Modes de la carte"`, `LEGENDE = "Légende du mode"`, `LIGNES_MAX = 3`, `FLUX` (le texte ci-dessus).
- `Initialiser(carte, Transform toile, monde, selection)` reçoit la toile, plus le guide. Il pose la bande : un `RectTransform` nu, enfant direct de la toile, en (776, 1012), 486 × 44. Ses commandes `Puissances`, `Habitants`, `Flux` (`SocleInterface.Commande`, 156 × 44, x locaux 0, 165, 330 ; libellé de x 36 à 156, à droite de l'icône) ; Puissances et Habitants gardent leur phrase, Flux a « Passe les terres en papier pour lire ce que vos lieux envoient à votre siège, et votre siège à son suzerain. ». Puis la légende : un fond `LEGENDE`, enfant direct de la toile ancré en haut à gauche, x 776, largeur 486, `fond` à 0,72, `raycastTarget` vrai, avec une `Infobulle` ; dedans un `Text` en (8, 4), largeur 470, `Corps`, `papier`, retour à la ligne. Le bas du fond reste à y 1004 (y = 1004 − hauteur, hauteur = `preferredHeight` + 8).
- `public Text Legende` désigne ce `Text`. Un clic pose `Mode` et `changement = true`, rien d'autre.
- `public static Color Teinte(ModeDeCarte mode, bool retenue, Color maison, float position)` : gardée → `alerte` ; Habitants → `Lerp(papier, accent, .65f * position)` ; Flux → `papier` ; Puissances → `Pigment(maison)`. `LateUpdate` l'appelle ; la répartition ne se calcule qu'en Habitants.
- `public static string LegendeDuMode(ModeDeCarte, RepartitionHabitants)` ; `public static string DetailDuMode(ModeDeCarte)`, une phrase par mode qui dit comment lire la couleur et le rouge.
- `public static int Lignes(Text texte, string contenu, float echelle)` : `lineCount` d'un `TextGenerator` peuplé avec `texte.GetGenerationSettings(new Vector2(texte.rectTransform.rect.width, 0))` à `scaleFactor = echelle`.
- `public void Legender(string texte, string detail)` lève `ArgumentException("légende de N lignes : trois au plus")` si `Lignes` dépasse 3 à l'échelle 1 ou 2/3 ; sinon elle écrit le texte, règle le fond, et l'infobulle reçoit `texte + "\n" + detail`.
- Le `catch` appelle `Legender(Indisponible(…), DetailDuMode(Puissances))` ; si ce texte dépasse trois lignes, la légende dit `"Calque indisponible : détail dans l'infobulle."` et le texte entier va à l'infobulle. `LegendeDuCalque`, `Indisponible` et `RepartitionHabitants.Legende` ne changent pas d'un caractère.

**`EmblemeCommande.cs`** : deux motifs neufs, `"foule"` pour `Habitants` (trois têtes sur leurs épaules) et `"fleche"` pour `Flux` (une hampe et sa pointe). Le code reste dans le style de `banniere`.

**`CabinetDeCarte.cs`** : le guide devient `Panneau(toile.transform, "Parcourir le monde", 24, 872, 740, 184)`, et `CalquesCarte.Initialiser` reçoit `toile.transform`. Le `Text` de l'aide garde sa largeur de 1190 (`LesAidesDisentLesNouveauxGestes` la fige). Si SC1 montre que `AIDE` déborde du guide réduit, `AIDE` devient `"Clic : choisir · Glisser : déplacer · Molette : zoomer · Échap : fermer"`.

**`Lot891.cs`** : `Bouton("Parcourir le monde", "Habitants")` devient `Bouton(CalquesCarte.BANDE, "Habitants")`.

**`Lot943.cs`** : `Bouton` cherche dans `CalquesCarte.BANDE`. `Visible` exige entiers le guide et la bande. On adapte le commentaire de tête. Le reste ne change pas.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot963-interface.xml -logFile 3d/unity/Temp/lot963-interface.log`. Elle doit sortir 0, sans échec ni cas ignoré, avec les cas neufs réussis.

**SC1 — La bande, la légende et leur place (`CabinetDeCarteTests.cs`, commande `I`).** Cas `La_bande_des_modes_et_sa_legende_restent_a_leur_place`. `Modes de la carte` porte `Puissances`, `Habitants`, `Flux`, chacun avec sa phrase et un enfant `Repère banniere`, `Repère foule` ou `Repère fleche` ; `Parcourir le monde` mesure 740 × 184 en (24, 872) et ne porte plus ni `Puissances` ni `Habitants`. `Legender` reçoit tour à tour `LegendeDuCalque(null)`, `LegendeDuCalque` d'une répartition de 1 à 275 000 habitants au jour 365 de 1400, et `FLUX` : chaque fois `Lignes` ≤ 3 aux échelles 1 et 2/3, l'infobulle de `LEGENDE` vaut `texte + "\n" + detail`, et, pour 1920 × 1080 puis 1280 × 720 (rectangles multipliés par largeur / 1920), la bande et le fond de légende ne recouvrent aucun enfant direct de la toile, actif ou non, qui porte une `Image` à `raycastTarget` vrai — feuillets, plan du bourg, menu, dossiers, bandeau, guide —, « Fond des dossiers », « Infobulle », la bande et la légende écartés ; ils restent à x ≤ 0,67 × largeur et dans l'écran. Contre-épreuves dans le cas : un guide de 1238 de large recouvre la bande ; l'ancienne légende des lieux (16, 104, 1100 × 160) recouvre un feuillet. Le cas vérifie aussi `AIDE.preferredWidth` ≤ 692 (740 − 2 × 24).

**SC2 — Changer de mode ne relit rien (`CabinetDeCarteTests.cs`, commande `I`).** Cas `Changer_de_mode_ne_touche_ni_l_horloge_ni_les_lectures`. Le cabinet reçoit une `LecturePartie` dont les quatre lecteurs comptent leurs appels, avec un monde posé comme dans `Proposer`. On invoque Flux, Habitants, puis Puissances. Après : zéro appel, `Occupee` faux, `Partie.Monde` est la même référence, l'horloge a `RequeteEnVol` faux et la même `Lue`. Contre-épreuve dans le cas : `_ = partie.Actualiser()` rend `Occupee` vrai.

**SC3 — La couleur suit le mode, trois lignes au plus (`CalquesCarteTests.cs`, commande `I`).** Cas `Chaque_mode_a_sa_couleur_et_sa_legende` : pour une même terre non gardée, `Teinte` rend trois couleurs distinctes dans les trois modes, et `alerte` dans chacun si elle est gardée ; `LegendeDuMode(Flux, null)` vaut exactement `FLUX` ; les trois légendes et les trois `DetailDuMode` passent `TexteDuMonde.Interdit` et `TexteDuMonde.SansUnite` ; `Lignes` d'un texte de quatre lignes sur un `Text` de 470 en `Corps` rend 4, et `Legender` de ce texte lève `ArgumentException` (contre-épreuve des trois lignes). À la main : Flux qui rend `Pigment(maison)` fait rougir le cas, puis on rétablit.

**SC4 — Sur le vrai service, la photo et sa contre-épreuve.** La commande `PHOTO` de la Photo sort 0 avec son image. `RELIRE` sort 1, sans image, et son journal dit `le changement de mode a relancé une lecture`.

**SC5 — Les scénarios qui cherchent leurs boutons dans la bande.** `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 891 -forgeCaptures 3d/unity/Temp/lot963-891 -logFile 3d/unity/Temp/lot963-891.log` et la même commande avec `-forgeLot 943 -forgeCaptures 3d/unity/Temp/lot963-943 -logFile 3d/unity/Temp/lot963-943.log` sortent 0, chacune avec son image. Le codeur les regarde.

**SC6 — Rien ne s'assouplit, rien d'autre ne bouge.** `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot963-pont.xml -logFile 3d/unity/Temp/lot963-pont.log` sort 0, sans échec ni cas ignoré (dont `PassageALaCapitaleTests` : le guide garde son y de 872). `git diff origin/master -- 3d/unity/Assets/Interface/Tests` ne montre que des lignes ajoutées. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Les légendes des lieux (#657) et des flèches (#658), leur place, leur infobulle ; cacher les flèches hors du mode Flux ; Lot657, Lot658, Lot875, Lot944 : le sous-lot suivant de #858.
- La preuve Lot858, troisième sous-lot. La barre du haut et la fin de « Parcourir le monde » (#859). Le socle (#849, #850).
- Tout nombre du monde, toute lecture nouvelle du service.

## Photo
La carte de 1400 en mode Habitants : les terres du clair au foncé. En bas à droite, la bande et ses trois commandes à icône. Juste au-dessus, la légende des habitants, entière, en trois lignes au plus. À gauche, le feuillet « Les autres maisons » est ouvert, au-dessus de « Parcourir le monde » réduit. À droite, les deux dossiers, entiers. La légende ne touche rien.

Le scénario `[ScenarioDeCapture(963, "mode-habitants")]` de `Lot963.cs` suit ces étapes :
1. `Lot549.Ouvrir`. Il prend `CabinetDeCarte`, `CalquesCarte` et `HorlogeDeCarte` sur la carte. Il passe `SurvolDeCarte` et `ParcoursDeCarte` en `automatique`, exige la toile `Cabinet` active, puis attend `Lot690.LecturePrete(cabinet.Partie)` avec `Lot690.Jusqua`.
2. Il invoque `Parcourir le monde/Autres maisons`, puis attend `!cabinet.Partie.Occupee` et `horloge.Lue != null`.
3. Dans une même image, sans `yield`, il note `horloge.Lue` (référence, `Tick`, `JoursParSeconde`), `cabinet.Partie.Monde` et `Occupee`, invoque `Modes de la carte/Flux`, `/Puissances`, puis `/Habitants` — avec `-forge963Relire`, il lance ensuite `_ = cabinet.Partie.Actualiser()` — et lève `le changement de mode a relancé une lecture du monde ou touché l'horloge : <détail>` si une valeur notée a changé.
4. Il attend que `calques.Legende.text` égale `CalquesCarte.LegendeDuMode(Habitants, new RepartitionHabitants(monde lu))`. Ce texte passe `TexteDuMonde.Interdit` et `SansUnite` ; `CalquesCarte.Lignes` ≤ 3 aux échelles 1 et 2/3 ; la cellule non gardée de plus petit identifiant (`Cellules de la carte/Cellule <id>`) a la couleur de `Teinte(Habitants, false, _, repartition.Position(id))` à 0,01 près.
5. Il pose la toile comme `Lot943` (`Lot549.Photographier`, puis `ScreenSpaceCamera`), sans rien cacher, et laisse passer 10 images de pose.
6. Il prend les rectangles d'écran de la légende et de la bande (`GetWorldCorners` puis `camera.WorldToScreenPoint`). Les deux sont dans l'image. Ils ne recouvrent ni « Les autres maisons », ni « Votre maison », ni « Territoire conservé », ni « FORGE · Le cabinet », ni « Parcourir le monde ». En cas d'échec, il lève l'erreur en nommant le panneau.
7. Il écrit la trace `CAPTURE_963 mode Habitants · légende « … » · lignes N · tick T`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 963 -forgeCaptures 3d/unity/Temp/lot963-photo -logFile 3d/unity/Temp/lot963-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 963 -forgeCaptures 3d/unity/Temp/lot963-relire -forge963Relire -logFile 3d/unity/Temp/lot963-relire.log
```

La première (`PHOTO`) sort 0 avec `*--mode-habitants.png` : c'est la photo. La seconde (`RELIRE`) est la contre-épreuve de SC4. Le codeur ouvre l'image lui-même : une légende coupée ou posée sur un panneau, une icône absente ou une carte qui n'est pas en dégradé d'habitants refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les deux commandes, leurs sorties, la trace `CAPTURE_963` et ce que montre l'image.
