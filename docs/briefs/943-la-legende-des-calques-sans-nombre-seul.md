# Lot #943 — La légende des calques sans nombre seul
Jalon : J4 · Machine : pc · Taille prévue : 170 lignes

## But
Sous « Parcourir le monde », la légende du calque des puissances ne montre plus d'année isolée : sous ses deux formes, puissances et habitants, elle passe les juges `TexteDuMonde.Interdit` et `TexteDuMonde.SansUnite`, et un test EditMode le garde.

## Le joueur
Le joueur garde la Morée et regarde la carte des puissances. Sous « Parcourir le monde », il lit « Puissances de la carte · Relief non transmis · Rouge : territoire conservé ». Il n'y lit plus le « 1400 » seul, qui ressemblait à un compte sans unité. Quand il passe aux habitants, il lit toujours « Habitants : … habitants (foncé) · échelle logarithmique · jour 32 de 1400 · Rouge : territoire conservé ». Partout sur la carte, un nombre est une date, une masse, des habitants ou des jours, jamais un chiffre nu. C'est un morceau du geste « La fiche parle en noms » du jalon 4 (`CAP.md`, lot 18, #856). Le lot #877, l'épreuve « aucun identifiant à l'écran », juge chaque `Text` actif du cabinet sans exemption : il tombait sur cette légende. #943 la corrige pour que #877 passe.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni le service, ni `TexteDuMonde` ne sont touchés.

La forme est tranchée ici : **on retire l'année**, on ne date pas. Les couleurs des puissances sont relevées une seule fois, au dessin de la carte (`CalquesCarte.cs:44`, « jamais relue »). Elles ne suivent pas la date servie. Écrire « jour 32 de 1400 » sous ces couleurs dirait au joueur qu'elles sont celles du jour, ce qui serait faux. La légende des habitants, elle, garde sa date : ses couleurs viennent du monde lu à cette date.

## Périmètre
3d/unity/Assets/Interface/CalquesCarte.cs
3d/unity/Assets/Interface/Tests/CalquesCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot943.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot943.cs.meta
docs/briefs/943-la-legende-des-calques-sans-nombre-seul.md

Tout autre chemin est interdit. C'est vrai en particulier pour `TexteDuMonde.cs`, `TexteDuMondeTests.cs`, `CabinetDeCarte.cs` et les autres scénarios (`Lot549`, `Lot690`, `Lot891`…). Le scénario appelle leurs membres `internal` sans les modifier. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt.

**Ce que le codeur change dans `CalquesCarte.cs`.**
- Il ajoute `public static string LegendeDuCalque(RepartitionHabitants repartition)`. Avec `null`, elle rend `"Puissances de la carte · Relief non transmis · Rouge : territoire conservé"`. Sinon, elle rend `repartition.Legende + " · Rouge : territoire conservé"`.
- La ligne 103-104 devient `legende.text = LegendeDuCalque(repartition);` (`repartition` vaut déjà `null` en mode puissances).
- `RepartitionHabitants.Legende` ne change pas d'un caractère. `Lot891` compose encore `Legende + " · Rouge : territoire conservé"` : il doit rester juste sans être touché.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`.

**SC1 — Les deux formes de la légende passent les deux juges (EditMode).** Le codeur ajoute à `CalquesCarteTests.cs` le cas `La_legende_des_deux_calques_passe_les_juges_du_clerc`. Il reprend le `Monde(...)` du fichier : date « jour 9 de 1400 », deux cellules de 1 et 5 631 habitants.
- `CalquesCarte.LegendeDuCalque(null)` vaut exactement `"Puissances de la carte · Relief non transmis · Rouge : territoire conservé"`.
- Avec cette répartition, elle vaut exactement `"Habitants : 1 habitant (clair) → 5\u00A0631 habitants (foncé) · échelle logarithmique · jour 9 de 1400 · Rouge : territoire conservé"`.
- Pour chacune : `TexteDuMonde.Interdit(legende)` est nul, et `TexteDuMonde.SansUnite(legende)` est nul. Le message d'échec cite la légende.
- Contre-épreuve dans le même cas : l'ancienne légende `"Puissances de la carte de 1400 · Relief non transmis · Rouge : territoire conservé"` donne `SansUnite` = `"1400"`. Le juge n'est donc pas assoupli : c'est le texte qui a changé.

Commande : `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot943-interface.xml -logFile 3d/unity/Temp/lot943-interface.log`. Elle sort 0. Le XML contient le nouveau cas, réussi, et aucun échec ni cas ignoré. Contre-épreuve à la main : remettre le texte de la ligne 103 d'avant fait rougir le nouveau cas sur `SansUnite` (« 1400 »), puis on rétablit.

**SC2 — Sur le vrai service, la légende affichée passe les juges sous ses deux formes.** La commande `PHOTO` de la Photo sort 0 avec son image. Le scénario `Lot943` juge le texte réellement affiché par `calques.Legende` :
- en mode Habitants, il doit être égal à `CalquesCarte.LegendeDuCalque(new RepartitionHabitants(<monde lu par le cabinet>))` ;
- en mode Puissances, à `CalquesCarte.LegendeDuCalque(null)`.
Chaque fois, `TexteDuMonde.Interdit(texte, <id de la Morée>)` puis `TexteDuMonde.SansUnite(texte)` doivent être nuls. Sinon le scénario lève `mot interdit « <mot> » dans la légende : « <texte> »` ou `nombre sans unité « <nombre> » dans la légende : « <texte> »`. La trace `CAPTURE_943` donne les deux légendes lues.

**SC3 — Contre-épreuve : l'ancienne légende.** Avec `-forge943Annee`, le scénario remplace, juste avant le dernier jugement et dans la même image, le texte jugé par l'ancienne légende `"Puissances de la carte de 1400 · Relief non transmis · Rouge : territoire conservé"`. `ANNEE` sort 1, sans image. Son journal dit `nombre sans unité « 1400 » dans la légende`.

**SC4 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot943-pont.xml -logFile 3d/unity/Temp/lot943-pont.log` sort 0. Le XML n'a ni échec ni cas ignoré, et au moins un cas.
- Les cas existants de `CalquesCarteTests.cs` sont gardés tels quels : `git diff origin/master -- 3d/unity/Assets/Interface/Tests/CalquesCarteTests.cs` ne montre que des lignes ajoutées.
- Le scénario et le test appellent `TexteDuMonde.Interdit` et `TexteDuMonde.SansUnite`. Ils n'en recopient aucun.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Changer `TexteDuMonde`, ses juges ou ses tests ; exempter un texte.
- Le texte « Calque indisponible : … » (`CalquesCarte.Indisponible`), les boutons et leurs phrases.
- Relire les couleurs des puissances à chaque jour, transmettre le relief.
- Les modes de carte et la place de la légende (#858), la barre du haut (#859).
- L'épreuve #877 elle-même : elle se rejoue après ce lot, dans son chantier.

## Photo
La carte de 1400 sur la Morée, gardée en rouge, en couleurs des puissances. En bas, le panneau « Parcourir le monde » est entier, avec ses deux boutons « Puissances » et « Habitants ». Sa légende dit « Puissances de la carte · Relief non transmis · Rouge : territoire conservé ». Aucun « 1400 » seul n'y paraît.

Le scénario `[ScenarioDeCapture(943, "legende-des-puissances")]` de `Lot943.cs` suit ces étapes, sur le modèle de `Lot891` :
1. `Lot549.Ouvrir`. Il prend `CabinetDeCarte` et `CalquesCarte` sur la carte, passe `SurvolDeCarte` et `ParcoursDeCarte` en `automatique`, exige la toile `Cabinet` active, puis attend `Lot690.LecturePrete(cabinet.Partie)` avec `Lot690.Jusqua`.
2. Il prend la fiche de départ unique au siège « Mistra ». Il lit le bourg par `ClientLieu`, comme `Lot891.Bourg`. Il zoome et centre la vue pour que le bourg tombe au-dessus du panneau. Il exige que `carte.CelluleSous(point)` soit la Morée, puis `cabinet.Garder(moree)`.
3. Il invoque `Parcourir le monde/Habitants`. Il attend, avec `Lot690.Jusqua`, que `calques.Legende.text` égale `CalquesCarte.LegendeDuCalque(new RepartitionHabitants(cabinet.Partie.Monde.Donnees.Monde))` (monde présent). Il juge ce texte comme en SC2.
4. Il invoque `Parcourir le monde/Puissances`. Il attend que `calques.Legende.text` égale `CalquesCarte.LegendeDuCalque(null)`. Il juge ce texte, en jouant `-forge943Annee` s'il est passé (SC3).
5. Il cache `Fond des dossiers` et `Votre maison`. Il pose la toile comme `Lot891` (`Lot549.Photographier`, puis `ScreenSpaceCamera`). Le panneau « Parcourir le monde » doit être entier dans l'image, et le bourg dans le cadre.
6. Il laisse passer 10 images de pose. Il juge à nouveau la légende des puissances, vérifie le cadre, puis écrit la trace `CAPTURE_943`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 943 -forgeCaptures 3d/unity/Temp/lot943-photo -logFile 3d/unity/Temp/lot943-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 943 -forgeCaptures 3d/unity/Temp/lot943-annee -forge943Annee -logFile 3d/unity/Temp/lot943-annee.log
```

La première (`PHOTO`) sort 0 avec `*--legende-des-puissances.png` : c'est la photo. La seconde (`ANNEE`) est la contre-épreuve de SC3. Le codeur ouvre l'image lui-même. Un panneau coupé, une légende tronquée ou un « 1400 » seul dans la légende refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les deux commandes, leurs sorties, la trace `CAPTURE_943` et ce que montre l'image.
