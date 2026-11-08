# Lot #1036 — Le marché et la grange, deux bâtiments de province de plus
Jalon : J6 · Machine : vps · Taille prévue : 550 lignes

## But
Une maison, celle du joueur comme celle de l'IA, choisit pour une province entre trois bâtiments payés au même grenier : le moulin (plus de grain), le marché (plus de commerce) et la grange (moins de départs). Chacun a son prix, et chacun change sa grandeur au tick près.

## Le joueur
Pour une province, le joueur choisit entre un moulin (plus de grain), un marché (plus de commerce) et une grange (moins de départs). Il y a trois prix, trois effets et un seul grenier pour les payer. Ce lot prépare le geste du jalon « poser ses bâtiments dans ses provinces sans descendre en 3D », et la décision « où va le grain de l'année : à quel bâtiment de quelle province, au grenier, ou laissé aux gens ». Avec un seul moulin, il n'y avait pas d'arbitrage. Désormais, 3 000 kg au grenier paient le moulin et la grange, mais pas le marché en plus : le refus le dit avec ses chiffres. Le joueur l'éprouve aujourd'hui par `POST /intentions`. Le lot #1034 (pc) mettra le geste sur la carte : il lit `data/batiments.toml` et y trouvera les trois bâtiments sans autre travail.

## Règle du monde
D'après `jeu/sim/MODELE.md`, « Les bâtiments de province » (complétée par ce lot), « Les modificateurs », « Le commerce entre cellules » (« La capacité d'une arête ») et « Les départs » :

- **Les données (niveau 2, plausibles, non sourcées).** Les deux nouveaux bâtiments s'ajoutent à `data/batiments.toml` sur le modèle du moulin (`pieces = 0`, `un_par_cellule = true`) :
  - le **marché** : 900 journées, 30 bras par jour, soit 2 700 kg au salaire de base. Il pose le modificateur `marche` (grandeur `commerce`, +0,20, portée `cellule`, `duree_jours = 0`) ;
  - la **grange** : 400 journées, 20 bras par jour, soit 1 200 kg. Elle pose `grange` (grandeur `departs`, −0,25, portée `cellule`, `duree_jours = 0`) ;
  - le moulin reste tel quel (600 journées, 20 bras, 1 800 kg, récolte +0,10).

  Un champ optionnel `genre` (« m » par défaut, ou « f ») accorde le refus du doublon : « un seul marché par province », « une seule grange par province ». Le message du moulin reste mot pour mot celui d'aujourd'hui. Une autre valeur de `genre` se refuse dans `lire_types`.
- **L'économie reste physique (décision 35).**
  - Le marché ne crée aucun kilo. Il multiplie par 1,20 la capacité de chaque arête terrestre qui touche sa cellule (`_capacite_modifiee`, lue au bourg). Ce qui passe en plus est du grain qui existait déjà.
  - La grange multiplie par 0,75 la part des foyers qui partent de chacun des lieux de sa cellule (`departs.appliquer_departs`). Les partants restent des foyers entiers.
  - Aucun code du moteur ne change : les deux grandeurs sont déjà lues (`lue = true`).
- **Le prix et le refus.** Le geste reste `batir_dans_une_province`, avec la même vérification (`batiments.verifier`) :
  - un grenier qui ne paie pas toutes les journées, en comptant ce que la maison a déjà déposé pour le tick, se refuse : « grenier insuffisant : X kg de grain demandés, Y kg disponibles » ;
  - une cellule qui a moins de paysans que les bras d'un jour du bâtiment se refuse : « pas assez de bras » ;
  - le moulin, le marché et la grange se paient au même grenier, et chacun avec son prix.
- **L'IA, par le même chemin (décision 38).** Le jour du mois où elle règle sa part, une maison de l'IA pèse les trois bâtiments pour la cellule de sa capitale, en cinq règles :
  1. Elle n'a aucun bâtiment de province en chantier : un chantier à la fois.
  2. Elle ne trace pas de route et n'ouvre pas son grenier ce jour-là.
  3. Le bâtiment n'est pas encore bâti ni déposé, et son grenier dépasse sa réserve voulue plus le coût de ce bâtiment.
  4. Parmi ces bâtiments, elle prend le premier dont la raison tient, dans cet ordre :
     - **le moulin** d'abord : la règle `moulin_quand_le_grenier_le_permet` ne change pas. Le grain nourrit tout le reste ;
     - puis **la grange**, si la province perd des gens : `grange_quand_les_gens_partent`. Sur la fenêtre de trente jours, la somme des `partis` des lieux de la cellule dépasse la somme de leurs `arrives` (`flux.flux_de_lieu`). Sa raison porte `partis_30j`, `arrives_30j`, `grenier_nourriture_kg`, `reserve_voulue_kg` et `cout_kg` ;
     - puis **le marché**, si la province commerce par ses frontières : `marche_quand_la_province_commerce`. Sur la fenêtre, la somme des `envoye_kg` et `recu_kg` de `flux.commerce_par_voisine` sur la cellule est positive. Sa raison porte `commerce_30j_kg`, le grenier, la réserve et le coût.
  5. Elle dépose par `recevoir_intention`. Le joueur qui dépose la même intention obtient le même monde, octet pour octet. Sa réserve voulue compte déjà les salaires qui restent à payer.

## Périmètre
jeu/data/batiments.toml
jeu/data/modificateurs.toml
jeu/sim/batiments.py
jeu/sim/ia.py
jeu/sim/MODELE.md
jeu/sim/tests/test_batiments.py
jeu/sim/tests/test_monde.py

## Conditions de succès
- **SC1 — Les données.** Commande : `cd jeu && python -m pytest sim/tests/test_batiments.py -k "donnees" -q`.
  - Ce que vérifie le test : `charger_types()` donne exactement le moulin, le marché et la grange, avec les journées, les bras, les pièces, les modificateurs et `un_par_cellule` ci-dessus. `charger_donnees().definitions` donne `marche` = (`commerce`, 0.20, `cellule`, 0) et `grange` = (`departs`, -0.25, `cellule`, 0). Le moulin est inchangé.
  - Contre-épreuve : une grange qui nomme un modificateur de portée `lieu` se refuse dans `lire_types`, de même qu'un `genre` qui ne vaut ni « m » ni « f ».
- **SC2 — Le refus avec sa raison, un seul grenier.** Commande : `cd jeu && python -m pytest sim/tests/test_batiments.py -k "refuse or grenier" -q`. Le test part de Paris et de son maître, au départ, grenier vide.
  - Le marché se refuse avec « grenier insuffisant : 2700 kg de grain demandés, 0 kg disponibles », et la grange avec « … 1200 kg … ».
  - Avec 3 000 kg au grenier : le moulin est accepté. Le marché se refuse ensuite avec « grenier insuffisant : 2700 kg de grain demandés, 1200 kg disponibles ». La grange est acceptée, puis une seconde grange se refuse avec « une seule grange par province ».
  - Une cellule de la maison qui a moins de 30 paysans refuse le marché (« pas assez de bras : 30 paysans par jour demandés »).
  - Chaque refus laisse `to_dict()` identique à l'octet.
  - Contre-épreuve : le même dépôt du marché avec 4 500 kg au grenier passe. C'est bien le grain qui refuse, pas la nature du bâtiment.
- **SC3 — Le marché achevé change le commerce de sa cellule, au tick près, et rien d'autre.** Commande : `cd jeu && python -m pytest sim/tests/test_batiments.py -k "marche_acheve" -q`. Le test joue un marché à Paris jusqu'à son achèvement.
  - Une copie du monde est gardée avant le tick d'achèvement. Ses `facteurs_du_tick` n'ont aucune entrée `commerce`. Après ce tick, ils ont `commerce` = 1.20 pour chaque lieu de Paris, et rien d'autre de nouveau.
  - La pose est (`marche`, `commerce`, 0.20, (`cellule`, Paris)), sous la source `batiment:marche-<id>`.
  - Au tick suivant, on le compare au même monde sans la pose (`M.retirer`), par `engine._capacites_aretes` sur le même index : chaque arête qui touche Paris vaut exactement ×1.20, et toutes les autres sont identiques.
  - La récolte versée de chaque cellule (mesure du test du moulin) et le prélèvement du jour (`flux.jours[t].preleve`) sont identiques au kilo.
  - Contre-épreuve : la même comparaison faite avec la pose du moulin à la place de celle du marché doit lever `AssertionError` (`pytest.raises`) : la récolte de Paris diffère et les arêtes ne bougent pas.
- **SC4 — La grange achevée change les départs de sa cellule, au tick près, et rien d'autre.** Commande : `cd jeu && python -m pytest sim/tests/test_batiments.py -k "grange_achevee" -q`.
  - La grange est jouée à Paris jusqu'à son achèvement. La vérification « au tick près » est la même que pour SC3 : il n'y a aucune entrée `departs` avant le tick d'achèvement, et `departs` = 0.75 pour chaque lieu de Paris après.
  - On vide ensuite le bourg de Paris de son grain, comme `test_departs_d_un_lieu`, dans le monde et dans sa copie sans la pose, et l'on joue un tick.
  - Résultat attendu : le bourg a strictement moins de `partis`, avec un témoin à plus de 0. Aucun lieu de Paris n'en a plus. Les `partis` de tout lieu hors de Paris sont identiques. La récolte versée et `convois` sont identiques.
  - Contre-épreuve : la même comparaison avec une pose `departs` de +0,25 (une grange qui ferait fuir) doit lever `AssertionError`.
- **SC5 — L'IA pèse les trois par le même chemin.** Commande : `cd jeu && python -m pytest sim/tests/test_batiments.py -k "ia" -q`.
  - Le test reprend le montage de `test_l_ia_batit_par_le_meme_chemin` : une grande maison, grenier à 1e8, au jour de sa part.
  - Un moulin achevé dans sa capitale, avec des départs nets sur la fenêtre (forcés par le bourg vidé) : l'IA propose la grange, sous `grange_quand_les_gens_partent`, et sa raison égale le monde relu sans `sim/ia.py`.
  - Le moulin et la grange achevés : elle propose le marché, sous `marche_quand_la_province_commerce`.
  - Avec un chantier de province en cours : elle ne propose rien.
  - Le joueur qui dépose les mêmes intentions donne le même `to_dict()` au tick suivant.
  - Contre-épreuve : une raison de grange faussée d'un foyer (`partis_30j` + 1) et une raison de marché faussée d'un kilo doivent lever `AssertionError` dans le contrôleur des raisons.
  - `test_l_ia_batit_par_le_meme_chemin` reste vert tel quel : le moulin vient d'abord.
- **SC6 — Les raisons de l'IA égalent le monde sur cent jours.** Commande : `cd jeu && python -m pytest sim/tests/test_monde.py -k "raisons_egalent_le_monde or ia_rejeu_octets or ia_mesure_reelle" -q`.
  - Dans `test_monde.py`, la lecture du monde au tick, sans `sim/ia.py`, choisit sa règle selon la nature du bâtiment. `_lire_moulin` reste mot pour mot ; s'y ajoutent `_lire_grange` et `_lire_marche`.
  - `_controler_raisons_du_pays` gagne deux branches, pour la grange (`partis_30j > arrives_30j` et grenier > réserve + coût) et pour le marché (`commerce_30j_kg > 0` et grenier > réserve + coût). Aucune assertion existante n'est retirée ni desserrée.
  - Contre-épreuve : celle du moulin faussé d'un kilo reste en place.
- **SC7 — Rien d'autre ne rougit.** Commande : `cd jeu && python -m pytest sim/tests/test_batiments.py sim/tests/test_modificateurs.py sim/tests/test_intentions.py sim/tests/test_monde.py sim/tests/test_pays_et_jauges.py -q`. Tout passe sans qu'un test existant soit modifié, hormis les deux ajouts de SC6.
  - Contre-épreuve : remettre l'ordre grange avant moulin dans `ia.py` fait rougir `test_l_ia_batit_par_le_meme_chemin`. On le constate à la main une fois, sans le commettre.

## Hors périmètre
- Le geste sur la carte dans Unity, avec la liste des trois bâtiments et leur prix : c'est le lot #1034 (pc).
- La parcelle que le plan trouverait au bâtiment dans le bourg (l'horizon de la 3D).
- Un coût en pièces : il arrive avec le jalon 8, et `pieces = 0` reste refusé autrement.
- Les modificateurs des bâtiments dans l'infobulle Unity : c'est le lot #1031.
- Des valeurs sourcées pour un marché ou une grange de 1400 : on reste au niveau 2.
- La récolte perdue par les ouvriers d'un chantier, dans `recolte_perdue_par_chantier` (niveau 3).
- Un ordre de l'IA qui comparerait les trois bâtiments en une seule unité, kilos contre foyers. Ici, l'ordre est fixé, et chaque raison est lue sur le monde.
- Toute modification du moteur (`engine.py`, `departs.py`, `modificateurs.py`) : les grandeurs `commerce` et `departs` sont déjà lues.
