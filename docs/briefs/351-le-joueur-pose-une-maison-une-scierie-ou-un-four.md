# Lot #351 — Le joueur pose une maison, une scierie ou un four sur sa parcelle
Jalon : J4 · Machine : vps · Taille prévue : 260 lignes

## But
Le joueur pose une maison, une scierie ou un four sur une parcelle de son
plan. Au tick suivant, le bâtiment entre au plan en chantier : il a pour
emprise le contour de la parcelle et un travail requis en journées.

Ce lot est le sous-lot 1 de #346, lui-même sous-lot 2 de #258. Il porte la
réponse **A** du propriétaire à #258 : sans geste, le monde et tous les tests
restent les mêmes. Aucun test existant ne change ni ne perd une ligne. Ne pas
reposer la question. Prendre des bras pour le bâtiment est le sous-lot 2 de
#346 : ici, aucune étape ne sert encore un bâtiment en chantier.

## Règle du monde
Niveau **2** : plausible, jamais sourcé. La règle découle de trois sections
de `jeu/sim/MODELE.md` : « Les intentions du joueur » (dépôt, puis
application au tick suivant), « Le plan du bourg » (le contrat de `Batiment`)
et « Le chantier et ses bras » (journées par m²).

1. **Le geste.** `recevoir_intention` accepte un quatrième type,
   `TYPE_POSER_BATIMENT = "poser_batiment"`. La liste reste fermée.
   - Champs obligatoires : `type`, `cell`, `parcelle`, `nature`. Un absent
     donne « champ manquant : X ». Sans `type`, le message reste celui
     d'aujourd'hui : « type d'intention inconnu : None ».
   - Champ facultatif : `foyers`, 1 par défaut, vérifié par `_foyers` comme
     pour la route et la parcelle.
   - Tout autre champ donne « champ inconnu : X ».
   - Les champs obligatoires de chaque type vivent dans **un seul
     dictionnaire** `{type: champs}`, lu par la boucle existante. Pas de
     ternaire imbriqué à trois branches.
2. **Les refus**, tous par `IntentionRefusee`, avant toute mise en attente,
   sans rien changer au monde, dans cet ordre :
   - `cell` : `_cellule`, même règle et même message que pour la route ;
   - `parcelle` : entier sans booléen, identifiant d'une parcelle **déjà au
     plan** de cette cellule (`monde.plans[cell].parcelles`). Sinon
     « parcelle absente du plan : <repr> ». Une parcelle en chantier convient.
     Une parcelle encore en attente (`DecoupeParcelle` non appliquée) n'est
     pas au plan : on pose au tick qui suit la découpe ;
   - un bâtiment du plan de cette cellule porte déjà cette parcelle :
     « parcelle déjà bâtie : <id> » ;
   - une `PoseBatiment` en attente porte déjà la même cellule et la même
     parcelle : « parcelle déjà promise : <id> » ;
   - `nature` : exactement l'un de `NATURES_BATIMENT = ("maison", "scierie",
     "four")`, déclaré dans `sim/intentions.py` près des types. Sinon
     « nature inconnue : <repr> ». Pas de casse ni d'espace tolérés ;
   - `foyers` : `_foyers`.
3. **Le dépôt accepté** est un `PoseBatiment(cell_id, parcelle, nature,
   foyers)` gelé, ajouté à `intentions_en_attente`. L'attente ne change ni
   les cellules, ni les plans, ni `to_dict()`.
4. **L'application.** `PoseBatiment.appliquer` relit la parcelle dans le plan
   et reconstruit le plan avec un bâtiment en chantier :
   - identifiant : max des identifiants de bâtiment (ou −1) plus 1 ;
   - `parcelle`, `nature`, `foyers` du dépôt ;
   - `emprise` : le contour de la parcelle, copié en tuples de tuples ;
   - `en_chantier=True`, `travail_fourni=0`,
     `travail_requis = travail_requis_de_batiment(emprise)`, calculé à
     l'application comme pour la route et la parcelle ;
   - rues et parcelles reprises telles quelles, par
     `Plan(rues=…, parcelles=…, batiments=…)` en mots-clés.
5. **La surface.** `aire_du_contour(points)` vit dans `sim/plan.py` (les
   sous-lots suivants de #258 la reliront). Formule du lacet, en valeur
   absolue :
   `|Σ (x_i · y_{i+1} − x_{i+1} · y_i)| × AIRE_PAR_PRODUIT_CROISE`,
   la somme bouclant du dernier point au premier.
   - `AIRE_PAR_PRODUIT_CROISE = 0.5` va dans le bloc « Plan du bourg » de
     `sim/constants.py`, avec son commentaire : c'est de la géométrie, et un
     littéral 2 est interdit dans `sim/` (`test_no_hardcoded`).
   - La valeur absolue rend la même aire quel que soit le sens du contour :
     une parcelle à gauche et une à droite de la rue ont des sens opposés.
   - Exemple : `[(5, 2), (15, 2), (15, 22), (5, 22)]` vaut 200 m².
6. **Le travail.** `travail_requis_de_batiment(emprise)` vit dans
   `sim/chantiers.py`, près des deux autres. Elle rend
   `max(1, ceil(aire_du_contour(emprise) × TRAVAIL_BATIMENT_JOURNEES_PAR_M2))`.
   - `TRAVAIL_BATIMENT_JOURNEES_PAR_M2 = 2` va dans `sim/constants.py`, près
     des constantes de route et de parcelle : fondations, murs de pisé,
     charpente et couverture d'un bâtiment simple, par m² d'emprise ;
     niveau 2, sans source.
   - Les deux fonctions relisent leur constante par le module à chaque appel.
   - La constante n'est lue que dans `chantiers.py`, jamais dans `engine.py`
     (`test_chaque_constante_du_moteur_change_le_monde` ne voit que
     `engine.py`, et le monde d'épreuve n'a pas de geste).
   - Exemple : la parcelle de 10 m × 20 m demande 400 journées. Un contour
     plat (trois points alignés) demande 1 journée.
7. **Le bâtiment porte son chantier.** `Batiment` gagne, après `emprise`,
   `en_chantier: bool = False`, `foyers`, `travail_requis` et
   `travail_fourni` (entiers, 0 par défaut).
   - Il les valide par `_chantier(self, "bâtiment")`, la fonction partagée
     de `Rue` et `Parcelle`, qui remplace l'appel actuel à `_identifiant`
     pour l'identifiant. Rien n'est recopié.
   - `nature` reste un **texte libre non vide** dans le plan : la liste
     fermée ne vaut que pour le geste. `test_lieux.py` construit
     `Batiment(nature="atelier")` sans champs de chantier : il reste valide.
   - `to_dict`, `/plan` et l'empreinte portent les quatre champs par `asdict`.
     `ClientPlan.cs` ne lit que les rues : rien ne change côté PC.
8. **Dans le tick**, un bâtiment en chantier reste à 0 journée fournie :
   `avancer_chantiers` ne le sert pas encore (sous-lot 2 de #346) et le
   reprend tel quel. Aucune cellule n'est écrite par le geste.
9. **Sans geste**, aucun bâtiment n'est posé : le monde est identique à
   l'octet près, et la suite entière reste verte sans retouche.
10. **Ce qui reste de niveau 3** : un bâtiment plus petit que sa parcelle,
    plusieurs bâtiments par parcelle, l'orientation et l'étage ; démolir,
    déplacer ou agrandir ; les matériaux ; l'effet du bâtiment achevé
    (logement, fabrication), qui viendra aux sous-lots 3 et 4 de #258.

### Ce que `MODELE.md` dit après le lot
- **« En une page »**, étape 2 : « une route, une parcelle ou un bâtiment
  entre au plan en chantier ». L'étape 3 ne change pas.
- **« Ce que le moteur ne fait pas encore »** : la phrase « Le plan peut porter
  des bâtiments, mais ils ne font rien » dit aussi qu'un bâtiment posé reste
  en chantier, aucune étape ne le servant encore.
- **« Les intentions du joueur »** :
  - la liste fermée nomme `poser_batiment` ;
  - un paragraphe donne le geste, ses champs, ses refus dans l'ordre
    (règle 2), `PoseBatiment` et son application (règle 4) ;
  - la phrase « Le dépôt et l'application de la route ou de la parcelle
    n'écrivent aucune cellule » vaut aussi pour le bâtiment.
- **« Le plan du bourg »** :
  - la puce `batiments` donne les quatre champs, leur contrat partagé avec
    la rue et la parcelle, et « nature, texte libre ; le geste n'accepte que
    maison, scierie ou four » ;
  - « Intentions y ajoute une rue ou une parcelle » devient « une rue, une
    parcelle ou un bâtiment » ;
  - dans la liste de niveau 3, la sous-chaîne **« gestes de bâtiment »
    reste**, reformulée par exemple en « gestes de bâtiment autres que la
    pose (démolir, déplacer, agrandir) » : `test_documentation_parcelle`
    l'exige ;
  - la pose, l'emprise égale à la parcelle et le coût sont de niveau 2 ;
    le reste de la règle 10 est de niveau 3.
- **« Le chantier et ses bras »** :
  - `TRAVAIL_BATIMENT_JOURNEES_PAR_M2 = 2`, ce qu'il paie, niveau 2 ;
  - la formule du requis, l'aire par le lacet et `AIRE_PAR_PRODUIT_CROISE` ;
  - « aucune étape ne sert encore un bâtiment en chantier ».
  Les mots que `test_documentation` et `test_documentation_parcelle`
  exigent restent.

## Périmètre
jeu/sim/constants.py
jeu/sim/plan.py
jeu/sim/intentions.py
jeu/sim/chantiers.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_chantiers.py

Précisions :
- `engine.py` ne change pas : sa docstring garde « journées de route puis
  de parcelle », et il ne lit aucune constante nouvelle.
- `chantiers.py` ne gagne que `travail_requis_de_batiment` (et l'import de
  `aire_du_contour`). `avancer_chantiers` ne change pas.
- `README.md` : le paragraphe de `POST /intention` donne aussi
  `{"type": "poser_batiment", "cell": X, "parcelle": 0, "nature": "maison"}`
  et ce que devient le dépôt ; la ligne de `sim/intentions.py` du tableau
  nomme aussi parcelles et bâtiments.
- `constants.py` gagne deux constantes, chacune commentée et lue dans
  `sim/` (`test_aucune_constante_terminale`).
- Les deux fichiers de test **ne perdent aucune ligne**. Ils gagnent des
  fonctions et une liste neuve. `_parcelle_reference`, `CAS_REFUS_PARCELLE`
  et `CAS_PARCELLE_INVALIDE` ne changent pas.

## Conditions de succès
Chaque contre-épreuve est jouée **dans le test** : `monkeypatch`, puis
`pytest.raises(AssertionError)` ou une comparaison qui doit différer. Les
nombres attendus se dérivent des constantes (`TAILLE_FOYER`,
`TRAVAIL_BATIMENT_JOURNEES_PAR_M2`, `AIRE_PAR_PRODUIT_CROISE`) ; un
échantillon vide échoue. Le bâtiment de référence,
`_batiment_reference(monde)`, se prépare sur un `World.charger(0)` : la
parcelle de `_parcelle_reference(monde)` y est déposée puis appliquée par
`engine._appliquer_intentions`. Il vaut `{"type": "poser_batiment",
"cell": <cellule de la route>, "parcelle": 0, "nature": "maison"}`.

**SC1 — Le dépôt refuse ce qui est mal formé, sans rien changer.**
`python3 -m pytest jeu/sim/tests/test_intentions.py -q -k refus_batiment`
Une liste `CAS_REFUS_BATIMENT` paramètre un test. Pour chaque cas :
`IntentionRefusee` avec le mot attendu, `intentions_en_attente == []` et
`to_dict()` égal à celui d'avant. Les cas, au moins :
- `cell`, `parcelle`, `nature` retirés à tour de rôle (« champ ») ; `type`
  retiré (« type ») ; un champ `extra` (« champ ») ;
- `cell` absente, `True`, `"0"`, `0.0` (« cell ») ;
- `parcelle` = 1, −1, `True`, `"0"`, 0.0, `None` (« parcelle absente ») ;
- une autre cellule, dont le plan n'a aucune parcelle (« parcelle absente ») ;
- `nature` = `"atelier"`, `"Maison"`, `" maison"`, `""`, `None`, 0
  (« nature ») ;
- `foyers` = 0, −1, `True`, 1.5, `"1"` (« foyers »).

Un second test, `test_refus_batiment_bati_promis_et_en_attente`, exige :
- une parcelle déposée mais pas appliquée : « parcelle absente du plan : 1 » ;
- deux poses sur la parcelle 0 avant le tick : la seconde est refusée
  (« parcelle déjà promise : 0 »), une seule attend ;
- après le tick, une troisième pose sur 0 : « parcelle déjà bâtie : 0 » ;
- sur le plan `_construire_plan(_donnees_plan())` de `test_lieux.py`, la
  parcelle 7 porte le bâtiment 7 : « parcelle déjà bâtie : 7 ».
Un troisième, `test_refus_batiment_ordre_et_messages`, part de
`cell=True, parcelle=True, nature="x", foyers=0` et corrige un champ à la
fois : messages exacts « cell inconnu : True », « parcelle absente du plan :
True », « nature inconnue : 'x' », « foyers invalide : … », puis l'acceptation.

Contre-épreuve : une pose en attente sur la parcelle 0 ne bloque pas la
parcelle 1, appliquée entre-temps : les deux poses sont acceptées.

**SC2 — L'aire suit le lacet, en valeur absolue.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k aire_batiment`
- `aire_du_contour` vaut 50 pour `[(0, 0), (10, 0), (0, 10)]` et pour le
  même triangle à l'envers, 200 pour le contour gauche de la parcelle de
  référence et pour le contour droit, 0 pour `[(0, 0), (1, 0), (2, 0)]`.
- `travail_requis_de_batiment` rend `max(1, ceil(aire × constante))`
  calculé par le test : 400 pour la parcelle de référence, 1 pour le contour
  plat et pour `[(0, 0), (0.1, 0), (0, 0.1)]`.
Contre-épreuve : `AIRE_PAR_PRODUIT_CROISE` mis à 1 par monkeypatch double
l'aire du triangle, et l'égalité à 50 échoue.

**SC3 — Appliqué au tick suivant, le bâtiment entre au plan en chantier.**
`python3 -m pytest jeu/sim/tests/test_intentions.py -q -k batiment_applique`
- Le dépôt rend un `PoseBatiment` gelé (`FrozenInstanceError`) ; avant
  application, `to_dict()` ne change pas.
- Après `engine._appliquer_intentions`, `plans[c].batiments` vaut
  `[Batiment(0, 0, "maison", contour, True, 1, requis, 0)]`, où `contour` est
  celui de la parcelle 0 et `requis` est calculé par le test depuis
  10 × 20 et la constante. L'emprise est un tuple de tuples. Rues et
  parcelles sont les mêmes objets qu'avant.
- Une parcelle 1 découpée à droite, puis une pose `"four"` avec `foyers: 3` :
  bâtiment 1, 3 foyers, même `requis` que le bâtiment 0.
- Sur un plan `_construire_plan(_donnees_plan())` augmenté de la route et
  d'une parcelle appliquées (identifiant 8), la pose sur 8 donne le
  bâtiment 8 ; le bâtiment 7 reste.
- `Batiment(7, 7, "atelier", triangle)` sans les champs neufs reste valide ;
  son `to_dict` porte `en_chantier: False` et trois zéros.
Contre-épreuve : la constante doublée entre le dépôt et l'application double
`requis`, et l'égalité avec la valeur nominale échoue.

**SC4 — Le bâtiment refuse un chantier incohérent.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k batiment_invalide`
Paramétré par la liste existante `CAS_PARCELLE_INVALIDE`, appliquée à
`Batiment(0, 0, "maison", [(0, 0), (1, 0), (0, 1)], …)` : chaque cas lève
`PlanInvalide` avec « bâtiment ».
Contre-épreuve : le bâtiment cohérent (`True, 1, 1, 0`) se construit.

**SC5 — Dans le tick : même geste, même monde ; sans geste, rien ne bouge.**
`python3 -m pytest jeu/sim/tests/test_intentions.py -q -k batiment_tick`
Trois `World.charger(0)` reçoivent, pour la cellule `c` de la route de
référence, le même plan construit directement : la rue achevée
`Rue(0, points, 4)` et la parcelle de référence **en chantier**,
`Parcelle(0, contour, True, 1, 4 × TAILLE_FOYER, 0)`. Deux reçoivent la même
pose avant le tick 0 ; le troisième est le témoin. On joue 3 ticks avec
`random.Random(0)` et `numero_tick=i`. On exige :
- les deux mondes à geste égaux par `to_dict()`, même état du générateur ;
- face au témoin : même état du générateur, `cells` égales, plans égaux sauf
  `plans[c].batiments` ;
- le bâtiment au plan, en chantier, à 0 journée fournie.
La parcelle restant en chantier, ce test reste vrai quand le sous-lot 2
servira les bâtiments (rien pour un bâtiment dont la parcelle est en
chantier).
Contre-épreuve : avec `engine._appliquer_intentions` remplacé par une
fonction qui ne fait rien, le monde à geste égale le témoin et l'assertion
« plans différents » échoue.

**SC6 — Rien d'existant ne bouge, et `MODELE.md` dit la règle.**
`python3 -m pytest jeu -q` reste vert, en particulier `test_foyers.py`
(`test_bit`), `test_monde.py`, `test_lieux.py`, `test_determinisme.py`,
`test_intentions.py`, `test_chantiers.py` (dont `test_documentation_parcelle`),
`test_write_coverage.py` et `test_no_hardcoded.py`.

`git diff -U0 origin/master -- jeu/sim/tests | grep -c '^-[^-]'` rend
**0** : aucune ligne de test retirée. Le codeur colle cette sortie dans la PR.

`git diff --name-only origin/master...HEAD` ne nomme que les chemins du
périmètre et ce brief.

`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k documentation_batiment` :
un test neuf lit `MODELE.md` et `README.md`, et exige :
- « Le chantier et ses bras » contient `TRAVAIL_BATIMENT_JOURNEES_PAR_M2`
  et `AIRE_PAR_PRODUIT_CROISE` ;
- « Les intentions du joueur » contient `poser_batiment` et `PoseBatiment` ;
- « Le plan du bourg » contient `poser_batiment` ;
- `README.md` contient `poser_batiment`.
Contre-épreuve, par `read_text` altéré : retirer
`TRAVAIL_BATIMENT_JOURNEES_PAR_M2`, ou `PoseBatiment`, fait échouer le
contrôle.

## Hors périmètre
- Prendre des bras pour un bâtiment : l'étape Chantiers et sa clé
  `(cell, "batiment", id)` sont le sous-lot 2 de #346.
- L'atelier qui fabrique, les artisans, la maison qui loge, les sans-logis :
  sous-lots 3 et 4 de #258.
- Une emprise plus petite que la parcelle, plusieurs bâtiments par parcelle,
  démolir, déplacer, agrandir, changer la nature ou les foyers.
- Poser sur une parcelle encore en attente.
- `engine.py`, `service.py`, Unity, `ClientPlan.cs` et les vues : aucun
  changement. `/plan` porte les bâtiments par le chemin existant.
- L'IA (jalon 5).
- Tout test existant : aucune ligne retirée ni modifiée.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
