# Lot #115 — Le modèle du monde dit ce que le tick fait vraiment
Jalon : J1 · Machine : vps · Taille prévue : 140 lignes

## But
`jeu/sim/MODELE.md` décrit le tick tel que `jeu/sim/engine.py::tick` le joue — fabrication en tête, compteur de ticks et date du monde en fin — et un test rougit dès que le document et le code divergent sur l'ordre des étapes ; les lots du pont (J1), qui montrent la date et le panier d'une cellule, sont ainsi découpés dans un document juste.

## Règle du monde
Sans objet : aucune règle du monde ne change, aucune constante, aucune ligne de `jeu/sim/*.py`. Le lot corrige la description, section par section, pour qu'elle dise ce que le code fait déjà. Fidélité : sans objet.

Ce que le code fait, et que le document doit dire (vérifié sur master) :

- **L'ordre du tick** (`tick()`, `jeu/sim/engine.py`) : `_valider_numero_tick` (refus d'un `numero_tick` qui n'est pas `world.ticks_ecoules`, avant toute mutation) → `_apply_fabrication` → `_apply_extraction` (si carte) → `_apply_production` ou `_apply_production_saison_moyenne` (selon le régime, section « Les trois régimes de production ») → `_apply_commerce` → `_apply_consumption` → `_update_hunger` → `_apply_mortality` → `_apply_natalite` → `_apply_migration` → `_avancer_compteur_ticks`.
- **La fabrication** (`_apply_fabrication`, `constants.fabrication_kg`) : au début du tick, sur le panier d'ouverture, chaque matière première présente (tout ce qui n'est ni `nourriture` ni `objet`) perd `TAUX_FABRICATION_PAR_TICK` (5 %) de son stock ; `RENDEMENT_FABRICATION` (0,6) kg d'`objet` naissent par kg consommé. Niveau 2. Aucun bras n'est occupé, aucun métier n'existe : la fabrication tourne comme la mine, *en plus* du reste.
- **La date** : le monde porte un compteur `ticks_ecoules` (0 à l'amorçage, +1 à la fin de chaque tick, sérialisé) ; `World.date_simulation` en dérive l'année (depuis `ANNEE_INITIALE` = 1400) et le jour de l'année par `constants.date_de_tick`. La date n'est pas stockée, le compteur l'est.

Les assertions contredites, à corriger dans `jeu/sim/MODELE.md` :

1. « En une page » : la liste numérotée commence à l'extraction. Elle devient la liste des étapes de `tick()` dans l'ordre du code, **chaque étape nommant sa fonction entre accents graves** (ex. « **Fabrication** (`_apply_fabrication`) — … ») ; la production nomme ses deux fonctions ; la validation du numéro de tick et l'avance du compteur (qui fait passer la date) y figurent aussi. Le texte en prose de chaque étape existante reste ; seules la numérotation et la mention des fonctions s'ajoutent.
2. « Ce que le moteur ne fait pas encore » : la puce **fabriquer** (« Le minerai extrait reste du minerai… ni transformation d'une marchandise en une autre ») et la puce **dater le monde** (« le monde ne porte aucune date ») sont fausses ; elles sont retirées ou réécrites pour dire ce qui manque encore (pas d'atelier ni de bras affectés, pas de consommation des objets ; pas de calendrier au-delà de l'année et du rang du jour).
3. « La base de temps » : « il n'est stocké nulle part et le monde ne porte pas de date » devient : le rang du jour se dérive du compteur `ticks_ecoules`, que le monde porte ; le tick refuse un `numero_tick` différent du compteur.
4. « L'extraction minière » : « Premier maillon du tick, et la seule façon dont une marchandise autre que la nourriture entre dans le monde » est doublement faux : l'extraction suit la fabrication, et la fabrication fait naître l'`objet`. L'extraction reste la seule source de **matière première**.
5. « Pourquoi le minerai ne bouge pas » : « il n'y a ni fabrication, ni métier, ni prix » devient faux pour la fabrication ; la phrase dit que la fabrication transforme la matière **sur place** et ne crée donc aucune demande entre cellules (la consommation par habitant reste nulle hors nourriture), et qu'il n'y a toujours ni métier ni prix.
6. Une section courte « La fabrication » (formule, deux constantes, niveau 2, ce qu'elle ne fait pas), rangée par mécanisme comme les autres.

## Périmètre
jeu/sim/MODELE.md
jeu/sim/tests/test_monde.py

## Conditions de succès
**SC1 — l'ordre du document est celui du code, lu dans le code.**
`python3 -m pytest jeu/sim/tests/test_monde.py -q -k ordre_du_tick` passe. Le cas :
- lit les étapes côté code **par `ast`** dans le corps de `tick()` de `jeu/sim/engine.py` : les appels, dans l'ordre du source, dont la cible est une fonction définie au niveau module de `engine.py` ; doublons retirés, ordre de première apparition gardé. Aucune liste d'étapes n'est écrite dans le test ; la docstring de `tick()` n'est pas lue ;
- lit les étapes côté document dans la section « ## En une page » de `jeu/sim/MODELE.md` : les identifiants entre accents graves des items de la liste numérotée, dans l'ordre, doublons retirés ;
- exige les deux listes non vides et égales, et nomme dans son message la première étape qui diffère.

Contre-épreuves, portées par le même fichier de test (cas paramétrés sur la fonction de comparaison, pas sur les fichiers réels) : liste code vide → échec ; liste document vide → échec ; liste document privée de `_apply_fabrication` → échec ; deux étapes échangées → échec. Chacune doit lever, sinon le cas rougit.

**SC2 — rouge d'abord.** Le test de SC1, joué contre le `jeu/sim/MODELE.md` de master (`git show origin/master:jeu/sim/MODELE.md`), échoue : la fabrication (et toute fonction) manque à la liste du document. Le codeur le montre dans la PR (commande et sortie), avant d'avoir corrigé le document.

**SC3 — les assertions contredites ont disparu.**
`grep -nE "porte aucune date|ne porte pas de date|ni fabrication|reste du minerai|Premier maillon du tick" jeu/sim/MODELE.md` ne rend rien (code de sortie 1). Contre-épreuve : la même commande sur le fichier de master rend au moins quatre lignes. Et `grep -n "_apply_fabrication\|ticks_ecoules\|RENDEMENT_FABRICATION" jeu/sim/MODELE.md` rend au moins une ligne pour chacun des trois noms.

**SC4 — rien d'autre ne bouge.**
`git diff --name-only origin/master` ne rend que les deux fichiers du périmètre (et ce brief) ; `python3 -m pytest jeu -q` passe entier, sans qu'aucun cas existant de `test_monde.py` ne soit modifié ni retiré (`git diff origin/master -- jeu/sim/tests/test_monde.py` ne montre que des ajouts).

## Hors périmètre
- toute modification de `jeu/sim/engine.py`, de sa docstring, de `constants.py`, `world.py` ou d'un autre code : si le code et le document divergent, c'est le document qui change ;
- ajouter un métier, un prix, une consommation d'objets, ou toute règle du monde ;
- relire le reste de `MODELE.md` au-delà des six points ci-dessus (les autres dettes éventuelles se signalent dans la PR, elles ne se corrigent pas ici) ;
- un contrôle de dérive pour d'autres sections que l'ordre du tick ;
- le service de simulation, le panneau Unity et la preuve du jalon J1.
