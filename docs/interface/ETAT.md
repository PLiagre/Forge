# État de l’interface — 17 octobre 2026

## Livré et en cours

- UI-14 réalisé sur `direct/interface-voisins` : journal réel des autres maisons, causes et refus, sans interpréter un reçu comme un achèvement. Trois rouges puis 49 verts ; sept ordres au tick 62, captures regardées et défilement vérifié. [Preuve](VOISINS.md). Les PR #670–673 attendent la CI ; les commandes visibles sont préparées et attendent #670. Prochaine étape : actualiser l’aperçu puis consulter le plan du bourg sans charger un kit 3D qui ne correspond pas à sa terre.

- UI-08 réalisé sur `direct/interface-territoires` : habitants, maîtres, réserves et flux par lieu, tous au tick reçu ; molette contenue dans le dossier. Trois rouges puis 33 verts ; captures du vrai service regardées. [Preuve](TERRITOIRES.md). Publication après le lecteur #668 ; en parallèle, préparation des ordres de prélèvement et de secours.

- Le propriétaire demande toute la suite. #666 et #667 fusionnés. UI-08a (`direct/interface-lecture-dossiers`) prépare les dossiers économiques ; quatre tests rouges puis trente verts. Les contrats avancés absents du service sont recensés dans [BESOINS-SIM.md](BESOINS-SIM.md), sans modification du moteur. Prochaine réalisation : dossier détaillé de territoire, comptes et commandes de maison, puis navigation et écrans avancés séparés de la partie réelle.

- UI-01 et UI-02 livrés sur master (#630, #631). Raccordement [#633](https://github.com/PLiagre/Forge/pull/633) fusionné ; écran [#666](https://github.com/PLiagre/Forge/pull/666) et matériau du build [#667](https://github.com/PLiagre/Forge/pull/667) en fusion automatique sous réserve de CI verte.
- UI-09 et UI-12, PR #671 : feuillet des terres, suzerain et flux, 42 tests verts et capture réelle regardée ; [preuve](COMPTES.md). #669 fusionné ; confirmations #670 et menu #672 en cours. Formulaires testés sur `direct/interface-commandes`.
- Les 108 images du dossier confirmé par le propriétaire ont été regardées, en douze planches de neuf, avec une note par image dans DA.md ; réductions conservées dans `references/`.
- [Cadrage #628](https://github.com/PLiagre/Forge/pull/628) et [socle #630](https://github.com/PLiagre/Forge/pull/630) fusionnés. La relance unique des tests chronométrés de #630 est verte, sans modification de seuil ; [preuve du socle](UI01.md).
- UI-02 : douze nouveaux tests rouges puis verts, six tests du socle toujours verts ; capture Play regardée à 1920 × 1080, objet LFS distant retéléchargé et empreinte vérifiée. Quatre états avec cause explicite ; une donnée absente ne devient pas zéro. [Preuves et limites](UI02.md).
- Worktree isolé : `C:/Users/liagr/.codex/worktrees/8c29/Forge/.atelier/direct/interface-cadrage`. Le checkout principal reste intact.
- UI-07a sur `direct/interface-calques` : puissances et habitants, légende datée, deux rouges puis 46 verts ; 596 cellules et retour de sélection joués, capture corrigée puis regardée. [Preuve](CALQUES.md). #669 fusionné ; #670–#672 rebasés sur master après résolution du suivi. Suite : dossier des voisins, puis ville et écrans avancés ; le relief attend son contrat.
- Les PR de lots #627 et #511 ont été consultées : aucun fichier commun avec `docs/interface/`.
- Contrôles : liens locaux et 108 empreintes d’originaux vérifiés, douze planches décodées et regardées, diff sans erreur d’espaces ; douze objets LFS retéléchargés du serveur et vérifiés. Aucun test Unity ou moteur exécuté pour cette documentation.

- UI-10a, PR #670 : modèle de confirmation, quatre rouges puis 37 verts ; [preuve](ORDRES.md). Territoires #669 fusionnés, captures LFS distantes vérifiées. Formulaires déjà testés et poussés sur `direct/interface-commandes` ; publier leur PR après fusion de #670.
## Décisions et prochaine action

- Reprise du 17 octobre : territoires #669, confirmations #670, calques #673 et voisins #674 fusionnés. Comptes #671 et menu #672 rebasés ; formulaires UI-10/UI-11 prêts à publier après retrait de leur dépendance déjà fusionnée.
- Menu et aide réalisés sur `direct/interface-menu` : Échap, Tabulation, retour de focus et silence ; deux rouges puis 44 verts, capture réelle regardée. [Preuve](MENU.md). Aperçu Windows actualisé dans `.atelier/apercu-cabinet/` avec commandes, comptes, menu, calques et voisins : 49 tests verts, 596 cellules et arrêt du service vérifiés. Toute l’interface n’est pas encore terminée.
- Prochaine action précise : publier les formulaires, terminer la preuve visuelle du plan du bourg puis poursuivre les outils de ville. Les écrans sans contrat de simulation seront construits dans une démonstration identifiée, conformément à BESOINS-SIM.md. Aucune nouvelle décision artistique à demander.

- Source visuelle confirmée : `docs/direction-artistique/`. Les originaux de ce worktree sont des pointeurs LFS ; les images ont été lues dans `D:/Forge/docs/direction-artistique/`, sans modifier ces originaux.
- Choix validés : papier clair sur cadre sombre ; ornements discrets et sceaux sur les engagements ; plusieurs dossiers visibles simultanément. Ce dernier choix remplace la proposition initiale d’un dossier unique pour permettre la comparaison.
- Contrats examinés : lieux, maisons, flux, horloge et intentions du pont. Les fonctions J6–J9 sont planifiées sous réserve de leurs contrats, pas déclarées disponibles.
- UI-01 : branche `direct/interface-socle` depuis `origin/master`, worktree frère `.atelier/direct/interface-socle` ; thème, composants et deux dossiers simultanés dans une galerie isolée.
- UI-02 : worktree `.atelier/direct/interface-etats`, branche partie de `origin/master`, rebasée sur le socle fusionné `116975a`. Aucun fichier commun avec les lots #627 et #511 ; aucune modification de la simulation.
- UI-02 fusionné (#631). Le propriétaire demande maintenant l’écran de partie concret : carte, maison, temps et dossiers, sans nouvelle galerie. [Découpage et contrat](PARTIE.md).
- Écran : worktree `.atelier/direct/interface-ecran`, depuis master avec le raccordement #633 ; 26 tests verts et parcours du vrai service (choix, reprise/pause, zoom, glissé, clic droit, panneaux). [Lancement et captures](PARTIE.md). Ancien choix direct arrêté au profit de la confirmation du cabinet.
- Prochaine action : après fusion de #666 et #667, poursuivre avec les dossiers de lieu. Aperçu Windows vérifié : 596 cellules, souris disponible, arrêt du service à la fermeture ; 40 tests carte/interface verts. UI-03 conserve ses preuves complémentaires de réponses retardées.
- Aucune question artistique ouverte ; fontes candidates à vérifier avant intégration, police Unity de secours explicitement provisoire pour la première galerie.

