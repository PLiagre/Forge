# Lot #1057 — Une ville affamée garde sa réserve : rapport de mesure

Mesuré le 11 novembre 2026, sous Linux (VPS), graine 0, IA active, aucun geste
du joueur. Niveau 2 : plausible, jamais sourcé.

## La décision qui change le brief

Le brief posait `reserve_ville_affamee_jours = 365`. La direction a tranché à
la place du propriétaire : **réponse B**, une ville affamée garde une réserve de
N jours de sa ration et n'exporte que le reste ; la preuve « n'exportent plus »
devient « exportent moins ». N est à choisir, et déclaré dans
`jeu/data/commerce.toml`, qui n'existait pas encore.

**N = 21 jours, et non 30 (correction 2).** La première version posait 30 jours,
l'exemple de la décision. La CI est rouge : `test_soudure.py::test_la_premiere_annee_tient_sans_joueur`
(graine 0, IA active, 365 jours, aucune cellule de la table du jalon 2 ne perd
plus de la moitié de ses habitants par la faim) trouve Alexandrie à 50,4 %.
Cause mesurée : Le Caire, affamé lui aussi, tient sa réserve dès le 330e jour
et cesse de verser du grain à Alexandrie, qui n'a plus que le bassin. La règle
fait ce qu'elle doit ; c'est sa durée qui est trop longue pour un monde où les
voisines affamées se nourrissent l'une l'autre. Le test n'est pas touché. Part
d'Alexandrie morte de faim au 365e jour (seuil 0,5), même graine, même IA :

| N | 1 (règle d'avant) | 7 | 10 | 15 | 20 | 21 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|
| Alexandrie | 28,5 % | 30,6 % | 36,5 % | 34,9 % | 38,2 % | 32,7 % | 56,6 % | 50,4 % |
| Gand et Bruges | 47,0 % | 45,3 % | 43,5 % | 42,9 % | 40,5 % | 40,5 % | 39,6 % | 38,0 % |

La courbe n'est pas monotone (un monde chaotique) mais le plafond est net : 25
et 30 jours échouent, tous les N mesurés de 1 à 21 passent. **21 jours** (trois semaines)
est la plus grande valeur mesurée verte ; la direction n'avait donné 30 qu'en
exemple. Le propriétaire peut le changer en une ligne de `commerce.toml`, la
preuve de la soudure borne ce qu'il peut y mettre.

Conséquence : avec la soudure (212 jours de ration au 1er janvier), aucune
ville affamée n'est sous 21 jours de ration en janvier. **Janvier ne change
donc pas**, octet pour octet, et la table du brief (janvier, 365 jours) ne vaut
plus. La réserve ne mord que plus tard, quand une ville a mangé son grenier
jusqu'à elle.

Une erreur du test du lot, trouvée au passage : sa contre-épreuve « la réserve
jamais sous la garde » figeait la liste des cellules affamées au jour 0 et leur
garde avec elle. Or la famine fait passer Gand sous ce que ses champs nourrissent
vers le 358e jour ; le moteur ne lui garde alors, à raison, que sa ration (il
relit l'état à chaque commerce). Le test recalcule désormais la garde jour par
jour, comme le moteur.

## SC3 — la table mesurée

Commande, depuis `jeu/` (deux copies du monde de 1400 jouées 365 jours, la
première avec la réserve du dépôt, la seconde sous `garder_le_commerce_d_avant`,
c'est-à-dire N = 1) :

```
python3 -m pytest sim/tests/test_commerce.py -q -s -k "premier_mois_ville_affamee or conservation_ville_affamee"
```

Sorties de nourriture de chaque cellule affamée (baisse de son stock pendant
l'appel extérieur de `_apply_commerce`) et stock au 365e jour, mesuré le 12
novembre 2026 :

| ville | sortie, règle d'avant | sortie, réserve de 21 jours | stock au 365e jour, avant | stock au 365e jour, réserve | 1er jour de différence |
|---|---|---|---|---|---|
| Le Caire | 28 054 t | 26 192 t | 1 217 t | 3 125 t | 130 |
| Alexandrie | 7 749 t | 7 060 t | 0 t | 0 t | 123 |
| Malaga | 8 631 t | 8 631 t | 10 816 t | 10 816 t | - |
| Pise | 10 189 t | 10 189 t | 8 769 t | 8 769 t | - |
| Paris | 0 t | 0 t | 956 t | 956 t | - |
| Gand et Bruges | 16 749 t | 15 903 t | 0 t | 0 t | 307 |
| Gênes | 10 529 t | 10 529 t | 18 442 t | 18 442 t | - |
| Plaisance | 0 t | 0 t | 4 557 t | 4 557 t | - |

Huit cellules sur 596 sont affamées au départ. Les sorties de janvier (les 30
premiers jours) sont identiques sous les deux règles ; Gand sort plus de
1 000 t en janvier, Le Caire aussi. Paris et Plaisance n'exportent rien sous
les deux règles (sans port) : ils ne comptent pas comme preuve.

**Ce que la mesure dit sans fard.** Avec 21 jours, l'effet est réel et modeste :
Le Caire exporte 1 862 t de moins sur l'année et finit avec 1 908 t de plus en
grenier, Alexandrie 689 t de moins, Gand 846 t de moins. Gand a mangé tout son
grain au 365e jour sous les deux règles : son stock y est nul des deux côtés, la
preuve y est la sortie, pas le stock. Une réserve plus longue rendrait l'effet
plus visible, mais 25 jours font déjà rougir la preuve de la première année.

La règle d'avant passe sous la réserve de 21 jours (contre-épreuve) ; la
réserve jamais, à aucun des 365 appels du commerce.

## SC4 — conservation

La même fixture vérifie, à chaque appel extérieur de `_apply_commerce` de la
copie à réserve, que la masse (paniers des cellules + bassin, `math.fsum`) est
conservée à `1e-9 × masse` près, et que les paniers des lieux d'une cellule
affamée qui ne reçoit rien égalent son stock. Contre-épreuve : 1 t ajoutée au
panier de Gand après le commerce fait échouer la vérification
(`-k conservation_ville_affamee_contre_epreuve`).

## SC5 — le décor d'avant et les empreintes

Avec 21 jours, les empreintes épinglées sur le monde de la soudure ne bougent
pas : la réserve ne mord qu'à partir du 123e jour, et ces épreuves jouent 1 à
30 ticks sans le décor d'avant. Mesuré à N = 21 le 12 novembre 2026 (toutes
vertes, aucune empreinte recapturée) :

```
python3 -m pytest sim/tests/test_determinisme.py -q -k "part_bit_pres or prelevement_bit_pres or du_au_suzerain_bit_pres"   # 3 passed
python3 -m pytest sim/tests/test_monde.py -q -k "test_service_ia_sans or test_service_reponse_figee_places_et_anciens_champs or test_service_reponse_figee_maitres_et_anciens_champs or test_service_reponse_figee_flux_et_origine"   # 7 passed
python3 -m pytest sim/tests/test_ville1400.py sim/tests/test_ville_dense.py -q -k "test_ilots_sc3_petites_bases_identiques or test_sc5_hors_epreuve_rien_ne_change"   # 2 passed
python3 -m pytest vues/relief/tests/test_carte1400.py -q -k test_capitales_ia_sans   # 1 passed
python3 -m pytest forge/tests/test_forge.py -q -k test_forge_ia_sans   # 2 passed
python3 -m pytest sim/tests/test_modificateurs.py -q -k sans_modificateur_la_photographie_a_365   # 1 passed
```

**Les empreintes savent rougir.** Avec `reserve_ville_affamee_jours = 365`
(essai temporaire fait avec la première version, remis ensuite),
`test_part_bit_pres`, `test_prelevement_bit_pres` et `test_du_au_suzerain_bit_pres`
rougissent ; les autres, sur le décor ou trop courtes, restent vertes.

**Contre-épreuve du décor.** Avec `amorcer_comme_avant_la_soudure` privé de
`garder_le_commerce_d_avant` (remplacé par une fonction vide le temps d'un
`pytest.main`), `python3 -m pytest forge/tests/test_forge.py -q -k test_forge_ia_sans`
rougit au cas à 30 ticks (empreinte `b2d3dc6d…` → `68046670…` à N = 21) : avec
cinq jours de stock, les villes affamées du décor sont sous leur réserve et
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
