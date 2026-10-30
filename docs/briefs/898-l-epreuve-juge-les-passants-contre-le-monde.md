# Lot #898 — L'épreuve juge les passants contre le monde
Jalon : J4 · Machine : pc · Taille prévue : 290 lignes

## But
Une commande du PC lance la session #897, rejoue ses gestes sur un service d'épreuve neuf et rend un verdict qui peut échouer : à Biskra, autant de passants par métier que le bourg servi en donne, chaque ouvrier sur un chantier qui a des bras, et plus personne dans la rue une fois le bourg vidé.

## Le joueur
Le joueur trace trois routes, entre dans Biskra et voit un ouvrier marcher sur l'une d'elles, au milieu des paysans ; quand les gens du bourg partent, la rue se vide (#784, #787, #788, #897). Il sent que chaque bras pris aux champs se voit dans sa capitale, et que la ville ne lui ment pas. Ce lot de fond rend cette promesse vérifiable : il juge l'écran du J4 « une ville vivante dont chaque passant suit le monde » et sa décision « des bras au chantier, c'est moins de bras aux champs » (`CAP.md`, jalon 4). C'est le sous-lot 3 de #789 (découpé de #421) ; la preuve complète du jalon, #508, le reprendra. La demande n'a pas de phrase « Le joueur » distincte : celle-ci en dit le bénéfice, selon « La règle d'un lot ».

## Règle du monde
Sans objet : outil d'épreuve, aucune règle nouvelle. Il lit sans les changer « Les lieux d'une cellule, vue dérivée » (le bourg est le rang 0), « Les foyers par métier », « Le chantier et ses bras » et le montage `POST /epreuve/vider-bourg` de « Ce que porte un lieu » (#896) dans `jeu/sim/MODELE.md`. Le service d'épreuve est déterministe : mêmes graine et gestes, mêmes octets de `/lieu` après le montage (#896, SC4). C'est ce qui permet de comparer la scène d'Unity à un service de référence lancé après elle.

**Dépend de : #896 et #897**, livrés (d0de813f, aa583e42). Rien ne change dans `3d/`, `jeu/sim/` ni dans un autre script de `pc/`.

**Mesures du chef**, service `--epreuve`, graine 0, gestes de `Lot897.cs`. Biskra = cellule 10103, seigneurie 6. Au tick 5 : bourg 165, cellule 3 459 (`ouvriers` 15 personnes, `paysans` 3 444), chantiers du jour `rue` 0, 1, 2 à 5 bras ; donc 16 passants, `ouvriers` 1 et `paysans` 15. `vider-bourg` rend `{"cell_id":10103,"tick":5}`. Au tick 6 : bourg 0, bras 5, 5 et 3, donc 0 passant.

**Le lanceur**, `pc/epreuve_passants.py`, sur le modèle de `pc/epreuve_vie_bourg.py`, dont il peut charger les aides par `importlib` sans le modifier :
```
py pc\epreuve_passants.py --sortie <dossier> [--seed S] [--unity CHEMIN] [--contre en-trop|ailleurs|anciens]
```
1. Unity absent ou port 8000 déjà pris : code 2, Unity n'est pas lancé. Le dossier est créé ; `verdict.txt`, `passants-bourg.json` et les deux images d'un essai précédent sont effacés.
2. Unity : `<unity> -batchmode -projectPath 3d/unity -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 897 -forgeSeed S -forgeTicks 0 -forgeServiceEpreuve -forgeCaptures <dossier> -logFile <dossier>\unity.log`, plus `-forge897PassantEnTrop`, `-forge897OuvriersAilleurs` ou `-forge897GarderAnciens` selon `--contre`. Sans `-quit` ni `-nographics`, durée bornée par `JALON1._unity`, service résiduel coupé par `JALON1._couper_service_residuel`. Un code non nul donne 2 avec la fin du journal.
3. Les preuves de cet essai : `passants-bourg.json`, `*--01-ouvriers-au-chantier.png` et `*--02-bourg-vide.png`, non vides et horodatés après le lancement (`JALON1.MARGE_HORODATAGE_S`). Sinon : 2.
4. La référence : un service neuf `python -m sim.service --epreuve --seed S --jours-par-seconde 0`, depuis `jeu/`, sur le port 8000, arrêté dans un `finally`. `references(port)` y rejoue exactement les gestes de `Lot897.cs`, en constantes recopiées et commentées : l'unique départ au siège « Biskra » de `/departs` (aucun ou plusieurs : erreur) ; `POST /intention` `choisir_depart` ; `POST /tick?n=1` ; trois `tracer_route` (`maison` « seigneurie-<id> », `cell`, points `[[0,d],[40,d]]` pour d = 0, 8, 16, `largeur_m` 4) ; quatre `POST /tick?n=1`. Chaque intention doit être acceptée. Puis `/lieu?cell=X&bourg=1` et `/plan?cell=X`, un seul `POST /epreuve/vider-bourg?cell=X`, un `POST /tick?n=1`, et les deux mêmes lectures. Toute requête est bornée et nomme son statut en cas d'échec.
5. `juger(rapport, refs) -> (code, lignes)` est pure : elle ne lit aucun fichier, ne modifie pas ses entrées, et `contre_epreuve` n'est qu'affiché. `passants_attendus(lieu)` est pure aussi. `verdict.txt` s'écrit par `CAPITALE._ecrire`.

**Le juge** lit les passants dans `liste`, jamais dans `attendu`, `projete`, `pose` ni `par_metier` du rapport : il compte lui-même.

**2, épreuve impossible**, quand le rapport est illisible, qu'un champ manque ou a un mauvais type, que `defaut` n'est pas nul, que les `etats` ne sont pas exactement « chantier » puis « vide », ou qu'un `bourg` ou un tick vaut −1. Aussi quand la référence est inutilisable : cellules ou ticks discordants (5 puis 6), `vider-bourg` qui ne rend pas la cellule et le tick 5, somme des métiers différente de la population, bourg plus grand que la cellule, bourg vidé non nul. Et quand **l'échantillon est vide** : aucun chantier de rue avec des bras, ou aucun ouvrier attendu, au tick 5. Une panne ne prouve aucun rouge.

**1, écart**, dès qu'une comparaison échoue, chacune sur sa ligne avec ce qui est vu et ce qui est attendu :
- `cellule` égale la cellule servie ; `tick_lieu`, `tick_plan` et `tick_applique` égaux au tick servi ; `bourg` égal à la population servie du rang 0, à chaque état ;
- **le nombre** : `passants_attendus` recalcule la règle de #784 sur le `/lieu` servi. N = bourg // 10. Les poids sont les personnes de chaque métier autre que `paysans`, et pour `paysans` max(0, bourg − les autres) ; les poids nuls tombent. Chaque part vaut N × poids // total, et le reste va aux plus grands restes, puis au nom par ordre ordinal. Un bourg à 0 donne {}. Le compte par métier de `liste` doit égaler ces parts (parts nulles ignorées des deux côtés), et `passants` doit égaler la longueur de `liste`, ses `id` étant tous distincts ;
- **les ouvriers** : à l'état « chantier », chaque passant `ouvriers` a pour destination « rue N », avec un chantier du jour `rue` N servi à des bras > 0. Sa distance horizontale (`x`, `y`) à la polyligne servie de la rue N vaut au plus 0,05 m. La ligne dit « ouvrier hors chantier » avec la distance ;
- **le vidage** : à l'état « vide », `liste` vide et `passants` 0. Tout `id` de l'état « vide » déjà présent à l'état « chantier » est nommé sur une ligne « anciens objets maintenus » ;
- `camera` identique aux deux états.

**0, égalité**, sinon. Le verdict écrit, pour chaque état, le tick, le bourg, les passants vus et attendus par métier, et les ouvriers sur un chantier (« 1/1 »).

## Périmètre
pc/epreuve_passants.py
jeu/ville/tests/test_epreuve_passants.py
jeu/ville/README.md
docs/mesures/898-epreuve-passants/rapport-normal.json
docs/mesures/898-epreuve-passants/rapport-en-trop.json
docs/mesures/898-epreuve-passants/rapport-ailleurs.json
docs/mesures/898-epreuve-passants/rapport-anciens.json
docs/mesures/898-epreuve-passants/verdict-normal.txt
docs/mesures/898-epreuve-passants/verdict-en-trop.txt
docs/mesures/898-epreuve-passants/verdict-ailleurs.txt
docs/mesures/898-epreuve-passants/verdict-anciens.txt
docs/briefs/898-l-epreuve-juge-les-passants-contre-le-monde.md

## Conditions de succès
Budget : environ 95 lignes de lanceur et de juge, 55 de tests, 7 de README, 36 de mesures (quatre rapports d'une ligne, quatre verdicts de 8 lignes au plus), et le brief. Le total, ajouts et suppressions, fichiers neufs compris, reste strictement sous 300 lignes. Sur le PC : éditeur fermé, depuis la racine, en PowerShell.

SC1 — **Le juge, sans PC.** Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_passants.py -q`, rouge avant le lanceur (fichier introuvable), vert après. Les tests relisent les quatre rapports versés sans les modifier sur disque. La référence vient de `references(port)` sur un vrai service, graine 0, en mémoire (`_service_epreuve(epreuve=True)` de `sim/tests/test_monde.py`, une fois par module). Cas exigés :
- `passants_attendus` rend les parts des tests de `PassantsDuBourgTests.cs` : bourg 109 du témoin → artisans 2, mineurs 2, paysans 6 ; l'égalité de reste départagée par le nom (forgerons 1) ; bourg 20 → artisans 1, mineurs 1 ; bourg 0 → {} ; et ouvriers 1, paysans 15 sur la référence ;
- `rapport-normal.json` rend 0 ;
- `rapport-en-trop.json` rend 1, avec un écart de nombre à l'état « chantier » seulement ; `rapport-ailleurs.json` rend 1, avec « ouvrier hors chantier » seulement ; `rapport-anciens.json` rend 1, avec des écarts à l'état « vide » seulement, dont « anciens objets maintenus ». Chacun, mis à `contre_epreuve: ""`, garde les mêmes écarts ;
- copies mutées du rapport normal qui rendent **1** : un ouvrier déplacé de 0,1 m ; sa destination mise à « rue 9 » ; un paysan retiré ; un paysan doublé avec le même `id` ; `bourg` + 1 ; `tick_plan` + 1 ; un passant ajouté à l'état « vide » ;
- copies qui rendent **2** : un `defaut` ; les états inversés ; un champ retiré ; un `bourg` à −1 ; une référence sans aucun chantier à bras au tick 5 ; une référence vidée qui sert encore un bourg habité ;
- un service sans `--epreuve` fait échouer `references` sur `POST /epreuve/vider-bourg` par son HTTP 404 ;
- `main` avec `--unity` vers un chemin absent rend 2 sans rien lancer et ne laisse que `verdict.txt` ;
- le juge ne modifie jamais ses entrées.

Contre-épreuve : un juge qui recopie `attendu` ou `par_metier` du rapport laisse passer le paysan doublé ; un juge qui accepte une liste vide d'ouvriers fait échouer le cas d'échantillon vide.

SC2 — **L'épreuve normale.** `py pc\epreuve_passants.py --sortie "$env:TEMP\lot898-normal"` rend **0**. Le verdict dit ÉGALITÉ, la cellule 10103, 16 passants (ouvriers 1, paysans 15) au tick 5, l'ouvrier sur son chantier, puis 0 au tick 6. Le codeur ouvre les deux images. Puis verser par copie : `Copy-Item "$env:TEMP\lot898-normal\passants-bourg.json" docs\mesures\898-epreuve-passants\rapport-normal.json` et `Copy-Item "$env:TEMP\lot898-normal\verdict.txt" docs\mesures\898-epreuve-passants\verdict-normal.txt`.

SC3 — **Chaque drapeau fait échouer l'épreuve.** Les trois commandes rendent **1**, jamais 0 ni 2, et sont versées de même vers `rapport-<nom>.json` et `verdict-<nom>.txt` :
- `py pc\epreuve_passants.py --contre en-trop --sortie "$env:TEMP\lot898-en-trop"` : 17 passants vus, 16 attendus ;
- `py pc\epreuve_passants.py --contre ailleurs --sortie "$env:TEMP\lot898-ailleurs"` : « ouvrier hors chantier », à plus de 5 m ;
- `py pc\epreuve_passants.py --contre anciens --sortie "$env:TEMP\lot898-anciens"` : 16 passants à l'état « vide », tous anciens.

Contre-épreuve : un lanceur qui rend 0 à l'une d'elles, ou qui rougit par le drapeau et non par la mesure (SC1), refuse le lot.

SC4 — **L'impossible le dit.** `py pc\epreuve_passants.py --unity C:\nexiste\pas\Unity.exe --sortie "$env:TEMP\lot898-sans-unity"` rend **2**. Puis, avec `py -m sim.service --seed 0 --jours-par-seconde 0` lancé depuis `jeu\` dans un second terminal, `py pc\epreuve_passants.py --sortie "$env:TEMP\lot898-port"` rend **2** (« répond déjà ») sans lancer Unity. Le codeur colle les deux sorties dans la PR.

SC5 — **Rien d'autre ne bouge.** `python3 -m pytest jeu -q` passe en entier ; `py -3 -m pytest jeu/ville/tests -q` passe sur le PC ; `git diff --check`, `git diff --name-only origin/master` et `git ls-files --others --exclude-standard` ne nomment que le Périmètre ; `git diff --numstat origin/master` totalise moins de 300. Contre-épreuve : un changement dans `3d/`, `jeu/sim/`, `pc/epreuve_vie_bourg.py` ou un test existant refuse la livraison.

SC6 — **Le README.** Dans `jeu/ville/README.md`, après « L'épreuve de la vie du bourg », une section « L'épreuve des passants », au même format : la commande du lanceur et ses drapeaux ; la commande Unity jouée, en entier ; le service de référence, les gestes rejoués et le seul montage `vider-bourg` ; les trois comparaisons et les codes 0, 1 et 2 ; la commande des tests sans PC ; les liens vers les huit fichiers versés.

## Hors périmètre
- Toute modification de `Lot897.cs`, `PassantsDeLaVille`, `PassantsDuBourg`, `TrajetsDesMetiers`, `ForgeCapture`, du service, du montage `vider-bourg` ou du moteur. Si la session semble devoir changer, le codeur le dit dans la PR sans l'écrire.
- La destination des paysans, la visibilité dans l'image et les écarts au trajet (le contrôle de #897 les tient), la tenue des 60 images/s (#422), la preuve complète du jalon (#508).
- Aucune image versée : les captures restent dans les dossiers temporaires et sont jointes au compte rendu.
- Aucun test existant assoupli ni réécrit.

## Photo
sans objet : outil d'épreuve en Python, rien de ce que voit le joueur ne change. Les images de la rue au chantier puis vidée sont celles de la session #897 ; le lanceur les reproduit dans `$env:TEMP\lot898-normal`, `$env:TEMP\lot898-en-trop`, `$env:TEMP\lot898-ailleurs` et `$env:TEMP\lot898-anciens`, et le codeur joint les huit au compte rendu.
