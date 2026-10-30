# Lot #897 — Une session Unity relève les ouvriers au chantier puis le bourg vidé
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Sur le vrai service d'épreuve, une session Unity photographie à Biskra un ouvrier qui marche sur la route en chantier, au milieu des paysans, puis la même rue vide une fois le bourg vidé. Elle écrit ce que la scène porte réellement, passant par passant.

## Le joueur
Le joueur entre dans Biskra après avoir tracé trois routes. Il voit un ouvrier marcher sur l'une d'elles, au milieu des paysans qui vont aux sorties de la ville. Quand les gens du bourg partent, la rue se vide. Il sent que chaque bras pris aux champs se voit dans sa capitale, et que la ville ne lui ment pas. Ce lot de fond prépare l'écran du J4, « une ville vivante dont chaque passant suit le monde », et sa décision, « des bras au chantier, c'est moins de bras aux champs » (`CAP.md`, jalon 4). C'est le sous-lot 2 de #789, lui-même découpé de #421 « Les gens du bourg circulent dans les rues ». #788 n'avait prouvé le bourg vide qu'avec des lectures fabriquées dans Unity : ici, tout vient du service. Le juge `pc/epreuve_passants.py` (sous-lot 3 de #789) lancera cette session et rendra le verdict. La demande n'a pas de phrase « Le joueur » séparée : celle-ci en dit le bénéfice, selon « La règle d'un lot ».

## Règle du monde
Sans objet : outil d'épreuve et vue, aucune règle neuve. La session lit sans les changer « Les lieux d'une cellule, vue dérivée », « Les foyers par métier », « Le plan du bourg » et « Le chantier et ses bras » de `jeu/sim/MODELE.md`, ainsi que le montage `POST /epreuve/vider-bourg` (#896, livré d0de813f). Les effectifs (`PassantsDuBourg`, #784 : un passant pour dix habitants du bourg) et les trajets (`TrajetsDesMetiers`, #787 : les ouvriers vont aux chantiers qui emploient des bras ce jour-là, les paysans aux sorties déclarées) restent inchangés.

**Dépend de : #896**, livré. Rien ne change dans `jeu/`, `Pont/`, `Desert/`, `ForgeCapture.cs` ni dans aucun test.

**Mesures du chef**, service `--epreuve`, graine 0, par HTTP. Biskra = cellule 10103, seigneurie 6, place carrée de ±50 m. Le choix au tick 0, puis `POST /tick?n=1`, puis trois `tracer_route` acceptés au tick 1 (`maison` « seigneurie-6 », points `[[0,d],[40,d]]` pour d = 0, 8, 16, `largeur_m` 4), puis quatre ticks. Au tick 5, le bourg a 165 habitants, la cellule 3 444 paysans et 15 ouvriers, et les rues 0, 1 et 2 emploient 5 bras chacune. #784 donne alors 16 passants : 1 ouvrier, qui va vers « rue 0 », et 15 paysans, répartis sur les sorties « base 0 » à « base 6 ». « base 0 » va de (50 ; 11,4) à (64,6 ; 14,8), juste au bout des trois routes. `vider-bourg` rend 200 `{"cell_id":10103,"tick":5}`, et `/lieu` sert alors un bourg à 0. Un tick de plus : au tick 6, le bourg est toujours à 0, avec 13 ouvriers pris aux autres lieux et des bras 5, 5 et 3.

**Pourquoi ce tick de plus.** #896 republie le monde sans avancer le tick. Or `PassantsDeLaVille` (#788) ignore toute relecture du tick qu'il a déjà appliqué. La session joue donc `POST /tick?n=1` après le montage, et le composant remplace la foule de lui-même, au tick 6. La session n'appelle jamais `Presenter`, `Retirer` ni `Tenir`, et ne fabrique ni `Lieu` ni `PlanLu`.

**Le nom du fichier.** L'issue dit `Lot789.cs`. Le fichier sera `Captures/Lot897.cs` (`-forgeLot 897`), car le PC rejoue les captures sous le numéro du lot.

**La session**, dans `Captures/Lot897.cs`, comporte deux scénarios : `[ScenarioDeCapture(897, "01-ouvriers-au-chantier")]` et `[ScenarioDeCapture(897, "02-bourg-vide")]`. Ils partagent leur état par des champs statiques. Ils réutilisent `Lot362.Deposer`, `Lot362.Tick`, `Lot362.Lire` et `Lot362.Monde` sans les modifier. Toute lecture HTTP se fait hors du fil Unity, comme dans `Lot788`.
1. **01.** La session refuse un rapport antérieur dans `Capture.DossierDesCaptures`. Elle refuse aussi deux drapeaux de contre-épreuve donnés ensemble : exception nommée avant toute requête. Elle masque le panneau et les `TextMesh`, comme `Lot788`. Le départ est l'unique fiche de `ClientDeparts` dont le siège se nomme « Biskra ». Viennent ensuite le choix, un tick, les trois routes ci-dessus et quatre ticks. Puis `outil.Ouvrir(cellule)` et l'attente (30 s au plus) de `PassantsDeLaVille.CelluleAppliquee == cellule` et `TickApplique == 5`. Enfin, la session lit elle-même `/lieu` et `/plan` (`ClientLieu`, `ClientPlan`) et exige la même cellule, le tick 5 des deux côtés et au moins un chantier de rue avec des bras.
2. **La caméra.** `DesertCityCamera.Poser` vise `Lot362.Monde(t, 32, 8)` en 1600 × 900, avec une inclinaison de 25 à 40° et la plus petite distance qui tient dans [0,05 ; 0,95] de l'image les deux bouts des trois routes et de « base 0 ». Ce cadrage est gardé tel quel pour 02. La session laisse passer 10 images, puis relève l'état « chantier » et rend la main pour la photo.
3. **02.** `POST /epreuve/vider-bourg?cell=10103` : exiger 200, la cellule et le tick 5. Relire `/lieu` : bourg à 0. Puis `Lot362.Tick`, l'attente (30 s au plus) de `TickApplique == 6`, la relecture de `/lieu` et `/plan` au tick 6, le même cadrage, 10 images, et le relevé de l'état « vide ».
4. **Le relevé** se fait sur la scène, jamais sur le bilan du composant. Un passant est un `MeshFilter` **actif** de la scène (`FindObjectsByType`, inactifs exclus) dont le `sharedMesh` est `outil.maillageCivil`. Pour chacun, on relève :
   - `id` (`GetInstanceID`), `nom`, puis `metier` et `destination`, lus dans le nom « métier|destination|indice » ;
   - `x`, `y`, ses coordonnées dans le plan (−x et −z d'Unity) ;
   - `ecart_trajet_m`, la distance horizontale à la polyligne du trajet de même destination, calculée par `TrajetsDesMetiers.Calculer` sur le `/plan` lu (−1 si cette destination n'existe pas) ;
   - `ecart_chantier_m`, la distance à la plus proche rue du plan dont le chantier du jour a des bras (−1 s'il n'y en a aucune) ;
   - `visible` : les 8 coins de ses bornes dans [0,03 ; 0,97] de l'image.

   Si la scène porte déjà un objet de ce maillage hors de la foule, le codeur le dit dans la PR, sans l'exclure par son nom.
5. **Le rapport** est `passants-bourg.json`, en UTF-8 sans BOM, réécrit à chaque relevé. `defaut` vaut « étape : message » si une exception survient (puis on la relance), et devient `null` après le relevé de 02. On y trouve `cellule`, `port`, `contre_epreuve` ("" ou le nom du drapeau, sans tiret) et exactement deux `etats`, « chantier » puis « vide ». Chaque état porte :
   - `tick_lieu`, `tick_plan` et `tick_applique` ;
   - `bourg` (la population lue du rang 0) ;
   - `projete` et `pose`, ceux du composant ;
   - `attendu`, les parts de `PassantsDuBourg.Projeter` sur la lecture de la session ;
   - `trajets` : métier → destinations accessibles ;
   - `chantiers` : `nature`, `identifiant`, `bras` ;
   - `passants` (le compte relevé), `par_metier` (relevé lui aussi), `liste` et `camera` (la matrice projection × vue).

   −1 veut dire « non calculé » ; 0 est une mesure.

**Trois drapeaux faussent la scène, pas le rapport.** Chacun est appliqué après que le composant a appliqué son tick, et avant le relevé :
- `-forge897PassantEnTrop` (le nombre) : une copie du premier paysan, sous la racine de la foule, avec le même nom, posée 0,6 m à sa droite ;
- `-forge897OuvriersAilleurs` (la destination) : chaque ouvrier est désactivé et remplacé par une copie immobile, de même nom, posée au milieu du premier trajet paysan accessible ;
- `-forge897GarderAnciens` (le maintien indu) : juste avant `vider-bourg`, tous les enfants de la racine passent sous un objet « Anciens gardés » (`SetParent(…, true)`). Ils gardent ainsi leurs identifiants.

Avec un drapeau, la session sort 0. C'est le contrôle ci-dessous qui doit rougir.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot897.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot897.cs.meta
docs/briefs/897-une-session-unity-releve-les-ouvriers-au-chantie.md

Tout autre chemin est interdit. Budget : environ 150 lignes de code, 11 de `.meta` (générée par Unity), le reste au brief.

## Conditions de succès
Toutes se jouent sur le PC, depuis la racine, éditeur fermé, avec rendu, sans `-quit` ni `-nographics`. Chaque dossier doit être neuf. `CONTROLE <dossier>` désigne `py -3 -c $controle <dossier>`, avec ce code indépendant :
```powershell
$controle = @'
import json,sys
from pathlib import Path
r=json.loads((Path(sys.argv[1])/'passants-bourg.json').read_text(encoding='utf-8-sig')); a,b=r['etats']
assert r['defaut'] is None and r['cellule']==10103 and (a['nom'],b['nom'])==('chantier','vide')
assert a['tick_lieu']==a['tick_plan']==a['tick_applique']==5 and b['tick_lieu']==b['tick_plan']==b['tick_applique']==6
assert a['bourg']==165 and b['bourg']==0 and a['camera']==b['camera'] and a['projete']==16
assert a['attendu']=={'ouvriers':1,'paysans':15} and any(c['nature']=='rue' and c['bras']>0 for c in a['chantiers'])
assert a['passants']==len(a['liste'])==16 and a['par_metier']==a['attendu'], 'nombre'
assert len({p['nom'] for p in a['liste']})==len({p['id'] for p in a['liste']})==16, 'nombre'
bras={'rue %d'%c['identifiant'] for c in a['chantiers'] if c['nature']=='rue' and c['bras']>0}
assert all(0<=p['ecart_trajet_m']<=0.05 for p in a['liste']), 'destination'
assert all(p['destination'] in bras and 0<=p['ecart_chantier_m']<=0.05 for p in a['liste'] if p['metier']=='ouvriers'), 'destination'
assert sum(p['visible'] for p in a['liste'] if p['metier']=='ouvriers')>=1 and sum(p['visible'] for p in a['liste'] if p['metier']=='paysans')>=2
assert b['projete']==b['pose']==b['passants']==0 and b['liste']==[] and b['attendu']=={}, 'maintien'
print('ok', a['passants'], a['par_metier'], '->', b['passants'])
'@
```

SC1 — **La rue suit le monde.** On joue la commande P de la section Photo, qui doit sortir 0, puis `CONTROLE 3d/unity/Temp/lot897-photo`, qui doit sortir 0 et afficher `ok 16 {'ouvriers': 1, 'paysans': 15} -> 0`. Le codeur montre d'abord le rouge de ce contrôle (rapport absent avant le code), puis son vert. Contre-épreuve : SC2, SC3 et SC4. Une session qui recopie le bilan du composant au lieu de parcourir la scène les laisse verts, et refuse donc la livraison.

SC2 — **Le nombre.** On joue la commande C1, qui doit sortir 0, puis `CONTROLE 3d/unity/Temp/lot897-en-trop`, qui doit sortir 1 sur `AssertionError: nombre`. Le rapport porte `passants` 17 à l'état « chantier ».

SC3 — **La destination.** On joue la commande C2, qui doit sortir 0, puis `CONTROLE 3d/unity/Temp/lot897-ailleurs`, qui doit sortir 1 sur `AssertionError: destination`. L'ouvrier relevé a `ecart_chantier_m` > 5.

SC4 — **Le maintien indu.** On joue la commande C3, qui doit sortir 0, puis `CONTROLE 3d/unity/Temp/lot897-anciens`, qui doit sortir 1 sur `AssertionError: maintien`. Les `id` de l'état « vide » sont ceux de l'état « chantier ».

SC5 — **Les images, regardées.** Chacun des quatre dossiers contient `*--01-ouvriers-au-chantier.png` et `*--02-bourg-vide.png`, avec leurs traces `CAPTURE_SCENARIO_OK`. Le codeur ouvre les huit images lui-même :
- P/01 montre les trois routes en chantier, un ouvrier entier sur l'une d'elles et au moins deux paysans entiers ;
- P/02 montre le même cadre, sans aucun civil ;
- C1/01 montre deux civils presque superposés ;
- C2/01 montre l'ouvrier immobile sur la sortie « base 0 » ;
- C3/02 montre les civils restés dans la rue.

Contre-épreuve : un cadre sans route, un civil coupé ou hors sol, ou une seconde image prise avant le tick 6 refusent la photo, même si les chiffres passent.

SC6 — **Les arguments.** La commande P, avec en plus `-forge897PassantEnTrop -forge897GarderAnciens`, vers `3d/unity/Temp/lot897-deux`, sort non zéro. Son journal nomme les deux drapeaux, et aucun dépôt n'est fait.

SC7 — **Les acquis et le budget.**
- Les tests EditMode restent verts : `& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -nographics -projectPath 3d/unity -runTests -testPlatform EditMode -testResults '3d/unity/Temp/lot897-tests.xml' -logFile '3d/unity/Temp/lot897-tests.log'`. Le XML doit être neuf et non vide, sans échec ni cas ignoré.
- `python3 -m pytest jeu -q` passe sur le VPS.
- `git diff --check`, `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ; `git diff --numstat origin/master` totalise moins de 300 lignes.

Contre-épreuve : un changement dans `Lot362.cs`, `Lot788.cs`, `ForgeCapture.cs`, `PassantsDeLaVille.cs`, `Pont/`, `jeu/` ou un test refuse la livraison.

## Hors périmètre
- Le juge et son lanceur `pc/epreuve_passants.py` (sous-lot 3 de #789) : service de référence, comparaison, verdict.
- Tout changement de `PassantsDeLaVille`, `PassantsDuBourg`, `TrajetsDesMetiers`, `DesertRoadTool`, des scènes, du service, du montage `vider-bourg` ou du moteur. En particulier, le remplacement de la foule sur une republication au même tick : si cela semble nécessaire, le codeur le dit dans la PR, sans l'écrire.
- Aucun rapport ni aucune image versé dans git, aucune section de README, aucune optimisation (#422).

## Photo
`Lot897.cs` joue la session ci-dessus. La photo est 01 : Biskra au tick 5, les trois routes en chantier tracées sur la place, un ouvrier qui marche sur la route 0 et les paysans de la sortie « base 0 ». 02 montre le même cadre au tick 6, la rue vide. Avec un drapeau, l'image montre l'anomalie. Joindre au compte rendu les huit images, les quatre `passants-bourg.json`, les quatre journaux et les sorties de `CONTROLE`.

Photo, commande P :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 897 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures '3d/unity/Temp/lot897-photo' -logFile '3d/unity/Temp/lot897-photo.log'
```
Contre-épreuve C1, le nombre :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 897 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forge897PassantEnTrop -forgeCaptures '3d/unity/Temp/lot897-en-trop' -logFile '3d/unity/Temp/lot897-en-trop.log'
```
Contre-épreuve C2, la destination :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 897 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forge897OuvriersAilleurs -forgeCaptures '3d/unity/Temp/lot897-ailleurs' -logFile '3d/unity/Temp/lot897-ailleurs.log'
```
Contre-épreuve C3, le maintien indu :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 897 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forge897GarderAnciens -forgeCaptures '3d/unity/Temp/lot897-anciens' -logFile '3d/unity/Temp/lot897-anciens.log'
```
Les quatre commandes sortent 0. Le rouge des contre-épreuves est celui de `CONTROLE` (SC2 à SC4).
