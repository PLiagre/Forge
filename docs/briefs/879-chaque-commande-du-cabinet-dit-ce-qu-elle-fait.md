# Lot #879 — Chaque commande du cabinet dit ce qu'elle fait
Jalon : J4 · Machine : pc · Taille prévue : 260 lignes

## But
Chaque commande du cabinet de la carte déclare, dès sa création, la phrase de ce qu'elle fait, et le cabinet montre cette phrase dans l'infobulle du socle quand le pointeur passe sur le bouton.

## Le joueur
Sur la carte, le joueur survole n'importe quelle commande du cabinet : le temps, sa maison, la part et le grenier, le menu, les calques, les voisins, le plan du bourg, les chantiers, la rue, les feuillets. Il lit alors, dans un petit feuillet près du curseur, ce qu'elle fait. Il y lit surtout si elle envoie un ordre au monde, appliqué au jour suivant, ou si elle ne fait que montrer. Il sent qu'il peut toucher à tout sans mode d'emploi, et qu'aucun ordre ne part par surprise. C'est le deuxième des trois sous-lots de #857 « L'infobulle au curseur », dans « La prise en main de la carte » (`CAP.md`, jalon 4). Il sert la décision du jalon : avant de « Confirmer l'ordre » d'une part ou d'un grenier ouvert, ou de « Confirmer la rue », le joueur sait que ce clic engage son grain et ses bras. Il sert aussi le geste « passer de la carte à sa ville d'un geste » : trouver le plan du bourg et le temps sans chercher. Le sous-lot 3 de #857 met le nom de la terre survolée dans le même feuillet ; #858 et #859 donneront leur phrase à leurs icônes.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change. `jeu/sim/`, `jeu/sim/MODELE.md`, le service et les ordres envoyés restent tels quels. Les phrases décrivent ce que chaque bouton fait déjà ; aucun bouton ne change d'action, de nom, de libellé, de place ni de taille.

## Périmètre
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/CommandesMaison.cs
3d/unity/Assets/Interface/MenuCabinet.cs
3d/unity/Assets/Interface/CalquesCarte.cs
3d/unity/Assets/Interface/DossierVoisins.cs
3d/unity/Assets/Interface/DossierBourg.cs
3d/unity/Assets/Interface/DossierChantiers.cs
3d/unity/Assets/Interface/OutilRue.cs
3d/unity/Assets/Interface/Feuillet.cs
3d/unity/Assets/Interface/DossierMaison.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot879.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot879.cs.meta
docs/briefs/879-chaque-commande-du-cabinet-dit-ce-qu-elle-fait.md

Tout autre chemin est interdit ; le `.meta` est généré par Unity et entre dans le diff. `SocleInterface.cs` et `Infobulle.cs` (#878) ne changent pas : la phrase passe par le dernier paramètre de `SocleInterface.Commande`, qui reste facultatif pour le socle (`SocleInterfaceTests` exige qu'une commande sans phrase n'ait pas d'`Infobulle`). C'est le cabinet qui exige la phrase. Chaque aide locale `Bouton(…)` (cabinet, maison, calques, bourg, rue) prend un paramètre `string phrase` obligatoire, sans valeur par défaut, et le transmet. Dans `CabinetDeCarteTests.cs`, les cas s'ajoutent après les cas existants ; aucune ligne existante n'est modifiée ni retirée, et l'aide existante `Proposer()` sert telle quelle. Budget : environ 70 lignes au numstat dans les dix fichiers, 45 de tests, 55 de capture, 2 de `.meta`, 85 de brief.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot879-interface.xml -logFile 3d/unity/Temp/lot879-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté : zéro cas est un échec. Les tests s'écrivent d'abord et se voient rouges avant le code.

**Les phrases**, exactement, passées à la création de chaque commande :
- `CabinetDeCarte` : « Ralentir » → « Passe le temps du monde à la vitesse inférieure. » ; « Pause / Reprendre » → « Arrête le temps du monde, ou le relance à la vitesse choisie. » ; « Accélérer » → « Passe le temps du monde à la vitesse supérieure. » ; « Choisir cette maison » → « Envoie au monde le choix de la maison consultée ; il l'applique au jour suivant. » ; chaque maison proposée → « Montre l'aperçu de cette maison, sans rien envoyer au monde. »
- `CommandesMaison` : « Prélèvement » → « Prépare un nouveau prélèvement sur vos lieux, en pour cent, sans l'envoyer. » ; « Ouvrir le grenier » → « Prépare l'ouverture de votre grenier, en kilos de grain, sans l'envoyer. » ; « Préparer » → « Relit la valeur saisie et prépare l'ordre, sans l'envoyer. » ; « Confirmer l’ordre » → « Envoie l'ordre préparé au monde ; il l'applique au jour suivant. » ; « Annuler / Retour » → « Abandonne l'ordre en préparation ; rien n'est envoyé. »
- `MenuCabinet` : « Menu » → « Ouvre ou ferme le menu : les gestes, le clavier, le volume. » ; « Revenir au jeu » → « Ferme le menu et rend la main à la carte. »
- `CalquesCarte` : « Puissances » → « Colore la carte selon la maison qui tient chaque terre. » ; « Habitants » → « Colore la carte selon le nombre d'habitants de chaque terre. »
- `DossierVoisins` : « Autres maisons » → « Ouvre ou ferme le journal des ordres des autres maisons. »
- `DossierBourg` : « Plan du bourg » → « Ouvre le plan du bourg de la terre conservée. » ; « Revenir à la carte » → « Ferme le plan du bourg et revient à la carte. »
- `DossierChantiers` : « Chantiers » → « Ouvre ou ferme les chantiers du bourg et ce qu'ils ont coûté. »
- `OutilRue` : « Tracer une rue » → « Commence le tracé d'une rue sur le plan, sur vos terres seulement. » ; « Relire le tracé » → « Prépare la rue tracée, sans l'envoyer ; le monde en calculera le coût. » ; « Annuler / Retour » → « Abandonne le tracé et revient au plan ; rien n'est envoyé. » ; « Confirmer la rue » → « Envoie la rue au monde ; il l'applique au jour suivant. »
- `Feuillet` : « Fermer » → « Ferme ce feuillet : » + son titre + « . »
- `DossierMaison` : « Terres et comptes » → « Ouvre ou ferme les terres et les comptes de votre maison. »

**`CabinetDeCarte.CommandesSansPhrase`.** `public static string[] CommandesSansPhrase(Transform toile)` parcourt `toile.GetComponentsInChildren<Button>(true)`, cachées comprises. Il rend, dans l'ordre du parcours, le nom de chaque bouton sans `Infobulle`, ou dont la `Phrase` est vide, blanche ou égale à son nom : une phrase qui répète le libellé ne dit rien. Une toile sans aucun bouton lève `ArgumentException("aucune commande dans le cabinet")` : un échantillon vide échoue.

**SC1 — Chaque commande a sa phrase.** `INTERFACE`, cas `ChaqueCommandeDuCabinetDitCeQuElleFait`. Après `Proposer()`, la toile est `racine.transform.Find("Cabinet")`. Le test exige que ses boutons, cachés compris, contiennent ces 26 commandes, sous 23 noms (« Confirmer l’ordre » s'écrit avec l'apostrophe U+2019 du code actuel) : « Ralentir », « Pause / Reprendre », « Accélérer », « Choisir cette maison », « Maison témoin », « Prélèvement », « Ouvrir le grenier », « Préparer », « Confirmer l’ordre », « Annuler / Retour » (deux fois), « Menu », « Revenir au jeu », « Puissances », « Habitants », « Autres maisons », « Plan du bourg », « Revenir à la carte », « Chantiers », « Tracer une rue », « Relire le tracé », « Confirmer la rue », « Terres et comptes », et « Fermer » trois fois. Il y a au moins 26 boutons, et `CommandesSansPhrase(toile)` est vide ; en cas d'échec, le message nomme les boutons fautifs. La phrase de « Confirmer l’ordre » est celle de la liste ci-dessus, mot pour mot. Contre-épreuves dans le même cas :
- `SocleInterface.Commande(toile, "Témoin sans phrase", 0, 0, null)` rend `CommandesSansPhrase` égal à `{ "Témoin sans phrase" }` ;
- un second témoin dont la phrase est son nom (« Témoin muet ») s'y ajoute ;
- un `Transform` vide lève `ArgumentException`.

Une aide `Bouton` qui oublie la phrase rougit.

**SC2 — Le cabinet montre la phrase du bouton survolé.** `INTERFACE`, cas `LeCabinetMontreLaPhraseDuBoutonSurvole`. Après `Proposer()`, le test prend chaque bouton actif dans la hiérarchie de la toile. Il en exige au moins ces onze : les trois du temps, « Menu », « Terres et comptes », « Maison témoin », « Choisir cette maison », « Plan du bourg », « Puissances », « Habitants » et « Autres maisons ». Pour chacun, il envoie `ExecuteEvents.pointerEnterHandler` avec un `PointerEventData` placé au centre écran du bouton (`RectTransformUtility.WorldToScreenPoint(null, …)`, toile en overlay). Il exige alors un seul « Infobulle » actif sous la toile, son texte égal à la `Phrase` du bouton, et ses coins dans `toile.pixelRect`. `pointerExitHandler` le rend inactif. À la fin, la racine a une seule `Canvas`, et aucun `Graphic` sous « Infobulle » n'a `raycastTarget`. Contre-épreuve : un bouton actif dont on retire l'`Infobulle` (`Object.DestroyImmediate`) ne montre aucun feuillet, et le test le constate.

**SC3 — La photo, et sa contre-épreuve.** Les deux commandes de la section Photo : la première sort 0 avec l'image ; la seconde sort 1, et son journal dit « commandes sans phrase : Commande sans phrase ».

**SC4 — Rien d'autre ne bouge.**
- `INTERFACE` passe sur toute l'assemblée, cas existants compris : `CabinetDeCarteTests` (trois boutons au bandeau, une seule `Canvas`, « Chantiers » sans recouvrement), `SocleInterfaceTests`, `MenuCabinetTests`, `CommandesMaisonTests`, `DossierChantiersTests`, etc. ;
- `git diff -U0 origin/master -- 3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs` ne montre aucune ligne retirée ;
- `git diff -U0 origin/master -- 3d/unity/Assets/Interface` ne change aucune chaîne de nom ou de libellé, aucune position ni aucune taille de bouton : seuls les paramètres de phrase et `CommandesSansPhrase` s'ajoutent ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

Contre-épreuve : un cas existant modifié, un libellé changé ou un fichier hors du Périmètre refuse la livraison.

## Hors périmètre
- L'infobulle d'une terre survolée, et l'effacement de la vieille boîte de survol sous le cabinet : sous-lot 3 de #857.
- Les curseurs (volume, part) et les champs de saisie (quantité, largeur, foyers) : ce ne sont pas des commandes, ils restent sans phrase.
- Les commandes de la capitale en 3D, de la galerie du socle et des outils de l'éditeur ; les anciens boutons de `HorlogeDeCarte`, éteints sous le cabinet.
- Rendre la phrase obligatoire dans `SocleInterface.Commande` : le socle garde `null` permis (#878).
- Le filet de cuivre, le délai d'apparition et les jetons (#849) ; les modes de carte (#858) ; la barre du haut (#859) ; tout nombre du monde.

## Photo
La photo montre la carte de 1400 et le vrai cabinet, sur le vrai service. Le pointeur est au centre de « Pause / Reprendre », dans le bandeau. Le feuillet de papier y dit « Arrête le temps du monde, ou le relance à la vitesse choisie. », entier dans l'image, à côté du point et pas dessus.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot879.cs`, un scénario unique `[ScenarioDeCapture(879, "infobulle-du-temps")]` sur le modèle de `Lot873`. Il réutilise `Lot549.Ouvrir/Photographier` et les aides `internal` de `Lot690` sans les changer. Chaque attente est bornée par `Lot690.Jusqua`, et chaque absence échoue en nommant sa cause. Les étapes :
1. Ouvrir `Forge_Carte`, exiger le `CabinetDeCarte` et la toile « Cabinet » active. Passer `SurvolDeCarte` et `ParcoursDeCarte` en `automatique`, attendre `Lot690.LecturePrete(cabinet.Partie)`, puis attendre que « Pause / Reprendre » soit `interactable` (horloge lue).
2. Avec `-forge879SansPhrase`, ajouter d'abord `SocleInterface.Commande(toile, "Commande sans phrase", 24, 980, null)`. Puis exiger `CabinetDeCarte.CommandesSansPhrase(toile)` vide, sinon échouer par « commandes sans phrase : » suivi des noms joints par « , ». Exiger au moins 26 boutons.
3. `Lot549.Photographier(camera, carte)`, `camera.rect` plein, toile « Cabinet » en `ScreenSpaceCamera` sur la caméra reçue (`planeDistance = nearClipPlane + 0.2f`), une image d'attente et `Canvas.ForceUpdateCanvases()`, comme `Lot873`.
4. Le point est le centre de « Pause / Reprendre » ramené à l'écran par `RectTransformUtility.WorldToScreenPoint(camera, …)`. `EventSystem.current` existe, et son `RaycastAll` à ce point a pour premier résultat le bouton ou un de ses enfants : rien ne le couvre. Le scénario envoie `pointerEnterHandler` au bouton avec ce point. Il exige un seul « Infobulle » actif sous la toile, de texte égal à la phrase du bouton. Ses quatre coins, ramenés à l'écran, sont dans `camera.pixelRect` et hors du carré de 48 px centré sur le point.
5. Dix images de pose, puis revérifier l'étape 4. La trace `CAPTURE_879` donne le nombre de commandes, le point, le rectangle du feuillet et son côté (gauche ou droite).

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 879 -forgeCaptures 3d/unity/Temp/lot879-photo -logFile 3d/unity/Temp/lot879-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 879 -forgeCaptures 3d/unity/Temp/lot879-sans-phrase -forge879SansPhrase -logFile 3d/unity/Temp/lot879-sans-phrase.log
```

La première sort 0 avec une image `*--infobulle-du-temps.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans cette image, et son journal dit « commandes sans phrase : Commande sans phrase ». Le codeur ouvre l'image lui-même. Un feuillet absent, coupé, posé sur le point ou d'un autre texte refuse la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre l'image.
