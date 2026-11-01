# Lot #929 — La fiche de survol parle en noms à l'écran
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
La fiche qui s'ouvre au survol d'une terre, sur la carte, l'écrit par le nom servi de son bourg, ses habitants à la date du monde, sa faim en jours et sa dette en masse, et se réécrit seule quand le nom arrive.

## Le joueur
Le joueur survole la Lorraine et lit « Metz », puis « Puissance : Archevêché de Trèves », ses habitants au jour du monde (« 62 457 habitants · jour 31 de 1400 »), sa faim en jours (« 0 jour de manque ») et sa dette en kilos ou en tonnes. Il ne lit plus « Cellule 10437 », ni « au tick 30 », ni « 12.5 kg ». Il reconnaît une terre par son nom avant d'y descendre, comme dans un registre. Le nom peut arriver une fraction de seconde après le survol : la fiche dit d'abord « Bourg en lecture », puis se corrige sans qu'il bouge la souris. C'est le geste « La fiche parle en noms, pas en identifiants » du jalon 4 (`CAP.md`, lot 18 ; #856 → #872 → #884 → #912). Sous-lot 2 de #912, après #928, qui a appris au juge de la carte à lire cette fiche.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni `MODELE.md`, ni le service, ni `pc/epreuve_carte.py` ne sont touchés. La fiche recopie ce qui est servi : le nom du rang 0 de `/lieu?cell=C` (par `NomsDesTerres`), et la date, les habitants, la faim et la dette de `/monde`. La sentinelle −1 reste « non calculée ».

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/FicheDeCellule.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/FicheDeCelluleTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/EpreuveCarte.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot526.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot929.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot929.cs.meta
docs/briefs/929-la-fiche-de-survol-parle-en-noms-a-l-ecran.md

Tout autre chemin est interdit, en particulier `NomsDesTerres.cs`, `TexteDuMonde.cs`, `CabinetDeCarte.cs`, `pc/epreuve_carte.py` et `jeu/ville/tests/test_epreuve_carte.py`.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `PONT` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot929-pont.xml -logFile 3d/unity/Temp/lot929-pont.log`, sans `-quit`. `INTERFACE` = la même commande avec `Forge.Interface.Tests` et `lot929-interface`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté ; zéro cas est un échec. Les tests réécrits et le cas neuf s'écrivent d'abord, et on les voit rouges contre la fiche d'aujourd'hui. `NBSP` = U+00A0. `METZ` = 10437.

**Ce que gagne `FicheDeCellule`.**
- Un champ `NomsDesTerres noms`, créé dans `Demarrer` par `NomsDesTerres.Local(port)`, après `Construire` et le `ClientMonde`. `Arreter` le remet à `null`.
- Un champ `double dernierPas`. `Pas(maintenant)` y range `maintenant` dès qu'il passe la garde `client == null`.
- `public string NomDuBourg { get; private set; }` : le nom passé à la dernière écriture.
- `Afficher`, si une terre est survolée, calcule `NomDuBourg = noms.Bourg(id, dernierPas) ?? noms.Raison(id, 0)`, puis écrit `Decrire(Survolee, VersMonde(monde), NomDuBourg)`. Avant l'arrivée du nom, `Raison` rend `NomsDesTerres.NomEnLecture`, donc « Bourg en lecture ». Après un échec, `Raison` rend la cause, que `Decrire` tait en « déclaré absent par le monde ».
- `Pas`, après sa lecture du monde, rappelle `Afficher` si une terre est survolée et que `noms.Bourg(id, maintenant) ?? noms.Raison(id, 0)` diffère de `NomDuBourg`. C'est ce qui réécrit la fiche quand le nom arrive.
- `Decrire` à deux arguments, son corps et son texte ne changent pas : `CabinetDeCarte` l'affiche. Le commentaire d'en-tête dit que la fiche écrit le nom du bourg et la date, et plus le tick.

**SC1 — Le faux service sert `/lieu` (réécriture décidée en A sur #856).** `PONT`. Dans `FicheDeCelluleTests`, `Servir` gagne une branche : pour le chemin `/lieu`, il répond 200 avec `lieu-graine0-tick3.json` (lu à côté de la carte). Dans ce corps, `"cell_id":9922` est remplacé par `"cell_id":` + la valeur `cell` de la requête. Le bourg servi est donc « Övre vik », quelle que soit la terre. Un helper `Nommee(point)` survole le point, puis fait des `fiche.Pas(t)` (t += 0,5, `Thread.Sleep(10)`) jusqu'à `fiche.NomDuBourg == "Övre vik"`, avec la limite `ATTENTE_MS`. Sinon le test échoue avec le texte affiché.

**SC2 — Les trois cas du survol disent la terre en noms.** `PONT`. On garde le même service, les mêmes terres et les mêmes vérifications, dites en noms. Les seules lignes réécrites sont les cinq assertions qui citent « Cellule », « au tick », « ticks de manque », « 12.5 kg » ou `MESSAGE_ABSENCE`, et les `SurvolerPoint` remplacés par `Nommee`.
- `La_fiche_dit_la_carte_et_le_monde_servis`. Sur Metz, `fiche.TexteAffiche` vaut exactement « Övre vik · Metz\nPuissance : » + `metz.Puissance.Nom` + « \nMaison : aucune, le monde n'en nomme pas\nHabitants : 1 » + NBSP + « 234 habitants · jour 31 de 1400\nFaim : 2 jours de manque\nDette de nourriture : 12,5 kg ». `TexteDuMonde.Interdit(texte, "10437")` et `TexteDuMonde.SansUnite(texte)` sont nuls. Sur `autre`, le texte commence par « Övre vik » et contient « \nPuissance : » + puissance + « \nMaison : » + maison + « \nHabitants : 0 habitant · jour 31 de 1400\nFaim : non calculée\nDette de nourriture : non calculée ». Sur `absente`, il finit par « \nHabitants et faim : absente du monde servi » et ne contient pas l'identifiant de `absente`. `fiche.Survolee?.CellId` est vérifié comme aujourd'hui.
- `Hors_des_cellules_la_fiche_se_cache` : rien ne change dans ses assertions.
- `Sans_monde_la_fiche_le_dit_et_garde_la_carte` (statut 500 sur `/monde`). Après `Nommee`, le texte commence par « Övre vik · Metz\nPuissance : ». Sa dernière ligne vaut « Habitants et faim : déclaré absent par le monde ». `fiche.MondeLu` est nul, et le texte ne contient ni « 500 », ni « 10437 ».

Contre-épreuve : la fiche d'aujourd'hui, à deux arguments, rougit le premier et le troisième cas. Le compte rendu donne ce rouge.

**SC3 — Le nom arrive après le survol, et la fiche se réécrit seule.** `PONT`, cas neuf `Le_nom_arrive_apres_le_survol_et_la_fiche_se_recrit`. `Servir`, `Poser`, puis `fiche.SurvolerPoint` sur Metz, une seule fois. Aussitôt, `NomDuBourg` vaut `NomsDesTerres.NomEnLecture`, et la première ligne vaut « Bourg en lecture · Metz ». On fait ensuite des `fiche.Pas(t)`, sans aucun nouveau survol, jusqu'à `NomDuBourg == "Övre vik"` (limite `ATTENTE_MS`). La première ligne vaut alors « Övre vik · Metz ». Le texte entier est égal à `FicheDeCellule.Decrire(fiche.Survolee, Lecture<MondeLu>.De(fiche.MondeLu), "Övre vik")`. `Interdit(texte, "10437")` et `SansUnite(texte)` sont nuls. Contre-épreuve : un `Pas` qui ne rappelle pas `Afficher` laisse « Bourg en lecture » et rougit.

**SC4 — `Lot526` lit le bourg et juge la fiche en noms.** Dans `Lot526` :
- `FicheDeMetz` passe de `static` à `internal static`, sans changer de nom.
- On ajoute `internal static FicheDeCellule Fiche` et `internal static string Bourg`, posés par le scénario.
- Une fois le monde lu, le scénario lit `/lieu?cell=` + `cellule.CellId` par `new ClientLieu(fiche.port, TimeSpan.FromSeconds(ATTENTE_S))`, dans un `Task.Run`, qu'il attend par `Lot690.Attendre`. Une lecture absente, ou sans nom au rang 0 (`Lieu.Bourg?.Nom`), échoue en citant sa cause. Puis il attend `fiche.NomDuBourg == Bourg`, au plus `ATTENTE_S` ; sinon il échoue avec le texte affiché.
- Une méthode `internal static void Juger(FicheDeCellule fiche, string bourg)` remplace la comparaison d'aujourd'hui, et vérifie dans cet ordre :
  1. `TexteDuMonde.Interdit(texte, id)` est nul (`id` = l'identifiant de la terre survolée, en invariant), sinon `InvalidOperationException("mot interdit « " + mot + " » dans la fiche : « " + texte + " »")` ;
  2. `TexteDuMonde.SansUnite(texte)` est nul, sinon « nombre sans unité « … » dans la fiche » ;
  3. `texte == FicheDeCellule.Decrire(fiche.Survolee, Lecture<MondeLu>.De(fiche.MondeLu), bourg)` ;
  4. la première ligne commence par `bourg` ;
  5. le texte contient « \nHabitants : » + `TexteDuMonde.Nombre(population)` + « habitant » ou « habitants » + « · » + `TexteDuMonde.Date(fiche.MondeLu.Date)`.
  Le scénario l'appelle avec `Bourg` avant la photo. Aucun autre `throw` ne disparaît.

Commande :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 526 -forgeCaptures 3d/unity/Temp/lot929-526 -logFile 3d/unity/Temp/lot929-526.log
```

Elle sort 0 avec son image. La trace `CAPTURE_526` commence par « Metz | Puissance : » et ne contient ni « Cellule » ni « tick ». Contre-épreuve : le `-forge929Cabinet` de la Photo fait échouer ce même `Juger`.

**SC5 — L'épreuve de la carte attend le bourg, et sort à 0.** Dans `EpreuveCarte.Epreuve`, après `fiche.SurvolerPoint(point)`, on attend `fiche.NomDuBourg != null && fiche.NomDuBourg != NomsDesTerres.NomEnLecture`, au plus `ATTENTE_MONDE_S`, une image à la fois. Ensuite seulement, on remplit `r.fiche`. Un nom qui n'arrive pas laisse partir le rapport tel quel : le juge le refuse. Les clés du rapport, le nom de la méthode `Jouer` et les arguments ne changent pas. Le commentaire d'en-tête dit l'attente. Commandes, depuis la racine :
- `py -m pytest jeu/ville/tests/test_epreuve_carte.py -q` passe, sans que le fichier soit touché ;
- `py pc\epreuve_carte.py --sortie 3d/unity/Temp/lot929-epreuve` sort 0. La cellule par défaut est 9008, bourg servi « Aïn al-Tawil » à la graine 0 ;
- `py pc\epreuve_carte.py --sortie 3d/unity/Temp/lot929-metz --cellule 10437` sort 0. `verdict.txt` contient `bourg : fiche 'Metz' · service 'Metz' · égal` et une ligne `date : fiche 'jour 31 de 1400' · service 'jour 31 de 1400' · égal` ;
- contre-épreuve : `py pc\epreuve_carte.py --sortie 3d/unity/Temp/lot929-decalage --cellule 10437 --decalage 1` sort 1, avec une ligne `date : … · ÉCART`.
Le compte rendu joint les trois `verdict.txt`.

**SC6 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `PONT` et `INTERFACE` passent sur toute leur assemblée. `CabinetDeCarteTests` et `ReperesDeDepartTests` y sont compris : ils montent une `FicheDeCellule`.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/FicheDeCelluleTests.cs` ne retire aucune ligne entre `// Lot #910` et la fin du fichier. Le nombre d'`Assert.`, `StringAssert.` et `LogAssert.` du fichier ne baisse pas.
- `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/FicheDeCellule.cs` ne touche pas les lignes de `Decrire` à deux arguments.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 300 lignes, fichiers neufs et brief compris.

Contre-épreuve : un cas retiré, une ligne du cabinet changée, ou un fichier hors du Périmètre refuse la livraison.

## Hors périmètre
- Le juge Python (`pc/epreuve_carte.py`, ses tests) : fait en #928.
- `Decrire` à deux arguments, le territoire du cabinet (`CabinetDeCarte`) et `DossierTerritoire` : d'autres sous-lots de #856.
- `NomsDesTerres`, `ClientLieu`, `TexteDuMonde`, le service, `jeu/sim/`.
- Changer la place, la taille ou le fond de la fiche à l'écran.
- Les autres scénarios de capture qui montent la carte (`Lot613`, `Lot614`, `Lot624`, `Lot729`, `Lot855`, `Lot880`) : aucun ne lit le texte de la fiche.

## Photo
La Lorraine de près, comme au lot 526. En bas à gauche, la fiche de la terre de Metz commence par « Metz » (sans « Cellule », sans « · Metz » répété). Puis viennent « Puissance : Archevêché de Trèves », « Maison : aucune, le monde n'en nomme pas », « Habitants : … habitants · jour N de 1400 », « Faim : … de manque » ou « non calculée », et « Dette de nourriture : … kg » ou « … t ». Aucun « tick », aucun identifiant à l'écran.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot929.cs` (et son `.meta`), avec un scénario `[ScenarioDeCapture(929, "fiche-de-metz")]` :
1. jouer `Lot526.FicheDeMetz(camera)` (`for (var e = …; e.MoveNext();) yield return null;`) ;
2. avec `-forge929Cabinet` sur la ligne de commande (`Environment.GetCommandLineArgs()`), prendre le `Text` sous `Lot526.Fiche` (`GetComponentsInChildren<Text>(true)`) dont le texte vaut `Lot526.Fiche.TexteAffiche` ; sinon échouer. Y écrire, dans la même image, le texte du cabinet : `FicheDeCellule.Decrire(Lot526.Fiche.Survolee, Lecture<MondeLu>.De(Lot526.Fiche.MondeLu))` ;
3. juste avant la fin, sans attendre d'image, `Lot526.Juger(Lot526.Fiche, Lot526.Bourg)`, et exiger `Lot526.Bourg == "Metz"`. `Capture.Photographier` photographie après la fin de l'énumérateur : la fiche jugée est celle de la photo ;
4. la trace `CAPTURE_929 <texte de la fiche, « \n » remplacé par « | »>`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 929 -forgeCaptures 3d/unity/Temp/lot929-photo -logFile 3d/unity/Temp/lot929-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 929 -forgeCaptures 3d/unity/Temp/lot929-cabinet -forge929Cabinet -logFile 3d/unity/Temp/lot929-cabinet.log
```

La première sort 0 avec `*--fiche-de-metz.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image, et son journal dit « mot interdit « Cellule » dans la fiche ». Le codeur ouvre l'image lui-même. Une fiche coupée, absente, qui dit « Bourg en lecture », « Cellule » ou « tick », refuse la livraison même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre l'image.
