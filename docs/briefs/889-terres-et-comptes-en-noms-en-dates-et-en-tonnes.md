# Lot #889 — « Terres et comptes » en noms, en dates et en tonnes
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Le feuillet « Terres et comptes » parle comme un registre : chaque terre tenue par son nom, la date du relevé, le grain en kilos ou en tonnes, les personnes avec leur séparateur. Il ne montre plus ni cellule, ni rang, ni tick.

## Le joueur
Le joueur ouvre « Terres et comptes ». La première ligne donne le nom de sa maison, puis la date du relevé, « jour 32 de 1400 ». Sous « TERRES TENUES », il lit « Mistra », puis « Mistra · <hameau> », au lieu de « Territoire 10340 · lieu 2 ». Son grenier dit « nourriture : 41,7 t », ses trente jours « Prélevé : 1,23 t », ses salaires en tonnes. Il sait quelles terres il tient et ce qu'elles lui rapportent, sans avoir à traduire un identifiant. C'est le sous-lot 1 de #874, lui-même sous-lot 5 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, prise en main de la carte). C'est un lot de fond de la décision du jalon : avant de payer un chantier en grain pris au grenier, le joueur doit lire ce grenier et sa part sans chercher.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. `/maison` sert déjà `date` (`jeu/sim/maisons_servies.py`), et `/lieu` sert le nom de chaque lieu, que `Forge.Pont.NomsDesTerres` (#871) lit et garde.

## Périmètre
3d/unity/Assets/Interface/DossierMaison.cs
3d/unity/Assets/Interface/Tests/DossierMaisonTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot655.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot658.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot889.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot889.cs.meta
docs/briefs/889-terres-et-comptes-en-noms-en-dates-et-en-tonnes.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot889-interface.xml -logFile 3d/unity/Temp/lot889-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté. Les tests s'écrivent d'abord, et on les voit rouges. `TexteDuMonde` et `NomsDesTerres` ne changent pas.

**Le feuillet (`DossierMaison`).**
- `Decrire(DocumentDuMonde doc, string nomSuzerain, Func<long, long, string> nomDuLieu)`. `nomDuLieu(cell, rang)` rend le nom du lieu, ou le texte de son absence.
- Ligne 1 : « <nom> · <sorte> · » + `TexteDuMonde.Date(new DateDuMonde(Annee, JourDeLAnnee))`. Si `doc.Annee` est nulle : `ArgumentException("Date non transmise")`.
- Sous « TERRES TENUES », une ligne par tenue : `nomDuLieu(cell, 0)` au rang 0 ; sinon `nomDuLieu(cell, 0) + " · " + nomDuLieu(cell, rang)`.
- Grenier, les cinq flux et « Salaires » : `TexteDuMonde.Masse`. Départs et arrivées : `Nombre(n)` + « personnes », ou « personne » pour 0 ou 1. La part reste en « 25 % ». Les bornes et les refus actuels ne changent pas.
- Chaque raison de « ABSENCES DÉCLARÉES » passe par `TexteDuMonde.Absence(raison, <cell_id du siège et des lieux, en texte invariant>)`. L'identifiant de la maison n'y est pas passé : « part absent pour la maison bar » reste lisible.
- `public static string Indisponible(string raison) => "Comptes indisponibles : " + TexteDuMonde.Absence(raison)`. Le `catch` de `Pas` l'appelle.
- `public static string NomDuLieu(NomsDesTerres noms, long cell, long rang, double maintenant)` = `noms.Nom(…) ?? TexteDuMonde.Absence(noms.Raison(cell, rang), cell en invariant)`. `Pas` passe `(c, r) => NomDuLieu(noms, c, r, maintenant)`.
- `Initialiser(toile, maison, port)` garde sa signature et crée `NomsDesTerres.Local(port)`. La surcharge des tests reçoit un `NomsDesTerres` en dernier. La relecture reste pilotée par le tick, qui ne s'affiche plus. `CabinetDeCarte` n'est pas touché.

**SC1 — Les comptes parlent en noms, en dates et en tonnes.** `INTERFACE`, cas neuf `Les_comptes_disent_les_terres_par_leur_nom_la_date_et_les_tonnes`. Le document est `Complet` avec trois tenues, `lieux` `[{10430,0},{10430,2},{10437,1}]`, puis `preleve_kg` 41712, `partis_personnes` 1 et `"salaires_payes_kg":1500`. `nomDuLieu` est un dictionnaire : (10430,0) « Bar-le-Duc », (10430,2) « Longeville », (10437,0) « Metz », (10437,1) « Scy ». Attendus, après `Replace("\r", "")` :
- la ligne 1 vaut « Bar · seigneurie · jour 8 de 1400 » ;
- le texte contient « TERRES TENUES\nBar-le-Duc\nBar-le-Duc · Longeville\nMetz · Scy\n », « Prélevé : 41,7 t », « Salaires : 1,50 t », « Grenier : bois : 0 kg · nourriture : 1,23 t », « Départs : 1 personne\n » et « Arrivées : 6 personnes » ;
- il ne contient ni « Territoire », ni « lieu 0 », ni « 1234 » ; `Interdit(texte, "10430", "10437")` et `SansUnite(texte)` sont nuls.

Contre-épreuve : l'ancienne ligne « Territoire 10430 · lieu 2 », un « tick 7 » ou « 41712 kg » rougit.

**SC2 — Les absences et les erreurs se disent sans identifiant.** `INTERFACE`, cas neuf `Les_noms_absents_la_date_absente_et_les_erreurs_passent_par_l_absence`.
- Un `NomsDesTerres` dont `lire` rend, pour 10430, un `Lieu` au rang 0 « Bar-le-Duc » et au rang 2 sans nom (absence « clé lieux[1].nom : null déclaré »). Pour 10437, il rend `LectureLieu.Absent("lieu 10437 : service coupé")`. On attend comme `ClientLieuTests.Attendre` : `SpinWait` jusqu'à `!LectureEnVol`.
- `NomDuLieu(noms, 10430, 0, 0)` vaut d'abord « nom en cours de lecture », puis « Bar-le-Duc » après l'attente. (10430, 5) donne « aucun lieu de ce rang dans la terre ». (10430, 2) donne « déclaré absent par le monde ». (10437, 0) dit « nom en cours de lecture », puis, après une seconde attente, « déclaré absent par le monde ». Chaque masque a son `LogAssert.Expect`.
- `Complet` sans sa clé `date` lève une `ArgumentException` dont le message contient « Date ».
- `Indisponible("Date non transmise")` vaut « Comptes indisponibles : Date non transmise ». `Indisponible("Lecture refusée (404) : maison inconnue")` vaut « Comptes indisponibles : déclaré absent par le monde ».
- La raison « nom de maison absent pour la cellule 10430 » s'écrit « nom : déclaré absent par le monde ».

Contre-épreuve : une raison passée telle quelle, ou une date absente qui passe, rougit.

**SC3 — Les cas existants suivent la décision A de #856.** La fixture `Document` reçoit `"date":{"annee":1400,"jour_de_l_annee":8}`. Les appels prennent un `nomDuLieu` témoin, qui donne « Bar-le-Duc » pour (10430, 0). Chaque assertion garde sa force :
- « tick 7 » devient « jour 8 de 1400 » ;
- « 10430 » devient « TERRES TENUES\nBar-le-Duc » ;
- « nourriture : 1234,5 kg » devient « nourriture : 1,23 t » ;
- dans `Le_feuillet_suit_le_tick_publie_et_garde_sa_cadence_apres_un_echec`, le faux service sert le jour `servi + 1`, et « tick 7/8/9 » devient « jour 8/9/10 de 1400 ». Le nombre d'appels et les cadences ne changent pas.
Les autres cas restent tels quels.

`git diff origin/master -- 3d/unity/Assets/Interface/Tests/DossierMaisonTests.cs` ne retire que ces lignes, plus les appels qui gagnent un argument. Contre-épreuve : une assertion retirée sans remplaçante refuse la livraison.

**SC4 — `Lot655` lit la date et les tonnes.**
- `Dit(texte, DateDuMonde date, part)` cherche « · » + `TexteDuMonde.Date(date)` + `Environment.NewLine`.
- Au tick + 1, la date est `partie.Monde.Donnees.Monde.Date`. À `fin`, on attend `horloge.Lue?.Tick == fin`, puis la date est `horloge.Lue.Date`.
- « Prélevé : » s'écrit avec `TexteDuMonde.Masse(PreleveKg)`.
- `MistraTerresEtComptes` devient `internal`. À sa fin, elle garde en `internal static` le `DossierMaison`, son `Text`, les `ComptesDeMaison` lus à `fin` et le port.

Les commandes, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 655 -forgeCaptures 3d/unity/Temp/lot889-655-photo -logFile 3d/unity/Temp/lot889-655-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 655 -forgeCaptures 3d/unity/Temp/lot889-655-sans-tick -forge655SansTick -logFile 3d/unity/Temp/lot889-655-sans-tick.log
```
La première sort 0. La seconde sort 1, avec « 25 % … attendu ».

**SC5 — `Lot658` lit le feuillet de même.** `Attendu` gagne `DateDuMonde Date`, prise sur `monde.LireAvecMaison()` dans `Lire`. La ligne 42 attend « · » + `Date(at.Date)` + NewLine, puis « Prélevé : » + `Masse(at.Preleve)` et « Dû envoyé : » + `Masse(at.Du)`. Les légendes (« Cellule … au tick ») ne changent pas : c'est le sous-lot 6 de #856.
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 658 -forgeCaptures 3d/unity/Temp/lot889-658-photo -logFile 3d/unity/Temp/lot889-658-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 658 -forgeCaptures 3d/unity/Temp/lot889-658-retirer -forge658RetirerDu -logFile 3d/unity/Temp/lot889-658-retirer.log
```
La première sort 0. La seconde sort 1, avec « flèche manquante ».

**SC6 — Rien d'autre ne bouge.** `INTERFACE` passe sur toute l'assemblée. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

## Hors périmètre
- `CommandesMaison`, l'ordre de part, `Lot656` et `EpreuvePart` : sous-lot 2 de #874.
- Les légendes des lieux et des flèches, `Lot657`, et les lignes « Cellule … au tick » lues par `Lot658` : sous-lot 6 de #856.
- `CabinetDeCarte`, `NomsDesTerres`, `TexteDuMonde`, le service et `jeu/`.
- Le mot « seigneurie » et l'écriture de la part en pourcentage.

## Photo
La photo montre la carte de 1400 avec le feuillet « Terres et comptes » de Mistra ouvert, à 25 %, après trente jours. On y lit la date en « jour N de 1400 », les terres tenues par leur nom (« Mistra », « Mistra · … »), le grenier et les flux en kg ou en t. Aucune cellule, aucun rang, aucun tick.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot889.cs`, un scénario `[ScenarioDeCapture(889, "mistra-en-noms")]`. Chaque attente est bornée par `Lot690.Jusqua`. Chaque absence échoue en nommant sa cause.
1. Jouer `Lot655.MistraTerresEtComptes(camera)` (`for (var e = …; e.MoveNext();) yield return null;`) : elle pose la photo.
2. Pour chaque tenue des comptes gardés, lire `/lieu?cell=` par `ClientLieu`, dans un `Task.Run`, et exiger le nom du rang 0 et celui du rang de la tenue. Sinon, `Echec` cite `AbsenceDuNom`. La ligne attendue s'écrit comme dans `Decrire`.
3. Attendre que chaque ligne attendue soit une ligne entière de `TexteAffiche`.
4. Dans une même image, sans `yield` : avec `-forge889Territoire`, ajouter d'abord « \nTerritoire <première cellule> · lieu 0 » au `Text` du feuillet. Puis exiger :
   - `Text.text` qui commence par `TexteAffiche` ;
   - `Interdit(Text.text, <chaque cellule tenue>)` nul, sinon `Echec("mot interdit « " + mot + " » dans le feuillet : « " + première ligne + " »")` ;
   - `SansUnite(Text.text)` nul.
5. La trace `CAPTURE_889` donne la maison, les lignes des terres tenues et la ligne 1.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 889 -forgeCaptures 3d/unity/Temp/lot889-photo -logFile 3d/unity/Temp/lot889-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 889 -forgeCaptures 3d/unity/Temp/lot889-territoire -forge889Territoire -logFile 3d/unity/Temp/lot889-territoire.log
```
La première sort 0 avec une image `*--mistra-en-noms.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image, avec « mot interdit » dans son journal. Le codeur ouvre l'image lui-même. Une « Cellule », un « rang », un « tick », un « Territoire 10… », un nombre sans unité ou un feuillet coupé refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, les sorties des trois contre-épreuves et ce que montre l'image.
