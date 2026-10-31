# Lot #944 — L'épreuve, aucun identifiant à l'écran, et la photo
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Sur le vrai service, une épreuve qui peut échouer garantit qu'avec la Morée gardée, aucun texte affiché par le cabinet ou par la fiche ne montre un identifiant ou un nombre sans unité, et qu'aucune valeur servie n'a disparu des dossiers.

## Le joueur
Le joueur choisit la Morée et la garde d'un clic. Il lit son dossier, « Terres et comptes », l'infobulle de survol et les légendes en noms, en dates et en unités : « Mistra · Maison : Paléologue », « jour 32 de 1400 », « Prélevé : 43,7 t ». Il n'y lit jamais « Cellule 10340 », « rang 1 », « 10340-1 », « seigneurie-3 », « tick 31 » ni un « 1400 » seul. Chaque chiffre que ces dossiers montraient avant la réécriture y est encore : il compare son grenier, sa part et ses lieux avant de descendre dans sa capitale. Le joueur a la preuve qu'aucun identifiant ni nombre nu ne reste à l'écran. C'est la preuve du geste « La fiche parle en noms, pas en identifiants » du jalon 4 (`CAP.md`, lot 18, #856), son sous-lot 8. Il ne change rien à l'écran : il le prouve.

Ce lot reprend #877, découpé par le dépanneur. Le scénario de #877 (`Lot877.cs` à la révision `437da99`, branche `lot/877-l-epreuve-aucun-identifiant-a-l-ecran-et-la-phot`) a été jugé conforme par deux relectures. Il tombait sur la légende des calques, « Puissances de la carte de 1400 » : un nombre seul, que #943 (fusionné, `c1917f99`) a retiré. Les exigences de #877 ne changent pas ici.

## Règle du monde
Sans objet : c'est un lot d'épreuve. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni le service, ni une vue ne sont touchés.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot944.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot944.cs.meta
docs/briefs/944-l-epreuve-aucun-identifiant-a-l-ecran-et-la-phot.md

Tout autre chemin est interdit, `Lot877.cs` compris : il n'entre pas dans `master`. C'est vrai aussi pour `TexteDuMonde.cs`, `CalquesCarte.cs`, `FicheDeCellule.cs`, les dossiers d'`Assets/Interface/` et les autres scénarios (`Lot526`, `Lot549`, `Lot655`, `Lot690`, `Lot855`, `Lot873`, `Lot943`…). Le scénario appelle leurs membres `internal` sans les modifier.

**Le point de départ.** Le codeur part de `git show 437da99:3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot877.cs` et l'écrit en `Lot944.cs`. Il renumérote, et rien d'autre au départ : la classe `Lot944`, `[ScenarioDeCapture(944, "moree-et-ses-comptes")]`, les drapeaux `-forge944Identifiant` et `-forge944SansValeur`, la trace `CAPTURE_944`, les deux commentaires d'en-tête. Le fichier ne garde aucun « 877 ». Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt et différent de `25b0f08b44014688801e79bad3910746` (celui de #877). Ensuite il rejoue les trois commandes de la Photo. Il ne corrige le scénario que si une commande échoue par la faute du scénario, jamais en retirant un texte des juges ou une valeur des références.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Les trois commandes de la Photo s'appellent `PHOTO`, `IDENTIFIANT` et `SANS_VALEUR`.

Repères mesurés au service, graine 0, après le choix au tick 30 et un jour poussé, au tick 31 (« jour 32 de 1400 »). Le scénario lit tout au service et n'écrit aucun de ces nombres en dur.
- La Morée est la terre 10340, son bourg « Mistra ». Elle a 15 lieux, de « Mistra » (rang 0) à « Nea Rachi » (rang 14), et 81 514 habitants.
- Maîtres de ses lieux : `seigneurie-3` (rangs 0 à 3), puis `plausible-10340-4`, `-7`, `-10` et `-13`. La maison du joueur est `seigneurie-3`, « Paléologue », 4 lieux tenus. Son suzerain est `grande-15`, « Paléologue », siège à Constantinople (terre 10374).
- Comptes : part 3 %, grenier « nourriture : 35,8 t ». Prélevé 43,7 t, reçu 36,1 t, dû envoyé 4,01 t, consommé en route 1,25 t, rendu 0 kg. Départs « 0 personne », arrivées « 145 personnes ». Salaires non servis.

**SC1 — Au même tick, tout texte affiché parle en noms et dit chaque valeur servie.** `PHOTO` sort 0 avec son image. Le jugement `Juger(bool drapeaux)` de `Lot944` ne fait aucun `yield` et lève une `InvalidOperationException` à la première faute. Il garde celui de `437da99` :
1. **Références**, lues à part après le dernier jour poussé : `/lieu?cell=<Morée>` par une `LectureDossier.Locale(port)` neuve et par `ClientLieu` ; les comptes du joueur puis du suzerain par `ClientMaison.LireComptes` ; `/lieu` de chaque terre tenue ; le monde par `Lot690.LireMonde`. Le tick du document, celui du monde, `horloge.Lue.Tick` et `fiche.MondeLu.Tick` valent tous `fin`, sinon l'échec cite les ticks.
2. **Identifiants**, en culture invariante : la Morée, chaque `cell_id` tenu, les sièges du joueur et du suzerain ; `<cell>-<rang>` pour chaque lieu de la Morée ; l'id du joueur, celui du suzerain et chaque `maitre` non nul.
3. **Textes nommés**, dans cet ordre : « Territoire conservé », « Terres et comptes », « Votre maison », « Commandes de maison », « Légende des lieux », « Légende des flèches », « Infobulle » (égal à `InfobulleDeTerre.TexteAffiche`), « Fiche de survol » (la chaîne `fiche.TexteAffiche`, car le cabinet éteint la toile de la fiche). Puis **tous** les autres `Text` actifs de `Cabinet` (`GetComponentsInChildren<Text>(false)`), nommés par leur chemin : la légende des calques en fait partie. Un texte nommé absent ou inactif échoue, moins de 8 `Text` actifs aussi.
4. **Les deux juges sur chaque texte, sans exemption.** `TexteDuMonde.Interdit(texte, ids)` nul, sinon `mot interdit « <mot> » dans « <nom> » : « <première ligne> »`. Puis `TexteDuMonde.SansUnite(texte)` nul, sinon `nombre sans unité « <nombre> » dans « <nom> » : « <première ligne> »`.
5. **Les valeurs**, chacune en tête d'une ligne, sinon `valeur absente « <valeur> » dans « <nom> »`. Masses par `TexteDuMonde.Masse`, nombres par `Nombre`, jours par `Jours`, dates par `Date` ; surface et part en `0.##` `fr-FR`.
   - Territoire conservé, coupé aux lignes vides : l'en-tête `<bourg> · Maison : <maître du rang 0>`, la date, `<habitants> habitants dans le territoire` ; une part par lieu servi (sinon `lieu absent « <nom> » dans « Territoire conservé »`), avec habitants et surface, `Maison : <nom>` ou `Sans maître`, chaque stock, `Sur 30 jours : <Masse> prélevés`, départs et arrivées en personnes.
   - Terres et comptes : `<nom> · … · <date>`, `Siège :`, `Suzerain :`, `Prélèvement : <part> %`, `Grenier : …`, une ligne par tenue (`<bourg>` au rang 0, `<bourg> · <lieu>` sinon), `Prélevé :`, `Reçu :`, `Dû envoyé :`, `Consommé en route :`, `Rendu :`, `Départs :`, `Arrivées :`, et `Salaires :` seulement si le service les sert.
   - Votre maison : nom, `Siège : <siège>`, `<n> lieux tenus · relevé au <date>`. Commandes de maison : `Prélèvement : <part> % · relevé au <date>`, puis `Grenier : …`.
   - Légende des lieux : `<bourg> · relevé au <date>` par terre tenue. Légende des flèches : `<siège> : <Masse> prélevés sur place`, chaque autre lieu tenu `<bourg> · <lieu> → <siège> : <Masse>`, puis `<siège> → <siège du suzerain> : <Masse> de dû`.
   - Infobulle : les trois lignes d'en-tête du territoire. Fiche de survol : `Lot526.Juger(fiche, <bourg>)`.

La trace `CAPTURE_944` donne le nombre de textes jugés, de valeurs lues, et la première ligne de chaque texte nommé. Si un texte hors du Périmètre échoue encore, le codeur cite la faute au compte rendu et le lot reste bloqué : on ne corrige pas un écran ici.

**SC2 — Contre-épreuve : un identifiant dans le dossier.** Avec `-forge944Identifiant`, `Juger(true)` ajoute « \n<Morée>-1 » au texte affiché de « Territoire conservé », dans la même image, juste avant de juger. `IDENTIFIANT` sort 1, sans image, et son journal dit `mot interdit « 10340-1 » dans « Territoire conservé »`.

**SC3 — Contre-épreuve : une valeur retirée.** Avec `-forge944SansValeur`, `Juger(true)` retire du texte affiché de « Terres et comptes » sa ligne qui commence par « Prélevé : ». Les juges passent, les valeurs échouent : `SANS_VALEUR` sort 1, sans image, et son journal dit `valeur absente « Prélevé : 43,7 t » dans « Terres et comptes »` (le nombre est celui que sert `/maison`).

**SC4 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot944-interface.xml -logFile 3d/unity/Temp/lot944-interface.log` sort 0. Pareil avec `Forge.Pont.Tests` (`lot944-pont`). Chaque XML a au moins un cas, ni échec ni cas ignoré.
- Le scénario appelle `TexteDuMonde.Interdit`, `TexteDuMonde.SansUnite` et `Lot526.Juger` sans en recopier aucun. `git diff --no-index` entre le `Lot877.cs` de `437da99` et `Lot944.cs` ne montre que le renumérotage, plus chaque correction que le compte rendu justifie par une sortie de commande.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Corriger un écran qui échoue, changer `TexteDuMonde`, ses juges, `CalquesCarte` ou un dossier.
- Les modes de carte et leur légende (#858), la barre du haut (#859).
- La ville, `PanneauLieu`, les outils de la capitale ; `pc/epreuve_carte.py` (#928, #929).
- Fusionner ou supprimer la branche de #877.

## Photo
La carte de 1400 sur la Morée. À droite, le dossier « Territoire conservé » commence par « Mistra · Maison : Paléologue », puis « jour 32 de 1400 ». À gauche, le feuillet « Terres et comptes » est ouvert en entier : « Paléologue · seigneurie · jour 32 de 1400 », « Prélèvement : 3 % », « Grenier : nourriture : 35,8 t », les quatre tenues en noms, la circulation en tonnes. Sous « Parcourir le monde », la légende dit « Puissances de la carte · Relief non transmis · Rouge : territoire conservé ». Nulle part un identifiant, un tick ou un nombre seul.

Le scénario `[ScenarioDeCapture(944, "moree-et-ses-comptes")]` de `Lot944.cs` garde les étapes de `437da99` :
1. `Lot549.Ouvrir` ; `SurvolDeCarte`, `ParcoursDeCarte` et `InfobulleDeTerre` en `automatique` ; il attend `Lot690.LecturePrete` puis `horloge.Lue`, et exige `JoursParSeconde == 0`.
2. Il prend la fiche de départ au siège « Mistra » (« Despotat de Morée », une seule), lit `/lieu` de la Morée (bourg, point P), zoome de 12 crans et centre comme `Lot855`. `HorsCarte(P)` est faux.
3. Il garde la Morée d'un clic : `Noter` à l'appui, au déplacement et au relâché en P, sans image entre les trois. `Retenue.CellId` = la Morée.
4. Sous `Votre maison/Maisons proposées`, il invoque la maison de la fiche puis « Choisir cette maison », attend un reçu accepté, `Lot690.PousserTick`, et attend que le cabinet lise la maison du joueur au tick suivant, au siège « Mistra ».
5. Il invoque « Terres et comptes », puis `fiche.Survoler(P)` et `InfobulleDeTerre.Pas(P, fiche.Survolee, t)` à chaque image.
6. Il attend au plus 30 s que `Juger(false)` passe, sinon il échoue avec la dernière cause. Puis `Juger(true)`, qui joue les drapeaux : les contre-épreuves échouent ici.
7. Il cache l'infobulle (`Pas(P, null, t)`), pose la toile comme `Lot873` (`Lot549.Photographier`, puis `ScreenSpaceCamera`). Les deux panneaux sont entiers, le feuillet tient dans sa fenêtre (`Lot655.Lisible`), le dossier n'a pas défilé.
8. Après 10 images de pose, `Juger(false)` à nouveau, puis la trace `CAPTURE_944`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot944-photo -logFile 3d/unity/Temp/lot944-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot944-identifiant -forge944Identifiant -logFile 3d/unity/Temp/lot944-identifiant.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot944-sans-valeur -forge944SansValeur -logFile 3d/unity/Temp/lot944-sans-valeur.log
```

La première (`PHOTO`) sort 0 avec `*--moree-et-ses-comptes.png` : c'est la photo. Les deux autres sont les contre-épreuves de SC2 et SC3, chacune dans son dossier neuf. Le codeur rejoue les trois jusqu'à ce résultat et ouvre l'image lui-même. Un panneau coupé, un feuillet tronqué, un « Cellule », un « tick », un identifiant ou un nombre seul visible refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les trois commandes, leurs sorties, la trace `CAPTURE_944` et ce que montre l'image.
