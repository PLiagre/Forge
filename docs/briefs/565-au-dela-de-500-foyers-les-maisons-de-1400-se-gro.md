# Lot #565 — Au-delà de 500 foyers, les maisons de 1400 se groupent en îlots
Jalon : J4 · Machine : vps · Taille prévue : 220 lignes

## But
Au-delà de 500 foyers du bourg à l'amorçage, la ville de 1400 de `sim/ville1400.py` groupe ses maisons en îlots d'au plus 20 foyers, avec le même compte exact de foyers ; à 500 foyers ou moins, la base reste la même à l'octet.

## Le joueur
Sa capitale, même grande comme Paris (7 866 foyers), tiendra en quelques centaines d'objets (au plus 395 pour Paris) que Unity pourra dessiner quand il y entrera, au lieu de milliers de maisons isolées ; une petite ville, elle, garde ses maisons une à une. C'est un lot de fond : il prépare le geste du jalon J4 « le joueur entre dans sa capitale en 3D — la ville de 1400 que tient le monde, pas un décor ». Le sous-lot 3 de la découpe de #411 servira cette base par `/plan`, puis #412 la dessinera dans Unity : c'est là que le joueur la verra. Il allège aussi #422 (60 images par seconde) : environ 56 000 objets pour les 596 villes au lieu de 559 558 maisons.

## Règle du monde
Section **« ## Le plan du bourg »**, sous-partie **« ### Le plan de base »** de `jeu/sim/MODELE.md` (écrite par #564). Règle de **niveau 2**, plausible, jamais sourcée. Le propriétaire a répondu **A** à la question du 11/10 : on réécrit le contrôle de #564 qui veut une maison par foyer partout, et la phrase « Chaque foyer a une maison » du modèle.

**Le seuil.** Soit `n = ranger_en_foyers(population).nombre`. Si `n <= FOYERS_SANS_ILOTS` (500), rien ne change : une maison par foyer, comme #564, à l'octet. Si `n > FOYERS_SANS_ILOTS`, les foyers se groupent en îlots.

**Les îlots.** `n // MAISONS_PAR_ILOT_MAX` îlots pleins de `MAISONS_PAR_ILOT_MAX` (20) maisons, puis, si `n % MAISONS_PAR_ILOT_MAX > 0`, un dernier îlot de ce reste. Un îlot de `k` maisons est un rectangle :
- façade le long de la voie : `FACADE_MAISON_1400_M × min(k, MAISONS_EN_FACADE_ILOT)`, avec `MAISONS_EN_FACADE_ILOT = 5` (nouvelle constante nommée) ;
- profondeur : `k × SURFACE_M2_PAR_FOYER_LOGE / façade` ; l'aire vaut donc `k × SURFACE_M2_PAR_FOYER_LOGE`.

Îlot de 20 : 25 m × 32 m. Îlot de 1 : la maison de #564, 5 m × 8 m. Raison du 5 à écrire dans MODELE.md : une façade de 20 × 5 = 100 m ne tient nulle part (37 m entre deux ruelles le long d'une rue, 60 m le long d'une ruelle), et la boucle d'allongement ne finirait jamais.

**La pose.** Comme une maison : même recul `RECUL_MAISON_1400_M`, des deux côtés de chaque voie, candidats triés par distance à l'origine puis rue puis rang, posés du centre vers l'extérieur, en sautant ceux qui chevauchent la place, une voie ou un objet déjà posé (même grille, même `_recouvrent`). Les îlots pleins se posent d'abord, sur les candidats de leur forme ; l'îlot du reste se pose ensuite, sur les candidats de sa forme à lui. S'il manque des emplacements, les rues s'allongent et tout recommence, comme dans #564 ; l'allongement compte des objets, pas des foyers, et doit finir. Le résultat garde la forme de #564 : chaque îlot est un élément de la liste `maisons`, `{"emprise": 4 points, "foyers": k}`. Aucun champ nouveau, aucune clé renommée : sous le seuil, le JSON est identique.

Au-dessus du seuil, une cellule porte exactement `ceil(n / MAISONS_PAR_ILOT_MAX)` objets (la preuve borne à `+ 1`).

**Constantes** (bloc « Plan du bourg » de `jeu/sim/constants.py`, chacune avec son commentaire de niveau 2, relues à chaque appel par `_constantes.X`) : `FOYERS_SANS_ILOTS = 500`, `MAISONS_PAR_ILOT_MAX = 20`, `MAISONS_EN_FACADE_ILOT = 5`. `test_no_hardcoded` refuse tout autre littéral que 0, 1, −1 dans une fonction. `test_write_coverage` veut chaque constante déclarée et lue.

**Mesures du chef** (graine 0, prototype ; à re-mesurer, jamais recopiées dans un test, sauf l'empreinte de SC3) : 394 cellules sur 596 dépassent 500 foyers, 202 restent dessous, la plus petite au-dessus en a 507, aucune n'en a 500 ou 501 ; 559 558 foyers ; 56 157 objets avec îlots ; 596 bases en 4,2 s avec îlots contre 26,0 s écrites par #564 (32,9 s sur le prototype sans îlots) ; Paris 0,04 s contre 0,40 s, rayon 737 m ; 96 364 paires éprouvées sans chevauchement ; 501 foyers → 26 objets ; 500 foyers → 500 maisons. Avec 7 en façade : 8,1 s et Paris à 1 205 m (raison de garder 5).

**À écrire dans « ### Le plan de base »** : la phrase « Chaque foyer a une maison » devient « Jusqu'à `FOYERS_SANS_ILOTS` foyers, chaque foyer a une maison » ; un paragraphe sur les îlots (`MAISONS_PAR_ILOT_MAX`, `MAISONS_EN_FACADE_ILOT` et sa raison, pose des îlots pleins puis du reste, champ `foyers`) ; la ligne du temps de #564 remplacée par les temps mesurés **avant et après** ce lot, sur la même machine (596 bases et Paris), en gardant les mots « 596 » et « Paris » suivis d'un temps en s, que lit SC10 de #564. Restent de **niveau 3**, à ajouter à la liste : la forme d'un îlot (cour, maisons mitoyennes, passages), et des îlots dans une ville de 500 foyers ou moins.

## Périmètre
jeu/sim/ville1400.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_ville1400.py

## Conditions de succès
Toutes dans `jeu/sim/tests/test_ville1400.py`, lancées par `cd jeu && python3 -m pytest sim/tests/test_ville1400.py -q`, en réutilisant la fixture `campagne` (graine 0, une fois par module, un an joué). Chaque compteur est dérivé des données et affiché (`print`), jamais écrit en dur, sauf l'empreinte figée de SC3.

**Seule réécriture permise d'un test existant** (réponse A du propriétaire) : l'aide `_controler_foyers` de SC2 de #564 (et, si besoin, le nom et le message de `test_sc2_une_maison_par_foyer`). Tout le reste du fichier — SC1, SC3 à SC10 de #564, leurs aides et leurs contre-épreuves — reste tel quel, et aucun autre fichier de test n'est touché.

- **SC1 — Le compte reste juste (SC2 de #564 réécrit).** `_controler_foyers(bases, populations)` lève une `AssertionError` au message distinct pour chaque faute : pour chaque base, la somme des `foyers` égale `ranger_en_foyers(population à l'amorçage).nombre` ; si ce nombre est `<= FOYERS_SANS_ILOTS`, chaque objet porte `foyers == 1` et une aire de `SURFACE_M2_PAR_FOYER_LOGE`, à la tolérance d'arrondi de #564 près (contrôle inchangé) ; au-dessus, chaque objet porte `1 <= foyers <= MAISONS_PAR_ILOT_MAX`, une aire de `foyers × SURFACE_M2_PAR_FOYER_LOGE` à une tolérance d'arrondi dérivée de ses côtés (périmètre × 10^−`SNAPSHOT_FLOAT_DECIMALS`), et le nombre d'objets est au plus `ceil(n / MAISONS_PAR_ILOT_MAX) + 1`. Sur les 596 bases : total des foyers, nombre d'objets, nombre de cellules au-dessus du seuil (> 0) et objets de Paris affichés. Contre-épreuves, chacune avec `pytest.raises(AssertionError, match=…)` sur son message : une copie de la base de Paris dont un îlot passe à 21 foyers et un autre perd 1 foyer (somme intacte, aires ajustées) échoue sur la borne ; une copie de Paris où un îlot de 20 est remplacé par 20 objets d'un foyer (somme intacte) échoue sur le nombre d'objets ; une base sous le seuil où deux maisons fusionnent en un objet de 2 foyers échoue ; un objet retiré à Paris échoue sur la somme (celle de #564) ; une liste vide échoue (« échantillon vide »).
- **SC2 — Le seuil, au foyer près.** Avec `base_d_une_population`, une direction puis sept : `FOYERS_SANS_ILOTS × TAILLE_FOYER` personnes donnent `FOYERS_SANS_ILOTS` objets, tous `foyers == 1` ; `(FOYERS_SANS_ILOTS + 1) × TAILLE_FOYER` donnent `ceil((FOYERS_SANS_ILOTS + 1) / MAISONS_PAR_ILOT_MAX)` objets (26), dont des îlots de `MAISONS_PAR_ILOT_MAX`. Contre-épreuve : avec `monkeypatch` de `FOYERS_SANS_ILOTS` à 501, les mêmes 501 foyers redonnent 501 maisons d'un foyer ; avec `MAISONS_PAR_ILOT_MAX` à 10, plus aucun objet ne dépasse 10 foyers ; avec `MAISONS_EN_FACADE_ILOT` à 7, l'emprise d'un îlot plein de Paris change et son aire reste `MAISONS_PAR_ILOT_MAX × SURFACE_M2_PAR_FOYER_LOGE`. Valeurs remises, la base revient à l'octet.
- **SC3 — Sous le seuil, rien n'a bougé d'un octet.** Pour les cellules de la graine 0 dont le bourg a `<= FOYERS_SANS_ILOTS` foyers à l'amorçage, triées par `cell_id`, le SHA-256 de `"\n".join(json.dumps(base_de_cellule(monde, cid), sort_keys=True))` vaut **`7f9be1e18e336199993e260423bfe32e5d211b7f6d1c2211d72905506d517004`**, mesuré par le chef sur 661d13e (avant ce lot) : 202 cellules, 0,9 s. Le codeur le re-mesure sur la base avant de toucher le code, et le dit dans la PR s'il diffère. Le nombre de cellules est dérivé, affiché et > 0. Contre-épreuve : avec `FOYERS_SANS_ILOTS` à 0 (`monkeypatch`), la même empreinte sur les mêmes cellules diffère.
- **SC4 — Même base au tick 0 et après un an, sans chevauchement.** SC1 (octets égaux au tick 0 et après 365 ticks, deux chargements égaux) et SC3 (aucun chevauchement, contrôlé avec une grille) de #564 passent **sans être modifiés** sur les bases avec îlots ; le nombre de paires éprouvées est affiché et > 0. Contre-épreuve nouvelle : deux îlots pleins de Paris, le second décalé d'une demi-façade d'îlot sur le premier, font échouer `_controler_chevauchements`.
- **SC5 — La vue tient sa promesse de taille et de temps.** Pour chaque cellule au-dessus du seuil, le nombre d'objets est au plus `ceil(n / MAISONS_PAR_ILOT_MAX) + 1` (contrôlé dans SC1) ; une population synthétique de 7 866 foyers avec une seule direction rend une base (l'allongement finit). Le temps des 596 bases et de Paris, avant (sur la base) et après, s'écrit dans MODELE.md (lu par SC6) ; aucun seuil de temps dans un test.
- **SC6 — Le modèle le dit.** Un test lit « ### Le plan de base » par l'aide `_sous_partie` de #564 et y trouve `FOYERS_SANS_ILOTS`, `MAISONS_PAR_ILOT_MAX`, `MAISONS_EN_FACADE_ILOT` et « îlot » ; la phrase « Chaque foyer a une maison » n'y figure plus seule (elle est précédée de « Jusqu'à »). SC10 de #564 passe inchangé (temps des 596 bases et de Paris). `jeu/sim/README.md` dit que la ligne de `sim/ville1400.py` parle d'îlots. Contre-épreuve : la lecture d'un texte sans la sous-partie échoue (« échantillon vide »).
- **SC7 — Rien d'autre ne bouge.** `cd jeu && python3 -m pytest sim -q` passe en entier, sans autre test modifié que `_controler_foyers` : en particulier `test_determinisme.py`, `test_no_hardcoded.py`, `test_write_coverage.py` (les trois constantes déclarées et lues) et SC7 de #564 (seul `ville1400.py` importe `sim.ville1400`). Contre-épreuve : celles de SC1 à SC6.

## Hors périmètre
- Servir la base (`/plan`, `EtatPublie`, le snapshot, la photographie), refuser au dépôt un geste posé sur un îlot, faire éviter les îlots à l'IA : sous-lot 3 de #411. Dessiner les îlots dans Unity : #412.
- Mettre la base dans `World.plans`, le tick, le logement ou l'empreinte du monde : les maisons et îlots de 1400 ne logent personne dans ce lot.
- Changer la place, les rues, les ruelles, la façade, le recul ou toute constante de #564 ; grouper sous 500 foyers.
- La forme intérieure d'un îlot (cour, mitoyenneté, passages), des îlots de tailles variées, des quartiers.
- Toucher `jeu/sim/world.py`, `jeu/sim/plan.py`, `jeu/sim/foyers.py`, `jeu/sim/tests/README.md` ou tout autre test que `test_ville1400.py`.
