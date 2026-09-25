# Brief 280 — La relecture juge les auteurs de la révision exacte

## But

La relecture refuse l'approbation d'un auteur de la révision examinée, même si la branche fait un aller-retour pendant les lectures GitHub.

## Règle du monde

Ce lot porte sur la chaîne, sans changement du monde simulé ni niveau de
fidélité applicable. Il réalise la demande #100, distinctement du lot 256.
La tête et la base sont des identifiants complets de commits Git. La liste
des commits propres à la tête se lit par une comparaison de ces deux
identifiants immuables, jamais par `pulls/N/commits`.

Chaque page nomme la même base et annonce le même total. La liste doit
être complète, non vide, sans doublon, et contenir la tête examinée.
Chaque commit doit donner son identifiant et les connexions GitHub de son
auteur et de son committer. Le committer est la personne qui a enregistré
le commit ; elle compte aussi comme auteur du code pour la règle de rôle.
Une identité inconnue, une réponse mal formée, une page manquante ou une
révision différente interdit l'approbation. Aucune identité n'est inventée.

La relecture visible, le verdict de la porte isolée et celui présenté par
le tableau emploient la même lecture. L'option `--revision` ne permet pas
de juger les auteurs d'une autre tête. La vérification finale de la tête
et de la base demeure ; elle ne remplace pas la preuve immuable.

## Périmètre

En écriture : `outils/github.py` pour les auteurs immuables,
`outils/porte.py` pour fournir la révision jugée à cette lecture,
`outils/__main__.py` pour partager le verdict avec la relecture visible,
`outils/tests/test_lecture.py`, `outils/tests/test_integration.py` et
`outils/tests/test_relecture.py` pour ajouter les contre-épreuves. Les
données des faux serveurs existants sont adaptées au contrat de l'API ;
leurs assertions restent inchangées. La fiche 280 relève du périmètre
implicite de la PR.

Tout autre chemin est interdit, dont `.github/`, `atelier/`, `sim/`,
`unity/`, `atelier.toml`, `AGENTS.md`, les autres briefs et les autres
fiches du registre. Aucun réglage GitHub ni secret ne change.

## Conditions de succès

### SC1 — Une preuve complète

`py -m pytest outils/tests/test_lecture.py -k auteurs -q` refuse une
preuve vide, tronquée, incohérente, dupliquée ou sans identité complète.
La pagination est éprouvée avec des commits dérivés des données du banc.

### SC2 — La porte refuse l'auteur masqué

`py -m pytest outils/tests/test_integration.py -k auteurs -q`
reproduit A → B → A : l'approbation de l'auteur de A est refusée, celle
d'un tiers sur A reste recevable. La page et la porte rendent le même avis.

### SC3 — La relecture visible suit la même règle

`py -m pytest outils/tests/test_relecture.py -k auteurs -q`
éprouve le même aller-retour par la commande de relecture et refuse une
révision demandée différente de la tête. Les nouveaux cas rougissent
avant correction ; aucune assertion préexistante n'est assouplie.

### SC4 — Les contrôles existants restent vrais

`python3 -m pytest outils/tests/ -q` passe sous Linux, dont le banc
shell et les contre-épreuves du lot 256. `py -m atelier feuille valider
--projet .` et sa variante avec la base de la PR valident le registre et
ses transitions.

## Hors périmètre

Identités des Apps, protections de branche, capacités Unity/Blender,
résolution des autres PR, lancement du pilote et correction de la zone 256.
