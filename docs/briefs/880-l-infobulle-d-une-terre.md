# Lot #880 — L'infobulle d'une terre
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Sur la carte, sous le cabinet, la terre survolée montre près du curseur son nom, son maître, la date et ses habitants. Ces lignes sont tirées de la même lecture que sa fiche et lui sont égales au même tick, et la vieille boîte de survol ne revient plus.

## Le joueur
Sur la carte, le joueur promène la souris. Près du curseur, la terre survolée dit son nom et la maison qui la tient, la date du monde et ses habitants, sans clic. Ce sont les trois premières lignes que sa fiche, le dossier « Territoire conservé », montrerait au même instant. La vieille boîte sombre du coin bas gauche, qui parlait en identifiants, a disparu. Quand le pointeur passe sur un bouton, le même feuillet dit ce que fait ce bouton. Il sent qu'il lit la carte comme un atlas : il trouve sa capitale, ses voisins et leurs maîtres sans ouvrir de dossier. C'est le dernier des trois sous-lots de #857 « L'infobulle au curseur », dans « La prise en main de la carte » (`CAP.md`, jalon 4), après #878 (le socle) et #879 (les phrases des commandes). Il sert les gestes du J4 « passer de la carte à sa ville d'un geste » et « paie au grenier » : le joueur trouve sa capitale et voit qui tient chaque terre avant de cliquer. #858 et #859 s'appuient sur ce feuillet.

## Règle du monde
Sans objet : c'est un lot de vue. Aucun nombre du monde ne change, ni `jeu/sim/`, ni `jeu/sim/MODELE.md`, ni le service. L'infobulle lit `/lieu?cell=`, comme le dossier, et n'ajoute aucune valeur qu'il ne montre pas (`docs/interface/DA.md`, « L'infobulle »).

## Périmètre
3d/unity/Assets/Interface/InfobulleDeTerre.cs
3d/unity/Assets/Interface/InfobulleDeTerre.cs.meta
3d/unity/Assets/Interface/CabinetDeCarte.cs
3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot880.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot880.cs.meta
docs/briefs/880-l-infobulle-d-une-terre.md

Tout autre chemin est interdit ; les `.meta` sont générés par Unity et entrent dans le diff. `Infobulle.cs`, `SocleInterface.cs`, `DossierTerritoire.cs` et `LectureDossier.cs` ne changent pas : ce lot les appelle. `FicheDeCellule.cs`, `SurvolDeCarte.cs`, `EpreuveCarte.cs` et leurs tests ne changent pas non plus : la fiche de survol, son texte et l'épreuve du jalon 2 qui le lit appartiennent à #872. Dans `CabinetDeCarteTests.cs`, les cas s'ajoutent après les cas existants ; aucune ligne existante n'est modifiée ni retirée. Budget : environ 45 lignes pour `InfobulleDeTerre.cs`, 6 dans le cabinet, 55 de tests, 75 de capture, 4 de `.meta` et 100 de brief, dans le style dense du dossier.

## Conditions de succès
`U` = `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`, sur le PC, éditeur fermé, depuis la racine, en PowerShell. `INTERFACE` = `U -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -assemblyNames Forge.Interface.Tests -testResults 3d/unity/Temp/lot880-interface.xml -logFile 3d/unity/Temp/lot880-interface.log`, sans `-quit`. Il faut une sortie 0, un XML sans échec ni cas ignoré, et chaque cas nommé réellement exécuté : zéro cas est un échec. Les tests s'écrivent d'abord et se voient rouges avant le code.

**`InfobulleDeTerre`** (espace `Forge.Interface`, `MonoBehaviour`) :
- `public const int LIGNES = 3; public const double PERIODE_S = 2;` (celle du dossier) ; `public bool automatique;` ; `public LectureDossier Lecture { get; set; }`, remplaçable par un test ; `public string TexteAffiche { get; private set; }`, nul quand l'infobulle de la terre est cachée.
- `public static string Decrire(string erreur, DocumentDuMonde document, long cellule)` rend les `LIGNES` premières lignes de `DossierTerritoire.Texte(erreur, document, cellule)`, jointes par `\n`, ou la seule ligne d'un état (attente, panne, dossier incomplet). Le texte vient du même code que la fiche ; rien n'est recalculé à part.
- `public void Initialiser(Canvas toile, LectureDossier lecture, Func<CelluleDeCarte> survolee)`.
- `public void Pas(Vector2 point, CelluleDeCarte terre, double maintenant)`. Avec `terre` nulle : si `TexteAffiche` n'est pas nul et que le feuillet « Infobulle » de la toile est actif avec ce texte, `Infobulle.Cacher(toile)`. Dans tous les cas, `TexteAffiche = null`. Le feuillet n'est caché que s'il porte encore le texte de la terre : la phrase d'un bouton, montrée dans la même image, reste. Sinon, avec `chemin = "/lieu?cell=" + terre.CellId` : si `!Lecture.EnCours` et (`Lecture.Cle != chemin` ou `maintenant ≥` la prochaine lecture), `_ = Lecture.Actualiser(chemin)` et la prochaine lecture passe à `maintenant + PERIODE_S`. Il n'y a jamais plus d'une lecture en vol : survoler vingt terres ne lance pas vingt requêtes au service. Le texte vaut `Decrire(…)` de l'erreur et du document de la lecture si `Lecture.Cle == chemin`, sinon `Decrire(null, null, id)`, l'attente : le document d'une autre terre n'est jamais lu pour celle-ci. Il ne se recalcule que si la terre, le document ou l'erreur change, car `TexteDuMonde.Absence` écrit au journal. Puis `Infobulle.Montrer(toile, TexteAffiche, point)`.
- `LateUpdate` (après `SurvolDeCarte`) : si `automatique` ou `Mouse.current == null`, rien. Sinon `Pas(position de la souris, survolee(), Time.realtimeSinceStartupAsDouble)`.

**`CabinetDeCarte`** : `Construire` installe une seule `InfobulleDeTerre`, avec `Initialiser(toile Cabinet, LectureDossier.Locale(carte.port), () => fiche.Survolee)`. `SurvolDeCarte` tient déjà `fiche.Survolee` à jour sous le cabinet, et la rend nulle sur un panneau. `Afficher`, appelé à chaque image, éteint en plus chaque enfant direct de la carte, autre que la toile « Cabinet », qui est actif et porte une `Canvas`. Aujourd'hui, `Construire` n'éteint que les toiles déjà actives à sa construction. Une `FicheDeCellule` démarrée après lui rallumerait la vieille boîte. Seuls les enfants directs sont parcourus : les cellules vivent sous « Cellules de la carte » et ne sont pas parcourues. La fiche de survol continue de lire, et `FicheDeCellule.TexteAffiche` reste celui de l'épreuve du jalon 2.

**SC1 — Les lignes de la fiche, et une seule lecture en vol.** `INTERFACE`, cas `LInfobulleDUneTerreDitLesLignesDeSaFiche`. Après le `SetUp` existant, la racine a exactement une `InfobulleDeTerre`, et en a encore une après un second `Construire`. Le test la met en `automatique` et remplace `Lecture` par une `LectureDossier` dont chaque appel attend un `TaskCompletionSource` et compte les chemins. Le témoin de la cellule 20 vaut `{"tick":8,"cell_id":20,"date":{"annee":1400,"jour_de_l_annee":9},"population":12345,"noms":{"maisons":{"m-1":{"nom":"Maison témoin"}}},"lieux":[{"rang":0,"nom":"Bourg témoin","population":12000,"surface_km2":12,"maitre":"m-1","stocks":{"nourriture":1234.5},"flux_30j":null}]}`. Celui de la cellule 10 est le même, avec `"cell_id":10` et le nom « Bourg dix ». Les terres 10 et 20 sont des `CelluleDeCarte` comme dans `UnTerritoireConserveSurvitALaFinDuSurvol`. La suite :
- `Pas(p, terre10, 0)` fait un appel, à « /lieu?cell=10 », et le texte vaut `DossierTerritoire.ATTENTE` ;
- `Pas(p, terre20, 0.1)`, lecture en vol, ne fait aucun nouvel appel, et le texte vaut `ATTENTE` ;
- quand la lecture de 10 rend son document, `Pas(p, terre20, 0.2)` fait le deuxième appel, à « /lieu?cell=20 ». Le texte vaut `ATTENTE`, jamais les lignes de « Bourg dix » ni « Dossier incomplet » ;
- quand 20 rend son document, le texte vaut exactement « Bourg témoin · Maison : Maison témoin\njour 9 de 1400\n » + `TexteDuMonde.Nombre(12345)` + « habitants dans le territoire ». Ces trois lignes égalent les trois premières de `DossierTerritoire.Texte(null, ce document, 20)`. Le feuillet « Infobulle » est seul actif sous la toile « Cabinet », avec ce texte ;
- `Pas` à 1 s ne relit pas, `Pas` à 2,3 s fait le troisième appel.

Contre-épreuves dans le même cas : avec un document du tick 9, au « jour 10 de 1400 », la deuxième ligne diffère de celle du dossier au tick 8, et le test le constate. Une lecture lancée à chaque changement de terre, ou le document de 10 montré pour 20, rougit.

**SC2 — La phrase d'un bouton n'est pas effacée par la terre.** `INTERFACE`, cas `LInfobulleDeLaTerreLaisseLaPhraseDUnBouton`. Avec la terre 20 lue (comme en SC1), `Pas` la montre. Puis, comme `LeCabinetMontreLaPhraseDuBoutonSurvole`, le test envoie `pointerEnterHandler` à « Pause / Reprendre » au centre écran du bouton. Ensuite `Pas(ce point, null, t)` laisse le feuillet actif avec la phrase du bouton, et `TexteAffiche` est nul. `pointerExitHandler` le cache. `Pas(p, terre20, t)` remontre la terre, puis `Pas(p, null, t)` cache le feuillet. À la fin, la racine a une seule `Canvas` active. Contre-épreuve : un `Cacher` sans condition efface la phrase du bouton et rougit.

**SC3 — La vieille boîte reste éteinte.** `INTERFACE`, cas `LaVieilleBoiteDeSurvolSEteintSousLeCabinet`. Le test donne une caméra neuve à la `CarteDessinee` de la racine, puis appelle `FicheDeCellule.Demarrer()` après `Construire` : la fiche démarre après le cabinet. Il exige d'abord « Toile de la fiche » active : c'est le rouge d'aujourd'hui, l'ordre est réel. Après `cabinet.Afficher()`, cette toile n'est plus `activeInHierarchy`, et la racine n'a qu'une `Canvas` active, « Cabinet ». Il finit par `fiche.Arreter()` et détruit la caméra. Contre-épreuve : sans l'extinction dans `Afficher`, le cas rougit.

**SC4 — La photo, et sa contre-épreuve.** Les deux commandes de la section Photo. La première sort 0 avec ses deux images. La seconde sort 1, et son journal contient « l'infobulle et la fiche diffèrent ».

**SC5 — Rien d'autre ne bouge.**
- `INTERFACE` passe sur toute l'assemblée, cas existants compris : `CabinetDeCarteTests` (une seule `Canvas`, trois boutons au bandeau, `UnTerritoireConserveSurvitALaFinDuSurvol`, les 26 commandes de #879), `SocleInterfaceTests` et `DossierTerritoireTests` ;
- `git diff -U0 origin/master -- 3d/unity/Assets/Interface/Tests/CabinetDeCarteTests.cs` ne montre aucune ligne retirée ;
- `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne listent que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 300 lignes, brief compris.

Contre-épreuve : un cas existant modifié, ou un fichier hors du Périmètre, refuse la livraison.

## Hors périmètre
- Le texte de la fiche de survol (`FicheDeCellule`), le bandeau et l'épreuve du jalon 2 : #872.
- Le trait de cuivre sur la terre survolée, le filet du feuillet, son court délai et les jetons : #849 et #850.
- Les modes de carte et leurs légendes (#858), la barre du haut (#859), l'infobulle dans la capitale en 3D.
- Tout nombre du monde, tout service, toute nouvelle route de lecture.

## Photo
Deux images, dans l'ordre de leurs noms. La première montre la carte de 1400 et le vrai cabinet sur le vrai service. Le pointeur est sur le bourg de la Morée. Près de lui, le feuillet de papier dit « Mistra · Maison : … », la date, puis les habitants du territoire, entier et pas sur le point. À droite, « Territoire conservé » ouvert sur la Morée commence par les mêmes trois lignes. Aucune boîte sombre en bas à gauche. La seconde montre le pointeur au centre de « Pause / Reprendre », et le feuillet dit « Arrête le temps du monde, ou le relance à la vitesse choisie. ».

Le codeur écrit `3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot880.cs`, sur le modèle de `Lot873` et `Lot879`, avec deux scénarios. Le second reprend la carte du premier par des champs statiques, comme `Lot729`. Il réutilise `Lot549.Ouvrir/Photographier` et les aides `internal` de `Lot690` sans les changer. Chaque attente est bornée par `Lot690.Jusqua`, et chaque absence échoue en nommant sa cause.

`[ScenarioDeCapture(880, "1-terre-survolee")]` :
1. Ouvrir `Forge_Carte` et exiger le `CabinetDeCarte`, la toile « Cabinet » active et une seule `InfobulleDeTerre`. Passer `SurvolDeCarte`, `ParcoursDeCarte` et l'`InfobulleDeTerre` en `automatique`, puis attendre `Lot690.LecturePrete(cabinet.Partie)`.
2. Prendre la fiche de départ au siège « Mistra », lire le rang 0 de `/lieu?cell=` (nom et point, comme `Lot873.Bourg`), zoomer de 12 crans et centrer sur le bourg. `survol.Survoler(carte.camera.WorldToScreenPoint(point))` doit rendre `fiche.Survolee` égale à la Morée. Garder la terre retenue par `cabinet.Garder` : la Morée. Avec `-forge880Voisin`, garder à la place la cellule sous le bourg du premier voisin servi (`carte.CelluleSous`), dont le nom de bourg doit différer.
3. `Lot549.Photographier(camera, carte)`, `camera.rect` plein, toile « Cabinet » en `ScreenSpaceCamera` sur la caméra reçue (`planeDistance = nearClipPlane + 0.2f`), une image d'attente, puis `Canvas.ForceUpdateCanvases()`. Le point `P` est le bourg ramené à l'écran de la caméra reçue.
4. À chaque image, `terre.Pas(P, fiche.Survolee, maintenant)`, jusqu'à ce que `TexteAffiche` commence par le nom du bourg suivi de « · ». Attendre ensuite que le dossier ait un document au même tick que la lecture de l'infobulle (`dossier.Document.Tick == terre.Lecture.Document.Tick`). Ses trois premières lignes doivent égaler, une à une, celles de `TexteAffiche`. Sinon, échouer par « l'infobulle et la fiche diffèrent : » suivi des deux textes.
5. Exiger : un seul « Infobulle » actif sous la toile, de texte `TexteAffiche`, ses quatre coins dans `camera.pixelRect` et hors du carré de 48 px centré sur `P` ; « Toile de la fiche » non `activeInHierarchy` ; une seule `Canvas` active sous la carte ; le cadre de « Territoire conservé » entier dans l'image.
6. Dix images de pose, avec `Pas` à chaque image, puis revérifier 4 et 5. La trace `CAPTURE_880` donne la cellule, `P`, le rectangle du feuillet, ses trois lignes et le tick commun.

`[ScenarioDeCapture(880, "2-bouton-survole")]` : réactiver la caméra de la carte si la photo l'a éteinte. Le point `B` est le centre de « Pause / Reprendre », ramené à l'écran. Le premier résultat de `EventSystem.current.RaycastAll` en `B` est ce bouton ou un de ses enfants. Comme le ferait la souris, le scénario fait `fiche.Quitter()`, envoie `pointerEnterHandler` au bouton en `B`, puis `terre.Pas(B, null, maintenant)`. Il exige un seul « Infobulle » actif, de texte égal à `Infobulle.Phrase` du bouton, entier dans `camera.pixelRect` et hors du carré de 48 px autour de `B`, et `TexteAffiche` nul. Il pose dix images, revérifie, puis trace `CAPTURE_880`.

Les commandes, depuis la racine, en PowerShell, sans `-quit` ni `-nographics` :

```
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 880 -forgeCaptures 3d/unity/Temp/lot880-photo -logFile 3d/unity/Temp/lot880-photo.log
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 880 -forgeCaptures 3d/unity/Temp/lot880-voisin -forge880Voisin -logFile 3d/unity/Temp/lot880-voisin.log
```

La première sort 0 avec `*--1-terre-survolee.png` et `*--2-bouton-survole.png` : c'est la photo. La seconde, la contre-épreuve, sort 1 sans la première image, et son journal dit « l'infobulle et la fiche diffèrent ». Le codeur ouvre les images lui-même. Chacun de ces défauts refuse la livraison, même avec une sortie 0 : un feuillet absent, coupé, posé sur le point ou d'un autre texte, une boîte sombre visible, ou un dossier dont les premières lignes diffèrent du feuillet. Les PNG restent hors du dépôt. Le compte rendu donne les commandes, le rouge initial des tests, la sortie de la contre-épreuve et ce que montrent les deux images.
