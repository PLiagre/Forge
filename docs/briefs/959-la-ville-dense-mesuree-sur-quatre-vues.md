# Lot #959 — La ville dense mesurée sur quatre vues
Jalon : J4 · Machine : pc · Taille prévue : 220 lignes

## But
Forge sait monter, à Biskra, une capitale dense : 600 maisons, 80 passants, un chantier de maison, une fumée et une lampe sur chaque maison habitée, les étals du panier, un soir. Elle mesure ensuite le temps d'image de quatre vues (survol, rue, place, chantier) et verse cette mesure, prise avant toute optimisation, dans `docs/mesures/422-capitale-dense/`.

## Le joueur
Le joueur ne gagne encore aucun geste, mais il voit la photo : sa capitale pleine, au soir, sous les quatre regards qu'il porte sur elle. Il la survole, marche dans une rue, regarde la place et suit son chantier, et chaque vue dit ce que coûte une image. C'est le sous-lot 3 de #422 « La capitale dense tient 60 images par seconde », et il prépare le geste du J4 « entre dans sa capitale en 3D, y marche », et son écran « une ville vivante dont chaque fumée, chaque étal et chaque passant suit le monde » (`CAP.md`, jalon 4). Cette mesure dit où la ville saccade. Les sous-lots 4 (maisons et enceinte regroupées) et 5 (LOD des fumées et des lampes) l'accéléreront, et le sous-lot 6 la rejouera pour prouver un 95e centile sous 16,7 ms. Ce que le joueur sentira, à la fin de #422 : sa capitale dense ne saccade pas quand il la survole ou y marche.

## Règle du monde
Sans objet : lot de vue et de mesure. Aucune règle ni aucun nombre du monde ne change, et `jeu/` n'est pas touché. La ville dense est celle de l'épreuve de #957 (`jeu/sim/MODELE.md`, « Ville d'épreuve (#957, outil de mesure de #422, réponse B du propriétaire) ») : `POST /epreuve/ville-dense?cell=C` porte le bourg à 800 habitants et sert dans `/plan` et `/occupation`, au même tick, une base de 600 maisons d'un foyer. Aucun geste n'y est joué après ce `POST`. Niveau de fidélité : sans objet.

**Ce que le chef a relevé (01/11/2026, master ef239f78).**
- Le service de la capture tourne avec `--jours-par-seconde 0` (`ForgeCapture.cs`, ligne 195), et `-forgeServiceEpreuve` ajoute `--epreuve` : le `POST` de #957 y est permis. Biskra est la cellule 10103, son seul départ a le siège « Biskra » (`ClientDeparts`, comme `Lot897.cs`).
- Les gestes de bâtisseur exigent un départ appliqué (`service.py`, environ ligne 802). Le service y met lui-même `maison`. Une parcelle se découpe le long d'une rue de geste, même en chantier (`intentions.py`, `_decoupe_parcelle`). Un bâtiment se pose sur une parcelle du plan, même en chantier : il attend alors la parcelle (`chantiers.py`). Il faut donc quatre ticks : départ, route, parcelle, maison.
- `DesertRoadTool.Ouvrir(cellule)` relit le plan et redessine tout : rues, parcelles, bâtiments, rues de 1400, maisons (`DessinerBatiments`, puis `maisons.Dessiner(lu.Base)`). Appelé après le `POST`, il dessine les 600 maisons. `DesertMaisons1400` expose `Posees`, `Foyers` et `Refus`.
- `PassantsDeLaVille` n'applique qu'une fois par paire (cellule, tick) : après un `POST` qui republie au même tick, la foule ne change pas (`Lot897.cs` l'a déjà noté). `Retirer()` est public : appelé après le `POST`, il fait relire la paire au prochain relevé (0,25 s). Un passant pour dix habitants du bourg (`PassantsDuBourg.HABITANTS_PAR_PASSANT`), donc 80 pour 800.
- Le montage de fumée, lampe et étal existe dans `EpreuveVieDuBourg.Monter`, mais il est privé et tient à son témoin. On ne le touche pas, on en reprend les réglages : `AlpineBuilder.Smoke`, `effet_fumee.mat`, `EffetsDeMaison.PourLaBase`, `EtalDuBourg.Configurer`, `EpreuveVieDuBourg.Heure` (19,6, public).
- Le banc (#958) : `BancDuTempsDImage.Mesurer(camera, chauffe, images, rendre)` se déroule par `while (m.MoveNext()) yield return null;`. Il rend lui-même en 1920 × 1080 sans vSync ni plafond. `OptimisationsDeLaVille.Actives` n'est lu par rien : à ce commit, toute mesure est « d'avant ».
- Un scénario a 60 s (`DELAI_SCENARIO_S`). Une mesure de 60 + 300 images en tient 165 ms par image. C'est pourquoi le montage et chaque vue sont des scénarios séparés.
- La photo d'un scénario est `CitadelPlayCheck.Capture` de la caméra, en 1600 × 900. Un `TextMesh` de la scène y paraît, une interface en surimpression non.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot959.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot959.cs.meta
docs/mesures/422-capitale-dense/avant.json
docs/mesures/422-capitale-dense/LISEZMOI.md
docs/briefs/959-la-ville-dense-mesuree-sur-quatre-vues.md

Tout autre chemin est interdit. Budget du `numstat`, hors brief : `Lot959.cs` 190, `.meta` 2, `avant.json` 1 (une ligne), `LISEZMOI.md` 25.

**`Editor/Captures/Lot959.cs`**, espace de noms `ForgeLocal3D.Captures`, dans le style de `Lot897.cs` : `static class Lot959`, un `Derouler` qui inscrit « étape : message » au rapport puis relance l'exception, et un `Ecrire(defaut)` qui réécrit le rapport à chaque étape. Le rapport s'appelle `lot959-ville-dense.json`, dans `Capture.DossierDesCaptures`, en UTF-8 sans BOM et sur une ligne. Son `defaut` nomme l'étape tant que le scénario 5 n'a pas fini, puis vaut `null`. Il réutilise `Lot362.Deposer`, `Lot362.Tick` et `Lot362.Monde`. Il ne modifie aucun autre fichier.

Drapeaux, constantes du fichier : `-forge959SansVille` (le `POST` n'est pas fait) et `-forge959SansEffets` (ni fumée, ni lampe, ni étal montés). Les deux ensemble : refus avant toute requête. Le rapport porte `contre_epreuve` : `""`, `"forge959SansVille"` ou `"forge959SansEffets"`.

Cinq scénarios, joués dans l'ordre de leur nom :

1. `[ScenarioDeCapture(959, "1-montage")]`
   - Refuse un rapport déjà présent (« rapport antérieur »), avant toute requête.
   - Prépare la scène comme `Lot897` : `automatique` sur l'outil, la caméra et le marcheur ; `VillageV2Visit` coupé ; `showPanel` faux ; `/Panneau du lieu` et les `TextMesh` de la scène désactivés.
   - Lit les départs et garde le seul dont le siège est « Biskra ». Puis, au tick 0 : `choisir_depart`, tick (1). `tracer_route` de (0 ; 0) à (40 ; 0), 4 m, en mètres du plan, tick (2). `decouper_parcelle` sur cette rue (son identifiant lu au plan) : segment 0, `debut_m` 4, `facade_m` 10, `profondeur_m` 15, côté gauche, tick (3). `poser_batiment` `maison` sur cette parcelle, tick (4).
   - Sauf sous `SansVille` : `POST /epreuve/ville-dense?cell=10103`. Il doit rendre 200, `cell_id` 10103 et `tick` 4, sinon il échoue en nommant le statut et le corps.
   - `outil.Ouvrir(cellule)`, puis `foule.Retirer()`.
   - Lit `/lieu`, `/plan`, `/bourg` et `/occupation` hors du fil, comme `EpreuveVieDuBourg.Lire` avec `ClientLieu` en plus. Cellule et tick doivent concorder (4).
   - Exige, dans cet ordre et chaque refus nommé :
     - `Maisons.Posees == 600`, `Foyers == 600`, `Refus` vide. Message : « 600 maisons attendues, N posée(s) », suivi des refus ;
     - le bourg à 800 ;
     - un bâtiment `maison` dessiné, à l'état `piquets` ou `murs` ;
     - puis, en au plus 30 s, `foule.CelluleAppliquee == 10103`, `TickApplique == 4`, `NombreProjete == 80`, `NombrePose == 80`, et 80 `MeshFilter` actifs au `maillageCivil` sous `foule.Racine`.
   - Sauf sous `SansEffets`, monte les effets :
     - sur **chaque** maison dessinée (case de `MaisonsDeLaBase.Poser` retrouvée par son nom « Maison r indice i »), une fumée et une lampe réglées comme dans `EpreuveVieDuBourg.Monter`, puis `EffetsDeMaison.PourLaBase` ;
     - **un étal par marchandise** du panier du bourg dont le stock lu est > 0, par ordre de nom. Chaque étal a un comptoir et une garniture, avec les matériaux de `Monter`. Sa référence est son stock lu. Les étals sont alignés sur la place, espacés de 5 m, centrés en (gx ; gy − 12), où (gx ; gy) est le barycentre de `plan.Base.Place`. Chaque coin de comptoir doit tomber dans l'emprise de la place, sinon le scénario échoue.
   - Règle `env.hour = EpreuveVieDuBourg.Heure`, puis `env.Apply()`. Applique les effets (`Appliquer`) : une cause non nulle fait échouer. Laisse passer au moins 60 images, au plus 600, jusqu'à ce que chaque fumée montée ait des particules.
   - Relève ensuite sur la scène : `fumees`, les `EffetsDeMaison` dont la fumée émet avec des particules ; `lampes`, ceux dont la lampe est allumée avec une intensité > 0 ; et chaque étal (`marchandise`, `reference_kg`, `rapport`, `cause`). Puis pose la caméra de la vue survol (ci-dessous), sans étiquette.
2. `"2-survol"`, 3. `"3-rue"`, 4. `"4-place"`, 5. `"5-chantier"` : chacun échoue si le scénario 1 n'a pas monté la ville. Il détruit l'étiquette de la vue précédente, pose sa caméra par `DesertCityCamera.Poser` (aspect 1600/900), laisse passer 10 images et relève les contrôles. Il mesure ensuite par `BancDuTempsDImage.Mesurer(camera, 60, 300, …)` (rendu vrai). **Après** la mesure, il pose l'étiquette, puis 10 images avant la photo.
   - **survol** : visée au barycentre de la place, cap 180, inclinaison 40. Distance : la plus petite, de 100 m à 450 m par pas de ×1,05, qui tient le centre de chacune des 600 maisons dans [0,02 ; 0,98] de l'image. Aucune : échec.
   - **rue** : la plus longue rue de `plan.Base.Rues`. Visée au point situé à 60 % de sa longueur depuis son premier point, cap tourné vers ce premier point, inclinaison 8, distance 12.
   - **place** : visée au centre de la rangée d'étals, cap du barycentre de la place vers ce centre, inclinaison 22, distance 28. Sous `SansEffets`, la visée est le point (gx ; gy − 12).
   - **chantier** : visée au centre des bornes de la pièce « Bâtiment <id> » de `outil.RacineBatiments`, cap 180, inclinaison 35, distance 25.
   - Les contrôles, relevés pour chaque vue sur la scène :
     - `maisons_dans_le_champ` : centres dans [0,02 ; 0,98] ;
     - `maisons_dans_le_cone` : bornes qui coupent le frustum ;
     - `passants_dans_le_cone` ;
     - `etals_dans_le_champ` : les huit coins du comptoir dans [0,02 ; 0,98] ;
     - `chantier_dans_le_champ` : les huit coins de la pièce dans [0,03 ; 0,97] ;
     - `hauteur_m` : la caméra au-dessus du terrain.
   - L'étiquette est un `TextMesh` blanc, enfant de la caméra, à 1 m devant elle, en haut à gauche (police `LegacyRuntime.ttf`). Ses bornes doivent être entières dans [0,01 ; 0,99]. Son texte est exactement `<nom> · médiane <m> ms · P95 <p> ms · max <x> ms`, chaque nombre écrit `ToString("F1", CultureInfo.InvariantCulture)` avec le point remplacé par une virgule. Le rapport relit ce texte **sur le composant**.
   - Chaque vue ajoute au rapport `{nom, vise, cap, inclinaison, distance, camera (16 nombres), <les six contrôles>, etiquette, releve}`, où `releve` est le `JsonUtility.ToJson` du `ReleveDuBanc`.

Le rapport porte en outre :
- `cellule`, `port`, `tick`, `bourg` ;
- `panier` : les stocks du bourg lus, un objet ;
- `maisons_posees`, `foyers`, `refus` ;
- `passants_projetes`, `passants_poses`, `passants_scene` ;
- `chantier` : `{identifiant, nature, etat}` ;
- `heure`, `fumees`, `lampes`, `etals` ;
- `optimisations` (`OptimisationsDeLaVille.Actives`) ;
- `machine` : `{gpu: SystemInfo.graphicsDeviceName, api: SystemInfo.graphicsDeviceType, cpu: SystemInfo.processorType, memoire_mo: SystemInfo.systemMemorySize, unity: Application.unityVersion, qualite: QualitySettings.names[QualitySettings.GetQualityLevel()]}` ;
- `vues`.

Chaque vue réussie écrit `Debug.Log("CAPTURE_959 <nom> médiane … P95 …")`.

**`docs/mesures/422-capitale-dense/avant.json`** : la copie, octet pour octet, du `lot959-ville-dense.json` de la commande P.

**`docs/mesures/422-capitale-dense/LISEZMOI.md`** (≤ 25 lignes) : ce qui est mesuré et comment (la commande P entière, le commit, la date, la machine du rapport). Il porte une table `| vue | médiane (ms) | P95 (ms) | max (ms) |` avec une ligne par vue, commençant par `| survol |`, `| rue |`, `| place |`, `| chantier |`, nombres à une décimale et virgule. Il porte aussi les quatre médianes de la contre-épreuve C2 (sans effets), la phrase « mesure d'avant les optimisations : rien ne lit `OptimisationsDeLaVille.Actives` à ce commit », et le renvoi aux sous-lots 4, 5 et 6 de #422.

## Conditions de succès
Les commandes Unity se jouent sur le PC, depuis la racine, éditeur fermé, **avec rendu** (jamais `-nographics`, jamais `-quit`), chaque fois dans un dossier neuf. `$unity` = `'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. Les commandes P, C1 et C2 sont dans la section Photo.

`CONTROLE <rapport> [<lisezmoi>]` = `py -3 -c $controle <rapport> [<lisezmoi>]`, avec ce code indépendant du C# :
```powershell
$controle = @'
import json,math,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig')); V=r['vues']
f=lambda v:f'{v:.1f}'.replace('.',',')
assert r['defaut'] is None, r['defaut']
assert (r['cellule'],r['tick'],r['bourg'])==(10103,4,800), 'ville'
assert (r['maisons_posees'],r['foyers'],r['refus'])==(600,600,[]), 'maisons'
assert (r['passants_projetes'],r['passants_poses'],r['passants_scene'])==(80,80,80), 'passants'
assert r['chantier']['nature']=='maison' and r['chantier']['etat'] in ('piquets','murs'), 'chantier'
m=sorted(k for k,v in r['panier'].items() if v>0)
assert r['heure']==19.6 and r['fumees']==600 and r['lampes']==600 and m, 'effets'
assert [e['marchandise'] for e in r['etals']]==m and all(e['cause'] is None and e['rapport']>0 for e in r['etals']), 'effets'
assert [v['nom'] for v in V]==['survol','rue','place','chantier'], 'vues'
for v in V:
    b=v['releve']; t=b['temps_ms']; n=len(t)
    assert (b['largeur'],b['hauteur'],b['chauffe'],b['images'],b['nombre'],n)==(1920,1080,60,300,300,300) and b['rendu'] is True, v['nom']+' banc'
    assert (b['vsync_pendant'],b['plafond_pendant'])==(0,-1) and all(math.isfinite(x) and x>0 for x in t), v['nom']+' banc'
    s=sorted(t); med=(s[149]+s[150])/2; p95=s[(95*n+99)//100-1]
    assert abs(b['mediane_ms']-med)<1e-6 and abs(b['p95_ms']-p95)<1e-6 and abs(b['maximum_ms']-s[-1])<1e-6, v['nom']+' resume'
    assert v['etiquette']==f"{v['nom']} · médiane {f(med)} ms · P95 {f(p95)} ms · max {f(s[-1])} ms", v['nom']+' etiquette'
S,R,P,C=V
assert S['maisons_dans_le_champ']==600, 'survol'
assert R['hauteur_m']<=4 and R['maisons_dans_le_cone']>=10, 'rue'
assert P['etals_dans_le_champ']==len(r['etals']), 'place'
assert C['chantier_dans_le_champ'] is True, 'chantier'
assert r['contre_epreuve']=='' and r['optimisations'] is True, 'drapeaux'
if len(sys.argv)>2:
    L=Path(sys.argv[2]).read_text(encoding='utf-8').splitlines()
    for v in V:
        b=v['releve']; l=[x for x in L if x.startswith('| '+v['nom']+' |')]
        assert len(l)==1 and all(f(b[k]) in l[0] for k in ('mediane_ms','p95_ms','maximum_ms')), 'lisezmoi '+v['nom']
print('ok',[(v['nom'],round(v['releve']['mediane_ms'],1),round(v['releve']['p95_ms'],1)) for v in V],r['machine']['gpu'])
'@
```

SC1 — **La ville dense, montée et mesurée.** La commande P sort en 0. Sa trace `CAPTURE_SERVICE` finit par `--epreuve`, et son journal porte quatre traces `CAPTURE_959`. `CONTROLE 3d/unity/Temp/lot959-photo/lot959-ville-dense.json` sort en 0 et affiche `ok [('survol', …), ('rue', …), ('place', …), ('chantier', …)] <gpu>`. Le codeur montre d'abord le rouge (rapport absent avant le code), puis le vert. Contre-épreuves : SC3 et SC4.

SC2 — **La mesure d'avant, versée.** `py -3 -c "import sys,filecmp;assert filecmp.cmp(sys.argv[1],sys.argv[2],shallow=False);print('ok')" 3d/unity/Temp/lot959-photo/lot959-ville-dense.json docs/mesures/422-capitale-dense/avant.json` sort en 0. `CONTROLE docs/mesures/422-capitale-dense/avant.json docs/mesures/422-capitale-dense/LISEZMOI.md` sort en 0. Contre-épreuve, faite à la main et dite dans la PR : une médiane changée d'un dixième dans `LISEZMOI.md`, et le contrôle sort en 1 sur `lisezmoi <vue>`.

SC3 — **Sans la ville dense, la mesure refuse.** La commande C1 sort avec un code différent de 0. Son journal nomme `600 maisons attendues`, et son rapport a un `defaut` non nul qui le nomme aussi. Une session qui mesurerait la ville de 1400 (33 maisons) en la croyant dense ferait passer C1 : la livraison est alors refusée.

SC4 — **Sans effets, le contrôle rougit.** La commande C2 sort en 0. `CONTROLE 3d/unity/Temp/lot959-sans-effets/lot959-ville-dense.json` sort en 1 sur `AssertionError: effets`. Son rapport porte `fumees` 0, `lampes` 0 et `etals` vide. Le codeur écrit dans la PR les quatre médianes de P et de C2, côte à côte : c'est le coût des effets que le sous-lot 5 réduira. Aucune comparaison de seuil n'est faite (le bruit d'une mesure n'est pas un verdict).

SC5 — **Les images, regardées.** P donne le plan fixe et `*--1-montage.png`, `*--2-survol.png`, `*--3-rue.png`, `*--4-place.png`, `*--5-chantier.png`. Le codeur les ouvre et dit ce qu'il voit :
- **montage** : la ville entière au soir, fumées et lampes ;
- **survol** : la même vue, avec son étiquette ;
- **rue** : une rue bordée de maisons à hauteur d'homme ;
- **place** : les étals garnis ;
- **chantier** : la maison aux piquets ou aux murs, sur la place.

Chaque étiquette doit se lire, entière, en haut à gauche. Une vue noire, vide de maisons, sans étiquette, ou dont l'étiquette ne porte pas les nombres de `CONTROLE` refuse la photo, même si les chiffres passent.

SC6 — **Les acquis et le budget.** `git grep -n "OptimisationsDeLaVille.Actives" -- 3d/unity/Assets` ne nomme que `OptimisationsDeLaVille.cs`, `TempsDImageTests.cs`, `BancDuTempsDImage.cs` et `Lot959.cs`. Tous les tests EditMode restent verts (`-runTests -testPlatform EditMode`, XML neuf, ni échec ni cas ignoré), et le workflow `unity` est vert, sans `error CS`. `python3 -m pytest jeu -q` passe sur le VPS. `git diff --name-only origin/master` ne nomme que le Périmètre. `git diff origin/master -- jeu/ 3d/unity/Assets/ForgeLocal3D/Pont/ 3d/unity/Assets/ForgeLocal3D/Desert/ 3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs 3d/unity/Assets/ForgeLocal3D/Editor/BancDuTempsDImage.cs 3d/unity/Assets/ForgeLocal3D/Editor/EpreuveVieDuBourg.cs` est vide. Hors brief, `git diff --numstat origin/master` totalise moins de 300 lignes.

## Hors périmètre
- Toute optimisation : regrouper maisons et enceinte (sous-lot 4 de #422), le LOD des fumées et des lampes (sous-lot 5), et la preuve P95 < 16,7 ms avec sa contre-épreuve `-forgeSansOptimisations` (sous-lot 6). Rien ne lit `OptimisationsDeLaVille.Actives` dans ce lot.
- Un seuil d'images par seconde : ce lot mesure, il ne juge pas.
- Toucher `jeu/`, le service et son `POST`, `ForgeCapture.cs` (délais, drapeaux), le banc, `EpreuveVieDuBourg`, `PassantsDeLaVille`, `EffetsDeMaison`, `EtalDuBourg`, `DesertRoadTool`, les scènes, les qualités et le pipeline.
- Monter fumées, lampes et étals dans le jeu hors des épreuves.
- Jouer un geste après le `POST` (la ville d'épreuve sert la mesure seule, MODELE.md).
- La mesure dans un joueur Windows construit.
- Verser les images et les autres rapports dans git : seul `avant.json` y entre.

## Photo
`Lot959.cs` joue la session ci-dessus. La photo, ce sont les quatre vues de Biskra dense au soir, chacune avec son temps d'image écrit en haut à gauche : survol de la ville entière, rue à hauteur d'homme, place et étals, chantier de la maison. Elles sont précédées du montage (la ville entière, sans étiquette). C1 échoue au montage ; C2 montre les mêmes vues sans fumée, sans lampe ni étal. Joindre au compte rendu :
- les images ;
- les trois `lot959-ville-dense.json` ;
- les journaux ;
- les sorties de `CONTROLE` et de la comparaison de SC2.

Photo, commande P :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 959 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures '3d/unity/Temp/lot959-photo' -logFile '3d/unity/Temp/lot959-photo.log'
```
Contre-épreuve C1, sans la ville dense (sort non zéro) :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 959 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forge959SansVille -forgeCaptures '3d/unity/Temp/lot959-sans-ville' -logFile '3d/unity/Temp/lot959-sans-ville.log'
```
Contre-épreuve C2, sans effets (sort en 0) :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 959 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forge959SansEffets -forgeCaptures '3d/unity/Temp/lot959-sans-effets' -logFile '3d/unity/Temp/lot959-sans-effets.log'
```
