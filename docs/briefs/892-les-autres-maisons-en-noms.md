# Lot #892 — Les autres maisons en noms
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Le feuillet « Les autres maisons » tient le journal des ordres de l'IA comme un registre. Il donne la date servie, chaque ordre « il y a N jours », la terre d'une route par le nom de son bourg, la faim en jours et les masses en kg ou en t. Un ordre de part ou de grenier ne fait plus tomber le journal.

## Le joueur
Le joueur ouvre « Autres maisons » dans « Parcourir le monde ». Il lit « Journal du jour 32 de 1400 », puis « Visconti · il y a 6 jours », « Tracer une route à Milan », « Bourg affamé : 21 399 habitants, 1 jour de faim. », « Dette alimentaire : 14,1 t ». Aujourd'hui, il lit « tick 25 · territoire 10466 », et dès qu'une maison fixe sa part, il ne lit plus que « Journal indisponible : Champ absent : cell ». Il voit quand et où ses voisins ont tracé une route pour un bourg affamé, sans traduire un identifiant. C'est la décision du jalon : une route vers les champs, ou des bras gardés aux champs. C'est le sous-lot 2 de #876, sous-lot 7 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, prise en main de la carte).

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, et ni `jeu/` ni `jeu/sim/MODELE.md` ne sont touchés. `/ia` sert déjà `date`, et le service a déjà `--ia` (`jeu/sim/service.py`). Un tick dure un jour (`TICK_DURATION_DAYS = 1`), donc « il y a N jours » vaut le tick du journal moins le tick de l'ordre. Le nom du bourg vient de `/lieu` par `NomsDesTerres` (#871).

## Périmètre
3d/unity/Assets/Interface/DossierVoisins.cs
3d/unity/Assets/Interface/Tests/DossierVoisinsTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot892.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot892.cs.meta
docs/briefs/892-les-autres-maisons-en-noms.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot892-interface.xml -logFile 3d/unity/Temp/lot892-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté. Les tests s'écrivent d'abord, et on les voit rouges. `TexteDuMonde`, `NomsDesTerres`, `DossierMaison`, `Feuillet` et `CabinetDeCarte` ne changent pas.

**Le journal (`DossierVoisins`).**
- `Decrire(DocumentDuMonde document, DocumentDuMonde registre, Func<long, string> nomDuBourg)`. Si `document.Annee` est nulle : `ArgumentException("Date non transmise")`.
- Ligne 1 : « Journal du » + `TexteDuMonde.Date(new DateDuMonde(Annee, JourDeLAnnee))`. Le tick du registre ne s'affiche plus.
- Ligne 2 : « Activité des premiers 30 jours : » + « mesure en cours », ou `Nombre(n)` + « maison » / « maisons ». « 30 premiers jours » laisserait « 30 » sans unité.
- En tête de chaque ordre : nom de la maison + « · » + « ce jour » si l'écart vaut 0, sinon « il y a » + `TexteDuMonde.Jours(écart)`. Les refus actuels restent : ordre daté après le journal, ordre dupliqué, raison absente.
- `cell` n'est lu que si `type == "tracer_route"`. La ligne vaut alors « Tracer une route à » + `nomDuBourg(cell)`. La clé de doublon reste tick/maison/type, plus `cell` pour une route. Les autres types gardent « Ordre non interprété par cette vue ».
- Raison `route_si_bourg_affame` : « Bourg affamé : » + `Nombre(population)` + « habitants » (« habitant » pour 0 ou 1) + « , » + `Jours(duree_faim_ticks)` + « de faim. ». Puis « Dette alimentaire : » + `Masse` + « · Nourriture : » + `Masse`. Les autres raisons gardent leur phrase.
- `public static string Indisponible(string raison) => "Journal indisponible : " + TexteDuMonde.Absence(raison)`. Le `catch` de `LateUpdate` l'appelle, et « ia désactivée » garde sa phrase.
- `public string TexteAffiche { get; private set; }`, écrit avec le feuillet. `Initialiser(toile, guide, port)` garde sa signature et crée `NomsDesTerres.Local(port)`. `LateUpdate` passe `c => DossierMaison.NomDuLieu(noms, c, 0, maintenant)`.

**SC1 — Les cas existants suivent la décision A de #856.** La fixture `Document` reçoit `"date":{"annee":1400,"jour_de_l_annee":61}`. Chaque appel prend un `nomDuBourg` témoin, qui donne « Milan » pour 10466. Chaque assertion garde sa force :
- « tick 25 » devient « Maison témoin · il y a 35 jours » ;
- « 10466 » devient « Tracer une route à Milan » ;
- « 30 premiers jours » devient « Activité des premiers 30 jours : 1 maison ».
Les autres attendus (« 14,5 kg », « 0,4 kg », « Ordre reçu », « Refus : terrain interdit », les trois `Throws`, « Aucun ordre transmis », « mesure en cours ») restent tels quels. `git diff origin/master -- 3d/unity/Assets/Interface/Tests/DossierVoisinsTests.cs` ne retire que ces lignes, la fixture et les appels qui gagnent un argument. Contre-épreuve : une assertion retirée sans remplaçante refuse la livraison.

**SC2 — Un ordre de grenier ou de part ne fait plus tomber le journal.** `INTERFACE`, cas neuf `Les_ordres_de_grenier_et_de_part_se_lisent_sans_terre`. Le relevé contient `Geste`, puis `{"tick":60,"intention":{"type":"ouvrir_grenier","maison":"grande-10","kg":1200},"raison":{"regle":"secours_apres_faim"}}` et `{"tick":59,"intention":{"type":"fixer_part","maison":"grande-10","part":0.08},"raison":{"regle":"part_sur_projets_et_gens"}}`. Aucun des deux n'a de `cell`. Attendus :
- `Decrire` rend un texte sans lever d'exception ;
- le texte contient « Maison témoin · ce jour », « Maison témoin · il y a 1 jour », « Maison témoin · il y a 35 jours », « Tracer une route à Milan », « Bourg affamé : 21 habitants, 1 jour de faim. », deux fois « Ordre non interprété par cette vue » et la ligne 1 « Journal du jour 61 de 1400 » ;
- `TexteDuMonde.Interdit(texte, "10466")` et `TexteDuMonde.SansUnite(texte)` sont nuls ;
- `Document` sans clé `date` lève une `ArgumentException` dont le message contient « Date » ;
- `Indisponible("Champ absent : cell 10466")` vaut « Journal indisponible : déclaré absent par le monde ».
Contre-épreuve : le code d'avant (`cell` lu pour tout ordre) lève « Champ absent : cell » et rougit ; un « tick », un « jours de faim » écrit « ticks de faim », ou « 14075 kg » au lieu de `Masse` rougit aussi.

**SC3 — Le service des captures se lance avec l'IA.** `ForgeCapture.cs` gagne `public const string SERVICE_IA = "-forgeServiceIa"`. Avec ce drapeau, `LancerService` ajoute « --ia » à la ligne de commande du service, et la trace `CAPTURE_SERVICE` le dit. Le commentaire d'usage le nomme. Sans le drapeau, rien ne change pour les autres captures. Preuve : le journal de la commande photo (section Photo) contient une ligne `CAPTURE_SERVICE graine 0 tick 30 pid … --ia`. Le scénario `Lot892` échoue d'abord si le drapeau manque.

**SC4 — Rien d'autre ne bouge.** `INTERFACE` passe sur toute l'assemblée. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

## Hors périmètre
- Dire en mots un ordre de part ou de grenier et sa raison : ils restent « Ordre non interprété par cette vue ».
- Le texte des refus servis par `sim/`, `CabinetDeCarte`, la place du feuillet, `Feuillet`, `NomsDesTerres`, `TexteDuMonde`, `jeu/` et le service.
- Le plan, les chantiers, l'outil de rue, les calques et le menu : sous-lot 1 de #876 (#891). L'épreuve de #856 : son sous-lot 8.

## Photo
La photo montre la carte de 1400 avec le feuillet « Les autres maisons » ouvert, au jour 32 de 1400, graine 0, IA active. Mesures faites sur le VPS avec `--ia` : au tick 31, le journal tient trois ordres de part au tick 30, puis la route de Visconti au tick 25. On y lit « Journal du jour 32 de 1400 ». Puis trois maisons « il y a 1 jour », « Visconti · il y a 6 jours », « Tracer une route à Milan » et « Dette alimentaire : 14,1 t ». Aucun tick, aucune cellule, aucun « Journal indisponible ».

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot892.cs`, un scénario `[ScenarioDeCapture(892, "autres-maisons-en-noms")]`. Chaque attente est bornée par `Lot690.Jusqua` ou `Lot690.Attendre`. Chaque absence échoue en nommant sa cause.
1. Sans `Capture.SERVICE_IA` dans la ligne de commande : `Echec("lancer avec -forgeServiceIa : /ia est coupé")`.
2. Ouvrir la carte par `Lot549.Ouvrir`, puis `Lot549.Photographier`. Poser le cabinet sur la caméra comme `Lot883` : rect plein, décalage vers l'est, toile en `ScreenSpaceCamera`. Mettre `automatique` sur `SurvolDeCarte`, `ParcoursDeCarte` et `CommandesDuTemps`.
3. Un seul `Lot690.PousserTick(carte.port)` : statut 200 exigé, sinon `Echec` cite le corps.
4. Invoquer le `Button` nommé « Autres maisons » sous la carte. Prendre le `DossierVoisins` de la carte.
5. Lire `/ia` et `/maisons` par `LectureDossier.Locale(port)`. Exiger le tick du `POST`, au moins un `tracer_route` et au moins un ordre d'un autre type. Sinon : `Echec("le journal n'a pas de route et d'ordre sans terre : " + compte par type)`. Pour chaque cellule de route, lire le rang 0 de `/lieu` par `ClientLieu` dans un `Task.Run`, et exiger son nom servi, comme `Lot873.Bourg`.
6. `attendu = DossierVoisins.Decrire(ia, maisons, c => nom lu)`. Attendre `dossier.TexteAffiche == attendu`.
7. Dans une même image, sans `yield` : prendre le `Text` du cabinet dont le texte vaut `TexteAffiche`. Avec `-forge892Tick`, y ajouter d'abord « \n<nom de la maison de la route> · tick <tick de la route> ». Puis exiger :
   - que `Text.text` commence par `TexteAffiche` ;
   - que `Interdit(Text.text, <chaque cellule de route>)` soit nul, sinon `Echec("mot interdit « " + mot + " » dans le journal : « " + ligne 1 + " »")` ;
   - que `SansUnite(Text.text)` soit nul ;
   - que le texte contienne « Tracer une route à » + nom lu ;
   - `Lot690.DansLeChamp(camera, Text)`.
8. La trace `CAPTURE_892` donne la ligne 1, le compte des ordres par type et la ligne de la route.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 892 -forgeServiceIa -forgeCaptures 3d/unity/Temp/lot892-photo -logFile 3d/unity/Temp/lot892-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 892 -forgeServiceIa -forgeCaptures 3d/unity/Temp/lot892-tick -forge892Tick -logFile 3d/unity/Temp/lot892-tick.log
```
La première sort 0, avec une image `*--autres-maisons-en-noms.png` et la trace `CAPTURE_SERVICE … --ia` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image, avec « mot interdit « tick » » dans son journal. Le codeur ouvre l'image lui-même. Ces textes refusent la livraison, même avec une sortie 0 : un « tick », un « territoire 10… », « Journal indisponible », « ne sont pas actives », un nombre sans unité, ou une route coupée en bas du feuillet. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre l'image.
