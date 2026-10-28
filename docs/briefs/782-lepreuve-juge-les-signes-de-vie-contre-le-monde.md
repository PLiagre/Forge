# Lot #782 — L’épreuve juge les signes de vie contre le monde
Jalon : J4 · Machine : pc · Taille prévue : 285 lignes

## But
Une commande du PC lance la session #781, relit le monde servi et rend un verdict qui peut échouer : chaque maison habitée de Biskra fume quand le bourg a de quoi manger, aucune ne fume quand il a faim, et aucun étal ne reste garni dans un bourg affamé.

## Le joueur
Le joueur qui entre dans Biskra voit ses maisons habitées fumer et s'éclairer le soir, et ses étals se vider quand le bourg n'a plus de vivres (#779, #780, #781). Il sent que sa ville vit de son ravitaillement : une route vers les champs, ou d'autres chantiers, cela se lit sur la place. Ce lot de fond rend cette promesse vérifiable : il écrit la contre-épreuve de J4 « un étal plein dans un bourg affamé fait échouer l'épreuve » (`CAP.md`, jalon 4, « La preuve »). La preuve complète du jalon, #508, la reprendra. La demande n'a pas de phrase « Le joueur » distincte : celle-ci en dit le bénéfice selon « La règle d'un lot ».

## Règle du monde
Sans objet : outil d'épreuve, aucune règle nouvelle. Il lit sans les changer les règles de niveau 2 de `jeu/sim/MODELE.md` : « Le panier de marchandises » (absence contre zéro), « Ce que veut dire « affamée » », « Les lieux d'une cellule, vue dérivée », la route `/occupation` (#776 : toute case de la base est habitée) et le montage jetable `POST /epreuve/vider-panier` (#777). Le service d'épreuve est déterministe : deux services `--epreuve` de même graine préparent le même bourg affamé (#777, SC4). C'est ce qui permet de comparer la session d'Unity à un service de référence lancé après elle.

**Dépend de : #781**, livré (978a79e) : `ForgeLocal3D.Capture.Photographier -forgeLot 781 -forgeServiceEpreuve [-forgeGarderEtalPlein]` écrit `vie-bourg.json` et deux images dans le dossier de `-forgeCaptures`. Rien ne change dans Unity, `jeu/sim/` ni `Pont/`.

**Le lanceur**, `pc/epreuve_vie_bourg.py`, sur le modèle de `pc/epreuve_ville1400.py` (helpers de `epreuve_jalon1.py`, `epreuve_capitale.py`, `epreuve_transition.py`, `jouer.py` chargés par `importlib`, sans les modifier) :
```
py pc\epreuve_vie_bourg.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--garder-etal-plein]
```
1. Port 8000 déjà pris, ou Unity absent : code 2, Unity n'est pas lancé. Le dossier est créé ; `verdict.txt`, `vie-bourg.json` et les deux images d'un essai précédent sont effacés avant le lancement.
2. Unity : `<unity> -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 781 -forgeSeed S -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures <dossier> -logFile <dossier>\unity.log`, plus `-forgeGarderEtalPlein` avec `--garder-etal-plein`. Sans `-quit` ni `-nographics`. Durée bornée par `JALON1._unity`. Ensuite, le service resté ouvert est coupé par `JALON1._couper_service_residuel`. Un code non nul donne 2 avec la fin du journal.
3. Les preuves de cet essai : `vie-bourg.json` et les deux images `*--01-place-nourrie.png` et `*--02-place-affamee.png`, non vides, horodatées après le lancement (`JALON1.MARGE_HORODATAGE_S`). Sinon : 2.
4. La référence : un service neuf `python -m sim.service --epreuve --seed S --jours-par-seconde 0`, depuis `jeu/`, sur le port 8000, attendu par `JOUER._attendre_pret`, arrêté dans un `finally`. La fonction `references(port)` lit `/departs` et y prend l'unique départ au siège nommé « Biskra » (aucun ou plusieurs : erreur). Elle lit `/lieu?cell=X&bourg=1` et `/occupation?cell=X`, envoie une seule fois `POST /epreuve/vider-panier?cell=X`, puis relit les deux routes. Aucune autre requête ne change le monde. Toute requête est bornée et nomme son statut en cas d'échec.
5. `juger(rapport, refs) -> (code, lignes)` est une fonction pure : elle ne lit aucun fichier, ne modifie pas ses entrées, et le drapeau `contre_epreuve` du rapport n'est qu'affiché. `verdict.txt` s'écrit par `CAPITALE._ecrire`.

**Le juge.** **2, épreuve impossible**, quand :
- le rapport est illisible, ou un champ manque ou a un mauvais type ;
- `defaut` n'est pas nul, ou les `etats` ne sont pas exactement « nourrie » puis « affamee » ;
- une valeur mesurée vaut −1 ;
- **l'échantillon est vide** : aucune maison, aucun étal, ou aucun étal `nourriture` dans un état ;
- la référence est inutilisable : base d'occupation vide, ticks discordants, bourg nourri sans nourriture strictement positive ou avec une faim non nulle, bourg vidé sans nourriture présente à zéro et faim strictement positive.

Une panne ne prouve aucun rouge. Sinon **1, écart**, dès qu'une de ces comparaisons échoue, chacune sur sa ligne avec ce qui est vu et ce qui est attendu :
- `cellule` égale la cellule de Biskra servie ;
- pour chaque état : `tick` et `tick_local` égaux au tick servi, `population`, `nourriture_kg` (à l'égalité exacte, sans tolérance) et `faim_ticks` égaux au bloc `bourg` servi ;
- **les maisons** : les couples (`rang`, `indice`) forment exactement l'ensemble {(rang, j) : j < foyers} de la base d'`/occupation`, aux deux états (manquants, doublons, inconnus) ;
- **les fumées** : à l'état nourri, le nombre de maisons avec `emission` et `particules > 0` égale le nombre de foyers de la base ; à l'état affamé, aucune `emission` et zéro particule partout. Le verdict écrit « fumées N/M » pour chaque état ;
- **les lampes** : actives, d'intensité positive et égale entre les deux états, maison par maison ;
- **l'étal** : à l'état nourri, `garnitures_visibles > 0`, un étal `nourriture` visible et un `reference_kg` égal à la nourriture servie. À l'état affamé, `garnitures_visibles == 0` et aucun étal `nourriture` visible : sinon la ligne dit « étal plein en famine » ;
- `causes` vides, `camera` identique et `heure` égale à 19.6 aux deux états.

**0, égalité**, sinon.

## Périmètre
pc/epreuve_vie_bourg.py
jeu/ville/tests/test_epreuve_vie_bourg.py
jeu/ville/README.md
docs/mesures/782-epreuve-vie-bourg/rapport-normal.json
docs/mesures/782-epreuve-vie-bourg/rapport-contre.json
docs/mesures/782-epreuve-vie-bourg/verdict-normal.txt
docs/mesures/782-epreuve-vie-bourg/verdict-contre.txt
docs/briefs/782-lepreuve-juge-les-signes-de-vie-contre-le-monde.md

## Conditions de succès
Budget indicatif : environ 90 lignes de lanceur et de juge, 65 de tests, 10 de README, 25 de mesures versées (deux rapports d'une ligne, deux verdicts de 12 lignes au plus) et 96 de brief. Le total, ajouts et suppressions, fichiers neufs compris, reste strictement sous 300 lignes. Sur le PC, éditeur fermé, depuis la racine, en PowerShell.

SC1 — **Le juge, sans PC.** Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_vie_bourg.py -q`, rouge avant le lanceur (fichier introuvable), vert après. Les tests relisent les deux rapports versés tels quels, sans les modifier sur disque. La référence vient de `references(port)` sur un vrai service d'épreuve, graine 0, en mémoire (`_service_epreuve(epreuve=True)` de `sim/tests/test_monde.py`, une fois par module). Cas exigés :
- `rapport-normal.json` rend 0, et le verdict écrit des fumées N/N nourrie et 0/N affamée, avec N > 0 ;
- `rapport-contre.json` rend 1, avec l'écart « étal plein en famine » et aucun écart de fumée, de maison ni de bourg ; mis à `contre_epreuve: false`, il donne les mêmes écarts ;
- copies mutées en mémoire qui rendent **1** : une fumée encore active dans l'état affamé ; une fumée absente dans l'état nourri ; une maison retirée ; une maison doublée ; `nourriture_kg` décalé de 1e-9 ; `faim_ticks` + 1 ; `tick` + 1 ; une intensité de lampe changée ;
- copies qui rendent **2** : `maisons` vide, `etals` vide, ou aucun étal `nourriture`, à chaque état ; un `defaut` ; un −1 ; une référence affamée qui sert encore de la nourriture ;
- un service sans `--epreuve` fait échouer `references` par son HTTP 404 ;
- `main` avec `--unity` vers un chemin absent rend 2 sans rien lancer ;
- le juge ne modifie jamais ses entrées.

Contre-épreuve : un juge qui rend 0 sans comparer l'étal fait échouer le cas contre ; un juge qui accepte une liste vide fait échouer les cas d'échantillon vide.

SC2 — **L'épreuve normale.** Commande : `py pc\epreuve_vie_bourg.py --sortie "$env:TEMP\lot782-normal"`, attendue à **0**. `verdict.txt` dit ÉGALITÉ, la cellule de Biskra, des fumées N/N puis 0/N, et l'étal garni puis vide. Les deux images existent : le codeur les ouvre lui-même. Puis verser par copie : `Copy-Item "$env:TEMP\lot782-normal\vie-bourg.json" docs\mesures\782-epreuve-vie-bourg\rapport-normal.json` et `Copy-Item "$env:TEMP\lot782-normal\verdict.txt" docs\mesures\782-epreuve-vie-bourg\verdict-normal.txt`.

SC3 — **L'étal plein en famine fait échouer l'épreuve.** Commande : `py pc\epreuve_vie_bourg.py --garder-etal-plein --sortie "$env:TEMP\lot782-contre"`, attendue à **1**, jamais à 2. Le verdict nomme « étal plein en famine », avec `garnitures_visibles` positif et la nourriture servie à 0, et rien d'autre en écart. Verser de même vers `rapport-contre.json` et `verdict-contre.txt`. Contre-épreuve : un lanceur qui rendrait 0 ici, ou qui rougirait par le drapeau et non par la mesure (SC1), refuse le lot.

SC4 — **L'impossible le dit.** Commandes : `py pc\epreuve_vie_bourg.py --unity C:\nexiste\pas\Unity.exe --sortie "$env:TEMP\lot782-sans-unity"` rend **2**. Puis, avec `py -m sim.service --seed 0 --jours-par-seconde 0` lancé depuis `jeu\` dans un second terminal, `py pc\epreuve_vie_bourg.py --sortie "$env:TEMP\lot782-port"` rend **2** (« répond déjà ») sans lancer Unity. Le codeur colle les deux sorties dans la PR.

SC5 — **Rien d'autre ne bouge.** Commandes :
- `python3 -m pytest jeu -q` passe en entier ;
- `py -3 -m pytest jeu/ville/tests -q` passe sur le PC ;
- `git diff --check`, `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ;
- `git diff --numstat origin/master` totalise moins de 300.

Contre-épreuve : un changement dans `3d/`, `jeu/sim/`, un autre script de `pc/` ou un test existant refuse la livraison.

SC6 — **Le README.** Dans `jeu/ville/README.md`, après « L'épreuve de la transition », une courte section « L'épreuve de la vie du bourg ». Elle donne :
- la commande complète du lanceur, avec ses drapeaux ;
- la commande Unity qu'il joue, en entier ;
- le service de référence, ce qu'il lit, et le seul `POST` qui change le monde ;
- les comparaisons, et les codes 0, 1 et 2 ;
- la commande des tests sans PC ;
- les liens vers les quatre fichiers versés.

## Hors périmètre
- Toute modification de la session #781, de `EffetsDeMaison`, `EtalDuBourg`, `ForgeCapture`, du service, de l'occupation, de la consommation ou de la faim. Si la session semble devoir changer, le codeur le dit dans la PR sans l'écrire.
- La famine naturelle provoquée par des chantiers, les passants (#421), la tenue des 60 images/s (#422), la preuve complète du jalon (#508).
- Aucune image versée : les captures restent dans les dossiers temporaires et sont jointes au compte rendu.
- Aucun test existant assoupli ni réécrit.

## Photo
sans objet : outil d'épreuve en Python, rien de ce que voit le joueur ne change. Les deux images de la place nourrie puis affamée sont celles du lot 781 ; le lanceur les reproduit dans `$env:TEMP\lot782-normal` et `$env:TEMP\lot782-contre`, et le codeur les joint au compte rendu.
