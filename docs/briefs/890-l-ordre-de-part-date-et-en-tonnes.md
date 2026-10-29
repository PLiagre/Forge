# Lot #890 — L'ordre de part daté et en tonnes
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
L'ordre de part de « Votre maison » parle comme un registre : le relevé est daté, le grenier est écrit en kilos ou en tonnes, et le reçu ne donne une date que s'il est sûr de la date.

## Le joueur
Le joueur ouvre « Votre maison ». Il lit « Prélèvement : 25 % · relevé au jour 33 de 1400 », puis « Grenier : nourriture : 571 t ». Il ne voit plus « tick 32 » ni « 570982,18 kg ». Il règle sa part au curseur et confirme. Le reçu dit « Ordre reçu au jour 32 de 1400. Le monde l'applique au jour suivant. » Si l'horloge lue n'est pas encore à ce jour, le reçu dit seulement « Ordre reçu. Le monde l'applique au jour suivant. » : il ne donne jamais une date fausse. Un refus reste écrit tel que le monde l'a rendu. Une cause d'envoi manqué qui montre une adresse ou un nombre devient « déclaré absent par le monde ». Le joueur sait ce qu'il prend et ce que son grenier contient, sans traduire. C'est le sous-lot 2 de #874, lui-même sous-lot 5 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, prise en main de la carte). C'est un lot de fond de la décision du jalon : chaque journée de chantier se paie en grain pris au grenier, et ce grenier se remplit par la part.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. `/maison` sert déjà `date` (`jeu/sim/maisons_servies.py`), que `DocumentDuMonde` lit (`Annee`, `JourDeLAnnee`). `/horloge` sert le tick et la date, que `HorlogeDeCarte.Lue` garde.

## Périmètre
3d/unity/Assets/Interface/CommandesMaison.cs
3d/unity/Assets/Interface/Tests/CommandesMaisonTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot656.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot890.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot890.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/EpreuvePart.cs
pc/epreuve_part.py
jeu/ville/tests/test_epreuve_part.py
docs/briefs/890-l-ordre-de-part-date-et-en-tonnes.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot890-interface.xml -logFile 3d/unity/Temp/lot890-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté. Les tests s'écrivent d'abord, et on les voit rouges. `TexteDuMonde`, `HorlogeDeCarte` et `CabinetDeCarte` ne changent pas.

**Le relevé et le reçu (`CommandesMaison`).**
- `Decrire(doc)` rend « Prélèvement : <part> · relevé au » + `TexteDuMonde.Date(new DateDuMonde(Annee, JourDeLAnnee))` + « \nGrenier : <réserves> ». Si `doc.Annee` est nulle : `ArgumentException("Date non transmise")`.
- La part garde son écriture (« 20 % »). Chaque quantité du grenier s'écrit `clé + " : " + TexteDuMonde.Masse(kg)`, clés triées, jointes par « · » ; un grenier vide reste « vide ».
- La raison d'une part ou d'un grenier absents passe par `TexteDuMonde.Absence(raison)`, sans identifiant passé.
- `Initialiser(parent, maison, lecture, ordre, Func<HorlogeLue> horloge = null)`. Sans `horloge`, elle lit `GetComponent<HorlogeDeCarte>()?.Lue` du même objet, à chaque appel. `CabinetDeCarte` garde son appel.
- Le texte du reçu se fixe à la première image où `Ordre.Recu` paraît (une nouvelle référence), et ne bouge plus jusqu'au reçu suivant. Une horloge qui avance ensuite ne le change pas.
- Acceptée, avec une horloge lue dont `Tick == AppliqueeAuTick` : « Ordre reçu au » + `Date(horloge.Date)` + « . Le monde l'applique au jour suivant. »
- Acceptée sinon : « Ordre reçu. Le monde l'applique au jour suivant. » Une seule fois, `Debug.Log("CommandesMaison : ordre reçu après le tick " + AppliqueeAuTick + ", horloge " + (lue au tick N | non lue))`.
- Refus : « Refus : » + `Erreur`, tel quel. Absence : « Envoi non confirmé : » + `TexteDuMonde.Absence(recu.Absence)` + « \nVérifiez le monde avant tout nouvel ordre. »

**SC1 — Le relevé dit la date et les tonnes.** `INTERFACE`, cas neuf `Le_releve_dit_la_date_et_les_tonnes_et_tait_les_identifiants`. Le document vaut `{"tick":31,"id":"seigneurie-3","part":0.5,"grenier":{"nourriture":570982.179398794,"bois":0},"absents":{},"date":{"annee":1400,"jour_de_l_annee":32}}`.
- `Decrire` vaut exactement « Prélèvement : 50 % · relevé au jour 32 de 1400\nGrenier : bois : 0 kg · nourriture : 571 t ». `Interdit(texte)` et `SansUnite(texte)` sont nuls.
- Avec `"grenier":{}` : la ligne 2 vaut « Grenier : vide ».
- Avec `"part":null` et l'absence « part absent pour la maison seigneurie-3 » : le texte commence par « Prélèvement : déclaré absent par le monde · relevé au jour 32 de 1400 », avec son `LogAssert.Expect`.
- Avec `"grenier":null` et l'absence « grenier absent pour la maison bar » : la ligne 2 vaut « Grenier : grenier absent pour la maison bar ».
- Sans la clé `date` : `ArgumentException` dont le message contient « Date ».

Contre-épreuve : « tick 31 », « 570982,18 kg » ou la raison « seigneurie-3 » montrée telle quelle rougit.

**SC2 — Le reçu n'est daté qu'au tick de l'horloge.** `INTERFACE`, cas neuf `Le_recu_n_est_date_qu_a_l_horloge_du_meme_tick`. `Monter` gagne un dernier argument `Func<HorlogeLue>`, ici `() => lue`, avec `lue` modifiable. Le faux envoi rend trois fois `AccepteeAu(17)`, puis `Absente("POST /intention : 127.0.0.1:8000 injoignable")`. Un `Geste(…, "Prélèvement", "25")` par essai, « Annuler / Retour » entre deux.
1. `lue = null` : `MessageAffiche` finit par « Ordre reçu. Le monde l'applique au jour suivant. » et ne contient pas « reçu au ». `LogAssert.Expect(LogType.Log, new Regex("après le tick 17"))`.
2. `lue = new HorlogeLue(16, new DateDuMonde(1400, 17), 0)` : même texte, même journal.
3. `lue = (17, jour 18 de 1400)` : le message contient « Ordre reçu au jour 18 de 1400. Le monde l'applique au jour suivant. ». Puis `lue = (18, jour 19 de 1400)` et `Afficher()` : le message est identique, à l'octet.
4. L'absence : le message contient « Envoi non confirmé : déclaré absent par le monde\nVérifiez le monde », avec son `LogAssert.Expect`.

À chaque essai, `Interdit(MessageAffiche)` et `SansUnite(MessageAffiche)` sont nuls. Contre-épreuve : une date prise à l'horloge du tick 16, un reçu qui suit l'horloge après coup, un « tick 17 » affiché ou une cause montrée telle quelle rougit.

**SC3 — Les cas existants suivent la décision A de #856.** La constante `Document` gagne `"date":{"annee":1400,"jour_de_l_annee":10}`. Chaque assertion garde sa force :
- « tick 9 » (lignes 17 et 115) devient « relevé au jour 10 de 1400 » ; « 12 kg », « 20 % » et « non transmise » restent ;
- `Le_panneau_dit_le_tick_recu_la_raison_ou_la_cause` monte avec l'horloge `(17, jour 18 de 1400)`. « après le tick 17 » devient « Ordre reçu au jour 18 de 1400. Le monde l'applique au jour suivant. » ; « après le tick 9 » et « après le tick 18 » deviennent « reçu au jour 10 de 1400 » et « reçu au jour 19 de 1400 », toujours absents ;
- le refus « Refus : grenier insuffisant : 13.5 kg demandés, 12.0 kg disponibles » et « Envoi non confirmé : coupure témoin » restent tels quels.
Les noms des cas et les autres assertions ne changent pas. `git diff origin/master -- 3d/unity/Assets/Interface/Tests/CommandesMaisonTests.cs` ne retire que ces lignes, plus l'appel de `Monter` qui gagne un argument. Contre-épreuve : une assertion retirée sans remplaçante refuse la livraison.

**SC4 — Le juge lit la date de `/maison` et les tonnes.** Dans `pc/epreuve_part.py` :
- `_valider` exige `m["date"]`, un objet avec `annee` entier ≥ 1 et `jour_de_l_annee` entier de 1 à 366. Sinon `ValueError("date relue absente ou illisible")`.
- `_masse(kg)` recopie `TexteDuMonde.Masse` pour kg ≥ 0. Les arrondis se font sur `decimal.Decimal(x)` en `ROUND_HALF_UP`, les tonnes `t = kg / 1000` calculées en flottant d'abord, comme en C#. Les milliers de tonnes se séparent par U+00A0.
- `_panneau` lit `^Prélèvement : (NOMBRE) % · relevé au jour ([0-9]+) de ([0-9]+)(?:\n|$)`. La part est juste si la date égale `m["date"]` et le pourcentage est à 0,005 près. Chaque morceau du grenier vaut exactement `clé + " : " + _masse(kg)`. L'attendu de « panneau part » s'écrit `f"{100 * m['part']} % · relevé au jour {j} de {a}"`.

`python3 -m pytest jeu/ville/tests/test_epreuve_part.py -q` (`py -m pytest …` sur le PC) passe. Dans `test_epreuve_part.py` :
- `test_masse` (neuf) compare `_masse` à la table littérale de `TexteDuMondeTests.Masses`, sans le cas négatif, plus 570982.179398794 → « 571 t » et 115486.43624743563 → « 115 t ». `_rapport` écrit ensuite le grenier par `_masse` et la ligne 1 par la date du corps ;
- `test_rapports_et_contre_epreuve` attend « Prélèvement : 50 % · relevé au jour 32 de 1400\nGrenier : nourriture : 571 t » et « Prélèvement : 10 % · relevé au jour 32 de 1400\nGrenier : nourriture : 115 t » ;
- dans `test_ecart`, « 570982,20 » et « 570982,19 » deviennent « 572 t » et « 570 t ». S'y ajoutent « 570982,18 kg » (l'ancienne écriture) en « panneau grenier ». « tick 32 » devient « jour 33 de 1400 », et s'y ajoute « jour 32 de 1401 », tous deux en « panneau part ». « 51 % » et « illisible » restent ;
- `test_impossible` gagne `("date", "date")` (clé `date` retirée du corps relu) et `("jour", "date")` (`jour_de_l_annee` à 0) ;
- la ligne 122 de `test_references` prend la tête « Prélèvement : 50 % · relevé au jour 32 de 1400\n » ; les 23 lignes du verdict restent 23.

Contre-épreuve : un `_panneau` qui garde la tolérance en kilos, ou qui ne lit pas la date, laisse passer « 570982,18 kg » ou « jour 33 » et rougit.

**SC5 — `Lot656` et `EpreuvePart` lisent la date.**
- `EpreuvePart.cs`, ligne 166 : la marque devient « relevé au » + `TexteDuMonde.Date(fini.Result.Donnees.Monde.Date)` + « \n ». Rien d'autre ne change.
- `Lot656` : `PartPosee`, `Releve()`, `Message()` et ses champs statiques deviennent `internal`. Avant de confirmer, l'attente de la ligne 37 exige aussi `horloge.Lue?.Tick == tick + 1`, et on garde `horloge.Lue.Date` comme date du reçu.
- Le reçu attendu est « Ordre reçu au » + `Date(date du reçu)`. Après `ExigerMonde(mondeP, nRecu, …)`, la date de `mondeP` égale la date du reçu, sinon `Echec("reçu daté … , monde au …")`.
- Après le second tick : lire `/monde` (`ExigerMonde(…, nRecu + 1, …)`) et sa date D, puis attendre `horloge.Lue.Tick == nRecu + 1`. Le relevé doit contenir « 25 % · relevé au » + `Date(D)` + « \n », puis « Grenier : » + les quantités de `/maison` en `Masse`. Le message garde la date du reçu.

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 656 -forgeCaptures 3d/unity/Temp/lot890-656-photo -logFile 3d/unity/Temp/lot890-656-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 656 -forgeCaptures 3d/unity/Temp/lot890-656-sans -forge656SansConfirmation -logFile 3d/unity/Temp/lot890-656-sans.log
py pc\epreuve_part.py --sortie 3d/unity/Temp/lot890-part
py pc\epreuve_part.py --sortie 3d/unity/Temp/lot890-part-inverse --part-forte 10
```
La première commande sort 0, avec les deux images. La deuxième sort 1, avec « reçu absent ». La troisième sort 0 : son `verdict.txt` dit « ÉGALITÉ », et ses lignes « panneau part » et « panneau grenier » sont égales. La quatrième sort 1, avec l'écart « grenier ».

**SC6 — Rien d'autre ne bouge.** `INTERFACE` passe sur toute l'assemblée, et `python3 -m pytest jeu -q` passe. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes.

## Hors périmètre
- Le feuillet « Terres et comptes » (`DossierMaison`, `Lot655`, `Lot658`) : livré par #889.
- Le texte du refus, que le monde rend en kilos à point décimal : il reste tel quel.
- `CabinetDeCarte`, `HorlogeDeCarte`, `TexteDuMonde`, `OrdreConfirme`, `RecuIntention`, le service et `jeu/sim/`.
- Le résumé de l'ordre (« Fixer le prélèvement à 25 %. », « Ouvrir le grenier : 13,5 kg. »), qui reprend la saisie du joueur.
- Les légendes des lieux et des flèches (`Lot657`) : sous-lot 6 de #856.

## Photo
La photo montre la carte de 1400 et « Votre maison » de Mistra. On y voit le curseur posé à 25 %, le relevé « Prélèvement : 25 % · relevé au jour N de 1400 » et le grenier en kg ou en t. Le reçu dit « Ordre reçu au jour N−1 de 1400. Le monde l'applique au jour suivant. » Aucun tick, aucun nombre sans unité.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot890.cs`, un scénario `[ScenarioDeCapture(890, "part-datee")]`. Chaque absence échoue en nommant sa cause.
1. Jouer `Lot656.PartPosee(camera)` (`for (var e = …; e.MoveNext();) yield return null;`) : il vérifie les dates et pose la photo.
2. Dans une même image, sans `yield` : prendre `Lot656.Releve()` et `Lot656.Message()`. Avec `-forge890Tick`, ajouter d'abord « · tick » + `AppliqueeAuTick` du reçu au texte du message.
3. Exiger, sur le relevé puis sur le message :
   - le relevé commence par « Prélèvement : 25 % · relevé au jour » ; le message contient « Ordre reçu au jour » ;
   - `Interdit(texte)` nul, sinon `Echec("mot interdit « " + mot + " » : « " + texte sur une ligne + " »")` ;
   - `SansUnite(texte)` nul.
4. La trace `CAPTURE_890` donne la maison, le relevé et le message, chacun sur une ligne.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :
```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 890 -forgeCaptures 3d/unity/Temp/lot890-photo -logFile 3d/unity/Temp/lot890-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 890 -forgeCaptures 3d/unity/Temp/lot890-tick -forge890Tick -logFile 3d/unity/Temp/lot890-tick.log
```
La première sort 0, avec une image `*--part-datee.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image, avec « mot interdit » dans son journal. Le codeur ouvre l'image lui-même. Un « tick », un « 570982 », un nombre sans unité, un reçu sans date ou un panneau coupé refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, les sorties des contre-épreuves, le `verdict.txt` des deux épreuves de part et ce que montre l'image.
