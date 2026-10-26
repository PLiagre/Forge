# Lot #696 — Le kit du désert sait relever son terrain, en Python
Jalon : J4 · Machine : vps · Taille prévue : 270 lignes

## But
Le kit du désert sait relever son terrain selon la classe de relief de la cellule. Ce relèvement se fait autour de l'eau de la guelta, plein au centre et fondu vers le bord. Ses paramètres passent à Unity par `gestes.json`, et l'épreuve du jalon 4 cherche sa route `--sur-une-maison` sur ce terrain relevé.

## Le joueur
Deuxième sous-lot de #683 « Le terrain de la capitale suit le relief de sa cellule » (lui-même sous-lot 5 de #409 « Le jeu ouvre la capitale du joueur »). C'est un lot de fond. Il prépare le geste du J4 de `CAP.md` : le joueur **entre dans sa capitale en 3D** et **y trace des routes vers ses champs ou vers le marché**.

Biskra, la capitale du Zab, est dans une cellule de montagne (10103). Le ksar de 1175 est en plaine. Après le sous-lot 3 de #683 (pc), le joueur du Zab entrera dans une ville aux reliefs plus marqués, d'un tiers environ. Il y sentira que la pente décide ses routes : une route acceptée en plaine devient trop raide ici. La décision « une route vers les champs, ou vers le marché » coûte alors plus cher.

Ce lot ne montre rien encore. Il fixe la règle du relèvement, et la verse là où Unity la lira. Il garde aussi la preuve du jalon juste : la route que l'épreuve fait tracer sur une maison de 1400 doit être refusée par le monde (la maison), pas par Unity (la pente). Mesuré par #683 : sur la grille brute, la route trouvée fait 12,2 % de pente une fois relevée ×1,3. Unity la refuserait pour la pente.

## Règle du monde
Sans objet pour le monde : `sim/` et `jeu/sim/MODELE.md` ne changent pas. C'est un lot d'outil du kit 3D. La classe de relief est celle que le monde tient pour chaque cellule (« La carte et les terres servies, vue dérivée » : clé `relief` de `/carte`). Les cinq classes sont `plaine`, `colline`, `marais`, `montagne` et `haute_montagne`.

Les facteurs de hauteur sont de fidélité niveau 2 : des ordres de grandeur plausibles, jamais sourcés. Ils ne sont pas les facteurs de production de `MODELE.md` (« Paramètres », facteur de relief) ; ils ne règlent que la forme du terrain dessiné.

## Périmètre
3d/local3d/desert/routes.py
3d/local3d/desert/sorties/ville/ksar_des_sept_puits/routes/gestes.json
3d/local3d/desert/sorties/ville/oued_des_vents/routes/gestes.json
3d/local3d/desert/README.md
pc/epreuve_jalon4.py
jeu/ville/tests/test_epreuve_jalon4.py

Tout autre chemin est interdit, Unity compris (`DesertRoads.cs` est le sous-lot 3). Aucun test existant ne change : les cas s'ajoutent en fin de `test_epreuve_jalon4.py`. `_aides`, `grilles` et les deux tests `sur_une_maison` existants restent tels quels, et doivent rester verts.

Budget : environ 35 lignes dans `routes.py`, 18 dans les deux `gestes.json`, 8 dans l'épreuve, 6 dans le README, 75 de tests ; le reste pour ce brief.

### `routes.py`
**1. Les clés de `PARAMETRES`.** `PARAMETRES` reçoit, après `arrondi`, des clés **plates**. Unity lit `gestes.json` par `JsonUtility`, qui ne lit pas un dictionnaire imbriqué. Voici les clés, dans cet ordre, chacune avec son commentaire d'une ligne :

| clé | valeur | sens |
|---|---|---|
| `relief_plaine` | 1.0 | facteur des hauteurs autour du pivot |
| `relief_marais` | 1.0 | |
| `relief_colline` | 1.15 | |
| `relief_montagne` | 1.3 | |
| `relief_haute_montagne` | 1.3 | |
| `relief_plein` | 400.0 | m, distance de Tchebychev au centre du terrain : facteur plein jusque-là |
| `relief_nul` | 500.0 | m : au-delà, terrain d'origine (le bord, à 512 m, et le raccord à l'horizon restent exacts) |

Ajoute un commentaire sur le plafond. La boîte du kit va de −11 à 42 m (`terrain.json` : `base` −11, `hauteur` 53). Le terrain de la graine 1433 va de −4,11 à 30 m. Le facteur ne peut donc pas dépasser 1,39 autour du pivot, et il en est à ×1,3. Mesuré par #683 : le maximum relevé est de 39,19 m.

**2. `pivot(seed)`.** La fonction rend `float(paysage.plan(seed)['pool']['position'][2])`, le niveau d'eau de la guelta (−0,6375 pour les deux graines versées). C'est autour de ce niveau qu'on relève : le rivage ne bouge pas.

**3. `ecrire_gestes`.** La fonction ajoute `P['pivot'] = pivot(seed)` après les cinq familles et avant `donnees`. Le pivot est ainsi la dernière clé de `parametres`, et les familles se tracent comme avant, sur la grille brute.

**4. `relever(h, classe, P)`.** La fonction rend une **nouvelle** grille et ne touche pas `h`.
- `F = P['relief_' + classe]`. Une classe sans clé lève `ValueError('classe de relief inconnue : ' + classe)`.
- Pour le sommet `[j, i]` : `x = TAILLE/2 − i·pas` et `y = TAILLE/2 − j·pas`, dans le repère du module. On en tire `d = max(|x|, |y|)`.
- On calcule `w = clip((relief_nul − d) / (relief_nul − relief_plein), 0, 1)`, puis `f = 1 + (F − 1)·w`.
- Résultat : `pivot + (h − pivot)·f`, en numpy vectorisé, sans boucle Python.
- **Là où `f == 1`, la valeur est `h` à l'identique** (`np.where`). Le bord au-delà de 500 m, et toute la grille d'une plaine ou d'un marais, ne bougent pas d'un ulp.

### Les deux `gestes.json` versés
Le VPS n'a pas `hauteurs.f32` : `ecrire_gestes` n'y tourne pas. On réécrit donc chaque fichier versé par un script jetable, qui n'est pas versé :
- il lit le fichier, puis remplace `parametres` par `dict(PARAMETRES)`, augmenté de `pivot = routes.pivot(graine)` ;
- il réécrit avec `json.dumps(..., ensure_ascii=False, indent=1)`, sans saut de ligne final, comme `ecrire_gestes`.

Le diff de chaque fichier ne fait qu'ajouter les 8 lignes et la virgule après `arrondi`. `routes`, `implantation` et `graine` sont identiques à l'octet. On met à jour les deux implantations. Unity lira ces clés dans `gestes.json` (sous-lot 3), et une clé absente vaudrait 0 pour `JsonUtility` : un facteur 0 aplatirait tout l'oued.

### `pc/epreuve_jalon4.py`
`poser_route_sur_une_maison` lit `/carte` par `http`, sur le service déjà lancé. Elle y prend le `relief` de l'entrée dont `cell_id` vaut `cellule`. Si aucune entrée ne correspond, elle lève `OSError(f"cellule {cellule} absente de /carte")`.

Elle forme ensuite `P = dict(gestes["parametres"], pivot=routes.pivot(aides["disposition"]["seed"]))`. Puis elle appelle `route_sur_une_maison(base, routes.relever(aides["grille"](ident), relief, P), plaine["largeur"], P)`. `route_sur_une_maison` ne change pas.

Pourquoi le pivot vient de `routes.pivot` et pas seulement du fichier : c'est la même fonction que celle d'`ecrire_gestes`, que `preparer_sessions` rappelle avant chaque essai. Et le faux jeu de gestes du test existant (`_aides`) n'a pas de pivot : le lire dans le fichier ferait rougir ce test.

Le docstring dit : « sur la grille relevée au relief que /carte sert pour la cellule ».

### README
Dans `3d/local3d/desert/README.md`, sous « Les paramètres vivent dans `routes.py` », ajoute un paragraphe. Il dit : facteur par classe, fondu 400 → 500 m, pivot = l'eau de la guelta, `relever`, et la route `--sur-une-maison` cherchée sur la grille relevée. Ajoute aussi « relief » à la ligne `gestes.json` du tableau.

## Conditions de succès
Toutes les commandes partent de la racine, sur le VPS.

**SC1 — `relever` relève autour du pivot, avec le fondu.** Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q -k relever`, qui rend 0. Le test prend une grille `RESOLUTION × RESOLUTION` aléatoire, de graine fixe, entre −5 et 30 m, et `P = dict(PARAMETRES, pivot=routes.pivot(1433))`. Il vérifie :
- `plaine` et `marais` rendent une grille `np.array_equal` à l'entrée ;
- `montagne` au sommet central (i = j = 1024) vaut `pivot + (h − pivot)·1,3` (à 1e-9 près), et `colline` y vaut ×1,15 ;
- `montagne` à `x = 450 m` (i = 124, j = 1024) vaut ×1,15, au milieu du fondu ;
- tous les sommets de `d ≥ 500` (i ou j ≤ 24 ou ≥ 2024) sont `==` à l'entrée ;
- une grille constante au pivot reste au pivot ;
- l'entrée n'est pas modifiée ;
- `relever(h, 'desert', P)` lève une `ValueError` qui nomme `desert`.

Contre-épreuves, chacune fait rougir son assertion : un `relever` sans fondu (`w = 1` partout) rougit le bord ; un pivot à 0 rougit le pivot ; sans `np.where`, l'identité de la plaine rougit.

**SC2 — les paramètres versés sont ceux qu'`ecrire_gestes` écrit.** Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q -k gestes_verses`, qui rend 0. Le test vérifie quatre choses :
- les valeurs de la table ci-dessus sont dans `PARAMETRES`, et `pivot` n'y est pas ;
- `max(relief_*) ≤ 1,39` ;
- pour chaque implantation versée, `parametres["pivot"] == routes.pivot(graine)`, et ce pivot égale `guelta.z` de son `terrain.json` versé ;
- `ecrire_gestes` reproduit le fichier à l'octet. Le test patche `routes.grille`, les cinq traceurs (`anciennes`, `plaine`, `flanc`, `raide_long`, `raide_travers` rendent les routes du fichier versé) et `routes.terrain.SORTIES` (vers `tmp_path`). Les octets écrits doivent égaler ceux du fichier versé.

Contre-épreuves : retirer la ligne `P['pivot']` d'`ecrire_gestes` rougit la comparaison à l'octet ; `relief_montagne = 1.4` rougit le plafond.

**SC3 — les routes versées ne bougent pas.** La commande suivante rend 0 :
`python3 -c "import json,subprocess as s;f=['3d/local3d/desert/sorties/ville/'+i+'/routes/gestes.json' for i in ('ksar_des_sept_puits','oued_des_vents')];a=[(json.loads(s.check_output(['git','show','origin/master:'+p])),json.load(open(p,encoding='utf-8'))) for p in f];assert all(v['routes']==n['routes'] and all(n['parametres'][k]==x for k,x in v['parametres'].items()) for v,n in a)"`
Contre-épreuve : changer une coordonnée d'une route versée fait lever l'`AssertionError`.

**SC4 — `--sur-une-maison` cherche sur la grille relevée au relief servi.** Commande : `python3 -m pytest jeu/ville/tests/test_epreuve_jalon4.py -q -k sur_une_maison`, qui rend 0. La commande prend les deux tests existants, inchangés, et un nouveau, paramétré sur `("servi", "colline")`. Le nouveau test reprend le montage du test existant : `_aides` avec la grille `raide`, et un `appeler_unity` qui ne doit pas être appelé. Il ajoute trois espions :
- `epreuve.http`, enveloppé : quand le paramètre vaut `colline`, la réponse de `/carte` est réécrite pour donner `colline` à la cellule de Biskra ;
- `routes.relever`, enveloppé, qui note la classe reçue ;
- `epreuve.route_sur_une_maison`, qui note `(h, P)` et rend `None`.

`main(["--avec-unity", "--sortie", …, "--sur-une-maison"])` doit rendre 2, avec « aucune route sur une maison » dans le verdict. Puis, selon le paramètre :
- avec `servi`, la classe notée est `montagne`, celle que `/carte` sert pour 10103 ;
- avec `colline`, la classe notée est `colline` ;
- dans les deux cas, `h` est `np.array_equal` à `routes.relever(raide, classe, dict(PARAMETRES, pivot=routes.pivot(0)))` et diffère de la grille brute.

Contre-épreuves : passer la grille brute à `route_sur_une_maison` rougit l'égalité ; une classe écrite en dur (`montagne`) rougit le cas `colline`.

**SC5 — rien d'autre ne bouge.** `python3 -m pytest jeu -q` rend 0. `git diff --name-only origin/master` ne liste que le périmètre et ce brief.

## Hors périmètre
- Unity : `DesertRoads` qui lit les facteurs et relève sa copie du terrain dans `Preparer`, l'outil, la photo de Biskra (sous-lot 3 de #683, pc). `ClientCarte` qui lit `relief` (sous-lot 1 de #683, pc).
- Retracer les routes versées sur un terrain relevé. Les familles de gestes restent tracées et jugées sur la grille brute de `hauteurs.f32`.
- Le jugement des routes posées par Unity (`juger`, `rejouer`), qui ne lit pas encore le relief.
- Le monde, `sim/`, `/carte` et `MODELE.md`. Les kits des autres terres (jalon 9).
