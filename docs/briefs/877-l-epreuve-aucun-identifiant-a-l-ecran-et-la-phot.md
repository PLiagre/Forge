# Lot #877 — L'épreuve, aucun identifiant à l'écran, et la photo
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Sur le vrai service, une épreuve qui peut échouer garantit qu'avec la Morée gardée, aucun texte affiché par le cabinet ou par la fiche ne montre un identifiant ou un nombre sans unité, et qu'aucune valeur servie n'a disparu des dossiers.

## Le joueur
Le joueur choisit la Morée et la garde d'un clic. Il lit son dossier, « Terres et comptes », l'infobulle de survol et les légendes en noms, en dates et en unités : « Mistra · Maison : Paléologue », « Mistra · Palaia Petra », « jour 32 de 1400 », « Prélevé : 43,7 t ». Il n'y lit jamais « Cellule 10340 », « rang 1 », « 10340-1 », « seigneurie-3 » ni « tick 31 ». Chaque chiffre que ces dossiers montraient avant la réécriture y est encore : il compare son grenier, sa part et ses lieux avant de descendre dans sa capitale, comme dans un registre. C'est la preuve du geste « La fiche parle en noms, pas en identifiants » du jalon 4 (`CAP.md`, lot 18). C'est le sous-lot 8 de #856, après #872 à #876, #928 et #929, tous livrés. Il ne change rien à l'écran : il prouve l'écran.

## Règle du monde
Sans objet : c'est un lot d'épreuve. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni le service, ni une vue ne sont touchés.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot877.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot877.cs.meta
docs/briefs/877-l-epreuve-aucun-identifiant-a-l-ecran-et-la-phot.md

Tout autre chemin est interdit. C'est vrai en particulier pour `TexteDuMonde.cs`, les dossiers d'`Assets/Interface/`, `FicheDeCellule.cs` et les autres scénarios (`Lot526`, `Lot549`, `Lot655`, `Lot690`, `Lot855`, `Lot873`…). Le scénario appelle leurs membres `internal` sans les modifier. Le `.meta` a deux lignes (`fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt).

## Conditions de succès
On lance sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Les trois commandes de la Photo s'appellent `PHOTO`, `IDENTIFIANT` et `SANS_VALEUR`.

Mesuré au service, graine 0, après le choix au tick 30 et un jour poussé, donc au tick 31, le « jour 32 de 1400 ». Ce sont des repères pour le codeur : le scénario lit tout au service et n'écrit aucun de ces nombres en dur.
- La Morée est la terre 10340, son bourg « Mistra ». Elle a 15 lieux, de « Mistra » (rang 0) à « Nea Rachi » (rang 14), et 81 514 habitants. Sa faim est de 0 jour, sa dette de 0 kg.
- Les maîtres de ses lieux : `seigneurie-3` (rangs 0 à 3), puis `plausible-10340-4`, `-7`, `-10` et `-13`.
- La maison du joueur est `seigneurie-3`, « Paléologue », avec 4 lieux tenus. Son suzerain est `grande-15`, « Paléologue », au siège de Constantinople (terre 10374).
- Ses comptes : part 3 %, grenier « nourriture : 35,8 t ». Prélevé 43,7 t, reçu 36,1 t, dû envoyé 4,01 t, consommé en route 1,25 t, rendu 0 kg. Départs « 0 personne », arrivées « 145 personnes ». Les salaires ne sont pas servis.

**SC1 — Au même tick, tout texte affiché parle en noms et dit chaque valeur servie.** `PHOTO` sort 0 avec son image. Le scénario `Lot877` est décrit sous Photo. Son jugement, `Juger(bool drapeaux)`, ne fait aucun `yield` et lève une `InvalidOperationException` à la première faute.

1. **Les références.** Elles sont lues à part, après le dernier jour poussé :
   - `/lieu?cell=<Morée>` par une `LectureDossier.Locale(port)` neuve, en `DocumentDuMonde` (noms des maîtres, surfaces, stocks) ;
   - le même lieu par `ClientLieu` ;
   - les comptes du joueur, puis ceux de son suzerain, par `ClientMaison.LireComptes` ;
   - `/lieu` de chaque terre tenue, pour les noms des tenues ;
   - le monde par `Lot690.LireMonde`.
   Les tâches sont attendues par `Lot690.Attendre`. Le tick du document de lieu, celui du monde lu, `horloge.Lue.Tick` et `fiche.MondeLu.Tick` valent tous `fin` (le tick après le jour poussé). Sinon le scénario échoue en citant les ticks.
2. **Les identifiants**, en culture invariante :
   - terres : la Morée, chaque `cell_id` tenu, le siège du joueur et celui du suzerain ;
   - lieux : `<cell>-<rang>` pour chaque lieu de la Morée ;
   - maisons : l'id du joueur, celui du suzerain et chaque `maitre` non nul de la Morée.
3. **Les textes nommés**, jugés dans cet ordre :
   - « Territoire conservé » : le `Text` sous `Territoire conservé/Lecture du territoire`, comme dans `Lot873` ;
   - « Terres et comptes » : le `Text` du panneau à `ScrollRect`, comme dans `Lot655` ;
   - « Votre maison » : le `Text` enfant direct du panneau, qui commence par le nom de la maison suivi de « \nSiège : » ;
   - « Commandes de maison » : le `Text` sous `Votre maison/Commandes de maison` qui commence par « Prélèvement : » ;
   - « Légende des lieux » et « Légende des flèches », par leur nom ;
   - « Infobulle » : le `Text` sous `Infobulle`, égal à `InfobulleDeTerre.TexteAffiche` ;
   - « Fiche de survol » : `fiche.TexteAffiche`. Le cabinet éteint la toile de la fiche, alors on juge sa chaîne.
   Viennent ensuite tous les autres `Text` de `Cabinet` actifs dans la hiérarchie (`GetComponentsInChildren<Text>(false)`), nommés par leur chemin sous `Cabinet`. Un texte nommé absent ou inactif fait échouer le scénario. Une toile avec moins de 8 `Text` actifs aussi : un échantillon vide échoue.
4. **Les deux juges, sur chaque texte d'abord.** `TexteDuMonde.Interdit(texte, ids)` doit être nul, sinon le scénario lève `mot interdit « <mot> » dans « <nom> » : « <première ligne> »`. Puis `TexteDuMonde.SansUnite(texte)` doit être nul, sinon il lève `nombre sans unité « <nombre> » dans « <nom> » : « <première ligne> »`. Aucun texte n'est exempté. Un texte hors des dossiers qui échoue se signale au compte rendu, et le lot reste bloqué : on ne corrige pas un écran hors du Périmètre.
5. **Ensuite, les valeurs.** Une valeur se lit si une ligne du texte commence par elle. Sinon le scénario lève `valeur absente « <valeur> » dans « <nom> »`. Les masses passent par `TexteDuMonde.Masse`, les nombres par `TexteDuMonde.Nombre`, les jours par `Jours`, les dates par `Date`. La surface et la part s'écrivent `0.##` en `fr-FR`, comme dans les dossiers, car `TexteDuMonde` n'a pas d'écriture pour elles.
   - **Territoire conservé.** Le texte est coupé en parts aux lignes vides (`"\n\n"`).
     - En-tête : `<bourg> · Maison : <nom du maître du rang 0>`, puis la date, puis `<Nombre(population)> habitants dans le territoire`.
     - Chaque lieu servi a exactement une part, dont la première ligne est son nom. Sinon le scénario lève `lieu absent « <nom> » dans « Territoire conservé »`.
     - Cette part dit : `<Nombre(population)> habitants · <surface> km²`, `Maison : <nom>` (ou `Sans maître`), `<clé> : <Masse>` pour chaque stock, `Sur 30 jours : <Masse(preleve_kg)> prélevés` et `<n> personne(s) partie(s) · <n> personne(s) arrivée(s)`. Le nom d'une faute y est « Territoire conservé · <lieu> ».
   - **Terres et comptes.**
     - Une ligne commence par `<nom> · ` et contient ` · <date>`.
     - `Siège : <nom>`, `Suzerain : <nom du suzerain>`, `Prélèvement : <part> %`, et `Grenier : <clé> : <Masse>` (joints par « · »).
     - Une ligne par tenue, égale à `<bourg>` au rang 0, et à `<bourg> · <lieu>` sinon.
     - `Prélevé : `, `Reçu : `, `Dû envoyé : `, `Consommé en route : ` et `Rendu : ` suivis de leur masse.
     - `Départs : <n> personne(s)` et `Arrivées : <n> personne(s)`.
     - `Salaires : <Masse>` seulement si le service sert les salaires.
   - **Votre maison** : `<nom>`, `Siège : <siège>`, puis `<Nombre(n)> lieux tenus · relevé au <date>`.
   - **Commandes de maison** : `Prélèvement : <part> % · relevé au <date>`, puis `Grenier : …`.
   - **Légende des lieux** : `<bourg> · relevé au <date>` pour chaque terre tenue.
   - **Légende des flèches.** Le siège : `<siège> : <Masse> prélevés sur place`. Chaque autre lieu de la Morée tenu par le joueur : `<bourg> · <lieu> → <siège> : <Masse(preleve)>`. Enfin `<siège> → <siège du suzerain> : <Masse(dû envoyé)> de dû`.
   - **Infobulle** : ses trois lignes sont les trois lignes d'en-tête du territoire.
   - **Fiche de survol** : `Lot526.Juger(fiche, <bourg>)`.

La trace `CAPTURE_877` donne le nombre de textes jugés, le nombre de valeurs lues et la première ligne de chaque texte nommé.

**SC2 — Contre-épreuve : un identifiant dans le dossier.** Avec `-forge877Identifiant`, `Juger(true)` ajoute « \n<Morée>-1 » (soit « 10340-1 ») au texte affiché de « Territoire conservé », juste avant de juger, dans la même image. `IDENTIFIANT` sort 1, sans image. Son journal dit `mot interdit « 10340-1 » dans « Territoire conservé »`.

**SC3 — Contre-épreuve : une valeur retirée.** Avec `-forge877SansValeur`, `Juger(true)` retire du texte affiché de « Terres et comptes » sa ligne qui commence par « Prélevé : », de la même façon. Les juges passent, puis les valeurs échouent : `SANS_VALEUR` sort 1, sans image, et son journal dit `valeur absente « Prélevé : 43,7 t » dans « Terres et comptes »` (le nombre est celui que sert `/maison`).

**SC4 — Rien ne s'assouplit, rien d'autre ne bouge.**
- `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot877-interface.xml -logFile 3d/unity/Temp/lot877-interface.log` sort 0. Pareil avec `Forge.Pont.Tests` (`lot877-pont`). Le XML ne doit avoir ni échec ni cas ignoré, et au moins un cas.
- Le scénario appelle `TexteDuMonde.Interdit`, `TexteDuMonde.SansUnite` et `Lot526.Juger`. Il n'en recopie aucun.
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre.
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Corriger un écran qui échoue, changer `TexteDuMonde`, ses juges ou un dossier.
- Les modes de carte et la légende qui passe sous le feuillet (#858), la barre du haut (#859).
- La ville, `PanneauLieu`, les outils de la capitale.
- `pc/epreuve_carte.py` et l'épreuve de la carte (#928, #929).

## Photo
La carte de 1400 sur la Morée. À droite, le dossier « Territoire conservé » commence par « Mistra · Maison : Paléologue », puis « jour 32 de 1400 ». À gauche, le feuillet « Terres et comptes » est ouvert en entier : « Paléologue · seigneurie · jour 32 de 1400 », « Prélèvement : 3 % », « Grenier : nourriture : 35,8 t », les quatre tenues en noms, et la circulation en tonnes. On ne voit nulle part un identifiant ou un tick.

Le scénario `[ScenarioDeCapture(877, "moree-et-ses-comptes")]` de `Lot877.cs` suit ces étapes :
1. `Lot549.Ouvrir`. Il passe `SurvolDeCarte`, `ParcoursDeCarte` et `InfobulleDeTerre` en `automatique`. Il attend `Lot690.LecturePrete`, puis `horloge.Lue`, et exige `JoursParSeconde == 0`.
2. Il prend la fiche de départ au siège « Mistra » (« Despotat de Morée », une seule). Il lit `/lieu` de la Morée pour avoir son bourg et son point. Il zoome de 12 crans et centre la vue comme `Lot855`. Au point P, `HorsCarte(P)` doit être faux.
3. Il garde la Morée d'un clic : `Noter` à l'appui, au déplacement et au relâché en P, sans image entre les trois, comme `Lot855.Toucher`. Il exige `Retenue.CellId` = la Morée.
4. Il choisit la maison. Sous `Votre maison/Maisons proposées`, il invoque le bouton dont le texte est la maison de la fiche, puis « Choisir cette maison ». Il attend un reçu accepté au tick lu, puis `Lot690.PousserTick`. Il attend que le cabinet lise la maison du joueur au tick suivant, comme `Lot655`, au siège « Mistra ».
5. Il invoque le bouton « Terres et comptes ». Puis `fiche.Survoler(P)` et `InfobulleDeTerre.Pas(P, fiche.Survolee, t)` à chaque image.
6. Il attend, au plus 30 s, que `Juger(false)` passe : les dossiers se relisent toutes les 2 s, les légendes aussi. Sinon il échoue avec la dernière cause.
7. Il appelle `Juger(true)`, qui joue les drapeaux. C'est ici que les contre-épreuves échouent.
8. Il cache l'infobulle (`Pas(P, null, t)`), qui passerait sur le feuillet. Il pose la toile comme `Lot873` (`Lot549.Photographier`, puis `ScreenSpaceCamera`). Les deux panneaux doivent être entiers dans l'image. Le texte du feuillet doit tenir dans sa fenêtre, comme `Lot655.Lisible`. Le dossier ne doit pas avoir défilé.
9. Il laisse passer 10 images de pose. Puis `Juger(false)` à nouveau, sans l'infobulle, et la trace `CAPTURE_877`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 877 -forgeCaptures 3d/unity/Temp/lot877-photo -logFile 3d/unity/Temp/lot877-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 877 -forgeCaptures 3d/unity/Temp/lot877-identifiant -forge877Identifiant -logFile 3d/unity/Temp/lot877-identifiant.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 877 -forgeCaptures 3d/unity/Temp/lot877-sans-valeur -forge877SansValeur -logFile 3d/unity/Temp/lot877-sans-valeur.log
```

La première (`PHOTO`) sort 0 avec `*--moree-et-ses-comptes.png` : c'est la photo. Les deux autres sont les contre-épreuves de SC2 et SC3. Le codeur ouvre l'image lui-même. Un panneau coupé, un feuillet tronqué, un « Cellule », un « tick » ou un identifiant visible refusent la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les trois commandes, leurs sorties, la trace `CAPTURE_877` et ce que montre l'image.
