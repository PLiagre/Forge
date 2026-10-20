# Le tick de master retrouve sa marge — lot #745

Mesure du 20/10/2026, VPS, Python 3.12.3 ; base `56f8dfdbfd89ab24982edbc32bcd2a417bd8fc49`. Monde chargé avec la graine 0 : 596 cellules, 1 364 arêtes, dont 917 terrestres. Le worktree demandé est refusé par le montage en lecture seule du Git partagé : la référence est extraite, sans modification, par `git archive 56f8dfd | tar -x -C /tmp/base-745`.

Trois gains, sans conserver de table sur `World` : les voisines terrestres sont regroupées au début de la migration, avec leur ordre, leurs doublons et leurs boucles ; les offres maritimes ne parcourent que les ports, les offres nécessaires aux demandes terrestres étant déjà calculées ; les capacités partagent les facteurs de relief du maillon, gardent la première arête et ne cherchent des apports routiers qu'aux bouts portant des rues. Les constantes et les arêtes sont relues à chaque tick. Les anciens chemins restent appelables, sans table ou avec `limiter_offres_maritimes=False`.

Les médianes alternées et les temps par maillon restent à renseigner après la fin des tests historiques, pour mesurer sans autre vérification locale en parallèle.

`python3 /tmp/empreinte-745.py /tmp/avant.txt` sur la base, puis `/tmp/apres-final.txt` dans le chantier : **366 empreintes identiques**, `cmp` silencieux (code 0). Empreintes avant = après :

- Initiale : `711f59586bbb68827f8113f5ae3fbb2f4add87eb602e598f5af9c96252b02ec2`.
- Finale : `e28d97d7a550c5a242ba34a4598652468068f8fd6a52b39da550436ace385ba4`.

Avec `--decaler`, `cmp` rend 1 ; la première différence est la ligne **102**, après le tick 100 (`diff -u` commence à la ligne 99 avec son contexte). Les 366 points sont bien calculés et la contre-épreuve détecte un seul cran de flottant.

Les commandes `python3 -m forge --ticks N --seed 0 --sortie DOSSIER --sans-chronique`, avec `N=0`, `N=30`, puis `N=30 --ia`, passent sur les deux côtés. SHA-256 de `monde.json`, avant = après ; les valeurs à zéro et trente ticks diffèrent :

| Course | SHA-256 |
|---|---|
| 0 tick | `10c8ddc27e5d95d54ab40f3abaef247cea004896d2f015c9a5c543d377b26bf3` |
| 30 ticks | `2d93a818d89807a834619f4dc9adad157619174b65e0334a39feb9336e168ebf` |
| 30 ticks, IA | `283ffbf3b0dc487aedd5ce25ab563e46bc7fcfcc2d8ee8b7617f6b1624a8a504` |

Commandes depuis `jeu/` (sélections ciblées conformément à la consigne du codeur ; les fichiers entiers de SC2/SC6 restent à la CI) :

```bash
python3 -m pytest sim/tests/test_commerce.py sim/tests/test_lieux.py -q -s -k raccourci_745
python3 -m pytest sim/tests/test_no_hardcoded.py sim/tests/test_write_coverage.py -q
python3 -m pytest sim/tests/test_commerce.py sim/tests/test_distribution_interieure.py -q -m 'not chronometre' -k 'raccourci_745 or index_aretes or routes_commerciales or capacite or longueur or migration or maritime or par_bourg or sans_route or sans_chemin or dette_par_lieu'
python3 -m pytest sim/tests/test_lieux.py sim/tests/test_monde.py sim/tests/test_foyers.py sim/tests/test_prelevement.py sim/tests/test_flux.py -q -m 'not chronometre' -k 'tick_sans_partage_general or maillons_production or metiers_migration or migration_famine or flux_des_lieux_mesures or flux_affames_notes or neutralite_empreintes or consommation or commerce or shared_length or frontiere or facteur_transport'
python3 -m pytest sim/tests/test_distribution_interieure.py -q -k route_commerce
python3 -m pytest forge/tests/test_forge.py sim/tests/test_determinisme.py -q -k 'forge_ia_sans or bit_pres'
```

Résultats déjà acquis, dans cet ordre : **3**, **8**, **191**, **9**, **1** tests verts ; la sélection historique reste en cours. Les raccourcis comparent toutes les cellules ou arêtes, les flottants exacts, l'identité des arêtes et l'ordre des clés ; leurs contre-épreuves détectent une table périmée, des constantes/routes changées et des offres côtières oubliées. La carte exportée à zéro tick a été regardée.

`git diff --check` est silencieux ; aucune ligne de test existante n'est retirée ou modifiée. Seuls `engine.py`, les ajouts de `test_commerce.py` et cette mesure sont changés par le codeur ; le brief était déjà présent à l'ouverture du chantier. Budget, constantes et modèle documentaire restent inchangés.
