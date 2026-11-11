# Lot #1057 — Une ville affamée garde sa réserve : rapport de mesure

Mesuré le 11 novembre 2026, sous Linux (VPS), graine 0, IA active, aucun geste
du joueur. Niveau 2 : plausible, jamais sourcé.

## La décision qui change le brief

Le brief posait `reserve_ville_affamee_jours = 365`. La direction a tranché à
la place du propriétaire : **réponse B**, une ville affamée garde une réserve de
N jours de sa ration et n'exporte que le reste ; la preuve « n'exportent plus »
devient « exportent moins ». N est choisi à **30 jours** (l'exemple de la
décision) et déclaré dans `jeu/data/commerce.toml`, qui n'existait pas encore.

Conséquence mesurée : avec la soudure (212 jours de ration au 1er janvier),
aucune ville affamée n'est sous 30 jours de ration en janvier. **Janvier ne
change donc pas**, octet pour octet, et la table du brief (janvier, 365 jours)
ne vaut plus. La réserve ne mord que plus tard, quand une ville a mangé son
grenier jusqu'à elle.

## SC3 — la table mesurée

Commande, depuis `jeu/` (deux copies du monde de 1400 jouées 300 jours, la
première avec la réserve du dépôt, la seconde sous `garder_le_commerce_d_avant`,
c'est-à-dire N = 1) :

```
python3 -m pytest sim/tests/test_commerce.py -q -s -k "premier_mois_ville_affamee or conservation_ville_affamee"
```

Sorties de nourriture de chaque cellule affamée (baisse de son stock pendant
l'appel extérieur de `_apply_commerce`) et stock au 300e jour :

| ville | sortie, règle d'avant | sortie, réserve de 30 jours | stock au 300e jour, avant | stock au 300e jour, réserve |
|---|---|---|---|---|
| Le Caire | 24 120 t | 24 101 t | 30 645 t | 30 690 t |
| Alexandrie | 7 749 t | 6 743 t | 0 t | 0 t |
| Malaga | 7 455 t | 7 455 t | 19 072 t | 19 072 t |
| Pise | 9 087 t | 9 087 t | 15 881 t | 15 881 t |
| Paris | 0 t | 0 t | 14 440 t | 14 440 t |
| Gand et Bruges | 15 693 t | 15 564 t | 6 323 t | 6 451 t |
| Gênes | 9 229 t | 9 229 t | 24 126 t | 24 126 t |
| Plaisance | 0 t | 0 t | 18 801 t | 18 801 t |

Huit cellules sur 596 sont affamées au départ. Les sorties de janvier (les 30
premiers jours) sont identiques sous les deux règles ; Gand sort plus de
1 000 t en janvier, Le Caire aussi. Premier jour de différence (mesure de 365
jours) : Alexandrie le 116e, Le Caire le 129e, Gand le 292e. Paris et Plaisance
n'exportent rien sous les deux règles (sans port) : ils ne comptent pas comme
preuve.

**Ce que la mesure dit sans fard.** Avec 30 jours, l'effet est réel et petit :
Gand exporte 129 t de moins sur 300 jours, Le Caire 19 t, Alexandrie 1 006 t.
Gand tombe à 0 t vers le 364e jour sous les deux règles. Une réserve plus
longue (90, 180 ou 365 jours) rend l'effet visible plus tôt : c'est une ligne de
`commerce.toml`, que le propriétaire peut changer.

La règle d'avant passe sous la réserve de 30 jours (contre-épreuve) ; la
réserve jamais, à aucun des 300 appels du commerce.

## SC4 — conservation

La même fixture vérifie, à chaque appel extérieur de `_apply_commerce` de la
copie à réserve, que la masse (paniers des cellules + bassin, `math.fsum`) est
conservée à `1e-9 × masse` près, et que les paniers des lieux d'une cellule
affamée qui ne reçoit rien égalent son stock. Contre-épreuve : 1 t ajoutée au
panier de Gand après le commerce fait échouer la vérification
(`-k conservation_ville_affamee_contre_epreuve`).

## SC5 — le décor d'avant et les empreintes

Avec 30 jours, les empreintes épinglées sur le monde de la soudure ne bougent
pas : la réserve ne mord qu'à partir du 116e jour, et ces épreuves jouent 1 à
30 ticks sans le décor d'avant. Mesuré à N = 30 (toutes vertes, aucune
empreinte recapturée) :

```
python3 -m pytest sim/tests/test_determinisme.py -q -k "part_bit_pres or prelevement_bit_pres or du_au_suzerain_bit_pres"   # 3 passed
python3 -m pytest sim/tests/test_monde.py -q -k "test_service_ia_sans or test_service_reponse_figee_places_et_anciens_champs or test_service_reponse_figee_maitres_et_anciens_champs or test_service_reponse_figee_flux_et_origine"   # 7 passed
python3 -m pytest sim/tests/test_ville1400.py sim/tests/test_ville_dense.py -q -k "test_ilots_sc3_petites_bases_identiques or test_sc5_hors_epreuve_rien_ne_change"   # 2 passed
python3 -m pytest vues/relief/tests/test_carte1400.py -q -k test_capitales_ia_sans   # 1 passed
python3 -m pytest forge/tests/test_forge.py -q -k test_forge_ia_sans   # 2 passed
```

**Les empreintes savent rougir.** Avec `reserve_ville_affamee_jours = 365`
(essai temporaire, remis à 30), `test_part_bit_pres`, `test_prelevement_bit_pres`
et `test_du_au_suzerain_bit_pres` rougissent ; les autres, sur le décor ou
trop courtes, restent vertes.

**Contre-épreuve du décor.** Avec `amorcer_comme_avant_la_soudure` privé de
`garder_le_commerce_d_avant`, `python3 -m pytest forge/tests/test_forge.py -q -k test_forge_ia_sans`
rougit au cas à 30 ticks (empreinte `b2d3dc6d…` → `5ea02554…`) : avec cinq
jours de stock, les villes affamées du décor sont sous leur réserve et
cessent d'exporter. Avec l'appel, les deux cas passent.

`test_modificateurs.py::test_sans_modificateur_la_photographie_a_365_jours_est_celle_d_avant`
(365 ticks) rougit sans `garder_le_commerce_d_avant` à côté de
`couper_la_famine`, et passe avec ; il garde ses deux valeurs d'empreinte.

## Budgets du tick

`test_tick_sous_le_budget_du_service` et `test_budget_flux_et_contre_epreuve`
rougissent sur ce VPS **avec ou sans** le lot (médianes de 105 à 143 ms contre
100 ms, mesurées sur un `HEAD` propre et sur la branche, la machine étant
chargée par d'autres lots). L'ajout du lot au tick est un accès au dictionnaire
par cellule offrante.
