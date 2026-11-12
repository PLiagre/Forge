# Lot #1054 — L'IA garde des raisons d'agir chaque année
Jalon : J5 · Machine : vps · Taille prévue : 750 lignes

## But
Chaque maison de l'IA sur la carte agit au moins une fois par an pendant dix ans, la cinquième année comme la première : le jour de sa part, elle dépose au plus un geste de points (concorde, Droit, province), baisse sa part quand son grenier déborde, et chaque geste dit sa raison, lue sur le monde.

## Le joueur
Les voisins du joueur ne s'endorment pas. La cinquième année comme la première, chaque maison prélève, rouvre son grenier, bâtit, affermit sa concorde, assoit son droit ou améliore une province, et dit pourquoi.

Le joueur lit ces gestes dans le journal des voisins (`/ia`, et dans Unity le dossier des voisins). Chacun porte sa raison : « sa concorde est sous son neutre », « son Droit est sous son maximum », « sa province la moins chère coûte 9 points », « son grenier dépasse deux fois sa réserve ». C'est le geste du jalon 5, « s'en méfier ou s'en servir ». Une maison qui assoit son droit ou améliore ses terres devient plus forte, et le joueur le voit. Une maison qui baisse sa part parce que son grenier déborde est riche, et il le voit aussi.

L'IA n'a aucun bonus (décision 38) : elle paie avec les mêmes points que le joueur et passe par la même porte, `recevoir_intention`.

Ce lot est de fond, côté monde. Aujourd'hui, la vue Unity du journal écrit « Raison non interprétée par cette vue » pour tout ce qui n'est pas une route. Un lot `pc` du jalon 5 dira ces raisons en phrases. Ici, le monde les produit, les sert dans `/ia`, et la preuve des dix ans les relit sur le monde au même tick.

## Règle du monde
D'après `jeu/sim/MODELE.md`, « Les décisions et les gestes de l'IA » (la part du mois) et « Le pays et ses jauges » (les gestes, l'amélioration d'une province, la puce « L'IA »). Les deux sections sont complétées par ce lot. Toutes les valeurs sont de niveau 2 : plausibles, jamais sourcées.

- **Le jour.** Rien ne change pour le jour : c'est le jour de la part (`_jour_de_la_part`, `crc32` de la clé modulo `FENETRE_FLUX_TICKS`), avec la fenêtre des flux pleine. Hors carte, ou pour la maison du joueur (même un départ en attente) : aucun geste, comme aujourd'hui.
- **Au plus un geste de points par maison et par mois.** `_proposition_de_jauge` devient `_proposition_de_points(monde, maison, cle, regles)`. Elle rend au plus une proposition : le premier geste de cette liste qui est voulu et payable.
  1. **Affermir la concorde.** La Concorde est strictement sous son `neutre`, et `jauges.verifier_geste(…, 'affermir_la_concorde', …)` rend `None`. L'intention est `depenser_jauge`. La raison `concorde_sous_son_neutre` est inchangée : `concorde`, `neutre`, `plume`, `cout`.
  2. **Asseoir le droit.** Le Droit est strictement sous son `maximum` (100 dans `data/jauges.toml`), et `verifier_geste(…, 'asseoir_le_droit', …)` rend `None`. L'intention est `depenser_jauge` / `asseoir_le_droit`. La raison neuve `droit_sous_son_maximum` porte `droit`, `maximum`, `sceau`, `cout` (le dict des données), `concorde` et `plume`.
  3. **Améliorer sa province la moins chère.** Les provinces candidates sont les cellules dont la maison tient elle-même le bourg (rang 0, `maitre == cle`), comme dans `_document_de_l_amelioration`. On prend celle dont `jauges.cout_du_niveau_suivant` est le plus bas ; à coût égal, la plus petite `cell_id`. Il faut que `jauges.verifier_amelioration` rende `None` **et que la Concorde ne soit pas sous son neutre**. Une maison dont la Concorde est sous son neutre garde sa Plume pour elle : pas de province tant qu'elle ne l'a pas affermie. Le Droit, payé en Sceau, n'attend pas la Concorde. L'intention est `ameliorer_une_province` (`maison`, `cell`). La raison neuve `province_la_moins_chere` porte `cell_id`, `niveau` (avant le geste), `cout`, `plume`, `concorde`, `droit` et `sceau`.

  Le premier point de la liste ne retient pas les autres : une concorde sous son neutre mais pas encore payable laisse passer le Droit. « Dès qu'il est payable » : la maison dépose le geste le premier mois où il est payable.
- **La part baisse quand le grenier déborde.** `_proposition_de_part` garde ses deux branches, dans cet ordre :
  - une perte nette d'au moins `TAILLE_FOYER`, ou un lieu affamé : la part baisse ;
  - sinon, un grenier sous la réserve voulue : la part monte.

  Elle en gagne une troisième. Sinon, si `grenier_nourriture_kg > IA_GRENIER_PLEIN_FOIS_LA_RESERVE × reserve_voulue_kg` (constante neuve, `2`, dans `constants.py`), la part baisse de `IA_PAS_DE_PART`, sans descendre sous 0. À exactement deux fois la réserve, elle se tait. Une part déjà à 0 se tait aussi (`nouvelle == part`).

  La raison garde son nom (`part_sur_projets_et_gens`) et ses champs : le grenier et la réserve y sont déjà, et le seuil se relit dans la constante. La vue Unity et son test, qui citent ce nom, restent justes.
- **L'ordre des propositions d'une maison, le jour de sa part :** route, secours, part, geste de points, bâtiment. C'est l'ordre d'aujourd'hui, où le geste de points prend la place de la concorde. La règle « un chantier à la fois » du bâtiment ne change pas. Le geste de points ne dépense pas de grain et n'empêche pas le bâtiment.
- **Le même chemin (décision 38).** `jouer_ia` dépose tout par `recevoir_intention`. La Plume engagée commune de #1053 (concorde et améliorations du même tick) s'applique telle quelle : un seul geste de points par mois n'en demande pas plus. Une maison de l'IA qui dépose une intention obtient le monde qu'obtient le joueur qui dépose la même.
- **Rien d'autre ne change.** Le moteur, les jauges (`sim/jauges.py`), les intentions, le service et les données sont intacts. Seul `constants.py` gagne une constante.
- **MODELE.md.**
  - Dans « Les décisions et les gestes de l'IA », le paragraphe de la part gagne la troisième branche, avec `IA_GRENIER_PLEIN_FOIS_LA_RESERVE`. Un paragraphe neuf, « Le geste de points du mois », dit la liste, l'ordre, la Plume gardée pour la Concorde, les trois raisons et leurs champs, et « au plus un par mois ».
  - Dans « Le pays et ses jauges », la puce « L'IA » renvoie à ce paragraphe. La phrase « L'IA n'a pas encore de règle pour l'améliorer (#1027) » est retirée.
  - La mesure des dix ans (SC5) y est écrite, avec sa date.

## Périmètre
jeu/sim/ia.py
jeu/sim/constants.py
jeu/sim/MODELE.md
jeu/sim/tests/test_intentions.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_pays_et_jauges.py

## Conditions de succès
Aucune empreinte épinglée ne change. Aucune ne joue l'IA au-delà du tick 30, et à 31 ticks aucune maison n'a encore 6 points : au premier mois, une compétence de 10 donne 5 points. La part du tick 30 change peut-être, mais seuls des tests sans hachage la lisent (`test_forge_ia_boucle` compare à un témoin rejoué). Aucun fichier d'empreinte n'est donc au Périmètre. Si l'un rougit quand même, le lot s'arrête et le dit : ce serait une règle mal posée, pas une empreinte à recapturer.

Les réécritures autorisées par la réponse B du 10/11/2026 sont exactement celles de l'issue :
- `test_ia_part_sur_un_an` et ses aides `_nouvelle_part`, `_lire_raison_part` et `_controler_parts` (`test_intentions.py`) ;
- la table de `test_service_ia_raison` (`test_monde.py`) ;
- `_lire_jauge` et `_controler_raisons_du_pays` (`test_monde.py`), plus la liste des types admis dans `_verifier_raisons`, qui gagne `ameliorer_une_province`.

Chacune reste au moins aussi stricte : aucune assertion retirée sans une plus forte à sa place. Tout autre test existant passe sans modification.

- **SC1 — Le geste de points du mois, sa liste et son ordre.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "ia_points" -q`. Les tests neufs, nommés `test_l_ia_points_…`, partent de `_monde_au_mois` sur la maison `seigneurie-1`, portée à son jour de part comme dans `test_l_ia_depense_ses_jauges_par_le_meme_chemin`.
  - Concorde −1, Plume 60, Sceau 40, Droit 50 : un seul geste de points, « Affermir la concorde », raison `concorde_sous_son_neutre`.
  - Concorde 0, Sceau 40, Droit 50, Plume 60 : « Asseoir le droit », raison `droit_sous_son_maximum`, avec `droit == 50`, `maximum == 100` et `sceau == 40`.
  - Concorde 0, Droit 100, Plume 20 : `ameliorer_une_province` sur la cellule au coût le plus bas parmi celles dont le bourg est à la maison, relues sur le monde (plus petite `cell_id` à égalité). Après un niveau posé à la main sur cette cellule (`niveaux_de_province`), le choix passe à la suivante la moins chère.
  - Concorde −1, Plume 20 (moins de 50), Sceau 0 : aucun geste de points, et surtout aucune province : la Plume est gardée. Avec Sceau 40, « Asseoir le droit » passe.
  - Dans chaque cas, la maison a au plus un geste de type `depenser_jauge` ou `ameliorer_une_province` dans `decider_intentions`, et aucun un autre jour que son jour de part.
  - Contre-épreuves :
    - une `_proposition_de_points` remise à l'ancienne par `monkeypatch` (la concorde seule) fait échouer les cas 2 et 3 (`pytest.raises(AssertionError)`) ;
    - une version qui rend tous les gestes payables fait échouer « au plus un » ;
    - une version sans la Plume gardée fait échouer le cas 4.
- **SC2 — Même chemin, même monde.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py -k "ia_points and chemin" -q`.
  - Sur le monde du cas 3 de SC1, `_controle_chemin_unique` (importé de `test_intentions.py`) passe avec `ia.jouer_ia` et `type_present='ameliorer_une_province'`.
  - Le joueur qui dépose, sur une copie, les mêmes intentions acceptées obtient, après un tick avec des copies du même aléa, un `to_dict()` identique à l'octet. `niveaux_de_province` y porte la cellule choisie.
  - Contre-épreuve (celle de l'issue) : une IA qui appelle `jauges.appliquer_amelioration` dans le monde au lieu de déposer l'intention fait échouer `_controle_chemin_unique` (`pytest.raises(AssertionError)`).
- **SC3 — La part baisse quand le grenier déborde ; ses tests réécrits, aussi stricts.** Commande : `cd jeu && python3 -m pytest sim/tests/test_intentions.py -k "ia_part" -q`.
  - `_nouvelle_part` gagne la troisième branche.
  - `_lire_raison_part` compte aussi, comme `_reserve_lue` de `test_monde.py`, les journées des bâtiments de province encore dues par la maison. Sans cela, sa réserve diverge de celle de l'IA dès qu'une maison bâtit.
  - `_controler_parts` admet une baisse seulement pour perte, faim ou grenier strictement au-dessus de deux fois la réserve. Une hausse n'est admise que si le grenier est sous la réserve, sans perte ni faim. Tout jour lu sans entrée garde `_nouvelle_part(raison) == raison['part']`.
  - L'année doit montrer les trois branches : baisse nette, hausse, et baisse « grenier plein ». Mesure du chef, graine 0, 365 jours avec la règle d'aujourd'hui : 229 jours de part sur 26 maisons avaient un grenier au-dessus de deux fois la réserve, sans perte ni faim ni grenier bas (67 pertes, 35 hausses). La branche neuve se verra donc dès la première année.
  - Un test neuf `test_ia_part_baisse_quand_le_grenier_deborde` part du monde de `test_ia_part…` sur `seigneurie-6` :
    - un grenier à `2 × reserve_voulue_kg + 1` baisse la part de `IA_PAS_DE_PART`, raison `part_sur_projets_et_gens` égale à `_lire_raison_part` ;
    - à `2 × reserve_voulue_kg` exactement, rien ;
    - à part 0, rien.
  - Contre-épreuves :
    - toutes celles de `test_ia_part_sur_un_an` restent (raison faussée d'un départ, baisse retournée en hausse, relevé vide) ;
    - en plus, une baisse dont la raison porte un grenier ramené à `1,5 × reserve` fait échouer `_controler_parts` ;
    - la copie d'avant de `_nouvelle_part` (deux branches), passée à `_controler_parts`, échoue sur un relevé qui contient une baisse « grenier plein ».
  - `test_ia_part_documentation` passe sans modification. Un test neuf exige `IA_GRENIER_PLEIN_FOIS_LA_RESERVE`, `droit_sous_son_maximum` et `province_la_moins_chere` dans la section. Contre-épreuve : la section retirée échoue.
- **SC4 — Les juges des raisons relisent les règles neuves.** Commande : `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "raisons_egalent_le_monde or service_ia_raison" -q` et `cd jeu && python3 -m pytest sim/tests/test_batiments.py -q`.
  - `_lire_jauge` lit la raison selon le geste déposé : `concorde_sous_son_neutre` ou `droit_sous_son_maximum`.
  - Un `_lire_amelioration` neuf recalcule sur le monde, sans `sim/ia.py` (`_noms_sans_ia`), la province la moins chère et les champs de `province_la_moins_chere`.
  - `_controler_raisons_du_pays` gagne deux branches :
    - Droit : `droit < maximum`, `sceau >= cout['sceau']`, et le geste de la concorde ni voulu ni payable ;
    - province : `concorde >= neutre`, `plume >= cout`, le Droit ni voulu ni payable, et `cout` égal au plus petit coût relu.

    La branche `else` actuelle devient explicite (`concorde_sous_son_neutre`). Une règle inconnue lève `AssertionError`.
  - La table de `test_service_ia_raison` est indexée par le geste : `tracer_route`, `fixer_part`, `ouvrir_grenier`, `depenser_jauge` (selon `geste`), `ameliorer_une_province` et `batir_dans_une_province` (selon `nature`). Un type absent de la table fait échouer `verifier` par `AssertionError`, pas par `KeyError`.
  - Contre-épreuves de `test_service_ia_raison` :
    - les deux cas écrits à la main restent ;
    - une `ameliorer_une_province` portant `concorde_sous_son_neutre` échoue ;
    - un `asseoir_le_droit` portant `concorde_sous_son_neutre` échoue.
  - Dans `test_ia_raisons_egalent_le_monde` (inchangé), une province de l'IA dont le `cout` est faussé d'un point doit faire échouer `_controler_raisons_du_pays`. Ce cas s'écrit dans le test neuf de SC5, pour ne pas toucher l'existant.
- **SC5 — La preuve : dix ans, chaque maison de la carte, chaque année.** Commande : `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "ia_garde_des_raisons" -q`.
  - Un seul test, `test_ia_garde_des_raisons_d_agir_dix_ans`, sans fixture partagée : sous `pytest-xdist`, une fixture de module se rejouerait sur chaque travailleur.
  - Il joue `cli._simulate(3650, 0, ia=True)` : graine 0, sans joueur, le mois des jauges compris. Il passe par `_verifier_raisons` (enveloppes de `cli.tick` et `cli.jouer_ia`), qui gagne :
    - la lecture de `fixer_part` par `_lire_raison_part`, importé de `test_intentions.py` comme `_lecture_secours` ;
    - celle d'`ameliorer_une_province` par `_lire_amelioration`.
  - Le juge, `_juger_dix_ans(releve, lectures, maisons, hors_carte)`, exige :
    - **les maisons comptées depuis le registre** : `maisons_de_l_ia(World.charger(0))`. Les 35 maisons sur la carte (`hors_carte is None`, `cell_id` non nul) ; le nombre est relu, pas écrit en dur, et un échantillon de moins de 35 échoue. La maison hors carte, les Djötchides (`grande-21`, « Le siège de la Horde d'Or… est à l'est des polygones de la carte figée »), est nommée dans le message, avec sa raison `hors_carte` relue au registre, et n'a aucune entrée au relevé ;
    - **chaque année** `a` de 1 à 10 (ticks `365 × (a − 1)` à `365 × a − 1`) : chaque maison de la carte a au moins une entrée sans `refus`. Le message nomme l'année et les maisons qui manquent ;
    - **chaque raison relue** : toute entrée acceptée, de tout type, égale la lecture du monde faite à son tick. Les routes passent par `_controler_raisons`, les secours par la lecture `_lecture_secours` du même tick, et les gestes de pays par `_controler_raisons_du_pays`. Les parts sont lues par `_lire_raison_part` et tenues par `_nouvelle_part`. Une entrée d'un type sans lecteur fait échouer le juge ;
    - au moins un geste de chacun des trois gestes de points, et une baisse « grenier plein » (SC3) sur les dix ans.
  - Le test imprime, par année, le nombre de maisons actives et le compte de chaque geste. Ces chiffres et la durée vont dans MODELE.md.
  - Coût : sur ce VPS, une année d'IA a pris 265 s (mesure du chef, 12/11/2026). Les dix ans prennent donc environ 45 min, et les cinq ans de SC6 environ 22 min. Chaque preuve est un seul test, que les tranches de la CI placent selon sa durée mesurée (`tranches.py`). Le lot ne touche pas aux tranches.
  - Contre-épreuves, sur le même relevé :
    - le juge appelé avec une liste de maisons vide, ou un relevé vide, lève `AssertionError` (échantillon vide) ;
    - le relevé privé de toutes les entrées d'une maison pour une année échoue, et le message nomme cette maison ;
    - une raison de province faussée d'un point (le cas de SC4) échoue.
- **SC6 — L'IA d'aujourd'hui échoue.** Commande : `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "ia_d_avant_s_endort" -q`.
  - Le test neuf `test_ia_d_avant_s_endort_la_cinquieme_annee` copie dans le fichier la règle d'avant le lot :
    - la proposition de concorde seule ;
    - la part à deux branches.

    Il les remet dans `sim.ia` par `monkeypatch`, et joue `cli._simulate(1825, 0, ia=True)`.
  - Le juge de SC5, restreint à la cinquième année, doit lever `AssertionError` (`pytest.raises`). Le test imprime le nombre de maisons actives cette année-là (l'issue mesurait 11).
  - Sans la copie (règle neuve), la même restriction passe : c'est SC5.
- **SC7 — Rien d'autre ne rougit.** Commande : `cd jeu && python3 -m pytest sim/tests/test_pays_et_jauges.py sim/tests/test_intentions.py sim/tests/test_batiments.py sim/tests/test_programme_ia.py sim/tests/test_determinisme.py sim/tests/test_modificateurs.py -q`, puis `cd jeu && python3 -m pytest sim/tests/test_monde.py -k "ia" -q`, puis `cd jeu && python3 -m pytest forge/tests/test_forge.py -k "ia" -q`.
  - Tout passe, en particulier sans modification :
    - `test_l_ia_depense_ses_jauges_par_le_meme_chemin` (un seul geste pour `seigneurie-1` au premier mois) ;
    - `test_ia_ordre_route_secours_part` (monde sans points : aucun geste de points) ;
    - `test_ia_rejeu_octets` (le rejeu par `--gestes` rejoue aussi les améliorations) ;
    - `test_ia_mesure_reelle` ;
    - les tests `test_forge_ia_*`.
  - Contre-épreuve : la constante `IA_GRENIER_PLEIN_FOIS_LA_RESERVE` mise à 1 par `monkeypatch` fait échouer le cas « à exactement deux fois, rien » de SC3.

## Hors périmètre
- Les phrases de ces raisons dans Unity (dossier des voisins) : un lot `pc` du jalon 5. Ici, `/ia` les sert telles quelles.
- Un deuxième geste de points dans le mois, l'Épée, le Renom : aucun geste ne les dépense encore.
- Toute modification de `sim/jauges.py`, `sim/intentions.py`, du moteur, du service ou des données (`data/jauges.toml`, `data/modificateurs.toml`) : les gestes, leurs coûts et la Plume engagée existent depuis #1046 et #1053.
- Une cause du monde qui ferait baisser le Droit (la succession contestée, #435/#436), ou remonter la Concorde d'elle-même.
- Le choix de la province par autre chose que son coût (récolte, faim, frontière) : niveau 3, pour plus tard.
- La maison hors carte : elle reste sans geste, nommée par la preuve.
- Le budget du tick : ce lot ne mesure ni ne promet un temps d'image.
