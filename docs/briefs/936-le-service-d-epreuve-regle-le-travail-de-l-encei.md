# Lot #936 — Le service d'épreuve règle le travail de l'enceinte
Jalon : J4 · Machine : vps · Taille prévue : 180 lignes

## But
Un service d'épreuve jetable, lancé par `python3 -m sim.service --epreuve --travail-enceinte J`, compte J journées par mètre d'enceinte au lieu de 30, pour ce seul processus. Une épreuve voit ainsi un mur s'achever en quelques ticks, sans qu'aucune règle du monde change.

## Le joueur
Lot de fond. C'est le sous-lot 1 de #909 « épreuve de l'enceinte », découpé de #417 « L'enceinte se dessine, et ses portes s'ouvrent sur les rues ». Il prépare le geste du J4 « trace son enceinte », et la décision du jalon : des bras au mur, c'est moins de bras ailleurs. À Biskra, le joueur trace un carré de ±80 m. Le monde lui demande 19 200 journées, et c'est juste : un mur coûte des années. Aucune épreuve ne peut attendre aussi longtemps pour montrer qu'un mur payé au grenier passe des piquets à l'achèvement. Avec J = 0,01, le même carré demande 7 journées et s'achève au tick 5. La session Unity (sous-lot 2 de #909, pc) le montrera, et le juge (sous-lot 3, pc) le vérifiera. Ce lot seul ne change rien à l'écran ni au jeu : la partie du joueur garde ses 30 journées par mètre.

## Règle du monde
Sans objet : c'est un outil d'épreuve, aucune règle de jeu ne change. Le lot s'appuie sur `jeu/sim/MODELE.md`, « Le plan du bourg » : le travail requis d'une enceinte vaut `max(1, ceil(périmètre bouclé × TRAVAIL_ENCEINTE_JOURNEES_PAR_M))`, et la constante, de niveau 2, est relue au calcul par `sim/chantiers.py`. Il s'appuie aussi sur « Le chantier et ses bras », dont les salaires, l'ordre de service et le grenier restent intacts. La ligne neuve va dans le paragraphe du mode épreuve, après celui de `vider-bourg`.

Contrat à livrer, dans `jeu/sim/service.py`, fonction `main` seulement :

- Ajouter l'option `--travail-enceinte J`, absente par défaut. Sa conversion suit `_lire_vitesse` et `_vitesse_cli` : nombre `float`, fini, strictement plus grand que 0. Sinon argparse refuse avec un message qui nomme `travail-enceinte` et la valeur reçue. C'est le cas de `0`, `-1`, `nan`, `inf`, `-inf`, `abc` et de la chaîne vide.
- Après `parse_args`, l'option sans `--epreuve` donne `parser.error(...)`, avec un message qui nomme `--travail-enceinte` et `--epreuve`. Ce refus, comme les autres, sort avec un code différent de 0, avant tout chargement du monde et sans imprimer « service prêt ».
- Si l'option est acceptée, faire `_constantes.TRAVAIL_ENCEINTE_JOURNEES_PAR_M = J` avant de construire `ServeurMonde`. Ce processus est jetable : rien n'est sauvegardé ni publié en plus. `ServeurMonde`, ses routes, `sim/constants.py` et `sim/chantiers.py` ne changent pas.

Mesure du chef, faite le 30/10/2026 sur `master` avec le monde d'épreuve, graine 0, constante posée à 0,01 dans le processus. C'est le scénario de #908 : Biskra est tirée de `/departs` (cellule 10103). On dépose `choisir_depart` au tick 0, puis un tick. On dépose la route `{"type": "tracer_route", "cell": 10103, "points": [[-66, 2.2], [-120, 2.2]], "largeur_m": 4}` au tick 1, puis un tick. On dépose l'enceinte `{"type": "tracer_enceinte", "cell": 10103, "points": [[-80, -80], [80, -80], [80, 80], [-80, 80]]}`, sans `foyers`, au tick 2. Ensuite, `POST /tick?n=1` un à un. Après les ticks qui portent `/horloge` à 3, 4 et 5, `/plan?cell=10103` sert l'enceinte avec `travail_requis` 7, `foyers` 1 et `travail_fourni` 1, 3 puis 7. `en_chantier` vaut vrai, vrai, puis faux. Sans la constante changée, le même scénario sert `travail_requis` 19 200, avec `travail_fourni` 1, 3 puis 8, toujours en chantier.

## Périmètre
jeu/sim/service.py
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py
docs/briefs/936-le-service-d-epreuve-regle-le-travail-de-l-encei.md

## Conditions de succès
Les commandes se lancent depuis la racine. Les cas neufs vont dans `jeu/sim/tests/test_monde.py`, à côté de `test_service_epreuve_reserve`, avec `travail_enceinte` dans leur nom. Ils réutilisent `lancer_service` et `requete_service` sans les modifier. Pour ajouter des arguments, ils enveloppent `subprocess.Popen` par `monkeypatch`, comme `test_service_epreuve_reserve` le fait pour `--epreuve`. Le vrai module tourne toujours en sous-processus. Aucun cas n'appelle `main` dans le processus de test sans restaurer la constante, car `test_chantiers.py` exige qu'elle vaille 30. Montrer le rouge des cas avant le code, puis leur vert. Budget : 25 lignes de service, 100 de tests, 4 de `MODELE.md`, le reste pour le brief.

SC1 — **Les refus.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k travail_enceinte_refus`. Le cas lance `python3 -m sim.service --port 0 --jours-par-seconde 0` par `subprocess.run`, une fois avec `--travail-enceinte 0.01` sans `--epreuve`, puis avec `--epreuve --travail-enceinte V` pour chaque V de `0`, `-1`, `nan`, `inf`, `-inf`, `abc` et `""`. Chaque lancement doit sortir avec un code différent de 0, sans « service prêt » sur la sortie. Son erreur doit nommer `travail-enceinte`, et `epreuve` dans le premier cas, la valeur reçue dans les autres. Contre-épreuve : `--epreuve --travail-enceinte 1e-2`, lancé par `lancer_service` avec `Popen` enveloppé, imprime « service prêt » et sert `/horloge` au tick 0. Un refus systématique fait donc rougir le cas, tout comme une option acceptée sans `--epreuve` ou acceptée pour J ≤ 0 ou infini.

SC2 — **Le carré de #908 s'achève au tick 5.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k travail_enceinte_carre`. Le cas joue le scénario de la mesure par HTTP sur un service lancé avec `--epreuve --travail-enceinte 0.01` : Biskra prise dans `/departs` par `siege.nom`, puis le dépôt et la vérification de chaque reçu. Il exige, après chaque tick, les valeurs mesurées de `/plan?cell=X` : requis 7, fourni 1, 3 puis 7, et `en_chantier` faux seulement au tick 5. Contre-épreuve : un service lancé avec `--epreuve` seul joue le même scénario et sert, au tick 5, `travail_requis == 19200`, `en_chantier` vrai et `travail_fourni < 19200`. Un cas de plus vérifie que `sim.constants.TRAVAIL_ENCEINTE_JOURNEES_PAR_M` vaut toujours 30 dans le processus de test, avant comme après. Une option ignorée, ou une constante changée hors du processus lancé, fait rougir.

SC3 — **Aucune règle du monde ne change.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k travail_enceinte_neutre`. Le cas joue le même scénario jusqu'au tick 5 sur deux services : `--epreuve --travail-enceinte 30` et `--epreuve` seul. Les octets de `/plan?cell=X` et de `/lieu?cell=X` doivent être identiques entre les deux. Contre-épreuve : le service lancé avec `--travail-enceinte 0.01` donne un `/plan?cell=X` différent au même tick. Une option qui toucherait autre chose que cette constante, comme les salaires, les bras ou l'ordre de service, fait rougir.

SC4 — **Rien d'ancien ne bouge.** `python3 -m pytest jeu/sim/tests/test_monde.py -q -k 'service_epreuve or horloge_cli or vider_bourg'`, puis `python3 -m pytest jeu -q` : tout doit être vert sans retouche d'un test existant. Le service lancé sans l'option garde exactement ses réponses. Contre-épreuve : si `git diff master -- jeu/sim/tests/test_monde.py jeu/sim/tests/test_chantiers.py` retire ou modifie une ligne existante, la livraison est interdite.

`MODELE.md` : deux à quatre lignes après le paragraphe de `vider-bourg`. Elles disent que `--travail-enceinte J`, réservé au mode épreuve, remplace `TRAVAIL_ENCEINTE_JOURNEES_PAR_M` pour ce seul processus, qu'il est refusé sans `--epreuve` ou si J n'est pas un nombre fini plus grand que 0, et qu'aucune règle ne change : le carré de ±80 de Biskra demande 7 journées à J = 0,01 au lieu de 19 200, et s'achève au tick 5.

## Hors périmètre
- La session Unity (`-forgeTravailEnceinte`, `Captures/Lot909.cs`) et le juge `pc/epreuve_enceinte.py` : ce sont les sous-lots 2 et 3 de #909, sur pc.
- Aucune autre constante réglable, aucune route HTTP neuve, aucun réglage pendant la partie.
- Aucune publication de la valeur dans `/horloge` ou ailleurs.
- Aucun changement de `sim/constants.py`, de `sim/chantiers.py`, de `ServeurMonde`, des intentions, des salaires, des bras ou de l'ordre de service.
- Aucun test existant assoupli ou réécrit.
