# Lot #1038 — Les événements à choix nés d'une cause du monde
Jalon : J6 · Machine : vps · Taille prévue : 950 lignes

## But
Quand une famine dure dans un pays, le monde ouvre pour sa maison un événement
à choix, décrit dans `jeu/data/evenements.toml`. Il a trois réponses : ouvrir
les greniers du pays, lever une taxe de disette ou laisser faire. Chacune a son
prix et ses effets, qui passent par des modificateurs, une jauge ou le grain
du grenier. Le joueur répond par une intention, et l'IA répond aux siens par
le même chemin.

## Le joueur
Quand une famine dure dans son pays, le jeu lui propose trois réponses, avec
leur prix et leurs effets :

- **ouvrir les greniers du pays** : un quart de son grenier part vers ses lieux
  affamés, et sa Concorde gagne un point ;
- **lever une taxe de disette** : il prend 25 % de plus sur la récolte pendant
  90 jours, et sa Concorde perd un point ;
- **laisser faire** : son Droit perd 5 points.

Le choix est entre son grain, la tenue de son pays et sa légitimité. Aucune
réponse ne met fin à la famine : c'est le monde qui la fait durer ou cesser.
S'il ne répond pas dans le mois, c'est « laisser faire » qui s'applique.

Ses voisins de l'IA reçoivent les mêmes événements et y répondent avec leur
raison. Sur la graine 0, les premières famines de l'IA tombent vers le 390e
jour (mesuré sans la règle : grande-22 et grande-3). Leurs greniers dépassent
leur réserve, donc elles ouvrent leurs greniers.

C'est le geste du jalon 6 « une famine qui dure lui propose un choix »
(décision 41), et celui des jauges : « répondre à un événement à choix »
(VISION.md, « Les gestes d'un pays »).

Ce lot est `vps`. Le service sert l'événement en attente (`GET /evenement`) et
reçoit la réponse (`POST /intention`). La fenêtre dans Unity viendra d'un lot
`pc` que la liste du jalon 6 ne porte pas encore. D'ici là, les réponses de
l'IA arrivent dans `/ia` avec leur raison, et le dossier des voisins de Unity
les affiche déjà comme des ordres reçus (« Ordre non interprété par cette
vue »).

## Règle du monde
`jeu/sim/MODELE.md` : ce lot ajoute une sous-section « Les événements à choix »
après « La famine, premier événement du monde », dans « Les modificateurs ».
Il ajoute aussi une ligne au point « L'IA » de « Le pays et ses jauges ». La
règle découle de ces deux sections et de la décision 41.

**Les données** : `jeu/data/evenements.toml`, nouveau, de niveau 2 (des valeurs
plausibles, jamais sourcées).

```toml
[evenements.famine]
nom = "La famine dure"
dit = "des lieux du pays ont faim depuis plus d'une semaine"
cause = "famine"          # la seule cause que le code sait lire aujourd'hui
delai_jours = 30          # sans réponse au bout de ce délai : le choix par défaut
par_defaut = "laisser_faire"

[[evenements.famine.choix]]
id = "ouvrir_les_greniers"
nom = "Ouvrir les greniers du pays"
dit = "…"
grenier = 0.25            # la part du grenier versée aux lieux du pays
jauges = { concorde = 1 }

[[evenements.famine.choix]]
id = "lever_une_taxe_de_disette"
nom = "Lever une taxe de disette"
dit = "…"
modificateurs = ["taxe_de_disette"]
jauges = { concorde = -1 }

[[evenements.famine.choix]]
id = "laisser_faire"
nom = "Laisser faire"
dit = "…"
jauges = { droit = -5 }
```

`jeu/data/modificateurs.toml` reçoit `[modificateurs.taxe_de_disette]` : nom
« Taxe de disette », grandeur `prelevement`, valeur `0.25`, portée `pays`,
`duree_jours = 90`.

`evenements.lire_evenements(document)` lève `EvenementInvalide`, avec un motif
qui nomme le champ, dans chacun de ces cas :

- une cause inconnue ;
- moins de deux choix ou plus de trois ;
- deux choix qui portent le même `id` ;
- un `par_defaut` qui n'est pas l'un des choix ;
- un `delai_jours` qui n'est pas un entier ≥ 1 ;
- un choix qui ne pose ni modificateur ni jauge (décision 41 : chaque choix
  pose des modificateurs ou dépense une jauge) ;
- un modificateur absent de `modificateurs.toml`, ou dont la grandeur n'est pas
  lue par le moteur ;
- une jauge absente de `jauges.toml`, ou un écart nul ou non fini ;
- une part du grenier hors de ]0, 1] ;
- tout autre champ dans un choix. Un choix ne peut donc ni écrire un stock, ni
  tuer, ni finir une famine : aucun n'impose une issue.

**La cause** (`sim/evenements.py`, `au_mois(monde, regles)`). La fonction est
appelée par `jauges.avant_le_tick`, juste après `mettre_a_jour`, donc
seulement aux bornes de mois. Les trois boucles (le service, `python -m sim`,
`python -m forge`) la jouent ainsi sans changer, IA ou non, rejeu compris.

Une maison a la cause « famine » au tick `t` si l'un des lieux dont elle est
le maître porte la pose `famine` (`evenement:famine`, lot #1029) et si son
dernier jour de faim tombe dans le mois écoulé : `fin − 365 jours ≥ t − 30`.
Un lieu affamé depuis sept jours ou moins n'a pas de pose : il ne fait pas la
cause. On lit le registre des modificateurs, jamais la faim brute.

Le monde d'avant la famine (`couper_la_famine`, `amorcer_comme_avant_la_soudure`)
n'a donc aucun événement. Ses épreuves et ses empreintes gardent leurs octets.

**L'événement.** `World.evenements` associe à l'identifiant d'une maison
`{"identifiant": "famine", "ouvert": t, "lieux": [[cell_id, rang], …]}`, où
`lieux` sont ses lieux qui font la cause, triés. Une maison a au plus un
événement en attente. `to_dict()` ne porte la clé `evenements` que si la table
n'est pas vide, triée par maison.

Chaque mois, `au_mois` fait deux choses, dans cet ordre, maison par maison
triée par identifiant, pour **toutes** les maisons du registre (celles de
l'IA, celle du joueur, et celles que personne ne joue) :

1. **Fermer.** Un événement ouvert depuis au moins `delai_jours`, et dont
   aucune réponse n'attend dans `intentions_en_attente`, se ferme par son
   choix `par_defaut`. Ce choix passe par la même fonction que la réponse
   déposée (`appliquer_choix`).
2. **Ouvrir.** Une maison sans événement en attente, qui a la cause, en
   reçoit un.

Sur la graine 0 sans IA, le premier événement s'ouvre au tick 30, pour
`plausible-10391-0` : sa famine a été posée au tick 25 (mesuré). Avec l'IA, les
premiers événements d'une maison de l'IA s'ouvrent au tick 390 (grande-22 et
grande-3, mesuré sur la base sans la règle).

**La réponse** : l'intention `repondre_evenement`, avec les champs `type`,
`maison` et `choix`, passe par `recevoir_intention`.

Le dépôt n'écrit rien dans le monde. Il refuse, avec sa raison, mot pour mot :

- `maison inconnue ou mal formée : {maison!r}` ;
- `aucun événement en attente : {maison}` ;
- `choix inconnu : {choix!r} ({ids triés, séparés par des virgules})` ;
- `réponse déjà déposée : {maison}` ;
- pour l'ouverture, `grenier vide : rien à ouvrir pour {maison}`. Le refus
  vaut aussi si la part est nulle une fois retirés les `ouvrir_grenier` et les
  `repondre_evenement` de la maison déjà en attente. L'ouverture reprend
  aussi les refus de `_ouvrir_grenier` (maison sans lieu, lieux sans dette ni
  habitants) ;
- pour un choix qui fait baisser une jauge déjà à son minimum, le texte de
  `verifier_geste` : « Concorde déjà à sa borne : … ». Le choix `par_defaut`
  n'est jamais refusé pour sa jauge : il est borné. Une hausse au-delà du
  maximum est bornée, elle non plus n'est pas refusée.

L'intention retenue, `RepondreEvenement(maison, choix, kg)`, garde les kilos de
l'ouverture, comptés au dépôt : `kg = part × (grain du grenier − grain déjà
engagé)`.

`_ouvrir_grenier` compte désormais aussi les `RepondreEvenement` en attente de
la maison dans le grain engagé : le grenier ne paie jamais deux fois.

`jauges.verifier_geste` reçoit un paramètre optionnel `effets` : les écarts de
jauge des réponses en attente. `_depenser_jauge` les lui passe, pour que
l'étape des intentions ne lève jamais `JaugeInvalide`. Par exemple, avec une
Concorde à 2, « ouvrir » est déposé puis « affermir la concorde » : ce geste
est refusé au dépôt, car la Concorde est déjà à sa borne.

**L'effet, au tick près.** `RepondreEvenement.appliquer`, à l'étape des
intentions du tick suivant le dépôt, appelle `appliquer_choix(monde, maison,
choix, kg)`, qui fait dans cet ordre :

1. elle ôte l'événement de `World.evenements` ;
2. elle déplace chaque jauge de son écart, borné, et repose les modificateurs
   des jauges (`jauges._ecrire`, `poser_les_modificateurs`) ;
3. pour chaque modificateur du choix, elle retire la source
   `evenement:<identifiant>:<maison>` puis la repose sur la cible
   `{"pays": maison}`. Une seconde taxe renouvelle la première au lieu de
   s'y ajouter ;
4. si `kg > 0`, elle joue `OuvrirGrenier(maison, kg).appliquer(monde)` : le
   grain quitte le grenier et arrive aux lieux par le secours, partagé selon
   leur dette, ou selon leurs habitants si aucun n'a de dette.

Comme les intentions précèdent le calcul des facteurs du tick, la taxe compte
dès le tick `t` où la réponse s'applique, jusqu'au tick `t + 89`. `expirer`
l'ôte au début du tick `t + 90`.

L'économie reste physique (décision 35). La taxe multiplie un prélèvement que
le moteur calculait déjà, jamais au-delà de la récolte. L'ouverture déplace de
vrais kilos. Aucun choix ne crée de kilo.

**L'IA** (`sim/ia.py`, `_proposition_de_reponse`). Le jour du mois où elle règle
sa part, une maison de l'IA qui a un événement en attente dépose une réponse.
Elle prend le premier choix qui tient, dans cet ordre, avec sa raison. La
raison porte toujours `evenement`, `ouvert`, `grenier_nourriture_kg` (lu au
moment de la décision), `reserve_voulue_kg` (`_reserve_voulue`) et
`part_du_grenier` :

1. `ouvrir_les_greniers` si `grenier × (1 − part) ≥ réserve voulue`, raison
   `grenier_au_dessus_de_sa_reserve` ;
2. sinon `lever_une_taxe_de_disette` si `grenier < réserve voulue` et si sa
   Concorde est au-dessus du minimum de la jauge, raison
   `grenier_sous_sa_reserve` (plus `concorde` et `minimum`) ;
3. sinon `laisser_faire`, raison `ni_grain_ni_concorde` (plus `concorde` et
   `minimum`).

La proposition se range après le geste de jauge du même jour. Elle n'empêche
aucun autre geste. Le dossier des voisins de Unity ne voit qu'un ordre de ce
type par maison et par jour.

Le joueur qui dépose la même intention obtient le même monde (décision 38) :
mêmes refus, mêmes kilos, mêmes poses. Une maison que personne ne joue laisse
faire au bout du délai, comme le joueur qui ne répond pas.

**Le service.**

- `GET /evenement?maison=<id>` est lu sous le verrou du tick, au tick publié.
  Il sert `{"maison", "tick", "date", "evenement"}`. `evenement` vaut `null`
  sans événement en attente. Sinon il porte :
  - `identifiant`, `nom`, `dit`, `ouvert`, `ouvert_date`, `ferme_au_tick`,
    `par_defaut` et `lieux` ;
  - `choix`, dans l'ordre des données. Chaque choix a son `id`, son `nom`,
    son `dit`, son prix (`grenier_kg`, les kilos que le dépôt prendrait à ce
    tick, ou `null`), ses `jauges` (les écarts) et ses `modificateurs`
    (`nom`, `grandeur`, `grandeur_nom`, `valeur`, `portee`, `duree_jours`).
    Il a aussi son `refus` : la raison du dépôt, ou `null`.

  Un paramètre invalide reçoit 400, une maison inconnue 404.
- `POST /intention` avec `repondre_evenement` est réservé à la maison du
  joueur, comme `ouvrir_grenier` :
  - sans joueur : « départ non appliqué : choisir une terre avant de répondre
    à un événement » ;
  - pour une autre maison : « maison interdite : seule la maison du joueur
    répond à ses événements ».
- Si l'IA échoue, `jouer_un_tick` défait aussi `World.evenements`, en plus des
  jauges et des modificateurs.

**MODELE.md.**

- La sous-section « Les événements à choix » décrit les données, la cause, la
  vie d'un événement (ouvrir, répondre, fermer par défaut), les trois choix et
  leurs effets, les refus, l'IA et `/evenement`.
- Le point « L'IA » de « Le pays et ses jauges » renvoie à cette sous-section.
- Le paragraphe « Niveau 2 » y ajoute les valeurs de `evenements.toml` et de la
  taxe.

## Périmètre
jeu/data/evenements.toml
jeu/data/modificateurs.toml
jeu/sim/evenements.py
jeu/sim/intentions.py
jeu/sim/jauges.py
jeu/sim/world.py
jeu/sim/ia.py
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_evenements_a_choix.py
docs/briefs/1038-les-evenements-a-choix-nes-d-une-cause-du-monde.md

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Le nouveau fichier de tests partage
deux fixtures de module :

- `W30` : la graine 0 sans IA, jouée jusqu'au tick 30 par `jauges.avant_le_tick`
  puis `engine.tick`, et arrêtée juste après le `avant_le_tick` du tick 30, sur
  l'événement de `plausible-10391-0` (≈ 8 s) ;
- `IA420` : `sim.__main__._simulate(420, 0, ia=True)`, avec `jouer_ia`
  enveloppé comme dans `test_jauges_sur_deux_ans…` (≈ 80 s). Elle garde le
  relevé, la lecture de chaque raison au moment du dépôt, et une copie du
  monde prise avant `jouer_ia` au premier tick où une maison de l'IA répond.

- **SC1 — Les événements viennent des données, et un choix ne peut pas
  imposer d'issue.**
  `python -m pytest sim/tests/test_evenements_a_choix.py -k donnees -q`.
  - `charger_evenements()` lit un seul événement, `famine` : trois choix dans
    l'ordre des données, `par_defaut = "laisser_faire"`, `delai_jours = 30`.
    Chaque choix pose un modificateur ou déplace une jauge.
    `charger_donnees().definitions["taxe_de_disette"]` vaut prélèvement, 0,25,
    portée pays, 90 jours.
  - Contre-épreuve : sur des copies du document lu, chacun des cas de refus de
    « Règle du monde » lève `EvenementInvalide` avec son motif. Parmi eux :
    - un choix sans modificateur ni jauge ;
    - un choix avec `population = -100` ou `fin_de_la_famine = true` (champ
      inconnu) ;
    - un modificateur `levee` (une grandeur que le moteur ne lit pas, donnée
      par une définition d'épreuve) ;
    - `grenier = 0` ou `1.5` ;
    - quatre choix ;
    - `par_defaut = "fuir"` ;
    - `cause = "peste"`.

- **SC2 — L'événement n'apparaît qu'avec sa cause.**
  `python -m pytest sim/tests/test_evenements_a_choix.py -k cause -q`.
  - Sur `W30` : `World.evenements` vaut exactement
    `{"plausible-10391-0": {"identifiant": "famine", "ouvert": 30, "lieux": […]}}`,
    et chacun de ses lieux porte la pose `famine`, qu'un contrôle
    `_cause_de(monde, maison)` relit sur le registre des modificateurs. Au tick
    29, alors que la famine est posée depuis le tick 25, il n'y a aucun
    événement : ils ne naissent qu'au mois.
  - Contre-épreuves :
    - les mêmes 30 ticks joués avec `couper_la_famine` ne donnent aucun
      événement, et `"evenements"` est absent de `to_dict()` ;
    - un événement injecté pour `grande-3`, qui n'a pas de famine au tick 30,
      fait lever `AssertionError` au contrôle de cause ;
    - une `au_mois` remplacée par une version qui ouvre un événement à toute
      maison qui a un lieu, sans lire la pose, fait échouer le contrôle sur
      `W30` ;
    - une réponse déposée pour `grande-3` est refusée : « aucun événement en
      attente : grande-3 ».

- **SC3 — Chaque choix change exactement ce qu'il dit, au tick près.**
  `python -m pytest sim/tests/test_evenements_a_choix.py -k exactement -q`.
  Pour chacun des trois choix, deux copies de `W30` : A reçoit la réponse par
  `recevoir_intention`, B ne reçoit rien. Le dépôt ne change pas `to_dict()`.
  Les deux copies jouent ensuite l'étape des intentions
  (`engine._appliquer_intentions`), puis on compare `to_dict()`. Les clés qui
  diffèrent sont exactement :
  - **ouvrir** : `evenements` (l'événement est ôté) ; `jauges` de la maison
    (Concorde +1, bornée, rien d'autre) ; les poses `jauge:concorde:` de la
    maison ; `greniers` de la maison (−kg, avec `kg == 0.25 × grenier au
    dépôt`) ; `secours` (la somme ajoutée vaut kg, au kilo près selon
    `math.isclose`) ;
  - **taxe** : `evenements` ; Concorde −1 et ses poses ; une seule pose de
    plus, `taxe_de_disette`, prélèvement +0,25, cible `("pays", maison)`,
    source `evenement:taxe_de_disette:plausible-10391-0`, `debut == 30`,
    `fin == 120` ;
  - **laisser faire** : `evenements` ; Droit −5 et sa pose `jauge:droit:`
    (prélèvement −0,01).

  La taxe, ensuite : après l'étape des intentions, `facteur(monde,
  "prelevement", cid, rang)` vaut celui de B plus 0,25 sur chaque lieu tenu
  par la maison. Sur une copie, `expirer` au tick 119 garde la pose, et au
  tick 120 il l'ôte. Une taxe déposée une seconde fois remplace la première,
  sans s'y ajouter.

  Contre-épreuves, chacune fait échouer la comparaison :
  - une réponse déposée un tick trop tard, dont l'effet manque au tick 30 ;
  - une ouverture qui verse les kilos au panier sans passer par le secours ;
  - une taxe à 0,30 ;
  - une Concorde déplacée de 2.

  Les refus, mot pour mot (test paramétré), sans rien écrire :
  - maison inconnue ;
  - aucun événement ;
  - choix inconnu ;
  - réponse déjà déposée ;
  - grenier vidé à 0 : « grenier vide : rien à ouvrir pour
    plausible-10391-0 » ;
  - taxe avec une Concorde forcée à −3 : texte de `verifier_geste` ;
  - laisser faire avec un Droit forcé à 0 : accepté, borné à 0 ;
  - champ inconnu ou manquant.

  Et les deux pièges du grain et des jauges :
  - avec une ouverture en attente, un `ouvrir_grenier` de plus que le reste
    est refusé (« grenier insuffisant »), et réciproquement ;
  - avec une Concorde à 2 et une ouverture en attente, `affermir_la_concorde`
    est refusé au dépôt. Sans ce refus, l'étape des intentions lèverait
    `JaugeInvalide` (vérifié en appelant `appliquer` sur une copie).

- **SC4 — Sans réponse, le choix par défaut s'applique au mois suivant, et
  jamais par-dessus une réponse.**
  `python -m pytest sim/tests/test_evenements_a_choix.py -k defaut -q`.
  - `W30` joué jusqu'au tick 60 sans réponse : au `avant_le_tick` du tick 60,
    le Droit de `plausible-10391-0` vaut 45. Un nouvel événement, `ouvert ==
    60`, le remplace, puisque la cause tient encore (mesuré : sa famine dure au
    tick 60).
  - Contre-épreuve : la même copie, avec « ouvrir » déposé au tick 59, n'est
    pas fermée par défaut au tick 60. Son Droit reste 50, sa Concorde a pris
    +1, et aucun nouvel événement ne s'ouvre avant le tick 90.

- **SC5 — L'IA répond par le même chemin, et le joueur au même choix obtient
  le même monde.**
  `python -m pytest sim/tests/test_evenements_a_choix.py -k "ia_et_joueur" -q -s`
  (≈ 3 min : 80 s pour l'IA, 80 s pour le joueur).
  - Sur `IA420` :
    - au moins une maison de l'IA dépose un `repondre_evenement`, aucun n'est
      refusé, et chacun répond à un événement dont `_cause_de` relit la cause ;
    - chaque raison égale celle que relit `_lire_reponse(monde, maison,
      intention)` sur le monde au moment du dépôt, et sa règle tient (par
      exemple `grenier × (1 − part) ≥ réserve voulue` pour l'ouverture) ;
    - le test imprime les maisons, leurs choix et leurs ticks.

    Si la règle repousse la première famine de l'IA au-delà du 420e jour,
    l'horizon s'allonge jusqu'à elle, sans dépasser 730 jours, et le brief
    n'en est pas trahi.
  - Le joueur au même choix : le même `_simulate`, où `jouer_ia` est remplacé
    par le dépôt de chaque intention non refusée du relevé à son tick, par
    `recevoir_intention`. Le `to_dict()` final, en JSON trié, égale celui de
    l'IA.
  - Les trois règles, sur la copie gardée par `IA420`, la maison qui répond :
    - grenier forcé à 4 × la réserve : `ouvrir_les_greniers` ;
    - grenier forcé à la moitié de la réserve, Concorde 0 :
      `lever_une_taxe_de_disette` ;
    - même grenier, Concorde −3 : `laisser_faire`.

    Pour chacune, une copie où l'IA joue (`jouer_ia`) et une copie où le
    joueur dépose la même intention donnent, après un tick, le même
    `to_dict()`.
  - Contre-épreuves :
    - une raison faussée (grenier +1 kg, ou une règle inconnue) fait lever le
      contrôle des raisons ;
    - un relevé rejoué sans sa première réponse donne un autre monde ;
    - une IA qui écrit sa réponse dans le monde (`appliquer_choix` appelé
      directement, sans dépôt) laisse le relevé sans réponse, et le contrôle
      « au moins une réponse » échoue.

- **SC6 — Le service sert l'événement et ses choix, et reçoit la réponse du
  joueur.**
  `python -m pytest sim/tests/test_evenements_a_choix.py -k service -q`.
  Service local en épreuve, sans IA, horloge à l'arrêt :
  - le joueur choisit `seigneurie-1` (`choisir_depart`). Le panier du bourg de
    sa capitale est vidé chaque jour (`POST /epreuve/vider-panier`) du tick 18
    au tick 29, de sorte que sa faim dépasse sept jours ;
  - au tick 30, `GET /evenement?maison=seigneurie-1` sert l'événement
    `famine`, ses trois choix dans l'ordre, leurs prix (`grenier_kg` égal à
    0,25 × le grenier servi par `/pays`), leurs effets, `refus` à `null`, et
    `ferme_au_tick == 60`. Ses `lieux` portent bien la pose `famine` dans
    `/modificateurs` ;
  - `GET /evenement?maison=grande-3` sert `"evenement": null` ;
  - `maison=` vide reçoit 400, `maison=inconnue` 404 ;
  - `POST /intention` `repondre_evenement` pour `grande-3` est refusé
    (« maison interdite : seule la maison du joueur répond à ses
    événements ») ; avant `choisir_depart`, il est refusé aussi (« départ non
    appliqué… ») ;
  - pour `seigneurie-1`, avec `lever_une_taxe_de_disette`, il est accepté
    (`appliquee_au_tick == 30`). Après `POST /tick?n=1`, `/evenement` sert
    `null` et `/modificateurs` porte la pose « Taxe de disette » sur le pays,
    `fin_date` à 90 jours.
  - Contre-épreuve : une seconde réponse déposée avant le tick est refusée
    (« réponse déjà déposée : seigneurie-1 »).
  - Une IA qui lève une exception après le mois défait `World.evenements`. Le
    test réutilise le montage d'erreur IA existant, s'il y en a un, dans ce
    fichier.

- **SC7 — Aucun test existant ne change, aucune empreinte non plus.**
  `python -m pytest sim/tests/ forge/tests/ -q -n auto -m "not chronometre"`
  passe sans toucher une assertion existante. Aucune empreinte épinglée ne
  change, parce que :
  - `EMPREINTES_365` (test_modificateurs.py) joue `engine.tick` seul, sans le
    mois, et famine coupée ;
  - les empreintes du service (test_monde.py) s'arrêtent au tick 4, avant
    tout mois ;
  - les épreuves de l'IA de `test_monde.py` (`_verifier_raisons`, dont la
    liste fermée des types d'intention) et `annee_ia` / `annee_programme`
    (test_intentions.py, qui ne jouent pas `avant_le_tick`) jouent le monde
    d'avant la famine, ou sans le mois : aucun événement n'y naît ;
  - `test_ia_option_explicitement` compare deux boucles qui jouent toutes deux
    `avant_le_tick`.

  `test_jauges_sur_deux_ans_l_ia_et_le_joueur_jouent_le_meme_monde`
  (test_pays_et_jauges.py) voit désormais des `repondre_evenement` dans son
  relevé, et son joueur les rejoue au même moment. Il doit passer tel quel :
  le même monde des deux côtés, aucun `depenser_jauge` refusé (vérifié par le
  SC3 sur la Concorde engagée).

## Hors périmètre
- La fenêtre de l'événement dans Unity, ses mots dans le dossier des voisins,
  et une alerte dans le bandeau : un lot `pc` à écrire. Ce lot ne touche rien
  dans `3d/`.
- Les autres causes de la décision 41 : la révolte (pas encore dans le monde)
  et la succession contestée (#435, #436). `lire_evenements` refuse toute
  cause autre que `famine`, jusqu'à ce que leurs lots la lui apprennent.
- Le fil des nouvelles (#1028, jalon 5) : un événement ouvert ou fermé par
  défaut n'y est pas écrit.
- La photographie : elle ne porte pas `evenements`. Seuls le service
  (`/evenement`, `/ia`) et `to_dict()` les servent.
- Le rejeu `--gestes` de `sim/__main__.py`, qui dépose avant le mois : une
  réponse du jour d'ouverture y serait refusée (aucun événement en attente).
  Ce lot ne change pas cet ordre ; ses preuves déposent au moment de l'IA.
- Aucune empreinte à recapturer, aucun test existant assoupli, aucun fichier de
  `atelier/`, `.github/`, ni `CAP.md` ou `docs/VISION.md`. La ligne 419 de
  VISION.md (« leur liste et leurs choix restent à écrire ») reste au
  propriétaire.
