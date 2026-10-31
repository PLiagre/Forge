# Lot #938 — Le juge de l'épreuve de l'enceinte
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Une commande du PC lance la session #937, rejoue ses gestes sur un service d'épreuve neuf et rend un verdict qui peut échouer : à Biskra, le mur servi est celui des coins cliqués, il coûte son périmètre fois J journées, il s'achève, et à chaque tick la scène dessine les portes que le monde sert.

## Le joueur
Le joueur trace son mur autour de Biskra (E, quatre clics, Entrée). Il le voit aux piquets, puis fini, avec sa porte ouverte au bout de la route de l'ouest (#908, #926, #937). Il sent que le mur qu'il paie au grenier est bien celui que le monde bâtit, et que la porte est là où passe sa route. Ce lot de fond rend cette promesse vérifiable : il juge le geste du J4 « trace son enceinte », sa décision « des murs, ou des maisons », et la contre-épreuve du jalon « un moteur qui ignore l'intention » (`CAP.md`, jalon 4). C'est le sous-lot 3 de #909, découpé de #417 ; la preuve complète du jalon, #508, le reprendra. La demande n'a pas de phrase « Le joueur » séparée : celle-ci en dit le bénéfice, selon « La règle d'un lot ».

## Règle du monde
Sans objet : outil d'épreuve, aucune règle neuve. Il lit sans les changer « Le plan du bourg » (l'enceinte, son travail requis, ses portes) et « Le chantier et ses bras » de `jeu/sim/MODELE.md`, et l'option `--travail-enceinte J` du mode épreuve (#936). Le service d'épreuve est déterministe : mêmes graine, J et gestes, même `/plan`. C'est ce qui permet de comparer la session Unity à une référence lancée après elle.

**Dépend de : #936 et #937**, livrés (6c7204ce, ad074247). Rien ne change dans `3d/`, `jeu/sim/` ni dans un autre script de `pc/`.

**Les noms.** L'issue dit `-forgeLot 909`. La session livrée par #937 s'appelle `Lot937.cs` : le juge lance `-forgeLot 937` et son drapeau `-forge937SansPorte`.

**Mesure du chef**, refaite le 31/10/2026 sur un service `--epreuve` en mémoire, graine 0, J = 0,01, gestes de `Lot937.cs`. Biskra = cellule 10103. Les trois intentions sont acceptées aux ticks 0, 1 et 2. Après les ticks 3 à 14, `/plan` sert l'enceinte de contour `[[-80,-80],[80,-80],[80,80],[-80,80]]`, `travail_requis` 7 (= ⌈640 × 0,01⌉), `travail_fourni` 1, 3, puis 7 du tick 5 au tick 14, `en_chantier` vrai, vrai, puis faux ; et à chaque tick une seule porte `{"identifiant":0,"largeur_m":4,"point":[-80.0,2.2],"rue":"plan"}`. Avec un service qui accepte `tracer_enceinte` sans l'appliquer, le reçu dit toujours « acceptée au tick 2 », mais `/plan` ne sert ni `enceinte` ni `portes` aux ticks 3 à 14. Douze ticks prennent environ 4 s.

**Le lanceur**, `pc/epreuve_enceinte.py`, sur le modèle de `pc/epreuve_passants.py`, dont il charge les aides par `importlib` sans le modifier :
```
py pc\epreuve_enceinte.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--contre ignore|sans-porte]
```
1. Unity absent ou port 8000 déjà pris : code 2, sans rien lancer. Le dossier est créé ; `verdict.txt`, `lot937-enceinte.json` et les images `*--1-enceinte-en-chantier.png`, `*--2-enceinte-finie.png` d'un essai précédent sont effacés.
2. Unity : `<unity> -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 937 -forgeSeed S -forgeTicks 0 -forgeServiceEpreuve -forgeTravailEnceinte 0.01 -forgeCaptures <dossier> -logFile <dossier>\unity.log`, plus `-forge937SansPorte` sous `--contre sans-porte`. J = `"0.01"` est une seule constante, passée telle quelle à Unity et à la référence. Durée bornée par `JALON1._unity`, service résiduel coupé par `JALON1._couper_service_residuel`. Un code non nul donne 2 avec la fin du journal. Les deux images et le rapport doivent être non vides et horodatés après le lancement. Le rapport est validé (`_rapport`) **avant** de lancer la référence.
3. La référence : depuis `jeu/`, sur le port 8000, arrêtée dans un `finally`, `[sys.executable, "-m", "sim.service", "--epreuve", "--travail-enceinte", "0.01", "--seed", S, "--jours-par-seconde", "0"]`. Sous `--contre ignore`, même liste, mais `-m sim.service` est remplacé par `-c IGNORANT <chemin du lanceur>`. `IGNORANT` charge le lanceur par son chemin, remplace `sim.service.recevoir_intention` par `ignorante(recevoir_intention)`, puis appelle `sim.service.main(sys.argv[1:])`. `ignorante(recevoir)` rend une fonction qui ne fait rien pour une intention `tracer_enceinte` et appelle `recevoir` sinon. Une fonction `commande_reference(graine, ignore)` rend cette liste.
4. `references(port, coins, travail)` rejoue les gestes : l'unique départ au siège « Biskra » de `/departs`, `choisir_depart`, un tick, `tracer_route` `[[-66,2.2],[-120,2.2]]` de 4 m (constante recopiée de `Lot937.cs`, commentée), un tick, `tracer_enceinte` sur les `coins` **du rapport**, puis douze fois un tick et `/plan?cell=X`. Chaque intention doit être acceptée, l'enceinte au tick 2 ; sinon `ValueError`. Elle rend `{"cellule", "travail", "coins", "plans"}`. Toute requête est bornée et nomme son statut en cas d'échec.
5. `travail_attendu(coins, travail)` = `max(1, ceil(Σ dist(coin i, coin i+1, le dernier relié au premier) × float(travail)))`, recopiée de `travail_requis_de_enceinte` de `sim/chantiers.py`, dans le même ordre de calcul. `juger(rapport, refs) -> (code, lignes)` et `travail_attendu` sont pures. `contre_epreuve` n'est qu'affiché. `verdict.txt` s'écrit par `CAPITALE._ecrire`.

**Le juge** recompte les écarts de porte depuis les `x`, `y` de `portes_dessinees`. Il ne lit jamais `ecart_porte_m`, ni `tours`, ni `pans`.

**2, épreuve impossible**, quand le rapport est illisible, qu'un champ manque ou a un mauvais type, qu'un entier vaut −1, que `defaut` n'est pas nul, ou que `recu` n'est pas `{acceptee: true, tick: 2}`. Aussi quand `travail_enceinte` du rapport diffère du J de la référence, ou qu'il y a moins de trois coins ou un coin non fini. Également quand les ticks des `releves` ne se suivent pas à partir de 3, ou dépassent 14. Et quand **l'échantillon est vide** : aucun relevé, ou aucun relevé avec une porte servie. Côté référence : des plans qui ne sont pas aux ticks 3 à 14, ou une autre cellule. Une référence sans enceinte n'est **pas** impossible : c'est un écart.

**1, écart**, dès qu'une comparaison échoue, chacune sur sa ligne avec le vu et l'attendu :
- `cellule` égale la cellule servie ;
- pour chaque relevé au tick t, contre le plan servi au même tick :
  - `t contour` : contour servi égal aux `coins` du rapport (« aucune enceinte servie » sinon) ;
  - `t travail requis (session)` et `t travail requis (servi)` égaux à `travail_attendu` ;
  - `t travail fourni` et `t en chantier` égaux au servi ; `t étape` vaut `fini` si et seulement si le servi n'est plus en chantier ;
  - `t portes servies` : la liste du rapport égale celle du plan, en `{x, y, rue, identifiant}`, dans l'ordre ;
  - `t portes dessinées` : autant que de portes servies, chaque porte servie à 0,05 m au plus (distance horizontale) d'une porte dessinée ;
- `achevée` : `acheve_au_tick` égal au premier tick servi hors chantier, qui doit exister, et le dernier relevé est à ce tick.

**0, égalité**, sinon. Le verdict écrit, par relevé : le tick, le fourni et le requis vus et servis, l'étape, et les portes dessinées sur servies (« 1/1 »). Il finit par le tick d'achèvement.

## Périmètre
pc/epreuve_enceinte.py
jeu/ville/tests/test_juge_enceinte.py
jeu/ville/README.md
docs/mesures/938-epreuve-enceinte/rapport-normal.json
docs/mesures/938-epreuve-enceinte/rapport-sans-porte.json
docs/mesures/938-epreuve-enceinte/verdict-normal.txt
docs/mesures/938-epreuve-enceinte/verdict-ignore.txt
docs/mesures/938-epreuve-enceinte/verdict-sans-porte.txt
docs/briefs/938-le-juge-de-l-epreuve-de-l-enceinte.md

## Conditions de succès
Budget : environ 100 lignes de lanceur et de juge, 60 de tests, 7 de README, 26 de mesures (deux rapports d'une ligne, trois verdicts de 8 lignes au plus), et le brief. Le total, ajouts et suppressions, fichiers neufs compris, reste strictement sous 300 lignes. Sur le PC : éditeur fermé, depuis la racine, en PowerShell.

SC1 — **Le juge, sans PC.** Commande : `python3 -m pytest jeu/ville/tests/test_juge_enceinte.py -q`, rouge avant le lanceur (fichier introuvable), vert après. Les tests relisent les deux rapports versés sans les modifier sur disque. Deux références, une fois par module, en mémoire : `references(port, coins de rapport-normal.json, "0.01")` sur `_service_epreuve(epreuve=True)` de `sim/tests/test_monde.py`, dans un `pytest.MonkeyPatch.context()` qui met `sim.constants.TRAVAIL_ENCEINTE_JOURNEES_PAR_M` à 0,01. La seconde ajoute `sim.service.recevoir_intention` remplacé par `ignorante(...)` du lanceur. La constante revient à 30 à la sortie. Cas exigés :
- `travail_attendu` : carré ±80 → 7 à `"0.01"`, 19 200 à `"30"` ; triangle `[[0,0],[0.1,0],[0,0.1]]` → 1 ;
- la référence mesurée : ticks 3 à 14, fourni 1, 3, 7, achevée au tick 5, la porte (−80 ; 2,2) « plan » à chaque tick ; la référence ignorante : `enceinte` et `portes` absentes à chaque tick ;
- `rapport-normal.json` rend 0 ; contre la référence ignorante, il rend **1**, avec parmi les écarts `3 contour`, `3 travail requis (servi)`, `3 portes servies` et `achevée` ;
- `rapport-sans-porte.json` rend 1, avec pour seuls écarts `t portes dessinées` aux trois ticks ; mis à `contre_epreuve: ""`, il garde les mêmes écarts ;
- copies mutées du rapport normal qui rendent **1** : une porte dessinée déplacée de 0,1 m ; une porte dessinée doublée ; `travail_requis` + 1 à un relevé ; `acheve_au_tick` à 4 ; l'étape `piquets` au dernier relevé ; la `rue` d'une porte servie changée. Une copie mutée de la référence : contour servi décalé d'un mètre ; `travail_requis` servi à 19 200 ;
- copies qui rendent **2** : un `defaut` ; `recu.tick` à 3 ; un champ retiré ; un tick à −1 ; `releves` vide ; les ticks 3, 5, 6 ; `travail_enceinte` à `"30"` ; aucune porte servie dans aucun relevé ;
- `commande_reference(0, False)` contient `-m sim.service` et `--epreuve --travail-enceinte 0.01 --seed 0 --jours-par-seconde 0` ; `commande_reference(0, True)` contient `-c`, le chemin du lanceur et les mêmes options ;
- `main` avec `--unity` vers un chemin absent rend 2 sans rien lancer et ne laisse que `verdict.txt`. `main` avec un faux Unity existant, `JOUER._repond` faux et `JALON1._unity` remplacé par une fonction qui note ses arguments et rend 1 : rend 2, et les arguments notés contiennent `-forgeLot 937`, `-forgeServiceEpreuve`, `-forgeTravailEnceinte 0.01`, plus `-forge937SansPorte` sous `--contre sans-porte` seulement ;
- le juge ne modifie jamais ses entrées.

Contre-épreuve : un juge qui lit `ecart_porte_m` laisse passer la porte doublée ou déplacée ; un juge qui prend le travail requis du rapport pour référence laisse passer la référence à 19 200.

SC2 — **L'épreuve normale.** `py pc\epreuve_enceinte.py --sortie "$env:TEMP\lot938-normal"` rend **0**. Le verdict dit ÉGALITÉ, la cellule 10103, 7 journées requises, fourni 1, 3, 7 aux ticks 3, 4, 5, porte 1/1 à chaque relevé, achevée au tick 5. Le codeur ouvre les deux images. Puis verser par copie : `Copy-Item "$env:TEMP\lot938-normal\lot937-enceinte.json" docs\mesures\938-epreuve-enceinte\rapport-normal.json` et `Copy-Item "$env:TEMP\lot938-normal\verdict.txt" docs\mesures\938-epreuve-enceinte\verdict-normal.txt`.

SC3 — **Chaque contre-épreuve fait échouer l'épreuve.** Les deux commandes rendent **1**, jamais 0 ni 2 :
- `py pc\epreuve_enceinte.py --contre ignore --sortie "$env:TEMP\lot938-ignore"` : « aucune enceinte servie », achèvement absent. Verser `verdict.txt` vers `verdict-ignore.txt` ;
- `py pc\epreuve_enceinte.py --contre sans-porte --sortie "$env:TEMP\lot938-sans-porte"` : 0 porte dessinée pour 1 servie aux ticks 3, 4, 5. Verser le rapport vers `rapport-sans-porte.json` et le verdict vers `verdict-sans-porte.txt`.

Contre-épreuve : un lanceur qui rend 0 à l'une d'elles, ou qui rougit par le drapeau et non par la mesure (SC1), refuse le lot.

SC4 — **L'impossible le dit.** `py pc\epreuve_enceinte.py --unity C:\nexiste\pas\Unity.exe --sortie "$env:TEMP\lot938-sans-unity"` rend **2**. Puis, avec `py -m sim.service --seed 0 --jours-par-seconde 0` lancé depuis `jeu\` dans un second terminal, `py pc\epreuve_enceinte.py --sortie "$env:TEMP\lot938-port"` rend **2** (« répond déjà ») sans lancer Unity. Le codeur colle les deux sorties dans la PR.

SC5 — **Rien d'autre ne bouge.** `python3 -m pytest jeu -q` passe en entier, `test_chantiers.py` compris (la constante revenue à 30) ; `py -3 -m pytest jeu/ville/tests -q` passe sur le PC. `git diff --check`, `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre. `git diff --numstat origin/master` totalise moins de 300. Contre-épreuve : un changement dans `3d/`, `jeu/sim/`, un autre script de `pc/` ou un test existant refuse la livraison.

SC6 — **Le README.** Dans `jeu/ville/README.md`, après « L'épreuve des passants », une section « L'épreuve de l'enceinte », au même format : la commande du lanceur et ses drapeaux ; la commande Unity jouée, en entier ; le service de référence, les gestes rejoués et la référence ignorante ; les comparaisons et les codes 0, 1 et 2 ; la commande des tests sans PC ; les liens vers les cinq fichiers versés.

## Hors périmètre
- Toute modification de `Lot937.cs`, `ForgeCapture`, `DesertRoadTool`, `PansDeLEnceinte`, du service ou du moteur. Si la session semble devoir changer, le codeur le dit dans la PR sans l'écrire.
- Le compte des tours et des pans, le cadre des images et le panneau (le contrôle de #937 les tient) ; la preuve complète du jalon (#508).
- Aucune image versée : les captures restent dans les dossiers temporaires et sont jointes au compte rendu.
- Aucun test existant assoupli ni réécrit.

## Photo
sans objet : outil d'épreuve en Python, rien de ce que voit le joueur ne change. Les images du mur aux piquets puis fini sont celles de la session #937 ; le lanceur les reproduit dans `$env:TEMP\lot938-normal`, `$env:TEMP\lot938-ignore` et `$env:TEMP\lot938-sans-porte`, et le codeur joint les six au compte rendu.
