# Lot #1004 — La preuve de la barre
Jalon : J4 · Machine : pc · Taille prévue : 230 lignes

## But
Un scénario prouve sur le vrai service le geste « Une seule barre en haut ». Une maison en pause y lit dans la barre la date, son grenier et sa part, égaux aux comptes servis au même tick. Chaque commande de l'ancien panneau garde sa place, aucun dossier ne recouvre la barre, et à 1280 × 720 rien n'y est coupé.

## Le joueur
Le joueur a pris Mistra et mis le monde en pause. En haut de l'écran, une seule barre lui dit tout, sans rien ouvrir :
- le jour et « En pause » ;
- le nom de sa maison ;
- « Prélèvement : 60 % » et ce que tient son grenier, les nombres du jour même que le monde vient de servir.

Il ouvre ses comptes, le journal des autres maisons ou le Menu : la barre reste lisible au-dessus. Sur un écran de 1280 × 720, aucun mot n'en est coupé. C'est le quatrième et dernier morceau du geste « Une seule barre en haut » du jalon 4 (`CAP.md`, lot 21, #859 ; preuve : « une barre lue un tick plus tôt échoue »). Ce geste sert la décision du jalon : lire son grenier et sa part d'un coup d'œil avant d'envoyer des bras au chantier, payés au grenier. Les trois premiers morceaux ont été livrés :
- #1001 a mis le grenier et la part dans la barre ;
- #1002 y a mis les dossiers en icônes ;
- #1003 a retiré le panneau « Parcourir le monde ».

Ce lot prouve qu'ensemble ils tiennent. Ensuite, #860 peut ouvrir le jeu en pause sur cette barre.

## Règle du monde
Sans objet : c'est un lot de preuve d'une vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni le service, ni aucun écran ne bougent. Le scénario relit lui-même `GET /maison?id=` (part, grenier, tick) pour juger la barre.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1004.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1004.cs.meta
docs/briefs/1004-la-preuve-de-la-barre.md

Tout autre chemin est interdit. C'est vrai en particulier pour `CabinetDeCarte.cs`, `DossierMaison.cs`, `DossierVoisins.cs`, `EmblemeCommande.cs`, `MenuCabinet.cs`, `HorlogeDeCarte.cs`, `SocleInterface.cs`, tous les tests, `jeu/`, et les scénarios `Lot549`, `Lot658`, `Lot690`, `Lot1001`, `Lot1002`, `Lot1003` : ils sont lus, jamais modifiés. Si le scénario trouve un vrai défaut dans la barre, le lot s'arrête et le compte rendu le nomme : il ne corrige aucun écran. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master b6e15ae6 (#1003 fusionné).

L'issue nomme le scénario `Lot859.cs`. Le pilote du PC ne rejoue que les commandes `-forgeLot 1004` (`atelier/pc.py`) : le scénario s'appelle donc `Lot1004.cs`, `[ScenarioDeCapture(1004, "barre-en-pause")]`. Il juge tout ce que l'issue demande pour #859.

**`Lot1004.cs`** est une `static class Lot1004`, dans le style de `Lot1001` et `Lot1003`, avec quatre drapeaux : `-forge1004Avance`, `-forge1004Perdre`, `-forge1004Recouvrir`, `-forge1004Couper`. Il écrit lui-même ses jugements : il n'appelle ni `CabinetDeCarte.Barre`, ni `DossierMaison`, et ne rend pas `internal` les fonctions privées des autres scénarios. Les rectangles se jugent en coins d'écran, à 0,5 px près, comme `Lot1003.Coins` et `Lot1003.Dans`. Ses étapes suivent ; la première faute lève une `InvalidOperationException` qui la nomme.

1. **Mistra, comme Lot1001.** Il joue `Lot658.FlechesDuSiege(camera)` en entier : Mistra, la part à 60 %, trente ticks, le feuillet « Terres et comptes » ouvert. Il prend `Lot658.carte`, `Lot658.toile`, `CabinetDeCarte` et `HorlogeDeCarte`. Il prend aussi le `Text` `FORGE · Le cabinet/Lecture de la maison…` (la barre) et le `Text` `FORGE · Le cabinet/Lecture de la date…` (la date), tous deux actifs. Sinon : `barre introuvable` ou `date introuvable`.
2. **Chaque commande de l'ancien panneau a sa place, comme Lot1003.** Avec `-forge1004Perdre`, il détruit d'abord (`Object.DestroyImmediate`) le bouton « Autres maisons » de `DOSSIERS`. Puis :
   - aucun `Transform` de la scène, inactifs compris, ne s'appelle « Parcourir le monde ». Sinon : `panneau « Parcourir le monde » encore là : <chemin>` ;
   - « Puissances », « Habitants » et « Flux » sont chacun un seul bouton de la toile, actif, sous `CalquesCarte.BANDE` ;
   - « Terres et comptes » et « Autres maisons » sont chacun un seul bouton, actif, sous `"FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS` ;
   - « Menu » est un seul bouton, actif, enfant direct de la toile, et sa phrase finit par `CabinetDeCarte.AIDE`.

   Un nom absent lève `commande « <nom> » perdue : 0 bouton dans la toile`. Un nom en double, ou hors de sa place, lève une erreur qui nomme l'écart.
3. **Cadrer à 1280 × 720.** `camera.rect` plein, `targetTexture` neuve de 1280 × 720 × 24, `ResetAspect()`. La toile reste en `ScreenSpaceCamera` sur cette caméra, à `nearClipPlane + 0.2`. Puis `yield return null` et `Canvas.ForceUpdateCanvases()`. Avec `-forge1004Couper`, il pose ensuite `sizeDelta` (600, 26) sur la barre.
4. **Aucun dossier ne recouvre la barre, comme Lot1002.**
   - Il ouvre « Les autres maisons » par son icône et le menu par « Menu » (`onClick.Invoke()`), puis `yield return null` et `Canvas.ForceUpdateCanvases()`.
   - Avec `-forge1004Recouvrir`, il remonte lui-même le feuillet « Les autres maisons » à `anchoredPosition` (24, −60).
   - Les trois panneaux « Terres et comptes », « Les autres maisons » et « Menu du cabinet » sont actifs. Sinon : `« <panneau> » fermé`.
   - Chaque panneau du socle actif (un enfant direct de la toile qui porte un enfant « Filet », hors le bandeau) ne chevauche pas le cadre du bandeau, réduit de 0,5 px. Sinon : `« <panneau> » recouvre la barre : <rect> sur <rect>`.
   - Il referme ensuite « Les autres maisons » et le menu par les mêmes boutons, puis rejuge : les deux sont inactifs, « Terres et comptes » reste actif, et aucun panneau ne chevauche la barre.
5. **Attendre le même tick, comme Lot1001.** Avec `Lot690.Jusqua`, il attend que toutes ces conditions tiennent :
   - `Partie.Occupee` et `horloge.RequeteEnVol` sont faux ;
   - `Partie.Comptes` est présent au tick du monde lu, et `horloge.Lue.Tick` l'égale ;
   - la barre ne dit plus `Comptes en attente du monde`.
6. **Juger, dans la même image, sans `yield`.**
   - Avec `-forge1004Avance`, il pousse d'abord un tick et l'attend (`Lot690.PousserTick(carte.port).Result`, statut 200).
   - Il relit lui-même les comptes de la maison du joueur (`new ClientMaison(carte.port, TimeSpan.FromSeconds(10)).LireComptes(id)`), qui doivent être présents.
   - **Même tick** : le tick servi égale celui de `Partie.Comptes` et `horloge.Lue.Tick`. Sinon : `barre lue au tick T, comptes servis au tick T'`.
   - **Le grenier et la part** : la barre égale le texte que le scénario écrit lui-même depuis ces comptes. Ce texte est : le nom, `"Prélèvement : " + (part × 100).ToString("0.##", fr-FR) + " %"`, puis `"Grenier : "` suivi du grenier trié en ordinal, chaque marchandise écrite avec `TexteDuMonde.Masse`, le tout joint par `" · "` (comme `Lot1001.Attendu`). La barre contient `Prélèvement : 60 %`. Sinon : `barre « … » ≠ comptes « … »`.
   - **En pause** : `horloge.Lue.JoursParSeconde` vaut 0. La date égale `HorlogeDeCarte.Decrire(horloge.Lue)` et finit par `"\nEn pause"`. Le libellé du bouton « Pause / Reprendre » dit « Reprendre ». Sinon : `maison pas en pause : <écart>`.
   - La barre et la date passent `TexteDuMonde.Interdit(texte, id)` et `TexteDuMonde.SansUnite`.
   - **Rien n'est coupé à 1280 × 720.** On juge chaque `Text` actif du bandeau (le titre, la date, la barre, les libellés des commandes du temps) et celui du « Menu » :
     - `preferredWidth` ≤ largeur de son cadre + 0,5, et `preferredHeight` ≤ hauteur de son cadre + 0,5 ;
     - la boîte de ses glyphes (`cachedTextGenerator.verts`, position ÷ `pixelsPerUnit`, dans le repère du `Text`, passée en coins d'écran) tient dans l'image et dans le cadre du bandeau ;
     - les boîtes de glyphes du titre, de la date et de la barre ne se chevauchent pas, et ne chevauchent aucun bouton de la barre.

     Chaque bouton de la barre (« Menu », les deux icônes, « Ralentir », « Pause / Reprendre », « Accélérer ») tient dans le cadre du bandeau et dans l'image. Sinon : `texte coupé dans la barre : « <nom> » <mesure>`.
7. **Rejuger.** Il laisse passer 10 images, puis rejuge les étapes 2 et 6 (sans pousser de tick) et le chevauchement de l'étape 4.
8. **Tracer.** Il écrit `CAPTURE_1004 barre « <barre sur une ligne> » · date « <date sur une ligne> » au tick T, comptes servis au tick T · commandes : Puissances, Habitants, Flux dans la bande ; Terres et comptes, Autres maisons dans la barre ; Menu · aucun panneau sur la barre · rien de coupé à 1280 × 720`.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell, les cinq commandes de la section Photo, chacune dans son dossier neuf.

**SC1 — La barre d'une maison en pause dit les comptes servis au même tick.** `PHOTO` sort 0, avec `*--barre-en-pause.png` et la trace `CAPTURE_1004`. Dans la trace, le tick de la barre égale le tick servi, la barre contient `Prélèvement : 60 %` et `Grenier :`, et la date finit par `En pause`. Contre-épreuve : SC2.

**SC2 — Une barre lue un tick plus tôt échoue.** `AVANCE` sort 1, sans image, et son journal dit `barre lue au tick`.

**SC3 — Une commande de l'ancien panneau perdue échoue.** `PERDRE` sort 1, sans image, et son journal dit `commande « Autres maisons » perdue`.

**SC4 — Aucun dossier ne recouvre la barre.** Dans `PHOTO`, l'étape 4 passe, avec trois panneaux ouverts puis refermés. Contre-épreuve : `RECOUVRIR` sort 1, sans image, et son journal dit `« Les autres maisons » recouvre la barre`.

**SC5 — À 1280 × 720, rien n'est coupé dans la barre.** Dans `PHOTO`, l'étape 6 passe à 1280 × 720. Contre-épreuve : `COUPER` sort 1, sans image, et son journal dit `texte coupé dans la barre : « Lecture de la maison… »`.

**SC6 — Rien d'autre ne bouge.**
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

Le compte rendu donne les cinq commandes, leurs codes de sortie, la trace `CAPTURE_1004`, la ligne d'erreur de chaque contre-épreuve, et ce que montre l'image.

## Hors périmètre
- Tout changement d'écran : la barre, les icônes, le Menu, la date et les feuillets sont pris tels que #1001, #1002 et #1003 les ont livrés.
- Les tests EditMode : aucun n'est ajouté ni touché ; la preuve est le scénario.
- Le jeu qui s'ouvre en pause et la ligne du prochain geste (#860) ; la langue visuelle de la barre (#849, #850).
- La définition du PNG : la chaîne l'écrit à 1600 × 900 (`CitadelPlayCheck.Capture`). C'est la même forme 16:9 que les 1280 × 720 jugés dans le scénario.
- Le service, `jeu/`, `HorlogeDeCarte`.

## Photo
La carte autour de Mistra, après trente jours à 60 % de part, monde en pause, comme la photo du lot 1001. En haut, la barre entière :
- « FORGE · Le cabinet », Menu, la date (« Jour … de 1400 », puis « En pause »), les deux icônes, et « Ralentir », « Reprendre », « Accélérer » ;
- dessous, le nom de la maison de Mistra · « Prélèvement : 60 % » · « Grenier : … », aux nombres du jour servi.

À gauche, sous la barre, le feuillet « Terres et comptes » ouvert porte les mêmes comptes. En bas, la carte est libre, sans le panneau « Parcourir le monde ». En bas à droite se trouvent la bande des modes et sa légende. Le scénario `Lot1004.cs` (Périmètre) joue les étapes ci-dessus. Il juge à 1280 × 720, et la chaîne écrit l'image à la fin du scénario.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1004 -forgeCaptures 3d/unity/Temp/lot1004-photo -logFile 3d/unity/Temp/lot1004-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1004 -forgeCaptures 3d/unity/Temp/lot1004-avance -forge1004Avance -logFile 3d/unity/Temp/lot1004-avance.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1004 -forgeCaptures 3d/unity/Temp/lot1004-perdre -forge1004Perdre -logFile 3d/unity/Temp/lot1004-perdre.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1004 -forgeCaptures 3d/unity/Temp/lot1004-recouvrir -forge1004Recouvrir -logFile 3d/unity/Temp/lot1004-recouvrir.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1004 -forgeCaptures 3d/unity/Temp/lot1004-couper -forge1004Couper -logFile 3d/unity/Temp/lot1004-couper.log
```

La première (`PHOTO`) sort 0 avec `*--barre-en-pause.png` : c'est la photo. Les quatre autres sont les contre-épreuves :
- `AVANCE` (SC2) : la barre reste au tick d'avant ;
- `PERDRE` (SC3) : « Autres maisons » a disparu ;
- `RECOUVRIR` (SC4) : un feuillet monte sur la barre ;
- `COUPER` (SC5) : la barre devient trop étroite pour son texte.

Chacune sort 1, sans image. Le codeur ouvre la photo lui-même. Les PNG restent hors du dépôt.
