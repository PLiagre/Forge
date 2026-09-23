# Brief 256 — Une PR qui touche la zone protégée attend le propriétaire

## But

L'intégration retient toute PR qui touche la porte de master, même verte et
approuvée, et nomme les chemins qui demandent le propriétaire.

## Règle du monde

Ce lot porte sur l'atelier, sans changement du monde simulé. Il réalise la
demande #75. La liste `zone` de `[integration]` dans `atelier.toml`, lue
depuis master par le workflow, fait autorité. Elle contient `atelier.toml`,
`AGENTS.md`, `.github/`, `outils/relecture.py`, `outils/integration.py`,
`outils/demandes.py` et `outils/perimetre.py`.

Une entrée terminée par `/` couvre un dossier et ses descendants ; les autres
entrées désignent un fichier exact. Un renommage examine l'ancien chemin
autant que le nouveau ; une suppression reste un changement. La lecture
GitHub parcourt toutes les pages et vérifie leur complétude avec le nombre
de fichiers annoncé par la PR. Une réponse tronquée, vide, mal formée ou
illisible ne vaut jamais absence de changement protégé. Un changement de
révision pendant la lecture retient la PR.

Le refus précède le rejeu comme la fusion. La raison commence par « zone
protégée : le propriétaire fusionne ». Une zone absente, vide ou mal formée
fait échouer la commande avant toute décision. La page de pilotage emploie
le même examen que l'intégration ; elle ne peut pas proposer une fusion
que la garde interdit. Le script de fusion conserve sa vérification de
révision. Aucune protection GitHub ne change.

## Périmètre

En écriture : `outils/integration.py` (examen des chemins),
`outils/github.py` (lecture complète des fichiers), `outils/__main__.py`
(transmission des fichiers et de la zone à l'intégration et au tableau),
`outils/registre.py` (lecture et validation de la zone), `atelier.toml`
(déclaration de la zone), `outils/tests/test_integration.py` et
`outils/tests/test_lecture.py` (ajout de cas). La fiche 256 relève du
périmètre implicite du lot.

Tout autre chemin est interdit, dont `sim/`, `atelier/`, `.github/`,
`AGENTS.md`, `outils/relecture.py`, `outils/demandes.py`, les autres briefs
et les autres fiches. Aucun test existant n'est affaibli.

## Conditions de succès

### SC1 — La zone entière bloque, et son retrait du diff libère

`py -m pytest outils/tests/test_integration.py -k zone -q` éprouve chaque
entrée lue dans `atelier.toml`, avec les contrôles verts et une revue
valide : aucune ne rend fusionner ni rebaser. La même PR qui ne touche
que des fichiers ordinaires suit la décision habituelle. Le nombre de cas
vient de la zone ; une zone sans cas échoue. Ajouter un suffixe à un nom de
fichier protégé ne le transforme pas en fichier protégé.

### SC2 — L'absence de configuration ou de preuve retient

La même commande refuse zone absente, vide ou mal formée, ainsi que fichiers
illisibles, manquants et changement de révision. La ligne de commande ne
rend jamais un geste de fusion dans ces cas. Une PR venue d'un fork reste
retenue sans aller lire son code.

### SC3 — Renommage et pagination ne cachent aucun fichier

`py -m pytest outils/tests/test_lecture.py -k zone -q` place un chemin
protégé dans une page suivante, puis dans l'ancien nom d'un fichier
renommé. La garde le voit. Les contre-épreuves retirent une page ou le
chemin précédent : la preuve devient incomplète et la PR est retenue.

### SC4 — Les contrôles existants restent vrais

`python3 -m pytest outils/tests/ -q` joue aussi le banc shell sous Linux.
`py -m atelier feuille valider --projet .` vérifie le registre. Les nouveaux
cas sont joués avant l'implémentation pour constater leur échec, puis après
pour constater leur succès. Aucun agent ne fusionne cette PR : le
propriétaire reçoit les résultats et décide sur le changement concret.

## Hors périmètre

Identités des robots, relecture, CI sélective, résolution des conflits,
capacités des machines, contrôle du périmètre d'un brief, CODEOWNERS et
réglages GitHub. Aucun secret et aucun asset ne sont ajoutés.
