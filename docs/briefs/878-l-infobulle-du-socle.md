# Lot #878 — L'infobulle du socle
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Le socle de l'interface sait poser l'infobulle, un petit feuillet de papier près du curseur, toujours entier dans l'écran et jamais sur le point survolé, et une commande du socle peut déclarer la phrase de ce qu'elle fait, qu'elle montre au survol.

## Le joueur
Dans la galerie du socle, le joueur survole une commande et lit, dans un petit feuillet près du curseur, ce qu'elle fait, ou pourquoi elle est indisponible. Le feuillet ne cache pas ce qu'il pointe et ne sort jamais de l'écran, même au coin, en 1920 × 1080 comme en 1280 × 720. Il sent qu'une commande s'explique d'elle-même, sans mode d'emploi. C'est le premier des trois sous-lots de #857 « L'infobulle au curseur », dans « La prise en main de la carte » (`CAP.md`, jalon 4). C'est un lot de fond des gestes du J4 « passer de la carte à sa ville d'un geste » et « paie au grenier » : le joueur doit trouver sa capitale et lire son grenier sans chercher. Le sous-lot 2 de #857 donne sa phrase à chaque commande du cabinet de la carte ; le sous-lot 3 met le nom de la terre survolée dans ce feuillet. #858 et #859 s'appuient dessus.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service. La galerie ne charge aucune partie.

## Périmètre
3d/unity/Assets/Interface/SocleInterface.cs
3d/unity/Assets/Interface/Infobulle.cs
3d/unity/Assets/Interface/Infobulle.cs.meta
3d/unity/Assets/Interface/Tests/SocleInterfaceTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot878.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot878.cs.meta
docs/briefs/878-l-infobulle-du-socle.md

Tout autre chemin est interdit ; les `.meta` sont générés par Unity et entrent dans le diff. Aucun appelant de `SocleInterface.Commande` ne change (cabinet, dossiers, menu, outils) : le nouveau paramètre est facultatif. `MatieresCabinet` et sa palette ne changent pas : aucun jeton n'est ajouté. Dans `SocleInterfaceTests.cs`, les cas s'ajoutent après les cas existants ; aucune ligne existante n'est modifiée ni retirée. Budget : environ 10 lignes dans le socle, 75 pour `Infobulle.cs`, 60 de tests, 50 de capture, 4 de `.meta` et 90 de brief, dans le style dense du dossier.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot878-interface.xml -logFile 3d/unity/Temp/lot878-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec, et les cas nommés réellement exécutés : zéro cas est un échec. Les tests s'écrivent d'abord et se voient rouges avant le code.

`Infobulle.cs` (espace `Forge.Interface`) porte :
- `public sealed class Infobulle : MonoBehaviour, IPointerEnterHandler, IPointerMoveHandler, IPointerExitHandler`, posée sur une commande qui déclare sa phrase, avec `public string Phrase { get; }`. À l'entrée et au déplacement du pointeur, elle montre sa phrase au point de l'événement (`eventData.position`) dans la toile racine de la commande ; à la sortie et à `OnDisable`, elle cache le feuillet ;
- `public const float ECART_PX = 24f, LARGEUR_MAX = 420f, MARGE = 12f` ;
- `public static Rect Placer(Vector2 point, Vector2 taille, Vector2 ecran)`, pure, en pixels d'écran, origine en bas à gauche. Le feuillet va à droite du point (`x + ECART_PX`) s'il y tient, sinon à sa gauche (bord droit à `x − ECART_PX`) ; sous le point (bord haut à `y − ECART_PX`) s'il y tient, sinon au-dessus (bord bas à `y + ECART_PX`). Si aucun des deux côtés ne tient sur un axe, `ArgumentException` : le code refuse de deviner, il ne recadre pas. Jamais de `Clamp` ;
- `public static RectTransform Montrer(Canvas toile, string texte, Vector2 point)` : un texte vide ou blanc lève `ArgumentException`. Sinon, il trouve ou crée l'enfant « Infobulle » de la toile, sans nouvelle `Canvas` : une `Image` habillée par `MatieresCabinet.Habiller` (papier), un `Text` en `SocleInterface.Police(false)`, taille `Corps`, couleur `encre`, à `MARGE` du bord. La largeur vaut `min(preferredWidth + 2 MARGE, LARGEUR_MAX)` en unités de toile, le texte va à la ligne, et la hauteur suit `preferredHeight`. Aucun graphique du feuillet n'est cible de rayon (`raycastTarget = false`), sinon il volerait le survol et `CabinetDeCarte.HorsCarte` le prendrait pour un panneau. Le feuillet passe en dernier enfant, actif, et sa place vient de `Placer` : taille × `toile.scaleFactor`, point relatif à `toile.pixelRect`, puis retour en unités, ancré en bas à gauche ;
- `public static void Cacher(Canvas toile)`.

`SocleInterface.Commande` gagne un dernier paramètre `string phrase = null`. Avec `null`, rien ne change et aucune `Infobulle` n'est posée. Une phrase vide ou blanche lève `ArgumentException("phrase vide refusée : " + nom)` avant toute création d'objet : une garde après l'effet ne protège rien. Sinon, la commande porte une `Infobulle` avec cette phrase. Dans `Creer`, les trois commandes de la galerie déclarent la leur : « Consulter le dossier » « Ouvre le dossier sans rien envoyer au monde. » ; « En attente du monde » « Indisponible : aucune partie chargée. » ; « Parcourir au clavier » « Passe d'une commande à l'autre avec les flèches ; Entrée agit. ».

**SC1 — Entière dans l'écran, jamais sur le point.** `INTERFACE`, cas `LInfobulleResteEntiereEtLibereLePoint`. Dans la galerie, le test montre la plus longue des trois phrases et lit la taille du feuillet en unités. Pour chaque écran (1920 × 1080, puis 1280 × 720), la taille passe en pixels (× largeur / 1920). Pour chaque point d'une grille de 20 px, bords et quatre coins compris (`(0, 0)`, `(W, 0)`, `(0, H)`, `(W, H)`), `Placer` rend un rectangle tel que `xMin ≥ 0`, `yMin ≥ 0`, `xMax ≤ W` et `yMax ≤ H`. Il ne chevauche pas (`Rect.Overlaps` faux) le carré de 48 px centré sur le point. Le test compte les points jugés : zéro point est un échec. Au centre de l'écran, un feuillet de `W / 2` de large (ou de `H / 2` de haut) lève `ArgumentException`. Contre-épreuve : un `Placer` qui garde toujours le bas à droite et recadre dans l'écran rougit au coin `(W, 0)`.

**SC2 — Une phrase vide est refusée.** `INTERFACE`, cas `UneCommandeRefuseUnePhraseVide`. `Commande(…, phrase: p)` lève `ArgumentException` dont le message contient le nom, pour `p` = `""`, `"   "` et `"\n"`. Après chaque refus, le parent n'a aucun enfant de ce nom. `Montrer(toile, "", point)` lève aussi. Une commande sans phrase (`null`) n'a pas d'`Infobulle`, et une commande avec phrase rend la même par `GetComponent<Infobulle>().Phrase`. Contre-épreuve : une garde qui jette après la création du bouton laisse un enfant et rougit ; une phrase blanche acceptée rougit.

**SC3 — La galerie montre l'infobulle sur ses commandes.** `INTERFACE`, cas `LaGalerieMontreLInfobulleSurSesCommandes`. Pour chacune des trois commandes, l'inactive comprise, le test envoie `ExecuteEvents.pointerEnterHandler` avec un `PointerEventData` dont la position est le centre écran du bouton. Il exige alors un seul « Infobulle » actif sous la toile « Documents », son texte égal à la phrase de la commande, et ses coins écran (toile en overlay) dans `toile.pixelRect`, hors du carré de 48 px autour du point. `pointerExitHandler` le rend inactif. Après les trois survols, la galerie a une seule `Canvas`, et aucun `Graphic` sous « Infobulle » n'a `raycastTarget`. Contre-épreuve : un feuillet dans sa propre `Canvas`, ou une `Image` laissée cible de rayon, rougit.

**SC4 — La photo, et sa contre-épreuve.** Les deux commandes de la section Photo : la première sort 0 avec l'image, la seconde sort 1 avec « phrase vide refusée : Commande sans phrase » dans son journal.

**SC5 — Rien d'autre ne bouge.** Les commandes :
- `INTERFACE` passe sur toute l'assemblée, cas existants de `SocleInterfaceTests` et de `CabinetDeCarteTests` compris (une seule `Canvas` sous le cabinet) ;
- `git diff -U0 origin/master -- 3d/unity/Assets/Interface/Tests/SocleInterfaceTests.cs` ne montre aucune ligne retirée ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

Contre-épreuve : un cas existant modifié, ou un fichier hors du Périmètre, refuse la livraison.

## Hors périmètre
- Les phrases des commandes du cabinet, du menu, des dossiers et des outils, et l'obligation d'en avoir une : sous-lot 2 de #857.
- L'infobulle d'une terre survolée et l'effacement de la vieille boîte de survol : sous-lot 3 de #857.
- Le filet de cuivre, le court délai d'apparition et les neuf états de `docs/interface/DA.md` : #849 pose les sept jetons et habille ce feuillet. Ce lot n'ajoute aucun jeton.
- Les modes de carte (#858), la barre du haut (#859), toute scène, tout service, tout nombre du monde.

## Photo
La photo montre la galerie du socle, le dossier « Le conseil » à droite, et le pointeur au bout droit de « Parcourir au clavier ». Le feuillet de papier y dit « Passe d'une commande à l'autre avec les flèches ; Entrée agit. », entier dans l'image, à côté du point et pas dessus.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot878.cs`, avec un scénario unique, `[ScenarioDeCapture(878, "infobulle-de-la-galerie")]`. Toute absence échoue en nommant sa cause. Les étapes :
1. `SocleInterface.Creer()` dans la scène reçue. Avec `-forge878PhraseVide`, le scénario ajoute d'abord au dossier « Le domaine » `SocleInterface.Commande(domaine, "Commande sans phrase", 24, 540, null, true, "")` : le refus remonte et le scénario échoue.
2. Passer la toile « Documents » en `ScreenSpaceCamera` sur la caméra reçue, comme `Lot855` (`camera.rect` plein, `planeDistance = nearClipPlane + 0.2f`), attendre une image et forcer `Canvas.ForceUpdateCanvases()`.
3. Coins : aux quatre coins de `toile.pixelRect`, rentrés d'un pixel, `Infobulle.Montrer` avec la phrase la plus longue. Les coins du feuillet, ramenés à l'écran par `RectTransformUtility.WorldToScreenPoint(camera, …)`, restent dans `pixelRect` et hors du carré de 48 px autour du point ; sinon le scénario échoue en nommant le coin.
4. Survol : le point est le milieu du bord droit de « Parcourir au clavier », ramené à l'écran, moins 8 px en x. Le scénario envoie `pointerEnterHandler` au bouton avec l'`EventSystem` de la galerie et ce point. Il exige le feuillet actif avec la phrase du bouton, entier dans `pixelRect`, hors du carré du point.
5. Dix images de pose, puis revérification de l'étape 4. La trace `CAPTURE_878` donne les quatre coins et leurs rectangles, le point, le rectangle du feuillet et son côté (gauche ou droite).

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 878 -forgeTicks 1 -forgeCaptures 3d/unity/Temp/lot878-photo -logFile 3d/unity/Temp/lot878-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 878 -forgeTicks 1 -forgeCaptures 3d/unity/Temp/lot878-phrase-vide -forge878PhraseVide -logFile 3d/unity/Temp/lot878-phrase-vide.log
```

La première sort 0 avec une image `*--infobulle-de-la-galerie.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans cette image, et son journal dit « phrase vide refusée : Commande sans phrase ». Le codeur ouvre l'image lui-même. Un feuillet absent, coupé, posé sur le point ou d'un autre texte refuse la livraison, même avec une sortie 0. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montre l'image.
