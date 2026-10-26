# Dossier du territoire — UI-08

Un clic droit conserve le territoire ; son dossier lit `/lieu?cell=…` et montre séparément chaque lieu, son nom, son maître, ses habitants, sa surface, ses réserves et ses mouvements sur trente jours. Le tick est celui de cette réponse. Les lieux se parcourent à la molette dans le papier, sans zoomer la carte ni fermer la maison.

Code éprouvé `dd6c2017`, lecteur de #668 : trois tests rouges avant réalisation, puis 33 tests d’interface verts. Deux rangs gardent leurs réserves distinctes ; zéro reste mesuré, flux non transmis reste absent ; cellule différente, rang dupliqué et liste vide refusés. Le cadre masque le débordement et intercepte les clics.

Parcours avec le vrai service, graine 0 : 596 cellules, Bar choisi et confirmé par le monde, reprise/pause, zoom/glissé, territoire 10430 conservé puis dossier défilé par événements de souris. Le zoom de la carte reste identique pendant ce dernier geste. [Rapport et tests](preuves/territoires-dd6c2017.zip).

[Haut du dossier](preuves/territoires-haut-dd6c2017.png) et [fin après défilement](preuves/territoires-defilement-dd6c2017.png) regardés à 1920 × 1080 : papier clair, encre et filet sobres conservés, comparaison avec les références `imprimerie_1600.png` et `forge_1450.png`. Les quantités affichées sont arrondies à deux décimales pour la lecture ; le document reçu reste intact.

Limites : noms et flux absents sont déclarés ; police provisoire ; les contrôles de taille et clavier seront complétés avec UI-33. Aucun nouveau nombre de simulation et aucune intention envoyée par ce dossier.
