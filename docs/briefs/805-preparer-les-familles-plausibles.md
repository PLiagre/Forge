# Lot #805 — Préparer les familles plausibles
Jalon : J6 · Machine : vps · Taille prévue : 280 lignes

## But
Le monde sait donner, par une règle pure, déterministe et documentée, une épouse et des enfants vivants au 1er janvier 1400 à un chef sans famille connue. La règle est éprouvée sur des familles d'épreuve, mais elle ne s'applique pas encore au monde de production.

## Le joueur
Ce lot prépare deux gestes du jalon 6 : « quel mariage (une alliance, une dot, un héritage possible) » et « le joueur continue avec l'héritier ». Aujourd'hui, 2 245 maisons plausibles et plusieurs maisons historiques (Grenade, Hafsides, Mérinides, Chypre…) n'ont ni épouse ni enfant. Sans ces familles, le joueur n'a dans la plupart des maisons voisines personne à marier, ni d'héritier à suivre. Après ce lot, rien ne change encore à l'écran. La règle qui donnera à ces maisons des fils et des filles crédibles existe et elle est prouvée : pas d'épouse pour un chef de 20 ans, pas d'enfant né d'une mère de 14 ans, la même famille dans toutes les parties. La production l'utilisera au lot qui active la génération (suite de la découpe de #431). L'arbre de #446 la montrera, et #438 permettra d'y proposer un mariage. Une famille attestée ou une absence attestée n'est jamais remplacée par une famille inventée.

## Règle du monde
Découle de « Les personnes » de `jeu/sim/MODELE.md`. On y ajoute une section **« Les familles plausibles »**, juste après. Elle fait passer la règle de génération du niveau 3 au **niveau 2**, plausible, jamais sourcée, et déclarée **non activée**. La phrase « Autres familles […] restent de niveau 3 » renvoie vers cette section.

Tout se fait dans `jeu/sim/personnages.py`, avec deux fonctions pures. Aucune ne lit le monde, le catalogue ni `random` :

- `generer_familles_plausibles(chefs, parametres=PARAMETRES_FAMILLES_PLAUSIBLES)` reçoit une liste de fiches de chefs, de la même forme que `World.personnages`. Elle rend `(fiches, ecartes)`. `fiches` est un tuple trié par `id` : les chefs (des copies, complétées ou non) et les personnes générées. `ecartes` est un dict `id du chef → motif`, pour chaque chef qui ne reçoit rien. L'entrée n'est jamais modifiée.
- `valider_familles_plausibles(fiches, chefs, parametres)` refait la génération sur l'entrée triée et exige l'égalité complète. Elle exige aussi la séparation des hypothèses (ci-dessous) et passe le tout dans `valider_liens_familiaux`. C'est elle qui refuse une famille altérée, pas une assertion de test.

**Paramètres explicites.** Ils tiennent dans une constante de module, `PARAMETRES_FAMILLES_PLAUSIBLES`, passée en argument et validée à l'appel. Chaque valeur est de niveau 2 et sa justification est écrite dans MODELE.md :
- `graine` = 1400 : la graine des familles, distincte de la graine de partie ;
- `age_epoux_min` = 21 ans révolus (« plus de 20 ans ») ;
- `age_chef_plausible` = (25, 55) ;
- `ecart_epouse` = (2, 12) ans ;
- `age_epouse_min` = 16 ;
- `age_premier_enfant` = 18 ;
- `age_dernier_enfant` = 40 ;
- `intervalle_mois` = (24, 40), car des naissances environ tous les deux ans, dont une partie meurt jeune, laissent un enfant vivant tous les deux à trois ans ;
- `enfants_max` = 6.

Des paramètres incohérents sont refusés par `ValueError` : premier enfant avant 15 ans (`AGE_MATERNEL_MIN`), dernier enfant au-delà de 45 ans, intervalle nul, minimum supérieur au maximum.

**Tirage.** Chaque valeur tirée est l'entier d'une empreinte `hashlib.sha256` de `(graine, id du chef, rôle)` ramené dans son intervalle. Le tirage ne dépend ni de l'ordre des chefs, ni du générateur du tick, ni de la graine de la partie.

**Chef admissible.** Un chef reçoit une épouse si toutes ces conditions tiennent :
- sa présence est absente ou `vivante` ;
- il n'a aucun conjoint ;
- son `etat_familial['conjoints']` n'est ni `union` ni `veuvage` ;
- il a au moins `age_epoux_min` ans révolus au 1er janvier 1400 pour **toutes** ses dates compatibles (bornes de `_bornes_naissance`).

Les cas limites se jugent ainsi :
- Une naissance `vers`, `intervalle` ou nulle d'un chef historique ne donne aucune borne : le chef est écarté, avec un motif. Sa lacune reste intacte.
- Un chef d'origine `plausible` sans naissance reçoit une naissance hypothétique au jour près : un âge tiré dans `age_chef_plausible`, plus un jour tiré.
- Une naissance historique n'est jamais écrasée.
- Si l'état des enfants est `documentes` ou `absence_attestee`, l'épouse est générée sans enfant.
- Le choix des chefs passés à la fonction revient à l'appelant. Les institutions n'en font pas partie.

**Épouse.** Elle naît après la borne haute du chef, plus un écart tiré dans `ecart_epouse` et un jour tiré. Si elle aurait moins de `age_epouse_min` ans au départ, sa naissance est ramenée pour qu'elle les ait tout juste. Les conjoints sont réciproques.

**Enfants.** Le premier naît quand la mère atteint `age_premier_enfant` ans, plus un intervalle tiré. Chaque suivant naît un intervalle tiré plus tard. La suite s'arrête au premier enfant qui naîtrait le 1er janvier 1400 ou après, quand la mère dépasserait `age_dernier_enfant`, ou après `enfants_max` enfants. Le nombre et les dates suivent donc l'âge de la mère au départ : une épouse de 18 ans n'a aucun enfant, une épouse de 30 ans en a plusieurs. Le père est le chef. Toutes les naissances générées ont la précision `jour`, pour que l'âge maternel et l'antériorité soient **vérifiés** et non « indéterminés ».

**Hypothèses séparées des faits.** Chaque personne générée porte :
- un identifiant `personne-<maison>-epouse` ou `personne-<maison>-enfant-<k>` ;
- `origine: 'plausible'` et `presence: 'vivante'` ;
- un nom descriptif (« Épouse de … », « 2e enfant de … ») ;
- des `sources` toutes nulles ;
- un champ `hypotheses` qui nomme, champ par champ, la règle et le paramètre qui l'ont produit.

Le complément d'un chef ajoute ses conjoints et ses `hypotheses`. Ses `nom`, `naissance`, `sources`, `lacunes` et `etat_familial` historiques restent identiques à l'entrée. Une hypothèse ne porte jamais d'URL.

**Non activé.** `construire_personnages`, `valider_personnages`, le catalogue et le monde ne changent pas. Aucune empreinte épinglée ne change : `grep -rnE 'sha256|EMPREINTE' jeu/` ne vise que des données ou des règles que ce lot ne touche pas, dont `EMPREINTES_365`.

## Périmètre
jeu/sim/personnages.py
jeu/sim/tests/test_familles_plausibles.py
jeu/sim/MODELE.md
docs/briefs/805-preparer-les-familles-plausibles.md

## Conditions de succès
Le fichier d'épreuve neuf construit ses propres **familles d'épreuve non vides** : au moins huit chefs couvrant les cas de la règle. Chaque contre-épreuve passe par le vrai `valider_familles_plausibles` ou par une assertion indépendante du constructeur. Il faut écrire les cas et constater leur rouge avant d'implémenter.

SC1 — `python3 -m pytest jeu/sim/tests/test_familles_plausibles.py -q -k seuils`
- **Attente indépendante, écrite à la main** : l'ensemble exact des chefs qui reçoivent une épouse, et celui des écartés avec leur motif.
- **Chefs admissibles** : un chef né le 1379-01-01 (21 ans révolus) ; un chef né en 1370, précision `annee` ; un chef plausible sans naissance.
- **Chefs écartés** : un chef né le 1379-01-02 (20 ans révolus) ; un chef né en 1379, précision `annee`, dont les bornes chevauchent le seuil ; un chef historique `vers` ou sans naissance ; un chef en `union` ou en `veuvage` ; un chef qui a déjà un conjoint ; un chef `decedee`.
- **Contre-épreuves**, refusées par le validateur : épouse retirée d'un chef admissible ; épouse ajoutée à un chef de 20 ans ou en `veuvage` ; conjoint non réciproque ; une génération vide pour tous, qui doit aussi échouer face à l'attente indépendante.

SC2 — `python3 -m pytest jeu/sim/tests/test_familles_plausibles.py -q -k age_maternel`
- **Ce que vérifie le test** :
  - le nombre d'enfants croît avec l'âge de l'épouse au départ, sur au moins quatre épouses d'âges différents ;
  - une épouse de moins de `age_premier_enfant` ans n'en a aucun ;
  - aucun enfant ne naît le 1er janvier 1400 ou après ;
  - `enfants_max` est respecté ;
  - le bilan de `valider_liens_familiaux` met **tous** les contrôles `age_maternel` et `anteriorite` des familles générées dans `verifies`, aucun dans `indetermines`.
- **Les paramètres gouvernent** : `age_premier_enfant` décalé d'un an déplace la première naissance d'un an ; `age_dernier_enfant` ramené à `age_premier_enfant` laisse au plus un enfant ; un `intervalle_mois` plus long réduit le nombre.
- **Contre-épreuves** : un enfant d'une mère de 14 ou de 46 ans, un enfant né après le départ, un enfant retiré ou ajouté, ou une date décalée d'un jour sont refusés par le validateur. Des paramètres incohérents (premier enfant à 14 ans, dernier à 46, intervalle nul, minimum supérieur au maximum) lèvent `ValueError`.

SC3 — `python3 -m pytest jeu/sim/tests/test_familles_plausibles.py -q -k graines_permutations`
- **Graines** : les graines de famille 0 et 42 donnent chacune deux résultats identiques, valides tous les deux, et différents entre eux sur au moins une date.
- **Permutations** : l'ordre inversé et une rotation des chefs donnent un résultat identique, comparé en entier.
- **Neutralité** :
  - `random.getstate()` est inchangé après l'appel ;
  - la génération passe encore quand `random.random` et `random.Random` sont remplacés par des fonctions qui lèvent une erreur ;
  - une inspection par `ast` montre que `sim/personnages.py` n'importe pas `random` ;
  - l'entrée n'est pas modifiée (comparaison avec une copie profonde).
- **Contre-épreuve** : une sortie non triée ou produite depuis une entrée permutée sans tri est refusée par le validateur.

SC4 — `python3 -m pytest jeu/sim/tests/test_familles_plausibles.py -q -k hypotheses`
- **Ce que vérifie le test** :
  - chaque personne générée a `origine == 'plausible'`, des sources toutes nulles et un champ `hypotheses` non vide ;
  - un chef historique complété garde à l'identique son `nom`, sa `naissance`, ses `sources`, ses `lacunes` et son `etat_familial` ;
  - un chef historique sans naissance reste sans naissance, avec sa lacune ;
  - un chef plausible reçoit une naissance qui tombe dans `age_chef_plausible`.
- **Contre-épreuves**, refusées par le validateur : une URL ajoutée à une hypothèse ; une `origine` passée à `historique` ; une naissance historique écrasée ; une lacune effacée ; `hypotheses` vidé.

SC5 — `python3 -m pytest jeu/sim/tests/test_familles_plausibles.py -q -k production_inchangee` et `python3 -m pytest jeu/sim/tests/test_maisons.py jeu/sim/tests/test_determinisme.py jeu/sim/tests/test_modificateurs.py jeu/sim/tests/test_no_hardcoded.py -q`
- **Non-activation** : le monde chargé ne contient aucune personne qui ait `hypotheses` ou un identifiant `-epouse`/`-enfant-`. Le monde se charge encore quand `generer_familles_plausibles` est remplacée par une fonction qui lève une erreur, ce qui prouve qu'aucun constructeur ne l'appelle.
- **Non-régression** : les tests existants passent sans aucune modification. Aucune empreinte épinglée ne change, car aucune partie du monde ne doit différer.
- **Contre-épreuve** : brancher la génération dans `construire_personnages` fait échouer `production_inchangee`.

SC6 — `git diff --numstat origin/master -- jeu/ | awk '{s+=$1+$2} END {exit !(s<300)}'` passe : le diff de code, de tests et de documentation reste sous 300 lignes, brief non compris. S'il ne tient pas, le codeur demande une découpe. Il ne retire ni un cas de règle ni une contre-épreuve.

## Hors périmètre
- Activer la génération en production : le choix des chefs (maisons plausibles, maisons historiques à état `lacune`, exclusion des institutions), son entrée dans `construire_personnages` et `valider_personnages`, le catalogue, ainsi que la recapture des empreintes et des bilans chronologiques qui suivra.
- Les prénoms plausibles des épouses et des enfants, et leur sexe.
- Les mariages des enfants, les frères et les parents des chefs.
- Le vieillissement, les naissances en cours de partie (#433), la mort (#432), l'héritier (#435), la proposition de mariage (#438), l'arbre (#446), le service et Unity.
- Les données familiales de #1085 (Branković, Evrenos, le Zab). Ce lot n'en dépend pas et ne touche ni `personnages-1400.json` ni `test_maisons.py`.
- Le moindre changement de règle économique, d'habitants ou du tick. Le moindre assouplissement d'un test existant.

DECISION: BRIEF
