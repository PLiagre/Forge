# Lot #573 — La part du seigneur part en convoi et arrive à son grenier
Jalon : J3 · Machine : vps · Taille prévue : 290 lignes

## But
À chaque tick, chaque lieu tenu donne à son maître sa part de la nourriture qu'il vient de récolter ; cette part voyage en convoi le nombre de jours de sa route, se mange un peu chaque jour, puis entre dans le grenier du maître.

## Le joueur
Le joueur voit sa part arriver chaque jour dans son grenier, moins ce que mangent les charretiers : plus il prend, plus son grenier se remplit, et moins il reste à ses lieux. C'est la décision du jalon J3, « prendre plus aujourd'hui ou garder ses gens », qui devient réelle dans le monde : à Bar (`seigneurie-1`, cellule 10430), la part du bourg et du lieu de rang 2 arrive le lendemain, celle des rangs 1 et 3 deux jours après. Le joueur ne règle pas encore sa part à l'écran (#405) et ne voit pas encore les flux sur la carte (#400, #401) : ce lot fait exister le grenier qui se remplit, que ces lots montreront.

## Règle du monde
Suite de la section **« ## Le prélèvement »** de `jeu/sim/MODELE.md` (après le paragraphe de la route écrit par #572), et l'ordre du tick de **« ## En une page »**. Elle découle de « Le grenier d'une maison » (les paniers `World.greniers`, la perte du grenier), de « Les maisons du monde » (`World.parts`, la part coutumière) et de « Les lieux d'une cellule » (la récolte de chaque lieu).

**L'étape.** Nouvelle étape **Prélèvement** du tick, juste après la Production et avant le Commerce ; « En une page » et la docstring de `engine.tick` la numérotent (8) et décalent les suivantes. Dans cet ordre :
1. **Perte en route.** Chaque convoi en route perd `PERTE_CONVOI_PAR_JOUR` (0,01) de sa charge ; les kilos perdus s'ajoutent à `World.mange_convois_kg`, sans arrondi. Ils ne deviennent ni dette ni nourriture ailleurs.
2. **Arrivée.** Les convois dont le tick d'arrivée est le tick courant (`World.ticks_ecoules`, le compteur avance en fin de tick) versent leur charge dans la nourriture du grenier de leur maison (`MARCHANDISE_NOURRITURE`), puis quittent la liste.
3. **Départ.** Pour chaque lieu de la table `World.routes_des_lieux`, `kg = World.parts[maitre] × récolte du lieu ce tick`. La récolte du lieu est la part de surface que la Production vient d'ajouter à ce lieu (`recolte × surface du lieu / surface de la cellule`, ou toute la récolte de la cellule si elle n'a qu'un lieu) ; jamais son stock. Les `kg` sortent du panier du lieu **et** de celui de sa cellule, et partent dans le convoi `(maitre, tick courant + jours)`. Une part nulle ou une récolte nulle n'écrit rien : ni convoi, ni ligne de panier, ni compteur.

Un convoi parti au tick `t` perd donc sa part `jours` fois (ticks `t+1` à `t+jours`) et arrive au tick `t+jours` : **un grenier reçoit exactement `prélevé × (1 − PERTE_CONVOI_PAR_JOUR)^jours`**. Il commence à perdre sa part de grenier (`PERTE_GRENIER_PAR_AN`) au tick suivant son arrivée. Seule la nourriture voyage : minerai et objets restent au lieu (**niveau 3**, non simulé ici). Aucun aléa n'est tiré.

**Ce que le tick lit.** Le maître et les jours de chaque lieu viennent de la table du sous-lot 1 (`World.routes_des_lieux`), jamais de `EtatDeLieu.maitre` ni de `World.maisons` (`test_maitre_tick`, `_tick_sans_lecture_registre`). La part vient de `World.parts`, relue à chaque tick (un changement de part vaut dès le tick suivant). Un `World(...)` d'épreuve, dont la table est `{}`, ne prélève rien.

**L'état du monde.** `World.convois` : les convois en route, regroupés par (maison, tick d'arrivée), vides au chargement. `World.mange_convois_kg` : cumul, 0,0 au chargement. Les deux vivent sur le monde, sans variable de module ni `global`. `to_dict()` ajoute `"convois"` (liste de `[maison, tick_arrivee, kg]`, kg = charge courante, triée par tick puis maison) seulement si un convoi est en route, et `"mange_convois_kg"` seulement s'il n'est pas nul : une part nulle laisse les octets d'avant.

**Constantes**, dans `jeu/sim/constants.py`, chacune avec son commentaire :
- `PART_COUTUMIERE` passe de 0,10 à **0,03** (niveau 2, valeur provisoire mesurée sur le prototype : à 10 % la population perd 5,7 % en un an, à 3 % environ 1 % ; le sous-lot 3 de #396 la prouve) ;
- `PERTE_CONVOI_PAR_JOUR = 0.01` — la part de la charge que mangent charretiers et bêtes chaque jour (niveau 2, plausible, jamais sourcé).

Elles se lisent dans `sim/prelevement.py` par `constantes.X` relu à chaque appel, **jamais dans `sim/engine.py`** (`test_chaque_constante_du_moteur_change_le_monde`) ; `test_no_hardcoded` refuse tout autre littéral que 0, 1, −1.

**Code.** L'étape vit dans un module neuf, `jeu/sim/prelevement.py`, que `engine.py` appelle. `engine.py` n'importe pas `sim.convois` et ne lit pas l'attribut `routes_des_lieux` (`test_le_tick_ne_lit_pas_la_table`) : c'est `prelevement.py` qui lit la table. Pour que l'étape reste appelée par un attribut de module (les tests l'enveloppent), `engine.py` appelle `prelevement.prelever(...)`, pas un nom importé.

**Budget du tick : 4 ms de marge, une seule passe sur les lieux.** Le chef de la première tentative a mesuré un prototype (`/tmp/proto573/jeu/sim/prelevement.py`, à relire, pas à recopier sans le comprendre) : une version naïve coûtait 8 ms par tick ; la version retenue 3,3 ms, et `test_tick_sous_le_budget_du_service` y donne 93 à 99 ms contre 90 à 93 ms sans elle. La forme qui tient : la récolte de chaque lieu recueillie pendant la boucle de production de sa cellule (sans recalculer les surfaces) ; la table des routes parcourue dans ses tableaux (`cids`, `rangs`, `maitre_idx`, `jours`, déjà triés par cellule), avec un index par cellule ou par rang construit au chargement si besoin ; la part relue une fois par maître et par tick, pas par lieu ; les convois rangés par tick d'arrivée, chaque groupe gardant la charge par maison ; la perte du jour calculée **par groupe** (un facteur commun), pas convoi par convoi ; le retrait de la cellule fait une fois par cellule ; aucun tuple, aucune `Route`, aucun objet alloué par lieu. Conservation mesurée sur le prototype : 8e-15 en relatif sur un an. Le prototype fait rougir `test_service_reponse_figee_du_pont_est_celle_du_service` (vérifié par le chef) : voir « Les tests figés » ci-dessous.

**Les tests figés.** Les tests qui figent le monde d'avant mettent `PART_COUTUMIERE` à 0 **avant** `World.charger` dans leur mise en place (`monkeypatch.setattr(sim.constants, "PART_COUTUMIERE", 0)` : avec une part coutumière nulle, `parts` reste hors de `to_dict`), **sans perdre ni modifier une seule assertion, empreinte ou contre-épreuve** :
- `test_part_bit_pres`, `test_registre_bit_pres`, `test_grenier_bit_pres` (`jeu/sim/tests/test_determinisme.py`) ;
- `test_service_ia_sans`, `test_service_reponse_figee_places_et_anciens_champs`, `test_service_reponse_figee_maitres_et_anciens_champs` (`jeu/sim/tests/test_monde.py`) ;
- `test_forge_ia_sans` (`jeu/forge/tests/test_forge.py`) ;
- et, au même titre, `test_service_reponse_figee_du_pont_est_celle_du_service` et `test_service_reponse_figee_du_pont_tick4_est_celle_du_service` (`test_monde.py`) : ils comparent le service aux mêmes fichiers figés du pont, que l'issue interdit de toucher. La question de #396, à laquelle le propriétaire a répondu A, nommait déjà ces fichiers et ces tests parmi ceux qui rougissent ; l'issue a oublié de les recopier.

Les tests qui lancent le service dans un **processus** (`lancer_service`) ne voient pas un `monkeypatch` du processus de test : ils passent par une aide neuve de `test_monde.py`, sur le modèle de `_lancer_service_ia` (une enveloppe de `subprocess.Popen`), qui lance le même `sim.service` avec les mêmes arguments après avoir posé `PART_COUTUMIERE = 0` dans le processus fils (par exemple `python -c` qui pose la constante puis `runpy.run_module("sim.service", run_name="__main__", alter_sys=True)`). `lancer_service` lui-même ne change pas. Aucun fichier de `3d/` ne bouge.

## Périmètre
jeu/sim/prelevement.py
jeu/sim/engine.py
jeu/sim/world.py
jeu/sim/constants.py
jeu/sim/convois.py
jeu/sim/MODELE.md
jeu/sim/README.md
jeu/sim/tests/test_prelevement.py
jeu/sim/tests/README.md
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/test_monde.py
jeu/forge/tests/test_forge.py

## Conditions de succès
SC1 à SC6 dans le fichier neuf `jeu/sim/tests/test_prelevement.py`, lancé par `cd jeu && python3 -m pytest sim/tests/test_prelevement.py -q`. Le monde de la graine 0 se charge une fois par module (fixture `scope="module"`, chaque test travaille sur une `copy.deepcopy`). Chaque compteur est dérivé et affiché (`print`), jamais écrit en dur. Pour observer l'étape, les tests enveloppent `sim.prelevement.prelever` par `monkeypatch` (mesure avant, appel, mesure après). **Ne jamais lancer la suite entière** (`pytest jeu`, `sim/tests/` ou un dossier) : elle dépasse l'heure ; chaque commande ci-dessous vise un fichier, avec `-k` au besoin.

- **SC1 — Rien ne se crée, rien ne se perd, sur un an.** Graine 0, 365 ticks numérotés. Soit `T = Σ nourriture des cellules + Σ charge des convois en route + Σ nourriture des greniers + mange_convois_kg + pertes_kg`. À chaque tick, `T` est le même avant et après l'étape Prélèvement (relatif 1e-12), et, pour chaque cellule, ce que l'étape retire de la cellule égale ce qu'elle retire de la somme de ses lieux (relatif 1e-9). Sur l'année : `Σ prélevé = Σ arrivé aux greniers + charge en route à la fin + mange_convois_kg`, et `Σ arrivé = Σ greniers à la fin + pertes_kg` ; `Σ prélevé > 0`, le nombre de convois arrivés > 0 et `mange_convois_kg > 0`, affichés. Contre-épreuves : un prélèvement qui remplit les convois sans rien retirer des lieux ni des cellules fait échouer la conservation (`pytest.raises(AssertionError)`) ; un prélèvement qui ne retire que des lieux, pas de la cellule, fait échouer l'égalité cellule / lieux.
- **SC2 — Ce que reçoit le grenier.** Graine 0, `PERTE_GRENIER_PAR_AN` remplacée par 0 : toutes les parts à 0 sauf `seigneurie-1` (Bar) à 0,5, au tick 0 seulement, puis remise à 0. Au tick 0, l'enveloppe relève les kilos retirés de chaque lieu de Bar. Après chaque tick suivant, le grenier de Bar vaut exactement `Σ kg du lieu × (1 − PERTE_CONVOI_PAR_JOUR)^jours` sur les lieux dont la route (`routes_des_lieux[(cid, rang)].jours`) est arrivée (relatif 1e-12) ; après le dernier jour de route, plus aucun convoi de Bar n'est en route. Minerai et objets des lieux de Bar ne changent pas à l'étape. Contre-épreuves : `PERTE_CONVOI_PAR_JOUR` remplacée par 0 rend un grenier égal à `Σ kg`, différent de l'attendu ; au premier tick d'arrivée, le grenier ne contient que les lieux à un jour (différent du total).
- **SC3 — Plus il prend, plus son grenier se remplit, moins il reste à ses lieux.** Deux copies du monde, 30 ticks : Bar à `PART_COUTUMIERE`, puis Bar au décuple ; les autres maisons inchangées. Avec la part forte, le grenier de Bar est plus plein et la nourriture de ses quatre lieux plus basse (direction, pas valeur ; écarts affichés). Contre-épreuve : la même comparaison avec deux parts égales donne des greniers égaux.
- **SC4 — Une part nulle rend le monde d'avant.** `PART_COUTUMIERE` à 0 avant `World.charger(0)`, 30 ticks : `json.dumps(to_dict(), sort_keys=True)` et le `pickle` des cellules (comme `test_part_bit_pres`) sont égaux, octet pour octet, à ceux du même monde où `sim.prelevement.prelever` est remplacé par une fonction qui ne fait rien ; `"convois"`, `"mange_convois_kg"` et `"parts"` absents de `to_dict`. Contre-épreuves : à part 0,03, ces clés sont présentes et les empreintes diffèrent ; un `World(cells, adjacency)` d'épreuve tické deux fois garde `convois` vide et le compteur à 0. Puis les neuf tests figés, chacun seul :
  `python3 -m pytest sim/tests/test_determinisme.py -q -k "part_bit_pres or registre_bit_pres or grenier_bit_pres or maitre_tick"`,
  `python3 -m pytest sim/tests/test_monde.py -q -k "service_ia_sans or reponse_figee"`,
  `python3 -m pytest forge/tests/test_forge.py -q -k forge_ia_sans`.
  `git diff` de ces trois fichiers ne retire ni ne change aucune ligne `assert`, `pytest.raises` ou empreinte (vérifié par le relecteur) ; `git diff --stat -- ../3d` est vide.
- **SC5 — Le tick ne lit ni le maître ni le registre.** Par lecture AST : `engine.py` n'importe pas `sim.convois`, ne lit pas `routes_des_lieux` et ne lit pas `PERTE_CONVOI_PAR_JOUR` ni `PART_COUTUMIERE` ; `prelevement.py` ne lit ni l'attribut `maitre` ni `maisons`. Sur la graine 0, avec `EtatDeLieu.maitre` et `World.maisons` remplacés par des lecteurs qui lèvent (comme `test_maitre_tick`), trois ticks passent **et prélèvent** (`convois` non vide). Contre-épreuve : le détecteur AST appliqué au texte `"lieu.maitre"` le trouve. Puis `python3 -m pytest sim/tests/test_convois.py -q` et `python3 -m pytest sim/tests/test_write_coverage.py sim/tests/test_no_hardcoded.py -q` passent sans modification, et `python3 -m pytest sim/tests/test_maisons.py -q -k part` aussi.
- **SC6 — Le modèle le dit.** Un test lit la section « ## Le prélèvement » de MODELE.md et y trouve `PERTE_CONVOI_PAR_JOUR`, `mange_convois_kg`, `World.convois`, « (1 − PERTE_CONVOI_PAR_JOUR)^jours », `PART_COUTUMIERE`, « niveau 2 », « niveau 3 » et un temps mesuré de l'étape ; « ## En une page » nomme « Prélèvement » entre « Production » et « Commerce » (rang lu dans le texte). `jeu/sim/README.md` nomme `sim/prelevement.py` ; `jeu/sim/tests/README.md` nomme `test_prelevement.py`. Contre-épreuve : une section absente donne un échantillon vide qui fait échouer la lecture.
- **SC7 — Le tick reste sous le budget.** `cd jeu && python3 -m pytest sim/tests/test_monde.py -q -m chronometre -k budget_du_service -s` passe, seul, sans `-n`, test inchangé ; la médiane affichée s'écrit dans la PR, à côté des 90 à 93 ms mesurés sur la base, et le temps de l'étape dans MODELE.md, avec la machine. Contre-épreuve : celle du test lui-même (un commerce ralenti le fait échouer).

## Hors périmètre
- La calibration prouvée de la part coutumière et les nouvelles empreintes figées avec prélèvement (sous-lot 3 de la découpe de #396).
- Le vassal qui envoie sa part au suzerain (#397) ; le grenier rouvert aux lieux (#398) ; les foyers qui partent (#399).
- Tout affichage : service, `/lieu`, photographie, chronique, carte, Unity (#400, #401, #405) ; aucun fichier de `3d/` ne bouge.
- La route intérieure de #418 et son « −1 jour de convoi ».
- Le geste qui règle la part (#395, #405) : ce lot lit `World.parts`, il ne l'écrit pas.
- Minerai et objets prélevés, capacité d'un convoi, convoi pillé ou perdu, saison des routes : niveau 3, non simulés.
- Modifier une assertion, une empreinte ou une contre-épreuve d'un test existant, ou un test hors des neuf nommés ci-dessus.
