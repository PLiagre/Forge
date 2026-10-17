# Consulter le plan du bourg — UI-15a

Depuis le territoire conservé, **Plan du bourg** ouvre les formes reçues de `/plan?cell=…` : place, maisons et rues de départ, puis rues, parcelles et bâtiments ajoutés au monde. Le nord reste en haut ; la largeur du cadre en mètres dérive des coordonnées. La consultation est possible sur une autre terre, sans outil de construction actif.

**Revenir à la carte** conserve sa position et le territoire retenu. Changer de territoire remplace le plan ; absence, forme incomplète, mauvais territoire ou largeur invalide refusent le dessin. Le plan ne crée aucune maison et ne décide aucun chantier.

Preuve du code `3302a711` (avant rebase : `d42de95f`) : trois contre-épreuves de données rouges, puis une quatrième reproduisant le rendu absent découvert pendant la capture ; 53 tests d’interface verts après correction. [Rapports, plans reçus et parcours](preuves/bourg-3302a711.zip). [Bar-le-Duc](preuves/bourg-bar-3302a711.png) et [Milan](preuves/bourg-autre-terre-3302a711.png) regardés dans Unity à 1920 × 1080 : 1144 sommets dessinés pour Bar, retour et changement de territoire vérifiés, molette sans zoom derrière le document. Papier, encre et filets suivent DA.md ; les captures réunissent les PR d’interface en cours.

Ce lot livre un plan consultable. Le passage à une ville 3D, les outils de construction et le détail des chantiers restent à réaliser ; les deux kits désert ne sont pas attribués arbitrairement aux autres villes. Le contrat de correspondance est indiqué dans BESOINS-SIM.md.

L’aperçu Windows du 17 octobre, antérieur à ce plan, rassemble commandes, comptes, menu, calques et voisins. [Contrôle de compilation et de lancement](preuves/apercu-17-octobre.zip) : 596 cellules, souris active, service arrêté à la fermeture. L’exécutable reste local dans `.atelier/apercu-cabinet/`, hors git.
