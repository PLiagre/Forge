# Lot #965 — La preuve des modes de carte
Jalon : J4 · Machine : pc · Taille prévue : 170 lignes

## But
Une capture sur le vrai service prouve le geste « Les modes de carte » entier. Dans chacun des trois modes, une seule légende est visible. Elle est entière, et ne recouvre ni un dossier, ni un feuillet, ni « Plan du bourg », ni la barre du haut. Changer de mode ne change ni le tick ni aucun nombre servi. Chaque commande à icône dit sa phrase.

## Le joueur
Le joueur a pris Mistra. Il ouvre « Terres et comptes » à gauche et passe d'un mode à l'autre en bas à droite : Puissances, Habitants, Flux. À chaque clic, la carte change de couleur, et une seule légende change de texte, toujours à la même place, juste au-dessus des trois commandes. Elle ne passe jamais sous le feuillet ouvert, ni sous ses dossiers de droite, ni sous la barre du haut. Les nombres de ses dossiers ne bougent pas, la date non plus : regarder la carte autrement ne touche pas au monde. Au survol, chaque icône dit ce qu'elle fait. C'est le dernier des trois morceaux du geste « Les modes de carte » du jalon 4 (`CAP.md`, lot 20, #858 : « une légende à la fois, à place fixe » ; « une légende qui recouvre un dossier échoue »). Ce geste sert la décision du jalon : trouver sa capitale, lire ses terres, son grenier et sa part, puis descendre dans sa ville sans chercher. Après ce lot, la preuve tient : une légende doublée, ou remontée sur le feuillet, fait échouer la capture.

## Règle du monde
Sans objet : c'est un lot de preuve d'une vue. Aucun nombre du monde ne change. Ni `jeu/sim/`, ni le service, ni `Forge.Pont`, ni `Forge.Interface` ne sont touchés. Le scénario lit le monde que le cabinet lit déjà, et pousse un tick seulement pour sa contre-épreuve `-forge965Tick`.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot965.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot965.cs.meta
docs/briefs/965-la-preuve-des-modes-de-carte.md

Tout autre chemin est interdit. C'est vrai en particulier pour `CalquesCarte.cs`, `LieuxDeCarte.cs`, `FlechesDeCarte.cs`, `CabinetDeCarte.cs`, `Infobulle.cs`, `SocleInterface.cs`, tous les tests, et les scénarios `Lot549`, `Lot658`, `Lot690`, `Lot963` et `Lot964`. Ils sont lus, jamais modifiés. Le `.meta` a deux lignes : `fileFormatVersion: 2`, puis un `guid` neuf de 32 caractères hexadécimaux, absent du dépôt.

Ce brief s'appuie sur master 63224df, où #963 et #964 sont fusionnés. Ce que le lot lit, tel quel :
- `CalquesCarte` : `BANDE`, `LEGENDE`, `FLUX`, `LIGNES_MAX`, `Mode`, `Legende`, `Lignes`, `LegendeDuMode(mode, repartition)`, `LegendeDuMode(mode, repartition, lieuxPeints)` ; `LieuxDeCarte.Peint` ; `RepartitionHabitants`.
- `Lot658.FlechesDuSiege(camera)`, `Lot658.carte`, `Lot658.toile` (`internal`) ; `Lot690.Jusqua`, `Lot690.Attendre`, `Lot690.PousserTick`, `Lot690.DansLeChamp`.
- `Infobulle.Phrase`, `Infobulle.Montrer`, `Infobulle.Cacher`. Les icônes sont les enfants `Repère banniere`, `Repère foule` et `Repère fleche` des commandes `Puissances`, `Habitants` et `Flux` de la bande.
- Le service des captures tourne à `--jours-par-seconde 0` (`ForgeCapture.LancerService`) : le tick ne bouge que si on le pousse. Le cabinet relit la partie chaque seconde, donc on compare des valeurs, jamais des références.
- Deux enfants directs de la toile s'appellent « Terres et comptes » : la commande du bandeau, et le feuillet. Le feuillet est celui qui porte un `ScrollRect`, comme dans `Lot964`.

**`Lot965.cs`**, dans le style de `Lot964.cs` : une classe `static class Lot965`, les fonctions `Echec`, `Ligne` et `Ecran` recopiées de `Lot964`, et les constantes des quatre drapeaux `-forge965DeuxLegendes`, `-forge965Remonter`, `-forge965Tick` et `-forge965Muet`. `FLOTTANTES` = `{ "Légende des lieux", "Légende des flèches", "Fond de la légende", "Fond des flèches" }`, les noms des légendes retirées par #964. Les étapes du scénario sont écrites à la Photo.

`Controler(string mode, string attendue)` juge l'état présent, dans la même image, sans `yield`. Il lève l'erreur à la première faute, dans cet ordre :
1. **Une seule légende.** Il regarde chaque enfant direct de la toile, actif dans la hiérarchie, sauf le feuillet `Infobulle`. Il compte comme légende chaque enfant qui s'appelle `LEGENDE` ou porte un nom de `FLOTTANTES`, ou qui porte un `Text` actif dont le texte égale `attendue`. Il doit en rester exactement une, `Légende du mode`. Sinon : `deux légendes visibles en mode <mode> : <noms>`.
2. **Entière, à sa place.** `calques.Legende.text` égale `attendue`. `Lignes` reste ≤ `LIGNES_MAX` aux échelles 1 et 2/3. `preferredHeight` ne dépasse pas la hauteur du cadre de plus de 1 px. `Lot690.DansLeChamp` passe sur la légende. Les rectangles d'écran du fond `LEGENDE` et de la bande sont dans l'image.
3. **Sur aucun panneau.** On prend chaque enfant direct de la toile, actif ou non, qui porte une `Image` à `raycastTarget` vrai, sauf `Fond des dossiers`, `LEGENDE` et `BANDE`. Cela couvre la barre du haut « FORGE · Le cabinet », « Votre maison », « Territoire conservé », « Parcourir le monde », les feuillets « Terres et comptes » et « Les autres maisons », « Menu du cabinet », « Plan du bourg » et « Les chantiers du bourg ». Les panneaux fermés sont jugés à la place où ils s'ouvrent. Le fond et la bande ne recouvrent le rectangle d'écran d'aucun. Sinon : `« <zone> » recouvre « A », « B » en mode <mode>`, avec tous les panneaux recouverts. Il exige aussi que le feuillet « Terres et comptes » soit actif.
4. **Aucun nombre servi ne bouge.** Les valeurs notées à l'étape 2 de la Photo n'ont pas changé : `horloge.Lue.Tick`, `horloge.Lue.JoursParSeconde`, le tick de `cabinet.Partie.Monde.Donnees.Monde`, et la liste `Textes()`. Sinon : `nombre servi changé au changement de mode <mode> : <ce qui a changé, avant → après>`. Le tick se compare en premier.

`Textes()` rend, dans l'ordre de la hiérarchie, le texte de chaque `Text` actif sous « FORGE · Le cabinet », « Votre maison », « Territoire conservé », « Parcourir le monde » et le feuillet « Terres et comptes ».

`Icones()` juge, pour chacune des commandes `Puissances`, `Habitants` et `Flux` de la bande :
- son enfant `Repère banniere`, `Repère foule` ou `Repère fleche` est actif dans la hiérarchie, sinon : `icône absente : <mode>` ;
- son `Infobulle.Phrase` n'est pas vide, diffère du nom, et passe `TexteDuMonde.Interdit` et `TexteDuMonde.SansUnite` ;
- `Infobulle.Montrer(canvas de la toile, phrase, centre de la commande en pixels d'écran)` rend un feuillet actif, dont le `Text` égale la phrase et qui est entier dans l'image. Puis `Infobulle.Cacher`.

## Conditions de succès
On lance tout sur le PC, éditeur fermé, depuis la racine, en PowerShell. `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Les cinq commandes entières sont écrites à la Photo.

**SC1 — La preuve passe sur le vrai service.** `PHOTO` sort 0 avec `*--trois-modes.png`. Son journal porte une trace `CAPTURE_965` qui nomme les trois modes, chacun avec sa légende et son nombre de lignes, le tick et le nombre de textes comparés. Le codeur ouvre l'image. La livraison est refusée, même avec une sortie 0, si l'image montre deux légendes, une légende coupée ou posée sur un panneau, un feuillet fermé, une icône absente ou des terres en pigment de maison.

**SC2 — Contre-épreuve : deux légendes visibles à la fois.** `DEUX` sort 1, sans image. Son journal dit `deux légendes visibles en mode Flux`.

**SC3 — Contre-épreuve : la légende remontée sur le feuillet.** `REMONTER` sort 1, sans image. Son journal dit `« Légende du mode » recouvre` et nomme « Terres et comptes ».

**SC4 — Contre-épreuve : un nombre servi qui bouge.** `TICK` sort 1, sans image. Son journal dit `nombre servi changé au changement de mode Puissances` et nomme le tick.

**SC5 — Contre-épreuve : une icône sans son repère.** `MUET` sort 1, sans image. Son journal dit `icône absente : Flux`.

**SC6 — Rien d'autre ne bouge.** `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot965-interface.xml -logFile 3d/unity/Temp/lot965-interface.log` sort 0, sans échec ni cas ignoré. `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre. `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

## Hors périmètre
- Tout changement de `CalquesCarte`, des lieux, des flèches, des dossiers ou du socle. Si la preuve trouve une faute, le codeur la décrit dans son compte rendu, sans la corriger ici. Les tests existants ne changent pas.
- Ouvrir « Plan du bourg », « Les chantiers du bourg » ou le menu pendant la capture : ils sont jugés à la place où ils s'ouvrent. Le contrôle à 1280 × 720 est déjà fait par le cas de #963.
- La barre du haut unique et la fin de « Parcourir le monde » (#859). La langue du cabinet (#849, #850).
- Tout nombre du monde, toute lecture nouvelle du service.

## Photo
La carte autour de Mistra, en mode Flux, après trente jours à 60 % de part. Les terres sont en papier, et les flèches orange et violette sont visibles. À gauche, le feuillet « Terres et comptes » est ouvert. À droite, « Votre maison » et « Territoire conservé » sont entiers. En haut, la barre du cabinet. En bas à droite, la bande des trois modes, chacun avec son icône, et juste au-dessus, une seule légende : celle du Flux, entière, sur aucun panneau. Aucune infobulle n'est ouverte.

Le scénario `[ScenarioDeCapture(965, "trois-modes")]` de `Lot965.cs` suit ces étapes :
1. Il joue `Lot658.FlechesDuSiege(camera)` en entier : Mistra, la part, trente ticks, le feuillet ouvert, Flux, la toile posée et cadrée. Puis il prend `Lot658.carte`, `Lot658.toile`, `CabinetDeCarte`, `HorlogeDeCarte`, `CalquesCarte` et `LieuxDeCarte`. Il passe `SurvolDeCarte`, `ParcoursDeCarte` et `InfobulleDeTerre` en `automatique`, et appelle `Infobulle.Cacher`.
2. Il attend, avec `Lot690.Jusqua`, que `cabinet.Partie.Occupee` et `horloge.RequeteEnVol` soient faux, et que `horloge.Lue.Tick` égale le tick du monde lu. Il note le tick, `JoursParSeconde` et `Textes()`. Avec `-forge965Tick`, il pousse alors un tick (`Lot690.PousserTick(carte.port)`, attendu, statut 200). Puis il attend que l'horloge et le monde lu soient au tick suivant.
3. Pour chaque mode, dans l'ordre Puissances, Habitants, Flux, il clique sur `Modes de la carte/<mode>`. La légende attendue est :
   - en Puissances, `LegendeDuMode(Puissances, null, true)`, et `lieux.Peint` est exigé ;
   - en Habitants, `LegendeDuMode(Habitants, new RepartitionHabitants(monde lu))` ;
   - en Flux, `FLUX`.

   Il attend que `calques.Mode` soit ce mode, que la légende égale l'attendue, et que `Occupee` et `RequeteEnVol` soient faux. Puis, dans la même image, sans `yield` :
   - en Flux seulement, avec `-forge965DeuxLegendes`, il pose sous la toile une copie du fond `LEGENDE` (`Object.Instantiate(fond, toile)`), nommée `Légende des lieux`, en (16, -104) ;
   - en Flux seulement, avec `-forge965Remonter`, il pose le fond `LEGENDE` en `anchoredPosition` (16, -104), la place de l'ancienne légende des lieux ;
   - il appelle `Controler(mode, attendue)`.
4. En Flux, avec `-forge965Muet`, il éteint `Modes de la carte/Flux/Repère fleche`. Puis il appelle `Icones()`, dans la même image, sans `yield`.
5. Il laisse passer 10 images. Il rappelle `Controler("Flux", FLUX)`. Il exige que le feuillet `Infobulle` soit fermé et qu'au moins une flèche de `Flèches de la carte` soit active.
6. Il écrit la trace `CAPTURE_965 Puissances « … » N lignes · Habitants « … » N lignes · Flux « … » N lignes · tick T · K textes inchangés`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 965 -forgeCaptures 3d/unity/Temp/lot965-photo -logFile 3d/unity/Temp/lot965-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 965 -forgeCaptures 3d/unity/Temp/lot965-deux -forge965DeuxLegendes -logFile 3d/unity/Temp/lot965-deux.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 965 -forgeCaptures 3d/unity/Temp/lot965-remonter -forge965Remonter -logFile 3d/unity/Temp/lot965-remonter.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 965 -forgeCaptures 3d/unity/Temp/lot965-tick -forge965Tick -logFile 3d/unity/Temp/lot965-tick.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 965 -forgeCaptures 3d/unity/Temp/lot965-muet -forge965Muet -logFile 3d/unity/Temp/lot965-muet.log
```

La première commande (`PHOTO`) sort 0 avec `*--trois-modes.png` : c'est la photo. Les quatre suivantes sont les contre-épreuves `DEUX` (SC2), `REMONTER` (SC3), `TICK` (SC4) et `MUET` (SC5). Chacune sort 1, sans image. Le codeur ouvre la photo lui-même. Les PNG restent hors du dépôt. Le compte rendu donne les cinq commandes, leurs sorties, la trace `CAPTURE_965`, la ligne d'erreur de chaque contre-épreuve et ce que montre l'image.
