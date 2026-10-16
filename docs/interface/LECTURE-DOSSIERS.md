# Lecture des dossiers — UI-08a

Le geste préparé : ouvrir un autre territoire sans recevoir ensuite les stocks du précédent, et consulter un dossier économique avec le tick de sa propre réponse. `LectureDossier` lit un document du service local, garde une seule demande par sélection et rejette les réponses de l’ancienne sélection. Une panne retire les nombres devenus invérifiables ; un tick ancien ne remplace pas le dernier reçu.

Code éprouvé `a211d85b` : quatre tests rouges sur le composant vide, puis trente tests d’interface verts. Cas : absence distincte de zéro, changement de sélection pendant une lecture, panne sans renvoi automatique, double demande et retour d’un tick ancien. [Rapports bruts](preuves/lecture-dossiers-a211d85b.zip). Les données de test sont fictives et ne circulent jamais dans la partie.

Ce lot de lecture ne change pas encore la présentation du cabinet : sa [capture Unity déjà vérifiée](preuves/cabinet-partie-af3d6b28.png) reste le point de comparaison papier/encre. Le dossier visible et sa capture avec le vrai service sont le lot suivant. L’audit [BESOINS-SIM.md](BESOINS-SIM.md) distingue les contrats réellement servis des écrans avancés à préparer en démonstration.
