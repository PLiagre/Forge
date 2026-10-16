# Les autres maisons — UI-14

Le joueur ouvre le journal des autres maisons depuis la carte : nom, territoire, ordre, raison et refus éventuel viennent de `/ia` et `/maisons`. Les deux ticks restent visibles. Un ordre reçu ne signifie pas un chantier achevé. La mesure d’activité porte sur les trente premiers jours, conformément au moteur.

Sans IA active, le dossier le dit. Un journal vide reste distinct d’une panne ; doublons, dates futures et raisons absentes refusent la lecture. Aucune décision ni intention n’est produite par ce dossier.

Preuve `4394d022` : trois rouges puis 49 tests d’interface verts. [Rapports, données reçues et parcours](preuves/voisins-4394d022.zip). Le vrai monde avec IA contient sept ordres au tick 62 ; défilement sans zoom de carte et réouverture d’un dossier au premier plan vérifiés. [Haut](preuves/voisins-journal-4394d022.png) et [suite](preuves/voisins-defilement-4394d022.png) regardés dans Unity à 1920 × 1080.

Les captures viennent du projet d’intégration réunissant les PR d’interface en cours. Le papier, l’encre et l’accent suivent DA.md ; typographie et couleurs politiques restent provisoires. Le feuillet commun est partagé avec le dossier des comptes ; il passe au premier plan à chaque ouverture.
