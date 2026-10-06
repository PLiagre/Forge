# Lot #352 — Le chantier bâtit la maison, la scierie ou le four
Jalon : J4 · Machine : vps · Taille prévue : 230 lignes

## But
Le bâtiment posé par le joueur prend des bras aux champs, jour après jour,
une fois sa parcelle prête, jusqu'à être bâti. Achevé, il ne fait encore rien.

Ce lot est le sous-lot 2 de #346, lui-même sous-lot 2 de #258. Il porte la
réponse **A** du propriétaire à #258 : sans geste, le monde et tous les tests
restent les mêmes. Aucun test existant ne change ni ne perd une ligne. Ne pas
reposer la question. Le geste `poser_batiment`, `Batiment` et son travail
requis existent déjà (#351, sur la base).

## Règle du monde
Niveau **2** : plausible, jamais sourcé. La règle prolonge la section
« Le chantier et ses bras » de `jeu/sim/MODELE.md`, avec « Le plan du bourg »
(contrat de `Batiment`) et « En une page » (étape 3).

1. **L'ordre.** Dans chaque cellule, par `cell_id`, l'étape Chantiers fait
   revenir tous les ouvriers aux champs, puis sert les rues en chantier par
   identifiant, puis les parcelles en chantier par identifiant, puis les
   **bâtiments en chantier par identifiant**. Chacun prend, comme aujourd'hui
   par `_servir`, le minimum des paysans restants, de `foyers × TAILLE_FOYER`
   et du travail restant ; une personne envoyée vaut une journée fournie.
   Le bâtiment s'achève au requis : `en_chantier` devient faux.
2. **La parcelle d'abord.** Un bâtiment dont la parcelle est **en chantier
   au début de l'étape** ne prend aucun bras ce tick. On lit l'état de la
   parcelle dans le plan tel qu'il était avant l'étape : une parcelle achevée
   pendant ce tick laisse son bâtiment attendre le tick suivant, comme les
   ouvriers du jour de l'achèvement ne reviennent que le lendemain. Le plan
   garantit déjà que la parcelle existe (`PlanInvalide` sinon).
3. **Le retour.** `avancer_chantiers` rend une entrée par bâtiment en
   chantier, de clé `(cell_id, "batiment", identifiant)`, même pour zéro
   bras, même pour un bâtiment qui attend sa parcelle. Les clés des rues
   `(cell_id, identifiant)` et des parcelles `(cell_id, "parcelle",
   identifiant)` ne changent pas. Un bâtiment achevé n'a pas d'entrée.
4. **Le plan** est reconstruit, par `Plan(rues=…, parcelles=…,
   batiments=…)` en mots-clés, seulement si une rue, une parcelle ou un
   bâtiment reçoit du travail. Sinon c'est le même objet. Les métiers ne
   sont écrits que s'ils changent. Aucun aléa, aucun état caché.
5. **Le bâtiment achevé ne fait rien** : ni logement, ni fabrication, ni
   bras. Aucune autre étape ne lit le plan. Ce sont les sous-lots 3 et 4
   de #258.
6. **Sans geste**, aucun plan n'a de bâtiment en chantier : l'étape fait
   exactement ce qu'elle fait aujourd'hui, et le monde reste le même à
   l'octet près.
7. **Niveau 3, non simulés** : ordre de priorité choisi par le joueur,
   matériaux et leur transport, saison, artisans spécialisés (maçons,
   charpentiers), coût de l'achèvement au-delà des journées.

### Ce que `MODELE.md` dit après le lot
- **« En une page »**, étape 3 : les ouvriers reviennent aux champs, puis
  les rues, les parcelles et enfin les bâtiments dont la parcelle est prête
  prennent leurs bras. `_avancer_chantiers` reste nommé.
- **« Ce que le moteur ne fait pas encore »** : « un bâtiment posé reste en
  chantier, aucune étape ne le servant encore » devient : un bâtiment se bâtit
  à la journée, mais achevé il ne fait rien. La phrase « Le plan peut porter
  des bâtiments, mais ils ne font rien » peut rester.
- **« Le plan du bourg »** : « Chantiers compte le travail des rues et
  parcelles » nomme aussi les bâtiments. L'achèvement d'un bâtiment est de
  niveau 2 ; son effet reste de niveau 3. La sous-chaîne « gestes de
  bâtiment » **reste** (`test_documentation_parcelle`).
- **« Le chantier et ses bras »** :
  - la phrase « Aucune étape ne sert encore un bâtiment en chantier : il
    garde zéro journée fournie… » est **retirée** et remplacée par les
    règles 1 à 5 ;
  - le paragraphe de `sim/chantiers.py` donne l'ordre rues → parcelles →
    bâtiments, l'attente de la parcelle (règle 2), la clé
    `(cell_id, "batiment", identifiant)` et la reconstruction (règle 4) ;
  - les mots qu'exigent `test_documentation`, `test_documentation_parcelle`
    et `test_documentation_batiment` restent.

## Périmètre
jeu/sim/chantiers.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_chantiers.py

Précisions :
- `chantiers.py` : la boucle `for nom, cle in (("rues", ()), ("parcelles",
  ("parcelle",)))` gagne `("batiments", ("batiment",))` ; avant la boucle,
  l'ensemble des identifiants de parcelles en chantier se lit dans `plan`
  (l'objet d'avant l'étape) ; un bâtiment dont la parcelle y figure reçoit
  0 sans passer par `_servir`. La reconstruction passe
  `batiments=listes["batiments"]`. La docstring du module et celle de
  `avancer_chantiers` nomment les bâtiments. Aucune constante nouvelle.
- `engine.py` : seule la ligne de l'étape 3 de la docstring de `tick` change,
  en « retour aux champs puis journées de route puis de parcelle puis de
  bâtiment ». La sous-chaîne « journées de route puis de parcelle » reste
  (`test_documentation_parcelle`). Rien d'autre.
- `README.md` : « le bâtiment reste en chantier, aucune étape ne lui
  fournissant encore de journées » devient : il prend ses bras après les
  routes et les parcelles, une fois sa parcelle achevée, et achevé ne fait
  rien. La ligne de `sim/chantiers.py` du tableau nomme parcelles et
  bâtiments ; « il part vide et n'a aucun effet sur le tick » est corrigé
  (le chantier prend des bras).
- `test_chantiers.py` **ne perd aucune ligne** ; il gagne des fonctions.
  `test_intentions.py` n'est pas touché : `test_batiment_tick_rejeu_et_temoin`
  garde sa parcelle en chantier, donc son bâtiment reste à 0 et le test
  reste vrai sans retouche.
- `ClientPlan.cs`, `service.py` et `/plan` : rien. `/plan` porte déjà
  `travail_fourni` et `en_chantier` par `asdict`.

## Conditions de succès
Chaque contre-épreuve est jouée **dans le test** : `monkeypatch`, puis
`pytest.raises(AssertionError)` ou une comparaison qui doit différer. Les
nombres attendus se dérivent de `TAILLE_FOYER`, des paysans lus et de
`travail_requis_de_batiment` ; un échantillon vide échoue. Le triangle
`[(0, 0), (1, 0), (0, 1)]` sert de contour quand la géométrie importe peu.
Une parcelle achevée s'écrit `Parcelle(i, triangle)` (défauts) ; une
parcelle en chantier `Parcelle(i, triangle, True, 1, R, 0)`.

**SC1 — Rues, puis parcelles, puis bâtiments, par identifiant.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k batiment_priorite`
Sur la cellule qui a le moins de paysans non nuls (même choix que
`test_compte_priorite_et_metiers_non_calcules`), `paysans` lus,
`requis = paysans + TAILLE_FOYER`, `foyers = paysans + 1` partout :
- rue 5 en chantier, parcelle 0 en chantier, bâtiments 1 et 0 en chantier
  sur deux parcelles achevées 1 et 2 : le retour vaut exactement
  `{(c, 5): paysans, (c, "parcelle", 0): 0, (c, "batiment", 0): 0,
  (c, "batiment", 1): 0}` ;
- sans rue ni parcelle en chantier (parcelles 1 et 2 achevées, bâtiments 1
  et 0) : `{(c, "batiment", 0): paysans, (c, "batiment", 1): 0}` ; le
  bâtiment 0 a `travail_fourni == paysans`, le 1 zéro ; la somme des
  métiers égale la population ;
- métiers non calculés (`habitants_par_metier = None`) : toutes les entrées
  à 0, `to_dict()` inchangé et `monde.plans[c] is plan`.
Contre-épreuve : le premier plan, avec la rue 5 achevée
(`Rue(5, …)` aux défauts), donne les `paysans` à la parcelle 0 ; l'égalité
avec le premier retour échoue. Les bâtiments passés à `Plan` dans l'ordre
1, 0 prouvent le tri par identifiant.

**SC2 — Un bâtiment ne prend aucun bras tant que sa parcelle est en chantier.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k batiment_attend_sa_parcelle`
Sur la cellule `c` de `_route_reference`, plan : parcelle 0 en chantier
avec `R = TAILLE_FOYER` (un tick suffit), bâtiment 0 sur la parcelle 0,
`Batiment(0, 0, "four", triangle, True, 1, 3 * TAILLE_FOYER, 0)`.
- 1er appel : `{(c, "parcelle", 0): TAILLE_FOYER, (c, "batiment", 0): 0}`,
  la parcelle est achevée, le bâtiment à 0 alors qu'il reste des paysans ;
- 2e appel : `{(c, "batiment", 0): TAILLE_FOYER}` ;
- sur un monde neuf, le même plan augmenté d'une parcelle 1 achevée et
  d'un bâtiment 1 en chantier sur elle (mêmes champs) : le 1er appel rend
  `{(c, "parcelle", 0): T, (c, "batiment", 0): 0, (c, "batiment", 1): T}`
  (`T = TAILLE_FOYER`) : l'attente vaut pour la parcelle du bâtiment, pas
  pour la cellule.
Contre-épreuve : le même plan dont la parcelle 0 est achevée dès le départ
donne `TAILLE_FOYER` au bâtiment 0 au 1er appel ; l'assertion « 0 au 1er
appel » échoue sur ce plan.

**SC3 — Le bâtiment compte ses journées, s'achève et rend les bras.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k batiment_compte`
Sur `c`, parcelle 0 achevée, bâtiment 0 en chantier, 1 foyer,
`requis = 3 * TAILLE_FOYER - 2` (non multiple, vérifié). Trois appels
rendent `{(c, "batiment", 0): a}` pour `a` = `TAILLE_FOYER`,
`TAILLE_FOYER`, `requis - 2 * TAILLE_FOYER` ; après chacun,
`_controler_compte` (bâtiment à la place de la rue) passe. Puis :
- 4e appel : `{}`, le bâtiment achevé (`en_chantier` faux,
  `travail_fourni == travail_requis`), plus d'ouvrier ;
- 5e appel, avec `chantiers.ecrire_habitants_par_metier` et `chantiers.Plan`
  remplacés par des `pytest.fail` : `{}` et `monde.plans[c] is plan`.
Contre-épreuve : `chantiers.Plan` remplacé par `lambda **kw: plan` (le plan
de départ) laisse `travail_fourni` à 0, et l'égalité à `TAILLE_FOYER`
échoue.

**SC4 — Au tick : mêmes gestes, même monde ; achevé, rien ne bouge.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k batiment_tick`
Trois `World.charger(0)` reçoivent sur `c` le même plan construit
directement : `Rue(0, points, 4)` achevée et la parcelle de référence
achevée, `Parcelle(0, contour)`, `contour` lu comme dans
`test_batiment_tick_rejeu_et_temoin`. Deux reçoivent avant le tick 0 la
même pose `_batiment_reference | {"foyers": F}`, avec
`F = ceil(requis / (3 * TAILLE_FOYER))`, `requis =
travail_requis_de_batiment(contour)` et l'assertion `F * TAILLE_FOYER ≤`
paysans de `c` ; le troisième est le témoin. Cinq ticks, `random.Random(0)`,
`numero_tick=i`, ouvriers de `c` relevés à `_apply_production`. On exige :
- les deux mondes à geste égaux par `to_dict()`, même état du générateur
  pour les trois ;
- relevés `[F·T, F·T, requis − 2·F·T, 0, 0]` (`T = TAILLE_FOYER`), bâtiment
  achevé à `requis` ;
- face au témoin, `_cellules_identiques_sauf_metiers` passe et les plans
  ne diffèrent que par `plans[c].batiments`.
Puis le bâtiment achevé : deux mondes, l'un avec le plan ci-dessus plus
`Batiment(0, 0, "maison", contour, False, 1, requis, requis)`, l'autre sans ;
trois ticks ; `cells` **égales en entier** (métiers compris), même état du
générateur, bâtiment inchangé.
Contre-épreuves :
- `engine._avancer_chantiers` remplacé par une fonction qui ne fait rien :
  le bâtiment reste à 0 et l'assertion « achevé » échoue ;
- le bâtiment de la comparaison « achevé » mis en chantier
  (`True, 1, requis, 0`) : les `cells` diffèrent et l'égalité échoue.

**SC5 — Rien d'existant ne bouge, et `MODELE.md` dit l'ordre et la règle.**
`python3 -m pytest jeu -q` reste vert, en particulier `test_chantiers.py`,
`test_intentions.py` (dont `test_batiment_tick_rejeu_et_temoin`),
`test_foyers.py`, `test_monde.py`, `test_lieux.py`, `test_determinisme.py`,
`test_write_coverage.py` et `test_no_hardcoded.py`.

`git diff -U0 origin/master -- jeu/sim/tests | grep -c '^-[^-]'` rend
**0** : aucune ligne de test retirée. Le codeur colle cette sortie dans la PR.

`git diff --name-only origin/master...HEAD` ne nomme que les chemins du
périmètre et ce brief.

`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k documentation_chantier_batiment` :
un test neuf lit `MODELE.md`, `README.md` et `engine.py`, et exige :
- « Le chantier et ses bras » contient `"batiment"` (la clé) et ne contient
  plus « Aucune étape ne sert encore un bâtiment » ;
- « Ce que le moteur ne fait pas encore » ne contient plus « aucune étape ne
  le servant encore » ;
- « En une page » contient « bâtiments » ;
- `engine.py` contient « journées de route puis de parcelle puis de
  bâtiment » ;
- `README.md` ne contient plus « aucune étape ne lui fournissant encore ».
Contre-épreuve, par `read_text` altéré : remettre « Aucune étape ne sert
encore un bâtiment » dans `MODELE.md`, ou retirer « puis de bâtiment » de
`engine.py`, fait échouer le contrôle.

## Hors périmètre
- L'effet du bâtiment achevé : logement de la maison, atelier qui fabrique,
  artisans, sans-logis (sous-lots 3 et 4 de #258).
- Une priorité choisie par le joueur entre chantiers, l'arrêt ou l'abandon
  d'un chantier, les matériaux.
- Le geste `poser_batiment` et ses refus, `Batiment`, le travail requis :
  livrés par #351, inchangés.
- `service.py`, `/plan`, `/lieu`, Unity, `ClientPlan.cs` et les vues.
- L'IA (jalon 5).
- Tout test existant : aucune ligne retirée ni modifiée ;
  `test_intentions.py` n'est pas touché.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
