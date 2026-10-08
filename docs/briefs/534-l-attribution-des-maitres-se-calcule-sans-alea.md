# Lot #534 — L'attribution des maîtres se calcule, sans aléa
Jalon : J3 · Machine : vps · Taille prévue : 280 lignes

## But
Le monde saura dire, sans aléa et sans rien stocker, qui tient chaque lieu : la seigneurie de départ ses quatre premiers lieux, chaque grande maison et institution sa cellule de siège, et des maisons plausibles, par groupes de trois, tout le reste.

## Le joueur
Rien encore à l'écran : ce sous-lot de fond décide, une fois pour toutes et sans aléa, qui tient chaque lieu du monde — ses quatre lieux autour de son siège, ceux des seigneurs voisins, et son suzerain. Il prépare « Chaque lieu a son seigneur » (#391) et le geste du jalon J3 : fixer sa part sur son domaine (#395), voir le grain monter vers son grenier (#396) et celui de son suzerain (#397). Les lieux et leurs seigneurs se montreront avec #400 (service et photographie), #401 (carte de la forge) puis #405 dans Unity.

## Règle du monde
Découpé de #391 par le propriétaire. Dépend de : #514 (livré). Découle de « Les maisons du monde », « Les lieux d'une cellule, vue dérivée » et « Les puissances de 1400, vue dérivée » de `jeu/sim/MODELE.md`.

**Constantes.** `sim/constants.py` reçoit `LIEUX_DE_LA_SEIGNEURIE = 4` et `LIEUX_PAR_SEIGNEUR_PLAUSIBLE = 3`, commentées niveau 2, lues par `sim.constants as _constantes` à chaque appel (jamais `from sim.constants import`). Une valeur booléenne, non entière ou inférieure à 1 est refusée en nommant la constante. Aucun littéral 3 ou 4 dans `maitres.py` (`test_no_hardcoded.py`).

**Le module.** `jeu/sim/maitres.py`, pur, hors de `sim.model` ; ni le tick, ni `world.py`, ni `snapshot_export.py`, ni `service.py` ne l'importent.

`attribuer_maitres(monde, vue=None, maisons=None)` rend `(maitres, plausibles)` :
- les couples viennent de `lieux_depuis_monde(monde)` (identité dérivée de `cell_id` et de la surface ; sur le monde chargé, ce sont les rangs de `cellule.lieux`) ; `vue` vaut par défaut `puissances_depuis_monde(monde)`, `maisons` `charger_maisons()` (pour `par_puissance`) ; le registre est `monde.maisons`, jamais relu des tables ;
- `maitres` : dict neuf `(cell_id, rang) → id de maison`, dans l'ordre des cellules puis des rangs ;
- `plausibles` : tuple de `MaisonDuMonde` (de `sim/registre_maisons.py`), dans l'ordre de création.

L'ordre, en parcourant cellules et rangs dans l'ordre ; à chaque étape les maisons passent dans l'ordre du registre (par `id`) et **un lieu déjà tenu ne change jamais de maître** :
1. chaque fiche de sorte `seigneurie` placée tient les `LIEUX_DE_LA_SEIGNEURIE` premiers rangs de la cellule de son siège, bourg (rang 0) compris ; tous si la cellule en a moins ;
2. chaque `grande maison` placée tient les lieux encore libres de la cellule de sa capitale, chaque `institution` placée ceux de la cellule de son siège. Un siège hors carte (Saraï, Venise : `cell_id is None`) ne tient aucun lieu et reste déclaré tel quel ;
3. dans une cellule couverte (`vue[cell_id]` non `None`), les rangs encore libres, triés, se coupent en groupes consécutifs de `LIEUX_PAR_SEIGNEUR_PLAUSIBLE` (le dernier éventuellement plus petit). Chaque groupe est une fiche `MaisonDuMonde(id=f"plausible-{cell_id}-{premier rang}", nom=id, sorte="plausible", suzerain=…, siege=id, cell_id, rang=premier rang, hors_carte=None)`. Le suzerain est la racine de **la puissance de la cellule** : `grande-<par_puissance[p]>`, ou `institution-<p>` si `par_puissance[p] is None`. Jamais la maison tenante de `maisons_depuis_monde`, ni la maison dont le siège est dans la cellule : les cellules de Dijon tenues par Valois-Bourgogne relèvent de `grande-3` (France), celles de Bohême de `grande-9` (Luxembourg, puissance 10) ;
4. dans une cellule non couverte, même découpage, `suzerain=None`.

Les noms plausibles sont #392 : nom et siège reprennent l'identifiant. Une seigneurie de départ ne devient pas suzeraine des plausibles de sa cellule : ils relèvent de la puissance.

`valider_attribution(monde, maitres, plausibles, vue=None, maisons=None)` lève `AttributionInvalide` (sous-classe de `ValueError`, définie dans `maitres.py`) dont le message nomme le couple `(cell_id, rang)` : échantillon vide (aucun lieu dérivé, ou `maitres` vide) ; couple dérivé sans maître ; couple en trop ; maître absent du registre augmenté `monde.maisons + plausibles` ; identifiant présent deux fois dans ce registre augmenté (le couple de son siège) ; puis, couple par couple dans l'ordre, maître différent de celui que donne la règle (premier couple fautif) ; enfin fiche plausible différente de celle que donne la règle (couple de son siège). Elle peut recalculer la règle par `attribuer_maitres` : l'indépendance est portée par l'attente des tests, dérivée sans ce module. La validation des suzerains reste celle du registre : `valider_registre_maisons(monde.maisons + plausibles)` refuse un suzerain inconnu ou un cycle par `PuissanceInvalide`.

**Rien d'autre ne change** : ni `EtatDeLieu`, ni `Cell`, ni `World.charger`, ni `World.maisons` (aucun plausible n'y entre), ni `to_dict`, ni la photographie, ni le tick ; aucune empreinte ni référence figée ne bouge.

**Mesures du chef (graine 0, indicatives, jamais figées dans un test)** : 6 619 lieux ; 2 245 plausibles (1 812 groupes de 3, 102 de 2, 331 de 1), 94 sans suzerain, 273 sous une institution ; lieux tenus : départs 24, grandes maisons 508, institutions 116, plausibles 5 971. Aucune cellule réelle ne porte deux sièges ; aucune cellule de départ n'a moins de quatre lieux (minimum 8) : ces cas sont synthétiques. `World.charger(0)` ≈ 1 s, `puissances_depuis_monde` ≈ 0,7 s : une fixture de module partagée par les tests `maitre`.

**MODELE.md**, « Les maisons du monde » : un paragraphe « Le maître de chaque lieu » donne la règle telle que codée (les quatre étapes, les deux constantes, l'identifiant `plausible-<cell_id>-<premier rang>`, le suzerain de la puissance de la cellule, la validation, rien de stocké) ; « propriété des lieux » sort du niveau 3. **Niveau 1** : sièges, capitales et identités historiques déjà sourcés. **Niveau 2**, plausible, jamais sourcé : les quatre lieux d'une seigneurie, les groupes de trois, les maisons plausibles et leurs suzerains. **Niveau 3** : maître stocké, changement de maître, noms plausibles (#392).

Budget : `maitres.py` 70, constantes 6, `MODELE.md` 18, tests 125, brief 60.

## Périmètre
jeu/sim/maitres.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_maisons.py
docs/briefs/534-l-attribution-des-maitres-se-calcule-sans-alea.md

## Conditions de succès
Commandes depuis `jeu/`, sauf SC6. Tests ajoutés à la fin de `sim/tests/test_maisons.py`, noms contenant `maitre` ; leur rouge (module absent) est constaté avant l'implémentation. L'attente des tests se dérive de `lieux_depuis_monde`, `monde.maisons`, `puissances_depuis_monde` et `charger_maisons().par_puissance`, **sans appeler `sim.maitres`** ; aucun total n'est figé ; tout échantillon est non vide.

SC1 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre_monde` : sur `World.charger(0)`, chaque couple dérivé a exactement un maître, présent au registre augmenté, sans identifiant dupliqué ; la somme des lieux par maître égale le nombre de lieux dérivés et celui des `cellule.lieux` ; chaque départ tient le bourg de son siège et ses premiers rangs ; chaque capitale et siège institutionnel placé (rang 0) est tenu par sa maison ; aucun plausible ne tient un lieu hors de sa cellule ; groupes, identifiants, noms, sièges, sortes, rangs, `hors_carte` et suzerains des plausibles égalent exactement l'attente recalculée depuis les rangs libres et la couverture ; `valider_attribution` accepte le résultat et `valider_registre_maisons(monde.maisons + plausibles)` aussi. Le test vérifie que l'échantillon contient au moins une cellule de chaque sorte : sous grande maison, sous institution, non couverte, avec un dernier groupe incomplet, à moins de quatre lieux. Contre-épreuve : une attente où le suzerain vient de `maisons_depuis_monde` (maison tenante) au lieu de la puissance diffère du résultat.

SC2 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre_cas` : monde synthétique `World(...)` de quelques cellules, `monde.maisons` et `vue` fabriqués (puissances réelles 3 → `grande-3` et 11 → `institution-11`) : départ dans une cellule de 2 lieux (il les tient tous, aucun plausible) ; départ et grande maison au même siège (le départ garde ses 4 premiers rangs, la grande maison reçoit le reste, aucun plausible), aussi avec les fiches données dans l'ordre inverse ; cellule sous grande maison, sous institution et non couverte, à 7 lieux (groupes 3, 3, 1 et suzerains `grande-3`, `institution-11`, `None`) ; siège hors carte qui ne tient rien. Contre-épreuve : la même attente avec la grande maison passée avant le départ diffère.

SC3 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre_constantes` : `monkeypatch` de chaque constante (par exemple 2 et 5) change l'attribution du monde synthétique, qui égale chaque fois l'attente recalculée avec la nouvelle valeur ; `True`, `0`, `2.5` sont refusés en nommant la constante. Contre-épreuve : l'attribution sous une constante changée diffère de l'attribution nominale.

SC4 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre_contre_epreuves` : sur l'attribution du monde chargé, chacune de ces altérations fait lever `AttributionInvalide` dont le message contient le couple attendu : un lieu sans maître ; un maître inconnu ; une fiche plausible retirée ; une fiche dupliquée ; le bourg d'un départ donné à une autre maison ; un lieu libre d'une capitale donné à un plausible ; deux groupes consécutifs fusionnés (le premier plausible prend le groupe suivant, sa fiche suivante retirée) ; un lieu déplacé vers le plausible d'une autre cellule ; `maitres` vide (« échantillon vide »). Un plausible au suzerain inconnu, puis deux plausibles suzerains l'un de l'autre, font lever `PuissanceInvalide` par `valider_registre_maisons` en nommant le plausible. L'attribution intacte reste acceptée.

SC5 — `python3 -m pytest sim/tests/test_maisons.py -q -k maitre_pur` : deux appels rendent des résultats égaux, des dicts distincts, des fiches gelées ; `json.dumps(monde.to_dict(), sort_keys=True)`, `monde.maisons`, la carte et `[vars(c) for c in monde.cells.values()]` sont identiques avant et après ; un parcours AST de `engine.py`, `world.py`, `snapshot_export.py` et `service.py` n'y trouve aucun import de `sim.maitres`. Contre-épreuve : le même parcours sur le texte `from sim.maitres import attribuer_maitres` le détecte.

SC6 — Depuis la racine : `python3 -m pytest jeu -q` passe, dont `test_no_hardcoded.py`, `test_write_coverage.py` et les tests `registre` de `test_maisons.py` inchangés ; `git diff --check` réussit ; `git diff master -- jeu/sim/tests` n'a aucune ligne retirée. `python3 -c 'from pathlib import Path; t=Path("jeu/sim/MODELE.md").read_text(); assert "plausible-<cell_id>-<premier rang>" in t and "LIEUX_DE_LA_SEIGNEURIE" in t'` réussit ; contre-épreuve : le même contrôle sur le `MODELE.md` de `master` échoue.

## Hors périmètre
Stocker le maître ou les plausibles dans le monde (`World.maisons`, `Cell`, `EtatDeLieu`, `to_dict`), la photographie, `/lieu`, `/monde`, le service, Unity et toute empreinte ou référence figée. Les noms plausibles (#392), la place d'un lieu dans sa cellule (#393), le grenier des plausibles (#394), la part, le prélèvement et le dû (#395–#397). Aucun changement des tables de `data/`, de `registre_maisons.py`, de `lieux.py`, de `puissances.py` ni du tick ; aucun test existant modifié.
