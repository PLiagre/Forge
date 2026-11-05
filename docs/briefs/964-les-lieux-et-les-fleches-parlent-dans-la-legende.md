# Lot #964 — Les lieux et les flèches parlent dans la légende de leur mode
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Les deux légendes flottantes de la carte disparaissent : ce que disent les lieux passe dans la légende du mode Puissances, ce que disent les flèches dans celle du mode Flux, et leur texte complet passe dans l'infobulle de cette légende. Les flèches ne se montrent plus qu'en mode Flux.

## Le joueur
Le joueur a pris sa maison. Il regarde sa carte de 1400. Il n'y a plus de cadre gris en haut à gauche, à moitié caché sous le feuillet ouvert, ni de second cadre posé sur « Parcourir le monde ». Il n'y a plus qu'une légende, en bas à droite, au-dessus des trois modes. En Puissances, le mode de l'ouverture, elle dit en trois lignes au plus ce que veulent dire les couleurs des terres et celles des disques de ses lieux : blanc pour les siens, une couleur pour les autres maîtres, rouge quand il part plus de gens qu'il n'en arrive. Au survol, l'infobulle donne le relevé de chaque terre, avec sa date et les lectures manquées. Il clique sur Flux. Les terres passent en papier. Les flèches orange et violettes apparaissent, et la légende dit ce qu'elles portent. Au survol, l'infobulle donne ce que chaque lieu a envoyé à son siège, en tonnes, et le dû envoyé au suzerain. En Puissances et en Habitants, les flèches ne chargent plus la carte. Il lit sa terre sans rien chercher : une seule légende à la fois, toujours à la même place. C'est le deuxième des trois morceaux du geste « Les modes de carte » du jalon 4 (`CAP.md`, lot 20, #858 : « une légende à la fois, à place fixe »). Ce geste sert la décision du jalon : trouver sa capitale, lire ce que sa part fait monter vers son siège, et y descendre sans chercher. La preuve Lot858, troisième morceau, le jugera entier.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, aucune lecture n'est ajoutée. Ni `jeu/sim/`, ni le service, ni `Forge.Pont` ne sont touchés. Les lieux et les flèches lisent le monde comme aujourd'hui, au même rythme, dans tous les modes. Seul l'affichage change. Ce lot suit la réponse A du propriétaire sur #858 : les détails vont dans l'infobulle de la légende ; les flèches ne se montrent qu'en mode Flux ; aucun test des légendes n'est rendu moins exigeant.

## Périmètre
3d/unity/Assets/Interface/LieuxDeCarte.cs
3d/unity/Assets/Interface/FlechesDeCarte.cs
3d/unity/Assets/Interface/CalquesCarte.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot657.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot658.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot875.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot944.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot964.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot964.cs.meta
docs/briefs/964-les-lieux-et-les-fleches-parlent-dans-la-legende.md

Tout autre chemin est interdit. C'est vrai en particulier pour `CalquesCarteTests.cs`, `Infobulle.cs`, `SocleInterface.cs`, `InfobulleDeTerre.cs` et les scénarios `Lot690`, `Lot891`, `Lot943` et `Lot963`. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 9f9a208, où #963 est fusionné (`ModeDeCarte`, `CalquesCarte.BANDE`, `LEGENDE`, `Legender`, `Lignes`, `DetailDuMode`).

Sur ce qu'on lit dans ce lot : « l'infobulle de la légende », c'est `Infobulle.Phrase` du fond `Cabinet/Légende du mode`. On ne lit jamais le feuillet partagé `Cabinet/Infobulle`, que l'infobulle des terres réécrit.

**`LieuxDeCarte.cs`**
- Plus de fond ni de `Text`. `Fond de la légende`, `Légende des lieux`, la propriété `Legende` et `Afficher` disparaissent. `Installer()` ne prend plus la toile.
- `TexteLegende` devient `{ get; private set; }`. Il vaut `ENTETE` à l'installation et à chaque changement de maison. `Appliquer` lui donne la chaîne qu'il écrit aujourd'hui, au caractère près. `ENTETE`, `Bourg`, `Tenue` et toutes les lignes ne changent pas.
- `public bool Peint => peinte != null;` : une maison du joueur est lue, et ses lieux se peignent.

**`FlechesDeCarte.cs`**
- Plus de fond ni de `Text`. `Fond des flèches`, `Légende des flèches`, la propriété `Legende`, `Afficher` et le recalage dans `Update` disparaissent. `Installer(LieuxDeCarte vue)` ne prend plus la toile.
- `TexteLegende => ENTETE + lignesLieux + ligneDu` : c'est exactement le texte qu'`Afficher` écrit aujourd'hui. `ENTETE` et les lignes ne changent pas.
- `Visibles => calques != null && calques.Mode == ModeDeCarte.Flux`, avec `calques = GetComponent<CalquesCarte>()` pris à `Installer`. `Pas` commence par `racine.gameObject.SetActive(Visibles)` quand la racine existe. `Fleche` crée la racine déjà réglée sur `Visibles`. Les flèches restent calculées et nommées hors du mode Flux : seule la racine `Flèches de la carte` est inactive.

**`CalquesCarte.cs`**
- `public const string PUISSANCES = "Puissances de la carte · Rouge : territoire conservé"`.
- `FLUX` vaut désormais `"Orange : prélevé de chaque lieu vers votre siège · Violet : dû de votre siège à son suzerain · Sur trente jours · Rouge : territoire conservé"`. C'est la forme courte de `FlechesDeCarte.ENTETE`. Cet en-tête entier fait quatre lignes à 470 px, donc il va dans l'infobulle.
- `public static string LegendeDuMode(ModeDeCarte mode, RepartitionHabitants repartition, bool lieuxPeints)` : en Puissances avec `lieuxPeints`, elle rend `PUISSANCES + "\n" + LieuxDeCarte.ENTETE`. Sinon, elle rend `LegendeDuMode(mode, repartition)`, qui ne change pas. Sans maison, la légende des Puissances reste donc `LegendeDuCalque(null)` : `Lot943` la lit telle quelle.
- `public static string DetailDuMode(ModeDeCarte mode, LieuxDeCarte lieux, FlechesDeCarte fleches)`. En Puissances avec `lieux?.Peint` : `DetailDuMode(Puissances) + " Relief non transmis." + lieux.TexteLegende.Substring(LieuxDeCarte.ENTETE.Length)`. Ce sont les lignes du relevé ; l'en-tête est déjà dans la légende, il ne s'écrit pas deux fois. En Flux avec `fleches` non nul : `DetailDuMode(Flux) + "\n" + fleches.TexteLegende`. Sinon : `DetailDuMode(mode)`. `DetailDuMode(mode)` ne change pas.
- `public void Brancher(LieuxDeCarte lieux, FlechesDeCarte fleches)` garde les deux vues. `LateUpdate` appelle `Legender(LegendeDuMode(mode, repartition, lieux != null && lieux.Peint), DetailDuMode(mode, lieux, fleches))`. Il récrit aussi la légende quand ce texte ou ce détail changent, même si le monde, la terre gardée et le mode n'ont pas bougé. Dans ce cas, il ne recolore aucune terre. `Legender`, `Ecrire`, la place et le `catch` ne changent pas.

**`CabinetDeCarte.cs`** : `lieux.Installer()`, `fleches.Installer(lieux)`, puis `GetComponent<CalquesCarte>().Brancher(lieux, fleches)`. Rien d'autre.

**`Lot657.cs`** : avant d'attendre `Pret`, il clique sur `Modes de la carte/Puissances` (`toile.Find(CalquesCarte.BANDE)`). `Pret` lit l'infobulle de la légende à la place de `vue.TexteLegende`. `Controler` juge la légende `calques.Legende`. Son texte doit égaler `LegendeDuMode(Puissances, null, true)`, le texte doit tenir dans le cadre, et le cadre doit être `DansLeChamp`. Puis `Controler` juge l'infobulle. Elle doit contenir `LieuxDeCarte.ENTETE` et chaque ligne de terre. Elle ne doit pas contenir « même instant ». Elle passe les deux juges, avec la maison. Le contrôle des disques ne change pas.

**`Lot658.cs`** : une fois le feuillet ouvert, il clique sur `Modes de la carte/Flux`. L'attente exige les `lignes` dans l'infobulle de la légende, et non plus dans `vue.TexteLegende`. Les terres dans `disques.TexteLegende` et le feuillet restent exigés comme avant. Au contrôle, la légende doit valoir `FLUX`, être active, tenir dans son cadre et être `DansLeChamp`. Dans `Caches`, on retire les deux noms des fonds disparus : le fond de la légende du mode prend les clics, il y est déjà. `FlechesDuSiege`, `carte` et `toile` restent `internal`.

**`Lot875.cs`** : après `Lot658.FlechesDuSiege`, la carte est en mode Flux. Le scénario exige que la légende égale `FLUX`, et la légende des flèches est l'infobulle de la légende. Puis il clique sur Puissances. Il attend que la légende égale `LegendeDuMode(Puissances, null, true)` et que l'infobulle contienne « · relevé au jour » : cette infobulle est la légende des lieux. Le contrôle « cachée sous » porte sur `calques.Legende`. Il écarte son propre fond, `CalquesCarte.LEGENDE`. `-forge875Identifiant` ajoute toujours son couple au texte des flèches, et `Exiger` ne change pas.

**`Lot944.cs`** : quand les références sont lues, et avant l'étape 6, le scénario clique sur Flux. Il attend que l'infobulle de la légende contienne chaque ligne de flèche attendue. Il note cette infobulle. Puis il clique sur Puissances. Il attend que l'infobulle contienne, pour chaque terre tenue, `Tenue(cellule, 0) + " · relevé au " + date`, et il la note aussi. `Tenue` et les lignes attendues sortent de `Juger` dans des fonctions statiques communes. `Juger` prend ces deux textes notés pour `LIEUX` et `FLECHES`, et non plus deux `Text` de la toile. Les deux juges, les `Lire`, `TEXTES_MIN` et les deux drapeaux ne changent pas. La photo se prend en Puissances, comme avant.

## Conditions de succès
On lance tout sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot964-interface.xml -logFile 3d/unity/Temp/lot964-interface.log`. `I` doit sortir 0, sans échec ni cas ignoré, et les cas neufs doivent réussir. `C(n, dossier, drapeaux)` = `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot n -forgeCaptures 3d/unity/Temp/dossier -logFile 3d/unity/Temp/dossier.log drapeaux`. Les commandes entières suivent.

**SC1 — Les lieux parlent dans la légende des Puissances (`CabinetDeCarteTests.cs`, commande `I`).** Le cas neuf est `Les_lieux_parlent_dans_la_legende_des_Puissances`. Il appelle `Preparer()`, puis `Publier(JOUEUR, new LieuTenu(10, 0), new LieuTenu(10, 1), new LieuTenu(20, 0))`, puis `Servir(cell => Reponse(cell, 4, false))`. Sous `Cabinet`, aucun objet ne s'appelle `Légende des lieux` ni `Fond de la légende`, actif ou non. `lieux.Peint` est vrai. `LegendeDuMode(Puissances, null, true)` vaut `PUISSANCES + "\n" + LieuxDeCarte.ENTETE`. Le détail `DetailDuMode(Puissances, lieux, fleches)` vaut la formule du Périmètre, et il contient `"\nAlba · relevé au jour 5 de 1400"` et `"\nDara · relevé au jour 5 de 1400"`. `calques.Legender(légende, détail)` ne lève rien. `Lignes` reste entre 1 et 3 aux échelles 1 et 2/3. L'infobulle vaut `légende + "\n" + détail`, contient `ENTETE` une seule fois, et passe `TexteDuMonde.Interdit(…, JOUEUR, B, C)` et `SansUnite`. Contre-épreuves dans le cas : `LegendeDuMode(Puissances, null, false)` vaut `LegendeDuCalque(null)` ; `DetailDuMode(Puissances, null, null)` vaut `DetailDuMode(Puissances)` ; `Legender(PUISSANCES + "\n" + FlechesDeCarte.ENTETE, …)` lève `ArgumentException`.

**SC2 — Les flèches ne se montrent qu'en mode Flux (`CabinetDeCarteTests.cs`, commande `I`).** Le cas neuf est `Les_fleches_ne_se_montrent_qu_en_mode_Flux`. Il pose les trois lieux tenus et le service du cas `UneFlecheParLieuTenuVersLeSiege`, avec `a` = 100 000 kg et `b` = 218 086 kg, recopiés dans le cas neuf. Alors `Fleches()` vaut `Flèche 10-1` et `Flèche 20-0`, et la racine `Flèches de la carte` a `activeSelf` faux, puisque le cabinet s'ouvre en Puissances. Le cas invoque ensuite `Cabinet/Modes de la carte/` Flux, Habitants, Puissances, puis Flux, et appelle `fleches.Pas(horloge)` après chaque clic. La racine est active seulement après les deux Flux, et `Fleches()` garde ses deux noms tout du long. Sous `Cabinet`, aucun objet ne s'appelle `Légende des flèches` ni `Fond des flèches`. `DetailDuMode(Flux, lieux, fleches)` vaut `DetailDuMode(Flux) + "\n" + fleches.TexteLegende`, et il contient `FlechesDeCarte.ENTETE` et `"\nAlba · Brivas → Siège : " + TexteDuMonde.Masse(100000)`. `Legender(FLUX, détail)` tient en trois lignes au plus aux deux échelles, et l'infobulle passe les deux juges. Contre-épreuve dans le cas : `Legender(FlechesDeCarte.ENTETE + " · Rouge : territoire conservé", …)` lève `ArgumentException`. À la main : si `Visibles` rend toujours vrai, le cas rougit ; puis on rétablit.

**SC3 — Les scénarios cliquent le mode et lisent l'infobulle.** Chacune de ces commandes sort 0 avec son image, et le codeur regarde les images :
- `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 657 -forgeCaptures 3d/unity/Temp/lot964-657 -logFile 3d/unity/Temp/lot964-657.log`
- la même commande avec `-forgeLot 658 -forgeCaptures 3d/unity/Temp/lot964-658 -logFile 3d/unity/Temp/lot964-658.log`
- avec `-forgeLot 875 -forgeCaptures 3d/unity/Temp/lot964-875 -logFile 3d/unity/Temp/lot964-875.log`
- avec `-forgeLot 944 -forgeCaptures 3d/unity/Temp/lot964-944 -logFile 3d/unity/Temp/lot964-944.log`
- avec `-forgeLot 943 -forgeCaptures 3d/unity/Temp/lot964-943 -logFile 3d/unity/Temp/lot964-943.log` : sans maison, la légende des Puissances n'a pas changé.

Les contre-épreuves sortent 1. La première est `-forgeLot 658 -forgeCaptures 3d/unity/Temp/lot964-658-du -forge658RetirerDu -logFile 3d/unity/Temp/lot964-658-du.log`, avec « flèche manquante ». La seconde est `-forgeLot 875 -forgeCaptures 3d/unity/Temp/lot964-875-id -forge875Identifiant -logFile 3d/unity/Temp/lot964-875-id.log`, avec « mot interdit ».

**SC4 — Sur le vrai service, la photo et sa contre-épreuve.** La commande `PHOTO` de la Photo sort 0 avec son image. `FLECHES` sort 1, sans image, et son journal dit `flèche visible hors du mode Flux`.

**SC5 — Rien ne s'assouplit, rien d'autre ne bouge.** `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot964-pont.xml -logFile 3d/unity/Temp/lot964-pont.log` sort 0, sans échec ni cas ignoré. `git diff origin/master -- 3d/unity/Assets/Interface/Tests` ne montre que des lignes ajoutées. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- La preuve Lot858, troisième sous-lot de #858. La barre du haut et la fin de « Parcourir le monde » (#859).
- La légende des Habitants, les disques des lieux (visibles dans tous les modes, comme aujourd'hui), les couleurs, le sens des deux rouges et le texte de `ENTETE`.
- Une infobulle plus haute que l'écran pour une très grande maison : `Infobulle.Placer` la refuse déjà. Ce lot ne la découpe pas ; Mistra tient.
- `Lot891`, `Lot943`, `Lot963` et `CalquesCarteTests` ne changent pas. Tout nombre du monde, toute lecture nouvelle.

## Photo
La carte autour de Mistra, en mode Flux, après trente jours à 60 % de part. Les terres sont en papier. Les flèches orange vont des lieux au siège, la violette va du siège vers celui du suzerain. À gauche, le feuillet « Terres et comptes » est ouvert. En bas à droite, la bande des modes, et la légende courte du Flux juste au-dessus. Au-dessus de la légende, son infobulle est ouverte : l'en-tête entier des flèches, puis ce que chaque lieu a envoyé, en tonnes, et le dû. On ne voit aucune légende flottante.

Le scénario `[ScenarioDeCapture(964, "flux-et-infobulle")]` de `Lot964.cs` suit ces étapes :
1. Il joue `Lot658.FlechesDuSiege(camera)` en entier : Mistra, la part, trente ticks, le feuillet, Flux, les flèches et l'infobulle contrôlées, la toile posée. Puis il prend `Lot658.carte`, `Lot658.toile`, `CalquesCarte`, `LieuxDeCarte` et `FlechesDeCarte`, et il passe `SurvolDeCarte`, `ParcoursDeCarte` et `InfobulleDeTerre` en `automatique`.
2. Sous la toile, actifs ou non, il ne doit rester aucun `Légende des lieux`, `Légende des flèches`, `Fond de la légende` ou `Fond des flèches`. Sinon il lève `légende flottante encore là : <nom>`.
3. Il clique sur `Modes de la carte/Puissances`. Il attend, avec `Lot690.Jusqua`, que la légende égale `LegendeDuMode(Puissances, null, true)` et que l'infobulle égale `légende + "\n" + DetailDuMode(Puissances, lieux, fleches)`. Avec `-forge964Fleches`, il réactive ensuite la racine `Flèches de la carte`, dans la même image que le contrôle, sans `yield`. Puis chaque enfant de `Flèches de la carte` doit être inactif dans la hiérarchie, sinon il lève `flèche visible hors du mode Flux : <nom>`. Au moins un disque de lieu doit rester actif.
4. Il clique sur Flux. Il attend que la légende égale `FLUX`, que l'infobulle égale `FLUX + "\n" + DetailDuMode(Flux, lieux, fleches)`, et qu'au moins une flèche soit active.
5. Il appelle `Infobulle.Montrer(canvas de la toile, infobulle, centre de la légende en pixels d'écran)`. Il laisse passer 10 images. Le feuillet `Infobulle` doit être actif, montrer le même texte, et être entier dans l'image. La légende et la bande doivent être dans l'image, et ne recouvrir ni « Terres et comptes », ni « Votre maison », ni « Territoire conservé », ni « FORGE · Le cabinet », ni « Parcourir le monde » : les rectangles se prennent comme dans `Lot963`.
6. Il écrit la trace `CAPTURE_964 mode Flux · légende « … » · infobulle N lignes · flèches K visibles · tick T`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 964 -forgeCaptures 3d/unity/Temp/lot964-photo -logFile 3d/unity/Temp/lot964-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 964 -forgeCaptures 3d/unity/Temp/lot964-fleches -forge964Fleches -logFile 3d/unity/Temp/lot964-fleches.log
```

La première commande (`PHOTO`) sort 0 avec `*--flux-et-infobulle.png` : c'est la photo. La seconde (`FLECHES`) est la contre-épreuve de SC4. Le codeur ouvre l'image lui-même. La livraison est refusée, même avec une sortie 0, si l'image montre une légende flottante, une infobulle coupée, des flèches absentes ou des terres en pigment de maison. Les PNG restent hors du dépôt. Le compte rendu donne les deux commandes, leurs sorties, la trace `CAPTURE_964` et ce que montre l'image.
