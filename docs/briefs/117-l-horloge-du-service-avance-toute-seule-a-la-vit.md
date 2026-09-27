# Lot #117 — L'horloge du service avance toute seule, à la vitesse choisie
Jalon : J1 · Machine : vps · Taille prévue : 260 lignes

## But
Le service local (`python3 -m sim.service`, depuis `jeu/`) fait avancer le monde tout seul, un jour par seconde par défaut, à la vitesse que le joueur choisit ou en pause, sans qu'une lecture attende jamais un tick ni voie une cellule à moitié mise à jour. C'est l'horloge que le panneau Unity du jalon J1 regarde bouger (CAP.md : « Le temps avance d'un jour par seconde ; il peut accélérer ou mettre en pause »).

## Règle du monde
Sans objet : c'est un lot d'outil. L'horloge est un regard qui déclenche les ticks du moteur existant ; elle n'ajoute aucune règle, aucune constante du monde, aucun champ à `Cell` ni à `World`, et ne touche ni `engine.py`, ni `world.py`, ni `model.py`, ni `constants.py`, ni `snapshot_export.py`, ni `MODELE.md`. Fidélité : sans objet.

Ce qu'elle respecte du modèle (`jeu/sim/MODELE.md`, « La base de temps » et « Le moteur sans état caché ») :

- **Un tick = un jour** (`TICK_DURATION_DAYS = 1`) : « jours par seconde » et « ticks par seconde » sont la même vitesse ; le service ne convertit rien.
- **Un seul moteur, un seul générateur.** Chaque tick de l'horloge est joué exactement comme ceux de `POST /tick` : `tick(world, rng, world.ticks_ecoules)`, avec l'unique `random.Random(S)` du service. Le monde au tick T ne dépend donc pas de la vitesse ni de l'heure : l'horloge à 20 jours/s qui atteint le tick T rend les mêmes octets qu'un service en pause poussé à T par `POST /tick`.
- **Rien ne se devine** (AGENTS.md, § 4) : vitesse absente, non numérique, négative, `nan` ou infinie → 400 qui nomme `jours_par_seconde` et la valeur reçue ; ni la vitesse ni le monde ne changent. Avant tout tick, la durée du dernier tick vaut `-1` (« non calculé ») ; `0` serait une mesure.

## Périmètre
jeu/sim/service.py
jeu/sim/tests/test_monde.py
jeu/sim/tests/test_determinisme.py
jeu/sim/tests/README.md
jeu/sim/README.md

## Conditions de succès

Forme attendue (`jeu/sim/service.py`, bibliothèque standard seule ; tout littéral numérique autre que 0, 1, -1 est une constante nommée au niveau du module, `test_no_hardcoded.py` inspectant tout `sim/*.py`) :

- **Deux verrous de rôle distinct.** Un verrou de tick sérialise les ticks (horloge et `POST /tick`) et rien d'autre. Après **chaque** tick, sous ce verrou, le service construit l'état publié — le document `/monde` complet (déjà sérialisé en octets canoniques), la vue `/lieu` de chaque cellule, `tick`, `date` — puis le **substitue d'un seul coup** (une affectation d'attribut) à l'état publié précédent, qui n'est jamais modifié ensuite. `GET /lieu`, `GET /monde` et `GET /horloge` lisent uniquement l'état publié, **sans prendre le verrou de tick**. Un `POST /tick?n=N` publie après chacun de ses N ticks. Les réponses de #116 (forme, arrondi par `_round_tree`, refus) sont inchangées.
- **Le fil de l'horloge** (`threading.Thread`, démon) joue un tick puis attend la prochaine échéance, fixée en temps absolu (`time.monotonic`) : l'échéance k vaut `t0 + k / v`, de sorte que les attentes ne cumulent pas d'erreur. S'il est en retard (le tick a duré plus que `1 / v`), il repart de maintenant **sans rattraper en rafale**. À `v = 0` il dort jusqu'au prochain changement de vitesse. Un changement de vitesse réveille le fil (`threading.Event` ou `Condition`) et repart de `t0 = maintenant` ; il n'interrompt pas un tick commencé.
- `--jours-par-seconde X` sur la ligne de commande, défaut nommé `DEFAULT_JOURS_PAR_SECONDE = 1` ; mêmes refus que `/vitesse` (argparse sort en erreur).
- `POST /vitesse?jours_par_seconde=X` : X flottant fini ≥ 0 ; rend le même document que `/horloge`.
- `GET /horloge` → `{"tick", "date", "jours_par_seconde", "duree_dernier_tick_ms", "budget_tick_ms"}` : `duree_dernier_tick_ms` est la durée de l'appel `tick(...)` seul (`time.perf_counter`), publication exclue, `-1` avant le premier tick ; `budget_tick_ms` est la constante nommée `BUDGET_TICK_MS = 100` (CAP.md, « Quand revenir sur cette décision »). Le budget se lit ainsi d'un `curl`, sans outil.

Le lanceur de test `lancer_service` de `test_monde.py` gagne un paramètre `jours_par_seconde` (défaut `0`) qu'il passe en `--jours-par-seconde`. C'est la **seule** ligne existante qui change hors ajouts : les cas de #116 supposent un monde qui n'avance que sur `POST /tick`, ils tournent donc en pause ; aucune de leurs assertions ne bouge.

**SC1 — vitesse 0 : le tick ne bouge pas ; vitesse v : il avance d'environ v par seconde.**
`python3 -m pytest jeu/sim/tests/test_monde.py -q -k horloge` passe. Un cas démarre un service à `--jours-par-seconde 0`, lit `/horloge` (`tick == 0`, `duree_dernier_tick_ms == -1`, `budget_tick_ms == 100`), attend 1,5 s et exige `tick == 0` exactement. Puis `POST /vitesse?jours_par_seconde=4` ; le cas lit `/horloge` à t₀ et à t₁ ≈ t₀ + 2,5 s (horloge `time.monotonic` du test), avec Δ = t₁ − t₀ et r = la plus longue des deux requêtes. La tolérance est **dérivée des mesures** par une fonction de contrôle unique : `|(tick₁ − tick₀) − v·Δ| ≤ 1 + v·(d + r)`, où d = la plus grande `duree_dernier_tick_ms` lue (en secondes). Si `d·v ≥ 1`, le cas échoue en nommant le budget (la machine ne tient pas la vitesse), il ne s'assouplit pas. Puis `POST /vitesse?jours_par_seconde=0`, le tick lu juste après ne bouge plus pendant 1 s (un tick commencé peut finir : tolérance d'un seul tick, entre la réponse de `/vitesse` et la première lecture, pas après). Contre-épreuve paramétrée sur la fonction de contrôle : une observation fabriquée à la moitié de la vitesse attendue (Δ = 2,5 s, v = 4, 5 ticks, d = 0,05 s, r = 0,01 s) et une au double (20 ticks) **doivent être refusées** ; l'observation exacte (10 ticks) acceptée.

**SC2 — une lecture pendant les ticks rend un état cohérent, identique à celui du même tick joué à la main.**
Un cas `horloge` de `test_determinisme.py` démarre un service A (graine 0) à `--jours-par-seconde 20` et, pendant ~1,5 s, lit en boucle `GET /monde` et `GET /lieu?cell=<plus petit cell_id>` ; puis `POST /vitesse?jours_par_seconde=0`. Il exige au moins trois ticks distincts observés (un échantillon vide ou figé échoue). Un service B (graine 0, en pause) est poussé par `POST /tick?n=1` successifs ; à chaque tick T observé chez A, les octets de `/monde` et de `/lieu` de A au tick T sont **identiques octet pour octet** à ceux de B au tick T. Contre-épreuve dans le même cas : la fonction de comparaison appliquée à un `/monde` de A au tick T contre celui de B au tick T+1 **doit lever**.

**SC3 — une lecture n'attend jamais la fin d'un tick.**
Un cas `horloge` de `test_monde.py`, sur un service en pause, lance `POST /tick?n=10` dans un fil. Le fil principal interroge `/horloge` jusqu'à `tick ≥ 1` (délai maximal dérivé : 10 fois la `duree_dernier_tick_ms` lue, plus 5 s de démarrage nommés), puis fait `GET /lieu` et `GET /monde` et note leur instant de fin. Il exige que ces deux lectures finissent **avant** la réponse du `POST` (instants `time.monotonic` comparés), avec un `tick` strictement compris entre 1 et 9 inclus, et que le `POST` rende finalement `tick == 10`. Contre-épreuve paramétrée sur la fonction de contrôle : une observation fabriquée où la lecture finit après le `POST`, ou porte `tick == 10`, **doit être refusée**. (Un service qui garde un seul verrou pour lire et jouer, comme celui de #116, fait échouer ce cas.)

**SC4 — rien ne se devine.**
Un cas `horloge` de `test_monde.py` exige que `POST /vitesse` sans paramètre, puis avec `jours_par_seconde=abc`, `-1`, `nan`, `inf` rende 400 avec un corps qui contient `jours_par_seconde` et la valeur reçue ; qu'après ces refus `/horloge` rende toujours `jours_par_seconde == 0` et `tick == 0` ; et que `python3 -m sim.service --jours-par-seconde -1 --port 0` sorte avec un code non nul sans écrire la ligne « service prêt ». Contre-épreuve : `POST /vitesse?jours_par_seconde=2.5` rend 200 et `jours_par_seconde == 2.5`.

**SC5 — rien d'autre ne bouge.**
`python3 -m pytest jeu -q` passe entier : les cas `service` de #116, `test_no_hardcoded.py`, `test_write_coverage.py` et le cas « bibliothèque standard seule » compris. `git diff --name-only origin/master` ne rend que les fichiers du périmètre (et ce brief). `git diff origin/master -- jeu/sim/tests/test_monde.py jeu/sim/tests/test_determinisme.py` ne montre que des ajouts, hors la signature et la commande de `lancer_service` décrites plus haut. `jeu/sim/README.md` dit la vitesse par défaut, `--jours-par-seconde`, `/vitesse` et `/horloge` ; `jeu/sim/tests/README.md` dit que `test_monde.py` porte aussi « l'horloge avance à la vitesse choisie, une lecture n'attend pas un tick ».

## Hors périmètre
- le client C#, le panneau Unity, `pc\Jouer.cmd`, l'épreuve PC et sa capture (lots `pc` du jalon J1) ;
- rendre le tick plus rapide (indexer le balayage des arêtes, porter le moteur) : ce lot **mesure** le budget, il ne le tient pas ;
- une vitesse maximale imposée, le rattrapage des ticks en retard, une horloge qui saute des jours ;
- appliquer ou stocker une intention (jalon 2) ;
- le contrat ville (`jeu/ville/`) et le retrait du `cityId` ;
- toute modification de `engine.py`, `world.py`, `model.py`, `constants.py`, `snapshot_export.py`, `__main__.py` ou `MODELE.md` ;
- l'historique des durées de tick, la moyenne, le suivi hebdomadaire du budget au journal (le journal relève de `atelier/`).
