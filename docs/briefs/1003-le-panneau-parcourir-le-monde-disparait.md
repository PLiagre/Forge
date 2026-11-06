# Lot #1003 — Le panneau « Parcourir le monde » disparaît
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Le panneau « Parcourir le monde » quitte le bas de la carte. Son aide devient la phrase du bouton « Menu », et l'état de la carte s'écrit au centre de sa vue. Chaque commande qu'il portait garde sa place, dans la barre ou dans la bande des modes.

## Le joueur
Le joueur voit la carte de 1400 libre en bas à gauche : plus aucun panneau ne cache la Grèce, l'Italie ou la Méditerranée sous le monde qu'il gouverne. Tout ce qui compte est en haut, dans une seule barre : sa maison, la date, le temps, son grenier, sa part, ses deux dossiers et le Menu. S'il ne sait plus les gestes, il pose le pointeur sur « Menu », qui les lui dit (« Clic : choisir une terre · Glisser : déplacer · Molette : zoomer · Échap : fermer »), entiers même sur un écran de 1280 × 720. Tant que la carte n'est pas servie, « La carte se prépare… » s'écrit au milieu de la vue, là où il regarde. C'est le troisième des quatre morceaux du geste « Une seule barre en haut » du jalon 4 (`CAP.md`, lot 21, #859 : « le panneau « Parcourir le monde » disparaît »). Ce geste sert la décision du jalon : lire son grenier et sa part d'un coup d'œil, au même endroit, avant d'envoyer des bras au chantier. #1001 a mis le grenier et la part dans la barre, #1002 les dossiers en icônes ; le sous-lot 4 (Lot859) prouvera le geste entier.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/` ni le service ne bougent, et aucune lecture n'est ajoutée.

## Périmètre
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot855.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot891.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot943.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot963.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot964.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot965.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1003.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1003.cs.meta
docs/briefs/1003-le-panneau-parcourir-le-monde-disparait.md

Tout autre chemin est interdit, en particulier `MenuCabinet.cs`, `MenuCabinetTests.cs`, `Infobulle.cs`, `SocleInterface.cs`, `CalquesCarte.cs`, `PassageALaCapitaleTests.cs` (sa constante 872 reste vraie : rien ne descend plus bas), `jeu/` et les scénarios `Lot549`, `Lot658`, `Lot690`, `Lot879`, `Lot892`, `Lot944`, `Lot1001`, `Lot1002`. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 51d8cc58.

La réécriture des vérifications suit la décision A du pilote sur #859 (technique) : chaque vérification qui cherchait le panneau cherche la barre ou le Menu, aussi exigeante. Elle couvre aussi les trois qui rougiraient sans être nommées par l'issue : `Chaque_icone_de_la_barre_a_sa_phrase_et_son_motif`, `Aucun_dossier_ne_recouvre_la_barre` (#1002) et Lot963.

**`CabinetDeCarte.cs`.**
- Le panneau « Parcourir le monde » et le `Text` de l'aide ne sont plus posés. Le fichier ne contient plus la chaîne « Parcourir le monde ». `AIDE` reste, inchangée.
- Après `menu.Initialiser`, la phrase de l'`Infobulle` du bouton « Menu » (enfant direct de la toile) devient sa phrase d'origine, puis `"\n"`, puis `AIDE` : `MenuCabinet.cs` ne change pas.
- `public const string ETAT = "État de la carte"`. Un `Text` de ce nom, enfant direct de la toile, est posé par `SocleInterface.Texte(toile, "La carte se prépare…", 343, 492, 600)`, puis 600 × 96, `alignment` `MiddleCenter`, couleur `papier`, `raycastTarget` faux. Son centre (643, 540) est celui de la vue de la carte (0,67 × 1920 / 2).
- Dans `Afficher` : si `carte.CellulesServies < 0`, l'état est actif et dit `carte.TexteAffiche ?? "La carte se prépare…"` ; sinon il est inactif.

**`CabinetDeCarteTests.cs`.** Les lignes retirées sont les seules listées ici ; tout le reste ne change pas.
- `LesAidesDisentLesNouveauxGestes` : la première assertion sur `AIDE` et la fin (texte du menu, fichier, seuil) restent. Les lignes du `Text` nommé `AIDE` deviennent :
  - aucun `Text` de la racine ne dit `AIDE` seule ;
  - la phrase du bouton « Menu » commence par `"Ouvre ou ferme le menu"` et finit par `"\n" + AIDE` ;
  - montrée par `Infobulle.Montrer` au centre du bouton, le `Text` de l'infobulle a `preferredHeight` ≤ sa hauteur (+ 0,5) ;
  - à 1280 × 720 : `Infobulle.Placer(p, taille × 2/3, (1280, 720))`, avec `p` = (260, 692), le centre du Menu à cette définition. Le rectangle rendu tient dans (0, 0, 1280, 720) et ne couvre pas `p`.
- `La_bande_des_modes_et_sa_legende_restent_a_leur_place` :
  - l'assertion sur `guide` (place 24, 872, taille 740 × 184, sans « Puissances » ni « Habitants ») devient : `toile.Find("Parcourir le monde")` est nul, et la toile porte exactement trois boutons « Puissances », « Habitants », « Flux », chacun enfant de `BANDE` ;
  - la dernière ligne (aide ≤ 692) devient : le `Text` `ETAT` qui dit « La carte se prépare… » a `preferredWidth` ≤ 600. En 1920 × 1080 et 1280 × 720, sa `Zone` tient dans la vue de la carte (x ≤ 0,67 × largeur) et ne chevauche ni `BANDE` ni `LEGENDE`.
- `Chaque_icone_de_la_barre_a_sa_phrase_et_son_motif` : l'assertion « reste dans le guide » devient `toile.Find("Parcourir le monde")` nul, et chaque bouton de ce nom a pour parent le conteneur `DOSSIERS`.
- `Aucun_dossier_ne_recouvre_la_barre` : « Parcourir le monde » sort de la liste `SupersetOf`. Une assertion ajoutée exige qu'aucun panneau de la liste ne porte ce nom.
- Cas neuf `Aucun_panneau_Parcourir_le_monde_ne_reste`, décrit en SC1.
- Cas neuf `L_etat_de_la_carte_parle_au_centre_de_sa_vue`, décrit en SC2.

**Scénarios.** Chacun garde ses étapes, ses jugements et sa contre-épreuve. Seule change la cible qui était le panneau, et le commentaire de tête qui le nomme.
- `Lot855`, étape 3 : `GUIDE` devient le bandeau « FORGE · Le cabinet ». Le clic se joue en deux points : `Q`, le centre du bandeau, et `M`, le centre du bouton « Menu ». Chacun doit être au-dessus de la vue de la carte, `HorsCarte` vrai, et le clic ne garde rien. La trace `CAPTURE_855` donne `Q` et `M`.
- `Lot891`, `Visible` : `{ "Plan du bourg", "Parcourir le monde" }` devient `{ "Plan du bourg", "FORGE · Le cabinet", "Menu" }`.
- `Lot943`, `Visible` : `{ GUIDE, CalquesCarte.BANDE }` devient `{ "FORGE · Le cabinet", "Menu", CalquesCarte.BANDE }`. La constante `GUIDE` est retirée.
- `Lot963` (étape 6), `Lot964` (étape 5) : « Parcourir le monde » devient « Menu » dans la liste des panneaux que la légende et la bande ne recouvrent pas.
- `Lot965` : « Parcourir le monde » devient « Menu » dans `DOSSIERS`.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell.
- `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`.
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1003-interface.xml -logFile 3d/unity/Temp/lot1003-interface.log`. Elle sort 0, sans échec ni cas ignoré.
- `P` = `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier`.

**SC1 — Aucun panneau « Parcourir le monde » ne reste, chaque commande a sa place (`I`, cas `Aucun_panneau_Parcourir_le_monde_ne_reste`).**
- Une fonction locale `Restes()` rend chaque `Transform` de la racine, inactifs compris, nommé « Parcourir le monde », ou dont le `Text` dit « Parcourir le monde ». Elle rend vide.
- `Assets/Interface/CabinetDeCarte.cs` ne contient pas « Parcourir le monde ».
- Chaque commande de l'ancien panneau est un seul bouton dans la toile, à sa place :
  - « Puissances », « Habitants » et « Flux » sous `BANDE` ;
  - « Terres et comptes » et « Autres maisons » sous `DOSSIERS` ;
  - « Menu », enfant direct de la toile, dont la phrase finit par `AIDE`.
- Le `Text` `ETAT` est un enfant direct de la toile.
- Contre-épreuve, dans le cas : `SocleInterface.Panneau(toile, "Parcourir le monde", 24, 872, 740, 184)` posé, `Restes()` le rend ; puis il est détruit.

**SC2 — L'état de la carte parle au centre de sa vue (`I`, cas `L_etat_de_la_carte_parle_au_centre_de_sa_vue`).** Avec `Poser(carte, "CellulesServies", …)` :
- à −1, après `Afficher()`, `ETAT` est actif et dit « La carte se prépare… » ;
- sa `Zone` (k = 1) a son centre à 1 px près de (643,2 ; 540), son `raycastTarget` est faux, son alignement `MiddleCenter` ;
- à 12, il est inactif ; remis à −1, il revient.

Contre-épreuve : un état posé en (24, 960), ou resté actif carte servie, fait rougir le cas.

**SC3 — Les cas réécrits et les autres passent (`I`).** `I` passe en entier, y compris :
- les quatre cas réécrits ;
- `ChaqueCommandeDuCabinetDitCeQuElleFait` ;
- `LeCabinetMontreLaPhraseDuBoutonSurvole` (l'infobulle du Menu, plus longue, reste entière) ;
- `SansHorlogeRecueLesCommandesDuTempsRestentInactives` ;
- `Sans_maison_la_barre_le_dit` ;
- tout `MenuCabinetTests` et `DossierMaisonTests`.

Puis `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot1003-pont.xml -logFile 3d/unity/Temp/lot1003-pont.log` sort 0 (`PassageALaCapitaleTests`).

**SC4 — Les six scénarios réécrits, et leurs contre-épreuves.** Chacune des commandes suivantes sort 0 avec son image et sa trace `CAPTURE_<n>` ; le codeur regarde chaque image.
- `P -forgeLot 855 -forgeCaptures 3d/unity/Temp/lot1003-855 -logFile 3d/unity/Temp/lot1003-855.log`
- `P -forgeLot 891 -forgeCaptures 3d/unity/Temp/lot1003-891 -logFile 3d/unity/Temp/lot1003-891.log`
- `P -forgeLot 943 -forgeCaptures 3d/unity/Temp/lot1003-943 -logFile 3d/unity/Temp/lot1003-943.log`
- `P -forgeLot 963 -forgeCaptures 3d/unity/Temp/lot1003-963 -logFile 3d/unity/Temp/lot1003-963.log`
- `P -forgeLot 964 -forgeCaptures 3d/unity/Temp/lot1003-964 -logFile 3d/unity/Temp/lot1003-964.log`
- `P -forgeLot 965 -forgeCaptures 3d/unity/Temp/lot1003-965 -logFile 3d/unity/Temp/lot1003-965.log`

Chacune, rejouée avec sa contre-épreuve dans un dossier neuf (`…-contre`), sort 1 sans image :
- 855 avec `-forge855Glisser` ;
- 891 avec `-forge891Tick` ;
- 943 avec `-forge943Annee` ;
- 963 avec `-forge963Relire` ;
- 964 avec `-forge964Fleches` ;
- 965 avec `-forge965Remonter`.

Le compte rendu donne chaque trace, et la ligne d'erreur de chaque contre-épreuve.

**SC5 — La photo et sa contre-épreuve.** `PHOTO` (section Photo) sort 0 avec son image et la trace `CAPTURE_1003`. `PANNEAU` sort 1, sans image, et son journal dit `panneau « Parcourir le monde » encore là`.

**SC6 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `git diff origin/master -- 3d/unity/Assets/Interface/Tests` ne retire que les lignes listées au Périmètre.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Editor/Captures` ne change, dans les six scénarios, que la cible du panneau, l'étape 3 de Lot855 et les commentaires qui le nomment.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- La preuve du geste entier « Une seule barre en haut » (Lot859) : sous-lot 4 de #859.
- Le texte du menu, sa place et son panneau ; `MenuCabinet.cs`.
- La ligne du prochain geste (#860) et la langue visuelle (#849, #850).
- Le message de `CarteDessinee` lui-même (« carte : en attente de … ») : il est écrit tel qu'il est servi, comme avant.
- `PassageALaCapitaleTests`, le service et `jeu/`.

## Photo
La carte de 1400 avec le vrai cabinet, sans maison choisie, rendue à 1280 × 720. En haut, la barre entière : « FORGE · Le cabinet », Menu, la date, les deux icônes, les trois commandes du temps, et dessous « Aucune maison choisie ». En bas à gauche, la carte est libre : plus de panneau. En bas à droite, la bande des modes et sa légende. Le pointeur est sur « Menu », et son infobulle dit « Ouvre ou ferme le menu : les gestes, le clavier, le volume. » puis « Clic : choisir une terre · Glisser : déplacer · Molette : zoomer · Échap : fermer », entière dans l'image.

Le scénario `[ScenarioDeCapture(1003, "barre-sans-panneau")]` de `Lot1003.cs` est une `static class Lot1003` avec le drapeau `-forge1003Panneau`. Il suit ces étapes et lève à la première faute :

1. **Ouvrir la carte, comme Lot1002.** `Lot549.Ouvrir`, `CabinetDeCarte`, toile `Cabinet` active, survol et parcours `automatique`, puis `Lot690.Jusqua(Lot690.LecturePrete(…))`.
2. **Le panneau est parti.** Avec `-forge1003Panneau`, le scénario pose d'abord lui-même `SocleInterface.Panneau(toile, "Parcourir le monde", 24, 872, 740, 184)`. Puis aucun `Transform` de la scène, inactifs compris (`FindObjectsByType<Transform>(FindObjectsInactive.Include, …)`), ne porte ce nom. Sinon : `panneau « Parcourir le monde » encore là : <chemin>`.
3. **Chaque commande a sa place.** Les mêmes places qu'en SC1 :
   - « Puissances », « Habitants », « Flux » sous `BANDE` ;
   - « Terres et comptes », « Autres maisons » sous `"FORGE · Le cabinet/" + DOSSIERS` ;
   - un seul « Menu », dont la phrase finit par `AIDE`.

   Chaque bouton est actif. `ETAT` existe et est inactif, la carte étant servie (`CellulesServies` ≥ 0). Sinon, l'erreur nomme l'écart.
4. **Cadrer à 1280 × 720.** `Lot549.Photographier(camera, carte)`, `camera.rect` plein, `targetTexture` 1280 × 720, `ResetAspect()`. La toile passe en `ScreenSpaceCamera` sur cette caméra, à `nearClipPlane + 0.2`. Puis `yield return null` et `Canvas.ForceUpdateCanvases()`.
5. **Survoler « Menu », comme Lot1002.**
   - Le premier objet sous le centre du bouton (`EventSystem.RaycastAll`) est « Menu » ou un de ses enfants.
   - `ExecuteEvents.pointerEnterHandler` y montre une seule « Infobulle ». Son texte égale la phrase du Menu, et ses coins d'écran tiennent dans l'image (0,5 px près). Sinon : `infobulle du Menu coupée : <rect> dans <image>`.
   - La bande des modes et le bandeau sont entiers dans l'image.
6. **Rejuger.** Il laisse passer 10 images, puis rejuge les étapes 2, 3 et 5.
7. **Tracer.** Il écrit `CAPTURE_1003 aucun panneau « Parcourir le monde » · commandes : Puissances, Habitants, Flux dans la bande ; Terres et comptes, Autres maisons dans la barre · infobulle du Menu <rect> dans <image> · « <phrase sur une ligne> »`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1003 -forgeCaptures 3d/unity/Temp/lot1003-photo -logFile 3d/unity/Temp/lot1003-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1003 -forgeCaptures 3d/unity/Temp/lot1003-panneau -forge1003Panneau -logFile 3d/unity/Temp/lot1003-panneau.log
```

La première (`PHOTO`) sort 0 avec `*--barre-sans-panneau.png` : c'est la photo. La seconde (`PANNEAU`) est la contre-épreuve de SC5 : le panneau remis la fait sortir 1, sans image. Le codeur ouvre la photo lui-même. Les PNG restent hors du dépôt. Le compte rendu donne les deux commandes, leurs sorties, la trace `CAPTURE_1003`, la ligne d'erreur de `PANNEAU` et ce que montre l'image.
