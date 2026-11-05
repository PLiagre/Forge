# Lot #1001 — La barre lit le grenier et la part au même tick
Jalon : J4 · Machine : pc · Taille prévue : 270 lignes

## But
Le bandeau du cabinet devient la barre du haut. Sous la date, la pause et la vitesse, il dit le nom de la maison du joueur, ou qu'aucune n'est choisie, puis sa part et son grenier, lus aux comptes servis au même tick que le monde lu.

## Le joueur
Le joueur a pris Mistra. En haut de l'écran, sans rien ouvrir, une ligne lui dit le nom de sa maison, son prélèvement (« Prélèvement : 60 % ») et ce que tient son grenier (« Grenier : nourriture : 571 t »). La date, la pause et la vitesse sont juste au-dessus. Tant qu'il n'a pas de maison, la barre dit « Aucune maison choisie ». Les nombres de la barre sont ceux du jour que le monde vient de servir : s'ils ne sont pas encore relus, la barre dit qu'elle attend, elle ne montre jamais le grenier de la veille. C'est le premier des quatre morceaux du geste « Une seule barre en haut » du jalon 4 (`CAP.md`, lot 21, #859 : « Sa maison, la date, le temps, son grenier et sa part » ; « une barre lue un tick plus tôt échoue »). Ce geste sert la décision du jalon : lire son grenier et sa part d'un coup d'œil avant d'envoyer des bras au chantier, payés au grenier. Les icônes des dossiers, le retrait du panneau « Parcourir le monde » et la preuve du geste viennent avec les trois sous-lots suivants de #859.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, ni `jeu/sim/`, ni le service. `GET /maison?id=` sert déjà `tick` à côté de `part` et `grenier` (`jeu/sim/maisons_servies.py`, `document_de_maison`) ; Unity le lit enfin.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/ClientMaison.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/ClientMaisonTests.cs
3d/unity/Assets/Interface/LecturePartie.cs
3d/unity/Assets/Interface/Tests/LecturePartieTests.cs
3d/unity/Assets/Interface/DossierMaison.cs
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1001.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot1001.cs.meta
docs/briefs/1001-la-barre-lit-le-grenier-et-la-part-au-meme-tick.md

Tout autre chemin est interdit, en particulier `DossierMaisonTests.cs`, `CommandesMaison.cs`, `SocleInterface.cs`, `HorlogeDeCarte.cs`, `jeu/` et les scénarios `Lot658`, `Lot690`, `Lot883`, `Lot944`, `Lot965` : ils sont lus, jamais modifiés. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt. Ce brief s'appuie sur master 513d0b5.

**`ClientMaison.cs`.** `ComptesDeMaison` gagne `public long? Tick { get; }` et un sixième paramètre `long? tick = null` à son constructeur : les constructions existantes ne changent pas. `Comptes(racine, demande)` lit `tick` s'il est présent (`racine.ContainsKey("tick")`), par `ServiceLocal.Entier(racine, "tick", 0)` : un tick nul, négatif, fractionnaire ou textuel refuse toute la réponse, à la clé `tick`. Absent, `Tick` vaut `null` : « tick non servi », jamais deviné. `Lire` (la fiche) ne change pas.

**`LecturePartie.cs`.** `public Lecture<ComptesDeMaison> Comptes { get; private set; }`. Cinquième paramètre du constructeur : `Func<string, Lecture<ComptesDeMaison>> comptes = null`. `Actualiser` lit, dans la même tâche et dans cet ordre : le monde, la fiche de la maison, puis ses comptes, seulement si le monde nomme une maison du joueur et que le lecteur existe ; sinon `Comptes` vaut `null`. Une exception remet `Comptes` à `null` avec `Maison`. `Locale(port)` passe `id => { using var c = new ClientMaison(port, TimeSpan.FromSeconds(10)); return c.LireComptes(id); }`.

**`DossierMaison.cs`.** Deux fonctions publiques et statiques sortent de `Decrire`, qui les appelle, et son texte ne change pas d'un caractère (`DossierMaisonTests` reste vert sans être touché) :
- `Prelevement(double? part)` rend `"Prélèvement : absent"` pour `null`, sinon `"Prélèvement : " + (Borne(part, 1, "part") * 100).ToString("0.##", fr-FR) + " %"` ;
- `Grenier(IEnumerable<KeyValuePair<string, double>> panier)` rend `"Grenier : absent"` pour `null`, `"Grenier : vide"` pour un panier vide, sinon les marchandises triées en ordinal, `clé + " : " + TexteDuMonde.Masse(Borne(kg, double.MaxValue, clé))`, jointes par `" · "`.

`Decrire` garde ses branches « non transmis » et son refus d'un nul sans raison.

**`CabinetDeCarte.cs`.** Dans `Construire`, sous la date : `barre = SocleInterface.Texte(bandeau, "Lecture de la maison…", 24, 72, 1872)`, de couleur `papier`, et `sizeDelta` (1872, 26) : il tient sous le filet et dans les 100 px du bandeau. Ce n'est pas une commande : le bandeau garde ses trois boutons enfants directs. `public static string Barre(Lecture<MondeAvecMaisonLu> monde, Lecture<ComptesDeMaison> comptes)` rend, à la première règle qui s'applique :
1. monde `null` : `"Lecture de la maison…"` ;
2. monde absent : `"Maison indisponible : " + TexteDuMonde.Absence(monde.Absence)` ;
3. aucune maison du joueur : `"Aucune maison choisie"` ;
4. comptes `null`, ou présents mais d'une autre maison que `MaisonDuJoueur`, ou dont `Tick` n'égale pas `monde.Donnees.Monde.Tick` (`null` compris) : `"Comptes en attente du monde"`, sans aucun nombre ;
5. comptes absents : `DossierMaison.Indisponible(comptes.Absence)` ;
6. sinon : le nom (ou `TexteDuMonde.Absence(Absents["nom"])` s'il est nul) + `" · "` + `DossierMaison.Prelevement(Part)` + `" · "` + `DossierMaison.Grenier(Grenier)`.

`Afficher` écrit `barre.text = Barre(Partie.Monde, Partie.Comptes)` à chaque image.

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot1001-interface.xml -logFile 3d/unity/Temp/lot1001-interface.log`. `P` = la même avec `-assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot1001-pont.xml -logFile 3d/unity/Temp/lot1001-pont.log`. Chacune sort 0, sans échec ni cas ignoré, cas neufs réussis.

**SC1 — La barre égale les comptes servis au même tick (`CabinetDeCarteTests.cs`, `I`).** Cas `La_barre_egale_les_comptes_servis_au_meme_tick`. `Publier(JOUEUR, new LieuTenu(10, 0))` (monde au tick 1), puis `Poser(partie, "Comptes", …)` des comptes de `JOUEUR` nommés « Maison témoin », part 0,25, grenier `{ nourriture : 1234.5, bois : 0 }`, tick 1. `cabinet.Afficher()`. Le `Text` « Lecture de la maison… », enfant de « FORGE · Le cabinet », vaut exactement `"Maison témoin · Prélèvement : 25 % · Grenier : bois : 0 kg · nourriture : 1,23 t"` (les deux morceaux que `DossierMaisonTests` exige déjà de `Decrire`), passe `Propre`, et tient dans son cadre : `preferredWidth` ≤ 1872, `preferredHeight` ≤ 26, bas à 98 ≤ 100. Avec part `null` et grenier vide : `"Maison témoin · Prélèvement : absent · Grenier : vide"`. Contre-épreuve : une barre qui écrit la part en fraction ou le grenier dans l'ordre servi rougit le cas.

**SC2 — Une barre lue un tick plus tôt échoue (`CabinetDeCarteTests.cs`, `I`).** Cas `Une_barre_lue_un_tick_plus_tot_echoue`. Mêmes comptes, monde au tick 1 : au tick 0, au tick `null`, puis d'une autre maison (`B`) au tick 1, la barre vaut chaque fois `"Comptes en attente du monde"` et ne contient ni `25 %` ni `1,23 t`. Remis au tick 1, elle revient au texte de SC1. Comptes absents (`"refus témoin"`) : `"Comptes indisponibles : refus témoin"`. Contre-épreuve : un `Barre` qui ne compare pas le tick rougit le cas.

**SC3 — Sans maison, la barre le dit (`CabinetDeCarteTests.cs`, `I`).** Cas `Sans_maison_la_barre_le_dit`. Après `Proposer()` : `"Aucune maison choisie"`. Monde posé absent (`"service coupé"`) : `"Maison indisponible : service coupé"`. Sans monde lu : `"Lecture de la maison…"`. `SansHorlogeRecueLesCommandesDuTempsRestentInactives` compte toujours trois boutons.

**SC4 — La partie lit les comptes au même passage (`LecturePartieTests.cs`, `I`).** Cas `Les_comptes_se_lisent_avec_la_maison`. Un lecteur de comptes compte ses appels et note l'identifiant reçu. Monde sans maison : `Actualiser` laisse `Comptes` nul, zéro appel. Monde qui nomme `identifiant-servi` : un appel, avec cet identifiant, et `Comptes.Donnees.Maison.Id` l'égale. Une `LecturePartie` à quatre paramètres laisse `Comptes` nul. Contre-épreuve : lire les comptes sans maison rougit le cas.

**SC5 — Le tick servi est gardé (`ClientMaisonTests.cs`, `P`).** Cas `Le_tick_servi_est_garde_avec_les_comptes`. `Complet` avec `,"tick":31` donne `Tick == 31` et les mêmes part, grenier et flux ; `Complet` tel quel donne `Tick == null` ; `"tick":-1`, `"tick":1.5`, `"tick":"jour"` et `"tick":null` refusent la réponse, et l'absence nomme `tick`. Tous les cas existants de `ClientMaisonTests` passent sans changer.

**SC6 — Sur le vrai service, la photo et sa contre-épreuve.** La commande `PHOTO` de la Photo sort 0 avec son image et la trace `CAPTURE_1001`. `AVANCE` sort 1, sans image, et son journal dit `barre lue au tick`.

**SC7 — Les scénarios qui lisent le bandeau.** `U -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 944 -forgeCaptures 3d/unity/Temp/lot1001-944 -logFile 3d/unity/Temp/lot1001-944.log` (il juge chaque texte actif du cabinet : mot interdit, nombre sans unité) et la même avec `-forgeLot 965 -forgeCaptures 3d/unity/Temp/lot1001-965 -logFile 3d/unity/Temp/lot1001-965.log` (le bandeau ne bouge pas quand on change de mode) sortent 0, chacune avec son image. Le codeur les regarde.

**SC8 — Rien ne s'assouplit, rien d'autre ne bouge.** `I` et `P` passent en entier, dont `DossierMaisonTests` et `CommandesMaisonTests`. `git diff origin/master -- 3d/unity/Assets/Interface/Tests 3d/unity/Assets/ForgeLocal3D/Pont/Tests` ne montre que des lignes ajoutées. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Les dossiers en icônes dans la barre, le retrait du panneau « Parcourir le monde » et la réécriture de ses vérifications : sous-lots 2 et 3 de #859.
- La preuve du geste entier (`Lot859`) : sous-lot 4.
- Une nouvelle lecture quand le monde avance entre la lecture du monde et celle des comptes : la barre dit qu'elle attend, et la lecture suivante, une seconde plus tard, la remet à jour.
- La ligne du prochain geste (#860), la langue visuelle de la barre (#849).
- « Votre maison », « Terres et comptes » et les commandes de la part : inchangés.
- Le service, `jeu/`, `HorlogeDeCarte` et le texte de la date.

## Photo
La carte autour de Mistra, après trente jours à 60 % de part, comme la photo du lot 658. En haut, la barre du cabinet : « FORGE · Le cabinet », Menu, la date et la vitesse (« En pause »), les trois commandes du temps. Sous le filet doré, la ligne neuve : le nom de la maison de Mistra · « Prélèvement : 60 % » · « Grenier : … ». À gauche, le feuillet « Terres et comptes » ouvert porte les mêmes deux lignes, au même jour.

Le scénario `[ScenarioDeCapture(1001, "barre-de-mistra")]` de `Lot1001.cs`, une `static class Lot1001` avec le drapeau `-forge1001Avance`, suit ces étapes :
1. Il joue `Lot658.FlechesDuSiege(camera)` en entier : Mistra, la part à 60 %, trente ticks, le feuillet ouvert, la toile posée sur la caméra et cadrée. Il prend `Lot658.carte`, `Lot658.toile`, `CabinetDeCarte` et `HorlogeDeCarte`. La barre est le `Text` `FORGE · Le cabinet/Lecture de la maison…`, active, sinon : `barre introuvable`.
2. Il attend, avec `Lot690.Jusqua`, que `cabinet.Partie.Occupee` et `horloge.RequeteEnVol` soient faux, que `Partie.Comptes` soit présent au tick du monde lu, que `horloge.Lue.Tick` l'égale, et que la barre ne dise plus `Comptes en attente du monde`.
3. Dans la même image, sans `yield` : avec `-forge1001Avance`, il pousse un tick et l'attend (`Lot690.PousserTick(carte.port).Result`, statut 200). Puis il lit lui-même les comptes de la maison du joueur (`new ClientMaison(carte.port, TimeSpan.FromSeconds(10)).LireComptes(id)`, présents), et juge, en levant à la première faute :
   - le tick des comptes lus égale celui de `Partie.Comptes`, sinon : `barre lue au tick T, comptes servis au tick T'` ;
   - la barre égale le texte que le scénario écrit lui-même depuis ces comptes, sans appeler `CabinetDeCarte.Barre` ni `DossierMaison` : le nom, `"Prélèvement : " + part × 100 en "0.##" fr-FR + " %"`, et le grenier trié en ordinal avec `TexteDuMonde.Masse`, joints par `" · "` ; elle contient `Prélèvement : 60 %` ; sinon : `barre « … » ≠ comptes « … »` ;
   - la barre passe `TexteDuMonde.Interdit(texte, id)` et `TexteDuMonde.SansUnite`, et `Lot690.DansLeChamp(camera, barre)`.
4. Il laisse passer 10 images, relit les comptes et rejuge comme à l'étape 3, sans pousser de tick.
5. Il écrit la trace `CAPTURE_1001 barre « … » au tick T, comptes servis au tick T`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1001 -forgeCaptures 3d/unity/Temp/lot1001-photo -logFile 3d/unity/Temp/lot1001-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 1001 -forgeCaptures 3d/unity/Temp/lot1001-avance -forge1001Avance -logFile 3d/unity/Temp/lot1001-avance.log
```

La première (`PHOTO`) sort 0 avec `*--barre-de-mistra.png` : c'est la photo. La seconde (`AVANCE`) est la contre-épreuve de SC6 : la barre est restée au tick d'avant, elle sort 1, sans image. Le codeur ouvre la photo lui-même. Les PNG restent hors du dépôt. Le compte rendu donne les deux commandes, leurs sorties, la trace `CAPTURE_1001`, la ligne d'erreur de `AVANCE` et ce que montre l'image.
