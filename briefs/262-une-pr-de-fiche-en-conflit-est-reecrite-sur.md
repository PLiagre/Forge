# Brief 262 — Une PR de fiche en conflit est réécrite sur master

## But

Une PR `feuille/` en conflit avec `master`, dont le diff ne touche que le
registre, est recalculée sur le dernier `master` et rejouée automatiquement,
au lieu d'attendre pour toujours que le propriétaire résolve le conflit à la
main.

## Règle du monde

Ce lot porte sur l'atelier, sans changement du monde simulé. Il réalise la
demande #88.

Chaque PR `feuille/` insère sa fiche au même endroit dans le registre : juste
sous `<!-- lots:debut -->`. Deux PR qui écrivent sur cette même ligne sont en
conflit pour git dès que l'une des deux entre dans `master`. Mesuré le
22 septembre 2026, après la fusion de la fiche 256 : treize PR de fiche
devenues `CONFLICTING` d'un coup. `outils/integration.py::examiner` rend
aujourd'hui `RIEN` avec « en conflit avec master » pour toute PR non
fusionnable, sans distinguer un vrai conflit de contenu d'un conflit qui ne
porte que sur l'endroit où une fiche s'insère.

Le contenu d'une PR `feuille/` n'est pas du texte libre : c'est une fiche
ajoutée, ou un état changé, calculable à partir de la PR elle-même. Il se
recalcule donc sur le dernier `master`, sans jugement, quand le diff ne
touche que le registre.

`examiner` reçoit une nouvelle décision, `reecrire`, à côté de `fusionner`,
`rebaser` et `rien`. Une PR dont la branche commence par `feuille/`, qui
n'est pas fusionnable, et dont `pr.fichiers` (déjà lu par `_pr_integrable`
pour la garde de zone) vaut exactement un seul chemin — celui que
`registre.branchement()` nomme comme registre du produit, jamais
`"ROADMAP.md"` en dur — prend cette décision au lieu de rester `RIEN`. Une PR
en conflit qui touche un autre fichier, ou dont la branche n'a pas ce
préfixe, garde la décision `RIEN` d'aujourd'hui : on ne réécrit que ce qui se
recalcule.

Le calcul lit trois versions du registre, chacune passée au lecteur de
l'atelier (`atelier.feuille.lire_texte`) après avoir été récupérée par son
SHA d'objet Git — arbre puis blob, comme `github.fichiers_proteges` lit déjà
un chemin à une révision donnée :

- celle de l'ancêtre commun entre la tête de la PR et `master` — le
  `merge_base_commit` de `compare/{master}...{tête}`, jamais le `base.sha`
  annoncé par la PR, qui ne bouge pas avec `master` ;
- celle de la tête de la PR ;
- celle du `master` courant.

Chaque fiche que la tête porte et que l'ancêtre commun ne porte pas est une
fiche ajoutée par cette PR ; chaque fiche présente dans les deux dont l'état
diffère est un changement d'état porté par cette PR.

Une fiche ajoutée est insérée dans le registre de `master` à la même place
relative que dans la tête : juste après la fiche qui la précède dans l'ordre
de la tête, si cette fiche précédente existe déjà dans `master` — en
remontant la liste des fiches qui précèdent tant qu'aucune n'existe encore
sur `master` — sinon en tête du registre, au même repère que
`palier.inserer`. Un changement d'état est appliqué à la fiche de même
numéro dans `master`, par la même fonction que `atelier feuille marquer` ;
une fiche que `master` porte déjà dans l'état visé ne change pas.

`.github/scripts/integrer.sh` reçoit un nouveau geste, `reecrire N` : il
pousse le registre recalculé sur la branche de la PR N, par-dessus `master`,
puis redemande les mêmes contrôles qu'un rejeu (`tests`, `security`,
`relecture`), avec la même garde de révision jugée que `rebaser` — une
poussée sur la branche entre la décision et le geste ne doit pas être
écrasée en silence. Aucun fichier de `.github/workflows/` ne change : la
révision jugée est déjà transmise au geste pour toute décision, mais aucune
sortie de workflow ne peut porter le texte d'un registre entier sans changer
le YAML. `.github/scripts/integrer.sh` obtient donc lui-même le registre
recalculé, par un nouvel appel direct à la commande `integration` (celle qui
existe déjà, sans commande neuve) pour la PR décidée — décider n'est pas
faire, comme le reste de l'intégration : `outils/integration.py` calcule le
registre, `.github/scripts/integrer.sh` fait le geste de le pousser.

## Périmètre

En écriture : `outils/integration.py` (la décision `reecrire` et le calcul
du registre recalculé), `outils/registre.py` ou un module neuf de `outils/`
(lecture des trois versions du registre par leurs objets Git — il réutilise
le lecteur de l'atelier, il n'en écrit pas un second), `outils/__main__.py`
(la seule commande `integration`, invoquée une seconde fois par le geste
pour obtenir le registre recalculé d'une PR déjà décidée `reecrire`),
`.github/scripts/integrer.sh` (le geste `reecrire`), `outils/tests/test_integration.py`
et `outils/tests/test_scripts.py` en ajout de cas, `docs/WORKFLOW.md` §
« Ce qui ouvre la porte de `master` ». La fiche 262 relève du périmètre
implicite du lot.

Tout autre chemin est interdit, nommément : `outils/relecture.py`,
`.github/workflows/`, `.github/scripts/lot.sh`, `atelier/`, `atelier.toml`,
`AGENTS.md`, les autres briefs et les autres fiches. Aucun test existant
n'est affaibli.

## Conditions de succès

### SC1 — Deux PR de fiche neuve se recalculent l'une après l'autre

Deux PR de fiche neuve ouvertes sur le même `master` : après la fusion de la
première, `outils/integration.py::examiner` rend `reecrire` pour la
seconde, et le registre recalculé porte les deux fiches, chacune une seule
fois, et passe `python3 -m atelier feuille valider`. Sans ce cas, rien ne
prouve que le conflit se lève. `python3 -m pytest
outils/tests/test_integration.py -k reecrire -q` éprouve ce cas.

### SC2 — Un changement d'état se recalcule, une fiche déjà à jour ne bouge pas

Une PR `feuille/` qui change un état (par exemple `idee → abandonne`) et qui
est en conflit est recalculée avec le même état ; une fiche que `master`
porte déjà dans cet état ne change pas. Même commande que SC1.

### SC3 — Ce qui ne se recalcule pas reste `RIEN`

Une PR en conflit qui touche un autre fichier que le registre, ou dont la
branche n'est pas `feuille/`, reste `RIEN` : on ne réécrit que ce qui se
recalcule. Même commande que SC1.

### SC4 — Le geste pousse une fois et redemande les trois contrôles

Sur le banc de `outils/tests/banc.py`, `python3 -m pytest
outils/tests/test_scripts.py -k reecrire -q` vérifie que `integrer.sh` avec
`reecrire N` pousse une seule fois sur la branche de la PR et redemande
`tests`, `security` et `relecture`, avec la même garde de révision jugée que
`rebaser` : une révision jugée absente ou différente de la tête courante
refuse le geste, sans pousser. Une décision illisible continue d'échouer
bruyamment, sans nouveau cas — le geste ne change que par l'ajout du
`case` `reecrire`.

### SC5 — Les contrôles existants restent vrais

`python3 -m pytest outils/tests/ -q` passe, banc shell compris sous Linux.
`py -m atelier feuille valider --projet .` vérifie le registre. Les nouveaux
cas sont joués avant l'implémentation pour constater leur échec, puis après
pour constater leur succès.

## Hors périmètre

Ne change pas l'endroit où `lot.sh` insère une fiche ; ne résout pas les
conflits des PR `brief/` et `agent/`, dont le contenu ne se recalcule pas ;
ne fusionne rien de plus qu'avant — `reecrire` rejoue les contrôles, il ne
fusionne pas. Identités des robots, relecture, CI sélective, capacités des
machines, contrôle du périmètre d'un brief, CODEOWNERS et réglages GitHub.
Aucun secret et aucun asset ne sont ajoutés.
