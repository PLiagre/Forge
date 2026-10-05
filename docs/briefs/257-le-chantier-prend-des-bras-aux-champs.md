# Lot #257 — Le chantier prend des bras aux champs
Jalon : J4 · Machine : vps · Taille prévue : 280 lignes

## But
Une route tracée par le joueur devient un chantier qui demande des journées
de travail. À chaque tick, le nombre de foyers paysans que le joueur a choisi
quitte les champs pour le chantier. Le travail fourni se compte à la journée
près, sans se créer ni se perdre. Les ouvriers reviennent aux champs quand la
route est achevée, et plus il y a de bras au chantier, moins la cellule
récolte.

Décision du propriétaire sur l'issue #257 : **A**, à suivre telle quelle.
- On réécrit les trois tests qui disent « une route ne touche aucune
  cellule », en plus strict : seule la cellule du chantier change, et dans
  cette cellule, seuls ses métiers changent.
- Le joueur dit dans son geste combien de foyers il envoie (un par défaut).
- `BRAS_AUX_CHAMPS_PAR_KM2 = 0,1` ne change pas.

Ne pas reposer la question.

## Règle du monde
Niveau **2** : plausible, jamais sourcé. La règle découle de quatre sections
de `jeu/sim/MODELE.md` : « Les foyers par métier » (le facteur de bras de
#256, que ce lot ne touche pas), « Le plan du bourg », « Les intentions du
joueur » et « La base de temps » (un tick vaut un jour).

1. **Le geste.** `tracer_route` accepte un champ facultatif `foyers`. C'est
   un entier ≥ 1, et un booléen est refusé. S'il est absent, il vaut 1. Une
   valeur invalide lève `IntentionRefusee("foyers invalide : attendu un
   entier ≥ 1, reçu <repr>")` sans rien mettre en attente. Les quatre champs
   obligatoires et le refus de tout autre champ ne changent pas. Il n'y a pas
   de borne haute : le chantier ne prend que les paysans qui existent.
   `TraceRoute` gagne `foyers`.
2. **Le travail demandé.** La longueur d'une route est la somme des
   longueurs euclidiennes de ses segments, en mètres. Le travail requis vaut
   `max(1, ceil(longueur × largeur_m × TRAVAIL_ROUTE_JOURNEES_PAR_M2))`
   journées. Une journée, c'est une personne qui travaille pendant un tick.
   La constante va dans `sim/constants.py`, valeur **0,5** (déblai,
   nivellement et fossés d'une route en terre battue ; niveau 2, sans
   source). La route de référence des tests, 65 m sur 4 m, demande 130
   journées : un foyer de 5 la finit en 26 jours.
   - Le calcul vit dans `sim/chantiers.py`, fonction
     `travail_requis_de_route(points, largeur_m)`, qui relit la constante
     par le module à chaque appel.
   - `TraceRoute.appliquer` l'appelle pour créer la rue.
3. **La rue porte son chantier.** `Rue` gagne trois champs entiers, tous à 0
   par défaut : `foyers`, `travail_requis` et `travail_fourni`. Ils sont
   refusés par `PlanInvalide` s'ils sont négatifs, booléens ou non entiers.
   Sont aussi refusés `travail_fourni > travail_requis`, une rue en chantier
   sans foyer, et une rue dont `en_chantier` ne vaut pas exactement
   `travail_fourni < travail_requis`. Une rue ancienne (0, 0, 0, pas en
   chantier) reste valide. `to_dict`, `/plan` et l'empreinte du monde
   portent les trois champs. Le client Unity `ClientPlan` ignore les clés
   qu'il ne lit pas (vérifié par le chef) : rien ne change côté PC.
4. **L'étape Chantiers.** C'est `_avancer_chantiers(world)` dans
   `engine.py`, juste après `_appliquer_intentions` et avant
   `_apply_fabrication`. Elle n'agit que sur un `World`, comme les
   intentions, et appelle `chantiers.avancer_chantiers(world)`. `engine.py`
   ne nomme jamais `plans` : le contrôle
   `test_plan_absent_de_l_arbre_du_moteur` reste tel quel. Pour chaque
   cellule, dans l'ordre des `cell_id` :
   - **Retour** : tous les `ouvriers` de la cellule redeviennent `paysans`.
   - **Envoi** : pour chaque rue en chantier, dans l'ordre des identifiants
     (la plus ancienne d'abord), on envoie
     `min(foyers × TAILLE_FOYER, travail_requis − travail_fourni, paysans encore disponibles)`
     personnes. Elles passent de `paysans` à `ouvriers`, et `travail_fourni`
     augmente d'autant. Si cela atteint `travail_requis`, la rue n'est plus en
     chantier. Le dernier jour, seules les journées qui manquent partent :
     aucune journée n'est perdue ni créée.
   - Les métiers ne sont réécrits que s'ils ont changé, et le plan n'est
     reconstruit (et revalidé) que si une rue a reçu du travail.
   - La fonction rend `{(cell_id, identifiant): personnes envoyées}` pour
     chaque rue en chantier vue. Le moteur ignore ce retour, mais les tests
     le lisent.
   - L'étape ne tire aucun aléa et ne garde aucun état dans son module.
   - Les métiers et la population de la cellule gardent leur somme.
   - Une cellule aux métiers non calculés (`-1`) n'envoie personne : son
     chantier attend.
   - Sans rue en chantier et sans ouvrier, l'étape n'écrit rien. Sans geste,
     le monde est donc identique à l'octet près.
5. **Les conséquences**, sans nouveau code :
   - la récolte du même tick lit les paysans restés aux champs
     (`foyers.facteur_bras` de #256). Avec 0,1 bras par km² cultivé, elle ne
     baisse que si le chantier vide presque la cellule. Par exemple, la
     cellule 1175 a 327 paysans pour 4,25 bras requis : 65 foyers la font
     baisser, un seul ne la touche pas ;
   - pendant le tick, naissances, morts et départs se répartissent au
     prorata, ouvriers compris. Le retour du tick suivant remet tout le monde
     en commun ;
   - les ouvriers comptent dans le bourg (vue dérivée des métiers non
     paysans), puisqu'ils travaillent au plan du bourg ;
   - `/lieu` publie `ouvriers` dans `foyers`, et `/monde` ne change pas ;
   - le tick où la route s'achève, ses ouvriers ont travaillé. Au tick
     suivant, ils sont aux champs.
6. **Ce qui reste de niveau 3** : l'âge et le sexe des ouvriers, leur
   nourriture à part, les outils, les matériaux, la saison du chantier, le
   salaire, et l'effet de la route achevée sur les flux.

### Ce que `MODELE.md` dit après le lot
- **« En une page »** : une étape 3 **Chantiers** (`_avancer_chantiers`), et
  la numérotation suit.
- **« Les foyers par métier »** : la phrase en gras devient « **Le tick ne
  lit les métiers que pour la récolte et pour le chantier** ». Elle garde
  mot pour mot la phrase que figent `test_foyers.py` (l. 239, 571, 732),
  qui ne change pas. Suit une ligne sur le métier `ouvriers`.
- **Une nouvelle section « ## Le chantier et ses bras »** après « Le plan du
  bourg ». Elle porte les règles 2, 4 et 5 : `TRAVAIL_ROUTE_JOURNEES_PAR_M2`,
  `ouvriers`, la priorité à la plus ancienne rue, le retour, la
  conservation des journées, le niveau 2, et l'effet faible, dit
  franchement (0,1 reste ; une cellule est immense ; les lieux de J3 le
  changeront).
- **« Le plan du bourg »** : les trois champs de `Rue`.
  - « Aucune règle du tick ne le lit » devient « seules les étapes
    Intentions et Chantiers le lisent ».
  - Le coût, les bras pris aux champs et l'achèvement passent du niveau 3 au
    niveau 2.
  - La phrase « Aucune règle ne fait passer une rue en chantier à achevée »
    disparaît.
- **« Les intentions du joueur »** : le champ `foyers` et son refus.
  - « La route ne consomme aucun aléa et ne lit ni n'écrit aucune cellule »
    devient : son dépôt et son application n'écrivent aucune cellule ;
    l'étape Chantiers écrit ensuite les métiers de sa seule cellule, sans
    aléa.
- **« Ce que le moteur ne fait pas encore »** :
  - « répartir le travail » : seul le chantier fait passer des paysans à
    ouvriers et retour ;
  - « investir » : une route se bâtit à la journée, mais n'améliore encore
    aucune capacité de transport.

### Les pièges du dépôt (lus par le chef)
- `test_plan_absent_de_l_arbre_du_moteur` interdit tout attribut `plans`
  dans `engine.py`, et `engine.py` n'importe pas `sim.intentions` (il y a un
  cycle par les seigneuries). L'étape vit dans `sim/chantiers.py`, qui
  importe `sim.constants`, `sim.model` et `sim.plan`, jamais
  `sim.intentions`.
- `test_intentions.py::test_applique_seulement_apres_la_garde` exige que
  les deux premières étapes du tick soient `_valider_numero_tick` puis
  `_appliquer_intentions` : `_avancer_chantiers` vient en troisième.
  `_verifier_meme_ordre_tick` compare le code à « En une page ».
- `test_no_hardcoded.py` balaie tout `sim/` : aucun littéral hors {0, 1, −1}.
  Le moteur lit par `_constantes.X`, jamais par `from sim.constants import`.
- `test_write_coverage.py` : `engine.py` ne lit aucune constante nouvelle
  (`TRAVAIL_…`, `METIER_OUVRIERS = "ouvriers"` et `TAILLE_FOYER` sont lues
  dans `chantiers.py`). Les deux constantes nouvelles ont donc un lecteur.
- `test_foyers.py` (`test_bit`, `test_bras_suffisent_un_an`, les contrôles
  de documentation) ne joue aucune route : il doit rester vert sans être
  touché.

## Périmètre
jeu/sim/constants.py
jeu/sim/plan.py
jeu/sim/intentions.py
jeu/sim/chantiers.py
jeu/sim/engine.py
jeu/sim/world.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_chantiers.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_intentions.py

Précisions :
- `world.py` : seul le commentaire « sans effet au tick » de `plans` change.
- `README.md` : une ligne pour `sim/chantiers.py`.
- `test_chantiers.py` est neuf et porte l'invariant du chantier.
- Dans `test_determinisme.py` et `test_intentions.py`, seuls changent les
  trois tests de SC5 et la liste `CAS_REFUS_ROUTE`, où l'on ajoute des cas.

## Conditions de succès
Chaque contre-épreuve est jouée **dans le test** (monkeypatch, puis
`pytest.raises(AssertionError)` ou une comparaison qui doit différer). Les
nombres attendus se dérivent des constantes (`TAILLE_FOYER`,
`TRAVAIL_ROUTE_JOURNEES_PAR_M2`) et du monde chargé, jamais écrits en dur.
Un échantillon vide échoue.

**SC1 — Le geste et la rue refusent ce qui est mal formé.**
`python3 -m pytest jeu/sim/tests/test_intentions.py jeu/sim/tests/test_chantiers.py -q -k "refus or foyers_du_geste or rue_invalide"`
- `CAS_REFUS_ROUTE` gagne `foyers` = 0, −1, `True`, 1.5 et `"1"`, chacun
  refusé avec le mot « foyers » et sans aucune mutation (le test existant
  le vérifie).
- Dans `test_chantiers.py` : sans `foyers`, la `TraceRoute` porte 1 ; avec
  `foyers: 3`, elle porte 3. Après `engine._appliquer_intentions`, la rue
  porte `foyers`, `travail_fourni == 0` et `travail_requis` égal au calcul
  du test (`ceil(65 × 4 × constante)`).
- `Rue` lève `PlanInvalide` pour : fourni > requis ; en chantier avec
  fourni == requis ; pas en chantier avec fourni < requis ; en chantier
  sans foyer ; un champ booléen ou négatif.

Contre-épreuve : la constante doublée par monkeypatch double
`travail_requis` (à l'arrondi supérieur près), et l'égalité avec la valeur
nominale échoue.

**SC2 — Le chantier compte son travail, journée par journée.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k compte`
Sur `World.charger(0)`, sans tick, on appelle seulement
`chantiers.avancer_chantiers` :
- **Une route courte.** Sur la cellule de `_route_reference`, une route
  dont le travail requis n'est pas un multiple de `TAILLE_FOYER` (par
  exemple 13 journées), un foyer. Les appels successifs envoient 5, 5 puis
  3 personnes, et la rue s'achève au troisième. La somme des envois égale
  `travail_fourni`, qui égale `travail_requis`. À chaque appel, les
  `ouvriers` de la cellule égalent les envois de l'appel, et
  `paysans + ouvriers` comme la population restent ceux du départ. Au
  quatrième appel, `ouvriers` a disparu et les paysans sont revenus.
- **La priorité.** Dans la cellule qui a le moins de paysans (le test la
  cherche et vérifie qu'elle en a au moins un), deux routes demandent
  chacune plus de foyers que la cellule n'a de paysans. La première prend
  tous les paysans, la seconde ne reçoit rien.
- **Les métiers non calculés.** Une cellule dont `habitants_par_metier` est
  `None` n'envoie personne, et son `travail_fourni` reste 0.

Contre-épreuve : la fonction de contrôle des invariants du test, appliquée
à un état falsifié (une journée comptée sans ouvrier, ou un ouvrier de
plus que les envois), lève `AssertionError`.

**SC3 — Dans le tick, les ouvriers partent avant la récolte, reviennent après le chantier, et rien d'autre ne bouge.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k tick`
On joue deux `World.charger(0)` avec `random.Random(0)` et `numero_tick=i`
sur 6 ticks : l'un sans geste, l'autre avec la route courte de SC2 déposée
avant le tick 0. Une enveloppe de `engine._apply_production` relève les
`ouvriers` de la cellule au moment de la récolte : 5, 5, 3, puis absents.
À la fin :
- `travail_fourni == travail_requis` et la rue n'est plus en chantier ;
- l'état du générateur est le même dans les deux mondes ;
- toute autre cellule est égale à l'octet près ;
- la cellule du chantier est égale, sa clé `foyers` exceptée.

Contre-épreuve : avec `engine._avancer_chantiers` remplacé par une fonction
qui ne fait rien, `travail_fourni` reste 0 et l'assertion échoue.

**SC4 — Plus de bras au chantier, moins de récolte (direction, pas valeur).**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k recolte`
Cellule `c` de `_route_reference`, `P` = ses paysans, `requis` = ses bras
requis, calculés par le test comme en #256. Quatre mondes, 30 ticks avec
`numero_tick` et la même graine :
- un témoin sans geste ;
- une route avec 1 foyer ;
- une route avec `F_moyen = (P − 1) // TAILLE_FOYER` foyers (le test vérifie
  que le reste `P − F_moyen × TAILLE_FOYER` est entre 0 et `requis`, bornes
  exclues) ;
- une route avec `F_gros = 2 × ceil(P / TAILLE_FOYER)` foyers. Le double
  garde de la marge : les naissances de ces 30 jours restent elles aussi
  hors des champs.

Chaque route est assez longue pour durer les 30 ticks, et le test le
vérifie. La récolte de `c` sur les 30 ticks se relève par enveloppe de
`_apply_production` (stock après moins stock avant). Le test exige :
- 1 foyer : récolte égale au bit près à celle du témoin ;
- `F_moyen` : récolte strictement plus petite ;
- `F_gros` : récolte nulle, donc strictement plus petite encore.

Le test affiche les quatre valeurs.

Contre-épreuve : avec `foyers.facteur_bras` remplacé par `lambda *a: 1.0`,
l'inégalité stricte échoue.

**SC5 — Les trois tests réécrits sont plus stricts, et rien d'autre ne s'assouplit.**
`python3 -m pytest jeu/sim/tests/test_determinisme.py jeu/sim/tests/test_intentions.py -q`
- `test_gestes_routes_deterministes_sans_cellule_ni_alea` est renommé
  `test_gestes_routes_deterministes_seule_la_cellule_du_chantier`.
  - L'assertion « toutes les cellules égales au témoin » devient : toute
    cellule autre que celle de la route est égale au témoin. Celle de la
    route est égale au témoin, sa clé `foyers` exceptée. La somme de ses
    personnes est celle du témoin, et `paysans + ouvriers` égale les
    paysans du témoin.
  - Les deux rues portent un `travail_fourni` de `10 × TAILLE_FOYER` et
    `7 × TAILLE_FOYER`.
  - Contre-épreuve ajoutée : une copie où la clé `foyers` d'une **autre**
    cellule est altérée fait échouer la comparaison.
  - Toutes les autres assertions restent.
- `test_service_route_recu_refus_et_rejeu` : la rue attendue au plan est le
  dictionnaire exact, augmenté de `"foyers": 1`, `"travail_requis": <calcul>`
  et `"travail_fourni": TAILLE_FOYER`. On ajoute : après le tick, le `/lieu`
  de la cellule avec la route publie `ouvriers` avec
  `{"personnes": TAILLE_FOYER, "foyers": 1}` ; celui du service sans route
  n'en a pas, et la somme des personnes est la même. L'égalité des
  trois `/monde` reste.
- `test_ligne_de_commande_gestes_et_refus` : « `temoin["cells"] ==
  monde["cells"]` » devient la même comparaison cellule par cellule que
  ci-dessus. Les rues portent un `travail_fourni` de `4 × TAILLE_FOYER` et
  `1 × TAILLE_FOYER`. `temoin["plans"]` non vide reste exigé.

`git diff -U0 origin/master -- jeu/sim/tests ':!jeu/sim/tests/test_chantiers.py' | grep '^-[^-]'`
ne rend que **cinq lignes** :
1. la ligne `def test_gestes_routes_deterministes_sans_cellule_ni_alea():` ;
2. `assert all(etat["cells"] == etats[2]["cells"] for etat in etats)` ;
3. et 4. les deux lignes du dictionnaire exact de la rue dans le test du
   service ;
5. `assert temoin["cells"] == monde["cells"] and temoin["plans"]`.

Le codeur colle cette sortie dans la PR.

**SC6 — Sans geste, le monde ne bouge pas ; toute la suite reste verte.**
`python3 -m pytest jeu -q` reste vert, en particulier :
- `test_foyers.py` (non modifié, `test_bit` compare 365 ticks à l'octet) ;
- `test_monde.py` (fichiers `/lieu` figés, ordre du tick) ;
- `test_write_coverage.py`, `test_no_hardcoded.py`, `test_lieux.py` ;
- `test_determinisme.py::test_plan_absent_de_l_arbre_du_moteur`.

`git diff --name-only origin/master...HEAD` ne nomme que les chemins du
périmètre et ce brief.

**SC7 — `MODELE.md` dit la règle.**
`python3 -m pytest jeu/sim/tests/test_chantiers.py -q -k documentation`
Un test lit `MODELE.md` et exige :
- une seule section « ## Le chantier et ses bras », qui contient
  `TRAVAIL_ROUTE_JOURNEES_PAR_M2`, `ouvriers` et « niveau 2 » ;
- « En une page » cite `_avancer_chantiers` ;
- « Le plan du bourg » ne contient plus « Aucune règle ne fait passer une
  rue en chantier à achevée » ;
- `README.md` nomme `sim/chantiers.py`.

Contre-épreuve, par `read_text` altéré : retirer la constante de la
section, ou y remettre l'ancienne phrase du plan, fait échouer le contrôle.

## Hors périmètre
- Les bâtiments en chantier : il n'y a aucun geste de bâtiment sur la base.
  Le lot qui créera ce geste reprendra cette étape.
- Relever `BRAS_AUX_CHAMPS_PAR_KM2`, ou toucher à la récolte, à la part
  minière, à l'amorçage ou à `population_soutenable_de`.
- Modifier ou annuler un chantier en cours, changer ses foyers, ou toute
  intention nouvelle autre que le champ `foyers`.
- L'effet d'une route achevée sur le commerce ou la distribution, le
  revêtement, les matériaux, les outils, le salaire, la nourriture propre
  des ouvriers et la saison : niveau 3.
- Unity, `ClientPlan.cs`, le traceur de route, le service et les vues :
  aucun changement. `/lieu` et `/plan` portent les nouvelles données par
  les chemins existants.
- L'IA (jalon 5).
- `test_foyers.py` et tout autre test que les trois de SC5 :
  non modifiés.
- `atelier/`, `.github/`, `atelier.toml`, `AGENTS.md`, `CLAUDE.md`, `CAP.md`.
