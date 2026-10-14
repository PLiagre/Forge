# Lot #603 — /lieu dit le nom, le prélevé et les départs de chaque lieu
Jalon : J3 · Machine : vps · Taille prévue : 285 lignes

## But
Chaque lieu publié par `/lieu` et par la photographie dit son nom, ce que son maître y a prélevé et les personnes qui en sont parties ou y sont arrivées sur les trente derniers jours, par une seule fonction commune.

## Le joueur
Le joueur peut lire, lieu par lieu, ce que la carte de J3 doit lui montrer : le nom de chaque lieu de sa cellule, ce qu'il y a pris en un mois, et ceux qui en sont partis ou y sont arrivés. Il voit ainsi le lieu qu'il saigne et celui qui se vide, au lieu d'un total de maison. Lot de fond, sans écran neuf : il prépare le geste de J3, fixer sa part et ouvrir son grenier, en lui donnant la mesure de ce que coûte sa part, lieu par lieu. La carte de la forge (#401) le montrera, puis la carte Unity (#403, #405).

## Règle du monde
Sans objet : aucune règle nouvelle, aucune constante, le tick ne change pas. Lot de lecture, sous-lot 3 de #400. Dépend de #601 (registre `World.flux`, `flux_de_lieu`) et de #602 (`/maisons`, `/maison`), livrés. Il s'appuie sur `jeu/sim/MODELE.md`, « Les flux sur trente jours » (fenêtre `FENETRE_FLUX_TICKS`, prélevé d'un lieu relu comme part × récolte, départs en personnes brutes par `(cell_id, rang)`), « Ce que porte un lieu » (publication par `lieux_en_photographie`) et « Les lieux d'une cellule, vue dérivée » (bloc `noms`).

**Ce que publie chaque lieu.** Deux clés s'ajoutent aux six actuelles :
- `nom` : le nom du lieu, celui de l'entrée de même `rang` dans `noms[cell_id]["lieux"]` (`noms_depuis_monde`). On ne le recalcule pas : on reprend le bloc déjà publié.
- `flux_30j` : `{"preleve_kg": float, "partis_personnes": int, "arrives_personnes": int}`. Les noms suivent `flux_30j` de `/maison` (#602). Les valeurs sont celles de `flux_de_lieu` (`preleve_kg`, `partis`, `arrives`), sans arrondi, comme le reste des lieux. `preleve_kg` est toujours un `float` (`0.0` avant le premier prélèvement).

Sans bloc de noms ou sans flux fournis (monde de fortune, appel à la main), `lieux_en_photographie` déclare `"nom": None` et `"flux_30j": None` : rien n'est deviné, comme `point` aujourd'hui. Pour un monde sans registre, la nouvelle fonction rend les mêmes zéros que `flux_de_lieu`.

**Une seule passe.** Nouvelle fonction `flux_des_lieux(monde)` dans `sim/flux.py` : elle rend, pour toute cellule, la liste par rang des trois valeurs. Elle parcourt une fois les jours de `_jours_de_fenetre`, dans leur ordre. Pour chaque lieu, les sommes se font dans le même ordre que `flux_de_lieu`, ce qui rend les deux égales au bit près. `lieux_en_photographie(cid, cell, places=None, noms=None, flux=None)` reçoit le bloc de la cellule et son entrée de `flux_des_lieux`. Trois appelants passent par elle :
- `ServeurMonde._construire_etat` : `self._noms` déjà en cache, un seul `flux_des_lieux` par publication ;
- `build_snapshot_document` : les lieux se remplissent après le calcul des `noms`, qu'il faut donc avancer ;
- `_image_du_monde` de la chronique : `test_la_decoupe_rend_la_photographie_au_bit_pres` exige que ses lieux égalent la photographie.

`flux_de_lieu` n'est appelé par aucun d'eux. Mesuré le 14/10 sur srv1914711, graine 0, au tick 35 (6 619 lieux, fenêtre pleine) :
- une passe coûte 37 à 53 ms (un pic à 72 ms) ;
- `flux_de_lieu` appelé sur chaque lieu coûte 140 ms ;
- `noms_depuis_monde` coûte 660 ms.

La chronique ne doit donc pas recalculer les noms à chaque image. Les noms ne sont pas un champ mobile : `capturer` reprend le bloc `noms` des cellules du décor de t0 et le passe à `_image_du_monde`. Sans lui, `_image_du_monde` les calcule (`noms_depuis_monde`), et le test de découpe garde son appel à deux arguments.

**Ce qui ne bouge pas.** `/monde`, `to_dict`, `/maison`, `/maisons` et `SNAPSHOT_SCHEMA_VERSION` restent tels quels, comme les clés de premier niveau de `/lieu` et de la photographie. Les anciens champs d'un lieu ne changent pas. `nom` et `flux_30j` ne sont pas des clés d'identité (aucun `*_id`). Le contrôle de l'issue en découle : retirer `nom` et `flux_30j` de chaque lieu, puis resérialiser (`_serialiser` pour le service, `serialize_snapshot` pour la photographie), redonne les empreintes actuelles.

**À savoir sur la cadence.** Au tick 35, `_construire_etat` coûte déjà 128 à 185 ms. Tick et publication font 266 à 315 ms, au-dessus des 250 ms de la cadence à 4 jours/s. Ce dépassement existait avant ce lot. Le lot l'aggrave d'une passe, et seulement d'une : il le mesure et le déclare, sans le corriger. `test_horloge_pause_vitesse_et_budget` joue les ticks 0 à 12, où la fenêtre est courte.

**Documentation.**
- `MODELE.md`, « Ce que porte un lieu » : le paragraphe « Le service les publie » (« chacun avec exactement … ») nomme `nom` et `flux_30j`, avec leur source et `None` hors monde chargé.
- `MODELE.md`, « Les flux sur trente jours » : la phrase « Les lecteurs servent les preuves et le futur service » devient vraie au présent et nomme `flux_des_lieux`, qui sert `/lieu` et la photographie en une passe.
- Garder tous les mots que les tests exigent déjà dans ces deux sections.
- `jeu/ville/README.md` : la liste des champs d'un lieu servi reçoit `nom` et `flux_30j`.

Budget du diff, ajouts et retraits compris :

| poste | lignes |
|---|---:|
| code (`flux.py` 22, `snapshot_export.py` 12, `service.py` 4, `capture.py` 8) | 46 |
| `MODELE.md` et README | 20 |
| fichiers figés et `LecteurJsonTests.cs` | 6 |
| tests | 128 |
| brief | 85 |
| **total** | **≈ 285** |

## Périmètre
jeu/sim/flux.py
jeu/sim/snapshot_export.py
jeu/sim/service.py
jeu/vues/chronique/capture.py
jeu/sim/MODELE.md
jeu/ville/README.md
jeu/sim/tests/test_flux.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_lieux.py
jeu/forge/tests/test_forge.py
jeu/vues/chronique/tests/test_chronique.py
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick3.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/lieu-graine0-tick4.json
3d/unity/Assets/ForgeLocal3D/Pont/Tests/LecteurJsonTests.cs
docs/briefs/603-lieu-dit-le-nom-le-preleve-et-les-departs-de-cha.md

## Conditions de succès
Les commandes se lancent depuis `jeu/`, sauf SC9. Voir rouges les nouvelles preuves avant d'implémenter. Échantillons non vides, comptes dérivés des données.

L'issue autorise seulement les changements d'assertions existantes qui suivent :
- les ensembles exacts de clés d'un lieu reçoivent `nom` et `flux_30j` (`_CLES_D_UN_LIEU`, les deux ensembles de `test_lieux.py`, le tableau de `LecteurJsonTests.cs`) ;
- les empreintes complètes de `/lieu` (`test_service_ia_sans`) et de la photographie (`test_forge_ia_sans`) sont régénérées ;
- les deux fichiers figés sont régénérés ;
- avant chaque contrôle d'empreinte existant sur des lieux, une ligne retire `nom` et `flux_30j` de chaque lieu ; la valeur attendue et l'assertion qui suivent restent telles quelles.

Toute autre assertion, contre-épreuve et valeur reste intacte.

SC1 — `python3 -m pytest sim/tests/test_flux.py -q -k flux_des_lieux`. Nouveau test : jouer 35 ticks sur une copie du monde réel en enveloppant `flux.noter_personnes`, qui relève par tick les partis et arrivés, puis lire `flux_des_lieux`. Il exige :
- pour chacun des 6 619 lieux, l'égalité exacte (`==`) avec `flux_de_lieu`, avec `preleve_kg` de type `float` ;
- pour chaque maison routée, la somme du prélevé de ses lieux égale `flux_de_maison(...)["preleve_kg"]` (`rel=1e-12`), compté à part par le prélèvement, et au moins une est non nulle ;
- partis et arrivés égaux, lieu par lieu, au relevé indépendant des 30 derniers ticks, avec au moins un lieu non nul de chaque sorte ;
- au moins un jour retiré du registre (le jour 0 absent).

Contre-épreuves :
- ramener `FENETRE_FLUX_TICKS` à 29 à la lecture échoue au relevé ;
- une copie où un `taux` d'un jour est altéré échoue à la somme par maison ;
- une variante qui compte chaque jour deux fois échoue.

SC2 — `python3 -m pytest sim/tests/test_monde.py -q -k "lieux_de_la_photographie or sans_seconde_cle or flux_des_lieux"`. `_CLES_D_UN_LIEU` reçoit `nom` et `flux_30j`. Les tests existants gardent l'égalité servi = photographie aux ticks 3 et 4 et leurs contre-épreuves. Nouveau test, sur un `ServeurMonde` en processus amené au tick 35 :
- pour toutes les cellules, les lieux de `etat_publie.lieux` égalent ceux de `build_snapshot_document(serveur.world, 0, 35)` ;
- chaque `nom` est une chaîne non vide, égale à `noms[cell_id]["lieux"][rang]["nom"]` du même document ;
- `flux_30j` a exactement les clés `{"preleve_kg", "partis_personnes", "arrives_personnes"}` ;
- au moins un lieu a `partis_personnes > 0`, au moins un `arrives_personnes > 0`, et tout lieu routé a `preleve_kg > 0`.

Contre-épreuves :
- échanger les noms de deux lieux d'une copie échoue ;
- un service dont `_construire_etat` passe `flux=None` (monkeypatch) échoue à l'égalité avec la photographie.

SC3 — même commande que SC2 : un seul calcul par publication. Pendant un `_construire_etat` puis un `build_snapshot_document`, `flux_de_lieu` remplacé par une fonction qui lève n'est jamais appelé, et `flux_des_lieux` l'est exactement une fois par appel. Contre-épreuve : une version qui l'appelle cellule par cellule fait échouer le compte.

SC4 — `python3 -m pytest sim/tests/test_lieux.py -q -k "photographie_et_empreinte"`. Les deux ensembles exacts reçoivent `nom` et `flux_30j`. Toutes les autres preuves restent, dont l'égalité des maîtres et leurs contre-épreuves. Dans `test_photographie_et_empreinte_maitre_manuel_absent`, `lieux_en_photographie(1, cellule)` sans noms ni flux déclare `nom` et `flux_30j` à `None`. Contre-épreuve : une copie où `nom` vaut une chaîne échoue.

SC5 — `python3 -m pytest sim/tests/test_monde.py -q -k "service_ia_sans or reponse_figee or lecteur_json or noms_publication"`. Les ancres de ce SC :
- **régénérer** les deux fichiers figés depuis le vrai service (`_lancer_service_sans_part(0)`, `/tick?n=3` puis `n=4`, `/lieu?cell=9922`) ; `fige == servi` reste exigé ;
- **contrôle d'origine** : dans chaque fichier régénéré, retirer `nom` et `flux_30j` de chaque lieu, puis resérialiser par `_serialiser`, redonne l'ancien fichier octet pour octet. SHA-256 attendus : `55748f4bab604cd482274db8af1185601410518af2013a64b777631b70cddb31` (tick 3) et `42da176f1b979cce1172b8c13e0c01e6749f3fb00ba2a372e94b383d1a7a7fd7` (tick 4) ;
- **`test_service_ia_sans`** : régénérer seulement la nouvelle empreinte complète de `/lieu?cell=1175` et `/lieu?cell=9922` aux ticks 0 et 4. Après retrait des nouveaux champs, on retrouve exactement les valeurs actuelles :
  - `1d293e89…`, `05d131f4…` (tick 0) ;
  - `99f49272…`, `dde477e1…` (tick 4) ;
  - et, sans point ni noms, `c16d0b6f…`, `d8cabad6…`, `32c0fa20…`, `ea965093…`.

  `/monde` garde ses empreintes ;
- **C#** : le tableau des clés d'un lieu de `LecteurJsonTests.cs` (texte seul, aucune exécution Unity) devient l'ordre trié du service, `{ "flux_30j", "maitre", "nom", "point", "population", "rang", "stocks", "surface_km2" }`.

Contre-épreuves :
- changer une population dans la copie privée des nouveaux champs échoue à l'ancien SHA ;
- garder `nom` dans cette copie échoue aussi ;
- les contre-épreuves existantes (`ia`, octet altéré, maître changé, `"maitre", ` retiré du C#) restent.

SC6 — `python3 -m pytest forge/tests/test_forge.py -q -k forge_ia_sans`. Seule l'empreinte complète du fichier aux ticks 0 et 30 est régénérée. Retirer `nom` et `flux_30j` de chaque lieu, puis resérialiser par `serialize_snapshot`, redonne exactement `9a4dba1e…` (tick 0) et `a878777d…` (tick 30). La suite du test (points, noms, maîtres, `ia`, contre-épreuves) s'applique ensuite à cette copie, telle quelle. Contre-épreuve : changer un `preleve_kg` dans le document complet change la nouvelle empreinte.

SC7 — `python3 -m pytest vues/chronique/tests/test_chronique.py -q`. `test_la_decoupe_rend_la_photographie_au_bit_pres` et `test_les_champs_mobiles_sont_mesures_et_pas_declares` passent sans changement, avec les mêmes `CHAMPS_MOBILES`. Nouveau test : `capturer(3, 0)` appelle `noms_depuis_monde` exactement une fois, pour la photographie de t0. Contre-épreuve : une capture qui ne transmet pas les noms du décor compte quatre appels et échoue.

SC8 — `python3 -m pytest sim/tests/test_monde.py sim/tests/test_lieux.py sim/tests/test_flux.py ville/tests -q -k "documente or modele or documentation or contrat"`. Les contrôles existants (`test_service_maitre_documente_parmi_les_champs_servis`, `test_service_lieux_documentes_dans_le_modele`, `test_documentation_et_contre_epreuve`, `test_contrat_cell_id.py`) passent. On ajoute deux contrôles :
- « chacun avec exactement » nomme `` `nom` `` et `` `flux_30j` `` ;
- « Les flux sur trente jours » nomme `flux_des_lieux`.

Contre-épreuve : une copie du texte privée de `` `flux_30j` `` dans ce paragraphe échoue.

SC9 — Depuis la racine :
- `python3 -m pytest jeu/sim/tests/test_monde.py -q -k horloge_pause_vitesse_et_budget` réussit ;
- `python3 -m pytest jeu/sim/tests/test_maisons_servies.py -q -s -k mesure_matiere` imprime la médiane de `_construire_etat` au tick 35. La PR la donne avant et après le lot, mesurées en alternance dans la même séance ;
- `python3 -m pytest jeu -q` et `git diff --check` réussissent.

## Hors périmètre
- Aucun écran, aucune scène ni client Unity de production. Seul le texte de `LecteurJsonTests.cs` change, sans exécution Unity ni Blender.
- La carte de la forge (#401) et la preuve par rejeu, côté maison du joueur et suzerain (sous-lot 4 de #400) viennent après.
- Ne changent pas : `/monde`, `/maison`, `/maisons`, `to_dict`, le tick, `sim/prelevement.py`, `sim/departs.py`, `sim/engine.py`, `sim/noms.py`, `sim/maisons_servies.py`, les constantes et `SNAPSHOT_SCHEMA_VERSION`.
- Pas de dû, de reçu, de mangé en route ni de rendu par lieu : ce sont des comptes de maison, servis par `/maison`.
- La cadence du service à 4 jours/s, déjà dépassée au tick 35, n'est pas corrigée ici : mesurée et déclarée seulement.
- Aucun test assoupli. Tout chemin hors du périmètre est interdit.
