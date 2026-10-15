# État de l’interface — 15 octobre 2026

## Livré et en cours

- UI-01 livré sur master ; UI-02 réalisé et vérifié sur `direct/interface-etats`, en cours de publication.
- Les 108 images du dossier confirmé par le propriétaire ont été regardées, en douze planches de neuf, avec une note par image dans DA.md ; réductions conservées dans `references/`.
- [Cadrage #628](https://github.com/PLiagre/Forge/pull/628) et [socle #630](https://github.com/PLiagre/Forge/pull/630) fusionnés. La relance unique des tests chronométrés de #630 est verte, sans modification de seuil ; [preuve du socle](UI01.md).
- UI-02 : douze nouveaux tests rouges puis verts, six tests du socle toujours verts ; capture Play regardée à 1920 × 1080. Quatre états avec cause explicite ; une donnée absente ne devient pas zéro. [Preuves et limites](UI02.md).
- Worktree isolé : `C:/Users/liagr/.codex/worktrees/8c29/Forge/.atelier/direct/interface-cadrage`. Le checkout principal reste intact.
- Les PR de lots #627 et #511 ont été consultées : aucun fichier commun avec `docs/interface/`.
- Contrôles : liens locaux et 108 empreintes d’originaux vérifiés, douze planches décodées et regardées, diff sans erreur d’espaces ; douze objets LFS retéléchargés du serveur et vérifiés. Aucun test Unity ou moteur exécuté pour cette documentation.

## Décisions et prochaine action

- Source visuelle confirmée : `docs/direction-artistique/`. Les originaux de ce worktree sont des pointeurs LFS ; les images ont été lues dans `D:/Forge/docs/direction-artistique/`, sans modifier ces originaux.
- Choix validés : papier clair sur cadre sombre ; ornements discrets et sceaux sur les engagements ; plusieurs dossiers visibles simultanément. Ce dernier choix remplace la proposition initiale d’un dossier unique pour permettre la comparaison.
- Contrats examinés : lieux, maisons, flux, horloge et intentions du pont. Les fonctions J6–J9 sont planifiées sous réserve de leurs contrats, pas déclarées disponibles.
- UI-01 : branche `direct/interface-socle` depuis `origin/master`, worktree frère `.atelier/direct/interface-socle` ; thème, composants et deux dossiers simultanés dans une galerie isolée.
- UI-02 : worktree `.atelier/direct/interface-etats`, branche partie de `origin/master`, rebasée sur le socle fusionné `116975a`. Aucun fichier commun avec les lots #627 et #511 ; aucune modification de la simulation.
- Prochaine action : attendre la CI et la fusion de UI-02, le marquer livré, puis UI-03 (horloge : pause/vitesse reçues et réponses retardées) depuis `origin/master`. Galeries isolées, police Unity provisoire et aucune donnée du monde branchée.
- Aucune question artistique ouverte ; fontes candidates à vérifier avant intégration, police Unity de secours explicitement provisoire pour la première galerie.
