# Lot #256 — Les champs demandent des bras
Jalon : J4 · Machine : vps · Taille prévue : 220 lignes

## But
La récolte d'une cellule suit les bras de ses paysans : tant qu'ils
suffisent, rien ne change ; sous ce seuil, chaque paysan qui manque aux
champs retire sa part de récolte. C'est la moitié « monde » de la décision
du jalon J4 (« des bras au chantier, c'est moins de bras aux champs cette
année ») : le jour où un chantier prendra des bras, la récolte le sentira.

Décision du propriétaire sur l'issue #256 : **A** — le tick lit les
métiers, **pour la récolte seulement** ; la constante est choisie pour que
toutes les cellules aient assez de bras au départ et sur l'année mesurée.
Ne pas reposer la question.

## Règle du monde
Niveau **2** : plausible, jamais sourcé. Découle de `jeu/sim/MODELE.md`,
« Les foyers par métier » et « Le rendement agricole et sa variabilité ».

1. **Les km² cultivés** d'une cellule sont ceux que la récolte travaille
   déjà : `area_km2 × facteur_relief × facteur_eau × facteur_agricole`
   (le facteur agricole est `1 − part minière`, fonction existante
   `_facteur_agricole`). Sans carte : `area_km2`. La saison n'y entre pas :
   un champ d'hiver demande les mêmes bras qu'un champ d'été.
2. **Les bras requis** = km² cultivés × `BRAS_AUX_CHAMPS_PAR_KM2`.
   Constante nommée dans `sim/constants.py`, valeur **0,1** (voir la mesure
   plus bas).
3. **Le facteur de bras** = `min(1, paysans / bras_requis)`, où `paysans`
   est `habitants_par_metier.get("paysans", 0)`. Les mineurs ne comptent
   pas : ils sont à la mine, et la part minière reste appliquée comme
   aujourd'hui (on ne la retire pas : l'équilibre bougerait).
4. **La récolte du tick** = la récolte d'aujourd'hui × facteur de bras.
   Bras suffisants : facteur exactement `1.0`, récolte identique au bit
   près. Sous le seuil, la récolte est proportionnelle aux paysans : un bras
   retiré retire `récolte_pleine / bras_requis`.
5. **Cellule sans métiers calculés** (`lire_habitants_par_metier` rend
   `-1`, cas des `Cell` nus des tests unitaires) : facteur `1.0`, récolte
   d'aujourd'hui. Des bras requis nuls (km² cultivés nuls) : facteur `1.0`
   (il n'y a rien à récolter de toute façon).
6. Le facteur s'applique **dans les deux maillons de production du tick**,
   `_apply_production` (avec ou sans carte) et
   `_apply_production_saison_moyenne` (le régime sans `numero_tick`, celui de
   `test_bit`). Il ne s'applique **pas** dans `production_du_tick_kg`,
   `population_soutenable_de` ni `production_moyenne_kg_par_tick` : le
   plafond de survie reste la récolte à bras suffisants. Le facteur ne
   pouvant que l'abaisser, ce plafond reste une borne supérieure, et
   l'amorçage ne dépend pas des métiers (pas de cercle).
7. Conséquence assumée (dite dans MODELE.md) : en famine, des paysans morts
   ou partis peuvent faire baisser la récolte, et la famine peut s'aggraver
   d'elle-même.

### La mesure qui fixe la constante (faite par le chef, graine 0)
Rapport `paysans / km² cultivés`, minimum sur les 596 cellules et sur
chaque tick d'une année :

| | départ | minimum sur 365 ticks |
|---|---|---|
| régime sans `numero_tick` (`test_bit`) | 5,76 | 0,291 (cellule 10322, tick 87, famine) |
| régime avec `numero_tick` (`forge`) | 5,76 | 0,248 (cellule 10322, tick 87) |

Aucune cellule n'a zéro paysan ni zéro récolte au départ. `0,1` laisse une
marge de 2,5 sous le pire tick mesuré. MODELE.md le dit franchement : la
valeur est **choisie basse pour que le monde mesuré ne bouge pas**, elle
n'est pas une densité agricole réaliste ; elle sera revue quand un geste
retirera des bras aux champs.

### Les pièges du dépôt (lus par le chef)
- `test_write_coverage.py::test_chaque_constante_du_moteur_change_le_monde`
  remplace chaque constante numérique que **`engine.py` lit directement**
  et exige que son petit monde de trois `Cell` nus change. Ces cellules
  n'ont pas de métiers : une lecture directe de `_constantes.BRAS_…` dans
  `engine.py` serait inerte et rougirait. **La constante se lit dans
  `sim/foyers.py`** (fonction `facteur_bras(metiers, km2_cultives)`, qui
  relit `_constantes.BRAS_AUX_CHAMPS_PAR_KM2` à chaque appel) ; `engine.py`
  appelle `foyers.facteur_bras`. `test_aucune_constante_terminale` est
  satisfait par cette lecture.
- `test_monde.py::test_une_seule_definition_part_miniere` compte les
  fonctions qui lisent `PART_MINIERE_*` : réutiliser `_facteur_agricole`,
  ne jamais relire ces noms.
- `test_no_hardcoded.py` refuse tout littéral hors {0, 1, −1} dans `sim/`.
- Le moteur lit les constantes par le module (`_constantes.X`), jamais par
  `from sim.constants import`.

## Périmètre
jeu/sim/constants.py
jeu/sim/foyers.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/tests/test_foyers.py

## Conditions de succès
Les nouveaux cas vont dans `jeu/sim/tests/test_foyers.py`, qui porte
l'invariant des foyers. Chaque contre-épreuve est jouée **dans le test**
(monkeypatch puis `pytest.raises(AssertionError)` ou comparaison qui doit
différer), comme le fait déjà ce fichier.

**SC1 — Bras suffisants, rien ne change ; un bras retiré, sa part en
moins.** `python3 -m pytest jeu/sim/tests/test_foyers.py -q -k recolte_bras`
Sur une cellule de `World.charger(0)` (avec carte, régime avec
`numero_tick`, même graine de rng à chaque appel) : bras requis calculés
par le test lui-même à partir des facteurs (sans appeler
`foyers.facteur_bras`) ; les paysans sont posés par
`ecrire_habitants_par_metier`. Avec `paysans = ceil(requis)` puis
`paysans = 10 × requis`, la récolte écrite par `_apply_production` est
**égale au bit près** à celle que produit `production_du_tick_kg` avec le
même tirage. Avec
`paysans = floor(requis) − k` pour k = 1 et 2, la récolte vaut
`pleine × paysans / requis` (`math.isclose`, `rel_tol=1e-12`) et l'écart
entre k = 1 et k = 2 vaut `pleine / requis`. Transformer un paysan en
mineur sous le seuil fait baisser la récolte ; ajouter des mineurs ne la
relève pas. Même contrôle sur `_apply_production_saison_moyenne`.
Contre-épreuve : `foyers.facteur_bras` remplacé par `lambda *a: 1.0` → les
assertions sous le seuil échouent ; un facteur qui compte aussi les
mineurs → l'assertion « mineurs ne relèvent pas » échoue.

**SC2 — Une cellule sans métiers récolte comme aujourd'hui.**
`python3 -m pytest jeu/sim/tests/test_foyers.py -q -k recolte_sans_metiers`
Un `Cell` nu (métiers `-1`), sans carte puis avec la carte de sa cellule :
la récolte est égale au bit près à `production_kg` / `production_du_tick_kg`
du même tirage. Une cellule amorcée vide (`{}`, population 0) récolte 0.
Contre-épreuve : un facteur qui lit `-1` comme zéro paysan → la récolte du
`Cell` nu tombe à 0 et l'égalité échoue.

**SC3 — Le monde mesuré ne bouge pas, sur l'année, dans les deux régimes.**
`python3 -m pytest jeu/sim/tests/test_foyers.py -q -k bras_suffisent_un_an`
`foyers.facteur_bras` est enveloppé pour enregistrer chaque valeur rendue
et le rapport `paysans / requis` ; `World.charger(0)`, `random.Random(0)`,
365 ticks sans `numero_tick`, puis 365 ticks avec `numero_tick=i`. Le test
exige : au moins 596 × 365 appels par régime (un échantillon vide échoue),
toutes les valeurs rendues `== 1.0`, et il affiche le rapport minimum
(attendu ≈ 2,9 et ≈ 2,5). Le moteur étant déterministe, un facteur
toujours égal à 1 prouve que le monde est celui d'avant.
Contre-épreuve : `BRAS_AUX_CHAMPS_PAR_KM2` multiplié par 100 → sur 30 ticks,
au moins une valeur rendue est `< 1.0`, et `_octets_sans_foyers` du monde
diffère de celui du même jeu de 30 ticks avec la constante nominale.

**SC4 — Aucun test existant ne s'assouplit ; toute la suite reste verte.**
`python3 -m pytest jeu -q` — verts, en particulier `test_foyers.py::test_bit`
(365 ticks comparés octet pour octet), `test_monde.py` (fichiers `/lieu`
figés des ticks 3 et 4), `test_write_coverage.py`, `test_no_hardcoded.py`,
`test_survie.py`.
`git diff origin/master -- jeu/sim/tests ':!jeu/sim/tests/test_foyers.py'`
est vide, et
`git diff -U0 origin/master -- jeu/sim/tests/test_foyers.py | grep '^-[^-]'`
ne rend que **deux lignes**, les deux phrases figées
`"le tick ne lit pas les métiers"` (l. 235 et l. 567), remplacées par
`"le tick ne lit les métiers que pour la récolte"`.
Contre-épreuve : avec `BRAS_AUX_CHAMPS_PAR_KM2 = 10`, au moins un de
`test_bit` ou `test_monde` rougit (le codeur le constate et le note dans la
PR, sans le committer).

**SC5 — MODELE.md dit la règle.**
`python3 -m pytest jeu/sim/tests/test_foyers.py -q -k "documentation"`
Dans « Les foyers par métier », la phrase **« Le tick ne lit les métiers
que pour la récolte »** remplace « Le tick ne lit pas les métiers », suivie
de la règle : km² cultivés, `BRAS_AUX_CHAMPS_PAR_KM2`, `min(1, …)`, niveau
2, valeur choisie basse et pourquoi, cellule `-1` inchangée, la famine qui
peut s'aggraver. « Le rendement agricole » ajoute le facteur de bras à la
formule et dit que le plafond de survie reste la récolte à bras suffisants.
« Ce que le moteur ne fait pas encore », point « répartir le travail » :
« aucun nombre du tick ne les lit » devient « le tick ne les lit que pour
la récolte » ; les changements de métier ne sont toujours pas simulés.
Un nouveau test exige dans la section des foyers `BRAS_AUX_CHAMPS_PAR_KM2`,
« km² cultivés » et « niveau 2 », et dans « Ce que le moteur ne fait pas
encore » l'absence de « aucun nombre du tick ne les lit ».
Contre-épreuve (dans le test, par `read_text` altéré) : retirer
`BRAS_AUX_CHAMPS_PAR_KM2` de la section, ou y remettre l'ancienne phrase à
la place de la nouvelle → le contrôle échoue.

## Hors périmètre
- Retirer des bras aux champs : aucun changement de métier, aucun chantier,
  aucune intention nouvelle. Aujourd'hui les bras ne manquent qu'en famine.
- La part minière : inchangée, toujours appliquée à la récolte.
- `population_soutenable_de`, `production_moyenne_kg_par_tick`,
  l'amorçage, l'extraction minière : inchangés.
- Les vues, le service et `/lieu` : ils n'affichent pas le facteur de bras
  (un lot de vue le fera) ; les fichiers figés ne changent pas.
- Une densité agricole réaliste : la valeur 0,1 est un choix de niveau 2
  pour garder le monde mesuré ; la retoucher est un autre lot.
- Âge, sexe, logement des foyers : niveau 3, non simulés.
