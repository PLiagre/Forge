# Lot #875 — Les légendes des lieux et des flèches en noms
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Sur la carte, les légendes des lieux et des flèches nomment chaque terre par son bourg et chaque lieu par son nom servi, datent le relevé au jour servi et écrivent ce qui monte au siège et au suzerain en kilos ou en tonnes.

## Le joueur
Le joueur regarde sa carte après trente jours de prélèvement. Sous « Blanc : vos lieux… », il lit « Mistra · relevé au jour 32 de 1400 » au lieu de « Cellule 10340 au tick 31 ». Dans la légende des flèches, il lit « Mistra · <nom du lieu> → Mistra : 218 t » au lieu de « Lieu 10340-1 → Mistra : 218 086 kg », puis « Mistra → Constantinople : 76,8 t de dû ». Un nom que le monde ne sert pas se dit absent (« lieu sans nom (nom non fourni) ») : rien n'est inventé. Il sait, d'un coup d'œil, quel lieu nourrit son siège et ce qu'il doit à son suzerain, sans traduire un numéro. C'est le sous-lot 6 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, prise en main de la carte). C'est un lot de fond de la décision du jalon : chaque journée de chantier se paie en grain pris au grenier, et ce grain monte des lieux par la part que ces flèches montrent.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. `/lieu` sert déjà la date (`Lieu.Annee`, `Lieu.JourDeLAnnee`) et le nom de chaque lieu (`LieuPlace.Nom`, `AbsenceDuNom`, lot #871).

## Périmètre
3d/unity/Assets/Interface/LieuxDeCarte.cs
3d/unity/Assets/Interface/FlechesDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot657.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot658.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot875.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot875.cs.meta
docs/briefs/875-les-legendes-des-lieux-et-des-fleches-en-noms.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot875-interface.xml -logFile 3d/unity/Temp/lot875-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté. Les tests s'écrivent d'abord, et on les voit rouges. `TexteDuMonde`, `NomsDesTerres`, `ClientLieu`, `ReperesDeDepart` et `CabinetDeCarte` ne changent pas.

**Les mots (`LieuxDeCarte`, publics et statiques, `c` = `cell_id` en invariant).**
- `Bourg(Lieu lieu)` : le `Nom` du `LieuPlace` de rang 0, où qu'il soit dans la liste ; sinon « Bourg sans nom (» + `TexteDuMonde.Absence(raison, c)` + «) », la raison étant `AbsenceDuNom`, ou « bourg non servi » sans lieu de rang 0.
- `Tenue(Lieu lieu, LieuPlace place)` : `Bourg(lieu)` au rang 0 ; sinon `Bourg(lieu)` + « · » + (`place.Nom` ou « lieu sans nom (» + `Absence(place.AbsenceDuNom, c)` + «) »).
- Ligne d'une terre lue : « \n » + `Bourg` + « · relevé au » + `TexteDuMonde.Date(new DateDuMonde(lieu.Annee, lieu.JourDeLAnnee))`.
- Terre sans lieux (lecture absente, `Lieux` nul ou vide) : « \nTerre sans lieux lus : » + `Absence(raison, c)` (« liste vide » pour la liste vide).
- Lieu sans point, sans maître ou sans flux : « \n » + `Tenue` + « : point absent », « : maître absent » ou « : » + `Absence(AbsenceDesFlux, c)`.

**Les flèches (`FlechesDeCarte`).** `Kg` disparaît ; chaque masse s'écrit `TexteDuMonde.Masse`. `ENTETE` ne change pas.
- Lieu : « \n » + `LieuxDeCarte.Tenue(lu.Lieu, l)` + « → » + `siege.Nom` + « : » + masse, ou l'absence des flux par `Absence`, ou « point absent ».
- Siège : « \n » + `siege.Nom` + « : » + masse + « prélevés sur place, sans flèche ».
- Terre sans lieux : « \nAucune flèche d'une terre sans lieux lus : » + `Absence(raison, c)`.
- Dû : « \n » + `siege.Nom` + « → » + `haut.Nom` + « : » + masse + « de dû ». Causes : « lecture refusée : » + `Absence(j.Absence, maison)` ; « suzerain non lu : » + `Absence(s.Absence, suzerain)` (l'identifiant du suzerain ne paraît plus) ; `Raison(m)` passe par `Absence`.
- Les noms des objets (« Lieu 10-1 », « Flèche 10-1 », `DU`) ne changent pas.

**SC1 — Les cas existants suivent la décision A de #856.** Dans `CabinetDeCarteTests` :
- `NomDe(cell, rang)` (neuf) rend Alba (10, 0), Brivas (10, 1), Cerda (10, 2), Dara (20, 0), Elne (20, 1), et lève sinon. `Place` prend `cell` en premier argument et pose `nom: NomDe(cell, rang)`. Chaque `new LieuPlace` des lignes 95 et 120–121 pose le sien. `Cellule` sert le jour `tick + 1` de 1400.
- Lignes 81–85 : « Cellule 10 au tick 4 » et « Cellule 20 au tick 4 » deviennent « \nAlba · relevé au jour 5 de 1400 » et « \nDara · relevé au jour 5 de 1400 » ; « au tick 11 », « au tick 12 » deviennent « relevé au jour 12 de 1400 », « relevé au jour 13 de 1400 ».
- Ligne 95 : « Cellule 10, rang 0 : flux non fournis » devient « \nAlba : flux non fournis » ; « au tick 6 » et « au tick 7 » deviennent « relevé au jour 7 de 1400 » et « relevé au jour 8 de 1400 ».
- Lignes 105–107 : chaque texte attendu prend la tête « \nTerre sans lieux lus : ». Lignes 108–109 : « Cellule 10, rang 1 : » devient « \nAlba · Brivas : ».
- Ligne 125 : « \nSiège : 1,23 t prélevés sur place, sans flèche », « \nAlba · Brivas → Siège : » + `Masse(a)`, « \nDara → Siège : » + `Masse(b)` ; `Not.Contain("10-2")` reste, et `Not.Contain("Cerda")` s'ajoute.
- Ligne 127 : « \nAlba · Brivas → Siège : 0 kg », « \nDara → Siège : flux non fournis ». Ligne 128 : les deux causes prennent la tête « \nAucune flèche d'une terre sans lieux lus : » ; « Lieu 10-1 » et « Lieu 20-0 » deviennent « Brivas » et « Dara ». Ligne 129 : « Lieu 10-1 » devient « Brivas ».
- Ligne 137 : « \nSiège → Capitale : 76,8 t de dû ». Ligne 142 : « kg de dû » devient « de dû », sinon l'assertion ne peut plus rougir.

Les noms des cas et les autres assertions ne changent pas. `git diff origin/master -- 3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs` ne retire que ces lignes et les aides `Place`, `Cellule`, `Reponse`, `Complet`. Contre-épreuve : une assertion retirée sans remplaçante refuse la livraison.

**SC2 — La légende des lieux parle en noms.** `INTERFACE`, cas neuf `La_legende_des_lieux_nomme_date_et_declare_l_absent`. Tenus : (10, 0), (10, 1), (10, 2), (20, 0), (30, 0), tick 4. Cellule 10 : rang 0 sans nom avec `absenceDuNom` « nom absent pour 10-0 », rang 1 « Brivas » sans flux (« flux absents au tick 4 »), rang 2 sans nom ni raison, sans point. Cellule 20 : Dara. Cellule 30 : `Absent("lieu 30 : délai dépassé")`.
- La légende contient exactement « \nBourg sans nom (déclaré absent par le monde) · relevé au jour 5 de 1400 », « \nBourg sans nom (déclaré absent par le monde) · Brivas : déclaré absent par le monde », « \nBourg sans nom (déclaré absent par le monde) · lieu sans nom (nom non fourni) : point absent », « \nDara · relevé au jour 5 de 1400 » et « \nTerre sans lieux lus : déclaré absent par le monde », avec leurs `LogAssert.Expect`.
- `Interdit(t, JOUEUR, B, C)` et `SansUnite(t)` sont nuls ; « Lieu 10-1 » existe sous `RACINE`.

Contre-épreuve : « Cellule 10 », « tick », « 10-0 » ou un nom inventé à la place de l'absence rougit.

**SC3 — La légende des flèches parle en noms et en tonnes.** `INTERFACE`, cas neuf `La_legende_des_fleches_nomme_et_pese`. Cellule 10 : rang 0 Alba (siège, 1 234,4 kg), rang 1 Brivas (570 982,18 kg), rang 2 au joueur sans nom ni raison (90 000 kg). Dû : 76 788,18 kg vers `Capitale`, puis `Lecture.Absent("maison grande-15 : délai dépassé")` pour le suzerain `grande-15`.
- La légende contient « \nSiège : 1,23 t prélevés sur place, sans flèche », « \nAlba · Brivas → Siège : 571 t », « \nAlba · lieu sans nom (nom non fourni) → Siège : 90,0 t », « \nSiège → Capitale : 76,8 t de dû », puis « \nDû au suzerain : suzerain non lu : déclaré absent par le monde ».
- À chaque étape, `Interdit(t, JOUEUR, B, C, "grande-15")` et `SansUnite(t)` sont nuls ; `Fleches()` garde « Flèche 10-1 » et « Flèche 10-2 ».

Contre-épreuve : « 570 982 kg », « Lieu 10-1 » ou « suzerain grande-15 » rougit.

**SC4 — `Lot657` et `Lot658` lisent les noms et les dates.**
- `Lot657.Lire` garde, pour chaque terre, la ligne « \n » + nom du rang 0 + « · relevé au » + `Date(Annee, JourDeLAnnee)` du `/lieu` relu. Un nom absent : `Echec("bourg sans nom servi")`. `Pret` et `Controler` (lignes 55 et 71) attendent ces lignes. `Controler` exige `Interdit(legende.text, maison)` et `SansUnite(legende.text)` nuls.
- `Lot658.Lire` garde, pour chaque lieu, sa tenue (le nom du bourg, puis « · » + son nom hors du rang 0) ; un nom absent : `Echec`. Ligne 41 : « \n » + tenue + « → Mistra : » + `Masse(kg)`, puis `Masse` pour le siège et le dû. Ligne 43 : les lignes de terre comme dans `Lot657`. Le feuillet (ligne 42) reste.
- `Lot658` : `FlechesDuSiege`, `carte` et `toile` deviennent `internal`.

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 657 -forgeCaptures 3d/unity/Temp/lot875-657 -logFile 3d/unity/Temp/lot875-657.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 657 -forgeCaptures 3d/unity/Temp/lot875-657-retire -forge657RetirerLieu -logFile 3d/unity/Temp/lot875-657-retire.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 658 -forgeCaptures 3d/unity/Temp/lot875-658 -logFile 3d/unity/Temp/lot875-658.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 658 -forgeCaptures 3d/unity/Temp/lot875-658-retire -forge658RetirerDu -logFile 3d/unity/Temp/lot875-658-retire.log
```
La première et la troisième sortent 0, avec leur image. La deuxième sort 1 (« couple manquant »), la quatrième sort 1 (« flèche manquante »).

**SC5 — Rien d'autre ne bouge.** `INTERFACE` passe sur toute l'assemblée, et `python3 -m pytest jeu -q` passe. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

## Hors périmètre
- Les noms des objets Unity (« Lieu 10-1 », « Flèche 10-1 », « Flèche du dû ») et `ReperesDeDepart.NomDuLieu`.
- Les en-têtes des deux légendes, leur place et leur taille ; l'épaisseur des flèches.
- Le feuillet « Terres et comptes » et l'ordre de part : livrés par #889 et #890.
- La fiche de survol, le bandeau, le plan, les chantiers, les voisins : sous-lots 3 et 7 de #856.
- Un nom de terre retrouvé quand sa lecture échoue : la ligne dit l'absence.
- `TexteDuMonde`, `NomsDesTerres`, `ClientLieu`, `CabinetDeCarte`, le service et `jeu/sim/`.

## Photo
La photo montre la carte de 1400 autour de Mistra après trente jours à 60 % : les disques des lieux, les flèches orange vers Mistra, la flèche violette vers Constantinople, le feuillet « Terres et comptes » ouvert. La légende des lieux dit « Mistra · relevé au jour N de 1400 » ; celle des flèches dit « Mistra · <lieu> → Mistra : … t » et « Mistra → Constantinople : … t de dû ». Aucun tick, aucun numéro de terre, aucun nombre sans unité.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot875.cs`, un scénario `[ScenarioDeCapture(875, "legendes-en-noms")]`. Chaque absence échoue en nommant sa cause.
1. Jouer `Lot658.FlechesDuSiege(camera)` (`for (var e = …; e.MoveNext();) yield return null;`) : il vérifie les lignes, les flèches, le feuillet, et pose la photo.
2. Dans une même image, sans `yield` : prendre les textes « Légende des lieux » et « Légende des flèches » sous `Lot658.toile`. Avec `-forge875Identifiant`, ajouter d'abord « \nLieu » + le nom du premier objet sous `FlechesDeCarte.RACINE` (« Flèche 10340-1 » donne « 10340-1 ») au texte des flèches.
3. Exiger, sur chaque texte : la légende des lieux contient « · relevé au jour » ; celle des flèches contient « → Mistra : » et « de dû » ; `Interdit(texte)` nul, sinon `Echec("mot interdit « " + mot + " » : « " + texte sur une ligne + " »")` ; `SansUnite(texte)` nul.
4. La trace `CAPTURE_875` donne les deux légendes, chacune sur une ligne.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 875 -forgeCaptures 3d/unity/Temp/lot875-photo -logFile 3d/unity/Temp/lot875-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 875 -forgeCaptures 3d/unity/Temp/lot875-identifiant -forge875Identifiant -logFile 3d/unity/Temp/lot875-identifiant.log
```
La première sort 0, avec une image `*--legendes-en-noms.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image, avec « mot interdit » dans son journal. Le codeur ouvre l'image lui-même. Un « tick », une « Cellule », un « 10340-1 », un nombre sans unité, une légende coupée ou cachée refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, les sorties des contre-épreuves et ce que montre l'image.
