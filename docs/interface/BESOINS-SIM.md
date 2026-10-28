# Contrats attendus par les écrans

Audit du service local le 16 octobre 2026 : lectures `/monde`, `/carte`, `/departs`, `/lieu`, `/plan`, `/maison`, `/maisons`, `/ia`, `/horloge`. Écritures `/intention`, `/vitesse`, `/tick`. Les routes ci-dessous sont des propositions, jamais des services déclarés disponibles. Aucun changement du moteur dans ces lots d’interface.

| Écran | Contrat proposé et raison | Absence et refus à préserver |
|---|---|---|
| Ville 3D | Correspondance livrée dans #685–700 : `TerresAvecKit`, siège lu par `/maison`, passage depuis la carte ; intégration du parcours complet encore à vérifier | Seul le Zab possède un kit déclaré ; pour les autres terres, garder le plan consultable |
| Enceinte | Forme, état et engagements de construction servis par le monde ; les journées et paiements des rues/parcelles/bâtiments sont déjà lus par UI-19a | Une défense absente ne devient pas un rempart local ni un coût nul |
| Personnage et famille | `/dynastie` : tick, personnes identifiées, parentés, chef, héritier, qualités servies ; décider d’un mariage ou d’une éducation | Personne inconnue ; héritier inconnu distinct de l’absence d’héritier ; aucun portrait fictif attribué à un personnage réel |
| Diplomatie | `/relations` : tick, interlocuteurs, revendications, offres, termes et échéances ; intentions de proposition et d’acceptation validées par le monde | Action interdite, offre expirée, interlocuteur absent |
| Armée | `/armees` : tick, identifiants, cell_id, effectifs, vivres en kg, destination ; intentions lever/marcher/ravitailler | Effectif non calculé distinct de zéro ; destination interdite |
| Bataille et siège | Session tactique : identifiant, révision, terrain, unités, ordres permis, résultats rendus au monde | Combat terminé, ordre ancien, entrée impossible ; aucune résolution locale dans l’interface |
| Trésor et dette | `/finances` : tick, monnaie et unité, trésor, prix par cell_id, dettes avec échéances ; intentions financières | Monnaie ou prix absent, créancier inconnu ; aucune estimation de taux dans l’interface |
| Sauvegarde | Liste, création et chargement atomique des sauvegardes par le service ; identifiant, date, version et état | Format incompatible, écriture impossible, chargement refusé ; ne pas sauvegarder les nombres du monde dans Unity |
| Chronique | Événements identifiés : tick, texte, acteurs, cell_id éventuel et pagination | Aucun événement reçu distinct d’un service absent ; pas de causalité déduite d’un écart de stocks |
| Décisions et délégation | File identifiée : révision, échéance, options autorisées ; consignes persistantes et reçu | Arbitrage déjà réglé, option expirée ; aucun ordre autonome produit par la vue |
| Bilan | État de fin explicitement servi : raison, dynastie, terres et chronologie | Une panne ne signifie jamais défaite ; score non servi reste absent |
| Calques et trajets | Relief et routes par cell_id, unités, bornes et légende servies ; transports avec origine/destination/charge | Une géométrie ou une mesure absente ne devient pas une route droite inventée |

Les écrans qui attendent ces contrats sont préparés dans un mode **Démonstration** séparé, avec fixtures identifiées. Ils ne déposent aucune intention dans la vraie partie. Dans la partie, leur indisponibilité indique la donnée manquante. Les décisions avancées ne seront jouables qu’après raccordement au moteur ; l’interface seule ne les débloque pas.
