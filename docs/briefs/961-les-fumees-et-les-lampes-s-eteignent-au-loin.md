# Lot #961 — Les fumées et les lampes s'éteignent au loin
Jalon : J4 · Machine : pc · Taille prévue : 240 lignes

## But
Dans la capitale dense, un composant `EffetsAuLoin` garde allumées les 32 lampes les plus proches de la caméra, met en pause les fumées à plus de 60 m et laisse Unity cesser de simuler les fumées hors de l'image. Il n'agit que si `OptimisationsDeLaVille.Actives` est vrai. La mesure de #959 montre le gain sur les vues survol et place.

## Le joueur
Le joueur survole sa capitale pleine au soir, ou s'arrête sur sa place, et l'image coule mieux : près de lui, les cheminées fument et les lampes brillent ; au loin, les fumées restent figées et les lampes s'éteignent, ce qui à cette distance ne se remarque presque pas. C'est le sous-lot 5 de #422 « La capitale dense tient 60 images par seconde ». Il prépare le geste du J4 « entre dans sa capitale en 3D, y marche » et son écran « une ville vivante dont chaque fumée, chaque étal et chaque passant suit le monde » (`CAP.md`, jalon 4). La mesure de #959 a montré que ces effets coûtent le plus : 138 ms par image en survol avec fumées et lampes, 26,5 ms sans. Le sous-lot 6 de #422 rejouera les quatre vues pour prouver un 95e centile sous 16,7 ms. Ce que le joueur sentira à la fin de #422 : sa capitale dense ne saccade pas quand il la survole.

## Règle du monde
Sans objet : lot de vue et de mesure. `jeu/` n'est pas touché. Aucune règle du monde ne change, et aucune épreuve des signes de vie non plus : `EffetsDeMaison` décide toujours si une maison fume et s'éclaire d'après le monde (#779). `EffetsAuLoin` décide seulement si on **montre** ce que `EffetsDeMaison` a allumé : il coupe la lampe sans toucher à son intensité, et il met la fumée en pause sans l'arrêter. Niveau de fidélité : sans objet.

**Ce que le chef a relevé (01/11/2026, master 58a59fcb).**
- Les fumées, lampes et étals ne sont montés que par les épreuves : `EpreuveVieDuBourg.Monter` (#781) et `Lot959.MonterEffets`. Le jeu ne les monte jamais. Seul `Lot959` montera le composant : #779, #781 et #782 ne le voient pas.
- `EffetsDeMaison.Appliquer` (inchangé) règle `lampe.intensity = soir` et `lampe.enabled = soir > 0`. Il lance la fumée par `if (!fumee.isPlaying) fumee.Play(true)` et l'éteint par `Stop(…, StopEmittingAndClear)`. Une lampe « voulue » est donc une lampe d'intensité > 0. Une fumée en pause a `isPlaying` faux et `isPaused` vrai : si `Appliquer` la relance, le composant la remet en pause à l'image suivante.
- `Lot959.MonterEffets` règle chaque fumée en `cullingMode = AlwaysSimulate`, avec 320 particules au plus et 40 émises par seconde. `AlpineBuilder.Smoke` les fait en boucle (`loop`), donc `Automatic` vaut `Pause` hors de l'image.
- Les scénarios de capture tournent en mode jeu (`EditorApplication.EnterPlaymode`), et `PassantsDeLaVille.Update` tourne pendant la mesure de #959 : le `LateUpdate` d'un composant tourne aussi à chaque image du banc.
- `OptimisationsDeLaVille.Actives` n'est lu, dans le code du jeu, par rien encore (#958). Le relevé de #959 compte `fumees` et `lampes` à la fin du montage : il doit trouver 600 et 600, donc **avant** que le composant soit monté.
- `ScenarioDeCaptureAttribute` a `AllowMultiple = false` : pour jouer les vues de #959 sous `-forgeLot 961`, il faut un `Lot961.cs` qui appelle les scénarios de `Lot959`.
- Le `LISEZMOI.md` de #959 est relu par son contrôle, qui veut une seule ligne `| survol |`. La mesure de ce lot va donc dans des fichiers neufs, à côté.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Pont/EffetsAuLoin.cs
3d/unity/Assets/ForgeLocal3D/Pont/EffetsAuLoin.cs.meta
3d/unity/Assets/ForgeLocal3D/Pont/Tests/EffetsAuLoinTests.cs
3d/unity/Assets/ForgeLocal3D/Pont/Tests/EffetsAuLoinTests.cs.meta
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot959.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot961.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot961.cs.meta
docs/mesures/422-capitale-dense/effets-au-loin.json
docs/mesures/422-capitale-dense/effets-au-loin-sans-optimisations.json
docs/mesures/422-capitale-dense/effets-au-loin.md
docs/briefs/961-les-fumees-et-les-lampes-s-eteignent-au-loin.md

Tout autre chemin est interdit. Budget du `numstat`, hors brief : `EffetsAuLoin.cs` 100, `EffetsAuLoinTests.cs` 70, `Lot959.cs` 30, `Lot961.cs` 15, trois `.meta` à 2 lignes chacun, deux `.json` à une ligne chacun, `effets-au-loin.md` 20.

**`Pont/EffetsAuLoin.cs`**, espace de noms `Forge.Pont`, `public sealed class EffetsAuLoin : MonoBehaviour`, dans le style de `EffetsDeMaison.cs` :
- Constantes publiques : `PLAFOND_DES_LAMPES = 32` et `DISTANCE_DES_FUMEES_M = 60f`.
- Deux fonctions pures et statiques, testées sans scène :
  - `bool[] LampesAllumees(Vector3 oeil, IReadOnlyList<Vector3> positions, IReadOnlyList<bool> voulues, int plafond)` : parmi les lampes voulues, les `plafond` plus proches de `oeil` sont vraies, en distance euclidienne 3D (carrés comparés). À distance égale, l'indice le plus petit passe d'abord. Une lampe non voulue est fausse et ne prend pas de place sous le plafond.
  - `bool[] FumeesEnPause(Vector3 oeil, IReadOnlyList<Vector3> positions, float distanceM)` : vrai si la distance est **strictement** supérieure à `distanceM`.
  - Refus : liste nulle → `ArgumentNullException` ; `positions` et `voulues` de tailles différentes, ou une coordonnée non finie (`oeil` compris) → `ArgumentException` ; `plafond < 0`, ou `distanceM` non finie ou ≤ 0 → `ArgumentOutOfRangeException`.
- `public void Configurer(Camera camera, IReadOnlyList<EffetsDeMaison> effets)` : copie la liste et garde la caméra. `Actif = OptimisationsDeLaVille.Actives`, lu ici et nulle part ailleurs. Si `Actif` est faux, il ne touche plus à rien, ni maintenant ni à aucune image. S'il est vrai, il note le `cullingMode` de chaque fumée et le passe à `ParticleSystemCullingMode.Automatic`. Refus : caméra nulle, liste nulle ou élément nul (`ArgumentNullException`).
- Propriétés publiques : `Actif`, `Effets` (le nombre d'effets suivis), `Camera`.
- `public void Regler()`, appelé par `LateUpdate`. Sans effet si le composant est inactif, la caméra détruite ou la liste vide. Sinon, avec `oeil = camera.transform.position` :
  - pour les lampes : `voulues[i] = lampe.intensity > 0`, puis `lampe.enabled = allumee[i]` pour chaque lampe voulue. Il ne touche jamais une lampe non voulue, ni aucune intensité.
  - pour les fumées : une fumée en pause selon `FumeesEnPause` et qui joue (`isPlaying`) est mise en pause (`Pause(true)`) et retenue. Une fumée retenue qui n'est plus au-delà de la distance, et encore en pause (`isPaused`), reprend (`Play(true)`) et n'est plus retenue. Une fumée retenue que `EffetsDeMaison` a arrêtée (`isStopped`) n'est plus retenue.
  - Une fumée ou une lampe détruite est sautée.
- `OnDisable` et `OnDestroy` rendent ce qu'il a pris : chaque lampe voulue est rallumée, chaque fumée retenue reprend, et chaque `cullingMode` retrouve sa valeur notée. Rien ne reste éteint par lui.
- Commentaire d'en-tête : « Lot #961 — le niveau de détail des effets de la capitale dense : une vue, jamais une règle du monde ; n'agit que si `OptimisationsDeLaVille.Actives`. »

**`Pont/Tests/EffetsAuLoinTests.cs`**, classe `EffetsAuLoinTests` de `Forge.Pont.Tests`, au moins ces cas :
- **plafond** : 6 lampes voulues sur l'axe x, à 6, 1, 5, 2, 4, 3 m, et plafond 3. Seules celles à 1, 2 et 3 m sont vraies, et le tableau d'entrée est intact.
- **non voulue** : la plus proche est non voulue, et le plafond est 2. Elle reste fausse, et les deux voulues suivantes sont vraies.
- **égalité** : 3 lampes à la même distance, plafond 2. Les indices 0 et 1 sont vrais.
- **plafond 0** : aucune ; **plafond 100** : toutes les voulues.
- **distance** : fumées à 59,9 m, 60 m et 60,1 m, avec la distance 60. Le résultat est `false, false, true`, et la distance est mesurée en 3D (une fumée à 60 m de haut, au-dessus de l'œil, compte).
- **refus** : un `[TestCase]` par refus de la liste ci-dessus.
- **composant** : un `GameObject` portant une `Camera` à l'origine, et 4 lampes ponctuelles d'intensité 8, allumées, à 1, 2, 3 et 4 m. On appelle `Configurer` avec une liste vide d'`EffetsDeMaison`, et on vérifie que `Regler()` n'allume ni n'éteint aucune lampe : le composant ne touche qu'aux effets qu'on lui donne. Les objets sont détruits en `TearDown`.

**`Editor/Captures/Lot959.cs`** : quatre changements, rien d'autre.
1. Les cinq méthodes de scénario (`Montage`, `Survol`, `Rue`, `Place`, `Chantier`) passent `internal static`.
2. À la fin de `Monter`, **après** `ReleverEffets()` et avant la pose de la caméra de survol : `auLoin = new GameObject("Effets au loin").AddComponent<EffetsAuLoin>(); auLoin.Configurer(camera, effets);`. Le composant est monté aussi sous `SansEffets`, avec une liste vide. `Monter` détruit d'abord un `auLoin` antérieur.
3. Dans `Vue`, après les 10 images et avec `Controles(camera)`, il relève sur la scène `effets`, un objet joint à la vue. Les distances se mesurent de `camera.transform.position` à `Lampe.transform.position` ou `Fumee.transform.position`, par le code de `Lot959` et non par le composant :
   - `lampes_allumees` : `Lampe.enabled` et `intensity > 0` ;
   - `lampe_allumee_la_plus_loin_m` et `lampe_eteinte_la_plus_proche_m` (éteinte : `!enabled` et `intensity > 0`) ;
   - `fumees_animees` : `isPlaying` et non `isPaused` ;
   - `fumees_en_pause` : `isPaused` ;
   - `fumee_animee_la_plus_loin_m` et `fumee_en_pause_la_plus_proche_m`.
   Une distance sans objet vaut `null`.
4. `Ecrire` ajoute au rapport `"effets_au_loin"`. Il vaut `null` tant que le composant n'est pas monté, puis `{actif, plafond, distance_m, effets, culling_automatique}`, où `culling_automatique` compte les fumées de `effets` dont `main.cullingMode == Automatic`.
Le nom du rapport, les drapeaux de #959, le relevé `fumees`/`lampes` du montage et les vues restent ceux de #959.

**`Editor/Captures/Lot961.cs`**, `static class Lot961` de `ForgeLocal3D.Captures` : cinq scénarios `[ScenarioDeCapture(961, "1-montage")]`, `"2-survol"`, `"3-rue"`, `"4-place"`, `"5-chantier"`. Chacun rend l'itérateur du scénario de même nom de `Lot959`. C'est tout. Le rapport reste `lot959-ville-dense.json`.

**`docs/mesures/422-capitale-dense/effets-au-loin.json`** : la copie, octet pour octet, du rapport de la commande P. **`effets-au-loin-sans-optimisations.json`** : la même chose pour la commande C. **`effets-au-loin.md`** (≤ 20 lignes) donne :
- les deux commandes entières, le commit, la date et la machine du rapport ;
- la table `| vue | sans optimisations (ms) | avec (ms) | rapport |`, avec une ligne par vue commençant par `| survol |`, `| rue |`, `| place |` ou `| chantier |` : médianes à une décimale avec la virgule, et rapport avec/sans à deux décimales avec la virgule ;
- les médianes d'`avant.json` en rappel ;
- le renvoi au sous-lot 6 de #422.

## Conditions de succès
Les commandes Unity se jouent sur le PC, depuis la racine, éditeur fermé, **avec rendu** (jamais `-nographics`, jamais `-quit`), chaque fois dans un dossier neuf. P et C sont dans la section Photo.

`CONTROLE961 <rapport P> <rapport C> [<md>]` = `py -3 -c $controle961 …`, avec ce code, indépendant du C# :
```powershell
$controle961 = @'
import json,sys
from pathlib import Path
J=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
P,C=J(sys.argv[1]),J(sys.argv[2]); N=['survol','rue','place','chantier']
f=lambda v,d=1:f'{v:.{d}f}'.replace('.',',')
for r,actif in ((P,True),(C,False)):
    t='avec' if actif else 'sans'
    assert r['defaut'] is None, t+' '+str(r['defaut'])
    assert (r['cellule'],r['tick'],r['bourg'],r['maisons_posees'],r['fumees'],r['lampes'],r['heure'])==(10103,4,800,600,600,600,19.6), t+' ville'
    assert r['contre_epreuve']=='' and r['optimisations'] is actif, t+' drapeaux'
    a=r['effets_au_loin']
    assert (a['actif'],a['plafond'],a['distance_m'],a['effets'],a['culling_automatique'])==(actif,32,60,600,600 if actif else 0), t+' composant'
    assert [v['nom'] for v in r['vues']]==N, t+' vues'
    for v in r['vues']:
        b=v['releve']; s=sorted(b['temps_ms']); k=t+' '+v['nom']
        assert (b['largeur'],b['hauteur'],b['chauffe'],b['images'],len(s))==(1920,1080,60,300,300) and b['rendu'] is True, k+' banc'
        assert abs(b['mediane_ms']-(s[149]+s[150])/2)<1e-6, k+' resume'
        e=v['effets']
        assert e['fumees_animees']+e['fumees_en_pause']==600, k+' fumees'
        if actif:
            assert e['lampes_allumees']==32, k+' plafond'
            assert e['lampe_allumee_la_plus_loin_m']<=e['lampe_eteinte_la_plus_proche_m'], k+' plus proches'
            assert e['fumee_animee_la_plus_loin_m'] is None or e['fumee_animee_la_plus_loin_m']<=60, k+' distance'
            assert e['fumee_en_pause_la_plus_proche_m'] is None or e['fumee_en_pause_la_plus_proche_m']>60, k+' distance'
        else:
            assert (e['lampes_allumees'],e['fumees_en_pause'])==(600,0), k+' intact'
assert P['vues'][0]['effets']['fumees_en_pause']==600 and P['vues'][1]['effets']['fumees_animees']>=1, 'vues de la distance'
m=lambda r,i:r['vues'][i]['releve']['mediane_ms']
g=[m(P,i)/m(C,i) for i in range(4)]
assert g[0]<=0.75, 'gain survol '+f(g[0],2)
assert g[2]<=0.90, 'gain place '+f(g[2],2)
if len(sys.argv)>3:
    L=Path(sys.argv[3]).read_text(encoding='utf-8').splitlines()
    for i,n in enumerate(N):
        l=[x for x in L if x.startswith('| '+n+' |')]
        assert len(l)==1 and all(x in l[0] for x in (f(m(C,i)),f(m(P,i)),f(g[i],2))), 'md '+n
print('ok',[(n,round(m(C,i),1),round(m(P,i),1),round(g[i],2)) for i,n in enumerate(N)],P['machine']['gpu'])
'@
```

SC1 — **Le choix des effets, testé.** Les tests EditMode (`-runTests -testPlatform EditMode`, XML neuf) sont tous verts, sans cas ignoré. Le XML nomme chaque cas de `EffetsAuLoinTests`. Le codeur montre d'abord le rouge (les tests sans le code), puis le vert. Contre-épreuve faite à la main et dite dans la PR : on ignore le plafond dans `LampesAllumees` (toutes les voulues vraies), et le cas **plafond** rougit ; on remplace la comparaison stricte des fumées par `>=`, et le cas **distance** rougit. On remet le code ensuite.

SC2 — **Le gain, mesuré.** P et C sortent en 0, et chacune porte quatre traces `CAPTURE_959` dans son journal. `CONTROLE961 3d/unity/Temp/lot961-photo/lot959-ville-dense.json 3d/unity/Temp/lot961-sans-optimisations/lot959-ville-dense.json` sort en 0 et affiche `ok [('survol', …), ('rue', …), ('place', …), ('chantier', …)] <gpu>`. Il vérifie :
- le plafond de 32 lampes sur chaque vue, qui sont bien les plus proches ;
- la distance de 60 m des fumées ;
- toutes les fumées en pause en survol, et au moins une animée dans la rue ;
- le passage de toutes les fumées en culling automatique ;
- une médiane avec optimisations au plus égale à 0,75 fois celle sans optimisations en survol, et à 0,90 fois en place.
Les seuils sont choisis bien au-delà du bruit, qui reste de quelques pour cent entre deux sessions. Le codeur écrit dans la PR les quatre rapports avec/sans.

SC3 — **Sans optimisations, rien ne bouge.** C'est la contre-épreuve de SC2. Dans le rapport de C, chaque vue garde 600 lampes allumées, 0 fumée en pause, et un `culling_automatique` à 0 : c'est vérifié par la boucle `sans` de SC2. De plus, `CONTROLE961` joué avec les deux rapports inversés (C d'abord) sort en 1 sur `AssertionError: avec drapeaux`. Un composant qui agirait sans regarder l'interrupteur fait rougir SC2 sur `sans … intact`.

SC4 — **La mesure, versée.** `py -3 -c "import sys,filecmp;assert filecmp.cmp(sys.argv[1],sys.argv[2],shallow=False) and filecmp.cmp(sys.argv[3],sys.argv[4],shallow=False);print('ok')" 3d/unity/Temp/lot961-photo/lot959-ville-dense.json docs/mesures/422-capitale-dense/effets-au-loin.json 3d/unity/Temp/lot961-sans-optimisations/lot959-ville-dense.json docs/mesures/422-capitale-dense/effets-au-loin-sans-optimisations.json` sort en 0. `CONTROLE961 docs/mesures/422-capitale-dense/effets-au-loin.json docs/mesures/422-capitale-dense/effets-au-loin-sans-optimisations.json docs/mesures/422-capitale-dense/effets-au-loin.md` sort en 0. Contre-épreuve faite à la main et dite dans la PR : on change d'un dixième la médiane du survol dans `effets-au-loin.md`, et le contrôle sort en 1 sur `md survol`.

SC5 — **Les images, regardées.** P et C donnent chacune `*--1-montage.png`, `*--2-survol.png`, `*--3-rue.png`, `*--4-place.png` et `*--5-chantier.png`. Le codeur les ouvre et dit ce qu'il voit, P à côté de C :
- **survol** : en P, des lampes allumées seulement du côté de la caméra, et des fumées toujours visibles mais figées ; en C, des lampes partout ;
- **rue** et **place** : en P, les maisons proches fument et s'éclairent comme en C ;
- chaque étiquette porte son temps d'image.
Une vue noire, une ville sans fumée visible en P ou une rue sans lampe en P refusent la photo, même si les chiffres passent.

SC6 — **Les acquis et le budget.**
- `git diff origin/master -- jeu/ 3d/unity/Assets/ForgeLocal3D/Pont/EffetsDeMaison.cs 3d/unity/Assets/ForgeLocal3D/Pont/OptimisationsDeLaVille.cs 3d/unity/Assets/ForgeLocal3D/Pont/Tests/KitDesBatimentsTests.cs 3d/unity/Assets/ForgeLocal3D/Pont/Tests/TempsDImageTests.cs 3d/unity/Assets/ForgeLocal3D/Editor/EpreuveVieDuBourg.cs 3d/unity/Assets/ForgeLocal3D/Editor/BancDuTempsDImage.cs 3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot779.cs 3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot781.cs pc/ docs/mesures/422-capitale-dense/avant.json docs/mesures/422-capitale-dense/LISEZMOI.md` est vide. Les épreuves #779, #781 et #782 ne changent donc pas.
- `git grep -n "OptimisationsDeLaVille.Actives" -- 3d/unity/Assets` ne nomme, en plus des quatre fichiers de #959, que `EffetsAuLoin.cs`.
- `git grep -n "EffetsAuLoin" -- 3d/unity/Assets` ne nomme que `EffetsAuLoin.cs`, `EffetsAuLoinTests.cs` et `Lot959.cs`.
- Le workflow `unity` est vert, sans `error CS`. `python3 -m pytest jeu -q` passe sur le VPS.
- `git diff --name-only origin/master` ne nomme que le Périmètre, et, hors brief, `git diff --numstat origin/master` totalise moins de 300 lignes.

## Hors périmètre
- Toucher `EffetsDeMaison`, `EpreuveVieDuBourg`, `EtalDuBourg`, le banc, `OptimisationsDeLaVille`, `ForgeCapture.cs`, les scènes, les qualités, le pipeline URP ou les matériaux.
- Le regroupement des maisons (sous-lot 4 de #422, abandonné), et la preuve P95 < 16,7 ms sur les quatre vues (sous-lot 6). Ce lot ne promet aucun seuil absolu, seulement un gain sur survol et place.
- Un niveau de détail des étals ou des passants, ou un fondu des lampes à la limite.
- Monter fumées, lampes ou ce composant dans le jeu hors des épreuves.
- Changer les seuils, la ville dense ou les vues de #959, ou réécrire `avant.json` et le `LISEZMOI.md` de #959.
- Verser les images et les journaux dans git : seuls les deux rapports `.json` et `effets-au-loin.md` y entrent.

## Photo
`Lot961.cs` rejoue la ville dense de #959 et ses quatre vues, avec le composant monté. La photo montre Biskra dense au soir, chaque vue avec son temps d'image en haut à gauche. En survol, les lampes ne brillent que du côté de la caméra et les fumées sont figées ; dans la rue et sur la place, les maisons proches fument et s'éclairent. La contre-épreuve C montre les mêmes vues sans optimisations, toutes les lampes allumées, avec des temps d'image plus longs. Joindre au compte rendu :
- les images de P et de C ;
- les deux `lot959-ville-dense.json` ;
- les journaux ;
- les sorties de `CONTROLE961` (SC2, SC3, SC4) et de la comparaison de SC4.

Photo, commande P :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 961 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures '3d/unity/Temp/lot961-photo' -logFile '3d/unity/Temp/lot961-photo.log'
```
Contre-épreuve C, sans optimisations (sort en 0, et `CONTROLE961` la juge) :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 961 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeSansOptimisations -forgeCaptures '3d/unity/Temp/lot961-sans-optimisations' -logFile '3d/unity/Temp/lot961-sans-optimisations.log'
```
