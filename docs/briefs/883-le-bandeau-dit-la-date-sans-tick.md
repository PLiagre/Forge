# Lot #883 — Le bandeau dit la date sans tick
Jalon : J4 · Machine : pc · Taille prévue : 210 lignes

## But
Le bandeau du cabinet et le panneau de l'horloge disent la date du monde, « Jour 6 de 1400 », puis la vitesse ou la pause, sans jamais montrer de tick.

## Le joueur
Le joueur ouvre la carte. En haut, le bandeau lui dit « Jour 34 de 1400 » et, dessous, « 1 jour par seconde » ou « En pause ». Il met en pause, accélère, ralentit : la date avance ou s'arrête, sans numéro de machine à côté. Il sent qu'il lit le calendrier d'un registre de 1400, pas un compteur. C'est le sous-lot 1 de #872, lui-même sous-lot 3 de #856 (« La fiche parle en noms », `CAP.md`, jalon 4, prise en main de la carte : « la date au lieu du tick »). C'est un lot de fond du geste **passer de la carte à sa ville d'un geste** : avant de descendre, le joueur lit la date et règle le temps depuis le bandeau.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. Ni `jeu/`, ni `jeu/sim/MODELE.md`, ni le service ne sont touchés. `/horloge` sert déjà `tick`, `date` et `jours_par_seconde`. Le tick reste lu dans `HorlogeDeCarte.Lue.Tick`, car `DossierMaison`, `CabinetDeCarte` (le reçu daté), `Lot655`, `Lot656` et `Lot730` s'en servent. Il n'est simplement plus écrit à l'écran.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/HorlogeDeCarte.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/HorlogeDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot525.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot883.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot883.cs.meta
docs/briefs/883-le-bandeau-dit-la-date-sans-tick.md

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `PONT` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot883-pont.xml -logFile 3d/unity/Temp/lot883-pont.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté (zéro cas est un échec). Les tests s'écrivent d'abord, et on les voit rouges contre l'ancien `Decrire`. Le juge est `Forge.Pont.TexteDuMonde.Interdit` (#870), qui ne change pas.

**Le changement.** `HorlogeDeCarte.Decrire(HorlogeLue h)` écrit « Jour » + jour de l'année + « de » + année, avec `Entier` comme aujourd'hui, puis « \n » et la ligne de vitesse inchangée. Le morceau « · tick N » disparaît. Rien d'autre ne change dans `HorlogeDeCarte` : ni `Lue`, ni la lecture, ni les boutons, ni l'écriture de la vitesse. Le commentaire d'en-tête dit que le tick est lu mais pas affiché. `CabinetDeCarte` ne change pas : son bandeau affiche déjà `HorlogeDeCarte.Decrire(horloge.Lue)` tel quel.

**SC1 — Le panneau dit la date servie, sans tick (réécriture décidée en A sur #856).** `PONT`. Dans `HorlogeDeCarteTests`, on garde le même relevé et la même égalité exacte, et aucune vérification n'est retirée :
- `Le_panneau_dit_l_horloge_servie_et_rien_d_autre` : les trois attendus deviennent « Jour 6 de 1400\n2.5 jours par seconde », « Jour 100 de 1400\n1 jour par seconde » et « Jour 100 de 1400\nEn pause ». Le tick, qui n'est plus dans le texte, se vérifie sur la lecture. Après chaque égalité, on ajoute `Assert.AreEqual(5L, horloge.Lue.Tick)`, puis `7L` et `7L`, et `Assert.IsNull(TexteDuMonde.Interdit(horloge.TexteAffiche), horloge.TexteAffiche)`. Le saut de 5 à 7 ticks et de 6 à 100 jours reste en place : le panneau recopie, il ne compte pas.
- `Sans_service_le_panneau_le_dit_et_ne_regle_rien` : le dernier attendu devient « Jour 6 de 1400\n2.5 jours par seconde ». On ajoute `Assert.AreEqual(5L, horloge.Lue.Tick)` et le même `Interdit` nul.

Contre-épreuve : l'ancien `Decrire`, avec « · tick », rougit ces deux cas. Le compte rendu en donne le rouge.

**SC2 — La date ne dépend pas du tick.** `PONT`, cas ajouté `La_date_ne_dit_jamais_le_tick` :
- `Decrire(new HorlogeLue(5, new DateDuMonde(1400, 6), 2.5))` et `Decrire(new HorlogeLue(9999, new DateDuMonde(1400, 6), 2.5))` valent tous deux exactement « Jour 6 de 1400\n2.5 jours par seconde » ;
- `Decrire(new HorlogeLue(30, new DateDuMonde(1401, 365), 0))` vaut « Jour 365 de 1401\nEn pause » ;
- `TexteDuMonde.Interdit` est nul pour chacun, et aucun ne contient « 9999 » ;
- le juge mord : `TexteDuMonde.Interdit("Jour 6 de 1400 · tick 5\n2.5 jours par seconde")` vaut « tick ».

Contre-épreuve : un `Decrire` qui garde le tick, ou qui écrit la date d'après le tick, rougit.

**SC3 — `Lot525` juge son texte.** Dans `Lot525`, chaque endroit qui compare `h.TexteAffiche` à `HorlogeDeCarte.Decrire(h.Lue)` (deux dans `EnMarche`, un dans `EnPause`) exige aussi `TexteDuMonde.Interdit(h.TexteAffiche) == null`. Sinon : `InvalidOperationException("mot interdit « " + mot + " » dans l'horloge : « " + texte + " »")`. Pour `Lot883`, les deux scénarios passent de `static` à `internal static`, sans être renommés. Une propriété `internal static HorlogeDeCarte Horloge => horloge;` est ajoutée. Aucun `throw` existant ne disparaît. Commande :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 525 -forgeCaptures 3d/unity/Temp/lot883-525 -logFile 3d/unity/Temp/lot883-525.log
```

Elle sort 0 avec ses deux images. `CAPTURE_525 en marche` et `CAPTURE_525 en pause` montrent « Jour N de 1400 | … » sans « tick ». Contre-épreuve : le `-forge883Tick` de la Photo rougit le même jugement.

**SC4 — Le bandeau du cabinet, à l'écran.** Voir la Photo : `-forgeLot 883` sort 0 avec deux images, et `-forge883Tick` sort 1.

**SC5 — Rien d'autre ne bouge.** `PONT` passe sur toute l'assemblée. Dans `git diff origin/master -- 3d/unity/Assets/ForgeLocal3D/Pont/Tests/HorlogeDeCarteTests.cs`, les seules lignes retirées sont les quatre qui contiennent « · tick ». `grep -c "Assert\." ` sur ce fichier ne baisse pas. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master`, fichiers neufs et brief compris, totalise moins de 300 lignes. Contre-épreuve : un cas existant retouché ailleurs qu'à ces quatre lignes, ou un fichier hors du Périmètre, refuse la livraison.

## Hors périmètre
Restent hors du lot :
- l'écriture de la vitesse (« 2.5 jours par seconde », avec un point) et le jugement `SansUnite` du bandeau : la barre du haut (#859) ;
- `CabinetDeCarte`, `CabinetDeCarteTests`, `Lot730` (qui compare déjà à `Decrire`, sans littéral), `Lot655` et `Lot656` ;
- la fiche de survol (`FicheDeCellule`, `Lot526`, `pc/epreuve_carte.py`) : sous-lot 2 de #872 ;
- les dossiers et le reste de #856 ; le service et `jeu/`.

## Photo
Deux images de la carte de 1400 entière, avec le cabinet par-dessus. En haut, le bandeau « FORGE · Le cabinet » dit « Jour N de 1400 » puis « 1 jour par seconde », le bouton du milieu affichant « Pause ». La seconde image montre la même carte : même date figée, « En pause », bouton « Reprendre ». Aucun « tick » n'apparaît à l'écran.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot883.cs`, avec deux scénarios. Il réutilise ceux de `Lot525` et les aides `internal` de `Lot690`, sans les changer. Chaque absence échoue en nommant sa cause.
1. `[ScenarioDeCapture(883, "01-en-marche")]` : jouer `Lot525.EnMarche(camera)` (`for (var e = …; e.MoveNext();) yield return null;`). Prendre `h = Lot525.Horloge` et sa `CarteDessinee`, puis la toile enfant « Cabinet ». Sinon, `Echec("la carte n'a pas de cabinet")`. Poser le cabinet sur la caméra comme `Lot730.Cabinet` :
   - `camera.rect` sur toute l'image ;
   - la caméra décalée vers l'est de `(1 - largeur) * orthographicSize * aspect` ;
   - la toile en `ScreenSpaceCamera` sur `camera`, `planeDistance = nearClipPlane + 0.2f`.
   Attendre dix images, puis `Juger(camera, h, "en marche")`. Exiger aussi que la seconde ligne finisse par « par seconde ».
2. `[ScenarioDeCapture(883, "02-en-pause")]` : jouer `Lot525.EnPause(camera)`, attendre dix images, puis `Juger(camera, h, "en pause")`. Exiger aussi la seconde ligne « En pause » et le libellé « Reprendre » sur le bouton « Pause / Reprendre » du bandeau.
3. `Juger` prend le `Text` nommé « Lecture de la date… » sous « Cabinet », sinon il échoue. Avec `-forge883Tick` sur la ligne de commande (`Environment.GetCommandLineArgs()`), il y écrit d'abord l'ancien texte, dans la même image : `Decrire(h.Lue).Replace("\n", " · tick " + h.Lue.Tick + "\n")`. Puis, dans l'ordre :
   - `TexteDuMonde.Interdit(bandeau.text)` est nul, sinon `Echec(moment + " : mot interdit « " + mot + " » dans le bandeau : « " + texte + " »")` ;
   - `bandeau.text == h.TexteAffiche == HorlogeDeCarte.Decrire(h.Lue)` ;
   - la première ligne vaut « Jour » + `h.Lue.Date.JourDeLAnnee` + « de » + `h.Lue.Date.Annee` ;
   - `Lot690.DansLeChamp(camera, bandeau)`.
4. La trace `CAPTURE_883 <moment> : <texte du bandeau, « \n » remplacé par « | »>`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 883 -forgeCaptures 3d/unity/Temp/lot883-photo -logFile 3d/unity/Temp/lot883-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 883 -forgeCaptures 3d/unity/Temp/lot883-tick -forge883Tick -logFile 3d/unity/Temp/lot883-tick.log
```

La première sort 0 avec `*--01-en-marche.png` et `*--02-en-pause.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans image. Son journal dit « en marche : mot interdit « tick » dans le bandeau ». Le codeur ouvre les deux images lui-même. Un « tick » visible, un bandeau coupé ou absent, une date en attente ou une date qui bouge en pause refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montrent les deux images.
