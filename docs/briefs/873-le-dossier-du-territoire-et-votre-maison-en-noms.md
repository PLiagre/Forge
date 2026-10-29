# Lot #873 — Le dossier du territoire et « Votre maison » en noms
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Les dossiers « Territoire conservé » et « Votre maison » du cabinet parlent en noms, en dates et en unités : le joueur n'y voit plus aucune cellule, aucun rang, aucun tick.

## Le joueur
Le joueur ouvre une terre. Il y lit le nom de son bourg et la maison de son maître, la date du relevé, ses habitants écrits avec leur séparateur (« 12 345 habitants »), chaque lieu par son nom sans rang, ses réserves et son prélèvement en tonnes. « Votre maison » lui donne son nom, son siège, ses lieux tenus et la date du relevé. Avant de choisir, l'aperçu d'une maison dit « 12 345 habitants autour de Mistra ». Le reçu du choix porte une date, ou « au jour suivant ». Il sent qu'il lit le registre d'un clerc de 1400, pas une base de données : il trouve sa capitale, lit son grenier et sa part sans chercher. C'est le sous-lot 4 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, prise en main de la carte). C'est un lot de fond du geste **passer de la carte à sa ville d'un geste** : avant de descendre, le joueur doit savoir quelle terre il regarde.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, et ni `jeu/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. Tout est déjà servi : `/lieu?cell=` donne `date`, `noms.maisons` et, pour chaque lieu, `nom`, `maitre`, `stocks` et `flux_30j` ; `/monde` donne la date ; `/departs` donne `Habitants`, mesurés sur la cellule du siège ; `/horloge` donne le tick et la date.

## Périmètre
3d/unity/Assets/Interface/DossierTerritoire.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/DossierTerritoireTests.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot855.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot873.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot873.cs.meta
docs/briefs/873-le-dossier-du-territoire-et-votre-maison-en-noms.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot873-interface.xml -logFile 3d/unity/Temp/lot873-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté (zéro cas est un échec). Les tests s'écrivent d'abord, et on les voit rouges. Tous les mots passent par `Forge.Pont.TexteDuMonde` (#870), qui ne change pas : `Nombre`, `Date`, `Masse` et `Absence` écrivent ; `Interdit` et `SansUnite` jugent. Le séparateur des milliers est U+00A0.

**Le dossier du territoire.** `DossierTerritoire.Decrire(document, cellule)` garde ses refus actuels (cellule différente, liste vide, rang répété) et en ajoute deux, chacun une `ArgumentException` : « Bourg absent de la terre » quand aucun lieu n'a le rang 0, « Date non transmise » quand `document.Annee` est nulle. Ses lignes, dans l'ordre :
1. « <nom du rang 0> · <Maitre(racine, rang 0)> ». `Maitre` est la fonction existante ; un nom nul s'écrit « Nom du bourg non transmis ».
2. `TexteDuMonde.Date(new DateDuMonde(Annee, JourDeLAnnee))`.
3. `Nombre(population)` + « habitants dans le territoire », puis « Molette : parcourir les lieux ».
4. Pour chaque lieu : une ligne vide ; son nom seul, sans « · rang N » ; `Nombre(population)` + « habitants · » + la surface en km², écrite comme aujourd'hui ; la ligne du maître ; chaque réserve en « clé : » + `Masse(kg)` ; « Sur 30 jours : » + `Masse(preleve_kg)` + « prélevés » ; enfin « N personne(s) partie(s) · M personne(s) arrivée(s) », au pluriel au-delà de 1, avec `Nombre`.

`public static string Texte(string erreur, DocumentDuMonde document, long cellule)` porte les trois états du dossier, et `LateUpdate` l'appelle. Avec une erreur : « Lecture indisponible : » + `TexteDuMonde.Absence(erreur, cellule en texte invariant)`. Sans document : `public const string ATTENTE = "Lecture de la terre, de ses lieux et de ses réserves…"`. Sinon : `Decrire`, et une `ArgumentException` donne « Dossier incomplet : » + `Absence(message, cellule)`.

**« Votre maison » (`CabinetDeCarte.AfficherMaison`).**
- **Maison choisie** : son nom (ou `Absence(Absents["nom"])` s'il manque) ; « Siège : <Siege.Nom> » ; `Nombre(n)` + « lieux tenus » (« lieu tenu » pour 1) + « · relevé au » + `Date(monde.Donnees.Monde.Date)`. `MaisonLue` ne sert pas d'habitants : rien de plus.
- **Aperçu** : « <Nom> · <Siege.Nom> », puis `Nombre(Habitants)` + « habitants autour de » + `Siege.Nom`, puis « Suzerain : … » comme aujourd'hui.
- **Reçu accepté** : si l'horloge lue est au tick du reçu (`horloge.Lue?.Tick == recu.AppliqueeAuTick`), « Choix reçu le <Date(horloge.Lue.Date)>.\nReprenez le temps : le monde l'appliquera au jour suivant. » ; sinon, horloge nulle comprise, « Choix reçu ; le monde l'applique au jour suivant. ». Le tick va au journal, une fois par reçu : `Debug.Log("CabinetDeCarte : choix reçu au tick " + AppliqueeAuTick)`, avec un champ qui garde le dernier reçu journalisé.
- **Refus ou absence** : « Demande refusée : » + `Absence(Erreur)` ; « Envoi non confirmé : » + `Absence(Absence)`.

**SC1 — Le dossier parle en noms.** `INTERFACE`, cas `Le_dossier_dit_le_bourg_son_maitre_la_date_et_chaque_lieu_par_son_nom`. Il remplace le premier cas de `DossierTerritoireTests` : c'est la réécriture décidée en A sur #856. Le document témoin a `cell_id` 10340, `date` {1400, 9}, `population` 12345 et `noms.maisons` `{"m-1":{"nom":"Maison témoin"}}`. Son rang 0 « Bourg témoin » a le maître `m-1`, 12000 habitants, `nourriture` 1234.5 et le flux {2500, 3, 1}. Son rang 2 « Hameau témoin » n'a pas de maître, et porte 345 habitants, `nourriture` 9 et un flux `null`. Attendus :
- la ligne 1 vaut « Bourg témoin · Maison : Maison témoin » et la ligne 2 « jour 9 de 1400 » ;
- le texte contient « 12 345 habitants » (U+00A0), « nourriture : 1,23 t », « nourriture : 9 kg », « Sur 30 jours : 2,50 t prélevés », « 3 personnes parties · 1 personne arrivée », « Hameau témoin » et « Flux non transmis » ;
- ni « rang », ni « tick », ni « 1234 » ; `Interdit(texte, "10340")` et `SansUnite(texte)` sont nuls ;
- le juge mord : `Interdit("Cellule 10340 · tick 8", "10340")` vaut « Cellule ».

Contre-épreuve : l'ancien en-tête, « · rang 2 », ou un stock en kg au-delà de 1 000 rougit.

**SC2 — Les absences se disent sans identifiant.** `INTERFACE`. Le cas existant `Cellule_incorrecte_rang_duplique_et_echantillon_vide_echouent` garde ses trois refus. Son `Debut` reçoit la date et un rang 0 valide, pour que chaque refus vienne de sa propre cause. Le cas neuf `Bourg_et_date_absents_echouent_et_l_attente_ne_montre_rien` exige :
- sans rang 0, un message qui contient « Bourg » ; sans clé `date`, un message qui contient « Date » ;
- `Texte(null, null, 10340)` == `ATTENTE`, avec `Interdit(ATTENTE, "10340")` nul ;
- `Texte("Lecture refusée (404) : cell inconnu : reçu 10340", null, 10340)` == « Lecture indisponible : déclaré absent par le monde », avec `LogAssert.Expect` sur « TexteDuMonde : absence déclarée par le monde : … » ;
- un rang répété donne « Dossier incomplet : déclaré absent par le monde ».

`Le_contenu_long_defile_dans_un_cadre_qui_arrete_les_clics` ne change pas. Contre-épreuve : une attente qui dit « Cellule 10340 », ou une raison passée telle quelle, rougit.

**SC3 — « Votre maison » se date.** `INTERFACE`, cas ajouté à `CabinetDeCarteTests` : `LaMaisonDuJoueurDitSonNomSonSiegeSesLieuxEtLaDate`. Après `Publier(JOUEUR, trois LieuTenu)` puis `cabinet.Afficher()`, le `Text` nommé « Lecture de la partie… » vaut exactement « Maison\nSiège : Siège\n3 lieux tenus · relevé au jour 1 de 1400 ». Avec un seul lieu, il dit « 1 lieu tenu ». `Interdit` et `SansUnite` sont nuls. Contre-épreuve : « relevé au tick 1 » rougit.

**SC4 — L'aperçu dit les habitants autour du siège.** `INTERFACE`, cas ajouté `LApercuDuChoixDitLesHabitantsAutourDuSiege`. On pose, par `Poser`, une partie dont `MaisonDuJoueur` est nulle et un `DepartsLus` d'une seule fiche `(42, "Despotat témoin", "Maison témoin", SiegeDeDepart("Mistra", 0, 0), 10340, 12345, null, [])`. Puis `Afficher`, `onClick.Invoke()` du bouton « Maison témoin », et `Afficher` encore. Le `Text` nommé « Consultez une maison avant de vous engager. » vaut exactement « Despotat témoin · Mistra\n12 345 habitants autour de Mistra\nSuzerain : aucun », et `Interdit(…, "10340", "42")` est nul. Contre-épreuve : « dans la cellule du siège », ou « 12345 » sans séparateur, rougit.

**SC5 — Le reçu n'est daté qu'au tick de l'horloge.** `INTERFACE`, cas ajouté `LeRecuNEstDateQuAuTickDeLHorloge`. Même montage que SC4, plus `Poser(partie, "Recu", RecuIntention.AccepteeAu(7))` ; `Lue` se pose par `Poser` sur `HorlogeDeCarte`.
- Horloge nulle : « Choix reçu ; le monde l'applique au jour suivant. », et `LogAssert.Expect(LogType.Log, "CabinetDeCarte : choix reçu au tick 7")`.
- `HorlogeLue(7, (1400, 8), 0)` : « Choix reçu le jour 8 de 1400.\nReprenez le temps : le monde l'appliquera au jour suivant. »
- `HorlogeLue(8, (1400, 9), 0)` : la forme sans date, sans « jour 9 » ni « jour 8 ».
- `Refusee(409, "maison 10340 déjà prise")` : « Demande refusée : déclaré absent par le monde ».
- `Absente("service coupé")` : « Envoi non confirmé : service coupé ».

Pour chaque texte, `Interdit(…, "10340")` et `SansUnite` sont nuls. Contre-épreuve : un reçu daté alors que l'horloge est au tick 8, ou « au tick 7 » à l'écran, rougit.

**SC6 — L'étape 5 de `Lot855` attend le nom du bourg.** À l'étape 2, `Lot855` garde `lecture.Result.Lieu.Bourg.Nom` ; s'il est nul, `Echec("étape 2 : le rang 0 de la Morée n'a pas de nom servi : " + AbsenceDuNom)`. Le `debut` attendu devient « <nom du bourg> · » au lieu de « Cellule <id> · tick ». Les étapes 5 et 6 et la pose exigent aussi une deuxième ligne du dossier qui commence par « jour ». Les commandes, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 855 -forgeCaptures 3d/unity/Temp/lot873-855-photo -logFile 3d/unity/Temp/lot873-855-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 855 -forgeCaptures 3d/unity/Temp/lot873-855-glisser -forge855Glisser -logFile 3d/unity/Temp/lot873-855-glisser.log
```

La première sort 0, et `CAPTURE_855` montre un dossier qui commence par le nom du bourg de la Morée. La seconde sort 1 avec « aucune terre gardée après le geste ». Contre-épreuve : un dossier qui dit encore « Cellule … » fait échouer l'étape 5.

**SC7 — Rien d'autre ne bouge.** `INTERFACE` passe sur toute l'assemblée. `git diff origin/master -- 3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs` ne montre aucune ligne retirée ; dans `DossierTerritoireTests.cs`, seuls le premier cas et `Debut` perdent des lignes. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes. Contre-épreuve : un cas existant du cabinet retouché, ou un fichier hors du Périmètre, refuse la livraison.

## Hors périmètre
Restent hors du lot :
- la fiche de survol (`FicheDeCellule`), le texte qu'`Afficher` écrit avant `DossierTerritoire.LateUpdate` et le bandeau (`HorlogeDeCarte.Decrire`) : #872 ;
- `CommandesMaison`, les comptes, la part et le grenier, `Lot655` et `Lot656` : sous-lot 5 de #856 ;
- les légendes et `Lot657`/`Lot658` (sous-lot 6) ; le plan, les chantiers, les voisins, les calques et le menu (sous-lot 7) ; l'épreuve au vrai service (sous-lot 8) ;
- l'écriture de la surface en km² ; les raisons fabriquées par `LectureDossier`, qui passent par `Absence` ; le service et `jeu/`.

## Photo
La photo montre la carte de 1400 avec la Morée gardée. À droite, « Territoire conservé » s'ouvre sur « <bourg de la Morée> · Maison : … », puis « jour N de 1400 », les habitants avec séparateur et les lieux par leur nom. « Votre maison » montre l'aperçu de la Morée : « … habitants autour de Mistra ».

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot873.cs`, un scénario unique `[ScenarioDeCapture(873, "moree-en-noms")]` sur le modèle de `Lot855`. Il réutilise `Lot549.Ouvrir/Photographier` et les aides `internal` de `Lot690` sans les changer. Chaque attente est bornée par `Lot690.Jusqua`, et chaque absence échoue en nommant sa cause.
1. Ouvrir `Forge_Carte`, exiger le `CabinetDeCarte`, attendre `Lot690.LecturePrete(cabinet.Partie)`.
2. Prendre la seule fiche de `/departs` au siège « Mistra » et lire `/lieu?cell=` de sa cellule par `ClientLieu`. Exiger `Bourg.Nom` non nul et un point au rang 0. `carte.CelluleSous(point)` doit être la Morée ; puis `cabinet.Garder(cellule)`.
3. Exiger un seul bouton de libellé `fiche.Maison` dans « Votre maison/Maisons proposées » et appeler son `onClick.Invoke()`. Attendre que l'aperçu contienne `TexteDuMonde.Nombre(fiche.Habitants) + " habitants autour de Mistra"`.
4. Attendre que « Territoire conservé/Lecture du territoire » commence par « <attendu> · ». `attendu` est le `Bourg.Nom` de l'étape 2 ; avec `-forge873Voisin`, c'est le `Bourg.Nom` de `/lieu?cell=` pour `fiche.Voisins[0].CellId`, qui doit être différent. Exiger aussi :
   - une deuxième ligne égale à `TexteDuMonde.Date` de `DossierTerritoire.Document` ;
   - pour le dossier comme pour l'aperçu, `Interdit(texte, <cellule de la Morée>)` et `SansUnite(texte)` nuls.
   En cas d'échec, citer la première ligne lue.
5. Photo comme l'étape 7 de `Lot855` : `Lot549.Photographier`, caméra sur toute l'image, toile « Cabinet » en `ScreenSpaceCamera`. Exiger les deux panneaux entiers dans le champ et le dossier non défilé. Attendre dix images, puis refaire les vérifications de l'étape 4.
6. La trace `CAPTURE_873` donne la cellule et les deux premières lignes du dossier et de l'aperçu.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 873 -forgeCaptures 3d/unity/Temp/lot873-photo -logFile 3d/unity/Temp/lot873-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 873 -forgeCaptures 3d/unity/Temp/lot873-voisin -forge873Voisin -logFile 3d/unity/Temp/lot873-voisin.log
```

La première sort 0 avec une image `*--moree-en-noms.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image : son journal dit que le dossier commence par le bourg de la Morée, alors que le nom attendu est celui du voisin. Le codeur ouvre l'image lui-même. Une « Cellule », un « rang », un « tick », un « 10340-1 », un dossier en attente ou un panneau coupé refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, les sorties des deux contre-épreuves (SC6 et celle-ci) et ce que montre l'image.
