# Menu et aide — UI-04 / UI-34

Le bouton Menu ou Échap ouvre un papier d’aide. Revenir au jeu ou Échap le ferme en rendant le focus précédent, sans perdre le territoire conservé ni changer le rythme de la simulation. La note du menu rappelle que Pause reste une action explicite du joueur.

Tabulation et Majuscule + Tabulation parcourent les commandes actives ; dans le menu, le parcours reste sur ses commandes. Le réglage du volume agit sur `AudioListener.volume`, de silence à plein volume, pour la session courante. Aucun son décoratif ni fichier sonore ajouté. Les gestes de carte, de dossier et de confirmation restent expliqués par écrit.

Preuve `922bb6d5` : deux contre-épreuves rouges, puis 44 tests d’interface verts, dont un test de focus dans le cycle Play réel de Unity. Le service réel a aussi été joué avec Échap, Tabulation, silence et retour au même territoire. [Rapports](preuves/menu-922bb6d5.zip), [capture Unity regardée](preuves/menu-cabinet-922bb6d5.png). Le papier clair, les filets discrets et les commandes espacées reprennent DA.md. Le projet de preuve contient également les territoires, commandes et comptes des lots précédents.

Cette livraison ne comprend pas encore le réglage de taille du texte, les sauvegardes ni le parcours complet des écrans avancés ; leur état reste séparé dans LOTS.md.
