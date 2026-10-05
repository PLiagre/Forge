# Lot #333 — Chaque lieu produit selon sa surface et mange selon ses habitants
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Chaque lieu d'une cellule reçoit sa part de la récolte selon sa surface et mange dans son propre panier. Seuls les chemins intérieurs portent la nourriture d'un lieu à l'autre. Sans chemin, le bourg d'une cellule minière a faim pendant que ses champs débordent : c'est la preuve du jalon J3, « la distribution à l'intérieur de la cellule cesse d'être gratuite ».

## Règle du monde
Elle découle de `jeu/sim/MODELE.md`, section « La distribution à l'intérieur de la cellule », que ce lot réécrit. Elle s'appuie aussi sur « Les lieux d'une cellule, vue dérivée » (`partager`, `repartir_sur_les_lieux`) et sur « Le déficit alimentaire et la mortalité ». Ce lot est le sous-lot 3 sur 5 du lot #236. Le propriétaire y a répondu **A** : la question n'est pas reposée. Cette réponse accepte en particulier la réécriture de `test_cellule_independante_du_contenu_des_lieux`, qui dit désormais l'inverse.

**Champ d'application.** La règle s'applique à une cellule **avec carte et avec lieux**, c'est-à-dire toute cellule de `World.charger`. Trois cas gardent le calcul d'aujourd'hui, au bit près :
- une cellule sans lieux (`Cell` construite à la main, `lieux == []`), y compris la règle de la part minière avec carte ;
- un monde sans carte ;
- une cellule à un seul lieu. Pour elle, aucune capacité n'est calculée.

**1. Production.** La récolte de la cellule (`food_produced`) se calcule exactement comme aujourd'hui et s'ajoute au panier de la cellule comme aujourd'hui. On l'ajoute aussi aux lieux : le lieu de surface `s_r` reçoit `récolte × s_r / A`. La règle vaut pour les deux chemins de production, `_apply_production` et `_apply_production_saison_moyenne`.

**2. Ce qui arrive à la cellule hors des lieux** (commerce, intentions, chantiers, écritures à la main) se répartit **encore à proportion**. Au début de la consommation, la nourriture des lieux est remise d'accord avec le panier de la cellule, par la règle de `repartir_sur_les_lieux` : le poids de chaque lieu est son contenu actuel, et ce sont les surfaces si tous les lieux sont vides. Ce que le commerce apporte ou retire suit donc le contenu de chaque lieu. Les habitants suivent la même règle si leur somme diffère de la population.

**3. Chaque lieu mange dans son panier.** Pour le lieu `r`, on note :
- `x_r` sa nourriture (la sentinelle −1 se lit 0) ;
- `b_r = population_r × FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK` son besoin.

Il mange `m_r = min(b_r, x_r)`. Il lui reste `s_r = x_r − m_r` et il lui manque `d_r = b_r − m_r`. Le tick lit les habitants des lieux, jamais les métiers. La phrase « Le tick ne lit les métiers que pour la récolte » reste vraie.

**4. Les chemins intérieurs, en étoile autour du bourg.** Chaque lieu `r > 0` a un chemin vers le bourg (rang 0). Ce chemin porte au plus `c = capacite_chemins_interieurs_kg(1, facteur de relief)` par tick, dans un sens. La capacité totale reste celle d'aujourd'hui, `(n − 1) × c`. Tout échange passe par le bourg :
- **Ce qu'on demande au bourg** : `d_0 + Σ_{r>0} min(d_r, c)`.
- **Ce qui remplit le pot** : le bourg met d'abord son propre reste `s_0`. Ensuite, les champs en surplus envoient, **par rang croissant**, chacun au plus `min(s_r, c)`, jusqu'à couvrir la demande.
- **Qui est servi** : le bourg d'abord, à hauteur de `d_0`. Ensuite, les champs qui manquent, par rang croissant, chacun au plus `min(d_r, c)`.
- **Ce qui reste du pot** reste au bourg.

On obtient ainsi un reste final `f_r` et un manque final `d'_r` pour chaque lieu.

**5. Distribution limitée.** C'est le cas où un lieu manque encore (`Σ d'_r > 0`) pendant qu'un autre garde de la nourriture (`Σ f_r > 0`). Alors :
- **La pénurie du tick** est `Σ d'_r`, la somme des manques des lieux. La faim, la mortalité, la natalité et la migration la lisent, comme aujourd'hui.
- **La dette** (`food_deficit_kg`) augmente de cette somme, sans rembourser la dette ancienne.
- **Le panier** de la cellule devient `Σ f_r`.
- **Le panier des lieux** sort de `partager(ce total, f)` : sa somme retrouve celle de la cellule au bit près, en `Fraction` aussi.

**6. Sinon, le calcul d'aujourd'hui.** Si personne ne manque, ou s'il ne reste rien nulle part, on applique le calcul de cellule d'aujourd'hui, inchangé au bit près, remboursement physique de la dette compris. Le panier des lieux sort ensuite de `partager(nouveau panier, f)`, ou des surfaces si tous les `f_r` sont nuls.

**Conséquences.**
- **Chemins illimités.** Avec `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = inf`, tout ce qui est demandé arrive. Le cas 5 ne se produit jamais, et le monde est identique au bit près au calcul gratuit (`test_identique_quand_chemins_suffisent`, inchangé).
- **Aucun kilo n'est créé.** Le panier ne devient jamais négatif. Ce qui est mangé ne dépasse pas le besoin du tick.

**La dette d'un lieu.** Le manque d'un lieu devient sa part de la dette du tick : la dette et la pénurie de la cellule sont la somme de celles de ses lieux. La dette reste **portée par la cellule**, comme les compteurs de faim, parce qu'`EtatDeLieu` garde exactement `rang`, `population` et `stocks`, champs que des tests figent. Une dette ou une faim propre à chaque lieu relève du sous-lot 4.

**La part minière.** Elle ne sert plus à la consommation des cellules qui ont des lieux : le bourg est désormais compté par `lieux[0].population`, qui loge les non-paysans depuis #332. Elle garde son rôle pour les cellules sans lieux. Le mot « écart », qui distingue la part minière de la vue du bourg, reste dans la section, car `test_bourg_documente` l'exige.

**Niveau de vraisemblance.** Le partage de la récolte par surface, l'étoile des chemins et l'ordre de service par rang sont de **niveau 2** : plausibles, jamais sourcés. Le délai, les pertes en route, les bras des porteurs et le tracé des chemins restent de **niveau 3**, non simulés.

**Déjà mesuré par les deux passages précédents** (graine 0, VPS, le 05/10/2026, prototype hors dépôt). Il n'y a pas à le refaire :
- avec des chemins illimités, le monde est identique au bit près ;
- sans chemin, les **25** bourgs miniers (25 cellules minières, toutes à plusieurs lieux) ont faim en 60 ticks ; avec des chemins illimités, **aucun** n'a faim ;
- le prototype naïf portait le tick à 118,7 ms. Optimisé, il ne coûte qu'environ +13 ms (77 ms contre 65 ms). Les leviers : ne rien calculer pour une cellule à un seul lieu, sortir tout de suite quand aucun lieu ne manque, lire les surfaces sans construire d'objets `Lieu` (par exemple une fonction `surfaces_des_lieux` dans `lieux.py`, que `lieux_de_cellule` réutilise), et n'appeler `partager` que quand les sommes diffèrent.

**Rouges déjà connus sur ce prototype**, à tenir par le code, jamais en touchant le test :
- `test_tick_repartit_sur_une_annee_et_suit_les_ecritures` : le prototype cassait la somme exacte des paniers par des arrondis (cellule 10212, nourriture). D'où la règle « les paniers des lieux sortent toujours de `partager` ».
- `test_tick_sous_le_budget_du_service`.
- Les deux réponses `/lieu` figées que lit Unity, à régénérer comme #332 l'a fait.

**Piège.** `test_acces_directs_au_panier_hors_modele` interdit tout `.stocks` hors de `model.py`. Pour lire et écrire les lieux, passez par `lire_stock_marchandise`, `ecrire_stock_marchandise`, `contenus_des_paniers` et `remplacer_panier`.

## Périmètre
jeu/sim/engine.py
jeu/sim/lieux.py
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_distribution_interieure.py
jeu/sim/MODELE.md
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs

## Conditions de succès
Ne jouez jamais `pytest jeu` ni `pytest sim` en entier : la suite prend 42 min sur le VPS. Ne jouez que les fichiers et les `-k` nommés ci-dessous, depuis `jeu/`.

- **SC1 — chaque lieu mange dans son panier, les chemins limitent.**
  - **Commande** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -s -k par_lieu` (tests neufs).
  - **Cellule d'épreuve** : une cellule construite à la main, avec 3 lieux ou plus (`creer_etat_de_lieu`), une carte de plaine, et habitants et nourriture posés lieu par lieu. Trois cas, chacun vérifié à `math.isclose(rel_tol=1e-12)` :
    - (a) **capacité 0, bourg sans nourriture, champs en surplus** : la pénurie rendue vaut le besoin du bourg, la dette augmente d'autant, `_update_hunger` met `hunger_ticks` à 1, et chaque champ garde exactement `x_r − b_r` ;
    - (b) **capacité `c` finie, inférieure au manque du bourg** : le bourg reçoit exactement `min(d_0, Σ min(s_r, c))` ; les champs donnent par rang croissant ; en montagne, il reçoit moins qu'en plaine (`FACTEUR_TRANSPORT_MONTAGNE`) ;
    - (c) **un champ qui manque, un bourg en surplus, capacité `c`** : le champ reçoit au plus `c`, et le reste demeure au bourg.
  - **Dans chaque cas** : la somme des lieux égale le panier de la cellule, en `==` et en `Fraction` ; aucun panier n'est négatif ; ce qui est mangé ne dépasse pas le besoin.
  - **Contre-épreuve** : la même vérification, sur le résultat du calcul gratuit (`engine._apply_consumption(cellule)` sans carte), lève `AssertionError` dans le cas (a).

- **SC2 — le commerce se répartit à proportion.**
  - **Commande** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -s -k proportion` (test neuf).
  - **Cellule d'épreuve** : 3 lieux ou plus, nourriture `x_r` **non proportionnelle aux surfaces**, personne ne manque, capacité 0. Le panier de la cellule est posé à `2 × Σ x_r` (le commerce apporte), puis à `0,5 × Σ x_r` (le commerce retire, avec des habitants choisis pour que personne ne manque).
  - **Attendu** : après `_apply_consumption(cellule, carte)`, chaque lieu a `k × x_r − b_r` (`isclose`), et la somme est exacte.
  - **Contre-épreuve** : `sim.lieux.partager`, remplacé par une version qui pèse par les surfaces, fait lever `AssertionError` à la même vérification.

- **SC3 — dans le vrai monde, le bourg sans chemin a faim.**
  - **Commande** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -s -k bourg_miniers_ont_faim` (test neuf).
  - **Mesure** : `World.charger(0)`, 60 ticks (`random.Random(0)`, `numero_tick=i`), avec `_apply_consumption` enveloppé. On compte les cellules minières (`part_miniere_de > 0`) qui ont eu au moins un tick où la pénurie rendue est > 0 **et** le panier de la cellule reste > 0 après consommation.
  - **Attendu** : avec `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = 0`, ce compte est > 0 (25 attendu, imprimé) ; avec `inf`, il vaut **0** sur toutes les cellules.
  - **Contre-épreuve** : `_apply_consumption` remplacé par le calcul gratuit (`lambda cellule, carte=None: original(cellule)`) donne 0 sans chemin, et l'assertion « > 0 » lève `AssertionError`.
  - **Restent verts sans retouche** : `test_monde_ressent_la_distribution`, `test_identique_quand_chemins_suffisent`, et tous les autres tests du fichier, qui jouent des `Cell` sans lieux.

- **SC4 — le test réécrit dit l'inverse, comme le propriétaire l'a accepté.**
  - **Commande** : `python3 -m pytest sim/tests/test_lieux.py -q -s -k depend_du_contenu`.
  - **Le test** : `test_cellule_independante_du_contenu_des_lieux` est remplacé par `test_cellule_depend_du_contenu_des_lieux`, et l'ancien nom disparaît.
    - (a) Avec `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = inf`, ses anciennes assertions restent mot pour mot. Le monde avec lieux et le monde à `lieux = []` ont des `_etats_cellules` égaux à chacun de 30 ticks. Déplacer un habitant du rang 0 au rang 1 ne change rien en 10 ticks.
    - (b) Sans chemin (capacité 0), dans une cellule minière à plusieurs lieux, déplacer ses non-paysans du bourg au rang 1 (la conservation tient) rend `_etats_cellules` différents en 10 ticks au plus. L'écart est imprimé.
  - **Contre-épreuve** : avec `_apply_consumption` remplacé par le calcul gratuit, la partie (b) lève `AssertionError`.

- **SC5 — les sommes exactes tiennent sur une année.**
  - **Commande** : `python3 -m pytest sim/tests/test_lieux.py sim/tests/test_determinisme.py -q` passe en entier.
  - **Sans modification**, en particulier : `test_tick_repartit_sur_une_annee_et_suit_les_ecritures` (somme des paniers des lieux égale à la cellule en `==` et en `Fraction`, à chaque tick d'une année, cellule 10212 comprise), `test_photographie_et_empreinte_portent_les_lieux`, `test_tick_bit_pres_sur_une_annee`, `test_metiers_lus_a_l_amorcage` et `test_amorcage_conserve_habitants_et_panier`.

- **SC6 — le tick tient son budget.**
  - **Commande** : `python3 -m pytest sim/tests/test_monde.py -q -s -k "budget or part_miniere"` passe sans retouche.
  - **Attendu** : `test_tick_sous_le_budget_du_service` donne une médiane < `BUDGET_TICK_MS` (100 ms), dont la valeur imprimée est recopiée dans la PR ; la cible mesurée est d'environ 77 ms. `test_une_seule_definition_part_miniere` passe aussi.

- **SC7 — les réponses figées que lit Unity sont régénérées depuis le service.**
  - **Régénération** : `lieu-graine0-tick3.json` et `lieu-graine0-tick4.json` sont réécrits avec les octets exacts de `GET /lieu?cell=9922`, après `POST /tick?n=3`, puis `?n=4`, sur un service graine 0.
  - **Commande** : `python3 -m pytest sim/tests/test_monde.py -q -k "pont"` passe, sans retouche de ces tests ni de leurs contre-épreuves.
  - **Côté Unity** : dans `LecteurJsonTests.cs`, seules les valeurs littérales que le nouveau fichier change sont mises à jour (population, stocks, population du bourg). Aucune assertion n'est retirée ni affaiblie : `git diff master -- …/LecteurJsonTests.cs` ne montre que des nombres changés.

- **SC8 — MODELE.md dit la règle.**
  - **Commande** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k documentee` (test neuf).
  - **La section** « La distribution à l'intérieur de la cellule », jusqu'au `## ` suivant, contient `partager`, « surface », « chemin », `capacite_chemins_interieurs_kg`, « par rang », « dette », « somme », « commerce », « à proportion », « sans lieux », « écart » et « niveau 3 ». Elle ne contient plus « réputé réparti au prorata des surfaces », ni « consommation du stock persisté de chaque lieu ».
  - **Le reste du fichier** ne contient plus « sans lire les habitants et paniers persistés », ni « un seul panier reste partagé dans la cellule ».
  - **Contre-épreuve** : le même texte, où « à proportion » est remplacé par « au hasard » dans la section, lève `AssertionError`.
  - **Gardes existantes, vertes sans retouche** :
    - `python3 -m pytest sim/tests/test_province.py -q -k bourg_documente` ;
    - `python3 -m pytest sim/tests/test_foyers.py -q -k "documentation or gardes"` ;
    - `python3 -m pytest sim/tests/test_monde.py -q -k lieux_documentes` ;
    - `python3 -m pytest sim/tests/test_lieux.py -q -k amorcage_documente`.

- **SC9 — aucun test ne s'assouplit, rien d'autre ne bouge.**
  - **Périmètre** : `git diff --stat master` ne montre que les fichiers du Périmètre.
  - **`test_lieux.py`** : `git diff master -- jeu/sim/tests/test_lieux.py` ne remplace que `test_cellule_independante_du_contenu_des_lieux`, comme dit en SC4.
  - **`test_distribution_interieure.py`** : `git diff master -- jeu/sim/tests/test_distribution_interieure.py` ne contient que des ajouts.
  - **Tests à rejouer**, sans retouche : `python3 -m pytest sim/tests/test_write_coverage.py sim/tests/test_survie.py sim/tests/test_commerce.py sim/tests/test_foyers.py sim/tests/test_chantiers.py -q`. Ils lisent la consommation, la faim et le panier.

## Hors périmètre
- Une dette, une faim, des morts ou des naissances propres à chaque lieu, et tout nouveau champ d'`EtatDeLieu` : c'est le sous-lot 4 du lot #236.
- Le commerce et la migration par le bourg, et la fin de la répartition proportionnelle : c'est le sous-lot 5.
- Le délai, les pertes en route, les bras des porteurs, le tracé ou la construction des chemins intérieurs, et un chemin direct entre deux champs.
- Les habitants des villes nommées logés au bourg ; tout changement de l'amorçage (#332) ou de la récolte de la cellule.
- Le service et la photographie, hors des deux réponses figées régénérées ; Unity, hors des valeurs littérales de `LecteurJsonTests.cs` ; le PC.

DECISION: BRIEF
