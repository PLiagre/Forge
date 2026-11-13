# Lot #849 — Le cabinet prend sa langue : la pierre, le bois brûlé et le registre
Jalon : J6 · Machine : pc · Taille prévue : 950 lignes

## But
Le socle de l'interface parle la langue du 28 octobre : seize jetons au contraste calculé, la pierre, le bois brûlé et le métal générés sans aléa, la rubrique, la ligne de compte, la note en marge, le séparateur et le sceau du registre, l'infobulle au filet de cuivre, et neuf états qui se lisent sans leur couleur. Une seconde galerie du socle les montre tous.

## Le joueur
Partout, le joueur reconnaît d'un coup d'œil ce qu'il peut faire, ce qu'il a choisi, ce qui attend le monde et ce qui presse. Repos, survol, focus, sélection, inactif, attente, reçu, refus et alerte ne se distinguent jamais par la seule teinte : chacun a son trait, son signe ou son mot, comme dans un registre où l'on lit le prix d'un geste avant de le sceller. Après ce lot, il le voit dans la galerie du socle, les neuf états côte à côte.

C'est un lot de fond. Il prépare le geste du jalon 6 : le joueur gouverne son pays depuis la carte et dépense ses jauges en gestes (affermir la concorde, asseoir le droit). La commande qui engage porte le sceau ; elle attend le monde, puis elle est reçue ou refusée avec sa raison, et la barre des jauges qui presse est en alerte. C'est aussi le registre où il lira le prix d'un bâtiment de province et d'un chantier (#419). Les écrans le recevront :
- #850 : la carte, la barre (#1032) et ses dossiers, la bande des modes ;
- #1033 : le panneau du pays ;
- plus tard au jalon 6, #446 : les commandes de l'arbre (éduquer, marier, changer la loi).

## Règle du monde
Sans objet : c'est un lot de vue. Il ne touche ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service, ni aucune empreinte. Les galeries ne chargent aucune partie, et aucun nombre du monde n'y paraît.

## Périmètre
3d/unity/Assets/Interface/SocleInterface.cs
3d/unity/Assets/Interface/MatieresCabinet.cs
3d/unity/Assets/Interface/Infobulle.cs
3d/unity/Assets/Interface/EtatsDuCabinet.cs
3d/unity/Assets/Interface/EtatsDuCabinet.cs.meta
3d/unity/Assets/Interface/GalerieDuRegistre.cs
3d/unity/Assets/Interface/GalerieDuRegistre.cs.meta
3d/unity/Assets/Interface/Tests/SocleInterfaceTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot849.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot849.cs.meta
docs/briefs/849-le-cabinet-prend-sa-langue-la-pierre-le-bois-bru.md

Tout autre chemin est interdit. Les `.meta` sont générés par Unity et entrent dans le diff.

« Aucun écran n'est encore touché » : `SocleInterface.Creer`, `Texte`, `Panneau`, `Commande`, `MatieresCabinet.Habiller`, `Engagement`, `EtatsLecture` et `GalerieEtats` gardent leur comportement, et aucun de leurs appelants ne change. Seule exception, voulue par l'issue : le feuillet de `Infobulle.Montrer` change de matière. Il garde sa taille, sa place, son enfant `Text` et l'absence de cible de rayon.

Dans `SocleInterfaceTests.cs`, les cas s'ajoutent après les cas existants. Aucune ligne existante n'est modifiée ni retirée.

Budget, dans le style dense du dossier :

| Partie | Lignes |
|---|---|
| socle | environ 110 |
| matières | 70 |
| infobulle | 5 |
| `EtatsDuCabinet` | 120 |
| galerie | 140 |
| tests | 260 |
| capture | 130 |
| `.meta` | environ 6 |
| brief | 110 |

## Conditions de succès
Les définitions des commandes :
- `U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell ;
- `I` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot849-interface.xml -logFile 3d/unity/Temp/lot849-interface.log`, sans `-quit` ;
- `P` = la même avec `-assemblyNames Forge.Pont.Tests -testResults 3d/unity/Temp/lot849-pont.xml -logFile 3d/unity/Temp/lot849-pont.log`.

Il faut une sortie 0, un XML sans échec, et les cas nommés réellement exécutés : zéro cas est un échec. Les tests s'écrivent d'abord, et se voient rouges avant le code.

### Ce que le code porte

**Jetons et contraste** (`SocleInterface`, espace `Forge.Interface`). La palette gagne sept jetons, à côté des huit et de `mer` :

| Jeton | Hex |
|---|---|
| `pierre` | `#1C1B19` |
| `bois-brule` | `#2B211B` |
| `metal` | `#3E3B33` |
| `sang` | `#7A1E19` |
| `cuivre` | `#A8683C` |
| `or-vieilli` | `#B49A61` |
| `vert-de-gris` | `#5E8C7A` |

Le socle expose aussi :
- `public static IReadOnlyList<string> Jetons`, les seize noms ;
- `public static double Contraste(Color devant, Color derriere)`, le rapport WCAG 2.1. Pour chaque composante `c` de la couleur sRGB lue, `c ≤ 0,03928 ? c / 12,92 : ((c + 0,055) / 1,055)^2,4`, puis `L = 0,2126 R + 0,7152 G + 0,0722 B` et le rapport `(L1 + 0,05) / (L2 + 0,05)`, le plus clair en haut ;
- `public static Color Attenue` = `Color.Lerp(papier, metal, .30f)`, le texte de l'état inactif : une teinte dérivée dans le socle, pas un jeton ;
- `public enum Usage { Texte, Trait }`, aux seuils 4,5 et 3 ;
- `public static readonly IReadOnlyList<(string devant, string derriere, Usage usage)> Paires`. Les noms sont des jetons, ou `attenue`. Les paires sont :
  - en texte : `papier` sur `pierre`, sur `bois-brule`, sur `metal` et sur `sang` ; `sang`, `encre` et `secondaire` sur `papier` ; `or-vieilli` et `vert-de-gris` sur `pierre` ; `attenue` sur `metal` ;
  - en trait : `cuivre` sur `bois-brule` et sur `papier` ; `or-vieilli` sur `bois-brule` ; `papier` sur `bois-brule` ; `vert-de-gris` sur `pierre` ; `sang` sur `papier` ;
- `public static string Refuse(IEnumerable<(string, string, Usage)> paires)`. Il rend `null` si chaque paire tient son seuil. Sinon, il rend la première fautive, ainsi : « or-vieilli sur papier : 2,0:1 < 4,5:1 (texte) », avec la virgule française. Un nom inconnu lève `ArgumentException`.

Un trait se juge contre la matière qu'il borde.

**Matières** (`MatieresCabinet`) :
- `public static Color32[] Pixels(string matiere)`, en 128 × 128, pour `pierre`, `bois-brule` et `metal`. Le calcul est entier et pur (hachage de x et y) : ni `UnityEngine.Random`, ni `System.Random`, ni heure, ni graine du monde. La pierre a des blocs et un grain, le bois brûlé des fibres horizontales, le métal un brossé fin et une patine. Un autre nom lève `ArgumentException` ;
- les sprites `Pierre`, `BoisBrule` et `Metal`, mis en cache comme `Papier` ;
- le sprite `FeuilletDInfobulle` : le papier de chiffon, bordé sur tout son tour d'un filet `cuivre` épais de `EtatsDuCabinet.De(Survol).Epaisseur` texels, sans le liseré `or` du papier ;
- `Infobulle.Montrer` habille son feuillet de ce sprite au lieu de `Habiller(papier)`. Le filet est dans le sprite, donc dans le rectangle du feuillet : rien ne dépasse.

**Registre** (`SocleInterface`) :
- `Rubrique(parent, titre, x, y, largeur, sombre = false)` : Noto Serif, taille `Titre`, le titre en capitales `fr-FR` lettres séparées par U+2009. Il est en `sang` sur papier, ou en `papier` si `sombre`. Dessous, deux enfants « Filet » de `metal`, de 1 px chacun, à 3 px d'écart ;
- `LigneDeCompte(parent, libelle, decimal? valeur, unite, x, y, largeur)` : le libellé à gauche en `encre`. Le nombre et son unité vont à droite, alignés à droite, par `EtatsLecture.Mesure`, de sorte qu'une valeur absente donne « — Donnée absente » et jamais 0. Un libellé ou une unité vide lève `ArgumentException` avant toute création ;
- `PiedDeFeuillet(parent, date, x, y, largeur)` : la date reçue, en `secondaire`. Une date vide lève l'exception ;
- `NoteEnMarge(parent, texte, x, y, largeur)` : en `secondaire`, taille 16. Un texte qui contient un chiffre lève l'exception : une note n'est jamais seule à porter un nombre ;
- `Separateur(parent, x, y, largeur)` : un filet de `metal` de 1 px et un seul losange de 8 × 8, tourné de 45°, au centre ;
- `Sceau(parent, x, y)` : une `Image` de 28 × 28, non cible de rayon, faite de cire `sang`. La moyenne des texels opaques est à moins de 12/255 de `sang`. Le sprite est généré comme `Cire`.

**Neuf états** (nouveau fichier `EtatsDuCabinet.cs`). Il déclare :
- `public enum EtatDuCabinet { Repos, Survol, Focus, Selection, Inactif, Attente, Recu, Refus, Alerte }` ;
- `public enum FormeDuTrait { Aucun, Plein, Double, Pointille }` ;
- `public readonly struct Declaration`, avec `Nom`, `Matiere`, `Texte`, `Trait` (jetons ou `attenue`), `Forme`, `Epaisseur` (en px), `Signe` et `Mot` (`null` s'il n'y en a pas) ;
- `De(etat)` et `Table`.

Les neuf déclarations, telles quelles :

| État | Matière | Texte | Trait | Signe | Mot |
|---|---|---|---|---|---|
| repos | `bois-brule` | `papier` | `metal`, plein, 1 (décoratif) | — | — |
| survol | `bois-brule` | `papier` | `cuivre`, plein, 2 | — | — |
| focus clavier | `bois-brule` | `papier` | `or-vieilli`, double, 2 | — | — |
| sélection | `bois-brule` | `papier` | `or-vieilli`, plein, 4 | — | « Choisi » |
| inactif | `metal` | `attenue` | aucun | — | « Indisponible » |
| attente | `bois-brule` | `papier` | `papier`, pointillé, 1 | « … » | « En attente du monde » |
| reçu | `pierre` | `vert-de-gris` | `vert-de-gris`, plein, 2 | — | « Ordre reçu » |
| refus | `papier` | `sang` | `sang`, plein, 2 | « × » | « Demande refusée » |
| alerte | `sang` | `papier` | aucun | « ! » | « Alerte » |

`EtatsDuCabinet` porte aussi :
- `public static IEnumerable<(string, string, Usage)> PairesDesEtats()`. Elle rend, pour chaque état, son texte sur sa matière, et son trait sur sa matière, sauf pour repos, dont le trait ne porte aucun état ;
- `public static string Confondus(IEnumerable<Declaration> table)`. Elle rend `null` si chaque paire d'états diffère par au moins une de ces quatre choses : la forme, l'épaisseur, le signe, le mot. Les jetons ne comptent pas. Sinon, elle rend « repos et reçu ne diffèrent que par leur teinte » ;
- `public static RectTransform Poser(Transform parent, EtatDuCabinet etat, string libelle, float x, float y, float largeur, float hauteur)`. Elle crée une plaque « État <nom> », dont le fond est la matière : sprite généré pour la pierre, le bois brûlé et le métal, aplat du jeton pour le papier et le sang. Le trait est fait de barres :
  - plein : quatre enfants « Trait », d'épaisseur `Epaisseur` ;
  - double : huit, en deux cadres à 4 px l'un de l'autre ;
  - pointillé : au moins huit enfants « Tiret » ;
  - aucun : zéro enfant.

  Le `Text` de la plaque dit le signe, puis le mot, puis le libellé, séparés par une espace ; il revient à la ligne. Aucun graphique de la plaque n'est cible de rayon.

**La galerie du registre** (nouveau fichier `GalerieDuRegistre.cs`, `MonoBehaviour` comme `GalerieEtats`, menu « Forge/Interface/Galerie du registre »). `Creer()` rend la racine « Galerie du registre ». Elle a une seule `Canvas`, « Registre », de référence 1920 × 1080, comme celle du socle, une navigation `EventSystem` et un fond plein écran en matière pierre. Ses zones, de haut en bas, ne se chevauchent pas :
1. le titre et « LE CABINET  /  LA LANGUE DU REGISTRE » en `or-vieilli` ;
2. seize pastilles « Jeton <nom> », chacune avec son nom et son hex ;
3. les trois matières, « Matière pierre », « Matière bois-brule » et « Matière metal », nommées ;
4. un feuillet de papier. Il porte la rubrique « Le grenier, exemple », deux lignes de compte et un pied de feuillet « Exemple, aucun tick reçu ». La première ligne est « Exemple de compte » 1250 kg, la seconde « Exemple absent » sans valeur. Viennent ensuite une note en marge sans chiffre, un séparateur, et une commande « Sceller l'exemple » (action nulle, phrase « Exemple d'engagement : aucun ordre envoyé. ») marquée de `Sceau` ;
5. les neuf plaques côte à côte, dans l'ordre de l'enum. Chacune a au-dessus le nom de son état, en `papier`, et le libellé « Ouvrir le grenier » ;
6. le pied « Démonstration visuelle — aucune partie chargée » ;
7. au coin bas droit, collée aux deux bords, la commande « Coin de l'écran » (340 × 44, phrase « Une infobulle au coin reste entière dans l'écran. »).

### Les conditions

**SC1 — Seize jetons, ceux de la DA.** `I`, cas `LesJetonsSontCeuxDeLaRevision`. Le test lit `docs/interface/DA.md`, depuis `Application.dataPath/../../../`. Il en tire les lignes des deux tableaux de jetons, nom et hex entre accents graves, et le `mer` de la phrase du pigment. Il exige que `Jetons` en soit exactement l'ensemble (seize noms, `or` et `or-vieilli` compris) et que chaque `Couleur(nom)` égale son hex. Zéro ligne lue est un échec. Contre-épreuve : un hex retouché dans le socle, ou un jeton absent, rougit.

**SC2 — Chaque paire déclarée tient son seuil, et l'or vieilli sur papier est refusé.** `I`, cas `ChaquePaireDeclareeTientSonSeuil`. Le test exige trois choses :
- `Refuse(Paires)` est `null` ;
- `PairesDesEtats()` est inclus dans `Paires` ;
- chaque contraste écrit dans la colonne « Contraste mesuré » de la DA (motifs `` `x` dessus : n,n:1 `` et `` sur `x` : n,n:1 ``) égale `Contraste` arrondi au dixième. Il y en a huit, et le nombre lu est compté.

Contre-épreuve, jouée dans le même cas : `Refuse(Paires + ("or-vieilli", "papier", Texte))` rend un message qui contient « or-vieilli sur papier » et « 2,0:1 ».

**SC3 — Chaque état se lit sans sa couleur.** `I`, cas `ChaqueEtatSeLitSansSaCouleur`. Le test exige :
- neuf états dans `Table` ;
- `Confondus(Table)` est `null` ;
- chaque signe déclaré est rendu par les deux polices Noto (`RequestCharactersInTexture`, puis `HasCharacter`).

Contre-épreuve, jouée dans le même cas : une table où reçu prend la forme, l'épaisseur, le signe et le mot de repos, en gardant ses jetons, fait rendre « repos et reçu ne diffèrent que par leur teinte ».

**SC4 — Les matières naissent sans aléa.** `I`, cas `LesMatieresNaissentSansAlea`. Pour chaque matière, `Pixels` rend les mêmes octets après `UnityEngine.Random.InitState(1)` puis `InitState(2)`, et ces octets ne sont pas vides. La moyenne de chaque canal est à moins de 3/255 du jeton. L'écart-type de la luminance est entre 1/255 et 8/255 : une matière, pas un aplat, et pas une texture sous le texte. Sur chaque pixel, `papier` garde 4,5:1. Le sprite `FeuilletDInfobulle` a ses texels de bord en `cuivre`, sur l'épaisseur du survol. Un nom inconnu lève l'exception. Contre-épreuve : un générateur qui tire `UnityEngine.Random`, ou un aplat du jeton, rougit.

**SC5 — Le registre refuse ce qui manque.** `I`, cas `LeRegistreRefuseCeQuiManque`. Le test exige :
- la rubrique en capitales et en Noto Serif, sur ses deux filets ;
- la ligne absente qui dit « — Donnée absente » sans aucun « 0 » ;
- la ligne de 1250 qui dit « 1250 kg », alignée à droite.

Puis il éprouve les refus : un libellé, une unité ou une date vides, et une note « 3 sacs », lèvent l'exception sans laisser d'enfant. Le séparateur porte un seul losange. Contre-épreuve : une garde placée après la création laisse un enfant et rougit.

**SC6 — La galerie montre tout, sans rien couper.** `I`, cas `LaGalerieDuRegistreMontreTout`. Sur `GalerieDuRegistre.Creer()`, détruite en `finally`, le test exige :
- une seule `Canvas` ;
- les seize pastilles, les trois matières, la rubrique, les deux lignes, la note, le séparateur, le sceau et « Coin de l'écran » ;
- les neuf plaques. Le `Text` de chacune contient son signe et son mot déclarés. Le nombre de ses « Trait » ou « Tiret » suit sa forme (4, 8, au moins 8, 0), et leur épaisseur égale `Epaisseur` ;
- chaque `RectTransform` dans 1920 × 1080 ;
- chaque `Text` actif qui tient dans son cadre : `preferredHeight` ≤ sa hauteur, et `preferredWidth` ≤ sa largeur s'il ne revient pas à la ligne ;
- le pied « aucune partie chargée ».

Contre-épreuve : une plaque dont le mot est retiré, ou une plaque pointillée réduite à un trait plein, rougit.

**SC7 — L'infobulle d'un objet au coin reste entière à 1280 × 720.** `I`, cas `LInfobulleDUnObjetAuCoinResteEntiere`. La taille du feuillet est celle de `Infobulle.Montrer`, sur la plus longue phrase de la galerie du registre. Le test place un objet de 340 × 44 unités, collé à chacun des quatre coins, en 1280 × 720 puis en 1920 × 1080 (× largeur / 1920). Le point est le centre de l'objet. `Infobulle.Placer` doit rendre un rectangle entier dans l'écran, qui ne chevauche pas le rectangle de l'objet ; huit cas sont comptés. Le feuillet montré a pour sprite `FeuilletDInfobulle`, et aucun de ses graphiques n'est cible de rayon. Contre-épreuve : un feuillet posé sans l'écart de 24 px chevauche l'objet et rougit.

**SC8 — La photo, et ses deux contre-épreuves.** Les trois commandes de la section Photo :
- la première sort 0, avec ses images et ses rapports ;
- `-forge849OrSurPapier` sort 1, et son journal dit « or-vieilli sur papier : 2,0:1 » ;
- `-forge849Teinte` sort 1, et son journal dit « repos et reçu ne diffèrent que par leur teinte ».

**SC9 — Rien d'autre ne bouge.** Les commandes :
- `I` passe sur toute l'assemblée, sans retouche des cas existants de `SocleInterfaceTests`, `EtatsLectureTests`, `CabinetDeCarteTests` et `GestesDesJaugesTests`, et `P` passe aussi ;
- `git diff -U0 origin/master -- 3d/unity/Assets/Interface/Tests/` ne montre aucune ligne retirée, et aucun autre fichier de tests ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 1500 lignes, brief compris.

Contre-épreuve : un cas existant modifié, ou un fichier hors du Périmètre, refuse la livraison.

## Hors périmètre
- Appliquer la langue à un écran : la carte, son bandeau, la barre et ses jauges (#1032), les dossiers, la bande des modes (#858), les légendes et le menu. C'est #850, qui y pose les neuf états ; le panneau du pays, c'est #1033 ; la capitale, #851. `Commande`, `Panneau`, `Habiller`, `Engagement` et `EtatsLecture` ne changent pas ici.
- Le court délai avant l'infobulle : `SocleInterfaceTests` (#878) et `CabinetDeCarteTests` (#879, #880) attendent le feuillet au premier survol, et un délai les rougirait. La galerie le dit par le trait de cuivre.
- Le pigment d'atlas et le jeton `mer`, déjà livrés (#842) ; les couleurs des maisons.
- Tout nombre, tout service, tout fichier Python.

## Photo
La photo montre la galerie du registre, sur la pierre :
- en haut, les seize jetons nommés, avec leur hex ;
- puis la pierre, le bois brûlé et le métal ;
- le feuillet du registre : sa rubrique en `sang` sur deux filets, ses deux lignes de compte (l'une « — Donnée absente »), sa note, son séparateur à losange et le sceau de cire ;
- dessous, **les neuf états côte à côte**, chacun avec son nom, son trait, son signe et son mot ;
- au coin bas droit, « Coin de l'écran » et son infobulle au filet de cuivre, entière.

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot849.cs`, avec deux scénarios, `[ScenarioDeCapture(849, "1-galerie-1920x1080")]` et `[ScenarioDeCapture(849, "2-galerie-1280x720")]`. Toute absence échoue en nommant sa cause. Les étapes :
1. Scénario 1 : `GalerieDuRegistre.Creer()` dans la scène reçue. La toile « Registre » passe en `ScreenSpaceCamera` sur la caméra reçue, rendue à 1920 × 1080, comme `Lot1031.Tendre` (`camera.rect` plein, `targetTexture` à la taille, `planeDistance = nearClipPlane + 0.2f`). Il attend une image, puis `Canvas.ForceUpdateCanvases()`. `camera.pixelRect` doit faire 1920 × 1080.
2. `SocleInterface.Refuse(Paires)` doit être `null`. Avec `-forge849OrSurPapier`, on y ajoute `("or-vieilli", "papier", Texte)`, et le scénario échoue avec le message de `Refuse`.
3. `EtatsDuCabinet.Confondus(Table)` doit être `null`. Avec `-forge849Teinte`, reçu reprend la forme, l'épaisseur, le signe et le mot de repos, et le scénario échoue avec le message de `Confondus`.
4. Chaque `Text` actif, ramené à l'écran par `RectTransformUtility.WorldToScreenPoint(camera, …)`, est entier dans `pixelRect` et tient dans son cadre.
5. `pointerEnterHandler` sur « Coin de l'écran », au centre écran de la commande, avec l'`EventSystem` de la galerie. Il faut un seul « Infobulle » actif, qui dit la phrase de la commande, entier dans `pixelRect`, sans chevaucher le rectangle de la commande.
6. Dix images de pose, puis une nouvelle vérification des étapes 4 et 5. `CitadelPlayCheck.Capture(camera, <DossierDesCaptures>/lot849-galerie-1920x1080.png, 1920, 1080)`. Le rapport `lot849-galerie-1920x1080.json` donne :
   - chaque paire avec son contraste ;
   - les neuf déclarations ;
   - les rectangles de la commande du coin et du feuillet.

   La trace est `CAPTURE_849`.
7. Scénario 2 : le même, sur la galerie du scénario 1, retendue à 1280 × 720 : étapes 4 à 6, image `lot849-galerie-1280x720.png`, rapport `lot849-galerie-1280x720.json`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 849 -forgeTicks 1 -forgeCaptures 3d/unity/Temp/lot849-photo -logFile 3d/unity/Temp/lot849-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 849 -forgeTicks 1 -forgeCaptures 3d/unity/Temp/lot849-or-sur-papier -forge849OrSurPapier -logFile 3d/unity/Temp/lot849-or-sur-papier.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 849 -forgeTicks 1 -forgeCaptures 3d/unity/Temp/lot849-teinte -forge849Teinte -logFile 3d/unity/Temp/lot849-teinte.log
```

La première donne la photo. Elle sort 0 avec `*--1-galerie-1920x1080.png`, `*--2-galerie-1280x720.png`, `lot849-galerie-1920x1080.png`, `lot849-galerie-1280x720.png` et les deux rapports `.json`. Les deux autres sont les contre-épreuves : chacune sort 1 sans image, dans son dossier neuf, et son journal dit la cause attendue (SC8).

Le codeur ouvre lui-même les deux images aux définitions exactes et les regarde. Chacun de ces défauts refuse la livraison, même avec une sortie 0 :
- un état qu'on ne distingue de son voisin que par la couleur ;
- un texte coupé à 1280 × 720 ;
- une infobulle coupée ou posée sur sa commande ;
- une texture sous un petit texte.

Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, les sorties des deux contre-épreuves et ce que montrent les deux images.
