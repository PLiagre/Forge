# Premier écran de partie

Le propriétaire a validé le 15 octobre le passage des galeries à un écran utilisable : carte, maison choisie, temps et dossiers simultanés. Les fonctions de carte existantes sont réutilisées ; la simulation reste seule responsable des décisions.
Le travail se livre en deux petites PR : raccordement de la maison (UI-05a), puis écran intégré (UI-06a, avec les commandes de temps existantes). Ce découpage technique ne change pas le résultat attendu : un écran connecté, pas une nouvelle galerie.
`LecturePartie` lit `/monde`, puis `/maison` ou `/departs`. Le choix utilise `POST /intention` avec l’identifiant reçu ; un reçu accepté attend encore la maison dans `/monde`. Aucune maison n’est devinée à partir du choix. En pause, il faut reprendre le temps pour appliquer le choix au prochain tick.
Une seule opération à la fois ; aucun renvoi automatique d’une intention. Une coupure retire les données de maison devenues invérifiables. Un refus conserve son motif. Seuls les identifiants de la liste servie sont proposés.
Preuve UI-05a : quatre nouveaux tests rouges sur le composant vide, puis vingt-deux verts avec UI-01/UI-02 ; [rapports bruts](preuves/partie-tests.zip). Cas : lecture retardée, double choix, refus, identifiant hors liste, coupure et confirmation par le monde. Fixtures explicitement fictives, réservées aux tests.
La preuve visuelle et le parcours réel appartiennent à UI-06a, qui consomme ce raccordement. Aucune capacité d’écran n’est déclarée livrée par ce seul lot de fond.
