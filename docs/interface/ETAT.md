# État de l’interface — 17 octobre 2026

## Livré

- Direction artistique validée : papier clair sur cadre sombre, ornements discrets, plusieurs dossiers simultanés. Les 108 références ont été regardées ; [DA](DA.md).
- Socle et états de lecture (#630–631), choix confirmé de maison (#633), cabinet de carte et matériau compilé (#666–667).
- Lecture fiable et dossiers de territoire (#668–669), confirmation unique des intentions (#670), terres et comptes (#671), menu, aide et navigation clavier (#672).
- Calques puissances/habitants (#673), journal réel des autres maisons (#674), plan consultable du bourg avec retour à la carte (#677).
- Prélèvement et secours (#676), avec confirmation et reçu du monde ; [preuve](COMMANDES.md).

## En cours

- Tracé de rue : PR #708, rebasée après #676. Quatre contre-épreuves rouges puis 57 tests d’interface verts ; annulation sans dépôt, double confirmation unique et effet seulement au tick vérifiés. La suite d’intégration avec les nouveaux contrats de capitale passe 101 tests le 17 octobre.
- Dossier des chantiers : PR #713, `direct/interface-chantiers`, travail accompli, grain payé et motifs d’arrêt reçus. Six contre-épreuves rouges puis 102 tests verts ; parcours réel aux ticks 69/70 et trois captures regardées après correction du bouton masqué. [Preuve](CHANTIERS.md). Objets LFS distants vérifiés ; fusion automatique demandée. L’aperçu Windows précédent ne contient pas encore ce dossier.
- Aperçu local : `.atelier/apercu-cabinet/Jouer.cmd`, compilé le 17 octobre avec tous ces écrans et le tracé `2f69245f`. Lancement réel : 596 cellules, souris active, arrêt du service à la fermeture. Il reste un aperçu de carte et de plan, avec les fontes et les couleurs politiques provisoires.

## Prochaine étape

1. Vérifier les fusions du tracé et des chantiers, puis poursuivre les intentions de parcelles et de bâtiments depuis le plan du bourg.
2. Les lots #685–700 ont livré la correspondance capitale/kit, le choix de cellule et le passage depuis la carte. Examiner leur intégration au cabinet ; le kit actuellement déclaré concerne le Zab, pas Bar-le-Duc.
3. Compléter enceinte et parcours 3D, puis préparer les écrans dynastiques, diplomatiques, militaires et les autres contrats absents dans une démonstration explicitement séparée, comme demandé dans [BESOINS-SIM.md](BESOINS-SIM.md).

Le relief, les trajets détaillés, les interfaces avancées, la typographie et les contrôles de lisibilité à toutes les tailles restent ouverts. Toute l’interface n’est pas terminée. Aucune nouvelle décision artistique n’est attendue du propriétaire ; aucun changement de la simulation dans ces branches.
