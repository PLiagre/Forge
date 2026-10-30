# Lot #891 — Le plan, les chantiers, la rue, les calques et le menu en noms
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Le plan du bourg, ses chantiers, l'outil de rue, la légende du calque Habitants et le menu du cabinet nomment le bourg, datent au jour servi et pèsent le grain, sans « Territoire N » ni tick.

## Le joueur
Le joueur garde la Morée et ouvre « Plan du bourg ». Le plan s'intitule « Mistra · jour 32 de 1400 · Nord en haut · Consultation du plan », et non plus « Territoire 10340 · tick 31 ». Les chantiers s'ouvrent sur « Mistra · jour 32 de 1400 » et disent « Ce jour : 3 ouvriers · 1,23 t de grain payés ». Quand il confirme une rue, le reçu dit « Rue reçue pour Mistra, appliquée au jour suivant ». Le calque Habitants dit « Habitants : 12 habitants (clair) → 5 631 habitants (foncé) · … · jour 31 de 1400 ». Le menu dit qu'un ordre attend « le prochain jour du monde ». Un nom que le monde ne sert pas se dit absent : rien n'est inventé. Il lit son bourg et ce que coûtent ses chantiers comme un registre, sans traduire un numéro. C'est le sous-lot 1 de #876, sous-lot 7 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4). Il sert l'écran du jalon (« ses chantiers et ce qu'ils coûtent ») et sa décision : chaque journée se paie en grain pris au grenier.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. `/plan` sert déjà `date` (`jeu/sim/service.py`, ligne 381), `/monde` aussi (`MondeLu.Date`), et `Forge.Pont.NomsDesTerres` (#871) lit le nom du bourg sur `/lieu`.

## Périmètre
3d/unity/Assets/Interface/DossierBourg.cs
3d/unity/Assets/Interface/DossierChantiers.cs
3d/unity/Assets/Interface/OutilRue.cs
3d/unity/Assets/Interface/CalquesCarte.cs
3d/unity/Assets/Interface/MenuCabinet.cs
3d/unity/Assets/Interface/Tests/DossierChantiersTests.cs
3d/unity/Assets/Interface/Tests/OrdreRueTests.cs
3d/unity/Assets/Interface/Tests/CalquesCarteTests.cs
3d/unity/Assets/Interface/Tests/MenuCabinetTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot891.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot891.cs.meta
docs/briefs/891-le-plan-les-chantiers-la-rue-les-calques-et-le-m.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot891-interface.xml -logFile 3d/unity/Temp/lot891-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté. Les tests s'écrivent d'abord, et on les voit rouges. `TexteDuMonde`, `NomsDesTerres`, `CabinetDeCarte` et `DossierVoisins` ne changent pas.

**Le plan et les chantiers (`c` = `cell_id` en texte invariant).**
- `DossierBourg.Entete(string bourg, DocumentDuMonde doc)`, public et statique : `bourg + " · " + TexteDuMonde.Date(new DateDuMonde(Annee, JourDeLAnnee))` ; `doc.Annee` nulle : `ArgumentException("Date non transmise")`.
- `DossierBourg.NomDuBourg(NomsDesTerres noms, long cell, double maintenant)`, public et statique : `noms.Bourg(…)`, sinon « Bourg sans nom (» + `TexteDuMonde.Absence(noms.Raison(cell, 0), c)` + «) ». `Initialiser` crée `NomsDesTerres.Local(port)` ; l'instance expose `public string Bourg(long cellule)` (avec `Time.realtimeSinceStartupAsDouble`) et `public Text Etat => etat`.
- Titre du plan : `Entete(Bourg(cellule), affiche) + " · Nord en haut · Consultation du plan"`, réécrit à chaque image tant qu'un plan est affiché (le nom lu après le plan le remplace) ; le dessin ne change qu'avec un nouveau document. En lecture : « Lecture du plan du bourg… ». Le `catch` : « Plan indisponible : » + `Absence(e.Message, c)`. La légende du plan ne change pas.
- `DossierChantiers.Initialiser` reçoit en dernier un `Func<long, string> bourg` (`DossierBourg` passe `Bourg`). `Decrire(DocumentDuMonde document, long cellule, string bourg)` : la première ligne est `DossierBourg.Entete(bourg, document)` ; le contrôle de `cell_id` reste avant elle. Le grain du jour s'écrit `TexteDuMonde.Masse(grain) + " de grain payés"`. En lecture : « Lecture des chantiers du bourg… ». Le `catch` : « Chantiers indisponibles : » + `Absence(e.Message, c)`. Le reste du texte ne change pas.

**La rue (`OutilRue`).** Deux fonctions publiques et statiques, que `Preparer` et `LateUpdate` appellent avec `dossier.Bourg(cible)` :
- `Resume(string bourg, int points, string largeur, string foyers)` = « Pointillés : tracé préparé · » + bourg + « · » + points + « points · largeur » + largeur + « m · Foyers : » + foyers + « . Coût calculé par le monde. » (sans espace avant le point final, comme aujourd'hui).
- `Message(RecuIntention recu, string bourg, long cellule)` : absent, « Reçu inconnu : » + `Absence(recu.Absence, c)` + « . Vérifiez le plan avant toute nouvelle demande. » ; accepté, « Rue reçue pour » + bourg + « , appliquée au jour suivant. Relisez le plan ; ce reçu ne signifie pas chantier terminé. » ; refusé, « Rue refusée : » + `Absence(recu.Erreur, c)`. Le `catch` de `Preparer` garde `Absence(e.Message, c)`.

**Le calque et le menu.**
- `RepartitionHabitants.Legende` = « Habitants : » + H(Minimum) + « (clair) → » + H(Maximum) + « (foncé) · échelle logarithmique · » + `TexteDuMonde.Date(monde.Date)`, où H(n) = `TexteDuMonde.Nombre(n)` + « habitant » pour 0 ou 1, « habitants » sinon. Une date hors bornes lève (l'`ArgumentOutOfRangeException` de `Date`).
- `CalquesCarte.Indisponible(string raison)`, public et statique : « Calque indisponible : » + `TexteDuMonde.Absence(raison)` + « . Couleurs des puissances conservées. » ; le `catch` l'appelle. `public Text Legende => legende`.
- `MenuCabinet` : « Un ordre reçu attend le prochain tick du monde. » devient « Un ordre reçu attend le prochain jour du monde. ».

**SC1 — Les cas existants suivent la décision A de #856.** `DossierChantiersTests` : `Json` gagne `"date":{"annee":1400,"jour_de_l_annee":69}` ; `Lire` passe le bourg « Bar-le-Duc ». Ligne 226 : « Territoire 10430 · tick 68 » devient `StringAssert.StartsWith("Bar-le-Duc · jour 69 de 1400\n", …)`. `CalquesCarteTests` : ligne 291, « tick 8 » devient « jour 9 de 1400 » ; ligne 292, « 90 » devient « 90 habitants (foncé) ». Les autres assertions et les noms des cas ne changent pas. `git diff origin/master` sur ces deux fichiers ne retire que ces lignes et l'aide `Lire`. Contre-épreuve : une assertion retirée sans remplaçante refuse la livraison.

**SC2 — Les chantiers nomment, datent et pèsent.** `INTERFACE`, cas neuf `Les_chantiers_nomment_le_bourg_datent_et_pesent_le_grain` dans `DossierChantiersTests` :
- un relevé du jour de la rue 2 à 3 bras et 1 234,5 kg donne « Ce jour : 3 ouvriers · 1,23 t de grain payés » ; à 12,5 kg, « 12,5 kg de grain payés » ;
- le texte ne contient ni « Territoire » ni « 1234 » ; `Interdit(texte, "10430")` est nul ;
- `Json` sans sa clé `date` lève une `ArgumentException` dont le message contient « Date » ; `DossierBourg.Entete("Bar-le-Duc", doc)` vaut « Bar-le-Duc · jour 69 de 1400 » ;
- un `NomsDesTerres` dont `lire` rend `LectureLieu.Absent("lieu 10430 : service coupé")` : `NomDuBourg(noms, 10430, 0)` vaut « Bourg sans nom (nom en cours de lecture) », puis, après `SpinWait` jusqu'à `!LectureEnVol`, « Bourg sans nom (déclaré absent par le monde) », avec son `LogAssert.Expect`.

Contre-épreuve : « tick 68 », « 1234,5 kg » ou une raison passée telle quelle rougit.

**SC3 — Le reçu et le résumé de la rue nomment le bourg.** `INTERFACE`, cas neuf `Le_recu_et_le_resume_de_la_rue_nomment_le_bourg_sans_tick` dans `OrdreRueTests` :
- `Resume("Mistra", 3, "6", "1")` vaut « Pointillés : tracé préparé · Mistra · 3 points · largeur 6 m · Foyers : 1. Coût calculé par le monde. » ;
- `Message(RecuIntention.AccepteeAu(68), "Mistra", 10430)` vaut « Rue reçue pour Mistra, appliquée au jour suivant. Relisez le plan ; ce reçu ne signifie pas chantier terminé. » ;
- `Refusee(409, "cellule 10430 hors de vos terres")` donne « Rue refusée : déclaré absent par le monde » (avec `LogAssert.Expect`) ; `Refusee(400, "tracé trop court")` donne « Rue refusée : tracé trop court » ; `Absente("Connexion refusée")` donne « Reçu inconnu : Connexion refusée. Vérifiez le plan avant toute nouvelle demande. » ;
- `Interdit(…, "10430")` est nul sur chacun.

Contre-épreuve : « au tick 68 » ou « Territoire 10430 » rougit.

**SC4 — La légende des habitants dit la date et des habitants.** `INTERFACE`, cas neuf `La_legende_des_habitants_dit_la_date_et_compte_en_habitants` dans `CalquesCarteTests` :
- cellules (10, 1) et (20, 5 631), date (1400, 9) : `Legende` vaut « Habitants : 1 habitant (clair) → 5 631 habitants (foncé) · échelle logarithmique · jour 9 de 1400 », le séparateur étant U+00A0 (`TexteDuMonde.Nombre(5631)`) ; `Interdit` et `SansUnite` sont nuls ;
- la date (1400, 0) : `Assert.Catch<ArgumentException>` ;
- `Indisponible("Population absente du territoire 30")` vaut « Calque indisponible : déclaré absent par le monde. Couleurs des puissances conservées. » (avec `LogAssert.Expect`) ; `Indisponible("Population des territoires incomplète")` garde sa raison.

Contre-épreuve : « tick 8 », « 5631 » sans séparateur ou « 1 habitants » rougit.

**SC5 — Le menu dit le prochain jour.** `INTERFACE`, cas neuf `Le_menu_dit_le_prochain_jour_du_monde_sans_tick` dans `MenuCabinetTests`, en `[Test]` comme le cas du volume : après `Initialiser`, le texte joint de tous les `Text` du panneau (`GetComponentsInChildren<Text>(true)`) contient « Un ordre reçu attend le prochain jour du monde. » et `Interdit` y est nul. Contre-épreuve : l'ancienne phrase rougit.

**SC6 — Rien d'autre ne bouge.** `INTERFACE` passe sur toute l'assemblée. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

## Hors périmètre
- « Les autres maisons » (`DossierVoisins`) et le service lancé avec `--ia` : sous-lot 2 de #876.
- La légende du calque Puissances, le texte d'aide du guide, la légende du plan (« Largeur du cadre … m »).
- « Rue 2 », « 25 / 181 journées de travail » et « Foyers : 1 » : ils restent tels quels.
- `TexteDuMonde`, `NomsDesTerres`, `CabinetDeCarte`, les positions des panneaux, le service et `jeu/`.

## Photo
La photo montre la carte de 1400 sous le calque Habitants, la Morée gardée en rouge à droite, le plan de Mistra ouvert à gauche avec son titre « Mistra · jour N de 1400 · Nord en haut · Consultation du plan », et sous lui le guide « Parcourir le monde » dont la légende dit « Habitants : … habitants (foncé) · échelle logarithmique · jour N de 1400 · Rouge : territoire conservé ». Aucun tick, aucun numéro de terre.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot891.cs`, un scénario `[ScenarioDeCapture(891, "plan-et-habitants")]`, sur le modèle de `Lot873` (qu'il ne modifie pas). Chaque attente est bornée par `Lot690.Jusqua` ou `Lot690.Attendre`. Chaque absence échoue en nommant sa cause.
1. `Lot549.Ouvrir`, puis attendre `Lot690.LecturePrete(cabinet.Partie)`. Prendre la fiche de départ au siège « Mistra », lire son bourg par `ClientLieu` (comme `Lot873.Bourg`, copié) et exiger son nom servi.
2. Zoomer, centrer la vue pour que le point du bourg tombe en viewport x ∈ [0,68 ; 0,98], y ∈ [0,40 ; 0,95] (à droite, au-dessus de « Territoire conservé »), exiger `CelluleSous(point)` = la Morée, puis `cabinet.Garder`.
3. Cliquer `toile/Territoire conservé/Plan du bourg`, puis `toile/Parcourir le monde/Habitants` (`onClick.Invoke`).
4. Attendre que `DossierBourg.Etat.text` vaille `DossierBourg.Entete(nom, Document) + " · Nord en haut · Consultation du plan"` et que `CalquesCarte.Legende.text` vaille `new RepartitionHabitants(Partie.Monde.Donnees.Monde).Legende + " · Rouge : territoire conservé"`.
5. `Exiger` (dans une même image, sans `yield`) : avec `-forge891Tick`, ajouter d'abord « · tick » + `Document.Tick` au titre. Puis, sur le titre et la légende, `Interdit(texte, cellule) ?? SansUnite(texte)` nul, sinon `Echec("mot interdit « " + mot + " » : « " + texte + " »")` ; puis les deux égalités de l'étape 4.
6. `Lot549.Photographier`, la toile en `ScreenSpaceCamera` comme `Lot873`. `Visible` exige entiers dans le champ le panneau « Plan du bourg » et le guide « Parcourir le monde », et le bourg dans la zone de l'étape 2. `Exiger` et `Visible` avant et après dix images.
7. La trace `CAPTURE_891` donne la cellule, le titre et la légende.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 891 -forgeCaptures 3d/unity/Temp/lot891-photo -logFile 3d/unity/Temp/lot891-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 891 -forgeCaptures 3d/unity/Temp/lot891-tick -forge891Tick -logFile 3d/unity/Temp/lot891-tick.log
```
La première sort 0, avec une image `*--plan-et-habitants.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image, avec « mot interdit » dans son journal. Le codeur ouvre l'image lui-même. Un « tick », un « Territoire 10… », un nombre sans unité, un plan ou une légende coupés ou cachés, une Morée hors champ refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre l'image.
