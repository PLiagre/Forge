# Lot #574 — La part coutumière tient ses gens
Jalon : J3 · Machine : vps · Taille prévue : 170 lignes

## But
La part coutumière `PART_COUTUMIERE` devient une valeur prouvée : un an de prélèvement coutumier, convois compris, coûte au plus 1 % des habitants du monde, c'est la plus haute valeur au centième qui le tient, et le monde avec prélèvement est figé à l'octet sur les graines 0 et 42.

## Le joueur
Le joueur qui laisse la coutume ne vide pas ses lieux : un an de prélèvement coutumier coûte au plus 1 % des habitants du monde, et prendre plus coûte davantage. C'est le point de départ de la décision du jalon J3, « prendre plus aujourd'hui ou garder ses gens » : la coutume est un choix sûr, et chaque centième au-dessus se paie en habitants. Le joueur réglera sa part à l'écran avec #405 (le geste de #395 existe déjà dans le service) ; #399 fera partir les foyers d'un maître qui prend trop, et #400 et #401 montreront ce qui circule.

## Règle du monde
Suite de la section **« ## Le prélèvement »** de `jeu/sim/MODELE.md` : un paragraphe neuf, **« Calibration de la part coutumière »**, après le paragraphe de l'étape Prélèvement écrit par #573. La règle du monde ne change pas : ce lot prouve la valeur de la constante et fige le monde qui en sort.

**La règle de calibration.** Graine 0, monde chargé par `World.charger(0)`, 365 ticks numérotés 0 à 364 avec `random.Random(0)`, toutes les maisons à la même part `p` (`monde.parts = dict.fromkeys(monde.parts, p)`). `habitants(p)` = somme des `population` des cellules après le 365e tick. La perte d'un an est `perte(p) = 1 − habitants(p) / habitants(0)` : on la mesure **contre le même monde sans prélèvement au même jour**, pas contre le 1er janvier (le monde grandit pendant l'année : 34 957 409 habitants au chargement, 36 077 631 un an plus tard sans prélèvement). La part coutumière est juste quand `perte(PART_COUTUMIERE) ≤ 0,01 < perte(PART_COUTUMIERE + 0,01)` (la somme arrondie au centième, `round(..., 2)`, jamais `0.039999…`).

**Les mesures du chef** (srv1914711, code de `master` à 1dca65c, convois de #573 compris, 37 à 47 s par année) :

| part | habitants après un an | perte |
|---|---|---|
| 0 | 36 077 631 | — |
| 0,02 | 35 854 591 | 0,62 % |
| 0,03 | 35 730 318 | 0,96 % |
| 0,04 | 35 576 715 | 1,39 % |
| 0,05 | 35 395 341 | 1,89 % |
| 0,10 | 34 007 518 | 5,74 % |

**0,03 tient avec les convois** : `PART_COUTUMIERE` reste à 0,03 (la clause « elle passe à 0,02 » de l'issue ne joue pas). La marge est mince (0,04 point) : un lot qui change la production, la faim ou les départs (#397, #398, #399) fera rougir cette preuve et devra remesurer. **Niveau 2** : une règle de jeu plausible (la coutume ne vide pas les lieux), jamais sourcée ; la part réelle d'un seigneur de 1400 n'est pas mesurée ici. Si l'exécutant mesure autre chose que ces chiffres (à 1 habitant près), il s'arrête et le dit dans la PR : le monde a changé depuis ce brief.

**Constante.** Dans `jeu/sim/constants.py`, seul le commentaire de `PART_COUTUMIERE` change : « provisoire » devient la valeur mesurée (0,03 : −0,96 % en un an, 0,04 : −1,39 %, graine 0), niveau 2. La valeur reste `0.03` ; aucune autre constante ne bouge.

## Périmètre
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_prelevement.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/README.md

## Conditions de succès
Toutes les commandes partent de `jeu/` et visent un fichier, avec `-k` au besoin. **Ne jamais lancer la suite entière** (`pytest jeu`, `sim/tests/` ou un dossier) : elle dépasse l'heure. Chaque nombre comparé est dérivé et affiché (`print`), jamais écrit en dur, sauf les empreintes figées de SC4. Aucun test existant ne change : les cas s'ajoutent à la fin de `test_prelevement.py` (l'invariant du prélèvement) et de `test_determinisme.py` (l'invariant des mondes figés).

- **SC1 — La coutume tient ses gens, et c'est la plus haute au centième.** Dans `test_prelevement.py`, une fonction `_habitants_apres_un_an(p)` applique la règle de calibration ci-dessus sur un `World.charger(0)` neuf (ou une `copy.deepcopy` d'un monde chargé une fois), mise en cache au niveau du module (`functools.cache`) pour qu'une année ne se joue qu'une fois par processus. Une fonction pure `_verifier_calibration(part, habitants)` (dictionnaire part → habitants) affirme `perte(part) ≤ 0,01` et `perte(round(part + 0,01, 2)) > 0,01`. Le test `test_calibration_de_la_part_coutumiere` l'appelle avec `c.PART_COUTUMIERE` et les années à 0, `PART_COUTUMIERE` et `PART_COUTUMIERE + 0,01`, et affiche les trois populations et les deux pertes. Commande : `python3 -m pytest sim/tests/test_prelevement.py -q -k calibration -s`. Contre-épreuves, dans le même test : `_verifier_calibration(0.10, …)` avec l'année jouée à 0,10 lève `AssertionError` (perte de 5,7 %, trop haute) ; `_verifier_calibration` sur un dictionnaire fabriqué où la part du dessus perd aussi moins de 1 % lève `AssertionError` (la vérification « plus haute au centième » mord, sans année de plus).
- **SC2 — Prendre plus coûte davantage.** Dans le même test ou un test voisin qui réutilise le cache : `habitants(0) > habitants(PART_COUTUMIERE) > habitants(PART_COUTUMIERE + 0,01) > habitants(0,10)` (direction, pas valeur ; les écarts affichés). Aucune année de plus que les quatre de SC1 (0 ; 0,03 ; 0,04 ; 0,10). Contre-épreuve : la même vérification de direction sur la liste renversée lève `AssertionError`. Le temps total du module affiché par `--durations=5` s'écrit dans la PR (≈ 3 min attendues pour les quatre années).
- **SC3 — La règle du modèle.** Un test de `test_prelevement.py` lit la section « ## Le prélèvement » (`_section_prelevement`) et y trouve « Calibration de la part coutumière », la valeur de `c.PART_COUTUMIERE` écrite au centième avec une virgule (dérivée de la constante, pas écrite en dur : « 0,03 »), « 1 % », « graine 0 », « niveau 2 », et les pertes mesurées à `PART_COUTUMIERE` et à `PART_COUTUMIERE + 0,01` ; le mot « provisoirement » n'y figure plus, ni « provisoire » dans la ligne de commentaire au-dessus de `PART_COUTUMIERE` dans `constants.py`. Contre-épreuve : la même lecture sur la section où « 0,03 » est remplacé par « 0,02 » lève `AssertionError`. `jeu/sim/tests/README.md` dit, à la ligne de `test_prelevement.py`, qu'il prouve la calibration, et à celle de `test_determinisme.py`, qu'il fige le monde avec prélèvement. Puis `python3 -m pytest sim/tests/test_prelevement.py -q -k "modele or calibration"` passe.
- **SC4 — Le monde avec prélèvement est figé.** Dans `test_determinisme.py`, un test neuf `test_prelevement_bit_pres`, sur le modèle de `test_part_bit_pres` **mais sans** `monkeypatch` de `PART_COUTUMIERE` : graines 0 et 42, `World.charger(seed)` et `random.Random(seed)`, empreintes relevées après 1, 3 et 20 ticks (après 1 tick des convois sont en route et aucun n'est arrivé ; après 3, les routes de 1 et 2 jours ont livré ; après 20, toutes, la plus longue faisant 14 jours). Chaque point donne deux SHA-256 : le JSON trié de `to_dict()`, et le `pickle` de (`dataclasses.asdict` des cellules, `stocks_mer`, état du `rng`, retours de `engine.tick`, greniers triés, convois internes triés `(arrivée, facteur, total, charges)`, `mange_convois_kg`, `pertes_kg`). Les six couples sont figés en dur dans une table `_PRELEVEMENT_BASE`, calculés une fois par l'exécutant. Le test affirme aussi qu'au point 1 `to_dict()` porte `convois` et `mange_convois_kg`, et qu'au point 3 il porte `greniers`. Commande : `python3 -m pytest sim/tests/test_determinisme.py -q -k "prelevement_bit_pres or part_bit_pres"`. Contre-épreuves : la vérification sur `{}` lève ; sur la table privée du point (42, 20) lève ; après `math.nextafter` sur la nourriture d'un grenier, l'empreinte recalculée de (42, 20) fait lever la vérification ; pour chaque graine et chaque point commun (1 et 3), les deux empreintes de `_PRELEVEMENT_BASE` diffèrent de celles de `_PART_BASE` (le monde figé est bien celui qui prélève).
- **SC5 — Rien d'autre ne bouge.** `git diff` de `test_prelevement.py` et `test_determinisme.py` n'a que des lignes ajoutées (aucune ligne retirée ni changée : vérifié par le relecteur avec `git diff --numstat`, colonne des suppressions à 0 pour ces deux fichiers) ; `git diff -- sim/constants.py` ne touche qu'une ligne de commentaire et laisse `PART_COUTUMIERE = 0.03`. Puis les tests de #573 passent sans modification : `python3 -m pytest sim/tests/test_prelevement.py -q -k "not calibration"`, et `python3 -m pytest sim/tests/test_write_coverage.py sim/tests/test_no_hardcoded.py -q`.

## Hors périmètre
- Changer la valeur de `PART_COUTUMIERE` (0,03 tient, mesuré) ou toute autre constante ; changer l'étape Prélèvement, les convois ou le moteur.
- Les foyers qui quittent un maître qui prend trop (#399), le vassal qui paie son suzerain (#397), le grenier rouvert (#398) : ils changeront les pertes mesurées ici, et la preuve avec.
- La calibration sur d'autres graines ou sur plus d'un an ; la part de l'IA (jalon 5).
- Tout affichage : service, photographie, carte, Unity (#400, #401, #405) ; aucun fichier de `3d/` ne bouge.
- Modifier une assertion, une empreinte ou une contre-épreuve d'un test existant, dont `test_part_bit_pres`, `test_registre_bit_pres`, `test_grenier_bit_pres` et les tests de #573.
