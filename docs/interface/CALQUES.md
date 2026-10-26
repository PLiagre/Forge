# Habitants sur la carte — UI-07a

Le joueur alterne entre les puissances de la carte de 1400 et les habitants reçus du monde. La légende indique les bornes mesurées, le tick et l’échelle logarithmique des teintes. Les nombres de population ne changent pas ; seul leur rendu varie. Le territoire conservé reste rouge et son dossier reste ouvert.

Une liste vide, un territoire dupliqué, une population négative, un compte incohérent ou une cellule absente refuse le calque entier avant tout changement de couleur. Le retour affiche les couleurs des puissances avec la cause. Le relief n’est pas inventé : son contrat manque encore, comme indiqué dans BESOINS-SIM.md.

Preuve `897fa9f0` : deux rouges puis 46 tests d’interface verts. [Rapports et parcours](preuves/calques-897fa9f0.zip). Service réel : 596 cellules teintées, bornes 5 et 360127 habitants au tick 2, puis retour aux puissances avec une seule sélection conservée. [Capture Unity regardée](preuves/calques-habitants-897fa9f0.png). La première capture trop pâle a été corrigée ; les teintes mates reprennent le papier et l’accent de DA.md, convertis pour le rendu linéaire de la carte.
