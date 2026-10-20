# Le tick de master retrouve sa marge — lot #745

Mesure du 20/10/2026, VPS, Python 3.12.3 ; chantier `57fe64e`, base `43c929decca6c54c71ddd795be3830c6676dd481` (ancêtre commun après la fusion de master). Monde chargé avec la graine 0 : 596 cellules, 1 364 arêtes, dont 917 terrestres. Le worktree demandé est refusé par le montage en lecture seule du Git partagé : la référence est extraite, sans modification, par `git archive 43c929d | tar -x -C /tmp/base-745-correction`.

Chaque gain reste dans le tick ; aucune table n'est conservée sur `World` :

- Migration : au lieu de balayer toutes les arêtes pour chaque cellule, une table des voisines terrestres est construite au début du maillon, dans l'ordre des arêtes, doublons et boucles compris.
- Capacités : au lieu de recalculer le relief et les apports routiers pour chaque arête, le maillon partage ses facteurs de relief et ne cherche les apports qu'aux bouts portant des rues ; il conserve la première arête. Arêtes, routes et constantes sont relues au tick suivant.
- Clés d'arêtes : une comparaison ordonne les deux identifiants, au lieu de deux appels à `min` et `max`.
- Commerce maritime : les offres restantes ne sont lues qu'aux ports, au lieu de toutes les cellules ; les arêtes maritimes déjà collectées sont transmises au contexte au lieu d'être relues.
- `partager` : la validation évite des vérifications de type répétées, et le tri stable décroissant des restes entiers remplace les clés en tuples, sans changer le départage par rang.
- Reprise des lieux : lorsque populations, clés et sommes des paniers sont déjà alignées, elle évite les copies et réécritures sans effet.
- Lecture de stock : `dict.get` remplace le test de présence puis l'indexation, en gardant valeur, type et sentinelle d'absence.

Les anciens chemins restent appelables sans table, avec `raccourci=False`, avec `limiter_offres_maritimes=False`, ou par `_lire_stock_par_presence`.

Mesure SC4 : `/tmp/mesure-745.py` charge `World.charger(0)`, joue cinq ticks de chauffe puis mesure vingt ticks (numéros 5 à 24, `time.perf_counter`, médiane). Une seconde course indépendante mesure chaque maillon dans son module ; le chronomètre de commerce ne compte que l'appel extérieur. `/tmp/alterner-745-correction.py` exécute base puis chantier, trois fois. Aucun autre test local ne tourne pendant ces mesures.

| Ordre | Côté | Première alternance (ms) | Alternance rejouée (ms) |
|---|---|---:|---:|
| 1 | base 1 | 92.263194 | 96.380084 |
| 2 | chantier 1 | 82.831138 | 81.258807 |
| 3 | base 2 | 149.967550 | 127.451947 |
| 4 | chantier 2 | 85.431683 | 82.206140 |
| 5 | base 3 | 97.646683 | 94.055370 |
| 6 | chantier 3 | 79.015096 | 86.330912 |

Le VPS partagé est chargé : écart maximal entre courses du même côté supérieur à 15 % dans la première série (base : 92,26 à 149,97 ms). L'alternance a donc été rejouée ; la seconde série reste variable (base : 94,06 à 127,45 ms). Les deux séries sont conservées, sans effacer les courses ralenties.

Les minima de la série rejouée sont **94.055370 ms** pour la base (course 3) et **81.258807 ms** pour le chantier (course 1) : **12.796563 ms gagnées**, soit **13.605 %**. Les deux seuils passent : `81.258807 ≤ 84.055370` (base − 10 ms) et `81.258807 ≤ 82.768726` (0,88 × base). La première série passe aussi : 79,015096 ms contre 92,263194 ms, soit 13,248098 ms et 14,359 % de gain.

Temps moyens des maillons sur les secondes courses correspondant aux minima retenus (base 3, chantier 1) ; écart = après − avant. Ces moyennes instrumentées ne sont pas les médianes des ticks ci-dessus ; leur somme inclut le coût des enveloppes et les variations de charge.

| Maillon | Avant (ms/tick) | Après (ms/tick) | Écart (ms/tick) |
|---|---:|---:|---:|
| `_valider_numero_tick` | 0.004 | 0.004 | +0.000 |
| `_appliquer_intentions` | 0.002 | 0.002 | +0.000 |
| `_appliquer_pertes_greniers` | 0.602 | 0.624 | +0.022 |
| `_avancer_chantiers` | 0.805 | 0.810 | +0.005 |
| `_affecter_artisans` | 0.488 | 0.653 | +0.165 |
| `repartir_sur_les_lieux` | 4.204 | 3.752 | -0.453 |
| `accorder_fabrication` | 1.820 | 1.757 | -0.063 |
| `_apply_fabrication` | 2.559 | 2.575 | +0.016 |
| `_apply_extraction` | 1.386 | 1.157 | -0.229 |
| `_apply_production` | 9.244 | 8.440 | -0.805 |
| `prelever` | 8.765 | 8.504 | -0.261 |
| `facteurs_des_routes` | 0.095 | 0.085 | -0.010 |
| `_apply_commerce` | 23.000 | 18.818 | -4.182 |
| `_apply_consumption` | 20.856 | 18.433 | -2.423 |
| `_update_hunger` | 0.402 | 0.356 | -0.046 |
| `_apply_mortality` | 2.461 | 2.217 | -0.244 |
| `_apply_natalite` | 5.030 | 4.711 | -0.318 |
| `noter_affames` | 0.014 | 0.013 | -0.001 |
| `_apply_migration` | 8.163 | 4.763 | -3.400 |
| `appliquer_departs` | 12.065 | 12.702 | +0.637 |
| `_avancer_compteur_ticks` | 0.009 | 0.008 | -0.001 |

`_remplir_chemins_interieurs` n’est pas appelé sur ces courses sans routes actives : 0 ms des deux côtés.

`python3 /tmp/empreinte-745.py /tmp/avant-745-correction.txt` sur la base, puis `/tmp/apres-745-correction.txt` dans le chantier : **366 empreintes identiques**, `cmp` silencieux (code 0). Empreintes avant = après :

- Initiale : `711f59586bbb68827f8113f5ae3fbb2f4add87eb602e598f5af9c96252b02ec2`.
- Finale : `e28d97d7a550c5a242ba34a4598652468068f8fd6a52b39da550436ace385ba4`.

Avec `--decaler`, `cmp` rend 1 ; la première différence est la ligne **102**, après le tick 100 (`diff -u` commence à la ligne 99 avec son contexte). Les 366 points sont bien calculés et la contre-épreuve détecte un seul cran de flottant. Deux premières commandes longues (année du chantier et exports de la base) ont été interrompues avec le code 143 ; elles ont été rejouées séparément et terminent avec le code 0. Les empreintes ci-dessus proviennent des courses complètes.

Les commandes `python3 -m forge --ticks N --seed 0 --sortie DOSSIER --sans-chronique`, avec `N=0`, `N=30`, puis `N=30 --ia`, passent sur les deux côtés. SHA-256 de `monde.json`, avant = après ; les valeurs à zéro et trente ticks diffèrent :

| Course | SHA-256 |
|---|---|
| 0 tick | `10c8ddc27e5d95d54ab40f3abaef247cea004896d2f015c9a5c543d377b26bf3` |
| 30 ticks | `2d93a818d89807a834619f4dc9adad157619174b65e0334a39feb9336e168ebf` |
| 30 ticks, IA | `283ffbf3b0dc487aedd5ce25ab563e46bc7fcfcc2d8ee8b7617f6b1624a8a504` |

SC5 : `cd jeu && python3 -m pytest -m chronometre sim/tests/ -q -s` : **8 tests verts, 1 317 écartés**, en 119,60 s, sans autre vérification locale en parallèle. Médianes imprimées :

| Mesure | Normale (ms) | Contre-épreuve ralentie (ms) |
|---|---:|---:|
| Tick du service | 88.04 | 1398.28 |
| Tick avec ateliers | 90.91 | 196.02 |
| Tick avec flux | 93.085 | 420.377 |
| Prélèvement pendant la mesure des flux | 8.827 | 112.686 |

La médiane avec départs actifs est **91,356 ms**, sans départs **87,177 ms**, pour vingt ticks de chaque côté ; le maillon départs fait **10,735 ms**, l'appel vide **0,001 ms**, et l'écart des médianes de tick est **4,178 ms**. Le test valide aussi sa contre-épreuve ralentie (médiane non imprimée). Le test de publication imprime, au tick 35, **36,145141 ms** pour `matiere_des_maisons` et **182,140561 ms** pour `_construire_etat`. Toutes les médianes de tick normales restent sous les 100 ms importées de `sim.service` ; les contre-épreuves dépassant le budget sont rejetées comme attendu.

Commandes depuis `jeu/` (sélections ciblées conformément à la consigne du codeur ; les fichiers entiers de SC2/SC6 restent à la CI) :

```bash
python3 -m pytest sim/tests/test_commerce.py sim/tests/test_lieux.py -q -s -k raccourci_745
python3 -m pytest sim/tests/test_no_hardcoded.py sim/tests/test_write_coverage.py -q
python3 -m pytest sim/tests/test_commerce.py sim/tests/test_distribution_interieure.py -q -m 'not chronometre' -k 'index_aretes or routes_commerciales or capacite or longueur or migration or maritime or par_bourg or sans_route or sans_chemin or dette_par_lieu'
python3 -m pytest sim/tests/test_lieux.py sim/tests/test_monde.py sim/tests/test_foyers.py sim/tests/test_prelevement.py sim/tests/test_flux.py -q -m 'not chronometre' -k 'tick_sans_partage_general or maillons_production or metiers_migration or migration_famine or flux_des_lieux_mesures or flux_affames_notes or neutralite_empreintes or consommation or commerce or shared_length or frontiere or facteur_transport'
python3 -m pytest sim/tests/test_distribution_interieure.py -q -k route_commerce
python3 -m pytest forge/tests/test_forge.py sim/tests/test_determinisme.py -q -k 'forge_ia_sans or bit_pres'
```

Résultats, dans cet ordre : **8**, **8**, **191**, **9**, **1**, **12** tests verts. La sélection historique termine en 1 732,80 s (46 tests écartés), dont l’année au bit près, les quatre couples de graines du registre et les deux du grenier. Aucun fichier de test existant n’est joué en entier, hormis les deux gardes explicitement demandées ; la suite entière reste à la CI. Les raccourcis comparent toutes les cellules ou arêtes, les flottants exacts, l'identité des arêtes et l'ordre des clés ; leurs contre-épreuves détectent une table périmée, des constantes/routes changées et des offres côtières oubliées. La carte exportée à zéro tick a été regardée.

`git diff --check` est silencieux ; aucune ligne de test existante n'est retirée ou modifiée. La correction de relecture complète ce seul relevé. Le lot change `engine.py`, `lieux.py`, `model.py`, les ajouts de `test_commerce.py` et de `test_lieux.py`, ainsi que cette mesure ; le brief était déjà présent à l'ouverture du chantier. Budget, constantes et modèle documentaire restent inchangés.
