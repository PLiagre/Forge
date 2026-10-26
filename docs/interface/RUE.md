# Préparer une rue — UI-17

Sur le plan d’un bourg dont sa maison est maître, le joueur place les points, saisit la largeur en mètres et les foyers mobilisés, puis relit le récapitulatif. Les pointillés désignent son brouillon ; ils restent distincts des chantiers reçus. Annuler ou fermer avant confirmation ne dépose rien. Un changement de territoire invalide le brouillon. La validation des droits et du terrain reste au moteur.

La confirmation envoie une intention unique. Le reçu accepté, refusé ou inconnu reste affiché jusqu’au retour explicite du joueur ; une panne ne relance jamais l’ordre. Le plan ne reçoit la rue que par sa lecture du monde. Un reçu ne signifie pas chantier achevé, et le coût n’est pas calculé dans la vue.

Preuve `2f69245f` : quatre contre-épreuves rouges, dont une largeur `NaN`, puis 57 tests d’interface verts. [Rapports, intention, plan appliqué et parcours](preuves/rue-2f69245f.zip). Sur le vrai service en pause : annulation sans dépôt, deux confirmations rapprochées pour une seule rue, aucun effet avant le tick, puis passage de deux à trois rues. L’outil reste inactif sur la terre des Visconti.

Captures Unity regardées à 1920 × 1080 : [récapitulatif](preuves/rue-confirmation-2f69245f.png), [reçu](preuves/rue-recu-2f69245f.png), [autre maison](preuves/rue-terre-etrangere-2f69245f.png). Papier et cire suivent DA.md ; les pointillés portent l’état sans dépendre uniquement de la couleur. Les captures réunissent les écrans en cours dans le projet d’intégration.

Branche `direct/interface-rue`, rebasée après fusion du plan #677 ; la dépendance provisoire `cc563597` a été retirée. Le diff propre du tracé reste sous 300 lignes. Parcelles, bâtiments et détail des chantiers restent à réaliser ; les contrats de passage à la capitale livrés dans #685–700 doivent être intégrés au cabinet.

Aperçu Windows recompilé et lancé le 17 octobre avec ce tracé : 596 cellules, souris active, code de sortie 0 et arrêt du service. [Contrôle du build et du lancement](preuves/apercu-rue-2f69245f.zip). Lancement local : `.atelier/apercu-cabinet/Jouer.cmd` ; le guide de ce dossier décrit le parcours.
