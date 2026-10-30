# Lot #910 — La fiche sait écrire une terre en noms
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
`FicheDeCellule` sait écrire une terre survolée par le nom de son bourg, la date servie, les habitants, la faim en jours et la dette en masse, sans identifiant ni tick.

## Le joueur
Rien ne change encore à l'écran. Lot de fond, sous-lot 1 de #884, lui-même découpé du sous-lot 2 de #872 et de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, lot 18). Le geste qu'il prépare : le joueur survole une terre, lit son nom, ses habitants, « 2 jours de manque » et sa dette, et reconnaît sa capitale avant d'y descendre, sans traduire « Cellule 10437 » ni « tick 30 ». Il sent un registre, pas un relevé de machine. Le sous-lot 3 de #884 branchera cette écriture à l'écran et la fera juger. Ici, la fiche affichée, le cabinet et l'épreuve de la carte restent ceux d'aujourd'hui.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. L'écriture lit des valeurs déjà servies : le nom du bourg (`NomsDesTerres`, `/lieu`, rang 0), les habitants, la faim, la dette et la date (`/monde`). La date affichée est `MondeLu.Date`, jamais un compte dérivé du tick. La sentinelle −1 de la faim et de la dette reste « non calculée » (`MODELE.md`, « Le déficit alimentaire et la mortalité » : −1 = non calculé, 0 est une mesure). `TexteDuMonde.Jours` refuse une durée négative : la sentinelle ne passe pas par lui.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/FicheDeCellule.cs
3d/unity/Assets/ForgeLocal3D/Pont/NomsDesTerres.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/FicheDeCelluleTests.cs
docs/briefs/910-la-fiche-sait-ecrire-une-terre-en-noms.md

Tout autre chemin est interdit. Aucun fichier neuf : pas de `.meta`. Les cas s'ajoutent dans `FicheDeCelluleTests` ; aucune ligne des trois tests déjà là n'est retirée ni réécrite.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `PONT` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot910-pont.xml -logFile 3d/unity/Temp/lot910-pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté. Zéro cas est un échec. Les cas neufs s'écrivent d'abord, et on les voit rouges (surcharge absente). `TexteDuMonde` ne change pas.

**Ce que gagne le code.**

`NomsDesTerres` expose `public const string NomEnLecture = "nom en cours de lecture";`. `Raison` rend cette constante à la place du littéral. La valeur reste celle que `DossierMaisonTests` et `DossierChantiersTests` comparent déjà : ces fichiers ne sont pas ouverts.

`FicheDeCellule` gagne `public static string Decrire(CelluleDeCarte c, Lecture<MondeLu> monde, string nomDuBourg)`. La méthode à deux arguments, son corps, et l'appel `Decrire(Survolee, VersMonde(monde))` dans `Afficher` ne bougent pas. La surcharge ne lit rien : elle reçoit le nom déjà lu.

L'en-tête, première ligne :
- `nomDuBourg == null` ou `nomDuBourg == NomsDesTerres.NomEnLecture` : le titre est « Bourg en lecture » ;
- sinon le titre est `TexteDuMonde.Absence(nomDuBourg, c.CellId.ToString(CultureInfo.InvariantCulture))`. Un nom propre (« Metz », « Övre vik ») ressort tel quel. Une raison sale devient « déclaré absent par le monde », et `Absence` écrit son journal.
- Puis les villes de `c.Villes`, dans l'ordre, dont le nom n'est pas le nom du bourg retenu. On n'omet une ville que si `titre == nomDuBourg` et `ville.Nom == nomDuBourg` : la ville qui porte le nom du bourg n'est pas répétée. Les autres restent, jointes par « , », précédées de « · » s'il y en a une. Aucune ville : pas de « · ».

Sous l'en-tête, les deux lignes de la méthode à deux arguments, aux mêmes mots : « Puissance : » et le nom, ou « aucune, le monde n'en nomme pas » ; « Maison : » de même.

Puis, si le monde est là et que la cellule y est :
- « Habitants : » + `TexteDuMonde.Nombre(population)` + « habitant » si la population est 0 ou 1, « habitants » sinon, + « · » + `TexteDuMonde.Date(monde.Donnees.Date)`. Le nombre passe par `Nombre` : ses milliers sont séparés par U+00A0.
- « Faim : » + `TexteDuMonde.Jours(hunger)` + « de manque » si `HungerTicks >= 0`. Donc 2 donne « Faim : 2 jours de manque », 0 donne « Faim : 0 jour de manque ». Si `HungerTicks < 0` : « Faim : non calculée ».
- « Dette de nourriture : » + `TexteDuMonde.Masse(kg)` si `FoodDeficitKg >= 0`. Si `FoodDeficitKg < 0` : « Dette de nourriture : non calculée ». `Masse(-1)` n'est pas appelé.

Les absences, à la place de ces trois lignes, sans identifiant, sans le mot « tick », sans le mot « cellule » :
- `monde == null` : « Habitants et faim : en attente du monde » ;
- `monde` non présente : « Habitants et faim : » + `TexteDuMonde.Absence(monde.Absence, identifiant de la cellule)`. La cause brute n'est pas recopiée entre parenthèses ;
- la cellule manque dans le monde servi : « Habitants et faim : absente du monde servi ». On n'y écrit ni le tick ni l'identifiant, même pas pour les faire masquer.

Chaque texte neuf doit rendre `TexteDuMonde.Interdit` et `TexteDuMonde.SansUnite` nuls.

**SC1 — L'en-tête nomme le bourg, ou dit qu'il n'est pas lu.** `PONT`, cas `LEnteteDitLeNomDuBourgOuSonAbsence`. Cellule fabriquée, identifiant 10437, puissance « Lorraine », maison nulle, une ville « Metz ». Monde de la fixture du fichier : tick 30, date (1400, 31), population 1234, faim 2, dette 12,5. `Decrire` à trois arguments :
- « Övre vik » : la première ligne est « Övre vik · Metz » ;
- « Metz », et une seconde ville « Thionville » après « Metz » : « Metz · Thionville », jamais « Metz · Metz » ni « Metz, Thionville » ;
- « Metz » seule ville : la première ligne est exactement « Metz » ;
- `null`, puis `NomsDesTerres.NomEnLecture` : « Bourg en lecture · Metz » les deux fois ;
- « lieu 10437 : service coupé » : `LogAssert.Expect(LogType.Log, "TexteDuMonde : absence déclarée par le monde : lieu 10437 : service coupé")`, puis la première ligne est « déclaré absent par le monde · Metz ». Le texte ne contient pas « 10437 ».

Contre-épreuve : un en-tête « Metz · Metz », ou « nom en cours de lecture » à la place de « Bourg en lecture », rougit.

**SC2 — Habitants, date, faim et dette, et les deux juges.** `PONT`, cas `LaFicheEnNomsDitLaDateLesJoursEtLaMasse`. Même cellule « Metz » seule, nom « Metz ». Le texte vaut exactement, lignes jointes par `\n` :

`Metz`
`Puissance : Lorraine`
`Maison : aucune, le monde n'en nomme pas`
`Habitants : ` + `TexteDuMonde.Nombre(1234)` + ` habitants · ` + `TexteDuMonde.Date(new DateDuMonde(1400, 31))`
`Faim : ` + `TexteDuMonde.Jours(2)` + ` de manque`
`Dette de nourriture : ` + `TexteDuMonde.Masse(12.5)`

On exige en plus les littéraux « 2 jours de manque » et « 12,5 kg » dans ce texte, `Interdit(texte)` nul et `SansUnite(texte)` nul. Une seconde cellule du même monde, population 0, faim −1, dette −1, nom « Metz » et ville « Metz », contient « Habitants : 0 habitant · », « Faim : non calculée », « Dette de nourriture : non calculée », et les deux juges sont nuls. Une troisième, population 1, faim 0, dette 0, contient « 1 habitant · », « Faim : 0 jour de manque » et « Dette de nourriture : 0 kg » : zéro reste une mesure.

Contre-épreuve : « 2 ticks de manque », « 12.5 kg », « au tick 30 » ou « 1234 » sans séparateur rougit l'égalité ou `Interdit`.

**SC3 — Une absence ne dit ni identifiant ni tick.** `PONT`, cas `LesAbsencesNeDisentNiIdentifiantNiTick`. En-tête « Metz », ville « Metz », nom « Metz ».
- `monde` nul : le texte finit par « Habitants et faim : en attente du monde » et ne contient pas « tick » ;
- `Lecture<MondeLu>.Absent("monde : cellule 10437 au tick 30")` : `LogAssert.Expect` sur « TexteDuMonde : absence déclarée par le monde : monde : cellule 10437 au tick 30 », puis la dernière ligne est « Habitants et faim : déclaré absent par le monde ». Le texte ne contient ni « 10437 », ni « tick », ni « cellule » ;
- monde servi comme en SC2, mais la cellule 10437 n'y est pas : la dernière ligne est « Habitants et faim : absente du monde servi ». Le texte ne contient ni « 30 », ni « tick », ni « 10437 ».
Les trois textes ont `Interdit` et `SansUnite` nuls. Contre-épreuve : l'ancienne phrase « cellule absente du monde servi au tick 30 » rougit `Interdit`.

**SC4 — La constante est celle de `Raison`, et l'écran ne la voit pas.** `PONT`, cas `LeNomEnLectureEstLaConstanteDeNomsDesTerres`. `NomsDesTerres.NomEnLecture` vaut « nom en cours de lecture ». Un `NomsDesTerres` dont `lire` lèverait si on l'appelait : `Raison(10437, 0)` vaut `NomEnLecture`, et le fichier `NomsDesTerres.cs` ne contient la chaîne « nom en cours de lecture » qu'une fois. Le même `PONT` rejoue les trois cas déjà là (`La_fiche_dit_la_carte_et_le_monde_servis`, `Hors_des_cellules_la_fiche_se_cache`, `Sans_monde_la_fiche_le_dit_et_garde_la_carte`) : la fiche affichée dit encore « Cellule 10437 · Metz », « au tick 30 », « 2 ticks de manque » et « 12.5 kg ».

Contre-épreuve : `Afficher` qui appellerait la surcharge à trois arguments fait échouer `La_fiche_dit_la_carte_et_le_monde_servis`.

**SC5 — Rien d'autre ne bouge, et le diff reste sous 300 lignes.**
- `git diff --numstat origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/FicheDeCelluleTests.cs` a 0 ligne retirée ;
- `git diff origin/master -- 3d/unity/Assets/Interface/CabinetDeCarte.cs pc/epreuve_carte.py 3d/unity/Assets/ForgeLocal3D/Editor/EpreuveCarte.cs 3d/unity/Assets/ForgeLocal3D/Pont/TexteDuMonde.cs` est vide ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

Contre-épreuve : un cas ancien retouché, le cabinet, le juge de la carte ou un fichier hors du Périmètre refuse la livraison.

## Hors périmètre
- Appeler la surcharge depuis `Afficher`, `Pas` ou `Demarrer`, et tenir un `NomsDesTerres` sur la fiche : c'est le sous-lot 3 de #884, qui montrera la terre survolée.
- La méthode à deux arguments, le texte affiché aujourd'hui, `CabinetDeCarte`, `pc/epreuve_carte.py`, `EpreuveCarte.cs`, `Lot526`.
- `TexteDuMonde`, le service, `jeu/sim/`, les dossiers qui lisent déjà `NomsDesTerres`.
- Une photo : l'écran ne change pas.

## Photo
sans objet : la surcharge n'est appelée par aucun écran. `Afficher` continue d'écrire la fiche à deux arguments, celle que l'épreuve de la carte lit déjà. Rien de visible ne change. Le sous-lot 3 de #884 posera la capture, quand la terre survolée s'écrira par son nom.
