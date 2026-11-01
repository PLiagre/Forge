# Lot #937 — La session Unity de l'épreuve de l'enceinte
Jalon : J4 · Machine : pc · Taille prévue : 280 lignes

## But
Sur le vrai service d'épreuve, une session Unity trace à Biskra l'enceinte avec l'outil du joueur, la regarde passer des piquets à l'achèvement tick après tick, et écrit à chaque tick les portes que la scène dessine contre celles que le monde sert.

## Le joueur
Le joueur trace son mur autour de Biskra (E, quatre clics, Entrée). Il le voit aux piquets, puis fini, avec sa porte ouverte sur la route de l'ouest. Il sent que le mur qu'il paie au grenier est bien celui que le monde bâtit, et que la porte est là où passe sa route. Lot de fond : c'est le sous-lot 2 de #909 « épreuve de l'enceinte », découpé de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues ». Il prépare le geste du J4 « trace son enceinte » et sa décision, « des murs, ou des maisons » (`CAP.md`, jalon 4). Le juge `pc/epreuve_enceinte.py` (sous-lot 3 de #909) lancera cette session et rendra le verdict. La demande n'a pas de phrase « Le joueur » séparée : celle-ci en dit le bénéfice, selon « La règle d'un lot ».

## Règle du monde
Sans objet : outil d'épreuve et vue, aucune règle neuve. La session lit sans les changer « Le plan du bourg » (l'enceinte, son travail requis, ses portes) et « Le chantier et ses bras » de `jeu/sim/MODELE.md`, ainsi que le paragraphe du mode épreuve sur `--travail-enceinte J` (#936, livré 6c7204ce). Elle passe par l'outil de #908 (livré 6a69159f) et le dessin de #907 et #926, sans les changer.

**Dépend de : #936**, livré, et de #908, livré.

**Mesure du chef**, refaite le 31/10/2026 par HTTP : `python3 -m sim.service --epreuve --travail-enceinte 0.01 --seed 0 --jours-par-seconde 0`. Biskra = cellule 10103, seigneurie 6. `choisir_depart` au tick 0, un tick, la route `[[-66,2.2],[-120,2.2]]` de 4 m au tick 1, un tick, l'enceinte `[[-80,-80],[80,-80],[80,80],[-80,80]]` acceptée au tick 2. Après les ticks qui portent `/plan` à 3, 4, 5 et 6 : `travail_requis` 7, `travail_fourni` 1, 3, 7, 7, `en_chantier` vrai, vrai, faux, faux. À chaque tick, une seule porte : `{"identifiant":0,"largeur_m":4,"point":[-80.0,2.2],"rue":"plan"}`. `PansDeLEnceinte.Etape` donne donc piquets, piquets, puis fini.

**Les noms.** L'issue dit `Lot909.cs` et `-forge909SansPorte`. Le PC rejoue les captures sous le numéro du lot : le fichier est `Captures/Lot937.cs` (`-forgeLot 937`), et le drapeau `-forge937SansPorte`. Le juge de #909 lancera `-forgeLot 937`.

**`ForgeCapture.cs`.** Ajouter `public const string TRAVAIL_ENCEINTE = "-forgeTravailEnceinte";` et le nommer dans le commentaire d'en-tête. Dans `Photographier`, après les entiers et avant `PortRepond` : absent, rien ne change. Présent, la valeur suivante doit se lire en `double` (`NumberStyles.Float`, culture invariante), finie et > 0. Sinon : `Debug.LogError("CAPTURE : -forgeTravailEnceinte attend un nombre fini > 0, reçu « v »")` (ou « rien »), puis `Sortir(CODE_REFUS)`. Sans `-forgeServiceEpreuve`, même sortie, avec un message qui nomme les deux drapeaux. `LancerService` ajoute alors ` --travail-enceinte ` suivi de la valeur au format `R` invariant, après ` --epreuve`. La ligne `CAPTURE_SERVICE` la porte donc déjà. Rien d'autre ne change.

**La session**, `Captures/Lot937.cs`, deux scénarios qui partagent leur état par des champs statiques. Elle reprend les gestes de `Lot908` en les recopiant, sans toucher `Lot908.cs`. Elle utilise `Lot362.Deposer`, `Tick`, `Lire` et `Monde`. Outil, caméra et marcheur passent en `automatique`.
1. **`[ScenarioDeCapture(937, "1-enceinte-en-chantier")]`.** Refuser un `lot937-enceinte.json` déjà présent dans `Capture.DossierDesCaptures`. Biskra par `ClientDeparts` (fiche unique au siège « Biskra »), le choix, un tick, la route, un tick. `Ouvrir(c)` vrai et `lieu.Ouvrir(c)` ; exiger 33 maisons, 7 rues de 1400 et 0 pièce d'enceinte. `EntrerEnceinte()`, puis les quatre coins cliqués comme `Lot908` (`RenderTexture` 1600 × 900, `ville.Poser(m, ville.Cap, 85, 60)`, `Clic` vrai). Panneau `Enceinte · 4 coin(s)`. `ValiderEnceinte()` : reçu accepté, appliqué au tick 2, `Derniers` égal aux coins. `Lot362.Tick`, puis `Attendre()` vrai. Relevé (point 3). Exiger au plan une enceinte en chantier, de contour égal aux coins. Caméra : celle du scénario 2 de `Lot908` (de l'ouest à 35°, cap = lacet de la porte + 180, visée `Monde(t,-80,0)`, recul ×1,06 depuis 40 m). Les cibles sont les tours (−80 ; ±80), la porte (−80 ; 2,2) et la route en (−95 ; 2,2), entre 0,02 et 0,98 de l'image, caméra à x Unity > 80. Garder ces arguments de `Poser`, puis `outil.Placer()` et dix images.
2. **`[ScenarioDeCapture(937, "2-enceinte-finie")]`.** Refuser de jouer seul. Tant que le dernier relevé est en chantier : si 12 ticks ont suivi le dépôt (celui de `Attendre` compris), lever `enceinte inachevée après 12 ticks : fourni F/R`. Sinon `Lot362.Tick`, `outil.Rafraichir()` vrai, et relevé. Une fois fini, exiger l'étape `Fini`, puis reposer la caméra avec les mêmes arguments, `outil.Placer()` et dix images. Le rapport final a `defaut` nul.
3. **Le relevé**, après chaque dessin : d'abord, sous `-forge937SansPorte`, `DestroyImmediate` de chaque enfant de `Enceinte.Racine` dont le nom commence par `Enceinte porte `. Ensuite, exiger dans le panneau la ligne `Enceinte : <étape> · 4 tour(s), 63 pan(s), 1 porte(s).` (étape en minuscules). Puis relire `/plan` par `Lot362.Lire` et parcourir **la scène**, jamais `Enceinte.Posees` : chaque `Transform` actif (`FindObjectsByType`, inactifs exclus) dont le nom commence par `Enceinte tour `, `Enceinte courtine ` ou `Enceinte porte `. Un élément de `releves` porte :
   - `tick`, `en_chantier`, `travail_fourni`, `travail_requis`, `etape` (`piquets`, `murs` ou `fini`) ;
   - `portes_servies` : `{x, y, rue, identifiant}` dans l'ordre du plan ;
   - `tours` et `pans`, comptés dans la scène ;
   - `portes_dessinees` : `{nom, x, y, lacet}`, avec x = −x Unity et y = −z Unity ;
   - `ecart_porte_m` : pour chaque porte servie, la distance horizontale à la plus proche porte dessinée (−1 s'il n'y en a aucune).
4. **Le rapport** `lot937-enceinte.json`, en UTF-8 sans BOM, est réécrit à chaque relevé. Il porte `cellule`, `port`, `contre_epreuve` ("" ou `forge937SansPorte`), `travail_enceinte` (la valeur brute de `-forgeTravailEnceinte`, ou `null`), `coins`, `recu` (`{acceptee, tick}`), `releves`, `acheve_au_tick` (ou `null`) et `defaut`. Sur une exception, `defaut` vaut « étape : message », écrit avant de relancer. À la fin, `Debug.Log("CAPTURE_937 " + rapport)`.

Sous `-forge937SansPorte`, la session sort en 0 : c'est le contrôle ci-dessous qui doit rougir.

## Périmètre
3d/unity/Assets/ForgeLocal3D/Editor/ForgeCapture.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot937.cs
3d/unity/Assets/ForgeLocal3D/Editor/Captures/Lot937.cs.meta
docs/briefs/937-la-session-unity-de-l-epreuve-de-l-enceinte.md

Le `.meta` fait deux lignes (`fileFormatVersion: 2`, `guid` neuf). Budget du `numstat` : `ForgeCapture` 20, `Lot937` 150, `.meta` 2, ce brief.

## Conditions de succès
Toutes se jouent sur le PC, depuis la racine, éditeur fermé, avec rendu, sans `-quit` ni `-nographics`, chaque dossier neuf. `$unity` = `'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'`. `CONTROLE <dossier>` = `py -3 -c $controle <dossier>`, avec ce code indépendant :
```powershell
$controle = @'
import json,sys
from pathlib import Path
r=json.loads((Path(sys.argv[1])/'lot937-enceinte.json').read_text(encoding='utf-8-sig')); R=r['releves']
assert r['defaut'] is None, r['defaut']
assert r['cellule']==10103 and r['travail_enceinte']=='0.01' and r['recu']=={'acceptee':True,'tick':2}
assert [x['tick'] for x in R]==[3,4,5] and r['acheve_au_tick']==5, 'travail'
assert [(x['travail_fourni'],x['travail_requis'],x['en_chantier'],x['etape']) for x in R]==[(1,7,True,'piquets'),(3,7,True,'piquets'),(7,7,False,'fini')], 'travail'
assert all(x['portes_servies']==[{'x':-80.0,'y':2.2,'rue':'plan','identifiant':0}] and (x['tours'],x['pans'])==(4,63) for x in R)
assert all(len(x['portes_dessinees'])==1 and len(x['ecart_porte_m'])==1 and 0<=x['ecart_porte_m'][0]<=0.05 for x in R), 'porte'
print('ok', [(x['tick'], x['travail_fourni'], x['etape'], len(x['portes_dessinees'])) for x in R])
'@
```

SC1 — **Le mur passe des piquets à l'achèvement, sa porte dessinée.** La commande P (section Photo) sort en 0, et sa trace `CAPTURE_SERVICE` finit par `--epreuve --travail-enceinte 0.01`. `CONTROLE 3d/unity/Temp/lot937-photo` sort en 0 et affiche `ok [(3, 1, 'piquets', 1), (4, 3, 'piquets', 1), (5, 7, 'fini', 1)]`. Le codeur montre d'abord le rouge (rapport absent avant le code), puis le vert. Contre-épreuve : SC2 et SC3.

SC2 — **La porte manquante se voit.** La commande C1 sort en 0. `CONTROLE 3d/unity/Temp/lot937-sans-porte` sort en 1 sur `AssertionError: porte`. Chaque relevé y porte `portes_dessinees` vide et `ecart_porte_m` `[-1]`, avec une porte servie. Une session qui compterait `Enceinte.Posees` ou le panneau au lieu de la scène laisserait ce contrôle vert : la livraison est alors refusée.

SC3 — **Le travail réglé passe vraiment au service.** La commande C2 sort avec un code différent de 0. Son journal nomme `enceinte inachevée après 12 ticks`, et sa trace `CAPTURE_SERVICE` finit par `--travail-enceinte 30`. Son rapport a 12 relevés, tous à `travail_requis` 19200, et un `defaut` non nul. Un `ForgeCapture` qui ne passerait pas la valeur rougirait SC1.

SC4 — **Les arguments.** Chacune de ces commandes sort en 2, sans trace `CAPTURE_SERVICE` ni dossier créé, et son journal nomme `-forgeTravailEnceinte` et la valeur reçue (ou `-forgeServiceEpreuve` pour la première) :
- `& $unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeTravailEnceinte 0.01 -forgeCaptures 3d/unity/Temp/lot937-refus-a -logFile 3d/unity/Temp/lot937-refus-a.log` ;
- la même avec `-forgeServiceEpreuve -forgeTravailEnceinte V`, pour V = `0`, `nan` et `abc`, vers `lot937-refus-0`, `lot937-refus-nan` et `lot937-refus-abc`.

SC5 — **Les images, regardées.** P et C1 donnent `*--1-enceinte-en-chantier.png` et `*--2-enceinte-finie.png`, C2 la première seule. Le codeur ouvre les cinq et dit ce qu'il voit : P/1, le mur aux piquets vu de l'ouest, avec la porte au bout de la route ; P/2, le même cadre, le mur fini et sa porte ; C1, la brèche sans porte dans le mur ; C2/1, les piquets. Un cadre sans route ou sans porte refuse la photo, même si les chiffres passent.

SC6 — **Les acquis et le budget.** Les captures de régression sortent en 0 sans changement de leur scénario : `& $unity -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 908 -forgeCaptures 3d/unity/Temp/lot937-regres-908 -logFile 3d/unity/Temp/lot937-regres-908.log`, puis la commande P de `docs/briefs/897-une-session-unity-releve-les-ouvriers-au-chantie.md`, vers `3d/unity/Temp/lot937-regres-897`, suivie de son `CONTROLE` vert. Les tests EditMode restent verts (`-runTests -testPlatform EditMode`, XML neuf, sans échec ni cas ignoré). `python3 -m pytest jeu -q` passe sur le VPS. `git diff --name-only origin/master` ne nomme que le Périmètre, `git diff origin/master -- jeu/ 3d/unity/Assets/ForgeLocal3D/Pont/ 3d/unity/Assets/ForgeLocal3D/Desert/` est vide, et `git diff --numstat origin/master` totalise moins de 300 lignes.

## Hors périmètre
- Le juge `pc/epreuve_enceinte.py`, son service de référence et ses tests (sous-lot 3 de #909).
- Tout changement de `DesertRoadTool`, `DesertEnceinte`, `PansDeLEnceinte`, du kit, de `Lot908.cs`, de `Lot362.cs`, du service ou du moteur. Un redessin automatique du mur à chaque tick dans la partie : si la session semble en avoir besoin, le codeur le dit dans la PR, sans l'écrire.
- Aucun rapport ni aucune image versés dans git.

## Photo
`Lot937.cs` joue la session ci-dessus. La photo montre Biskra vue de l'ouest : d'abord le mur aux piquets au tick 3, puis, au tick 5, le même cadre avec le mur fini, sa porte ouverte au bout de la route. C1 montre la brèche sans porte ; C2 échoue après les piquets. Joindre au compte rendu les images, les trois `lot937-enceinte.json`, les journaux et les sorties de `CONTROLE`.

Photo, commande P :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 937 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeTravailEnceinte 0.01 -forgeCaptures '3d/unity/Temp/lot937-photo' -logFile '3d/unity/Temp/lot937-photo.log'
```
Contre-épreuve C2, le travail du jeu (sort non zéro) :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 937 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeTravailEnceinte 30 -forgeCaptures '3d/unity/Temp/lot937-trente' -logFile '3d/unity/Temp/lot937-trente.log'
```
Contre-épreuve C1, la porte retirée (sort en 0) :
```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe' -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 937 -forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeTravailEnceinte 0.01 -forge937SansPorte -forgeCaptures '3d/unity/Temp/lot937-sans-porte' -logFile '3d/unity/Temp/lot937-sans-porte.log'
```
