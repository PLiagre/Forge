# Lot #1002 — Les dossiers deviennent des icônes de la barre
Jalon : J4 · Machine : pc · Taille prévue : 250 lignes

## But
« Terres et comptes » et « Autres maisons » deviennent deux icônes de la barre du haut, chacune avec son motif et sa phrase au survol. Elles ouvrent leur feuillet sous la barre, sans jamais la recouvrir.

## Le joueur
Le joueur ouvre ses comptes et le journal des autres maisons depuis la barre du haut, juste à côté de la date et du temps, sans aller chercher un bouton en bas à gauche dans le panneau « Parcourir le monde ». Deux icônes y sont gravées : un coffre pour « Terres et comptes », deux pignons pour « Les autres maisons ». Au survol, chacune dit ce qu'elle ouvre (« Terres et comptes : ouvre ou ferme… »). Un clic ouvre le feuillet sous la barre : la date, le temps, le grenier et la part restent lisibles pendant que le feuillet est ouvert. C'est le deuxième des quatre morceaux du geste « Une seule barre en haut » du jalon 4 (`CAP.md`, lot 21, #859 : « ses dossiers en icônes »). Ce geste sert la décision du jalon : lire son grenier et sa part d'un coup d'œil avant d'envoyer des bras au chantier. #1001 a mis le grenier et la part dans la barre. Le sous-lot 3 retirera le panneau « Parcourir le monde » et le sous-lot 4 prouvera le geste entier.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/` ni le service ne bougent, et aucune lecture n'est ajoutée : les feuillets lisent `/maison`, `/ia` et `/maisons` comme avant.

## Périmètre
3d/unity/Assets/Interface/EmblemeCommande.cs
3d/unity/Assets/Interface/DossierMaison.cs
3d/unity/Assets/Interface/DossierVoisins.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot963.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1002.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1002.cs.meta
docs/briefs/1002-les-dossiers-deviennent-des-icones-de-la-barre.md

Tout autre chemin est interdit. C'est vrai en particulier pour `DossierMaisonTests.cs`, `SocleInterface.cs`, `Feuillet.cs`, `MenuCabinet.cs`, `CalquesCarte.cs`, `jeu/` et les scénarios `Lot549`, `Lot655`, `Lot658`, `Lot690`, `Lot855`, `Lot879`, `Lot891`, `Lot892`, `Lot943`, `Lot944`, `Lot964`, `Lot965` et `Lot1001` : ils sont lus, jamais modifiés. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master b6762e46.

**`EmblemeCommande.cs`.**
- `Poser` donne à « Terres et comptes » un motif à lui, `"coffre"` : une caisse à couvercle et serrure. « Menu » garde `"livre"`. « Autres maisons » reçoit `"maisons"` : deux pignons côte à côte.
- Les deux motifs neufs sont tracés dans `OnPopulateMesh` avec `Trait`, comme les autres, dans un carré de ±8 px.
- Nouvelle fonction `public static Button Icone(Transform barre, string nom, float x, System.Action action, string phrase)`. Elle appelle `SocleInterface.Commande(barre, nom, x, 0, action, phrase: phrase)`, puis :
  - fixe le bouton à 56 × 44 ;
  - rend inactif le `GameObject` du `Text` du bouton : le nom n'est plus écrit, la phrase le dit ;
  - recentre le `"Repère " + motif` (ancres et pivot à (0,5 ; 0,5), position (0, 0), échelle 1,5).
- Un nom sans motif lève une `ArgumentException` (« icône sans motif : … »). `Icone` ne pose donc jamais une icône vide.

**`CabinetDeCarte.cs`.**
- `public const string DOSSIERS = "Dossiers de la barre"`. Dans `Construire`, juste après le bandeau, un `RectTransform` nu de ce nom est créé, enfant de « FORGE · Le cabinet », ancres et pivot à (0, 1), position (1112, −20), taille 136 × 44. Les icônes sont ses enfants : le bandeau garde ses trois boutons enfants directs (`SansHorlogeRecueLesCommandesDuTempsRestentInactives` en compte toujours 3).
- La date passe de 760 à 600 de large (480 → 1080). Elle finit ainsi avant les icônes (1112 → 1248), et les icônes avant « Ralentir » (1296).
- `DossierVoisins` reçoit ce conteneur à la place du `guide`. `DossierMaison` le reçoit en dernier paramètre.
- Le panneau « Parcourir le monde », son aide et ses tests ne changent pas : leur retrait est le sous-lot 3.

**`DossierMaison.cs`.**
- Les deux `Initialiser` gagnent un dernier paramètre optionnel, `Transform barre = null`.
- Sans barre, le bouton reste sur la toile en (1000, 20), 260 × 44, comme avant : `DossierMaisonTests` ne change pas et reste vert.
- Avec la barre : `EmblemeCommande.Icone(barre, "Terres et comptes", 0, bascule, phrase)`.
- La phrase devient, dans les deux cas : `"Terres et comptes : ouvre ou ferme les terres et les comptes de votre maison."`.

**`DossierVoisins.cs`.**
- `Initialiser(Transform toile, Transform barre, int port)` pose `EmblemeCommande.Icone(barre, "Autres maisons", 80, bascule, "Les autres maisons : ouvre ou ferme le journal de leurs ordres.")`.
- Le feuillet garde son titre « Les autres maisons » et sa place.

**`Lot963.cs`.**
- Le scénario clique `Bouton("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS, "Autres maisons")` au lieu de `Bouton("Parcourir le monde", "Autres maisons")`, et son commentaire de tête le dit.
- Rien d'autre ne change. Les étapes 2 à 6, la liste des cinq panneaux de l'étape 6 (« Parcourir le monde » compris : il existe encore) et la contre-épreuve `-forge963Relire` restent telles quelles : même exigence.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell.
- `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`.
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1002-interface.xml -logFile 3d/unity/Temp/lot1002-interface.log`. Elle sort 0, sans échec ni cas ignoré, et les cas neufs réussissent.

**SC1 — Chaque icône a sa phrase et son motif (`CabinetDeCarteTests.cs`, `I`).** Cas `Chaque_icone_de_la_barre_a_sa_phrase_et_son_motif`. On prend `toile.Find("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS)`.
- Il porte exactement deux `Button`, « Terres et comptes » puis « Autres maisons » par x croissant, chacun de 56 × 44, sans aucun `Text` actif.
- Chacun a un enfant `Repère coffre` (pour le premier) ou `Repère maisons` (pour le second), et aucun `Repère livre`.
- La phrase de son `Infobulle` n'est pas vide, diffère de son nom et de celle de l'autre icône, et commence par le titre du feuillet qu'elle ouvre suivi de `" : "` (« Terres et comptes : », « Les autres maisons : »).
- Un clic sur l'icône active le feuillet de ce titre (l'enfant direct de la toile qui porte un `ScrollRect`), un second clic le ferme.
- Dans toute la toile, il n'y a qu'un bouton de chacun de ces deux noms. « Parcourir le monde » n'en a plus aucun.
- `EmblemeCommande.Icone(conteneur, "Sans motif", 0, null, "témoin")` lève `ArgumentException`.

Contre-épreuve : une icône sans phrase, une icône restée dans le guide, ou « Terres et comptes » qui garde le livre du Menu font rougir le cas.

**SC2 — Aucun dossier ne recouvre la barre (`CabinetDeCarteTests.cs`, `I`).** Cas `Aucun_dossier_ne_recouvre_la_barre`. Après `Proposer()`, on ouvre les deux feuillets par leurs icônes et le menu par « Menu », puis `Canvas.ForceUpdateCanvases()`.
- Chaque panneau du socle, actif ou non, ne chevauche pas le cadre de « FORGE · Le cabinet » (à 0,5 px près, coins du monde). Un panneau du socle est un enfant direct de la toile qui porte un enfant « Filet », hors le bandeau lui-même. Cela couvre « Terres et comptes », « Les autres maisons », « Menu du cabinet », « Plan du bourg », « Votre maison », « Territoire conservé » et « Parcourir le monde ».
- Le conteneur des icônes tient dans le bandeau, au-dessus du filet (bas ≤ 70 dans la toile).
- Il ne chevauche ni le `Text` « Lecture de la date… », ni le `Text` « Lecture de la maison… », ni « Menu », « Ralentir », « Pause / Reprendre » ou « Accélérer ».
- La date tient dans ses 600 px : `preferredWidth` ≤ 600 pour `"Date indisponible : le monde ne répond pas"` et pour `HorlogeDeCarte.Decrire` d'un jour 365 de 1400 à 1,5 jour par seconde.

Contre-épreuve : un feuillet posé en y 80, ou le conteneur laissé en x 1000 (sur la date), font rougir le cas.

**SC3 — Les cas existants passent sans changer (`I`).** `I` passe en entier, y compris :
- `SansHorlogeRecueLesCommandesDuTempsRestentInactives` (trois boutons enfants directs) ;
- `ChaqueCommandeDuCabinetDitCeQuElleFait` ;
- `LeCabinetMontreLaPhraseDuBoutonSurvole` (l'infobulle des deux icônes reste entière) ;
- `La_bande_des_modes_et_sa_legende_restent_a_leur_place` ;
- `LesAidesDisentLesNouveauxGestes` ;
- tout `DossierMaisonTests`, qui pose le bouton sur la toile passée, sans barre.

**SC4 — Lot963 clique l'icône de la barre.** On lance `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 963 -forgeCaptures 3d/unity/Temp/lot1002-963 -logFile 3d/unity/Temp/lot1002-963.log`. Elle sort 0, avec `*--mode-habitants.png` et la trace `CAPTURE_963`. La même commande avec `-forge963Relire -forgeCaptures 3d/unity/Temp/lot1002-963-relire -logFile 3d/unity/Temp/lot1002-963-relire.log` sort 1, sans image, et son journal dit `relancé une lecture`.

**SC5 — Sur le vrai service, la photo et sa contre-épreuve.** La commande `PHOTO` de la Photo sort 0 avec son image et la trace `CAPTURE_1002`. `RECOUVRIR` sort 1, sans image, et son journal dit `recouvre la barre`.

**SC6 — Les scénarios qui ouvrent les dossiers par leur nom.** Deux commandes sortent 0, chacune avec son image, et le codeur les regarde :
- `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot1002-944 -logFile 3d/unity/Temp/lot1002-944.log`. Ce scénario ouvre « Terres et comptes » par son bouton et juge chaque texte actif du cabinet.
- La même avec `-forgeLot 892 -forgeCaptures 3d/unity/Temp/lot1002-892 -logFile 3d/unity/Temp/lot1002-892.log`. Ce scénario cherche un seul « Autres maisons » sous la carte et lit son feuillet.

**SC7 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `git diff origin/master -- 3d/unity/Assets/Interface/Tests` ne montre que des lignes ajoutées.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot963.cs` ne change que la ligne du clic et le commentaire de tête.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Le retrait du panneau « Parcourir le monde », de son aide et de la réécriture de leurs vérifications (`LesAidesDisentLesNouveauxGestes`, `La_bande_des_modes…`, Lot855, Lot891, Lot943, Lot964, Lot965) : sous-lot 3 de #859.
- La preuve du geste entier (`Lot859`) : sous-lot 4.
- Le contenu des deux feuillets, leur place (24, 124) et leurs lectures : inchangés.
- Le Menu, son motif et sa place ; la bande des modes.
- La langue visuelle des icônes (#849) et la ligne du prochain geste (#860).
- `SocleInterface`, `Feuillet`, le service et `jeu/`.

## Photo
La carte de 1400 avec le vrai cabinet, sans maison choisie. En haut, la barre :
- « FORGE · Le cabinet », Menu, la date ;
- les deux icônes neuves (le coffre, les deux pignons) juste avant les trois commandes du temps ;
- dessous, « Aucune maison choisie ».

À gauche, le feuillet « Les autres maisons », ouvert par son icône, commence sous la barre. Le pointeur est posé sur l'icône « Terres et comptes », et son infobulle dit « Terres et comptes : ouvre ou ferme les terres et les comptes de votre maison. ».

Le scénario `[ScenarioDeCapture(1002, "icones-de-la-barre")]` de `Lot1002.cs` est une `static class Lot1002` avec le drapeau `-forge1002Recouvrir`. Il suit ces étapes et lève à la première faute :

1. **Ouvrir la carte, comme Lot879.** Il joue `Lot549.Ouvrir(camera, ouverte)`, prend `CabinetDeCarte` et la toile `Cabinet` (active), met `SurvolDeCarte` et `ParcoursDeCarte` en `automatique`, et attend `Lot690.LecturePrete(cabinet.Partie)` avec `Lot690.Jusqua`.
2. **Trouver les icônes.** Le conteneur est `toile.Find("FORGE · Le cabinet/" + CabinetDeCarte.DOSSIERS)`, actif, sinon : `dossiers de la barre introuvables`. Il porte exactement deux boutons, « Terres et comptes » puis « Autres maisons », actifs, chacun avec sa phrase. La toile n'a aucun autre bouton de ces deux noms, et le bandeau a trois boutons enfants directs. Sinon, l'erreur nomme l'écart.
3. **Ouvrir « Les autres maisons » par son icône.** Il clique l'icône (`onClick.Invoke()`). Le feuillet « Les autres maisons » (l'enfant direct de la toile qui porte un `ScrollRect`) est actif, sinon : `feuillet « Les autres maisons » fermé`. Avec `-forge1002Recouvrir`, le scénario remonte lui-même ce feuillet à `anchoredPosition` (24, −60).
4. **Cadrer, comme Lot879.** `Lot549.Photographier(camera, carte)`, `camera.rect` plein, `targetTexture` 1600 × 900, `ResetAspect()`. La toile passe en `ScreenSpaceCamera` sur cette caméra, à `nearClipPlane + 0.2`. Puis `yield return null` et `Canvas.ForceUpdateCanvases()`.
5. **Juger, en coins d'écran.**
   - Chaque panneau du socle actif (enfant direct de la toile avec un « Filet », hors le bandeau) ne chevauche pas le cadre du bandeau, réduit de 0,5 px. Sinon : `« <panneau> » recouvre la barre : <rect> sur <rect>`.
   - Les deux icônes sont entières dans le cadre du bandeau et dans l'image.
6. **Survoler l'icône « Terres et comptes », comme Lot879.**
   - Le premier objet sous le point central de l'icône (`EventSystem.RaycastAll`) est l'icône ou un de ses enfants.
   - `ExecuteEvents.pointerEnterHandler` y montre un seul « Infobulle », dont le texte égale la phrase de l'icône, entière dans l'image.
7. **Rejuger.** Il laisse passer 10 images, puis rejuge les étapes 5 et 6.
8. **Tracer.** Il écrit `CAPTURE_1002 icônes « Terres et comptes », « Autres maisons » dans la barre <rect> · feuillet « Les autres maisons » <rect> · infobulle « <phrase> »`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1002 -forgeCaptures 3d/unity/Temp/lot1002-photo -logFile 3d/unity/Temp/lot1002-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1002 -forgeCaptures 3d/unity/Temp/lot1002-recouvrir -forge1002Recouvrir -logFile 3d/unity/Temp/lot1002-recouvrir.log
```

La première commande (`PHOTO`) sort 0 avec `*--icones-de-la-barre.png` : c'est la photo. La seconde (`RECOUVRIR`) est la contre-épreuve de SC5 : le feuillet remonté sur la barre la fait sortir 1, sans image. Le codeur ouvre la photo lui-même. Les PNG restent hors du dépôt. Le compte rendu donne les deux commandes, leurs sorties, la trace `CAPTURE_1002`, la ligne d'erreur de `RECOUVRIR` et ce que montre l'image.
