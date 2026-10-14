# Lot #604 — La photographie porte la maison du joueur et son suzerain, et la preuve rejoue
Jalon : J3 · Machine : vps · Taille prévue : 260 lignes

## But
Quand le joueur a choisi sa terre, la photographie porte la fiche de sa maison et celle de son suzerain, octet pour octet celles de `/maison`. Une partie rejouée par `python3 -m sim --gestes` redonne ces fiches, et chaque compte sur trente jours égale la somme des jours relevés un à un.

## Le joueur
Après ce lot, la photographie d'une partie dit au joueur ce que `/maison` lui dit en jeu, pour sa maison et pour celle de son suzerain : sa part, son grenier, ce qui est monté de ses lieux, ce qui est arrivé au grenier, ce qui est parti chez son suzerain, ce que les charretiers ont mangé, ce qu'il a rendu, et combien de gens sont partis ou arrivés en trente jours. Le journal de la forge lira donc la même chose que le jeu. La preuve rejoue « fixer sa part » puis « ouvrir son grenier ». Elle montre que ces chiffres disent ce que le monde a fait : ni le jour de trop, ni le jour oublié.

C'est un lot de fond. Il prépare la décision de J3, « prendre plus aujourd'hui ou garder ses gens », en garantissant que les chiffres où le joueur la lira sont justes. La carte de la forge (#401) la rendra visible au journal, puis la carte Unity (#403, #405).

## Règle du monde
Sans objet : c'est une vue. Aucune règle, aucune constante, aucun tick ne change, et `to_dict` reste tel quel. C'est le sous-lot 4 de #400. Il dépend de #602 (`sim/maisons_servies.py` : `matiere_des_maisons`, `document_de_maison`) et de #603 (`noms` et `flux_des_lieux` dans `build_snapshot_document`), tous deux livrés. Il s'appuie sur ces sections de `jeu/sim/MODELE.md` :
- « La photographie de 1400, vue dérivée » ;
- « Les maisons servies, vue dérivée » ;
- « Les flux sur trente jours » (fenêtre `FENETRE_FLUX_TICKS`, élagage à l'écriture).

**Décision du pilote (A, question technique du 14/10).** Les fiches n'apparaissent que si le joueur a choisi sa terre, comme le bloc `ia`, qui n'existe que s'il y a un relevé. Les deux tests « ne diffère que par la terre » les mettent de côté comme `terre_choisie`, vérifient qu'elles nomment sa maison et son suzerain, et comparent tout le reste à l'identique.

**Ce que fait le code (`jeu/sim/snapshot_export.py`).**
- Une fonction `_maisons_du_joueur(world, noms, places)` rend `None` si `world.maison_du_joueur is None`. Sinon elle rend `{"maison": <fiche>, "suzerain": <fiche ou None>}`. Les fiches viennent d'**un seul** `matiere_des_maisons(world, noms, places)` suivi de `document_de_maison` pour la maison du joueur et pour son `suzerain` du registre (`world.maisons`). Un suzerain `None` (une racine) donne `"suzerain": None`, ce qui est un fait. `noms` et `places` sont ceux que `build_snapshot_document` calcule déjà : rien n'est recalculé. Une `MaisonInconnue` devient `SnapshotExportError("maison inconnue : …")`, avec l'identifiant.
- `build_snapshot_document` l'appelle **après** `terre_choisie` : un identifiant mal formé lève toujours « seigneurie inconnue » en premier. La clé de premier niveau `maisons_du_joueur` est posée **après** `_round_tree`, comme `ia`, et seulement si la valeur n'est pas `None`. `/maison` sert les flux sans arrondi : arrondir rendrait l'égalité fausse (`_round_float` coupe à `SNAPSHOT_FLOAT_DECIMALS`, alors que le `preleve_kg` mesuré vaut 404681.8245188855).
- Sans joueur, rien ne change : mêmes clés, mêmes octets, même `SNAPSHOT_SCHEMA_VERSION`, aucun appel à `matiere_des_maisons`. `sim/maisons_servies.py`, `sim/service.py` et `/maison` restent tels quels.

**Mesures du chef** (14/10, srv1914711, graine 0) : monde chargé ; Duché de Bar choisi au tick 0 ; part 0,25 au tick 1 ; au tick 20, grenier ouvert pour `int(grenier // 2)` = 95 045 kg, sur un grenier de 190 091 kg ; 35 ticks en tout.
- La maison est `seigneurie-1` et son suzerain `grande-3`, une racine (`suzerain` vaut `None`).
- Fiche du joueur : `preleve_kg` 404 681,8 ; `recu_kg` 354 819,2 ; `du_envoye_kg` 39 424,4 ; `mange_en_route_kg` 7 432,2 ; `rendu_kg` 95 045,0 ; partis 0, arrivés 0 ; 4 lieux.
- Fiche du suzerain : `recu_kg` 377 117,6, partis 2 367 personnes.
- Le registre garde les jours 5 à 34. Le jour 4 (le 31e) a un prélevé non nul pour le joueur (11 319 kg).
- `matiere_des_maisons` et les deux fiches coûtent 28 ms. La photographie entière coûte déjà 23 s ; le lot n'y change rien de sensible.
- **Piège :** sous Python 3.12, `sum()` des flottants est compensé. La somme des jours relevés par `sum()` diffère alors d'un ulp de la fiche (354819.1708364306 contre 354819.17083643057). Le relevé doit s'accumuler par `+=`, jour après jour dans l'ordre, en partant de `0`, comme `matiere_des_maisons`.

**Documentation (`MODELE.md`).**
- La phrase « la photographie porte `terre_choisie`, `null` sans choix ; c'est sa seule différence » devient fausse. Elle doit nommer aussi `maisons_du_joueur`, absente sans choix.
- « La photographie de 1400, vue dérivée » reçoit un paragraphe : la clé, ses deux fiches tirées de `document_de_maison` sans arrondi, son absence sans choix, l'ordre après `terre_choisie`, et le refus « maison inconnue ».
- « Les maisons servies, vue dérivée » dit que la photographie réutilise `document_de_maison`.

Budget du diff, ajouts et retraits compris :

| poste | lignes |
|---|---:|
| `snapshot_export.py` | 18 |
| `MODELE.md` | 12 |
| réécriture des deux tests | 10 |
| nouveaux tests (`test_maisons_servies.py`) | 125 |
| brief | 95 |
| **total** | **≈ 260** |

## Périmètre
jeu/sim/snapshot_export.py
jeu/sim/MODELE.md
jeu/sim/tests/test_maisons_servies.py
jeu/sim/tests/test_monde.py
jeu/forge/tests/test_forge.py
docs/briefs/604-la-photographie-porte-la-maison-du-joueur-et-son.md

## Conditions de succès
Les commandes se lancent depuis `jeu/`, sauf SC6. Il faut voir les nouvelles preuves rouges avant d'écrire le code. Chaque contrôle est une fonction qui reçoit les documents, pour que sa contre-épreuve lui passe une copie altérée. Aucun identifiant ni aucune valeur n'est écrit en dur : tout se dérive du monde, du registre et des gestes.

La décision du pilote autorise seulement ces changements d'assertions existantes :
- dans `test_photographie_1400_terre` (`sim/tests/test_monde.py`) et dans `test_depart_et_photographie_ne_differe_que_par_la_terre` (`forge/tests/test_forge.py`), une ligne retire `maisons_du_joueur` du document avec joueur, à côté du retrait de `terre_choisie` ;
- ces deux tests gagnent des lignes qui vérifient : `["maison"]["id"]` vaut `f"seigneurie-{bar.id}"`, `["suzerain"]["id"]` vaut le `suzerain` de cette maison dans le registre (non `None` pour Bar), et le témoin sans joueur n'a pas la clé.

Toute autre assertion, contre-épreuve et empreinte reste intacte, dont `doc == sans`, `photographie == temoin` et le refus « seigneurie inconnue ».

SC1 — La preuve rejoue : `python3 -m pytest sim/tests/test_maisons_servies.py -q -k photographie_rejoue`. Nouveau test.

Le déroulé :
1. Le service tourne en processus (`_service_local`). On pose les gestes par `POST /intention` aux ticks qu'écrit le fichier des gestes :
   - tick 0 : `choisir_depart`, Duché de Bar, retrouvé par son nom dans `charger_seigneuries()` ;
   - tick 1 : `fixer_part` à 0,25 pour `serveur.world.maison_du_joueur` ;
   - tick 20 : `ouvrir_grenier` pour `kg = int(grenier // 2)`, où `grenier` est la nourriture lue dans `serveur.world.greniers` à ce tick ; on exige `kg > 0`.
2. On joue 35 ticks par `POST /tick?n=1`. Après chaque tick `t`, on relève le jour `serveur.world.flux.jours[t]` :
   - copie des cinq vecteurs aux indices de la maison du joueur et de son suzerain (`routes_des_lieux.noms`) ;
   - copie de `partis` et `arrives`.
3. On lit `/maison?id=` pour les deux maisons.
4. On écrit ces trois gestes dans un fichier, puis on lance `python3 -m sim --ticks 35 --seed 0 --gestes g.json --snapshot-json p.json` en sous-processus (le motif de `test_part_cli_determinisme`). La commande doit rendre 0.

Les contrôles :
- **égalité** : `p["maisons_du_joueur"] == {"maison": fiche du joueur servie, "suzerain": fiche du suzerain servie}`. Pour chaque fiche, `_serialiser` (de `sim.service`) donne exactement les octets servis par `/maison`. `tick` vaut 35 ;
- **identité** : la maison est `serveur.world.maison_du_joueur`, soit `f"seigneurie-{bar.id}"`. Le suzerain est son `suzerain` du registre ;
- **relevé** : pour chaque fiche, chacun des cinq kilos égale **exactement** (`==`) la somme, par `+=` à partir de `0`, des jours relevés 5 à 34 (les 30 derniers). Ni `sum()` ni `approx`. `partis_personnes` et `arrives_personnes` égalent la somme, sur les mêmes jours, des mouvements relevés pour les couples de `fiche["lieux"]` ;
- **échantillons non vides** : les cinq kilos du joueur sont > 0 ; `rendu_kg == kg` exactement ; `part == 0.25` ; `grenier` égale `serveur.world.greniers` du joueur ; `recu_kg` du suzerain est > 0 ; les deux fiches comptent au moins une personne partie ou arrivée. Le jour 4 relevé a un `preleve` > 0 pour le joueur : le 31e jour pèse.

Contre-épreuves :
- **31e jour** : `sim.constants.FENETRE_FLUX_TICKS` est mis à 31 (monkeypatch) pendant **toute** une course en processus, `sim.__main__._simulate(35, 0, gestes)`, puis on appelle `build_snapshot_document(world, 0, 35)`. Le contrôle du relevé échoue sur `preleve_kg`. Le patch doit couvrir la course entière, parce que le registre élague à l'écriture : patcher à la seule lecture ne garderait aucun jour de plus ;
- une copie de la photographie au `rendu_kg` augmenté de 1 échoue à l'égalité ;
- échanger les deux fiches échoue à l'identité ;
- un relevé sur 29 jours (6 à 34) échoue au relevé ;
- passer les fiches par `_round_tree` change au moins une valeur, et l'égalité échoue.

SC2 — La fonction et ses refus : `python3 -m pytest sim/tests/test_maisons_servies.py -q -k maisons_du_joueur`. Nouveau test sur un `World.charger(0)`, avec `noms_depuis_monde` et `places_du_monde` :
- sans choix, `_maisons_du_joueur` rend `None` ;
- avec `maison_du_joueur` posé sur la première terre, elle rend exactement les clés `{"maison", "suzerain"}`. Ces fiches égalent `document_de_maison(matiere_des_maisons(...), id)` pour les deux identifiants ;
- `matiere_des_maisons` est appelée une seule fois. On le vérifie en l'enveloppant par monkeypatch dans `sim.snapshot_export`.

Contre-épreuve : une copie du registre dont la maison du joueur a pour `suzerain` un identifiant absent (`dataclasses.replace`) lève `SnapshotExportError`, et le message nomme cet identifiant.

SC3 — Les tests réécrits :
- `python3 -m pytest sim/tests/test_monde.py -q -k "photographie_1400"` ;
- `python3 -m pytest forge/tests/test_forge.py -q -k "ne_differe_que_par_la_terre or carte_de_1400"`.

Les deux tests réécrits passent avec les seuls changements autorisés plus haut. Les refus (« seigneurie inconnue », Morée, `test_photographie_1400_refus`) passent sans changement.

Contre-épreuve ajoutée dans chacun : une copie du document avec joueur qui **garde** `maisons_du_joueur` échoue à l'égalité avec le témoin.

SC4 — Sans joueur, rien ne bouge :
- `python3 -m pytest sim/tests/test_monde.py -q -k "schema_ferme or photographie_1400_schema or snapshot_ia_sans or service_ia_sans"` ;
- `python3 -m pytest forge/tests/test_forge.py -q -k "forge_ia_sans or forge_ia_sorties"` ;
- `python3 -m pytest sim/tests/test_carte_servie.py -q`.

Ces commandes passent sans changement : `_ROOT_KEYS`, les empreintes de la forge aux ticks 0 et 30, et `/departs` égal à `terre_choisie`. Contre-épreuve : une version qui pose toujours la clé (à `null` sans joueur) fait rougir `test_schema_ferme_et_couches`. On le constate une fois, avant de livrer, sans l'écrire dans un test.

SC5 — Documentation : `python3 -m pytest sim/tests/test_maisons_servies.py -q -k "modele or photographie_documentee"`. `test_modele_et_contre_epreuve` passe sans changement. Nouveau test :
- la section « La photographie de 1400, vue dérivée » nomme `` `maisons_du_joueur` `` et `` `document_de_maison` `` ;
- le texte ne contient plus « c'est sa seule différence ».

Contre-épreuve : une copie du texte privée de `` `maisons_du_joueur` `` dans cette section échoue.

SC6 — Depuis la racine :
- `python3 -m pytest jeu/sim/tests/test_no_hardcoded.py jeu/sim/tests/test_write_coverage.py -q` réussit ;
- `git diff --check` réussit.

La CI joue la suite entière. La PR donne la durée du test de SC1.

## Hors périmètre
- `/maison`, `/maisons`, `/lieu`, `/monde`, `sim/service.py` et `sim/maisons_servies.py` ne changent pas.
- Ne changent pas non plus : `to_dict`, le tick, les constantes, `terre_choisie` et `SNAPSHOT_SCHEMA_VERSION`.
- Aucune fiche des autres maisons dans la photographie : seulement le joueur et son suzerain.
- Aucun dessin : la carte de la forge (#401) et Unity (#403, #405) viennent après. Pas de bloc IA neuf.
- La chronique (`vues/chronique/`) ne porte pas ces fiches : elle part d'un monde sans joueur.
- Aucun test assoupli. Tout chemin hors du périmètre est interdit.
