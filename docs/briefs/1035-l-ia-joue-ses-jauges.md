# Lot #1035 — L'IA joue ses jauges
Jalon : J6 · Machine : vps · Taille prévue : 350 lignes

## But
Les maisons de l'IA dépensent leur Plume et leur Sceau comme le joueur : elles
affermissent leur Concorde quand elle tombe sous son neutre, et asseyent leur
Droit quand il est sous un seuil écrit dans les données (70), chaque geste
avec sa raison, lisible sur le monde au tick où il est déposé.

## Le joueur
Ses voisins dépensent leur Plume et leur Sceau comme lui : un voisin à la
concorde basse l'affermit, un autre asseoit son droit, et chacun dit pourquoi.
Sur la graine 0, en deux ans, une vingtaine de grandes maisons et de
seigneuries montent leur Droit de 50 à 60 ou 70 (mesuré : 24 maisons,
40 gestes, le premier au 183e jour) et prélèvent de 2 à 4 % de plus sur leurs
terres ; deux voisins dont la Concorde est tombée l'affermissent. Le joueur ne
gouverne plus seul ses jauges : un voisin qui a un bon diplomate devient plus
solide que lui s'il garde son Sceau. Ce geste est celui du jalon 6 (« quand
dépenser sa Plume pour affermir la concorde »), et l'IA le fait par le même
chemin (CAP.md, « La règle d'un jalon » : l'IA, principe 4 ; décision 38).
Chaque geste arrive dans `/ia` avec sa raison ; le dossier des voisins dans
Unity l'affiche déjà comme un ordre reçu (« Raison non interprétée par cette
vue ») : les mots de cette raison à l'écran sont un lot de vue à part, qui
n'est pas dans ce lot.

## Règle du monde
`jeu/sim/MODELE.md`, « Le pays et ses jauges », points « Les gestes » et
« L'IA ».

- **Le seuil, dans les données** (réponse A du propriétaire, 10 novembre
  2026). `jeu/data/jauges.toml` reçoit une table `[ia]` avec
  `droit_bas = 70` : sous cette valeur, une maison de l'IA juge son Droit bas.
  Niveau 2 : voulu, réglable sans toucher au code, jamais sourcé. `lire_regles`
  le lit dans un nouveau champ `Regles.ia` et refuse, avec `JaugeInvalide` et
  sa raison : une table `[ia]` absente, un `droit_bas` qui n'est pas un nombre
  fini (un booléen compris), ou qui n'est pas dans
  `minimum < droit_bas ≤ maximum` de la jauge `droit`.
- **La règle de l'IA** (`sim/ia.py`, `_proposition_de_jauge`). Le jour du mois
  où elle règle sa part (comme aujourd'hui), une maison de l'IA propose **au
  plus un** geste de jauge, le premier qui tient, dans cet ordre :
  1. « Affermir la concorde » si sa Concorde est sous son neutre et que sa
     Plume le paie — inchangé, raison `concorde_sous_son_neutre` avec les mêmes
     champs ;
  2. sinon « Asseoir le droit » si son Droit est strictement sous
     `regles.ia["droit_bas"]` et que son Sceau le paie
     (`jauges.verifier_geste` rend `None`), raison
     `{"regle": "droit_sous_son_seuil", "droit", "seuil", "sceau", "cout"}` —
     `droit` et `sceau` lus par `jauges.etat` au moment de la décision,
     `seuil` lu dans les données, `cout` copié du geste.

  Un seul geste par maison et par mois : le dossier des voisins dans Unity
  (`DossierVoisins.cs`) refuse deux ordres de même type, même maison, même
  jour (« Ordre dupliqué dans le journal »), et la lecture des raisons des
  tests est rangée par `(tick, maison)`. La Concorde passe d'abord : un pays
  qui se défait se recoud avant d'asseoir son souverain.
- **Le même chemin** (décision 38). Le geste part par `recevoir_intention`
  comme celui du joueur : mêmes coûts (30 de Sceau pour +10 de Droit), mêmes
  refus, même application à l'étape des intentions. Le Droit au-dessus de 50
  pose déjà +0,2 % de prélèvement par point : à 70, +4 %.
- **Rien d'autre ne change.** Le Droit ne baisse toujours de lui-même par
  aucune cause (la succession contestée viendra avec #435 et #436) : à 70,
  l'IA s'arrête. Aucun geste ne dépense l'Épée. Le document `/pays`
  (`jauges.gestes` : deux gestes, `grandeurs`, `modificateurs`) ne change pas ;
  le seuil de l'IA n'y est pas servi.
- **MODELE.md** : le point « L'IA » décrit les deux gestes, leur ordre, le
  « un par mois », la raison `droit_sous_son_seuil` et ses champs ; le
  paragraphe « Niveau 2 » ajoute le seuil de 70.

## Périmètre
jeu/data/jauges.toml
jeu/sim/jauges.py
jeu/sim/ia.py
jeu/sim/MODELE.md
jeu/sim/tests/test_pays_et_jauges.py
jeu/sim/tests/test_monde.py (seulement `_lire_jauge` et `_controler_raisons_du_pays`)
docs/briefs/1035-l-ia-joue-ses-jauges.md

## Conditions de succès
Les commandes se lancent depuis `jeu/`.

- **SC1 — Le seuil vient des données.**
  `python -m pytest sim/tests/test_pays_et_jauges.py -k seuil_du_droit_de_l_ia -q`.
  Un nouveau test lit `regles.ia == {"droit_bas": 70}`. Contre-épreuve, dans le
  même test, sur une copie du document lu de `J._CHEMIN` : sans table `[ia]`,
  avec `droit_bas = true`, `"70"`, `nan`, `0` (le minimum du Droit) ou `101`,
  `J.lire_regles` lève `JaugeInvalide` avec un motif qui nomme `ia.droit_bas` ;
  avec `droit_bas = 60`, il lit 60.

- **SC2 — L'IA asseoit son droit par le même chemin, sur un monde forcé.**
  `python -m pytest sim/tests/test_pays_et_jauges.py -k "asseoit_son_droit" -q`.
  Comme `test_l_ia_depense_ses_jauges_par_le_meme_chemin` (`_monde_au_mois`,
  `seigneurie-1`, son jour de la part, `J.avant_le_tick` puis `ia.jouer_ia`) :
  - Droit 50, Sceau 31,5, Concorde 0 : la maison dépose exactement un geste,
    `asseoir_le_droit`, sans refus ; sa raison vaut
    `{"regle": "droit_sous_son_seuil", "droit": 50, "seuil": 70, "sceau": 31.5,
    "cout": {"sceau": 30}}` et égale `_lire_jauge` (test_monde.py) lue sur le
    monde après le dépôt. Une copie du monde prise avant `jouer_ia`, où le
    joueur dépose les mêmes intentions par `recevoir_intention`, donne après un
    tick le même `to_dict()` (JSON trié), avec un Droit de 60. Contre-épreuve :
    la même copie sans dépôt donne un `to_dict()` différent.
  - Elle se tait (aucun `asseoir_le_droit`) : Droit 70 et Sceau 500 ; Droit 60
    et Sceau 29,9.
  - Concorde −1, Plume 60, Droit 50, Sceau 31,5 : un seul geste, `affermir_la_concorde`.
  - Le seuil se lit dans les données : avec `J.charger_regles` remplacé
    (monkeypatch) par des règles dont `ia` vaut `{"droit_bas": 60}`, Droit 60
    et Sceau 31,5 ne déposent rien ; avec `{"droit_bas": 80}`, Droit 70 et
    Sceau 31,5 déposent `asseoir_le_droit` avec `"seuil": 80`. Une règle qui
    écrirait 70 dans le code échoue ici.

- **SC3 — Une IA fautive échoue.**
  `python -m pytest sim/tests/test_pays_et_jauges.py -k "sans_points_ou_dont_la_raison" -q`.
  - Une IA qui dépense sans points : la vérification des points que lit
    `ia.py` est remplacée par une qui accepte tout (le dépôt garde la sienne ;
    par exemple un petit `_payable` dans `ia.py` que le test remplace), avec
    Droit 50 et Sceau 10 : le geste est refusé au dépôt et noté avec `refus`,
    et `_controler_raisons_du_pays` lève `AssertionError`.
  - Une raison qui ne se relit pas sur le monde : la raison de SC2 avec
    `droit` + 10, `seuil` 71 ou `sceau` − 1 fait lever
    `_controler_raisons_du_pays` ; une règle inconnue (`"regle": "droit_haut"`)
    aussi.
  - `_controler_raisons_du_pays` vérifie, pour `droit_sous_son_seuil`,
    `droit < seuil` et `sceau ≥ cout["sceau"]`, et lève sur une règle qu'il ne
    connaît pas (aujourd'hui toute règle inconnue est lue comme la Concorde) ;
    `_lire_jauge` choisit sa lecture selon `intention["geste"]` et lit le seuil
    dans les données, sans `sim/ia.py` (`_noms_sans_ia` reste vrai).

- **SC4 — La preuve : graine 0, 730 jours.**
  `python -m pytest sim/tests/test_pays_et_jauges.py -k jauges_sur_deux_ans -q -s`
  (≈ 4 min sur le VPS : 118 s pour l'IA, 116 s pour le joueur ; un seul test,
  sans fixture partagée, pour xdist).
  - `sim.__main__._simulate(730, 0, ia=True)`, `jouer_ia` enveloppé comme dans
    `_verifier_raisons` : après chaque appel, `_lire_jauge` lit la raison de
    chaque `depenser_jauge` sur le monde du même tick. Exigé : aucun
    `depenser_jauge` refusé ; au plus un par `(tick, maison)` ;
    `_controler_raisons_du_pays` passe ; **au moins deux maisons distinctes**
    affermissent leur Concorde (Plume) et **au moins deux** asseyent leur Droit
    (Sceau). Mesuré sur la base avec la règle : Plume 2 maisons (grande-8,
    grande-22), 4 gestes ; Sceau 24 maisons, 40 gestes, premier au tick 183 ;
    au 730e jour, 16 maisons à 70 de Droit, 8 à 60, toutes les autres à 50.
    Le test imprime ces comptes.
  - Le joueur au même geste : le même `_simulate(730, 0, ia=True)`, où
    `jouer_ia` est remplacé par un dépôt, par `recevoir_intention`, de chaque
    intention non refusée du relevé à son tick (au même moment que l'IA, après
    le mois des jauges) : le `to_dict()` final, en JSON trié, égale celui de
    l'IA (vérifié sur la base avec la règle : égal).
  - Contre-épreuve, sans rejouer : le contrôle des comptes, appliqué au relevé
    privé de ses `asseoir_le_droit` (une IA qui ne joue que la Plume, ce que
    donnerait un seuil au neutre), lève `AssertionError` ; les contre-épreuves
    de SC2 et SC3 portent le reste.

- **SC5 — Aucun test existant ne change, aucune empreinte non plus.**
  `python -m pytest sim/tests/ forge/tests/ -q -n auto -m "not chronometre"`
  passe sans toucher une assertion existante. Aucune empreinte épinglée ne
  change : `EMPREINTES_365` (test_modificateurs.py) ne joue pas l'IA, les
  empreintes du service (test_monde.py) s'arrêtent au tick 4, et aucune épreuve
  de l'IA ne dépasse 100 jours, où le Sceau vaut au plus 15 (trois mois à
  compétence 10) : aucun `asseoir_le_droit` n'y est possible.
  `test_l_ia_depense_ses_jauges_par_le_meme_chemin` garde son seul geste
  `affermir_la_concorde`.

## Hors périmètre
- Aucune cause du monde qui fait baisser le Droit : la succession contestée
  (#435, #436) l'ajoutera, et l'IA y répondra par cette même règle.
- Aucun geste de l'Épée (aucun n'existe), aucun changement des deux gestes du
  panneau, de leurs coûts ou de `/pays`.
- Les mots de `droit_sous_son_seuil` et de `concorde_sous_son_neutre` dans le
  dossier des voisins de Unity (lot `pc` à part) ; rien dans `3d/`.
- L'amélioration de province par l'IA et la règle « Droit sous son maximum »
  du brief #1054 (jalon 5) : sa branche n'est pas sur la base. Ce lot fixe le
  seuil dans les données, selon la réponse du propriétaire ; #1054, à sa
  reprise, part de `[ia] droit_bas` et de cette règle (mêmes fichiers :
  `ia.py`, `test_monde.py`, `test_pays_et_jauges.py`).
- Le rejeu par `--gestes` (`sim/__main__.py`) dépose ses gestes avant le mois
  des jauges, l'IA après : un geste de l'IA posé le premier jour de son mois
  peut y être refusé (mesuré : 27 points au lieu de 30). Ce lot ne change pas
  cet ordre ; sa preuve du joueur dépose au moment de l'IA.
- Aucune empreinte à recapturer, aucun test existant assoupli.
