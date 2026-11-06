# Lot #1012 — Le dossier des voisins dit pourquoi l'IA trace sa route vers le champ
Jalon : J5 · Machine : pc · Taille prévue : 260 lignes

## But
Le feuillet « Les autres maisons » lit la raison `route_vers_le_champ` du programme de l'IA : la faim du bourg, le champ visé par son nom et ses vivres, le coût en jours de travail et en kilos face au grenier et à la réserve voulue ; il lit toujours l'ancienne raison `route_si_bourg_affame`.

## Le joueur
Le joueur ouvre « Autres maisons » et lit, sous « Luxembourg · il y a 2 jours » et « Tracer une route à Prague » : « Faim du bourg : 1 jour sur le dernier mois. », « Champ visé : Stará Lhota, 106 t de vivres, le plus plein des 20 lieux autour du bourg. », « Coût : 81 jours de travail, 243 kg · Grenier : 1 406 t · Réserve voulue : 696 t. ». Il lit pourquoi une maison bâtit sa route, au lieu de « Raison non interprétée par cette vue. » : son bourg a faim, elle va chercher le champ le plus plein, et son grenier paie sans entamer sa réserve. C'est le geste du jalon 5 « regarder le monde vivre, puis s'en méfier ou s'en servir », avec « les gestes de l'IA, avec leurs raisons ». Dans le jeu, la phrase vient dès que le branchement du programme (#1000, dont ce lot est découpé) fait de la route vers le champ la règle ; d'ici là, la photo joue le programme amorcé comme le font les tests de `sim/`.

## Règle du monde
Sans objet : lot de vue. Aucun nombre du monde ne change ; `jeu/` et `jeu/sim/MODELE.md` ne sont pas touchés. La raison est celle que rend `proposer_route_vers_le_champ` (`jeu/sim/programme_ia.py`) : `faim_du_bourg_ticks` (jours où le bourg est affamé, de t−30 à t−1), `champs_nourriture_kg` (vivres des lieux de rang ≥ 1, triés par rang : l'indice `champ_vise − 1` est le champ visé), `champ_vise` (son rang), `journees`, `cout_kg`, `grenier_nourriture_kg`, `reserve_voulue_kg`. Un tick dure un jour.

## Périmètre
3d/unity/Assets/Interface/DossierVoisins.cs
3d/unity/Assets/Interface/Tests/DossierVoisinsTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1012.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1012.cs.meta
docs/briefs/1012-le-dossier-des-voisins-dit-pourquoi-l-ia-trace-s.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1012-interface.xml -logFile 3d/unity/Temp/lot1012-interface.log`, sans `-quit` : sortie 0, XML sans échec ni cas ignoré, chaque cas nommé exécuté. Le test s'écrit d'abord et se voit rouge. `TexteDuMonde`, `NomsDesTerres`, `DossierMaison`, `Feuillet`, `LectureDossier` ne changent pas.

**Le journal (`DossierVoisins`).**
- Nouvelle forme `Decrire(DocumentDuMonde document, DocumentDuMonde registre, Func<long, long, string> nomDuLieu)` (terre, rang), qui porte le corps actuel. La forme `Func<long, string> nomDuBourg` reste et appelle la nouvelle avec `(c, r) => r == 0 ? nomDuBourg(c) : throw new ArgumentException("Nom du lieu non fourni")`. `LateUpdate` passe `(c, r) => DossierMaison.NomDuLieu(noms, c, r, maintenant)`.
- Raison `route_si_bourg_affame` : ses deux lignes ne changent pas. Toute autre règle garde « Raison non interprétée par cette vue. ».
- Raison `route_vers_le_champ`, sur un `tracer_route` seulement (sinon `ArgumentException("Raison de route sur un ordre sans terre")`). `champ_vise` (`Entier`) doit valoir de 1 au nombre `n` de `champs_nourriture_kg`, sinon `ArgumentException("Champ visé hors des lieux de la terre")` ; l'élément `champ_vise − 1` doit être un `double` fini, sinon `ArgumentException("Vivres du champ visé invalides")`. Trois lignes :
  - « Faim du bourg : » + `Jours(faim_du_bourg_ticks)` + « sur le dernier mois. » ;
  - « Champ visé : » + `nomDuLieu(cell, champ_vise)` + « , » + `Masse(vivres)` + « de vivres, le plus plein des » + `Nombre(n)` + « lieux autour du bourg. » (« lieu » si `n` = 1) ;
  - « Coût : » + `Jours(journees)` + « de travail, » + `Masse(cout_kg)` + « · Grenier : » + `Masse(grenier_nourriture_kg)` + « · Réserve voulue : » + `Masse(reserve_voulue_kg)` + « . ».
  « journées » et « champs » ne sont pas des unités de `SansUnite` : d'où « jours de travail » et « lieux ».

**SC1 — La route vers le champ se lit.** `INTERFACE`, cas neuf `La_route_vers_le_champ_dit_la_faim_le_champ_et_son_cout`. Fixture : `{"tick":57,"intention":{"type":"tracer_route","maison":"grande-10","cell":10466},"raison":{"regle":"route_vers_le_champ","faim_du_bourg_ticks":3,"champs_nourriture_kg":[0,455,1552,512],"champ_vise":3,"journees":80,"cout_kg":240,"grenier_nourriture_kg":702932.7,"reserve_voulue_kg":426720,"ecart_degres":0}}`, avec `Geste` dans le même relevé, et `nomDuLieu` témoin : (10466, 0) → « Milan », (10466, 3) → « Lambrate », sinon `ArgumentException`. Attendus : « Maison témoin · il y a 3 jours », « Faim du bourg : 3 jours sur le dernier mois. », « Champ visé : Lambrate, 1,55 t de vivres, le plus plein des 4 lieux autour du bourg. », « Coût : 80 jours de travail, 240 kg · Grenier : 703 t · Réserve voulue : 427 t. », et pour `Geste` « Bourg affamé : 21 habitants, 1 jour de faim. » ; aucun « Raison non interprétée » ; `Interdit(texte, "10466")` et `SansUnite(texte)` nuls. Contre-épreuves, chacune une `ArgumentException` : `champ_vise` 0, puis 5 ; `cout_kg` retiré ; la fixture lue par la forme `nomDuBourg` (« Nom du lieu non fourni »). Le code d'avant rougit : il écrit « Raison non interprétée par cette vue. ».

**SC2 — Les cas existants ne bougent pas.** `git diff --numstat origin/master -- 3d/unity/Assets/Interface/Tests/DossierVoisinsTests.cs` montre 0 ligne retirée, et `INTERFACE` passe sur toute l'assemblée, `Lot892.cs` compilé tel quel. Contre-épreuve : un attendu retiré ou affaibli refuse la livraison.

**SC3 — Le service des captures peut jouer le programme.** `ForgeCapture.cs` gagne `public const string SERVICE_PROGRAMME = "-forgeServiceProgramme"`. Avec ce drapeau, l'interpréteur reçoit `-c "import pytest, sim.tests.test_monde as t; t._brancher_programme(pytest.MonkeyPatch()); import runpy; runpy.run_module('sim.service', run_name='__main__')"` au lieu de `-m sim.service`, le reste de la ligne identique (c'est `_AMORCAGE_PROGRAMME` de `test_monde.py`, que `lancer_service` utilise déjà) ; la trace `CAPTURE_SERVICE` finit par « programme » ; le commentaire d'usage le nomme. Sans lui, la ligne de commande ne change pas. Preuve : le journal de `PHOTO` contient `CAPTURE_SERVICE graine 0 tick 69 pid … --ia programme`.

**SC4 — La photo et sa contre-épreuve** (section Photo) : `PHOTO` sort 0 avec l'image ; `ANCIENNE` sort 1 sans image, son journal dit « ne dit pas sa raison ».

**SC5 — Rien d'autre ne bouge.** `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ; `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes (`Lot1012.cs` sous 85 lignes).

## Hors périmètre
- Brancher le programme dans `decider_intentions`, retirer l'ancienne règle, écrire `MODELE.md` : #1000. Ce lot-là retirera aussi `SERVICE_PROGRAMME` quand il retirera `_brancher_programme`.
- Dire `ecart_degres`, les ordres de part et de grenier et leurs raisons (« Ordre non interprété par cette vue » reste), la fiche de survol, la carte (#322, #429), le service (#428).

## Photo
La carte de 1400, graine 0, IA active avec la route vers le champ du programme, au jour 71 de 1400, feuillet « Les autres maisons » ouvert. Mesuré sur le VPS (CLI amorcée, égale au service par `test_ia_service_ia_egal_cli`) : routes du programme aux ticks 65 (Barquq, Le Caire → Bir al-Kabir) et 68 (Luxembourg, Prague → Stará Lhota, champ 19, faim 1 jour, 81 journées, 243 kg, grenier 1 405 998 kg, réserve 695 838 kg) ; aucun ordre aux ticks 69 et 70. En haut du journal : « Journal du jour 71 de 1400 », puis le bloc de Luxembourg avec ses trois lignes de raison (section « Le joueur »).

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1012.cs`, `[ScenarioDeCapture(1012, "route-vers-le-champ")]`, sur le modèle de `Lot892` ; chaque attente bornée par `Lot690.Jusqua` ou `Lot690.Attendre`, chaque absence nomme sa cause.
1. Sans `Capture.SERVICE_IA` et `Capture.SERVICE_PROGRAMME` : `Echec("lancer avec -forgeServiceIa -forgeServiceProgramme : la route vers le champ n'est pas jouée")`.
2. Ouvrir et poser la carte comme `Lot892` (`Lot549.Ouvrir`, `Lot549.Photographier`, toile sur la caméra, `automatique` sur survol, parcours, commandes du temps). Un `Lot690.PousserTick`, statut 200. Invoquer l'unique bouton « Autres maisons ».
3. Lire `/ia` et `/maisons` (`LectureDossier.Locale`), au tick du `POST`. Prendre, dans l'ordre de `Decrire` (tick décroissant), la première entrée de raison `route_vers_le_champ` ; aucune : `Echec("aucune route vers le champ dans le journal : " + compte par règle)`. Lire `/lieu` de chaque terre de route par `ClientLieu` dans un `Task.Run` ; le nom d'un rang absent fait échouer.
4. `attendu = DossierVoisins.Decrire(ia, maisons, (c, r) => nom lu)` ; attendre `dossier.TexteAffiche == attendu`, puis dix images.
5. Dans une même image, sans `yield`, sur le `Text` du cabinet qui montre `TexteAffiche` : avec `-forge1012Ancienne`, remplacer d'abord dans `Text.text` la ligne « Faim du bourg : … » de ce bloc par « Raison non interprétée par cette vue. ». Puis exiger :
   - que le bloc (de sa ligne « <maison> · … » à la ligne vide suivante) contienne « Faim du bourg : », « Champ visé : <nom du champ lu> » et « Coût : », sans « Raison non interprétée », sinon `Echec("la route de <maison> ne dit pas sa raison : « <bloc> »")` ;
   - `Interdit(Text.text, <terres des routes>)` et `SansUnite(Text.text)` nuls ; `Lot690.DansLeChamp(camera, Text)` ;
   - contenu du feuillet en haut (`anchoredPosition.y` = 0) et hauteur préférée du texte jusqu'à la fin du bloc (`cachedTextGeneratorForLayout.GetPreferredHeight(début, GetGenerationSettings(new Vector2(largeur, 0))) / pixelsPerUnit`) sous la hauteur de la fenêtre défilante, sinon `Echec("la raison de la route est sous le bas du feuillet")`.
6. Trace `CAPTURE_1012` : ligne 1, compte des ordres par règle, le bloc de la route.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1012 -forgeServiceIa -forgeServiceProgramme -forgeTicks 69 -forgeCaptures 3d/unity/Temp/lot1012-photo -logFile 3d/unity/Temp/lot1012-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1012 -forgeServiceIa -forgeServiceProgramme -forgeTicks 69 -forge1012Ancienne -forgeCaptures 3d/unity/Temp/lot1012-ancienne -logFile 3d/unity/Temp/lot1012-ancienne.log
```
`PHOTO` (la première) sort 0 avec `*--route-vers-le-champ.png` et la trace `CAPTURE_SERVICE … --ia programme` : c'est la photo. `ANCIENNE` sort 1 sans image. Le codeur ouvre l'image : « Journal indisponible », « Raison non interprétée » dans le bloc de la route, un « tick », un identifiant de terre, un nombre sans unité ou une raison coupée refusent la livraison même avec une sortie 0. Le service amorcé demande `pytest` à l'interpréteur du PC (`pc/Tests.cmd` le lance déjà) ; s'il manque, la trace `CAPTURE : service absent` le dit. Les PNG restent hors du dépôt ; le compte rendu donne les commandes, le rouge initial du test, la sortie de la contre-épreuve et ce que montre l'image.
