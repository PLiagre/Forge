# État de l’interface — 14 octobre 2026

## Livré et en cours

- Aucun composant Unity livré ; UI-01 commencé après validation artistique du propriétaire.
- Les 108 images du dossier confirmé par le propriétaire ont été regardées, en douze planches de neuf, avec une note par image dans DA.md ; réductions conservées dans `references/`.
- Cadrage : `direct/interface-cadrage`, base `origin/master` à `2535e03` ; [PR #628](https://github.com/PLiagre/Forge/pull/628), fusion automatique activée, contrôles en cours.
- Worktree isolé : `C:/Users/liagr/.codex/worktrees/8c29/Forge/.atelier/direct/interface-cadrage`. Le checkout principal reste intact.
- Les PR de lots #627 et #511 ont été consultées : aucun fichier commun avec `docs/interface/`.
- Contrôles : liens locaux et 108 empreintes d’originaux vérifiés, douze planches décodées et regardées, diff sans erreur d’espaces ; douze objets LFS retéléchargés du serveur et vérifiés. Aucun test Unity ou moteur exécuté pour cette documentation.

## Décisions et prochaine action

- Source visuelle confirmée : `docs/direction-artistique/`. Les originaux de ce worktree sont des pointeurs LFS ; les images ont été lues dans `D:/Forge/docs/direction-artistique/`, sans modifier ces originaux.
- Choix validés : papier clair sur cadre sombre ; ornements discrets et sceaux sur les engagements ; plusieurs dossiers visibles simultanément. Ce dernier choix remplace la proposition initiale d’un dossier unique pour permettre la comparaison.
- Contrats examinés : lieux, maisons, flux, horloge et intentions du pont. Les fonctions J6–J9 sont planifiées sous réserve de leurs contrats, pas déclarées disponibles.
- UI-01 : branche `direct/interface-socle` depuis `origin/master`, worktree frère `.atelier/direct/interface-socle` ; thème, composants et deux dossiers simultanés dans une galerie isolée.
- Prochaine action : test rouge du socle, implémentation puis test vert et capture Unity regardée ; ouvrir sa PR sans dépendre de la fusion du cadrage pour les fichiers de code.
- Aucune question artistique ouverte ; fontes candidates à vérifier avant intégration, police Unity de secours explicitement provisoire pour la première galerie.
