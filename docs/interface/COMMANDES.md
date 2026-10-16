# Prélèvement et secours — UI-10 / UI-11

Dans « Votre maison », le joueur lit le taux et les réserves au tick reçu, choisit un prélèvement ou un secours, saisit une quantité, puis confirme le récapitulatif. Le sceau rouge est réservé à cette confirmation. Annuler revient au dossier sans envoi. Un reçu reste visible jusqu’au retour explicite ; une panne demande de vérifier le monde avant tout nouvel ordre.

Le formulaire conserve les unités du contrat : pourcentage converti en fraction, secours en kg. Le moteur tranche les droits et les quantités possibles. Aucun stock ni taux n’est recalculé par la vue. Sans comptes reçus pour la maison choisie, la préparation reste indisponible.

Preuve `a20d7db7` : deux contre-épreuves rouges (relevé effacé, préparation toujours inactive), puis 39 tests d’interface verts. [Rapports et parcours réel](preuves/commandes-a20d7db7.zip). Avec le service réel, le prélèvement reste à 3 % pendant la pause malgré le reçu, puis passe à 20 % au tick suivant ; un secours excessif est refusé avec sa cause. Aucun réglage du moteur modifié.

Captures Unity à 1920 × 1080 regardées : [confirmation](preuves/commandes-confirmation-a20d7db7.png), [reçu pendant la pause](preuves/commandes-recu-a20d7db7.png), [refus du grenier](preuves/commandes-refus-a20d7db7.png). Papier et encre conformes à DA.md, engagement rouge, territoire toujours conservé. La carte et la police de secours gardent les limites visuelles déjà indiquées dans PARTIE.md.
