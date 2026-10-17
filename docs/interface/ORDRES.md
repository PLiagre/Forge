# Confirmation des ordres — UI-10a

Le modèle prépare les gestes de prélèvement et de secours : un brouillon annulable, une confirmation unique, puis un reçu conservé. Aucun envoi automatique après refus ou panne ; recommencer exige un nouveau geste du joueur. Un reçu ne modifie aucune donnée du monde.

Les saisies acceptent virgule ou point. Le pourcentage devient une fraction, les réserves restent en kg ; les limites économiques appartiennent au service. Ce lot ne présente pas encore les formulaires à l’écran : le raccord visible suit dans le dossier de maison.

Preuve : quatre tests rouges avant implémentation, puis 37 tests verts (dont les 33 précédents), [rapports bruts](preuves/ordres-677352d8.zip). Code testé : `677352d8`. Pas de changement visuel dans ce lot ; les captures du [territoire](TERRITOIRES.md) concernent le dernier écran effectivement joué, pas ces commandes.
