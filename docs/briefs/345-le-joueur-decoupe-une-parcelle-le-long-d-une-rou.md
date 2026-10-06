# Lot #345 — Le joueur découpe une parcelle le long d'une route
Jalon : J4 · Machine : vps · Taille prévue : 270 lignes

## But
Le joueur découpe une parcelle rectangulaire le long d'un segment d'une route
de son plan. Elle entre au plan en chantier au tick suivant, puis prend ses
bras aux champs après les routes, journée par journée, jusqu'à son achèvement.

Ce lot est le sous-lot 1 de #258, découpé par le chef. Il porte la réponse
**A** du propriétaire : sans geste, le monde et tous les tests restent les
mêmes. Aucun test existant ne change, ni ne perd une ligne. Ne pas reposer la
question.

## Règle du monde
Niveau **2** : plausible, jamais sourcé. La règle découle de trois sections
de `jeu/sim/MODELE.md` : « Le plan du bourg » (le contrat de `Parcelle`),
« Les intentions du joueur » (le dépôt, puis l'application au tick suivant)
et « Le chantier et ses bras » (journées, `ouvriers`, ordre de service).

1. **Le geste.** `recevoir_intention` accepte un troisième type,
   `TYPE_DECOUPER_PARCELLE = "decouper_parcelle"`. La liste reste fermée :
   tout autre type est refusé comme aujourd'hui.
   - Champs obligatoires : `type`, `cell`, `rue`, `segment`, `debut_m`,
     `facade_m`, `profondeur_m`, `cote`. Un champ manquant donne
     « champ manquant : X ».
   - Champ facultatif : `foyers`, 1 par défaut. Même règle et même message
     que pour la route (entier ≥ 1, sans booléen). La vérification est
     partagée avec la route, pas recopiée.
   - Tout autre champ donne « champ inconnu : X ».
2. **Les refus**, tous par `IntentionRefusee`, avant toute mise en attente,
   sans rien changer au monde, dans cet ordre :
   - `cell` : même règle et même message que pour la route ;
   - `rue` : entier sans booléen, identifiant d'une rue **déjà au plan** de
     cette cellule (`monde.plans[cell].rues`). Sinon
     « rue absente du plan : <repr> ». Une route encore en attente n'est pas
     au plan : on ne découpe le long d'une route qu'au tick qui suit son dépôt.
     Une rue en chantier convient ;
   - `segment` : entier sans booléen, `0 ≤ segment < len(rue.points) − 1`.
     Sinon « segment hors de la rue : <repr> » ;
   - `debut_m` : nombre fini sans booléen, **≥ 0**. Le début du segment est
     une position permise : la règle « ≤ 0 refusé » de l'issue vaut pour la
     façade et la profondeur. Sinon « debut_m invalide : <repr> » ;
   - `facade_m` et `profondeur_m` : nombre fini sans booléen, **> 0**.
     Sinon « facade_m invalide : <repr> » ou « profondeur_m invalide : <repr> » ;
   - `debut_m + facade_m > longueur du segment` (distance euclidienne de ses
     deux points, sans tolérance) : « façade dépasse le segment : <debut> +
     <facade> > <longueur> ». Un segment de longueur nulle refuse donc toute
     façade, sans division par zéro (ce contrôle précède le calcul du contour) ;
   - `cote` : exactement `"gauche"` ou `"droite"`. Sinon
     « cote invalide : <repr> » ;
   - le contour calculé passe par `Parcelle(0, contour)`. Un `PlanInvalide`
     (un point devenu infini, par exemple) devient
     « parcelle invalide : <raison> ».
3. **Le contour.** Il est calculé au dépôt, d'après la rue du plan. Le
   segment va de `a = points[segment]` à `b = points[segment + 1]`, avec
   `L = dist(a, b)` et `u = (b − a) / L`. La normale gauche est
   `n = (−u_y, u_x)` : on regarde dans le sens du tracé, x vers l'est et
   y vers le nord. Pour `droite`, on prend `−n`. On note
   `d = largeur_m × DEMI_LARGEUR_PAR_LARGEUR`, où la constante vaut 0,5 :
   c'est de la géométrie, un littéral 2 est interdit dans `sim/`. Le contour
   a quatre points, dans cet ordre :
   - `c0 = a + u·debut_m + n·d` ;
   - `c1 = a + u·(debut_m + facade_m) + n·d` ;
   - `c2 = c1 + n·profondeur_m` ;
   - `c3 = c0 + n·profondeur_m`.

   La façade borde donc le bord de la chaussée, et la parcelle s'étend vers
   l'extérieur. Exemple : sur la route de référence
   `[[0, 0], [40, 0], [40, 25]]`, de 4 m de large, au segment 0, avec
   `debut 5`, `facade 10`, `profondeur 20` :
   - à gauche : `[(5, 2), (15, 2), (15, 22), (5, 22)]` ;
   - à droite : `[(5, −2), (15, −2), (15, −22), (5, −22)]`.
   Au segment 1, à gauche, `debut 0`, `facade 25`, `profondeur 10` :
   `[(38, 0), (38, 25), (28, 25), (28, 0)]`.
4. **Le dépôt accepté** est un `DecoupeParcelle(cell_id, contour, facade_m,
   profondeur_m, foyers)` gelé, au contour en tuples. L'attente ne change ni
   les cellules, ni les plans, ni `to_dict()`.
   - `DecoupeParcelle.appliquer` reconstruit le plan avec une parcelle en
     chantier : son identifiant vaut max des identifiants de parcelle (ou −1)
     plus 1, avec `en_chantier=True`, `foyers`, `travail_fourni=0`, et
     `travail_requis = travail_requis_de_parcelle(facade_m, profondeur_m)`,
     calculé à l'application comme pour la route.
   - Les rues et les bâtiments du plan sont repris tels quels.
5. **Le travail.** `travail_requis_de_parcelle(facade_m, profondeur_m)` vit
   dans `sim/chantiers.py`. Elle rend
   `max(1, ceil(facade_m × profondeur_m × TRAVAIL_PARCELLE_JOURNEES_PAR_M2))`.
   - La surface est le produit façade × profondeur, exact pour le rectangle,
     et non une aire recalculée sur les points.
   - La constante vaut **0,1** et va dans `sim/constants.py` : arpentage,
     bornage, défrichage et clôture d'un lot à bâtir, niveau 2, sans source.
   - La fonction relit la constante par le module à chaque appel.
   - Exemple : 10 m × 20 m demandent 20 journées.
6. **La parcelle porte son chantier.** `Parcelle` gagne, après `contour`,
   `en_chantier: bool = False`, `foyers`, `travail_requis` et
   `travail_fourni` (entiers, 0 par défaut).
   - Elle les valide **exactement comme `Rue`** : `en_chantier` booléen ;
     entiers ≥ 0, sans booléen ; fourni ≤ requis ;
     `en_chantier == (fourni < requis)` ; au moins un foyer en chantier.
   - Les messages commencent par `parcelle.` au lieu de `rue.`.
   - La vérification est une fonction partagée par les deux classes : on ne
     la recopie pas.
   - Une parcelle d'avant (0, 0, 0, pas en chantier) reste valide :
     `_donnees_plan` de `test_lieux.py` passe sans changement.
   - `to_dict`, `/plan` et l'empreinte du monde portent les quatre champs
     par `asdict`. `ClientPlan.cs` ne lit que les rues (vérifié par le
     chef) : rien ne change côté PC.
7. **L'étape Chantiers** (`chantiers.avancer_chantiers`) suit la même règle
   qu'aujourd'hui. Après les rues en chantier, par identifiant, elle sert les
   **parcelles** en chantier, par identifiant, avec les paysans qui restent.
   - Chaque parcelle reçoit `min(foyers × TAILLE_FOYER, requis − fourni,
     paysans disponibles)` personnes. Elles passent de `paysans` à
     `ouvriers`, et `travail_fourni` augmente d'autant. La parcelle s'achève
     au requis, et aucune journée ne se crée ni ne se perd.
   - Une rue passe toujours avant une parcelle, quels que soient leurs
     identifiants.
   - Le retour garde la clé `(cell_id, identifiant)` pour une rue (les tests
     existants la lisent). Une parcelle prend la clé
     `(cell_id, "parcelle", identifiant)`.
   - Le plan est reconstruit seulement si une rue **ou** une parcelle a reçu
     du travail, avec `Plan(rues=…, parcelles=…, batiments=…)` en mots-clés :
     `test_compte_journees_et_retour` remplace `chantiers.Plan` par une
     fonction qui n'accepte que des mots-clés.
   - Un seul corps sert les deux listes (par exemple `_servir(element,
     metiers)`), pas deux boucles recopiées.
   - Métiers non calculés : personne ne part. Sans chantier ni ouvrier :
     rien n'est écrit. Aucun aléa, aucun état caché.
8. **Sans geste**, aucune parcelle n'est en chantier. Le monde est donc
   identique à l'octet près, et la suite entière reste verte sans retouche.
9. **Ce qui reste de niveau 3** :
   - deux parcelles qui se chevauchent, une parcelle qui coupe une autre rue
     ou sort du bourg ;
   - la propriété, le prix et le cadastre ;
   - une parcelle le long d'une route encore en attente ;
   - les matériaux ;
   - l'effet de la parcelle achevée : le bâtiment est le sous-lot suivant
     de #258.

### Ce que `MODELE.md` dit après le lot
- **« En une page »** :
  - étape 2 : « une route ou une parcelle entre au plan en chantier » ;
  - étape 3 : « … puis les rues, et après elles les parcelles, prennent
    leurs bras et comptent les journées fournies ».
- **« Les intentions du joueur »** :
  - la liste fermée nomme `decouper_parcelle` ;
  - un paragraphe donne le geste, ses champs, ses refus (règle 2), le contour
    (règle 3, avec l'exemple), `DecoupeParcelle` et son application
    (règle 4) ;
  - la phrase sur la route qui n'écrit aucune cellule vaut aussi pour la
    parcelle.
- **« Le plan du bourg »** :
  - la puce `parcelles` donne les quatre champs et leur contrat ;
  - « Intentions y ajoute une rue » devient « une rue ou une parcelle » ;
  - dans la liste de niveau 3, « gestes de parcelle et de bâtiment » devient
    « gestes de bâtiment » ;
  - le découpage d'une parcelle, son coût et son achèvement sont de niveau 2,
    et ses chevauchements de niveau 3.
- **« Le chantier et ses bras »** :
  - `TRAVAIL_PARCELLE_JOURNEES_PAR_M2 = 0,1`, ce qu'il paie et le niveau 2 ;
  - la formule de la parcelle ;
  - l'ordre : les rues par identifiant, puis les parcelles par identifiant.
  Les mots que `test_documentation` exige restent.
- **« Ce que le moteur ne fait pas encore »**, à « répartir le travail » :
  le chantier, des rues et des parcelles.

## Périmètre
jeu/sim/constants.py
jeu/sim/plan.py
jeu/sim/intentions.py
jeu/sim/chantiers.py
jeu/sim/engine.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_chantiers.py

Précisions :
- `engine.py` : seule la ligne 3 de la docstring de `tick()` change
  (« journées de route » devient « journées de route puis de parcelle »).
  `engine.py` ne lit aucune constante nouvelle.
- `README.md` : le paragraphe de `POST /intention` donne aussi
  `{"type": "decouper_parcelle", "cell": X, "rue": 0, "segment": 0,
  "debut_m": 5, "facade_m": 10, "profondeur_m": 20, "cote": "gauche"}`, et ce
  que devient le dépôt.
- `constants.py` gagne `TRAVAIL_PARCELLE_JOURNEES_PAR_M2 = 0.1` près de la
  constante de route, et `DEMI_LARGEUR_PAR_LARGEUR = 0.5` dans le bloc
  « Plan du bourg ». Chacune a son commentaire et un lecteur dans `sim/`
  (`test_aucune_constante_terminale`).
- Les deux fichiers de test **ne perdent aucune ligne**. Ils gagnent des
  fonctions et des listes neuves. `_route_reference` et `CAS_REFUS_ROUTE`
  ne changent pas.

## Conditions de succès
Chaque contre-épreuve est jouée **dans le test** : `monkeypatch`, puis
`pytest.raises(AssertionError)` ou une comparaison qui doit différer. Les
nombres attendus se dérivent des constantes (`TAILLE_FOYER`,
`TRAVAIL_PARCELLE_JOURNEES_PAR_M2`, `DEMI_LARGEUR_PAR_LARGEUR`) et du monde
chargé ; un échantillon vide échoue. La parcelle de référence des tests,
`_parcelle_reference(monde)`, est déposée sur un `World.charger(0)` où la
route `_route_reference` a été déposée puis appliquée par
`engine._appliquer_intentions`. Elle vaut `{"type": "decouper_parcelle",
"cell": <cellule de la route>, "rue": 0, "segment": 0, "debut_m": 5,
"facade_m": 10, "profondeur_m": 20, "cote": "gauche"}`.

**SC1 — Le dépôt refuse ce qui est mal formé, sans rien changer.**
`python3 -m pytest jeu/sim/tests/test_intentions.py -q -k refus_parcelle`
Une liste `CAS_REFUS_PARCELLE` paramètre un test. Pour chaque cas, on exige
`IntentionRefusee` avec le mot attendu, `intentions_en_attente == []` et
`to_dict()` égal à celui d'avant. Les cas, au moins :
- chaque champ obligatoire retiré à tour de rôle (« champ ») ;
- un champ `extra` (« champ ») ;
- `cell` absente ;
- `foyers` = 0, −1, `True`, 1.5, `"1"` ;
- `rue` = 1, −1, `True`, `"0"` ;
- la rue 0 d'une autre cellule, où il n'y a pas de rue (« rue ») ;
- `segment` = 2, −1, `True`, 0.0 ;
- `debut_m` = −1, NaN, inf, `True`, `"5"` ;
- `facade_m` = 0, −1, NaN, `True` ;
- `profondeur_m` = 0, −1, inf, `None` ;
- `facade_m` = 36 avec `debut_m` = 5, puis `debut_m` = 40 avec
  `facade_m` = 1 (« dépasse ») ;
- `cote` = `"haut"`, `"Gauche"`, `None` ;
- `debut_m` = 1e308 avec `facade_m` = 1e308 : la façade dépasse.

Un test à part dépose la route et la parcelle sur un monde neuf, **avant**
tout tick : la parcelle est refusée (« rue absente du plan ») et seule la
route attend.

Contre-épreuve : avec `segment` = 1 (le second segment, long de 25 m),
`facade_m` = 25 et `debut_m` = 0 sont acceptés. Avec le même cas, le contrôle
« dépasse » appliqué à 25,000001 doit lever. Le test affiche le nombre de cas
refusés.

**SC2 — Le contour borde le segment, du bon côté, à la demi-largeur.**
`python3 -m pytest jeu/sim/tests/test_intentions.py -q -k contour_parcelle`
On dépose trois parcelles et on relit `DecoupeParcelle.contour` :
- gauche, segment 0 : exactement `((5, 2), (15, 2), (15, 22), (5, 22))` ;
- droite, segment 0 : les mêmes y, de signe opposé ;
- gauche, segment 1, `debut 0`, `facade 25`, `profondeur 10` :
  `((38, 0), (38, 25), (28, 25), (28, 0))`.

Les 2 sont écrits `4 × k.DEMI_LARGEUR_PAR_LARGEUR`. Le dépôt rend un objet
gelé (`FrozenInstanceError`), et modifier le dictionnaire déposé après coup
ne change pas son contour.

Contre-épreuve : `DEMI_LARGEUR_PAR_LARGEUR` mis à 0 par monkeypatch donne
une façade sur l'axe, et l'égalité avec le contour attendu (calculé avant le
monkeypatch) échoue.

**SC3 — Appliquée au tick suivant, la parcelle entre au plan en chantier.**
`python3 -m pytest jeu/sim/tests/test_intentions.py -q -k parcelle_appliquee`
- Avant application, `to_dict()` ne change pas.
- Après `engine._appliquer_intentions`, `plans[c].parcelles` vaut
  `[Parcelle(0, contour, True, 1, requis, 0)]`, avec
  `requis = max(1, ceil(10 × 20 × k.TRAVAIL_PARCELLE_JOURNEES_PAR_M2))`
  calculé par le test. Les rues sont celles d'avant, à l'identique.
- Une seconde parcelle, avec `foyers: 3`, prend l'identifiant 1 et 3 foyers.
- Sur un plan `_construire_plan(_donnees_plan())`, dont la parcelle est la 7,
  augmenté de la route appliquée, la nouvelle parcelle prend l'identifiant 8.
  Le bâtiment 7 reste.
- `Parcelle(0, triangle)` sans les champs neufs reste valide, et son
  `to_dict` porte `en_chantier: False` et trois zéros.

Contre-épreuve : la constante doublée entre le dépôt et l'application double
`requis` (à l'arrondi supérieur près), et l'égalité avec la valeur nominale
échoue.

**SC4 — La parcelle refuse un chantier incohérent.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k parcelle_invalide`
Les mêmes cas que `test_rue_invalide`, appliqués à
`Parcelle(0, [(0, 0), (1, 0), (0, 1)], …)` : fourni > requis ; en chantier
avec fourni == requis ; pas en chantier avec fourni < requis ; en chantier
sans foyer ; un champ booléen, négatif, flottant ou texte. Chacun lève
`PlanInvalide` avec « parcelle ».

Contre-épreuve : la parcelle cohérente (`True, 1, 1, 0`) se construit.

**SC5 — Le chantier sert les rues, puis les parcelles, à la journée près.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k parcelle_compte`
Sur `World.charger(0)`, sans tick, on appelle seulement
`chantiers.avancer_chantiers`.
- **Le compte.** La cellule de `_route_reference` reçoit un plan qui n'a
  qu'une parcelle construite directement : `requis = 3 × TAILLE_FOYER − 2`,
  1 foyer. Les appels rendent `{(c, "parcelle", 0): attendu}` avec 5, 5, puis
  3. La somme égale `travail_fourni`, qui égale `requis`. À chaque appel, les
  `ouvriers` égalent l'envoi, et `paysans + ouvriers` comme la population
  restent ceux du départ. Au quatrième appel, le retour est `{}` et les
  ouvriers sont revenus aux champs.
- **L'ordre.** Dans la cellule qui a le moins de paysans (au moins un), on a
  la rue 5 et la parcelle 0, chacune demandant plus de foyers que la
  cellule n'a de paysans. La rue reçoit tous les paysans et la parcelle 0,
  malgré son identifiant plus petit. Le retour vaut
  `{(c, 5): paysans, (c, "parcelle", 0): 0}`.
- **Métiers non calculés** : personne ne part, `to_dict()` est inchangé et le
  plan est le même objet.

Contre-épreuve : avec `chantiers.Plan` remplacé par une fonction qui rend le
plan d'origine, `travail_fourni` de la parcelle reste 0 et l'égalité au
compte attendu échoue.

**SC6 — Dans le tick : même geste, même monde ; sans geste, rien ne bouge.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k parcelle_tick`
Trois `World.charger(0)` ont chacun le même plan pour la cellule `c` de
`_route_reference` : la route de référence, achevée (`Rue(0, points, 4)`,
champs par défaut). Deux d'entre eux reçoivent, avant le tick 0, la même
parcelle de 10 m × 13 m, soit 13 journées : le test vérifie, par la formule,
que `requis % TAILLE_FOYER != 0` et `requis > 2 × TAILLE_FOYER`. Le
troisième est le témoin, sans geste. On joue 6 ticks, avec
`random.Random(0)` et `numero_tick=i`. Une enveloppe de
`engine._apply_production` relève les `ouvriers` de `c` à la récolte. On
exige :
- relevés `[5, 5, requis − 10, 0, 0, 0]`, la parcelle achevée
  (`travail_fourni == travail_requis`, plus en chantier) ;
- les deux mondes à geste égaux par `to_dict()` à l'octet près, avec le
  même état du générateur ;
- face au témoin : même état du générateur, toute autre cellule égale, la
  cellule `c` égale sa clé `foyers` exceptée, et les plans égaux sauf
  `plans[c].parcelles`.

Contre-épreuve : avec `engine._avancer_chantiers` remplacé par une fonction
qui ne fait rien, `travail_fourni` reste 0 et l'assertion d'achèvement
échoue.

**SC7 — Rien d'existant ne bouge, et `MODELE.md` dit la règle.**
`python3 -m pytest jeu -q` reste vert, en particulier :
- `test_foyers.py` (`test_bit`, 365 ticks à l'octet) ;
- `test_monde.py` (ordre du tick, `/plan`) ;
- `test_lieux.py` (plans), `test_determinisme.py`, `test_intentions.py`,
  `test_chantiers.py` ;
- `test_write_coverage.py` et `test_no_hardcoded.py`.

`git diff -U0 origin/master -- jeu/sim/tests | grep -c '^-[^-]'` rend
**0** : aucune ligne de test retirée. Le codeur colle cette sortie dans la PR.

`git diff --name-only origin/master...HEAD` ne nomme que les chemins du
périmètre et ce brief.

`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k documentation_parcelle` :
un test neuf lit `MODELE.md`, `README.md` et `engine.py`, et exige :
- la section « Le chantier et ses bras » contient
  `TRAVAIL_PARCELLE_JOURNEES_PAR_M2` ;
- « Les intentions du joueur » contient `decouper_parcelle` et
  `DecoupeParcelle` ;
- « Le plan du bourg » ne contient plus « gestes de parcelle » ;
- `README.md` contient `decouper_parcelle`.

Contre-épreuve, par `read_text` altéré : retirer la constante de la section,
ou y remettre « gestes de parcelle », fait échouer le contrôle.

## Hors périmètre
- Poser un bâtiment sur une parcelle, l'atelier, la maison, le logement :
  ce sont les sous-lots suivants de #258.
- Les chevauchements de parcelles, une parcelle qui coupe une rue ou sort du
  bourg, la propriété, le prix, le cadastre : niveau 3, non vérifiés.
- Modifier, annuler ou déplacer une parcelle, ou changer ses foyers.
- Découper le long d'une route encore en attente.
- Relever `BRAS_AUX_CHAMPS_PAR_KM2` ou `TRAVAIL_ROUTE_JOURNEES_PAR_M2`, et
  toucher à la récolte ou à l'amorçage.
- Unity, `ClientPlan.cs`, le traceur de route, `service.py` et les vues :
  aucun changement. `/plan` porte les parcelles par le chemin existant.
- L'IA (jalon 5).
- Tout test existant : aucune ligne retirée ni modifiée.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
