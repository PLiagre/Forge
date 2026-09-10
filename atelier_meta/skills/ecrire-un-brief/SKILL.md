---
name: ecrire-un-brief
description: >
  Écrire le brief d'un lot. Un fichier, cinq sections, une PR. Ne code
  rien. Le fond (ce que le monde saura faire) est une affaire du dépôt
  produit, pas de l'atelier.
---

# Écrire un brief

Le **format** à cinq sections et les façons de le rater vivent dans
le `AGENTS.md` du dépôt **produit**. Ce skill dit comment s'y
prendre, pas ce qu'est le monde.

1. Un seul changement. Si la moitié peut fusionner sans l'autre, couper.
2. Chaque condition de succès nomme une commande qui peut échouer.
3. Le périmètre liste des fichiers, nommément. Tout le reste est interdit.
4. Un compteur dérive des données. Un échantillon vide échoue.
5. Ne pas demander de modifier un test existant.
6. Si le lot touche au monde du produit, dire le niveau de fidélité
   que *ce* produit définit.
7. Dans le périmètre, les fichiers autorisés dans leur phrase, les
   fichiers interdits dans la leur — jamais les deux dans la même :
   l'atelier lit les premiers pour poser le verrou et écarte les
   seconds.

Le brief part dans une PR, sur une branche à lui, et la fiche du lot
dans la feuille de route du produit passe à `pret` dans la même PR
(`python3 -m atelier feuille marquer --projet . --lot NNN --etat pret`).
Le propriétaire fusionne ; c'est cette fusion qui rend le lot codable.

Ne code rien. Tu n'exécuteras pas ce lot.
