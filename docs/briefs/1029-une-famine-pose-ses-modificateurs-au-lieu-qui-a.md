# Lot #1029 — Une famine pose ses modificateurs au lieu qui a faim
Jalon : J5 · Machine : vps · Taille prévue : 450 lignes

## But
Un lieu qui a faim depuis plus de `FAIM_AVANT_SECOURS_JOURS` reçoit la pose
« Famine » (−50 % de natalité, source `evenement:famine`). Elle est prolongée
chaque jour de faim et s'efface seule 365 jours après le dernier. C'est le
premier événement du monde dans le registre des modificateurs (décision 34).

## Le joueur
Quand il survole un lieu affamé, le joueur lit dans l'infobulle la ligne de la
famine. L'infobulle de #1031 la dit déjà telle que le service la sert :
« Natalité : −50 % Famine · événement · encore 365 jours ». Il sait donc
combien de temps la famine durera. Le document `/modificateurs` porte aussi sa
date de fin (`fin_date`), que l'écran pourra dire plus tard. La famine pèse
vraiment : pendant un an après la faim, le lieu refait ses gens deux fois moins
vite. La faim, elle, tue toujours par la dette, comme avant. La Concorde de son
pays baisse déjà quand une part de ses lieux a faim (`sim/jauges.py`, #1039) :
ce lot n'y touche pas.

Le jalon J5 (« le monde vivant ») y gagne un monde qui garde la trace de ses
famines, et un fil de nouvelles à venir (#1028) qui pourra dire « une famine
commence » d'après une pose réelle.

## Règle du monde
Section `jeu/sim/MODELE.md` « Les modificateurs ». Ce lot y ajoute une
sous-section « La famine, premier événement du monde ».

Décision du propriétaire du 10 novembre 2026 sur l'issue (réponse A) : la
famine est posée au 8e jour de faim, prolongée chaque jour de faim, et s'efface
seule 365 jours après le dernier jour de faim.

- **Les données** (`data/modificateurs.toml`, niveau 2, plausible, non sourcé).
  Ajouter la définition `[modificateurs.famine]` : `nom = "Famine"`,
  `grandeur = "natalite"`, `valeur = -0.5`, `portee = "lieu"`,
  `duree_jours = 365`. Son commentaire dit trois choses : la durée se compte
  depuis le dernier jour de faim ; le seuil est `FAIM_AVANT_SECOURS_JOURS`
  (`sim/constants.py`) ; la faim ne pose rien d'autre. Aucune constante
  numérique neuve dans le code : le 365 vit dans les données, et le seuil est
  celui du secours.
- **L'événement** (module neuf `sim/evenements.py`). Il expose
  `poser_les_famines(monde, affames, donnees=None)`, appelée par `engine.tick`
  au tick `t` (`monde.ticks_ecoules == t`). L'appel se fait après la boucle des
  cellules (consommation, faim, mortalité, natalité) et avant
  `_flux.noter_affames`. `affames` est l'ensemble `(cell_id, rang)` déjà
  recueilli par `recueillir_affames` : la population est positive, la pénurie
  aussi, et `duree_faim_ticks > 0`. Pour chaque lieu de cet ensemble, dans
  l'ordre trié :
  - s'il porte déjà une pose `famine` (identifiant `famine`, cible
    `("lieu", cid, rang)`), sa fin devient `t + duree_jours // TICK_DURATION_DAYS`.
    C'est la même formule que dans `modificateurs.poser`. La pose est remplacée
    par `dataclasses.replace(pose, fin=…)`, son `debut` reste celui du premier
    jour ;
  - sinon, si `lieu.duree_faim_ticks > FAIM_AVANT_SECOURS_JOURS` (le 8e jour de
    faim, au plus tôt), la fonction appelle
    `modificateurs.poser(monde, "famine", "evenement:famine", {"lieu": [cid, rang]}, donnees)`.
    `debut` vaut `t` et `fin` vaut `t + 365` ;
  - sinon, rien ne se passe : un lieu sans faim, ou qui a faim depuis 7 jours
    ou moins, ne reçoit aucune pose.

  Un lieu ne porte jamais deux poses `famine`. Les données ne se lisent
  (`charger_donnees()`) que si un lieu reçoit une pose ou en prolonge une. Un
  tick sans faim ne lit aucun fichier et ne coûte rien : le tick avec IA reste
  sous 100 ms. `World.modificateurs` reste trié (`_ordre` ne lit pas `fin`).
- **L'effacement.** Rien de neuf : `modificateurs.expirer`, premier maillon du
  tick, ôte la pose au début du tick `L + 365`, où `L` est le dernier tick de
  faim. Le facteur natalité 0,5 touche donc le lieu aux ticks `t + 1` à
  `L + 364`. Il est calculé une fois par tick (`facteurs_du_tick`) et lu par
  `_apply_natalite`.
- **Ce qui ne change pas.** `_apply_natalite` ne fait naître que dans un lieu
  nourri et sans dette (`duree_faim_ticks == 0` et
  `dette_alimentaire_kg == 0`). Pendant la faim, il n'y a donc aucune
  naissance, avec ou sans famine. La famine n'agit qu'après, sur un lieu qui
  mange de nouveau. Elle ne touche ni la mortalité (la faim tue par la dette,
  `_apply_mortality` est inchangé), ni un kilo, ni un stock (décision 35).
- **Le document de l'infobulle.** `document_des_modificateurs` ajoute à chaque
  ligne, à côté de `reste_jours`, le champ `fin_date` :
  `constantes.date_de_tick(fin)` (`{"annee", "jour_de_l_annee"}`), ou `null`
  sans fin. `detail()` et `Pose.en_document()` ne changent pas : `/pays` sert
  ce dernier, et `test_le_document_dit_le_nom_de_la_grandeur_le_mot_de_la_source_et_le_reste`
  fige leurs clés.
- **Le monde d'avant.** `sim/tests/amorcage_d_avant.py` gagne
  `couper_la_famine(monkeypatch)`, qui remplace
  `sim.evenements.poser_les_famines` par une fonction qui ne pose rien.
  `engine.py` l'appelle donc par l'attribut du module,
  `_evenements.poser_les_famines(...)`, jamais par un import de nom.
  `amorcer_comme_avant_la_soudure` l'appelle aussi : le décor d'avant la
  soudure est aussi celui d'avant la famine, et son docstring le dit. Toutes
  les épreuves de ce décor gardent ainsi leurs octets sans être touchées, entre
  autres `forge/tests/test_forge.py::test_forge_ia_sans`, les réponses figées
  du pont (`test_monde.py::test_service_reponse_figee_*`) et `test_logement_sans_geste`.

## Périmètre
jeu/data/modificateurs.toml
jeu/sim/evenements.py
jeu/sim/engine.py
jeu/sim/modificateurs.py
jeu/sim/MODELE.md
jeu/sim/tests/amorcage_d_avant.py
jeu/sim/tests/test_modificateurs.py
jeu/sim/tests/test_famine.py

Dans `jeu/sim/tests/test_modificateurs.py`, une seule modification est
permise. `test_sans_modificateur_la_photographie_a_365_jours_est_celle_d_avant`
reçoit la fixture `monkeypatch` et, en première ligne,
`couper_la_famine(monkeypatch)`, avec un commentaire qui cite la réponse A du
10 novembre 2026. Ses assertions et `EMPREINTES_365` restent tels quels, octet
pour octet. Aucun autre test de ce fichier ne change. `forge/tests/test_forge.py`
n'est pas dans le périmètre : il passe par `amorcer_comme_avant_la_soudure`.

## Conditions de succès
Les commandes se lancent depuis `jeu/`. Ne lance jamais la suite entière, ni
un fichier de test entier, sauf les deux contrôles statiques de SC8. Rejoue
chaque test avec `python3 -m pytest <fichier> -q -k <nom>`. Ne remesure pas le
monde.

- **SC1 — Au jour dit, et seulement avec la faim.** Commande :
  `python3 -m pytest sim/tests/test_famine.py -q -k au_jour_dit`. Le test
  charge `World.charger(0)` sans IA et joue 60 ticks. À chaque tick, il relève
  `duree_faim_ticks` de chaque lieu (graine 0 : 9 lieux ont faim plus de 7 jours
  la première année, le premier vers le jour 25). Il vérifie trois choses :
  - au moins une pose `famine` existe au 60e tick ;
  - chaque pose a pour `debut` le tick exact où son lieu a atteint
    `duree_faim_ticks == FAIM_AVANT_SECOURS_JOURS + 1`, avec la source
    `evenement:famine` et la cible `("lieu", cid, rang)` ;
  - tout lieu qui a dépassé le seuil porte une pose, et aucun autre lieu n'en
    porte.

  Contre-épreuve, dans le même test : une fausse `poser_les_famines`, qui pose
  sur chaque lieu peuplé sans regarder sa faim, fait échouer la vérification
  (`pytest.raises(AssertionError)`).
- **SC2 — Prolongée, puis effacée.** Commande :
  `python3 -m pytest sim/tests/test_famine.py -q -k s_efface`. Le test part de
  la fixture de départ et fixe à la main `ticks_ecoules` et `duree_faim_ticks`
  d'un lieu. Il appelle `evenements.poser_les_famines` puis
  `modificateurs.expirer`, et vérifie :
  - aucune pose au 7e jour de faim, une pose au 8e ;
  - un jour de faim au tick `L` porte la fin à `L + 365`, sans changer le
    `debut` ni créer une seconde pose ;
  - la pose est encore là au tick `L + 364` et partie au tick `L + 365` ;
  - un lieu dont la faim est de 0 n'a rien.

  Contre-épreuves : une famine posée avec `fin = None` (elle ne s'efface
  jamais), puis une famine jamais prolongée (fin restée `debut + 365`), font
  chacune échouer la vérification.
- **SC3 — Les naissances baissent de la valeur posée, au tick près.**
  Commande : `python3 -m pytest sim/tests/test_famine.py -q -k naissances`. Le
  test prend deux copies de la fixture de départ : un témoin, et une copie où
  un lieu nourri et sans dette porte la pose `famine`, posée par l'événement
  (faim fixée à la main au-dessus du seuil, puis remise à 0, dette 0). Un
  enrobage de `engine._apply_natalite` relève la population et
  `natalite_remainder` de ce lieu avant et après, sur un tick. Le test
  vérifie que :
  - ses naissances valent exactement
    `int(population × taux × 0,5 + reste)`, quand le témoin fait
    `int(population × taux + reste)`, avec
    `taux = constantes.naissances_par_habitant_par_tick()` et un résultat
    strictement plus petit ;
  - tous les autres lieux ont les mêmes naissances dans les deux mondes.

  Contre-épreuve : une valeur de −0,25 au lieu de −0,5 dans des données
  d'épreuve fait échouer l'égalité.
- **SC4 — Ni kilo, ni mort de plus.** Commande :
  `python3 -m pytest sim/tests/test_famine.py -q -k ni_kilo`. Sur un tick,
  témoin contre famine :
  - la masse de nourriture du monde est la même (paniers, greniers, convois,
    mer, pertes, comme `_masse` de `test_modificateurs.py`) ;
  - un lieu affamé et endetté qui porte la famine perd exactement autant
    d'habitants par `_apply_mortality` que dans le témoin, et n'a aucune
    naissance ;
  - `facteurs_du_tick` n'a pas de clé `mortalite`.

  Contre-épreuve : une fausse famine qui retire un kilo au panier du lieu fait
  échouer l'égalité des masses.
- **SC5 — L'infobulle dit la fin.** Commande :
  `python3 -m pytest sim/tests/test_famine.py -q -k fin_date`. Le test sert
  `/modificateurs` par `ServeurMonde` (comme
  `test_le_document_dit_le_nom_de_la_grandeur_le_mot_de_la_source_et_le_reste`)
  sur un monde où un lieu porte la famine. La ligne doit dire :
  - `nom == "Famine"`, `valeur == -0.5`, `source_dite == "événement"` ;
  - `reste_jours == (fin − tick publié) × TICK_DURATION_DAYS` ;
  - `fin_date == constantes.date_de_tick(fin)`.

  Une pose sans fin (le moulin) a `fin_date` à `null`. Contre-épreuve : une
  `fin_date` calculée sur `debut` échoue.
- **SC6 — Les deux tests figés gardent leurs empreintes.** Commandes :
  - `python3 -m pytest sim/tests/test_modificateurs.py -q -k test_sans_modificateur_la_photographie_a_365_jours_est_celle_d_avant` ;
  - `python3 -m pytest forge/tests/test_forge.py -q -k test_forge_ia_sans`.

  Les deux sont verts avec leurs empreintes inchangées. Contre-épreuve, dans
  `test_famine.py -k coupee` : sans `couper_la_famine`, 60 ticks de la graine 0
  laissent au moins une pose dans `monde.modificateurs`. La coupure est donc
  bien ce qui garde ces octets.
- **SC7 — Les tests existants qui comptent les poses, les naissances ou les
  morts restent verts, sans être touchés.** Rejoue chacun avec `-k` :
  - `sim/tests/test_modificateurs.py` : `test_les_donnees_disent_les_grandeurs_du_moteur`,
    `test_une_pose_datee_expire_et_une_source_se_retire`,
    `test_natalite_et_mortalite_d_une_cellule`,
    `test_le_service_et_la_photographie_servent_le_detail`,
    `test_le_document_dit_le_nom_de_la_grandeur_le_mot_de_la_source_et_le_reste`,
    `test_le_reste_d_une_pose_datee_se_compte_depuis_le_tick_publie`,
    `test_l_amorcage_sert_paris_et_ses_cinq_poses` ;
  - `sim/tests/test_survie.py` : `test_dette_alimentaire_ferme_la_natalite`,
    `test_ration_exacte_ouvre_la_natalite`,
    `test_natalite_remainder_sentinelle_et_amorcage`,
    `test_la_demographie_repond_a_la_natalite` ;
  - `sim/tests/test_lieux.py` : `test_demographie_locale_natalite` ;
  - `sim/tests/test_soudure.py` : `test_la_premiere_annee_tient_sans_joueur`
    (la famine n'ôte que des naissances : aucune mort de faim de plus) ;
  - `sim/tests/test_foyers.py` : `test_bras_suffisent_un_an` ;
  - `sim/tests/test_ville1400.py` : `test_sc1_meme_ville_apres_un_an` ;
  - `sim/tests/test_monde.py` : `test_service_reponse_figee_places_et_anciens_champs`,
    `test_service_reponse_figee_maitres_et_anciens_champs`,
    `test_logement_sans_geste`.

  Si l'un d'eux rougit à cause de la famine, ne le change pas : arrête-toi et
  dis lequel, avec son écart. Un test existant ne s'assouplit jamais.
- **SC8 — Les contrôles statiques.** Commande :
  `python3 -m pytest sim/tests/test_no_hardcoded.py sim/tests/test_write_coverage.py -q`.
  Ce sont deux analyses AST, courtes. `sim/evenements.py` n'y porte aucun
  littéral numérique hors de {0, 1, −1}.

Le relecteur vérifie six choses :
- le diff de `test_modificateurs.py` se borne à la fixture et à la ligne de
  coupure du test des 365 jours, et `forge/tests/test_forge.py` n'apparaît pas
  au diff ;
- `EMPREINTES_365` et les empreintes de `test_forge_ia_sans` sont identiques à
  `origin/master` ;
- `_apply_natalite` et `_apply_mortality` sont inchangés ;
- la famine ne crée ni ne détruit aucun kilo (SC4) ;
- la phrase « Le joueur » est vraie : la ligne servie se lit
  « Natalité : −50 % Famine · événement · encore N jours » dans le format de
  `InfobulleDeTerre.cs` ;
- SC8 passe.

## Hors périmètre
- Unity : l'infobulle n'est pas modifiée. Dire `fin_date` (« jusqu'au … »)
  plutôt que « encore N jours » à l'écran est un lot `pc` à part.
- La Concorde : `sim/jauges.py` la baisse déjà avec la faim (#1039). Le lot
  n'ajoute aucune pose sur une jauge.
- Toute autre règle du monde : la natalité pendant la faim ou la dette reste
  nulle, la mortalité et la dette sont inchangées, et le secours (#424) garde
  son seuil.
- Le fil des nouvelles (#1028) : il lira cette pose, et ce lot n'écrit aucune
  nouvelle.
- L'IA : elle ne lit pas la famine pour décider.
- D'autres événements (épidémie, bonne récolte) : ce lot ne pose que la famine.
