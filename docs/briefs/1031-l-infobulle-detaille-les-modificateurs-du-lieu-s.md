# Lot #1031 — L'infobulle détaille les modificateurs du lieu survolé
Jalon : J6 · Machine : pc · Taille prévue : 700 lignes

## But
Au survol d'une terre, l'infobulle de la carte ajoute aux trois lignes du dossier une ligne par modificateur qui joue sur son bourg, avec sa valeur, son nom, sa source et sa durée, dans l'ordre du registre. Elle donne ensuite le total de chaque grandeur, lus dans `GET /modificateurs` au tick du dossier.

## Le joueur
Au survol d'un lieu ou d'une province, le joueur lit chaque modificateur qui joue, comme dans EU4 : « Récolte : +10 % Moulin · bâtiment · tant que sa source tient », « Départs : +10 % Concorde (-2) · jauge du pays · … », chacun avec sa source et sa durée, puis le total par grandeur. Il voit pourquoi sa province rend plus ou se vide, et ce que son moulin ou sa Concorde lui valent. Cela prépare les décisions du jalon 6 : à quel bâtiment de quelle province va le grain, quand dépenser sa Plume pour affermir la Concorde. Une terre sans pose montre la même infobulle qu'aujourd'hui.

## Règle du monde
Sans objet : c'est un lot de vue. La vue lit le registre tel qu'il est (`jeu/sim/MODELE.md`, « Les modificateurs », paragraphe « Le détail »). Elle n'additionne rien : chaque ligne et chaque total sont ceux de `detail()`.

Le lot ajoute **des mots et un reste**, pas de règle. Ce sont trois champs de plus dans `document_des_modificateurs`, servis par `/modificateurs` et portés par la photographie :
- pour chaque grandeur d'un lieu, `nom` (le `nom` de `[grandeurs.<id>]`, « Récolte ») ;
- pour chaque ligne, `source_dite` : le mot de la sorte de sa source (« bâtiment », « jauge du pays »), lu dans une nouvelle table `[mots_des_sources]` de `data/modificateurs.toml`. Chaque source admise y a son mot. Une source sans mot, ou un mot pour une source inconnue, est refusé par `ModificateurInvalide` à la lecture. Cette table se lit à part, pas dans `Donnees` : les `M.Donnees(sources, grandeurs, definitions)` des tests existants ne changent pas ;
- pour chaque ligne, `reste_jours` : `(fin − tick publié) × TICK_DURATION_DAYS`, ou `null` sans fin.

Les poses, l'ordre, `total` et `facteur` ne changent pas. `MODELE.md`, « Le détail », dit ces trois champs. Niveau 2 pour les mots, comme le reste du fichier.

L'amorçage de la photo n'est pas le monde. Il pose sur Paris, au tick 0, cinq modificateurs par les fonctions du registre : un moulin, trois jauges de la France, et un événement d'épreuve. C'est un banc d'essai de l'infobulle, sur le précédent de `test_le_service_et_la_photographie_servent_le_detail` (« batiment:moulin-de-paris »). Mesuré le 8 novembre 2026, graine 0 : sans IA, la France n'a ni grain au grenier ni pose sur un an. Avec l'IA, son moulin arrive au jour 150 et sa Concorde reste à 0 toute l'année. Le Paris de la photo ne vient donc pas seul.

## Périmètre
jeu/sim/modificateurs.py
jeu/data/modificateurs.toml
jeu/sim/tests/test_modificateurs.py
jeu/sim/MODELE.md
3d/unity/Assets/ForgeLocal3D/Pont/TexteDuMonde.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/TexteDuMondeTests.cs
3d/unity/Assets/Interface/InfobulleDeTerre.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1031.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1031.cs.meta

### Ce que le codeur écrit

**Python (`jeu/sim/modificateurs.py`, `jeu/data/modificateurs.toml`).** Les trois champs de « Règle du monde », ajoutés dans `document_des_modificateurs` seulement. `detail()` et `Pose.en_document()` restent tels quels : `/pays` sert `en_document()` et ne change pas. La table :

```toml
[mots_des_sources]
batiment = "bâtiment"
loi = "loi"
idee = "idée"
conseiller = "conseiller"
evenement = "événement"
jauge = "jauge du pays"
```

**L'amorçage (`jeu/sim/tests/test_modificateurs.py`).** Une fonction `_amorcer_paris_cinq_poses(monkeypatch)` remplace `World.charger`, que `ServeurMonde.__init__` appelle (`sim/service.py:219`), par le chargement d'origine suivi des poses. Elle prend Paris par `_paris(monde)` et sa maison par le `maitre` du rang 0 de cette cellule (`grande-3` aujourd'hui, jamais écrit en dur). Elle pose :
1. `poser(monde, "moulin", "batiment:moulin-paris", {"cellule": paris})` ;
2. 3. 4. l'état des jauges de la maison : `etat_initial` avec `concorde = -2`, `droit = 40` et `renom = 20`, écrit dans `monde.jauges[maison]`, puis `jauges.poser_les_modificateurs(monde, regles)`. Cela donne « Concorde (-2) » (départs +10 %), « Droit (+40) » (prélèvement -2 %) et « Renom (+20) » (commerce +2 %) ;
5. une définition d'épreuve, passée en `donnees` à `poser`, comme `_avec` : nom « Épreuve de l'infobulle », grandeur `natalite`, valeur -0,05, portée `lieu`, 90 jours, source `evenement:epreuve-de-l-infobulle`, posée sur `[paris, 0]`. C'est la seule pose qui a une fin : elle montre la durée à l'écran.

Avant le 31e tick, aucun mois des jauges ne passe (`mois_ecoule` : `t % 30 == 0`, `t > 0`). Au tick 30, où la capture pousse le service, les cinq noms et valeurs sont donc ceux du tick 0.

**Le drapeau (`ForgeCapture.cs`).** `-forgeServiceModificateurs` lance le service par `-c "import pytest, sim.tests.test_modificateurs as t; t._amorcer_paris_cinq_poses(pytest.MonkeyPatch()); import runpy; runpy.run_module('sim.service', run_name='__main__')"`, suivi des mêmes `--seed`, `--port` et `--jours-par-seconde 0`. Avec `-forgeServiceProgramme` ou `-forgeServiceEpreuve`, il est refusé : `CODE_REFUS`, avec une raison qui nomme les deux drapeaux. Le commentaire d'en-tête le dit.

**L'infobulle (`InfobulleDeTerre.cs`, `CabinetDeCarte.cs`).**
- Une **seconde lecture**, `LectureModificateurs` (un `LectureDossier` à part, sur `/modificateurs`), initialisée par `CabinetDeCarte` sur le même port. Elle est relue à la même période que `/lieu`. La lecture `Lecture` ne demande que `/lieu?cell=…` : les chemins que comptent les tests existants ne changent pas.
- Une fonction pure `DecrireModificateurs(DocumentDuMonde modificateurs, long cellule)` rend les lignes du bourg (rang 0) de la terre survolée, lues dans `lieux`, puis `grandeurs` dans l'ordre servi, puis `lignes` dans l'ordre servi :
  - une ligne par pose : `<nom de la grandeur> : <valeur> <nom de la pose> · <source_dite> · <durée>` ;
  - après les lignes d'une grandeur : `<nom de la grandeur>, total : <total>` ;
  - valeur et total en `TexteDuMonde.Pourcentage(fraction)` (nouveau) : fois 100, deux décimales au plus, virgule, « + » devant un positif, « - » devant un négatif, rien devant zéro, puis « % » après une espace (« +10 % », « -2 % », « +1,96 % ») ;
  - durée : `null` donne « tant que sa source tient », un nombre N donne `"encore " + TexteDuMonde.Jours(N)`.
- `TexteAffiche` vaut les trois lignes de `Decrire`, suivies de ces lignes, **seulement** si le document des modificateurs a le **même tick** que le dossier montré et que `lieux` porte le bourg survolé. Sinon, il ne change pas d'un caractère : pas de pose, lecture en attente, autre tick, ou lecture en échec. Le dossier, lui, déclare déjà un service absent.
- Le feuillet reste celui du socle (`Infobulle.Montrer`, `LARGEUR_MAX`) : ni couleur ni police hors du socle.

## Conditions de succès
**SC1 — le document dit les mots et le reste.** `cd jeu && python3 -m pytest sim/tests/test_modificateurs.py -q` passe, avec ces cas neufs :
- le moulin posé à Paris est servi par `ServeurMonde._construire_etat` avec, pour le rang 0, `grandeurs.recolte.nom == "Récolte"`, `source_dite == "bâtiment"` et `reste_jours is None` ;
- une pose de 90 jours a `reste_jours == 90` au tick de sa pose et `89` un tick plus tard. Contre-épreuve : un reste calculé depuis `debut` donne 90 au second tick, et le cas échoue ;
- un `[mots_des_sources]` sans `jauge` est refusé avec une raison qui nomme « jauge » ;
- la photographie et le service portent le même document (cas existant, inchangé).

**SC2 — l'amorçage sert Paris et ses cinq poses.** Même commande. Un cas neuf lance `ServeurMonde` sous `_amorcer_paris_cinq_poses`, pousse 30 ticks et lit `/modificateurs` : le bourg de Paris porte exactement ces cinq lignes, dans l'ordre du registre, avec leurs valeurs : `commerce` Renom (+20), `departs` Concorde (-2), `natalite` Épreuve de l'infobulle, `prelevement` Droit (+40), `recolte` Moulin. Le tick vaut 30. Contre-épreuve dans le même cas : sans amorçage, `lieux` ne porte pas Paris au tick 30. Ce cas protège aussi le drapeau de la capture.

**SC3 — l'infobulle lit les lignes servies, et rien de plus sans pose.** Tests EditMode, ajoutés à `CabinetDeCarteTests.cs` (lancés par la CI Unity du PC, `-runTests -testPlatform EditMode`). Les documents sont faits à la main, sur le modèle de `DocTerre` ; `LectureModificateurs` est remplacée comme `Lecture` :
- une terre sans entrée dans `lieux` : `TexteAffiche` est égal, au caractère près, à `Decrire(...)` d'aujourd'hui ;
- une terre à trois poses sur deux grandeurs : `TexteAffiche` vaut les trois lignes du dossier, puis exactement les lignes et totaux attendus, écrits en clair dans le test (« Récolte : +10 % Moulin · bâtiment · tant que sa source tient », « Récolte, total : +10 % », « Natalité : -5 % Épreuve de l'infobulle · événement · encore 90 jours »…) ;
- contre-épreuve : le même document des modificateurs à un tick différent de celui du dossier ne montre rien de plus ;
- la lecture `Lecture` n'a demandé que des `/lieu?cell=…`, et `LectureModificateurs` que `/modificateurs` ;
- `TexteDuMonde.Interdit(TexteAffiche, sources des poses, identifiants des maisons)` est nul : aucun « batiment:… » ni « grande-3 » à l'écran.

`TexteDuMondeTests.cs` reçoit les cas de `Pourcentage` : 0,1 donne « +10 % », -0,02 donne « -2 % », 0,0196 donne « +1,96 % », 0 donne « 0 % », NaN est refusé.

Les tests existants de l'infobulle ne sont pas touchés et restent verts : `LInfobulleDUneTerreDitLesLignesDeSaFiche`, `LInfobulleDeLaTerreLaisseLaPhraseDUnBouton`, et les épreuves `Lot880` et `Lot944`. `Lot944` exige trois lignes exactement sur la Morée. Mesuré le 8 novembre 2026, graine 0 : la Morée choisie au tick 30 ne porte aucune pose aux ticks 31 et 32 (les neuf Concorde (-1) du premier mois sont sur de petits seigneurs). Elle ne grandit donc pas.

**SC4 — à l'écran, au même tick, les lignes sont celles de `/modificateurs`.** Le scénario `Lot1031.cs`, « 1-paris-survole », joué par la première commande de « Photo », sort 0. Ses étapes :
1. Il ouvre la carte comme `Lot880` (`Lot549.Ouvrir`), en survol et infobulle automatiques. Il lit lui-même `/modificateurs` par un client à part. Il y prend la cellule du moulin (la pose de source `batiment:moulin-paris`) et vérifie par `/lieu?cell=` que son bourg s'appelle « Paris ».
2. Il centre la caméra sur Paris, en 1920 × 1080, et survole son bourg.
3. Il attend que trois ticks soient égaux : celui du dossier de l'infobulle, celui de son document des modificateurs, et celui de sa propre lecture.
4. Il exige :
   - les trois premières lignes égales à celles du dossier (invariant de `Lot880`) ;
   - autant de lignes de pose que de lignes servies pour le rang 0, cinq, dans l'ordre servi. Chacune contient son `nom`, sa valeur en `Pourcentage` et sa `source_dite`. Le total de chaque grandeur suit ses lignes ;
   - « Moulin » et « Concorde (-2) » présents ;
   - `TexteDuMonde.Interdit` nul ;
   - le texte du `Text` du feuillet égal à `TexteAffiche` ;
   - le feuillet entier dans l'image, sans recouvrir le point survolé (`Feuillet` de `Lot880`).
5. Il écrit `rapport-1031.json` dans `Capture.DossierDesCaptures` : tick, lignes servies, lignes montrées, cadre du feuillet. Il journalise `CAPTURE_1031`.

Contre-épreuves, chacune sort 1, sans image :
- `-forge1031Decale` : une fois l'infobulle alignée, le scénario pousse `POST /tick?n=1` et compare ce qu'elle montre à sa nouvelle lecture. Les ticks diffèrent : échec, avec les deux ticks dans la raison ;
- `-forge1031SansLigne` : le scénario retire du `Text` du feuillet la dernière ligne de pose avant de juger. Le compte ne tient plus : échec, avec la ligne manquante.

**SC5 — entière à 1280 × 720 avec cinq poses.** Le scénario « 2-paris-1280x720 », dans la même commande, sort 0. Il passe la caméra en 1280 × 720 (`targetTexture`, `ResetAspect`, la toile en `ScreenSpaceCamera` comme `Lot880`). Il garde Paris survolé et appelle `Pas(point, Paris)` en cinq points : le bourg à l'écran, et les quatre coins de l'image à 30 px des bords. En chacun :
- le feuillet porte les cinq lignes de pose et leurs totaux ;
- il est entier dans l'image ;
- la hauteur préférée de son texte ne dépasse pas sa hauteur.

`Infobulle.Placer` qui lève une exception est un échec. Contre-épreuve : `-forge1031SansLigne` rougit aussi ce scénario, car il juge le même compte.

## Hors périmètre
- Le détail des autres lieux d'une cellule (rangs 1 et plus) : l'infobulle d'une terre lit son bourg. Les poses de pays et de cellule le touchent comme les autres lieux, et aucune définition des données ne se pose aujourd'hui sur un lieu seul.
- Un `/modificateurs?cell=` filtré : le document entier se relit toutes les deux secondes. Un lot le filtrera s'il est mesuré lent.
- La barre et ses jauges (#1032), le panneau du pays (#1033), bâtir depuis la carte (#1034), la langue du cabinet (#849, #850).
- Toute règle du monde : poses, ordre, totaux, jauges et bâtiments restent ceux de #1025, #1039 et #1040. L'amorçage ne sert qu'à la capture.
- Le drapeau `-forgeServiceProgramme` : son amorçage appelle `sim.tests.test_monde._brancher_programme`, qui n'existe plus. Ce lot ne le répare pas et ne s'en sert pas.
- Le juge `TexteDuMonde.SansUnite` sur ces lignes : un niveau de jauge (« Concorde (-2) », « Droit (+40) ») n'a pas d'unité. Seul `Interdit` s'applique.

## Photo
Paris survolé sur la carte, en 1920 × 1080, au jour 31 de 1400 (tick 30), service arrêté. Près du curseur, le feuillet du socle porte, de haut en bas :
- les trois lignes du dossier : « Paris · Maison : … », la date, les habitants ;
- dans l'ordre du registre, chaque ligne suivie du total de sa grandeur :
  - « Commerce : +2 % Renom (+20) · jauge du pays · tant que sa source tient » ;
  - « Départs : +10 % Concorde (-2) · jauge du pays · tant que sa source tient » ;
  - « Natalité : -5 % Épreuve de l'infobulle · événement · encore 60 jours » (reste au tick 30 de la pose de 90 jours) ;
  - « Prélèvement : -2 % Droit (+40) · jauge du pays · tant que sa source tient » ;
  - « Récolte : +10 % Moulin · bâtiment · tant que sa source tient ».

Le moulin et la Concorde de Paris sont lisibles, et rien n'est coupé. Le scénario `Lot1031.cs` (Périmètre) pose la carte, centre la caméra sur Paris et survole son bourg. La chaîne écrit l'image à la fin de « 1-paris-survole », puis celle de « 2-paris-1280x720 ».

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1031 -forgeServiceModificateurs -forgeCaptures 3d/unity/Temp/lot1031-photo -logFile 3d/unity/Temp/lot1031-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1031 -forgeServiceModificateurs -forge1031Decale -forgeCaptures 3d/unity/Temp/lot1031-decale -logFile 3d/unity/Temp/lot1031-decale.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1031 -forgeServiceModificateurs -forge1031SansLigne -forgeCaptures 3d/unity/Temp/lot1031-sans-ligne -logFile 3d/unity/Temp/lot1031-sans-ligne.log
```

La première sort 0 avec `*1-paris-survole*.png` et `*2-paris-1280x720*.png`, et `rapport-1031.json` : c'est la photo. Les deux autres sont les contre-épreuves, chacune sort 1 :
- `DECALE` (SC4) : l'infobulle et `/modificateurs` ne sont plus au même tick ;
- `SANS-LIGNE` (SC4, SC5) : une ligne de pose manque au feuillet.

Le codeur ouvre les deux images lui-même. Les PNG restent hors du dépôt.
