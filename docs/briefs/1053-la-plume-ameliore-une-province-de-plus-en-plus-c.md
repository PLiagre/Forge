# Lot #1053 — La Plume améliore une province, de plus en plus cher
Jalon : J5 · Machine : vps · Taille prévue : 600 lignes

## But
Une maison, celle du joueur comme celle de l'IA, peut toujours dépenser sa Plume pour améliorer une de ses provinces : chaque niveau coûte plus cher que le précédent et fait récolter de vrais kilos en plus dans la cellule.

## Le joueur
Le joueur dépense sa Plume pour améliorer une de ses provinces. Ce geste ne s'épuise jamais : il reste toujours une province à améliorer, et chaque niveau coûte plus cher que le précédent (6 points, puis 9, puis 13,5…).

Sa Plume lui pose désormais un vrai choix : affermir la concorde (50 points), ou améliorer une province de plus. Et laquelle : sa capitale déjà améliorée, à un coût qui monte, ou une province neuve encore à 6 points.

Un chef médiocre (gestion 1, 6 points par an) paie le premier niveau en un an. Le joueur voit l'effet là où il le cherche : l'infobulle du lieu survolé (#1031, livrée) lit déjà `/modificateurs` et y montrera « Province améliorée : Récolte +2 % ». La récolte de la province grandit de vrais kilos, et `/pays` lui donne, pour chacune de ses provinces, son niveau, le prix du suivant et, s'il ne peut pas payer, la raison du refus.

Aujourd'hui, il fait le geste par `POST /intention`. Un lot `pc` du panneau du pays le mettra sous un bouton. Pour le jalon 5, ce lot est le geste « qui ne s'épuise jamais » que le propriétaire a voulu dans sa réponse B à #1027 : l'IA le peut dès ce lot, par le même chemin. Le troisième morceau de #1027 lui donnera sa raison de le faire, pour que chaque maison de l'IA dépose au moins un geste par an sur dix ans (la preuve du jalon).

## Règle du monde
D'après `jeu/sim/MODELE.md`, « Le pays et ses jauges » (complétée par ce lot), « Les modificateurs » et « Les intentions du joueur ». Toutes les valeurs sont de niveau 2 : plausibles, jamais sourcées.

- **Les données.** `data/jauges.toml` gagne une table `[amelioration_de_province]` :
  - `nom` = « Améliorer une province », et un `dit` ;
  - `reserve = "plume"` (une des réserves de `[points]`) ;
  - `cout_premier_niveau = 6`, `facteur_par_niveau = 1.5`.
  - `modificateur = "amelioration_de_province"`.

  `data/modificateurs.toml` gagne la définition `amelioration_de_province` : nom « Province améliorée », grandeur `recolte`, valeur 0,02, portée `cellule`, `duree_jours = 0`.

  `lire_regles` valide la table et la range dans un champ neuf de `Regles` (pas dans `gestes` : le panneau de #1046 ne doit pas la voir). Il refuse avec sa raison :
  - une réserve inconnue ;
  - un `cout_premier_niveau` qui n'est pas strictement positif ;
  - un `facteur_par_niveau` qui ne dépasse pas 1 (« coût croissant attendu ») ;
  - un modificateur absent des données, qui ne se pose pas sur une cellule ou dont la grandeur n'est pas lue par le moteur.
- **Le coût.** Pour une province au niveau `k` (0 si elle n'a jamais été améliorée), le niveau suivant coûte `cout_premier_niveau × facteur_par_niveau ** k` points de Plume, soit 6, 9, 13,5, 20,25… Le coût n'est pas arrondi, et les raisons l'écrivent au dixième par `_points`.

  Un chef de gestion 1 gagne 0,5 point par mois, donc 6 points en douze mois (les mois tombent aux ticks 30, 60, …, 360). Le premier niveau est payable en un an.
- **Le niveau, dans le monde.** `World.niveaux_de_province` (cell_id → niveau entier ≥ 1) ne garde que les cellules améliorées. `to_dict()` le porte sous `niveaux_de_province`, trié par cell_id, seulement s'il n'est pas vide : la photographie de la graine 0 au 365e jour garde ses octets.

  Le niveau appartient à la cellule, pas à la maison : `cell_id` reste la seule clé. Une province qui changera de maître (la conquête, plus tard) garde son niveau.
- **Le geste.** L'intention neuve `ameliorer_une_province` a pour champs obligatoires `type`, `maison` et `cell`. Elle passe par `recevoir_intention`, du joueur (`POST /intention`, sans garde de plus dans le service) ou de l'IA (`ia.jouer_ia`).

  Le dépôt refuse, avec sa raison et sans rien écrire au monde :
  - une maison inconnue ou mal formée : « maison inconnue ou mal formée : 'x' » ;
  - un `cell` qui n'est pas un entier : « cell invalide : entier attendu, reçu True » ;
  - une cellule inconnue : « cellule inconnue : -1 » ;
  - une cellule dont le bourg (rang 0) est tenu par un autre maître : « pas sur vos terres : le bourg de la cellule N est à 'grande-3' », même mot que les bâtiments ;
  - une Plume insuffisante : « pas assez de points de Plume : 9 points demandés, 6 points disponibles ».

  **La Plume engagée compte les deux sortes de gestes.** Au dépôt, la Plume disponible est l'état de la maison moins le coût de tous ses gestes déjà déposés pour le tick : ses `depenser_jauge` (le coût en Plume d'« Affermir la concorde ») et ses `ameliorer_une_province`. Une deuxième amélioration de la même cellule dans le même tick coûte le niveau d'après.

  `verifier_geste` (pour `depenser_jauge`) compte aussi les améliorations déjà déposées. Sinon, 50 points paieraient au dépôt une amélioration puis « Affermir la concorde », et le tick lèverait `JaugeInvalide`.
- **L'application, à l'étape des intentions du tick suivant.** La Plume est revérifiée sans relire le registre ni les maîtres (comme `appliquer_geste`, `registre=False`). Puis :
  1. la Plume baisse du coût ;
  2. le niveau de la cellule monte de 1 ;
  3. `modificateurs.poser` pose `amelioration_de_province` sur `("cellule", cell_id)` sous la source `jauge:province:<cell_id>-<niveau>`.

  Chaque niveau a ainsi sa propre pose. Au niveau 2, le facteur de récolte vaut `1 + fsum(0,02, 0,02)` = 1,04.
- **Les poses des jauges ne l'effacent pas.** Aujourd'hui, `jauges.poser_les_modificateurs` retire toute pose dont la source commence par `jauge:`. Ce lot restreint ce retrait aux sources `jauge:<nom>:` des jauges des règles (`concorde`, `renom`, `droit`). Les poses `jauge:province:…` survivent au mois et aux gestes. `lire_regles` refuse une jauge qui s'appellerait `province`.

  `modificateurs_de` et `jauges.modificateurs` dans `/pays` ne changent pas : `ClientPays` n'y accepte que `jauge:<jauge servie>:<maison>`.
- **L'économie reste physique (décision 35).** Le geste ne coûte et ne crée aucun kilo : il dépense des points. Son modificateur multiplie la récolte, que le moteur lit déjà (`engine._apply_production`, `_verser_recolte`). Le grain en plus naît aux champs de la cellule, entre aux paniers, se prélève et se mange. Aucun code du moteur ne change.
- **Servi dans `/pays`, sous `jauges`.** `document_des_jauges` gagne la clé `amelioration`, qui contient :
  - `nom`, `dit` et `reserve` ;
  - `modificateur` : `nom`, `grandeur`, le nom de la grandeur (« Récolte ») et la `valeur` par niveau ;
  - `provinces` : pour chaque cellule dont la maison tient elle-même le bourg, triée par cell_id, `cell_id`, `niveau` (0 si jamais améliorée), `cout` du niveau suivant et `refus` (la raison du dépôt, ou `null`).

  Comme pour les gestes de #1046, `/pays` ne compte pas les gestes déjà déposés. `jauges.gestes` (deux gestes, lus par le panneau de #1046 et par la capture `Lot1046`), `jauges.grandeurs` et `jauges.modificateurs` restent identiques à l'octet.
- **L'IA, par le même chemin (décision 38).** Elle n'a pas encore de règle pour améliorer : c'est le troisième morceau de #1027. Sa porte vers le monde reste `jouer_ia` → `recevoir_intention`. Une maison de l'IA qui dépose l'intention obtient le monde qu'obtient le joueur qui dépose la même.
- **MODELE.md.** « Le pays et ses jauges » gagne une puce « Améliorer une province » : coût, niveau, pose, source, raisons, Plume engagée commune, ce que sert `/pays`. Le niveau 2 des trois valeurs (6, 1,5, +2 %) est dit à la fin de la section.

## Périmètre
jeu/data/jauges.toml
jeu/data/modificateurs.toml
jeu/sim/jauges.py
jeu/sim/intentions.py
jeu/sim/world.py
jeu/sim/MODELE.md
jeu/sim/tests/test_pays_et_jauges.py

## Conditions de succès
Tous les tests neufs vont dans `jeu/sim/tests/test_pays_et_jauges.py`, qui porte l'invariant des jauges. Leur nom contient `amelioration`. Aucun test existant n'est modifié.

- **SC1 — Les données.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "amelioration and donnees" -q`.
  - `charger_regles()` donne la table ci-dessus : réserve `plume`, 6, 1.5, `amelioration_de_province`.
  - `charger_donnees().definitions["amelioration_de_province"]` vaut (`recolte`, 0.02, `cellule`, 0).
  - Contre-épreuve (paramétrée, sur le document réel modifié en mémoire) : `lire_regles` lève `JaugeInvalide` avec le bon motif pour chacun de ces cas :
    - `facteur_par_niveau = 1` → « coût croissant » ;
    - `cout_premier_niveau = 0` ;
    - `reserve = "grain"` ;
    - un modificateur inconnu ;
    - le modificateur `jauge-…` d'une portée `pays` ;
    - une jauge nommée `province`.
- **SC2 — De plus en plus cher, et le premier niveau payable en un an.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "amelioration and cher" -q`.
  - Une fonction du test, `_couts_croissants(regles, niveaux=20)`, vérifie que le coût du niveau `k+1` dépasse strictement celui du niveau `k` pour `k` de 0 à 19, et que le premier vaut 6.
  - Le test dérive des données (`J.competences`) une maison dont le chef a une gestion de 1 et qui tient le bourg d'une cellule. Un échantillon vide échoue.
  - Sur une copie du départ, après `365 // FENETRE_FLUX_TICKS` = 12 appels à `J.mettre_a_jour`, sa Plume vaut 6 et le dépôt de l'amélioration passe. Après 11 appels (5,5 points), il se refuse avec « pas assez de points de Plume : 6 points demandés, 5,5 points disponibles ».
  - Contre-épreuve : des `Regles` où `facteur_par_niveau` est forcé à 1.0 par `dataclasses.replace` (sans passer par `lire_regles`) font lever `AssertionError` à `_couts_croissants` (`pytest.raises`). Un niveau sans coût croissant fait échouer le test.
- **SC3 — Les refus, avec leur raison, sans toucher au monde.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "amelioration and refus" -q`.
  - Chaque raison de « Le geste » est obtenue mot pour mot, Plume manquante comprise, avec ses nombres. La province d'un autre maître est une cellule dont le bourg est tenu par une autre maison, trouvée sur le monde.
  - Après chaque refus, `to_dict()` est identique à l'octet et `intentions_en_attente` est vide.
  - Plume engagée commune, avec 55 points :
    - une amélioration (6 points) est acceptée, puis « Affermir la concorde » (50 points) est refusé avec « 49 points disponibles » ;
    - dans l'autre ordre, sur une copie, « Affermir la concorde » passe, puis l'amélioration est refusée avec « 5 points disponibles ».
  - Avec 15 points, deux améliorations de la même cellule sont acceptées (6 + 9) ; une troisième est refusée avec « 13,5 points demandés, 0 point disponible ».
  - Contre-épreuve : le même premier dépôt avec 6 points passe. C'est bien la Plume qui refuse.
- **SC4 — Le niveau, la pose, et la récolte de la cellule en vrais kilos.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "amelioration and kilos" -q`.
  - Après le dépôt et un tick :
    - `niveaux_de_province == {cid: 1}` ;
    - la Plume a baissé de 6 exactement ;
    - le grenier de la maison n'a pas bougé du fait du geste (comparé au même tick sans dépôt) ;
    - la seule pose neuve est (`amelioration_de_province`, `recolte`, 0.02, (`cellule`, cid)), sous `jauge:province:<cid>-1`.
  - Au tick suivant, comparé au même monde sans la pose (`M.retirer`), avec la mesure de `_verser_recolte` du test du moulin : la cellule reçoit exactement ×1,02 (rel 1e-12), et toute autre cellule est identique.
  - Un second niveau coûte 9, pose `…-2`, et la cellule récolte ×1,04 contre le monde sans ses deux poses. Le deuxième niveau a coûté plus que le premier.
  - La pose survit à `J.mettre_a_jour` et à un « Affermir la concorde » appliqué.
  - Contre-épreuves :
    - la mesure faite contre un monde qui garde la pose doit lever `AssertionError` (`pytest.raises`) : la récolte est la même ;
    - l'ancien retrait de `poser_les_modificateurs` (toute source `jauge:`), remis par `monkeypatch`, fait disparaître la pose après le mois, et la vérification de survie lève `AssertionError`.
- **SC5 — Le joueur et l'IA, même monde, octet pour octet.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "amelioration and meme_monde" -q`.
  - Le test prend une maison de l'IA (`toutes_les_maisons_de_l_ia`, clé `ia._cle_du_grenier`) qui tient le bourg de la cellule de sa capitale, avec 20 points de Plume.
  - Côté IA : `ia.jouer_ia` est joué avec `ia.decider_intentions` remplacé (`monkeypatch`) par la seule proposition `ameliorer_une_province` de cette maison. Le relevé la dit acceptée.
  - Côté joueur : sur une copie d'avant, la même intention est déposée par `recevoir_intention`, la porte de `POST /intention`.
  - Un tick chacun, avec des copies du même aléa : les deux `to_dict()` sont identiques à l'octet, et `niveaux_de_province` y figure.
  - Même graine et mêmes gestes, sur 35 ticks : même monde.
  - Contre-épreuve : le joueur qui améliore une autre cellule de la même maison donne des octets différents (`!=`).
- **SC6 — Servi dans `/pays`, sous `jauges`, sans changer les gestes du panneau.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "amelioration and service" -q`.
  - Avec un `ServeurMonde` (`127.0.0.1`, port 0), `jauges.amelioration` donne le nom, la réserve et le modificateur (avec « Récolte »). Ses `provinces` sont exactement les cellules dont la maison tient le bourg, relues sur le monde, chacune avec son niveau, son coût et son refus.
  - `set(jauges["gestes"]) == {"affermir_la_concorde", "asseoir_le_droit"}`. `jauges.grandeurs` et `jauges.modificateurs` égalent ceux d'avant le geste.
  - `POST /intention` répond `200` à l'amélioration payable, puis `400` avec, mot pour mot, le `refus` que `/pays` servait pour une province trop chère. Après `POST /tick?n=1`, `/pays` sert le niveau 1 et le coût de 9.
  - Contre-épreuve : la province d'un autre maître n'apparaît pas dans `provinces`, et son dépôt par `POST /intention` répond `400` « pas sur vos terres ».
- **SC7 — Rien d'autre ne rougit.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py sim/tests/test_modificateurs.py sim/tests/test_batiments.py sim/tests/test_intentions.py sim/tests/test_determinisme.py -q`, puis `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "raisons_egalent_le_monde or ia_rejeu_octets or ia_mesure_reelle" -q`.
  - Tout passe sans qu'un test existant soit modifié, en particulier :
    - `test_le_service_sert_le_pays_et_ses_jauges` et `test_le_service_dit_les_jauges_et_ce_qu_elles_posent` (`grandeurs` figé à trois) ;
    - les octets de la photographie du 365e jour (`test_modificateurs.py`) ;
    - la liste des sources admises (`test_modificateurs.py`, inchangée : la source reste de sorte `jauge`) ;
    - la liste des types déposés par l'IA dans `test_monde.py` (l'IA ne dépose pas encore ce geste).
  - Contre-épreuve : un `to_dict()` qui porterait `niveaux_de_province` même vide fait rougir le test des octets du 365e jour. On le constate une fois à la main, sans le commettre.

## Hors périmètre
- La raison de l'IA pour améliorer, et son geste de points par mois (concorde, droit, province) : c'est le troisième morceau de #1027, qui ajoutera ce type à la liste des intentions de l'IA de `test_monde.py` et sa preuve des dix ans.
- Le bouton dans le panneau du pays, dans Unity : un lot `pc` du jalon 6 lira `jauges.amelioration`. Ici, `jauges.gestes` ne change pas.
- Une amélioration qui donnerait autre chose que de la récolte (bras, levée, prélèvement), ou un plafond de niveau.
- Un niveau qui se perd, et ce que devient le niveau à la conquête : il reste à la cellule.
- Une nouvelle sorte de source dans `data/modificateurs.toml` : la Plume est une réserve du pays, et la sorte `jauge` (« jauge du pays ») la dit déjà.
- Toute modification du moteur (`engine.py`, `modificateurs.py`), du service (`service.py`) et de l'IA (`ia.py`) : la récolte est déjà lue, et `POST /intention` laisse passer tout type que `recevoir_intention` connaît.
- Des valeurs sourcées : 6 points, ×1,5 par niveau et +2 % de récolte restent de niveau 2.
