# Lot #342 — Chaque lieu porte sa dette et sa faim
Jalon : J3 · Machine : vps · Taille prévue : 240 lignes

## But
Chaque lieu d'une cellule garde sa propre dette alimentaire et sa propre durée de faim. Le monde sait alors quel lieu a faim : le bourg sans chemin, et non ses champs pleins. Les morts et les naissances ne changent pas encore : le monde reste identique au bit près.

## Règle du monde
Elle découle de `jeu/sim/MODELE.md`, sections « La distribution à l'intérieur de la cellule » (l'étoile de #333, qui donne le manque final de chaque lieu) et « Les lieux d'une cellule, vue dérivée », sous-section « Ce que porte un lieu » (`partager`). Elle s'appuie aussi sur « Le déficit alimentaire et la mortalité » et « Ce que veut dire « affamée » », qui restent vraies pour la cellule.

Ce lot est le premier des deux sous-lots du lot #334, lui-même sous-lot 4 du lot #236. Le propriétaire a répondu **A** sur #334 : chaque lieu porte sa dette et sa faim, et le test qui fige la liste des données d'un lieu est réécrit. La question n'est pas reposée.

**Deux données de plus sur le lieu.** `EtatDeLieu` porte désormais exactement :
- `rang`, `population`, `stocks`, comme aujourd'hui ;
- `dette_alimentaire_kg` (flottant, défaut `0.0`) ;
- `duree_faim_ticks` (entier, défaut `0`).

`creer_etat_de_lieu` accepte les deux nouvelles valeurs par mot-clé, avec ces défauts. Elle les passe par mot-clé au constructeur `EtatDeLieu(...)` : `test_write_coverage` ne voit un écrivain que là, ou sur une variable nommée `etatdelieu`. L'amorçage ne change pas : une cellule de `World.charger` part à dette 0 et à faim 0, et ses lieux aussi.

**Champ d'application.** La règle vaut pour une cellule **avec carte et avec lieux**, donc pour toute cellule de `World.charger`, qu'elle ait un lieu ou plusieurs. Une cellule sans lieux, ou un monde sans carte, ne touche pas aux lieux, comme aujourd'hui.

**Notations**, pour une cellule et un tick :
- `P` : la dette de la cellule avant consommation (la sentinelle −1 se lit 0) ;
- `L_r` : la dette du lieu `r` avant consommation ;
- `N` : la dette de la cellule après consommation, calculée exactement comme aujourd'hui ;
- `pénurie` : la valeur que `_apply_consumption` rend, inchangée ;
- `m_r` : le manque final du lieu `r` après l'étoile (le `d'_r` de #333).

**1. Remise d'accord.** Si `Σ L_r ≠ P`, les dettes des lieux sont d'abord repartagées : `L = partager_si_necessaire(cellule, P, L)`. Les poids sont les dettes actuelles, ou les surfaces si toutes sont nulles. C'est le cas d'une dette écrite à la main sur la cellule.

**2. Le manque de chaque lieu.** Il ne compte que si la cellule a manqué :
- si `pénurie == 0`, tous les `m_r` valent 0 ;
- si `pénurie > 0` et qu'au moins un `m_r` est positif, on garde les `m_r` de l'étoile ;
- si `pénurie > 0` mais que tous les `m_r` sont nuls (écart d'arrondi entre la somme des lieux et le calcul de cellule), tout le manque va au bourg : `m = [pénurie, 0, …]`.

Pour une cellule à un seul lieu, `m = [pénurie]`.

**3. La dette de chaque lieu.**
- Si `N == 0` : chaque lieu a une dette de 0, sans appeler `partager`.
- Sinon, si `pénurie > 0` : dettes = `partager(N, [L_r + m_r])`. Chaque lieu reçoit sa dette ancienne plus son manque, et la somme égale `N` au bit près.
- Sinon (remboursement ou dette inchangée) : dettes = `partager(N, L)`, appelé seulement si `Σ L_r ≠ N`. Le remboursement se partage donc **à proportion des dettes** : un lieu sans dette reste à 0.
- Pour une cellule à un seul lieu, sa dette vaut `N`.

**4. La faim de chaque lieu.** `duree_faim_ticks` du lieu `r` vaut l'ancienne valeur + 1 si `m_r > 0`, et 0 sinon : la règle de `_update_hunger`, appliquée au lieu. Par construction :
- la cellule a faim ce tick si et seulement si au moins un de ses lieux a faim ;
- aucun lieu n'a une durée de faim plus longue que celle de sa cellule.

**5. Rien d'autre ne bouge.** La dette, la faim, le panier, la pénurie rendue, les morts, les naissances et la migration restent ceux de la cellule, calculés comme aujourd'hui. Les nouvelles données ne sont **lues par aucune règle** dans ce lot. Le monde reste donc identique au bit près. `test_cellule_depend_du_contenu_des_lieux` et `test_identique_quand_chemins_suffisent` passent sans retouche.

**Ce qui est publié.** L'empreinte (`cellule_vers_dict`, donc `World.to_dict`) porte les deux nouvelles clés dans chaque lieu, pour que le déterminisme les couvre. La photographie (`lieux_en_photographie`) et `/lieu` ne les publient **pas** : leurs clés restent `rang`, `surface_km2`, `population`, `stocks`. Les réponses figées `lieu-graine0-tick3.json` et `lieu-graine0-tick4.json` ne changent pas d'un octet.

**Niveau de vraisemblance.** Une dette et une faim propres à chaque lieu sont de **niveau 2** : plausibles, jamais sourcées. `partager` donne des kilos entiers aux rangs supérieurs à zéro, ce qui fait un écart de moins d'un kilo par lieu et par tick. La fraction reste au bourg.

**Où placer le code.**
- Une fonction nommée, `engine._porter_dette_et_faim_sur_les_lieux`, appelée à la fin de `_apply_consumption`, dans le chemin à un lieu comme dans le chemin à plusieurs lieux. `P` et les `L_r` sont lus **avant** que le calcul de cellule n'écrive `food_deficit_kg`.
- **Jamais** dans `repartir_sur_les_lieux`, ni dans une fonction que `_REFERENCE_TICK_331` remplace (`test_determinisme.py`). Sinon, la course de référence de `test_tick_bit_pres_sur_une_annee` n'aurait pas ces données, et les empreintes divergeraient.

**Coût mesuré** (graine 0, VPS, le 06/10/2026) :
- le monde compte 596 cellules, dont 402 à plusieurs lieux ;
- en moyenne, 112 cellules à plusieurs lieux portent une dette à chaque tick, et 19 manquent ;
- `partager` coûte environ 7 µs, soit environ 1 ms par tick ;
- `test_tick_sous_le_budget_du_service` donne aujourd'hui une médiane de 90 ms, pour un budget de 100 ms : la marge est mince.

Les leviers : ne rien faire quand `N == 0`, que toutes les dettes et faims des lieux sont à 0 et qu'aucun lieu ne manque ; n'appeler `partager` que si la somme diffère.

**Pièges.**
- `test_consommation_par_lieu_sans_repartage_inutile` interdit tout appel à `partager` quand la dette est nulle et que personne ne manque. D'où « `N == 0` → 0 sans `partager` ».
- `_cellule_par_lieu` (test_distribution_interieure.py) pose une dette de cellule de 9 avec des lieux à 0. La remise d'accord de l'étape 1 sert là.
- `test_acces_directs_au_panier_hors_modele` interdit tout `.stocks` hors de `model.py`. Ce lot ne touche pas aux paniers.
- `partager` refuse une somme de poids nulle, même pour un total nul.

## Périmètre
jeu/sim/model.py
jeu/sim/engine.py
jeu/sim/lieux.py
jeu/sim/tests/test_lieux.py
jeu/sim/tests/test_distribution_interieure.py
jeu/sim/MODELE.md

## Conditions de succès
Ne jouez jamais `pytest jeu` ni `pytest sim` en entier : la suite prend 42 min sur le VPS. Ne jouez que les fichiers et les `-k` nommés ci-dessous, depuis `jeu/`.

- **SC1 — le lieu porte exactement cinq données, et chacune a un écrivain et un lecteur.**
  - **Commandes** : `python3 -m pytest sim/tests/test_lieux.py -q -k amorcage_conserve`, puis `python3 -m pytest sim/tests/test_write_coverage.py -q`.
  - **Le test réécrit** : dans `test_amorcage_conserve_habitants_et_panier`, seule la ligne `fields(EtatDeLieu) == {"rang", "population", "stocks"}` change. Elle devient `{"rang", "population", "stocks", "dette_alimentaire_kg", "duree_faim_ticks"}`. Le reste du test est inchangé.
  - **Contre-épreuve** : `test_write_coverage` lève une erreur si on retire la seule lecture de `duree_faim_ticks` dans `engine.py`. Le test réécrit lève `AssertionError` si on retire un des deux champs d'`EtatDeLieu`.

- **SC2 — la dette et la faim de chaque lieu suivent la règle, cas par cas.**
  - **Commande** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -s -k dette_par_lieu` (tests neufs).
  - **Cellules d'épreuve** : `_cellule_par_lieu`, 3 lieux de surfaces `(1000.5, 1000, 1000)`. Dans chaque cas, on vérifie : la somme des dettes des lieux égale `food_deficit_kg`, en `==` et en `Fraction` ; aucune dette n'est négative ; les durées de faim sont exactes.
    - (a) **Manque au bourg**, capacité 0, habitants `[20, 1, 1]`, paniers `[0, 6, 200]`, dette de cellule 9 et lieux à 0. Après `_apply_consumption` : la dette de cellule vaut 49, les dettes des lieux valent `[43, 3, 3]` et les faims `[1, 0, 0]`.
    - (b) **Manque au champ**, capacité 10, habitants `[1, 20, 1]`, paniers `[200, 0, 100]`, même dette. Après : la dette de cellule vaut 39, les dettes des lieux `[3, 33, 3]` et les faims `[0, 1, 0]`.
    - (c) **Remboursement à proportion**, habitants `[1, 2, 3]`, paniers `[10, 10, 12]`, dette de cellule 40, dettes des lieux `[30, 10, 0]`, faims `[2, 0, 0]`. Après : la dette de cellule vaut 20, les dettes des lieux exactement `[15, 5, 0]` et les faims `[0, 0, 0]`.
    - (d) **Dette nulle, personne ne manque** : `partager` est remplacé par une fonction qui échoue, et les dettes des lieux restent à 0.
    - (e) **Un seul lieu** : sa dette égale celle de la cellule, et après `_update_hunger`, sa faim égale `hunger_ticks`, dans un tick avec manque et dans un tick sans manque.
  - **Contre-épreuve** : la même vérification de (a), appliquée à une copie où les dettes du bourg et du rang 1 sont échangées, lève `AssertionError`.

- **SC3 — dans le vrai monde, les lieux portent la dette de leur cellule, et le bourg sans chemin a faim seul.**
  - **Commande** : `python3 -m pytest sim/tests/test_lieux.py -q -s -k dette_et_faim_des_lieux` (test neuf).
  - **Mesure** : `World.charger(0)`, 60 ticks (`random.Random(0)`, `numero_tick=i`), une fois avec la capacité par défaut, une fois avec `CAPACITE_CHEMIN_INTERIEUR_KG_PAR_TICK = 0`. Après chaque tick, pour chaque cellule :
    - la somme des dettes des lieux égale `food_deficit_kg`, en `==` et en `Fraction` ;
    - aucune dette n'est négative ;
    - `hunger_ticks > 0` si et seulement si au moins un lieu a `duree_faim_ticks > 0` ;
    - aucun lieu n'a une durée de faim plus longue que `hunger_ticks`.
  - **Attendu avec la capacité 0** : on compte les couples (cellule, tick) où un lieu a faim pendant qu'un autre lieu de la même cellule n'a pas faim. Ce compte est > 0 et il est imprimé.
  - **Contre-épreuve** : `engine._porter_dette_et_faim_sur_les_lieux` remplacé par une fonction qui ne fait rien. La vérification de somme lève alors `AssertionError`, car des cellules portent une dette dès les premiers ticks.

- **SC4 — le monde reste identique au bit près.**
  - **Commandes** : `python3 -m pytest sim/tests/test_lieux.py -q -s -k "dette_sans_effet or depend_du_contenu"`, puis `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k "identique or bourg_miniers or ressent"`.
  - **Le test neuf** `test_dette_sans_effet_sur_le_monde` (test_lieux.py) joue deux mondes `World.charger(0)` pendant 60 ticks, avec la capacité 0 : l'un normal, l'autre avec `_porter_dette_et_faim_sur_les_lieux` remplacé par une fonction qui ne fait rien. Il compare à chaque tick :
    - `_etats_cellules` ;
    - la population et le panier de chaque lieu ;
    - la valeur que rend `tick`.

    Tout est égal.
  - **Contre-épreuve** : la même comparaison, étendue aux dettes des lieux, lève `AssertionError`.
  - **Sans retouche** : `test_cellule_depend_du_contenu_des_lieux`, `test_identique_quand_chemins_suffisent`, `test_bourg_miniers_ont_faim` et `test_monde_ressent_la_distribution` passent.

- **SC5 — les sommes, le déterminisme et l'empreinte tiennent.**
  - **Commande** : `python3 -m pytest sim/tests/test_lieux.py sim/tests/test_determinisme.py sim/tests/test_distribution_interieure.py -q` passe en entier.
  - **Sans modification**, en particulier : `test_tick_bit_pres_sur_une_annee`, `test_tick_repartit_sur_une_annee_et_suit_les_ecritures`, `test_photographie_et_empreinte_portent_les_lieux`, `test_consommation_par_lieu`, `test_consommation_par_lieu_sans_repartage_inutile` et `test_commerce_a_proportion`.
  - **L'empreinte** : un test neuf, ou une assertion ajoutée au test neuf de SC3, vérifie que chaque lieu de `cellule_vers_dict` porte les clés `dette_alimentaire_kg` et `duree_faim_ticks`. Il vérifie aussi que changer la dette d'un lieu change `json.dumps(monde.to_dict(), sort_keys=True)`.
  - **Contre-épreuve** : le même test, avec `cellule_vers_dict` qui omet ces clés, lève `AssertionError`.

- **SC6 — `/lieu` et la photographie ne publient rien de neuf.**
  - **Commande** : `python3 -m pytest sim/tests/test_monde.py -q -k "pont or lieux_documentes"` passe, sans retouche de ces tests ni de leurs contre-épreuves.
  - **Attendu** : `git diff --stat master -- 3d/` est vide. Les réponses figées `lieu-graine0-tick3.json` et `lieu-graine0-tick4.json` restent valides telles quelles, et `LecteurJsonTests.cs` n'est pas touché.

- **SC7 — le tick tient son budget.**
  - **Commande** : `python3 -m pytest sim/tests/test_monde.py -q -s -k "budget or part_miniere"` passe sans retouche.
  - **Attendu** : la médiane de `test_tick_sous_le_budget_du_service` reste < `BUDGET_TICK_MS` (100 ms). La valeur imprimée est recopiée dans la PR ; elle était de 90 ms sur master le 06/10/2026.

- **SC8 — MODELE.md dit la règle.**
  - **Commande** : `python3 -m pytest sim/tests/test_distribution_interieure.py -q -k "dette_par_lieu_documentee or documentee"` (le premier test est neuf).
  - **La sous-section « Ce que porte un lieu »**, jusqu'au `### ` suivant, nomme `dette_alimentaire_kg` et `duree_faim_ticks`. Elle garde `rang`, `population` et `stocks`.
  - **La section « La distribution à l'intérieur de la cellule »** contient `partager`, « à proportion des dettes », « faim » et « au bit près ». Elle ne contient plus « Dette et faim restent portées par la cellule ».
  - **Contre-épreuve** : le même texte, où « à proportion des dettes » est remplacé par « au hasard », lève `AssertionError`.
  - **Gardes existantes, vertes sans retouche** :
    - `python3 -m pytest sim/tests/test_lieux.py -q -k amorcage_documente` ;
    - `python3 -m pytest sim/tests/test_province.py -q -k bourg_documente` ;
    - `python3 -m pytest sim/tests/test_foyers.py -q -k "documentation or gardes"`.

- **SC9 — aucun test ne s'assouplit, rien d'autre ne bouge.**
  - **Périmètre** : `git diff --stat master` ne montre que les fichiers du Périmètre.
  - **`test_lieux.py`** : `git diff master -- jeu/sim/tests/test_lieux.py` ne remplace qu'une ligne existante, celle de SC1. Tout le reste est ajout.
  - **`test_distribution_interieure.py`** : `git diff master -- jeu/sim/tests/test_distribution_interieure.py` ne contient que des ajouts.
  - **Tests à rejouer**, sans retouche : `python3 -m pytest sim/tests/test_survie.py sim/tests/test_commerce.py sim/tests/test_foyers.py sim/tests/test_chantiers.py -q`. Ils lisent la consommation, la faim, la dette et le panier.

## Hors périmètre
- Des morts, des naissances ou des restes propres à chaque lieu, une population de cellule égale à la somme des lieux, et la réécriture de la partie (a) de `test_cellule_depend_du_contenu_des_lieux` : c'est le second sous-lot de #334.
- Toute règle qui lit la dette ou la faim d'un lieu (mortalité, natalité, migration, IA, prélèvement) ; les sections « Le déficit alimentaire et la mortalité » et « La natalité » de MODELE.md.
- La publication de la dette ou de la faim d'un lieu par `/lieu`, la photographie ou Unity ; toute régénération des réponses figées.
- Le commerce et la migration par le bourg, et la fin de la répartition proportionnelle : c'est le sous-lot 5 de #236.
- Tout changement de l'étoile des chemins, de la récolte, de l'amorçage ou de `repartir_sur_les_lieux` ; le PC.
