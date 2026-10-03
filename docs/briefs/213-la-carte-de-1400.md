# Lot #213 — La carte de 1400
Jalon : J2 · Machine : vps · Taille prévue : 290 lignes

## But
`python3 -m forge` rend dans `carte.png` la carte de 1400 que le joueur regarde pour choisir sa terre : les densités de population en fond, les frontières des puissances et leurs noms, les grandes villes, la terre choisie entourée et sa fiche en bas de l'image, le tout lu dans la photographie `monde.json` sans qu'aucun nombre soit calculé par la vue.

## Règle du monde
Sans objet : c'est un lot de vue. La vue **lit** les clés que #212 a mises dans la photographie (`puissance`, `villes`, `densite_hab_par_km2` par cellule ; `terre_choisie` et `villes_hors_carte` à la racine ; voir « La photographie de 1400, vue dérivée » de `jeu/sim/MODELE.md`). Elle ne lit ni `population` ni `area_km2` pour en tirer un nombre, et elle ne touche ni à `sim/` ni à `MODELE.md`. **Base : master après #212** (`c375745`). Si la branche part d'avant, le codeur la rebase d'abord sur `origin/master`.

**Pourquoi `carte.png`, et pas un nouveau fichier.** Le journal publie la capture que rend `atelier/captures.py` : c'est `carte.png`, produit par `python3 -m forge --ticks 30 --seed 0 --sans-chronique --largeur 900`, sans `--lecture` ni `--depart`. Pour que l'écran du jalon 2 arrive au journal sans toucher `atelier/`, c'est `carte.png` qui devient la carte de 1400.

### Ce que la vue lit et dessine
Le nouveau module `jeu/vues/relief/carte1400.py` expose `carte_de_1400(document, *, lecture, largeur) -> (image RGBA numpy, compte_rendu dict)` et `lignes_de_fiche(document) -> list[str]`. Il réutilise ce qui existe, sans le dupliquer : `index_des_cellules`, `_bbox` et `_vers_pixel` de `raster.py` (une seule géométrie pour toutes les cartes), `carte_de_statistique`, `plan_avec_legende` et `_sans_accent` de `statistique.py`.

1. **Le fond : la densité.** C'est `plan_avec_legende(carte_de_statistique(document, lecture=lecture, largeur=largeur))`, donc la même rampe, la même hachure « non mesurée » et la même légende qu'aujourd'hui. Dans `lectures.py`, l'extracteur `_densite` **lit** `cellule.get("densite_hab_par_km2")` (`None` si la clé manque) au lieu de diviser `population` par `area_km2`. Une photographie d'avant #212 refuse donc la lecture `densite` par le chemin existant (« portée par aucune cellule »).
2. **Les frontières.** Chaque cellule a une clé : `puissance["id"]`, ou `-1` si `puissance` est `null`. Un pixel de terre est **frontière** si son voisin de droite ou celui du dessous est de la terre avec une autre clé. La côte n'est pas une frontière. Les pixels frontière sont peints d'une couleur chaude unique, qui ne fait pas partie de la rampe bleue (constante nommée, avec son commentaire).
3. **Les cellules sans puissance** (`puissance: null`, 31 aujourd'hui) : un pixel sur quatre (lignes et colonnes paires) est peint de la couleur des frontières. La densité reste lisible entre les points, et ce motif ne se confond pas avec la hachure grise « non mesurée ».
4. **Les noms des puissances.** Pour chaque puissance, on prend la cellule dont le `centroid` (`x_m`, `y_m`) est le plus proche de la moyenne des centroïdes de ses cellules. Son nom y est écrit sur un petit rectangle sombre (`textbbox` puis `rectangle`, sans `stroke_width`). Ordre : du plus grand nombre de cellules au plus petit, puis par `id`.
5. **Les villes.** Un point blanc cerclé de noir au `centroid` de chaque cellule qui a des `villes`. L'étiquette est le nom de sa ville la plus peuplée, suivi de « +n » si la cellule en a d'autres. La photographie ne porte pas la position exacte des villes : le point est au centre de leur cellule (niveau 2), et l'image le dit.
6. **Les étiquettes ne se chevauchent pas.** On pose d'abord les villes, de la plus peuplée à la moins peuplée, puis les puissances. Une étiquette dont la boîte touche une boîte déjà posée est omise et comptée. Les points des villes, eux, sont toujours dessinés.
7. **La terre choisie.** Si `terre_choisie` n'est pas `null`, le bord de sa cellule (`cell_id`) est tracé en rouge, sur deux pixels : les pixels de la cellule dont un voisin n'en est pas.
8. **La fiche.** Une bande sous la carte, de la largeur de l'image et de la hauteur que demandent ses lignes, porte `lignes_de_fiche(document)`, passées par `_sans_accent` (la police par défaut de Pillow, `ImageFont.load_default()` sans `size`, n'a pas tous les accents) :
   - avec un choix : nom, maison et religion ; siège ; cellule ; habitants ; production en kg par jour ; suzerain et sa maison (ou « maison : aucune ») ; cellules et habitants du suzerain ; nombre de voisins et leurs puissances distinctes (ou « sans puissance ») ;
   - sans choix : « Terre choisie : aucune — python3 -m forge --depart ID » ;
   - toujours : « Villes hors carte : … » (ou « aucune »), et une ligne de légende : « orange : frontières ; pointillé : aucune puissance documentée (n cellules) ; villes au centre de leur cellule ».
   Les nombres sont ceux du document, écrits tels quels. Seule la production est arrondie au kilo, et c'est de l'affichage. Aucune ligne n'est recalculée depuis les cellules.
9. **Les refus.** `Carte1400Erreur(RuntimeError)`, avec un message qui nomme ce qui manque, quand une cellule n'a pas la clé `puissance` ou `villes`, quand la racine n'a pas `terre_choisie` ou `villes_hors_carte` (« photographie antérieure au lot #212 : rephotographier »), ou quand le `cell_id` de `terre_choisie` n'est dans aucune cellule. Rien n'est deviné.
10. **Le compte rendu** est `resume(carte)` de `statistique.py`, inchangé, augmenté de : `puissances` (nombre d'`id` distincts), `cellules_sans_puissance`, `pixels_de_frontiere`, `villes_dessinees` (somme des longueurs des listes `villes`), `cellules_avec_villes`, `villes_hors_carte` (la liste lue), `etiquettes_omises` et `terre_choisie` (l'`id`, ou `None`).

Aucun littéral numérique hors {0, 1, −1, 2} dans le code de rendu sans constante nommée en tête de module (tailles de point, épaisseurs, couleurs, marges), chacune avec sa raison en une ligne, comme dans `statistique.py`.

### La commande
Dans `jeu/forge/__main__.py` :
- `--lecture` prend `default=None`. La carte lit `args.lecture or "densite"`, et le tableau `args.lecture or "population"`. Le tableau garde son comportement d'aujourd'hui (il ne connaît pas la couche `densite`), et la carte montre les densités par défaut. Une lecture explicite vaut pour les deux, comme avant.
- `_carte` appelle `carte_de_1400` et enregistre `carte.png`. `resume.json["carte"]` est le compte rendu ci-dessus. `test_les_vues_lisent_la_meme_photographie` y lit toujours `tick`, `seed` et `cellules`.
- Une `Carte1400Erreur` passe par le `except` existant : code 2, avec « carte : … » sur stderr.
- La docstring du module dit « carte.png : la carte de 1400 — densités, frontières, villes, terre choisie et sa fiche ».

Dans `docs/NOTICE.md` : la ligne de `carte.png`, celle de `--lecture` (« par défaut : densité pour la carte, population pour le tableau ») et la ligne `densite` de la table des lectures (« lue dans la photographie »).

### Le lot regarde lui-même la capture
Le codeur lance, depuis `jeu/`, les deux commandes : celle du journal, `python3 -m forge --ticks 30 --seed 0 --sans-chronique --largeur 900 --sortie /tmp/c213-sans`, puis la même avec `--depart <id du Duché de Bar> --sortie /tmp/c213-bar`. Il **ouvre les deux `carte.png` et les regarde**. À la fin de ce brief, il ajoute une section « ## Ce que la capture montre », de 15 lignes au plus, qui dit ce qu'il voit :
- la France entourée de sa frontière, avec Paris dedans ;
- Le Caire et le delta, Constantinople, Londres ;
- le désert égyptien clair contre le delta et la Flandre foncés ;
- Bar entourée de rouge, et une fiche lisible ;
- combien d'étiquettes sont omises, et où ;
- ce qui est illisible.

Ce qui est faux **dans le monde** (une densité, une frontière) se déclare dans cette section ; il ne se corrige pas ici. Ce qui est faux **dans l'image** (étiquette coupée, couleur confondue, fiche tronquée à 900 px) se corrige avant de rendre le lot.

## Périmètre
jeu/vues/relief/carte1400.py
jeu/vues/relief/lectures.py
jeu/vues/relief/tests/test_carte1400.py
jeu/forge/__main__.py
jeu/forge/tests/test_forge.py
docs/NOTICE.md
docs/briefs/213-la-carte-de-1400.md

## Conditions de succès
Toutes les commandes se lancent depuis `jeu/`, sauf mention contraire. Les tests partent d'une vraie photographie : `build_snapshot_document(World.charger(0), 0, 0)`, et pour la terre choisie, le même monde après `deposer_intention` (Duché de Bar, trouvé par `nom` dans `charger_seigneuries()`) et un `tick`. Les deux sont construites une seule fois par module (fixture `scope="module"`), et chaque contre-épreuve travaille sur une `copy.deepcopy`. Aucun nom de ville, de puissance ni aucun `id` n'est écrit en dur : tout se dérive du document. Chaque test imprime ses compteurs, et un échantillon vide échoue. Chaque contre-épreuve est prouvée rouge avant d'être gardée.

**SC1 — la densité est lue, pas calculée.** Commande : `python3 -m pytest vues/relief/tests/test_carte1400.py -q -s -k densite`.
- Pour chaque cellule, `LECTURES["densite"].valeur(cellule) == cellule["densite_hab_par_km2"]`. Une cellule privée de cette clé rend `None`, même si elle a `population` et `area_km2`.
- Une copie du document où chaque `population` est doublée (densités intactes) rend une image **identique** (`np.array_equal`).
- Contre-épreuve : une copie où la `densite_hab_par_km2` d'une seule cellule devient dix fois le maximum rend une image différente.
- Depuis la racine, `grep -cE '"(population|area_km2)"' jeu/vues/relief/carte1400.py` rend 0, et `grep -c '"area_km2"' jeu/vues/relief/lectures.py` rend 0. Sur la base, le second rend 1.

**SC2 — les frontières suivent les puissances.** Commande : `python3 -m pytest vues/relief/tests/test_carte1400.py -q -s -k frontiere`.
- Sur la photographie de graine 0 : `pixels_de_frontiere > 0`, `puissances` égal au nombre d'`id` distincts du document, et `cellules_sans_puissance` égal au nombre de cellules à `puissance: null` (> 0).
- Contre-épreuves :
  - une copie où toutes les cellules prennent la même puissance rend `pixels_de_frontiere == 0` ;
  - une copie où une cellule couverte prend la puissance d'une cellule voisine différente (voisine : qui partage un pixel de frontière avec elle, dérivé de l'index) rend un autre nombre de pixels de frontière.

**SC3 — chaque ville documentée a son point.** Commande : `python3 -m pytest vues/relief/tests/test_carte1400.py -q -s -k villes`.
- `villes_dessinees` vaut la somme des longueurs des listes `villes` (> 0), `cellules_avec_villes` vaut le nombre de cellules qui en ont, et `villes_hors_carte` vaut la liste de la racine.
- `etiquettes_omises` est un entier ≥ 0, et il est imprimé.
- Contre-épreuve : une copie dont toutes les listes `villes` sont vidées rend `villes_dessinees == 0` et une image différente.

**SC4 — la fiche lit la terre choisie.** Commande : `python3 -m pytest vues/relief/tests/test_carte1400.py -q -s -k fiche`.
- Sans choix : une ligne commence par « Terre choisie : aucune », `terre_choisie` du compte rendu vaut `None`, et aucun pixel n'a la couleur du bord de la terre choisie.
- Avec Bar :
  - les lignes contiennent, passés par `_sans_accent`, le nom, le nom du suzerain, `str(habitants)` et `str(cell_id)` de `terre_choisie`, ainsi que chaque nom de `villes_hors_carte` ;
  - `terre_choisie` vaut l'`id` de Bar ;
  - les pixels de la couleur du bord sont plus de zéro et tombent tous sur la cellule `cell_id` dans l'index.
- Contre-épreuve : une copie où `terre_choisie["habitants"]` augmente d'un rend une ligne qui porte le nouveau nombre. La fiche lit, elle ne recompte pas.

**SC5 — une photographie incomplète est refusée.** Commande : `python3 -m pytest vues/relief/tests/test_carte1400.py -q -s -k refus`.
- Les cas sont paramétrés : une cellule sans `puissance`, une cellule sans `villes`, une racine sans `terre_choisie`, une racine sans `villes_hors_carte`, et un `terre_choisie["cell_id"]` absent des cellules (max + 1). Chacun lève `Carte1400Erreur` dont le message nomme la clé ou le `cell_id`.
- Contre-épreuve : le document intact passe.

**SC6 — la commande rend la carte de 1400.** Commande : `python3 -m pytest forge/tests/test_forge.py -q -s`.
- Un test ajouté joue `--depart <id de Bar>` puis sans `--depart`, au même horizon court que le fichier. Il vérifie que `carte.png` existe, que `resume.json["carte"]["lecture"] == "densite"`, et que `["terre_choisie"]` vaut l'`id` de Bar avec le choix et `None` sans.
- Avec `--lecture faim`, `resume.json["carte"]["lecture"] == "faim"`.
- Contre-épreuve dans le même test : un `monkeypatch` de `vues.relief.carte1400.carte_de_1400` qui lève `Carte1400Erreur` rend le code 2.
- Tous les tests existants du fichier restent verts sans modification.

**SC7 — la capture est regardée.** Commande, depuis la racine : `grep -c "^## Ce que la capture montre" docs/briefs/213-la-carte-de-1400.md` rend 1, et la section nomme au moins Paris, Le Caire, la Flandre et le Duché de Bar.
- Contre-épreuve : sur ce brief tel qu'écrit par le chef, la commande rend 0.
- Le relecteur ouvre lui aussi `carte.png` (commande du journal) avant de rendre son avis.

**SC8 — rien d'autre ne bouge.** Commande, depuis la racine : `python3 -m pytest jeu -q`. Elle reste verte, en particulier `vues/relief/tests`, `vues/tableau/tests` et `sim/tests/test_no_hardcoded.py`.
- `git diff origin/master -- jeu/vues/relief/tests jeu/forge/tests jeu/sim/tests | grep -E '^-[^-]'` ne rend rien : les tests existants ne reçoivent que des ajouts.
- `git diff --stat origin/master -- jeu/sim` est vide.

## Hors périmètre
- La preuve du jalon 2 : la table de référence (Flandre, Île-de-France, Italie du Nord et delta du Nil plus denses que la médiane, désert plus vide ; Paris, Londres, Venise, Constantinople et Le Caire à la bonne puissance) et sa contre-épreuve.
- `atelier/captures.py` : la capture du journal est prise sans `--depart`, donc sa fiche dit « aucune ». La faire passer avec un choix est un geste du mode direct, réservé au propriétaire.
- Toute donnée nouvelle dans la photographie (position exacte des villes, raison d'une cellule non couverte, suzeraineté, frontières réelles), `sim/` entier, `MODELE.md` et les tables de `data/`.
- Choisir sa terre en cliquant sur la carte, la carte dans Unity, le service (`/monde`, `/lieu`), le tableau (`vues/tableau`), la chronique (`vues/chronique`) et le rendu 3D de `vues/relief`.
- Les maisons sur la carte (couleur ou nom par maison) : la carte montre les puissances.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`, et tout test existant.
