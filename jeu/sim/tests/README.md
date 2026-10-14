# Les tests du jeu

## La règle d'admission

Un test existe s'il protège **l'une de ces trois choses**, et seulement :

1. un **invariant physique** — la masse se conserve, l'adjacence est
   symétrique, une dette ne se rembourse pas plus vite que le surplus ;
2. une **règle de jeu visible** — on ne mange pas deux fois, on a faim,
   puis on meurt ;
3. le **déterminisme** — même graine, même monde.

Un test qui protège une étape de processus, un compteur de coût, une
constante justifiée par un document, ou un mode d'automatisation n'a pas
sa place ici.

Corollaire : **ne pas ajouter un fichier de test par lot.** Un nouveau lot
ajoute ses cas dans le fichier qui porte déjà l'invariant concerné.

## Ce que porte chaque fichier

| fichier | ce qu'il protège |
|---|---|
| `test_survie.py` | faim, dette alimentaire, mortalité, direction du modèle de survie |
| `test_commerce.py` | conservation de la masse, un kg ne nourrit qu'une fois, pas de sur-livraison |
| `test_province.py` | la province est dérivée, jamais stockée |
| `test_determinisme.py` | même graine, même monde ; départage stable des égalités ; fige le monde avec prélèvement |
| `test_ville1400.py` | la ville de 1400 se dérive des foyers du bourg et reste la même après une année |
| `test_monde.py` | chargement de la carte, ligne de commande, schéma du snapshot ; le service local rend la photographie ; l'horloge avance à la vitesse choisie, une lecture n'attend pas un tick |
| `test_no_hardcoded.py` | aucun nombre magique dans le moteur |
| `test_write_coverage.py` | tout champ du modèle est écrit quelque part et lu quelque part |
| `test_convois.py` | la table du dû au suzerain, ses retenues hors carte et la durée de route d'un lieu jusqu'au siège de son maître, calculée une fois et laissée hors du tick |

```bash
py -m pytest sim/tests/ -q
```

`test_prelevement.py` protège le dû au suzerain, sa cascade et la conservation, les pertes et délais de convoi, les parts, le déterminisme à part nulle et la calibration de la part coutumière sur un an.

Les preuves `test_departs_tick_` exercent les départs actifs et leur conservation ;
`test_departs_budget_comparaison` mesure leur coût. Les références historiques
explicitement isolées à `TAUX_DE_DEPART = 0` décrivent le monde sans mieux-vivre,
y compris la calibration ancienne ; les autres preuves gardent les départs actifs.

Recensement des références lors du branchement des départs (ticks par course) :

| Épreuves | Invariant, durée et décision |
|---|---|
| `test_determinisme.py::test_tick_bit_pres_sur_une_annee`, `test_registre_bit_pres`, `test_grenier_bit_pres` | 365 ticks (puis 2 pour le grenier plein) : actif, les deux courses rejouent le tick courant ; les helpers anciens, le registre et le grenier vide doivent rester équivalents. |
| `test_determinisme.py::test_maitre_tick`, `test_noms_purete_et_tick` | 1 et 3 ticks : actif, aucune lecture de maître, registre ou noms ; aucune référence de peuplement. |
| `test_foyers.py::test_bit`, `test_un_an`, `test_bras_suffisent_un_an` | 365 ticks, contre-épreuves de 30 : actif, équivalence des foyers, sommes et bras suffisants restent des invariants du monde courant. |
| `test_prelevement.py::test_calibration_de_la_part_coutumiere`, `test_modele_calibration_de_la_part_coutumiere` | 365 ticks pour chacune des quatre parts du cache : taux nul avant tout accès au cache, référence historique de pertes et bornes à 1 %. |
| `test_prelevement.py::test_conservation_sur_un_an`, `test_charge_et_jours_de_bar`, `test_bar_paie_les_valois`, `test_deux_etages_et_pyramide_videe`, `test_le_suzerain_paie_a_son_tour` | 365 ticks, puis horizons dérivés des routes, 30 ticks et appels directs : actif, conservation et dû calculé sur les récoltes observées ; le dû ne change pas les populations. |
| `test_lieux.py::test_cellule_depend_du_contenu_des_lieux`, `test_tick_repartit_sur_une_annee_et_suit_les_ecritures`, `test_dette_et_faim_des_lieux`, `test_dette_a_un_effet_sur_le_monde`, `test_tick_sans_partage_general_apres_migration` | 30 puis 10, 365 puis 1, 60 puis 1, 60, et 1 tick : actif, conservation, effets locaux, dettes et absence de repartage restent exigés, montages modifiés compris. |
| `test_distribution_interieure.py::test_identique_quand_chemins_suffisent`, `test_monde_ressent_la_distribution`, `test_bourg_miniers_ont_faim`, `test_route_nourrit_le_bourg`, `test_route_vers_le_desert`, `test_sans_route`, `test_route_sans_maitre` | 30, 120, 60, puis courses de routes de 30 ticks et sondes de 1 : taux nul seulement pour `test_monde_ressent_la_distribution`, qui compare le peuplement ancien des bourgs (rouge avec départs actifs) ; les autres restent actifs, y compris consommation gratuite, capacité nulle et route neutre. |
| `test_commerce.py::test_kg_transportes_augmente_avec_mer`, `test_cellule_sans_production_survit_avec_capacite_derivee`, `test_cellule_sans_production_depérit_avec_capacite_plate`, `test_index_aretes_premiere_entree_repli_et_tick_suivant` | Année CLI, borne dérivée de mortalité, puis 2 ticks : actif, transport, survie sans lieux et reconstruction des arêtes ; les autres montages commerciaux sans lieux jouent 1 tick et les migrations directes restent intactes. |
| `test_monde.py::test_cellules_minieres_produisent_moins_et_portent_moins_de_monde`, `test_ateliers_sans_geste`, `test_logement_monde_inchange`, `test_plan_service_base_constante_et_calculee_une_fois` | Réserve initiale + borne de mortalité, 10, 10 et 365 ticks : actif, production, neutralité des vues et base constante ; les empreintes embarquées du service à 3 et 4 ticks restent actives. |
| `test_determinisme.py::test_part_bit_pres`, `test_prelevement_bit_pres`, `test_du_au_suzerain_bit_pres` | Points 1, 3 et 20, graines 0 et 42 : actif, empreintes inchangées et contre-épreuves inchangées ; les autres rejeux (200, 30, 25, 20, 12 ou 10 ticks) comparent le monde courant. |

Les cas `ouverture` de `test_intentions.py` protègent les refus sans effet, la
réservation du grain, l'application sans registre et la garde du service. Ceux
de `test_prelevement.py` suivent la conservation des secours, leurs pertes et
délais, la baisse des dettes, la livraison au lieu et les octets déterministes.
Les contre-épreuves neutralisent le retrait ou l'arrivée, ignorent l'attente
ou relisent le maître : les assertions doivent alors échouer.
